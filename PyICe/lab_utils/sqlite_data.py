"""Sqlite data utility."""
import datetime
import sqlite3
import re
import ast
import numpy
import pandas
import collections
from .time_zones import UTC
from .str2num import str2num


class sqlite_data(
        collections.abc.Sequence):  # collections.Iterable to disable slicing?
    """Provide an iterable, sequence-like interface over SQLite query results.

    Each row returned behaves like a ``sqlite3.Row`` object, meaning
    individual columns can be accessed by column name (``row['vbat']``) or by
    positional index (``row[0]``).  The class also supports integer indexing,
    slicing, ``len()``, and iteration so it can be used anywhere a Python
    sequence is expected.  ``table_name`` may be a plain table name, a view
    name, or any SQL expression that produces a relation.

    Typical downstream consumers include ``LTC_plot`` for graphing, ``numpy``
    record-array conversion, ``pandas`` DataFrame conversion, CSV/XLSX export,
    and the ``lab_core.logger`` post-processing pipeline.
    """

    def __init__(self, table_name=None,
                 database_file='data_log.sqlite', timezone=None):
        """Open a SQLite database connection and prepare type converters.

        Register custom SQLite type converters for DATETIME, NUMERIC,
        PyICe collection types, and PyICe BLOB arrays so that values are
        automatically deserialized into Python ``datetime``, ``list``,
        ``dict``, ``tuple``, or ``numpy.ndarray`` objects when rows are
        fetched.  If *table_name* is provided, a default ``SELECT *``
        query is constructed immediately.

        Args:
            table_name: Name of the SQLite table (or view, or any SQL
                expression that yields a relation) to query.  When
                ``None``, the caller must later call :meth:`set_table`
                or :meth:`query` before iterating.
            database_file: Filesystem path to the SQLite database file
                produced by ``lab_core.logger`` or any other writer.
            timezone: A ``tzinfo`` instance used to localize stored UTC
                timestamps.  Defaults to UTC when ``None``.
        """
        if timezone is None:
            self.timezone = UTC()
        else:
            self.timezone = timezone
        sqlite3.register_converter("DATETIME", self.convert_timestring)
        sqlite3.register_converter("NUMERIC", self.convert_vector)
        sqlite3.register_converter("PyICeDict", self.convert_vector)  # TODO
        sqlite3.register_converter("PyICeTuple", self.convert_vector)  # TODO
        sqlite3.register_converter("PyICeList", self.convert_vector)  # TODO
        sqlite3.register_converter("PyICeBLOB", self.convert_ndarray)
        sqlite3.register_converter("PyICeFloatList", lambda d: numpy.fromstring(
            d[1:-1], sep=',', dtype=numpy.dtype('<d')))
        sqlite3.register_converter("PyICeIntList", lambda d: numpy.fromstring(
            d[1:-1], sep=',', dtype=numpy.dtype('int')))
        # automatically convert datetime column to Python datetime object
        self.conn = sqlite3.connect(
            database_file,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.conn.row_factory = sqlite3.Row  # index row data tuple by column name
        self.set_table(table_name)
        self.sql_query = None
        self.params = []
        if table_name is not None:
            # remove rowid because it's now an explicitly stored column from
            # the logger
            self.sql_query = "SELECT * from {}".format(table_name)

    def set_table(self, table_name):
        """Store the default table name used by subsequent queries.

        Call this to change which table (or view) the instance targets
        without re-creating the connection.  Note that this does *not*
        rebuild the default ``SELECT *`` query; call :meth:`query`
        afterward to update the active SQL statement.

        Args:
            table_name: Name of the SQLite table, view, or sub-select
                expression to use as the default relation.
        """
        self.table_name = table_name

    def convert_timestring(self, time_bytes):
        """Convert a stored UTC timestamp byte-string into a timezone-aware datetime.

        SQLite stores timestamps as ISO-8601 ASCII strings
        (``'%Y-%m-%dT%H:%M:%S.%fZ'``).  This converter parses the
        byte-string, attaches UTC, then converts to the instance's
        configured timezone so that all downstream consumers see
        correctly localized ``datetime.datetime`` objects.

        Args:
            time_bytes: Raw bytes read from a DATETIME column, expected
                to decode to an ASCII ISO-8601 timestamp ending in 'Z'.

        Returns:
            A timezone-aware ``datetime.datetime`` localized to the
            timezone specified at construction time.
        """
        time_string = time_bytes.decode('ascii')
        return datetime.datetime.strptime(
            time_string, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=UTC()).astimezone(self.timezone)

    @classmethod
    def convert_vector(cls, col_data_bytes):
        """Deserialize a NUMERIC or PyICe collection column value from bytes.

        Detects whether the stored UTF-8 string represents a list
        (``[…]``), dict (``{…}``), or tuple (``(…)``) and reconstructs
        the original Python object via ``ast.literal_eval``.  Scalar
        values are converted with ``str2num``.

        Args:
            col_data_bytes: Raw bytes read from a NUMERIC, PyICeDict,
                PyICeTuple, or PyICeList column in the database.

        Returns:
            The deserialized Python object: a ``list``, ``dict``,
            ``tuple``, ``int``, ``float``, or the original string if
            numeric conversion fails.
        """
        col_data_str = col_data_bytes.decode('utf-8')
        if re.match(r'^\[.*\]$', col_data_str):
            return ast.literal_eval(col_data_str)  # This is slow!
        elif re.match(r'^\{.*\}$', col_data_str):
            return ast.literal_eval(col_data_str)
        elif re.match(r'^\(.*\)$', col_data_str):
            return ast.literal_eval(col_data_str)
        else:
            return str2num(col_data_str, except_on_error=False)

    def convert_ndarray(self, col_data_bytes):
        # Expect flat (1d) array of homogeneous dtype
        # uint8; support up to 255 format string characters to follow
        """Reconstruct a flat numpy ndarray from a PyICeBLOB column.

        PyICe stores numpy arrays as binary blobs with a leading
        length-prefixed dtype format string (e.g. ``<d`` for
        little-endian float64).  This converter reads the dtype header
        and rebuilds the original 1-D array.

        Args:
            col_data_bytes: Raw bytes read from a PyICeBLOB column.
                The first byte encodes the length of the dtype format
                string that immediately follows, with array data after.

        Returns:
            A 1-D ``numpy.ndarray`` with the dtype specified in the blob
            header.
        """
        fmt_str_size = col_data_bytes[0]
        # ascii dtype format string, ex "<d" little endian double precision
        # float 64.
        fmt_str = col_data_bytes[1:fmt_str_size + 1]
        return numpy.frombuffer(
            col_data_bytes, offset=1 + fmt_str_size, dtype=numpy.dtype(fmt_str))

    def __getitem__(self, key):
        """Retrieve one row by integer index, or a list of rows by slice.

        Translates the Python index or slice into SQL ``LIMIT``/``OFFSET``
        clauses applied to the active query, so only the requested rows
        are fetched from the database.  Negative indices and slice steps
        are not supported.

        Args:
            key: An integer row index (0-based) returning a single
                ``sqlite3.Row``, or a ``slice`` object returning a list
                of rows.

        Returns:
            A single ``sqlite3.Row`` when *key* is an integer, or a list
            of ``sqlite3.Row`` objects when *key* is a slice.

        Raises:
            Exception: If the slice has ``start >= stop`` (reverse
                iteration) or if a slice step is provided.
        """
        subs = {}
        if isinstance(key, slice):
            if key.start is None:
                subs['start'] = 0
            else:
                subs['start'] = key.start
            if key.stop is None:
                subs['limit'] = -1  # no limit
            else:
                if subs['start'] >= key.stop:
                    raise Exception('Reverse iteration not supported.')
                subs['limit'] = key.stop - subs['start']
            if key.step is not None:
                raise Exception('Slice step not supported.')
            fetch = sqlite3.Cursor.fetchall
        else:
            subs['start'] = key
            subs['limit'] = 1
            fetch = sqlite3.Cursor.fetchone
        return fetch(self.conn.execute(
            self.sql_query + " LIMIT {limit} OFFSET {start};".format(**subs), self.params))

    def __iter__(self):
        """Yield rows from the active query by executing it against the database.

        Each iteration re-executes the stored SQL query, so the caller
        always sees the current state of the database.  Each yielded
        item is a ``sqlite3.Row`` supporting both column-name and
        positional access.

        Returns:
            A ``sqlite3.Cursor`` that lazily yields ``sqlite3.Row``
            objects one at a time.
        """
        return self.conn.execute(self.sql_query, self.params)

    def __len__(self):
        """Return the total number of rows matched by the active SQL query.

        WARNING: This fetches *all* rows into memory just to count them,
        which is very expensive on large result sets.  Prefer iterating
        or slicing when possible instead of calling ``len()``.

        Returns:
            The integer count of rows in the full result set.
        """
        # this is hard because the iterable doesn't actually know its length
        # self.cursor.rowcount doesn't work; returns -1 when database isn't modified.
        # not very efficient for big dataset!
        return len(self.conn.execute(self.sql_query, self.params).fetchall())

    def __enter__(self):
        """Enter the context manager, returning this instance for use in a ``with`` block.

        Using ``sqlite_data`` as a context manager guarantees the
        underlying SQLite connection is closed when the block exits,
        even if an exception occurs.

        Returns:
            This ``sqlite_data`` instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the underlying SQLite connection when leaving the ``with`` block.

        Any pending transaction is implicitly rolled back by the
        ``sqlite3`` module when the connection is closed.

        Args:
            exc_type: The exception class if an exception was raised
                inside the ``with`` block, otherwise ``None``.
            exc_val: The exception instance if one was raised, otherwise
                ``None``.
            exc_tb: The traceback object if an exception was raised,
                otherwise ``None``.
        """
        self.conn.close()

    def get_table_names(self, include_views=True):
        """Return the names of all tables (and optionally views) in the database.

        Queries the ``sqlite_master`` catalog to discover what relations
        exist.  Useful for inspecting an unfamiliar database file before
        choosing which table to query.

        Args:
            include_views: When ``True`` (the default), include SQL
                views alongside physical tables in the result.

        Returns:
            A list of table (and view) name strings.  Returns an empty
            list if the database contains no tables.
        """
        view_where = "OR type == 'view'" if include_views else ''
        tables = self.conn.execute(
            f"SELECT name FROM sqlite_master WHERE type == 'table'{view_where}").fetchall()
        if tables is None:
            return []
        else:
            return [r[0] for r in tables]

    def get_column_names(self):
        """Return the column names produced by the active SQL query.

        Executes the query, inspects the first row's keys, and returns
        them as a list.  These names can be used to build subsequent
        queries, to index into ``sqlite3.Row`` results, or to label
        axes in ``LTC_plot``.

        Returns:
            A list of column-name strings in query-column order, or
            ``None`` if the query returned no rows.

        Raises:
            Exception: If no table name or query has been set on this
                instance.
        """
        if self.sql_query is None:
            raise Exception('table_name not specified')
        first_row = self.conn.execute(self.sql_query, self.params).fetchone()
        if first_row is None:
            return None
        return list(first_row.keys())

    def get_column_types(self):
        """Return the Python type of each column based on the first row of data.

        Because SQLite uses dynamic typing and the PyICe logger does not
        enforce column types, the types found in the first row may not
        match those in subsequent rows.  This method is primarily used
        internally by :meth:`numpy_recarray` to build the ``dtype``
        descriptor for the record array.

        Returns:
            An ``OrderedDict`` mapping column-name strings to Python
            type objects (e.g. ``{'vbat': <class 'float'>, ...}``).
        """
        cursor = self.conn.execute(self.sql_query, self.params).fetchone()
        return collections.OrderedDict(
            [(k, type(cursor[k])) for k in list(cursor.keys())])

    def get_distinct(self, column_name, table_name=None,
                     where_clause=None, force_tuple=False):
        """Return the sorted unique values found in one or more columns.

        Issues a ``SELECT DISTINCT`` query against the specified (or
        default) table.  This is useful for discovering what parameter
        values exist in a sweep, building UI selection lists, or
        constructing ``WHERE … IN (…)`` clauses for follow-up queries.
        When multiple columns are requested, each distinct combination
        is returned as a ``namedtuple``.

        Args:
            column_name: A single column-name string, or a list/tuple
                of column-name strings to retrieve distinct
                combinations of.
            table_name: Table, view, or sub-select expression to query.
                Falls back to the instance default when ``None``.
            where_clause: Optional SQL ``WHERE`` clause (including the
                ``WHERE`` keyword) to restrict which rows are
                considered.
            force_tuple: When ``True`` and *column_name* is a single
                string, wrap each value in a one-element ``namedtuple``
                instead of returning bare scalars.

        Returns:
            A tuple of distinct values sorted in ascending order.
            Single-column queries return scalar values unless
            *force_tuple* is ``True``; multi-column queries return
            ``namedtuple`` instances.

        Raises:
            Exception: If *table_name* is ``None`` and no default table
                was set on the instance.
        """
        if isinstance(column_name, (list, tuple)):
            column_names = ', '.join(column_name)
            column_count = len(column_name)
            column_list = list(column_name)
        else:
            column_names = column_name
            column_count = 1
            column_list = [column_name]
        nt_type = collections.namedtuple('distincts', column_list)
        if table_name is None:
            table_name = self.table_name
            if table_name is None:
                raise Exception('table_name not specified')
        if where_clause is None:
            where_clause = ""
        data = self.conn.execute(
            f"SELECT DISTINCT {column_names} from {table_name} {where_clause};").fetchall()
        if column_count > 1 or force_tuple:
            try:
                distincts = sorted(nt_type._make(row) for row in data)
            except TypeError:
                distincts = (nt_type._make(row) for row in data)
            # Sorted will sort distincts by the first distinct column name
            # requested, then by the 2nd column name, and so on. e.g
            # get_distinct((x,y)) will sort by x then by y
        else:
            try:
                distincts = sorted(row[0] for row in data)
            except TypeError:
                distincts = (row[0] for row in data)
        return tuple(distincts)

    def query(self, sql_query, *params):
        """Execute an arbitrary SQL query and make its results the active dataset.

        Replaces the default ``SELECT *`` query with a custom SQL
        statement.  After calling this method, iteration, indexing,
        slicing, and export methods all operate on the new result set.
        Each row returned supports access by column name or by
        positional index.

        Args:
            sql_query: A complete SQL ``SELECT`` statement (or any
                statement that returns rows).
            *params: Bind-parameter values substituted for ``?``
                placeholders in *sql_query*, following ``sqlite3``
                parameter substitution rules.

        Returns:
            A ``sqlite3.Cursor`` over the result set, which can be
            iterated immediately or ignored in favor of later
            sequence-style access on this instance.
        """
        self.sql_query = sql_query
        self.params = params
        return self.conn.execute(self.sql_query, self.params)

    def zip(self):
        """Transpose the active query results from row-major to column-major order.

        Iterates all rows and applies the built-in ``zip`` transpose so
        that the result is a list of tuples, one per column, where each
        tuple contains all row values for that column.  Useful for
        feeding columnar data directly into plotting functions.

        Returns:
            A list of tuples, one per column, each containing all row
            values for that column in query order.
        """
        return list(zip(*self))

    def csv(self, output_file, elapsed_time_columns=False,
            append=False, encoding='utf-8'):
        """Export the active query results to a comma-separated-values file.

        Iterates all rows and serializes them as CSV text with proper
        escaping (doubled double-quotes, comma-containing fields
        wrapped in quotes).  If *output_file* is ``None``, no file is
        written and only the CSV string is returned, which is useful
        for programmatic consumption.

        Args:
            output_file: Filesystem path for the output CSV file.  Pass
                ``None`` to skip writing and just return the CSV string.
            elapsed_time_columns: When ``True``, insert ``elapsed_time``
                and ``elapsed_seconds`` columns immediately after the
                ``datetime`` column, computed relative to the first row.
            append: When ``True``, append to *output_file* instead of
                overwriting it.
            encoding: Character encoding used when writing the file.

        Returns:
            The full CSV text as a string, regardless of whether a file
            was written.
        """
        # migrate to csv.DictWriter ?
        # https://docs.python.org/3/library/csv.html
        output_txt = ""
        datetime_col = None
        for pos, column in enumerate(self.get_column_names()):
            output_txt += '{},'.format(column)
            if elapsed_time_columns and column == 'datetime':
                output_txt += 'elapsed_time,'
                output_txt += 'elapsed_seconds,'
                datetime_col = pos
        output_txt = '{}\n'.format(output_txt[:-1])
        start_time = None
        for row in self:
            for pos, column in enumerate(row):
                # stringify data
                esc_data = str(column)
                # escape rules:
                if '"' in esc_data:
                    # doubled double quotes escape all double quotes
                    esc_data = esc_data.replace('"', '""')
                if ',' in esc_data:
                    # double quotes enclose all fields containing commas
                    esc_data = '"{}"'.format(esc_data)
                output_txt += '{},'.format(esc_data)
                if start_time is None and pos == datetime_col:
                    start_time = column
                if elapsed_time_columns and pos == datetime_col:
                    # elapsed_time
                    output_txt += '{},'.format(column - start_time)
                    # elapsed_seconds
                    output_txt += '{},'.format((column -
                                                start_time).total_seconds())
            output_txt = '{}\n'.format(output_txt[:-1])
        if output_file is not None:
            with open(output_file, 'a' if append else 'w') as f:
                f.write(output_txt.encode(encoding))
                f.close()
            print('Output written to {}'.format(output_file))
        return output_txt

    def xlsx(self, output_file, elapsed_time_columns=False):
        """Export the active query results to an Excel ``.xlsx`` workbook.

        Creates a single-worksheet workbook using the internal
        ``sqlite_to_xlsx`` helper.  The worksheet contains the same
        columns as the active query, optionally augmented with elapsed-
        time columns.

        Args:
            output_file: Filesystem path for the output ``.xlsx`` file.
            elapsed_time_columns: When ``True``, insert elapsed-time
                columns computed from the ``datetime`` column, matching
                the behavior of :meth:`csv`.
        """
        from .sqlite_to_xlsx import sqlite_to_xlsx  # local import to avoid circular dependency
        with sqlite_to_xlsx(output_file) as writer:
            writer.add_worksheet(self, elapsed_time_columns)
            writer.close()

    def to_list(self):
        """Materialize all query results into a plain Python list.

        Unlike iterating directly (which uses a lazy cursor), this
        method loads every row into memory at once, which is handy when
        the data needs to be traversed more than once without
        re-executing the query.

        Returns:
            A list of ``sqlite3.Row`` objects, one per result row.
        """
        return [row for row in self]

    def numpy_recarray(self, force_float_dtype=False, data_types=None):
        """Convert the active query results into a NumPy record array.

        Record arrays allow column access by attribute name
        (``arr.vbat``) and row access by integer index (``arr[2]``),
        making them convenient for vectorized math with SciPy,
        ``lab_utils.transform``, and ``lab_utils.decimate``.

        By default, column names and dtypes are inferred from the first
        row of data.  Use *force_float_dtype* to coerce all columns to
        ``float``, or supply *data_types* for full manual control.

        Args:
            force_float_dtype: When ``True``, set every column's dtype
                to ``float`` regardless of the actual stored type.
                Mutually exclusive with *data_types*.
            data_types: An iterable of ``(column_name, example_value)``
                pairs used to build the ``numpy.dtype``.  The Python
                type of each *example_value* determines the column
                dtype.  Mutually exclusive with *force_float_dtype*.

        Returns:
            A ``numpy.recarray`` whose fields correspond to the query
            columns.

        Raises:
            Exception: If both *force_float_dtype* and *data_types* are
                specified at the same time.
        """
        if force_float_dtype and data_types is None:
            dtype = numpy.dtype([(key, type(float()))
                                for key in self.get_column_types()])
        elif force_float_dtype and data_types is not None:
            raise Exception(
                'Specify only one of force_float_dtype, data_types arguments.')
        elif data_types is None:
            dtype = numpy.dtype([(k, v)
                                for k, v in self.get_column_types().items()])
        else:
            dtype = numpy.dtype([(column_name, type(example_contents))
                                for column_name, example_contents in data_types])
        arr = numpy.array([tuple(row) for row in self], dtype)
        return arr.view(numpy.recarray)

    def pandas_dataframe(self):
        """Convert the active query results into a Pandas DataFrame.

        Delegates to ``pandas.read_sql_query`` using the current
        connection and stored SQL query, so registered type converters
        (datetime, vectors, etc.) are applied automatically.  The
        resulting DataFrame is convenient for exploratory analysis,
        groupby operations, and integration with Jupyter notebooks.

        Returns:
            A ``pandas.DataFrame`` with one column per query column and
            one row per result row.
        """
        return pandas.read_sql_query(self.sql_query,
                                     self.conn,
                                     params=self.params,
                                     # index_col='rowid',
                                     # parse_dates={'datetime':
                                     # '%Y-%m-%dT%H:%M:%S.%fZ'}) #date parsing
                                     # not necessary with SQLite3 registered
                                     # converter
                                     )

    def column_query(self, column_list):
        """Build a comma-separated column list fragment for use inside a SQL SELECT.

        Concatenates the column names with commas so the result can be
        interpolated directly into a ``SELECT`` statement, e.g.
        ``"SELECT {} FROM …".format(obj.column_query(['a', 'b']))``.

        Args:
            column_list: An iterable of column-name strings to include
                in the fragment.

        Returns:
            A single string of comma-separated column names (no
            trailing comma).
        """
        str = ''
        for column in column_list:
            str += '{},'.format(column)
        return str[:-1]

    def time_delta_query(self, time_div=1, column_name=None):
        """Build a SQL expression that computes elapsed time from the first row.

        The returned fragment is a computed-column expression suitable
        for embedding in a ``SELECT`` list, e.g.::

            "SELECT rowid, {}, * FROM t".format(db.time_delta_query())

        It calculates fractional seconds between each row's ``datetime``
        and the first row's ``datetime``, then divides by *time_div* to
        produce the desired time scale.

        Args:
            time_div: Divisor applied to the raw elapsed seconds.  Use
                ``1`` for seconds, ``60`` for minutes, ``3600`` for
                hours, etc.
            column_name: Alias for the computed column in the result
                set.  When ``None``, an appropriate name is chosen
                automatically based on *time_div* (e.g.
                ``elapsed_hours``).

        Returns:
            A SQL expression string of the form
            ``"(expr - first_time) / time_div AS column_name"`` ready
            for interpolation into a ``SELECT``.

        Raises:
            Exception: If no default table name has been set on the
                instance (needed to look up the first timestamp).
        """
        if column_name is None:
            if time_div == 0.001:
                column_name = "elapsed_milliseconds"
            elif time_div == 1:
                column_name = "elapsed_seconds"
            elif time_div == 60:
                column_name = "elapsed_minutes"
            elif time_div == 3600:
                column_name = "elapsed_hours"
            elif time_div == 86400:
                column_name = "elapsed_days"
            elif time_div == 31536000:
                column_name = "elapsed_years"
            else:
                column_name = "elapsed_time"
        frac_s_str = "strftime('%s',datetime)+strftime('%f',datetime)-strftime('%S',datetime)"
        if self.table_name is None:
            raise Exception('table_name not specified')
        first_time = self.conn.execute(
            "SELECT {} FROM {} ORDER BY rowid ASC;".format(
                frac_s_str, self.table_name)).fetchone()[0]
        return "({}-{})/{} AS {}".format(frac_s_str,
                                         first_time, time_div, column_name)

    def filter_change(self, column_name_list, table_name=None,
                      first_row=False, preceding_row=False):
        """Identify row IDs where any monitored column changed value.

        Performs a self-join on consecutive ``rowid`` pairs and returns
        the ``rowid`` of every row where at least one of the specified
        columns differs from the preceding row.  The resulting tuple is
        designed to be interpolated into a ``WHERE rowid IN …`` clause
        for a follow-up query that fetches only the transition points.

        Args:
            column_name_list: An iterable of column-name strings to
                monitor for changes between consecutive rows.
            table_name: Table to scan.  Falls back to the instance
                default when ``None``.
            first_row: When ``True``, unconditionally include ``rowid``
                1 in the result so the initial state is captured.
            preceding_row: When ``True``, also include the ``rowid``
                immediately before each detected change, which is
                useful for plotting step transitions.

        Returns:
            A sorted tuple of integer ``rowid`` values where at least
            one monitored column changed.

        Raises:
            Exception: If *table_name* is ``None`` and no default table
                was set on the instance.
        """
        if table_name is None:
            table_name = self.table_name
            if table_name is None:
                raise Exception('table_name not specified')
        if first_row:
            first_row = (1,)
        else:
            first_row = tuple()
        sql_query = 'SELECT delay.rowid from {table_name} as orig JOIN {table_name} as delay ON orig.rowid = delay.rowid-1 WHERE '.format(
            table_name=table_name)
        for column_name in column_name_list:
            sql_query += 'orig.{column_name} IS NOT delay.{column_name} OR '.format(
                column_name=column_name)
        sql_query = sql_query[:-4]
        try:
            row_ids = list(zip(*self.conn.execute(sql_query)))[0]
        except IndexError:
            # no changes
            return first_row
        if preceding_row:
            preceding_row_ids = tuple(row - 1 for row in row_ids)
            return tuple(sorted(first_row + row_ids + preceding_row_ids))
        return tuple(sorted(first_row + row_ids))

    def optimize(self):
        """Defragment and analyze the database to reduce file size and improve query speed.

        Runs SQLite ``VACUUM`` (which rebuilds the entire database file,
        reclaiming unused pages) followed by ``ANALYZE`` (which updates
        index statistics used by the query planner).

        WARNING: ``VACUUM`` can take a very long time on large databases
        and requires up to 2× the current file size in free disk space.
        WARNING: ``VACUUM`` may reassign ``rowid`` values, which can
        invalidate any externally cached row identifiers.
        """
        self.conn.execute("VACUUM;")
        self.conn.execute("ANALYZE;")

    def expand_vector_data(self, csv_filename=None,
                           csv_append=False, csv_encoding='utf-8'):
        """Expand vector-valued columns to full row rank and return a record array.

        Instrument drivers for oscilloscopes, network analyzers, etc.
        often store multi-point waveforms as string-encoded lists in a
        single column.  This method parses those lists, replicates any
        scalar columns to match the vector length, and flattens the
        result so every data point has its own row.  The output is
        suitable for direct plotting or further NumPy analysis.

        Args:
            csv_filename: If not ``None``, write the expanded data to
                this file path in CSV format.
            csv_append: When ``True``, append to *csv_filename* instead
                of overwriting it.
            csv_encoding: Character encoding used when writing the CSV
                file.

        Returns:
            A ``numpy.recarray`` with one row per vector element, where
            scalar columns are broadcast to match the vector length.

        Raises:
            Exception: If vector columns within the same row have
                inconsistent lengths.
        """
        columns = []
        dtypes = []
        data_length = None
        column_names = self.get_column_names()
        for column in column_names:
            columns.append([])
            for i, row in enumerate(self):
                try:
                    if row[column].startswith(
                            '[') and row[column].endswith(']'):
                        column_data = [
                            float(x) for x in row[column].strip("[]").split(",")]
                        if data_length is None and len(column_data) > 1:
                            data_length = len(column_data)
                        elif len(column_data) != 1 and len(column_data) != data_length:
                            raise Exception('Inconsistent data length in vector expansion: {} and {}'.format(
                                len(columns[-1]), data_length))
                    else:
                        column_data = [row[column]]
                except AttributeError:
                    column_data = [row[column]]
                columns[-1].append(column_data)
        if data_length is None:
            print("WARNING: No vector data found.")
            data_length = 1
        for i, column in enumerate(columns):
            if len(column[0]) == 1:
                dtypes.append((column_names[i], type(column[0][0])))
            else:
                dtypes.append((column_names[i], float))
            for rowcount, rowcoldata in enumerate(column):
                if len(rowcoldata) == 1:
                    # expand scalar data to vector length
                    column[rowcount] = rowcoldata * data_length
        # flatten row data
        data = []
        for rowid in range(rowcount + 1):
            rowdata = []
            for columnid in range(i + 1):
                rowdata.append(columns[columnid][rowid])
            data.extend(list(zip(*rowdata)))
        # csv output
        if csv_filename is not None:
            csv_txt = ""
            for column in column_names:
                csv_txt += '{},'.format(column)
            csv_txt = '{}\n'.format(csv_txt[:-1])
            for row in data:
                for column in row:
                    csv_txt += '{},'.format(column)
                csv_txt = '{}\n'.format(csv_txt[:-1])
            with open(csv_filename, 'a' if csv_append else 'w') as f:
                f.write(csv_txt.encode(csv_encoding))
                f.close()
            print('Output written to {}'.format(csv_filename))
        array = numpy.array(data, dtype=dtypes)
        return array.view(numpy.recarray)
