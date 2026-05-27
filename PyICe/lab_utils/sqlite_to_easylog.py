"""Sqlite to easylog utility."""
from .sqlite_to_csv import sqlite_to_csv


class sqlite_to_easylog(sqlite_to_csv):
    """Export SQLite data in the CSV dialect consumed by EasyLog Graph.

    Extends ``sqlite_to_csv`` so that column headers carry parenthesized unit
    annotations, which is how EasyLog Graph
    (http://www.lascarelectronics.com/data-logger/easylogger-software.php)
    determines which trace belongs on which Y-axis. Use this when you want to
    interactively browse logged bench data with the free EasyLog viewer.
    """
    def __init__(self, chart_name, table_name, y1_axis_units='V',
                 y2_axis_units='A', database_file='data_log.sqlite'):
        """Configure the EasyLog export with chart title, table source, and axis units.

        Automatically inserts ``rowid`` (labelled with *chart_name*) and
        ``datetime`` columns, which EasyLog requires in fixed positions at
        the beginning of each row.

        Args:
            chart_name: Title shown at the top of the EasyLog graph; also
                used as the display name for the ``rowid`` column.
            table_name: Name of the SQLite table to query.
            y1_axis_units: Unit string for the left Y-axis (e.g. ``'V'``).
            y2_axis_units: Unit string for the right Y-axis (e.g. ``'A'``).
            database_file: Path to the SQLite database file.
        """
        self.y1_axis_units = y1_axis_units
        self.y2_axis_units = y2_axis_units
        sqlite_to_csv.__init__(self, table_name, database_file)
        sqlite_to_csv.add_column(
            self,
            query_name='rowid',
            display_name=chart_name)
        # the position of these fields is important
        sqlite_to_csv.add_column(
            self,
            query_name='datetime',
            display_name='Time')

    def add_comment(self, *args, **kwargs):
        """Raise an exception because EasyLog files do not support comment lines.

        Overrides the parent ``sqlite_to_csv.add_comment`` to prevent creation
        of files that EasyLog Graph cannot parse.

        Args:
            *args: Ignored; present only for interface compatibility.
            **kwargs: Ignored; present only for interface compatibility.

        Raises:
            Exception: Always raised—comment lines are not allowed in EasyLog files.
        """
        raise Exception(
            "Comment lines don't seem to be allowed in EasyLog files.")

    def add_column(self, query_name, second_y_axis=False,
                   display_name=None, format='', transform=None):
        """Register a data column and assign it to a Y-axis via unit annotation.

        The column header is automatically suffixed with the configured unit
        string in parentheses (e.g. ``"vout (V)"``), which is how EasyLog
        Graph decides whether a trace is plotted on the left or right Y-axis.

        Args:
            query_name: SQLite column name to select from the table.
            second_y_axis: If ``True``, place this trace on the right-side
                Y-axis (uses ``y2_axis_units``); otherwise use the left-side
                Y-axis (``y1_axis_units``).
            display_name: Column header label shown in the CSV. Defaults to
                *query_name* when ``None``.
            format: Python format-spec string controlling numeric display
                (e.g. ``'3.2f'``).
            transform: Optional callable applied to each cell value before
                writing.
        """
        if display_name is None:
            display_name = query_name
        # Data goes to first or second y-axis based on parenthesized units in
        # column heading
        display_name = "{} ({})".format(
            display_name, self.y2_axis_units if second_y_axis else self.y1_axis_units)
        sqlite_to_csv.add_column(
            self,
            query_name=query_name,
            display_name=display_name,
            format=format,
            transform=transform)

    def add_columns(self, column_list, second_y_axis=False, format=''):
        """Register multiple data columns on the same Y-axis in one call.

        Convenience wrapper around ``add_column``; each name in *column_list*
        is added with identical *second_y_axis* and *format* settings.

        Args:
            column_list: Sequence of SQLite column names to add.
            second_y_axis: If ``True``, assign all columns to the right-side
                Y-axis; otherwise the left-side.
            format: Python format-spec string controlling numeric display
                (e.g. ``'3.2f'``).
        """
        for column in column_list:
            self.add_column(
                query_name=column,
                second_y_axis=second_y_axis,
                format=format)
    # def _add_elapsed_time(self, *args, **kwargs):
        # raise Exception("Elapsed time not supported yet. Is it really needed?")

    def write(self, output_file, append=False):
        """Write the configured columns to an EasyLog-compatible CSV file.

        Call this after all desired columns have been added with
        ``add_column`` / ``add_columns``. The file is written with Windows
        ANSI encoding (``mbcs``) as expected by EasyLog Graph.

        Args:
            output_file: Destination file path for the CSV output.
            append: If ``True``, append rows to an existing file instead of
                overwriting it.
        """
        sqlite_to_csv.write(
            self,
            output_file=output_file,
            append=append,
            encoding='mbcs')  # windows ANSI codepage
