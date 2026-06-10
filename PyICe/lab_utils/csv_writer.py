"""Csv writer utility.

>>> from PyICe.lab_utils.csv_writer import csv_writer

"""
import collections


class csv_writer(object):
    """Base class providing shared CSV formatting logic for higher-level interfaces.

    Manages a list of column definitions (each carrying a query name, display
    name, optional value transform, and printf-style format string) and an
    optional list of header comment lines.  Subclasses such as csv_logger
    (live instrument logging) and sqlite_to_csv (SQLite export) inherit this
    class to get consistent column setup, header generation, and RFC-4180
    compliant data escaping without duplicating that logic.

    Subclasses are expected to override ``_add_elapsed_time`` to supply a
    time source appropriate for their context.

    >>> from PyICe.lab_utils.csv_writer import csv_writer
    >>> csv_writer is not None
    True

    """

    def __init__(self):
        """Set up an empty column list and comment buffer.

        Initialises the namedtuple factory used to store per-column
        configuration (query name, display name, transform callable, format
        string, and optional query function), the identity no-op transform,
        and the mutable ``columns`` and ``comments`` lists that accumulate
        state before any output is written.

        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> csv_writer is not None
        True

        """
        self.column_data_t = collections.namedtuple(
            'column_setup', [
                'query_name', 'display_name', 'transform', 'format', 'query_function'])
        self.no_transform = lambda x: x
        self.columns = []
        self.comments = []

    def _format_header(self):
        header_txt = ''
        for comment in self.comments:
            header_txt += comment + '\n'
        for column in self.columns:
            header_txt += "{},".format(column.display_name)
        return header_txt[:-1] + '\n'

    def _format_output(self, data, column_setup_tuple):
        """Format a single cell value according to its column's rules and return it as a CSV token.

        Called once per column for every row that is written.  The method
        applies, in order: an optional override from ``query_function`` (which
        replaces ``data`` entirely when present), the column's ``transform``
        callable, and then the column's ``format`` string.  After stringification
        the value is made RFC-4180 safe: embedded double-quotes are doubled, and
        fields containing commas are wrapped in double-quotes.  A trailing comma
        delimiter is appended so that the caller can concatenate tokens directly.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, '_format_output')
        True

        Args:
            data: Raw value fetched from the data source for this column.
                Ignored when ``column_setup_tuple.query_function`` is not None.
            column_setup_tuple: A ``column_data_t`` namedtuple describing the
                column, containing ``query_function``, ``transform``, and
                ``format`` fields used to process ``data``.

        Returns:
            A CSV-escaped string representation of the cell value with a
            trailing comma delimiter (e.g. ``'3.14,'`` or ``'"hello, world",'``).
        """
        if column_setup_tuple.query_function is not None:
            data = column_setup_tuple.query_function()
        data = column_setup_tuple.transform(data)
        # stringify data
        data = '{}'.format(column_setup_tuple.format).format(data)
        # escape rules:
        if '"' in data:
            # doubled double quotes escape all double quotes
            data = data.replace('"', '""')
        if ',' in data:
            # double quotes enclose all fields containing commas
            data = '"{}"'.format(data)
        return '{},'.format(data)

    def add_comment(self, comment_str, comment_character='#'):
        """Append a prefixed comment line to the file header.

        Call this before writing any data rows to embed metadata (test
        conditions, timestamps, instrument serial numbers, etc.) at the top of
        the output file.  Multiple calls accumulate lines in the order they are
        added.  Live Graph interprets ``'@'`` as a description line and ``'#'``
        as a comment line; neither character affects numeric data parsing.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_comment')
        True

        Args:
            comment_str: Text body of the comment, without the leading prefix
                character.
            comment_character: Single character prepended to ``comment_str``
                to form the comment line.  Defaults to ``'#'``, which Live
                Graph treats as a comment.  Use ``'@'`` for a Live Graph
                description line.
        """
        self.comments.append('{}{}'.format(comment_character, comment_str))

    def add_elapsed_seconds(self, display_name='elapsed_seconds', format=''):
        """Add a column that reports elapsed time in seconds since the first data row.

        Delegates to ``_add_elapsed_time`` with an identity transform so the
        raw elapsed-seconds value is written directly.  Use this when
        sub-minute resolution is important or when the downstream tool expects
        SI base units.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_elapsed_seconds')
        True

        Args:
            display_name: Column header written to the CSV file.
                Defaults to ``'elapsed_seconds'``.
            format: Python format specification (e.g. ``'.3f'``) applied to
                the numeric value before it is written.  An empty string uses
                the default ``str()`` representation.
        """
        self._add_elapsed_time(
            display_name=display_name,
            format=format,
            transform=self.no_transform)

    def add_elapsed_minutes(self, display_name='elapsed_minutes', format=''):
        """Add a column that reports elapsed time in minutes since the first data row.

        Delegates to ``_add_elapsed_time`` with a divide-by-60 transform.
        Convenient for medium-duration tests (minutes to a few hours) where
        per-second granularity is unnecessary.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_elapsed_minutes')
        True

        Args:
            display_name: Column header written to the CSV file.
                Defaults to ``'elapsed_minutes'``.
            format: Python format specification (e.g. ``'.2f'``) applied to
                the numeric value before it is written.  An empty string uses
                the default ``str()`` representation.
        """
        self._add_elapsed_time(
            display_name=display_name,
            format=format,
            transform=lambda x: x / 60.0)

    def add_elapsed_hours(self, display_name='elapsed_hours', format=''):
        """Add a column that reports elapsed time in hours since the first data row.

        Delegates to ``_add_elapsed_time`` with a divide-by-3600 transform.
        Well-suited for long-running reliability or burn-in tests where a
        fractional-hour axis is more readable than a large second count.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_elapsed_hours')
        True

        Args:
            display_name: Column header written to the CSV file.
                Defaults to ``'elapsed_hours'``.
            format: Python format specification (e.g. ``'.2f'``) applied to
                the numeric value before it is written.  An empty string uses
                the default ``str()`` representation.
        """
        self._add_elapsed_time(
            display_name=display_name,
            format=format,
            transform=lambda x: x / 3600.0)

    def add_elapsed_days(self, display_name='elapsed_days', format=''):
        """Add a column that reports elapsed time in days since the first data row.

        Delegates to ``_add_elapsed_time`` with a divide-by-86400 transform.
        Use for multi-day soak or life-test logs where fractional days are the
        most natural unit for both display and downstream analysis.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_elapsed_days')
        True

        Args:
            display_name: Column header written to the CSV file.
                Defaults to ``'elapsed_days'``.
            format: Python format specification (e.g. ``'.3f'``) applied to
                the numeric value before it is written.  An empty string uses
                the default ``str()`` representation.
        """
        self._add_elapsed_time(
            display_name=display_name,
            format=format,
            transform=lambda x: x / 86400.0)

    def _add_elapsed_time(self, *args, **kwargs):
        raise NotImplementedError('Elapsed time not implemented')

    def add_column(self, query_name, display_name=None,
                   format='', transform=None, query_function=None):
        """Add a single, fully-configurable column to the output file.

        Offers the full set of customisation options for one column.  Prefer
        this over ``add_columns`` when you need per-column transforms, format
        strings, or a Python-side data source (``query_function``).  The column
        is appended to ``self.columns`` in the call order, which determines the
        left-to-right order in the CSV output.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_column')
        True

        Args:
            query_name: Name used to look up this column's value in the
                external data source (e.g. a channel or SQLite column name).
                Also used as ``display_name`` when ``display_name`` is omitted.
            display_name: Column header written to the CSV file.  Defaults to
                ``query_name`` when not provided.
            format: Python format specification inserted into ``'{:...}'.format(value)``
                (e.g. ``'.2f'`` for two decimal places, ``'d'`` for integer).
                An empty string produces the default ``str()`` representation.
            transform: Single-argument callable applied to the raw queried value
                before formatting (e.g. ``lambda v: v * 1000`` to convert V to mV).
                Defaults to an identity function when not provided.
            query_function: Zero-argument callable whose return value is used
                as the column data instead of the external data source (e.g.
                ``time.time`` to embed a live timestamp).  When provided,
                ``query_name`` is only used for the column header fallback.
        """
        if display_name is None:
            display_name = query_name
        format = format = '{{:{}}}'.format(format)
        if transform is None:
            transform = self.no_transform
        self.columns.append(
            self.column_data_t(
                display_name=display_name,
                query_name=query_name,
                transform=transform,
                format=format,
                query_function=query_function))

    def add_columns(self, column_list, format=''):
        """Add multiple columns at once using a shared format string.

        Iterates over ``column_list`` and calls ``add_column`` for each entry
        using its name as both the query name and the display name.  All
        columns share the same ``format`` string and receive no transform or
        ``query_function``.  Use ``add_column`` directly when individual
        columns need different formats, transforms, or Python-side data sources.


        >>> from PyICe.lab_utils.csv_writer import csv_writer
        >>> hasattr(csv_writer, 'add_columns')
        True

        Args:
            column_list: Iterable of query/display name strings, one per
                column to add (e.g. a list of SQLite column names or
                instrument channel names).
            format: Python format specification applied uniformly to every
                column in ``column_list`` (e.g. ``'.4f'`` for four decimal
                places).  An empty string uses the default ``str()``
                representation.
        """
        for column in column_list:
            self.add_column(column, format=format)
