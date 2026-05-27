"""Sqlite to csv utility."""
import sqlite3
from .csv_writer import csv_writer


class sqlite_to_csv(csv_writer):
    """Export selected columns from a SQLite database table to a CSV file.

    Queries a SQLite database at write-time and formats the results as CSV,
    making the data ready for interactive visualization in tools such as
    Live Graph (https://sourceforge.net/projects/live-graph/) or
    KST (kst-plot.kde.org). Column selection, transforms, formatting, and
    elapsed-time derivation are all configured before calling write().
    """
    def __init__(self, table_name, database_file='data_log.sqlite'):
        """Connect to a SQLite database and prepare to export a named table.

        Opens a persistent connection to the SQLite file and stores a cursor
        for use during column-discovery and write operations. The connection
        remains open until the instance is used as a context manager or the
        caller explicitly closes it.

        Args:
            table_name: Name of the database table whose rows will be
                exported. Passed verbatim into SQL queries, so it must
                match the table name exactly (case-sensitive on most
                platforms).
            database_file: Path to the SQLite database file. Defaults to
                ``'data_log.sqlite'`` in the current working directory.
        """
        csv_writer.__init__(self)
        self.table_name = table_name
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        """Support use as a context manager, returning this instance.

        Allows the database connection to be closed automatically via a
        ``with`` statement, preventing resource leaks even if an exception
        is raised inside the block.

        Returns:
            This ``sqlite_to_csv`` instance, ready for column configuration
            and writing.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the database connection when leaving the ``with`` block.

        Called automatically at the end of a ``with`` statement regardless
        of whether an exception occurred. Closes the SQLite connection but
        does not suppress any exceptions raised inside the block.

        Args:
            exc_type: Exception class, or ``None`` if no exception was raised.
            exc_val: Exception instance, or ``None`` if no exception was raised.
            exc_tb: Traceback object, or ``None`` if no exception was raised.

        Returns:
            ``None``, which allows any exception to propagate normally.
        """
        self.conn.close()
        return None

    def add_timestamps(self):
        """Schedule the ``rowid`` and ``datetime`` columns for CSV output.

        Convenience wrapper that queues both the SQLite row identifier and
        the human-readable timestamp column so they appear in the exported
        CSV. Call this before write() to include time-axis data needed by
        most visualization tools.
        """
        self.add_column('rowid')
        self.add_column('datetime')

    def _add_elapsed_time(self, display_name, format, transform):
        self.cursor.execute(
            'SELECT strftime("%s",datetime) FROM {} LIMIT 1'.format(
                self.table_name))
        self.add_column(
            query_name='strftime("%s",datetime) - {}'.format(
                self.cursor.fetchone()[0]),
            display_name=display_name,
            format=format,
            transform=transform)

    def write(self, output_file, append=False, encoding='utf-8'):
        """Query the database and write all configured columns to a CSV file.

        Builds a single SELECT statement from every column added via
        add_column() (or add_timestamps()), executes it against the configured
        table, and streams the formatted rows to ``output_file``. A header row
        using each column's display name is written first. Call this method
        after all column selections and transforms have been registered.

        Args:
            output_file: Path to the destination CSV file. The file is created
                if it does not exist; existing content is overwritten unless
                ``append`` is ``True``.
            append: When ``True``, rows are appended to an existing file
                instead of replacing it. No additional header is written in
                append mode, so the caller is responsible for header
                consistency. Defaults to ``False``.
            encoding: Character encoding used when writing the file, passed
                directly to Python's ``str.encode()``. Defaults to
                ``'utf-8'``.
        """
        query_txt = ''
        for column in self.columns:
            query_txt += "{},".format(column.query_name)
        query_txt = query_txt[:-1]
        with open(output_file, 'a' if append else 'w') as f:
            f.write(self._format_header().encode(encoding))
            for row in self.cursor.execute(
                    'SELECT {} FROM {}'.format(query_txt, self.table_name)):
                row_txt = ''
                for cidx, column in enumerate(row):
                    row_txt += self._format_output(column, self.columns[cidx])
                f.write((row_txt[:-1] + '\n').encode(encoding))
            f.close()
        print('Output written to {}'.format(output_file))
