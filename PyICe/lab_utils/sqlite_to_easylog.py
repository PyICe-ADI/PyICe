"""Sqlite to easylog utility."""
from .sqlite_to_csv import sqlite_to_csv


class sqlite_to_easylog(sqlite_to_csv):
    """Wrapper to make specific format required by Easy Log Graph software.

    Formats data stored in an SQLite database so that it can be browsed interactively.
    Use EasyLogGraph (http://www.lascarelectronics.com/data-logger/easylogger-software.php) to visualize data.
    """
    def __init__(self, chart_name, table_name, y1_axis_units='V',
                 y2_axis_units='A', database_file='data_log.sqlite'):
        """Chart_name will appear at top of graph.

        table_name is the sqlite database table name
        y1_axis_units controls the left-side y-axis label
        y2_axis_units controls the right-side y-axis label
        database_file is the filename of the sqlite database

        Args:
            chart_name: Chart name.
            database_file: Database file.
            table_name: Database table name.
            y1_axis_units: Y1 axis units.
            y2_axis_units: Y2 axis units.
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
        """Add a comment.

        Args:
            **kwargs: Additional keyword arguments.
            *args: Additional positional arguments.

        Raises:
            Exception: On error condition.
        """
        raise Exception(
            "Comment lines don't seem to be allowed in EasyLog files.")

    def add_column(self, query_name, second_y_axis=False,
                   display_name=None, format='', transform=None):
        """Query name is the name of the sqlite column.

        second_y_axis is a boolean.  Setting to True places data on the right-side y-axis scale
        display_name, if not None, sets csv column header title differently from database column name
        format controls appearance of queried data. Ex: "3.2f"

        Args:
            display_name: Display name.
            format: Format name string.
            query_name: Query name.
            second_y_axis: Second y axis.
            transform: Transform.
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
        """Adds a list of sqlite column names at once.

        all columns will be placed on left-side y-axis scale unless second_y_axis is True
        format controls appearance of queried data. Ex: "3.2f"

        Args:
            column_list: Column list.
            format: Format name string.
            second_y_axis: Second y axis.
        """
        for column in column_list:
            self.add_column(
                query_name=column,
                second_y_axis=second_y_axis,
                format=format)
    # def _add_elapsed_time(self, *args, **kwargs):
        # raise Exception("Elapsed time not supported yet. Is it really needed?")

    def write(self, output_file, append=False):
        """Write queried data to output_file after column setup is complete.

        Args:
            append: Append.
            output_file: Output file.
        """
        sqlite_to_csv.write(
            self,
            output_file=output_file,
            append=append,
            encoding='mbcs')  # windows ANSI codepage
