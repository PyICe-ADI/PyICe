"""Sqlite to xlsx utility."""
import os
import atexit
import datetime
import sqlite3
import numpy

numpy_missing = False


class sqlite_to_xlsx(object):
    """Export SQLite tables and views to a formatted Excel ``.xlsx`` workbook.

    Creates a workbook with autofilters, sparklines, alternating-row shading,
    frozen header panes, and named ranges for each column. Use as a context
    manager or call ``close`` explicitly when finished writing.
    """

    def __init__(self, output_file):
        """Create the Excel workbook and set up default cell formats.

        Opens *output_file* in constant-memory mode (suitable for very large
        tables) and disables automatic formula/URL/number conversion so that
        raw SQLite values are preserved exactly.

        Args:
            output_file: Destination path for the ``.xlsx`` file.
        """
        import xlsxwriter
        self.rowcol_to_cell = xlsxwriter.utility.xl_rowcol_to_cell
        self.output_file = output_file
        self._workbook = xlsxwriter.Workbook(self.output_file, {'constant_memory': True,
                                                                'strings_to_formulas': False,
                                                                'strings_to_urls': False,
                                                                'strings_to_numbers': False,
                                                                }
                                             )
        self.formats = {'default': self._workbook.add_format({'font_name': 'Courier New', 'font_size': 9}),
                        'date_time': self._workbook.add_format({'num_format': 'yyyy/mm/dd hh:mm:ss.000', 'font_name': 'Courier New', 'font_size': 9}),
                        'delta_time': self._workbook.add_format({'num_format': 'hh:mm:ss.000', 'font_name': 'Courier New', 'font_size': 9}),
                        'row_shade': self._workbook.add_format({'bg_color': '#D0FFD0'}),
                        }
        # Add generation information?
        # self._workbook.set_custom_property(name, value[, property_type])
        atexit.register(self.close)

    def __enter__(self):
        """Return self for use as a context manager."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the workbook when leaving the ``with`` block.

        Args:
            exc_type: Exception type, or ``None`` if no exception occurred.
            exc_value: Exception instance, or ``None``.
            traceback: Traceback object, or ``None``.

        Returns:
            ``None``—exceptions are never suppressed.
        """
        self.close()
        return None

    @property
    def workbook(self):
        """Expose the underlying ``xlsxwriter.Workbook`` for advanced customisation.

        Use this to add extra chartsheets, custom formats, or properties that
        ``sqlite_to_xlsx`` does not wrap directly.
        See: http://xlsxwriter.readthedocs.io/workbook.html

        Returns:
            The ``xlsxwriter.Workbook`` instance backing this export.
        """
        return self._workbook

    def add_worksheet(self, sqlite_data_obj, elapsed_time_columns=False):
        """Create a worksheet from one ``sqlite_data`` instance and populate it with all rows.

        The worksheet includes auto-sized columns, autofilters, sparklines,
        named ranges, alternating-row shading, and frozen header panes. If the
        table contains a ``datetime`` column and *elapsed_time_columns* is
        ``True``, two extra columns (``elapsed_time`` and ``elapsed_seconds``)
        are inserted immediately after ``datetime``.
        See: http://xlsxwriter.readthedocs.io/worksheet.html

        Args:
            sqlite_data_obj: A ``lab_utils.sqlite_data`` instance pointing at
                the table, view, or query to export.
            elapsed_time_columns: If ``True``, add computed elapsed-time
                columns alongside the ``datetime`` column.

        Returns:
            The newly created ``xlsxwriter.Worksheet``, or ``None`` if the
            SQLite table contained no rows.

        Raises:
            Exception: If the workbook has already been closed.
        """
        if self._workbook is None:
            raise Exception(
                'Attempted to add worksheet after closing workbook')
        worksheet_name = sqlite_data_obj.table_name[:31]
        # ' [ ] : * ? / \ ' Characters are not allowed, but should be similarly excluded from SQLite table names.
        if len(sqlite_data_obj.table_name) > 31:
            # Max Excel sheet name length
            print(
                'Warning: SQLite table name "{}" truncated to "{}" to comply with Excel maximum worksheet name length requirements.'.format(
                    sqlite_data_obj.table_name,
                    worksheet_name))
        columns = sqlite_data_obj.get_column_names()
        if columns is None:
            print(
                'Warning: SQLite table "{}" contains no rows. Omitting from Excel output'.format(
                    sqlite_data_obj.table_name))
            return None
        try:
            worksheet = self._workbook.add_worksheet(worksheet_name)
        except Exception as e:
            print(
                "WARNING: Problem adding worksheet named: {}".format(worksheet_name))
            print('\t{}{}'.format(e, type(e)))
            print(
                "\tAdding {} table data to unnamed sheet instead.".format(
                    sqlite_data_obj.table_name))
            worksheet = self._workbook.add_worksheet()
        column_width_pad = 1.0
        filter_button_width = 3
        row_idx = 0
        col_idx = 0
        datetime_col = None
        # different from columns if elapsed time columns added.
        column_names = []
        for column in columns:
            # save column names to create named ranges after rowcount is
            # determined
            column_names.append(column)
            worksheet.write(row_idx, col_idx, column)
            worksheet.set_column(
                col_idx,
                col_idx,
                len(column) *
                column_width_pad +
                filter_button_width,
                self.formats['default'])
            if column == 'datetime':
                datetime_col = col_idx
                if elapsed_time_columns:
                    worksheet.write(row_idx, col_idx + 1, 'elapsed_time')
                    worksheet.set_column(
                        col_idx +
                        1,
                        col_idx +
                        1,
                        len('elapsed_time') *
                        column_width_pad +
                        filter_button_width,
                        self.formats['default'])
                    column_names.append('elapsed_time')
                    worksheet.write(row_idx, col_idx + 2, 'elapsed_seconds')
                    worksheet.set_column(
                        col_idx +
                        2,
                        col_idx +
                        2,
                        len('elapsed_seconds') *
                        column_width_pad +
                        filter_button_width,
                        self.formats['default'])
                    column_names.append('elapsed_seconds')
                    col_idx += 2
            col_idx += 1
        column_count = col_idx - 1
        row_idx += 1
        col_idx = 0
        start_time = None
        for row in sqlite_data_obj:
            for column in row:
                if col_idx == datetime_col:
                    if not isinstance(column, datetime.datetime):
                        # print "WARNING: datetime column affinity not set
                        # correctly in sqlite table {}. Attempting conversion
                        # to datetime
                        # object.".format(sqlite_data_obj.table_name)
                        column = sqlite_data_obj.convert_timestring(column)
                    # Excel can't deal with timezone-aware datetimes. Output
                    # Zulu time.
                    worksheet.write_datetime(
                        row_idx, col_idx, column.replace(
                            tzinfo=None), self.formats['date_time'])
                    # Something has changedin xlsx lib. col_sizes[idx] now
                    # returns list [size,bool].
                    worksheet.set_column(col_idx, col_idx, max(len(
                        self.formats['date_time'].num_format) * column_width_pad, worksheet.col_sizes[col_idx][0]))
                else:
                    if isinstance(column, list) or isinstance(column, dict) or (
                            not numpy_missing and isinstance(column, numpy.ndarray)):
                        # >>> type(foo)
                        # <class 'numpy.ndarray'>
                        # >>> str(foo)
                        # '[1 2 3 4 5]'
                        # >>> str(list(foo))
                        # '[1, 2, 3, 4, 5]'
                        column = str(column)
                    worksheet.write(row_idx, col_idx, column)
                    try:
                        worksheet.set_column(
                            col_idx, col_idx, max(
                                len(column) * column_width_pad, worksheet.col_sizes[col_idx][0]))
                    except TypeError:
                        pass  # numbers doesn't have length
                if start_time is None and col_idx == datetime_col:
                    start_time = column
                if elapsed_time_columns and col_idx == datetime_col:
                    worksheet.write_datetime(
                        row_idx,
                        col_idx + 1,
                        column - start_time,
                        self.formats['delta_time'])  # elapsed_time
                    worksheet.set_column(col_idx +
                                         1, col_idx +
                                         1, max(len(self.formats['delta_time'].num_format) *
                                                column_width_pad, worksheet.col_sizes[col_idx +
                                                                                      1][0]))
                    worksheet.write(
                        row_idx,
                        col_idx + 2,
                        (column - start_time).total_seconds())  # elapsed_seconds
                    col_idx += 2
                col_idx += 1
            row_idx += 1
            col_idx = 0
        # Add named range for each column
        for col_idx, column in enumerate(column_names):
            self._workbook.define_name(
                '{}!{}'.format(
                    worksheet_name, column), '={}!{}:{}'.format(
                    worksheet_name, self.rowcol_to_cell(
                        1, col_idx, True, True), self.rowcol_to_cell(
                        row_idx - 1, col_idx, True, True)))
        # Add sparklines
        for col_idx in range(len(column_names)):
            worksheet.add_sparkline(
                row_idx, col_idx, {
                    'range': '{}:{}'.format(
                        self.rowcol_to_cell(
                            1, col_idx, True, True), self.rowcol_to_cell(
                            row_idx - 1, col_idx, True, True)), 'axis': True})
        # Add autofilters
        worksheet.autofilter(0, 0, row_idx - 1, column_count)
        # Add white/green alternating row colors
        worksheet.conditional_format(1, 0, row_idx - 1, column_count, {'type': 'formula',
                                                                       'criteria': '=MOD(SUBTOTAL(3,$A$1:$A2),2)=0',
                                                                       'format': self.formats['row_shade']}
                                     )
        # Add PyICe/Python logos
        icon_path = os.path.join(os.path.dirname(__file__), "tssop.png")
        worksheet.insert_image(row_idx + 2, 2, icon_path, {'y_offset': 20,
                                                           'x_scale': 0.35,
                                                           'y_scale': 0.35,
                                                           })
        try:
            import io
            import urllib.request
            import urllib.error
            import urllib.parse
            url = 'https://www.python.org/static/community_logos/python-powered-h-140x182.png'
            image_data = io.BytesIO(urllib.request.urlopen(url).read())
            worksheet.insert_image(row_idx + 2, 4, url, {'image_data': image_data,
                                                         'x_scale': 0.5,
                                                         'y_scale': 0.5,
                                                         })
        except Exception:
            print("INFO: Python logo insertion failed.")
            # print e
        # Keep column header line at top while scrolling
        worksheet.freeze_panes(1, 0)
        # Add column headers to the top of each printed page
        worksheet.repeat_rows(0)
        if column_names[0] == 'rowid':
            # Add rowid to the left of each printed page
            worksheet.repeat_columns(0)
            if column_names[1] == 'datetime':
                # Keep rowid, datetime at left while scrolling, preserving
                # frozen first row
                worksheet.freeze_panes(1, 2)
            else:
                # Keep rowid at left while scrolling, preserving frozen first
                # row
                worksheet.freeze_panes(1, 1)
        # Lock worksheet to prevent inadvertent data corruption. Unlock with
        # "Review -> Unprotect Sheet". No password required.
        worksheet.protect('', {'sort': True,
                               'autofilter': True,
                               'format_cells': True,
                               'format_columns': True,
                               'format_rows': True,
                               })
        return worksheet

    def add_database(self, db_file_name='data_log.sqlite',
                     elapsed_time_columns=False):
        """Import every table and view from an SQLite database, one worksheet per table.

        Iterates over ``sqlite_master`` to discover all tables and views, then
        calls ``add_worksheet`` for each. Empty tables are silently skipped.
        See: http://xlsxwriter.readthedocs.io/worksheet.html

        Args:
            db_file_name: Path to the SQLite database file.
            elapsed_time_columns: If ``True``, add elapsed-time columns next
                to each ``datetime`` column (see ``add_worksheet``).

        Returns:
            A ``dict`` mapping worksheet names (str) to their
            ``xlsxwriter.Worksheet`` instances for all non-empty tables.
        """
        from .sqlite_data import sqlite_data  # local import to avoid circular dependency
        conn = sqlite3.connect(db_file_name)
        worksheets = {}
        for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type=='table' OR type=='view'"):
            print("Inserting worksheet: {}".format(row[0]))
            ws = self.add_worksheet(
                sqlite_data_obj=sqlite_data(
                    table_name=row[0],
                    database_file=db_file_name),
                elapsed_time_columns=elapsed_time_columns)
            if ws is not None:
                worksheets[ws.get_name()] = ws
        return worksheets

    def add_xy_chart(self, subtype='straight_with_markers'):
        """Create an XY (scatter) chart object in the workbook.

        The returned chart must still be placed into a worksheet
        (``worksheet.insert_chart``) or a chartsheet (``add_chartsheet``)
        before it will be visible. Data series, titles, and axis labels must
        also be configured manually via the chart's own methods.

        Available *subtype* values:
            ``'straight_with_markers'``, ``'straight'``,
            ``'smooth_with_markers'``, ``'smooth'``

        See: http://xlsxwriter.readthedocs.io/chart.html

        Args:
            subtype: Line style for the scatter chart (default:
                ``'straight_with_markers'``).

        Returns:
            A new ``xlsxwriter.Chart`` instance of type ``'scatter'``.
        """
        return self._workbook.add_chart(
            {'type': 'scatter', 'subtype': subtype})

    def add_chartsheet(self, name, chart):
        """Add a dedicated chartsheet displaying a single chart.

        A chartsheet is a full-tab chart (no cells). Use ``add_xy_chart`` to
        create the chart object first, configure its series and axes, then
        pass it here.

        Args:
            name: Tab name for the new chartsheet (max 31 characters).
            chart: An ``xlsxwriter.Chart`` instance (e.g. from
                ``add_xy_chart``).

        Returns:
            The newly created ``xlsxwriter.Chartsheet`` instance.
        """
        chartsheet = self._workbook.add_chartsheet(name)
        chartsheet.set_chart(chart)
        return chartsheet

    def close(self):
        """Close Excel workbook and release file lock. No further writing is possible after closing."""
        if self._workbook is not None:
            self._workbook.close()
            self._workbook = None
            print('Output written to {}'.format(self.output_file))
