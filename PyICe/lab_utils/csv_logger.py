"""Csv logger utility."""
import datetime
import atexit
from .csv_writer import csv_writer


class csv_logger(csv_writer):
    """Stream instrument readings to a CSV file row-by-row as measurements are collected.

    Inherits column management from csv_writer and adds live file I/O so that
    each call to write() immediately flushes a new data row to disk. This makes
    the output file readable by external tools such as Live Graph
    (https://sourceforge.net/projects/live-graph/) while the test is still
    running, enabling real-time "marching waves" visualization. Columns are
    registered from lab_core channel objects before the first write; the CSV
    header is emitted automatically on the first write() call.

    Use as a context manager or register it with a lab_core.logger instance via
    register_logger_callback() for fully automatic operation.
    """

    def __init__(self, output_file, encoding='utf-8'):
        """Open the output CSV file and prepare the logger for use.

        Creates the output file immediately in binary-write mode so that rows
        can be flushed incrementally during a test run. Registers __del__ with
        atexit as a safety net to close the file if the caller does not use the
        context manager protocol or call unregister_logger_callback().

        Args:
            output_file: Path to the CSV file to create or overwrite.
            encoding: Text encoding used when writing the file. Defaults to
                ``'utf-8'``.
        """
        csv_writer.__init__(self)
        self.output_file = output_file
        self.encoding = encoding
        self.header_written = False
        self.f = open(self.output_file, 'wb')
        atexit.register(self.__del__)
        self._row_id = -1

    def __enter__(self):
        """Support use of csv_logger as a context manager.

        Enables the ``with csv_logger(...) as log:`` pattern, which guarantees
        that the file handle is closed via __exit__ even if an exception occurs
        during the test run.

        Returns:
            This csv_logger instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the CSV file when leaving a ``with`` block.

        Called automatically at the end of a ``with`` statement, whether the
        block exits normally or raises an exception. Does not suppress
        exceptions; any exception raised inside the ``with`` block will
        propagate normally after the file is closed.

        Args:
            exc_type: Exception class, or ``None`` if no exception occurred.
            exc_val: Exception instance, or ``None`` if no exception occurred.
            exc_tb: Traceback object, or ``None`` if no exception occurred.

        Returns:
            ``None``, so any active exception is re-raised by the runtime.
        """
        print("__exit__ closing CSV filehandle: {}".format(self.output_file))
        self.f.close()
        return None

    def __del__(self):
        """Close the CSV file when the object is garbage-collected.

        Acts as a last-resort safety net via atexit registration. Prefer the
        context manager or unregister_logger_callback() for deterministic
        cleanup, since finalizer invocation order is not guaranteed.
        """
        print("__del__ closing CSV filehandle: {}".format(self.output_file))
        self.f.close()

    def _row_count(self):
        """Return a monotonically increasing row index, starting at zero.

        Used as the query_function for the ``rowid`` column added by
        add_timestamps(). Each call increments the internal counter by one,
        so successive write() calls receive consecutive integer identifiers.

        Returns:
            Integer row index for the current row, beginning at 0 on the first
            call.
        """
        self._row_id += 1
        return self._row_id

    def add_timestamps(self):
        """Prepend auto-generated ``rowid`` and ``datetime`` columns to the output.

        Inserts two bookkeeping columns before any channel data columns. The
        ``rowid`` column holds a zero-based integer that increments with every
        row, making it easy to detect missed samples. The ``datetime`` column
        records the wall-clock time of each write() call in ISO-8601 format
        (``YYYY-MM-DDTHH:MM:SS.ffffffZ``), which Live Graph and most CSV
        tools can parse directly.

        Call this method before the first write(), typically right before
        add_columns(). register_logger_callback() calls it automatically if
        no columns have been configured yet.
        """
        csv_writer.add_column(
            self,
            query_name=None,
            display_name='rowid',
            query_function=self._row_count)
        csv_writer.add_column(
            self,
            query_name=None,
            display_name='datetime',
            query_function=datetime.datetime.now,
            transform=lambda t: datetime.datetime.strftime(
                t,
                "%Y-%m-%dT%H:%M:%S.%fZ"))  # 2015-10-20 21:54:17

    def _add_elapsed_time(self, display_name, format, transform):
        csv_writer.add_column(
            self,
            query_name=None,
            display_name=display_name,
            format=format,
            query_function=datetime.datetime.now,
            transform=lambda t: transform(
                (t - self._time_zero).total_seconds()))

    def add_column(self, channel):
        """Register a single lab_core channel as a data column in the CSV output.

        Extracts the channel name via channel.get_name() and passes it to the
        underlying csv_writer as the column's query key. Raw numeric precision
        is preserved by intentionally omitting a display transform. Must be
        called before the first write(); the header row is written on the
        initial write() call and the column layout is frozen at that point.

        Args:
            channel: A lab_core channel object whose get_name() method returns
                the key used to look up values in the channel_data dictionary
                passed to write().

        Raises:
            Exception: If called after the CSV header has already been written,
                because columns cannot be added once the schema is fixed.
        """
        if self.header_written:
            raise Exception(
                "Can't add column {} after header has been written.".format(
                    channel.get_name()))
        # csv_writer.add_column(self, query_name=channel.get_name(),
        # transform=channel.format_display) #this loses precision!
        csv_writer.add_column(
            self,
            query_name=channel.get_name(),
            transform=None)

    def add_columns(self, channel_list):
        """Register multiple lab_core channels as data columns in the CSV output.

        Iterates over channel_list and calls add_column() for each entry,
        preserving the list order as the column order in the file. Use this as
        a convenience shortcut when all channels share the same default
        formatting; call add_column() individually when per-column control is
        needed. Must be called before the first write().

        Args:
            channel_list: An iterable of lab_core channel objects to add, in
                the order they should appear in the CSV output.

        Raises:
            Exception: If called after the CSV header has already been written,
                because columns cannot be added once the schema is fixed.
        """
        if self.header_written:
            raise Exception("Can't add columns after header has been written.")
        for channel in channel_list:
            self.add_column(channel)

    def write(self, channel_data):
        """Encode one row of channel readings and flush it to the CSV file.

        On the very first call, emits the header row (column names) and records
        the wall-clock start time used by any elapsed-time columns. On every
        call, iterates over registered columns in order: columns backed by a
        query_function (e.g. rowid, datetime) are invoked directly; columns
        backed by a query_name are looked up in channel_data; columns whose key
        is absent from channel_data produce an empty field rather than raising
        an error. Each row is immediately flushed to disk so that live-plotting
        tools see new data without waiting for the file to be closed.

        This method is designed to be passed as a callback to
        lab_core.logger.add_log_callback() so it is invoked automatically
        after every measurement sweep.

        Args:
            channel_data: Dictionary mapping channel name strings to their
                current measured values, as produced by a lab_core logger or
                channel group read.

        Returns:
            The channel_data dictionary passed in, unchanged, so the caller
            can chain additional processing on the same data.
        """
        # migrate to csv.DictWriter ?
        # https://docs.python.org/3/library/csv.html
        if not self.header_written:
            self.f.write(self._format_header().encode(self.encoding))
            self._time_zero = datetime.datetime.now()  # for elapsed time computation
            self.header_written = True
        row_txt = ''
        for column in self.columns:
            if column.query_function is not None:
                row_txt += self._format_output(None, column)
            elif column.query_name in channel_data:
                row_txt += self._format_output(
                    channel_data[column.query_name], column)
            else:
                # allow missing column data???
                row_txt += ','
                # raise Exception('Data for column: {} not provided to write() method.'.format(column.display_name))
        self.f.write((row_txt[:-1] + '\n').encode(self.encoding))
        # does flushing slow down operation too much? Make optional?
        self.f.flush()  # just in case line buffering doesn't work
        return channel_data

    def register_logger_callback(self, logger):
        """Attach this csv_logger to a lab_core.logger for automatic per-sweep CSV writes.

        If no columns have been configured yet, automatically calls
        add_timestamps() followed by add_columns(logger) to mirror all
        channels registered with the logger. Then registers write() as a
        post-sweep callback so that every time the logger completes a
        measurement sweep, a new CSV row is written and flushed immediately.
        This is the primary integration point for live "marching waves"
        visualization.

        Args:
            logger: A lab_core.logger instance whose channel list will be used
                to auto-configure columns (when none exist yet) and whose
                add_log_callback() mechanism will invoke write() after each
                sweep.
        """
        if not len(self.columns):
            self.add_timestamps()
            self.add_columns(logger)
        logger.add_log_callback(self.write)

    def unregister_logger_callback(self, logger, close_file=True):
        """Detach this csv_logger from a lab_core.logger and optionally close the file.

        Removes write() from the logger's post-sweep callback list so that
        subsequent sweeps no longer produce CSV rows. Use this when a logger
        instance is being reused across multiple tests and a fresh output file
        is needed for each one: detach the old csv_logger, create a new one,
        and register it with register_logger_callback().

        Args:
            logger: The lab_core.logger instance from which to remove the
                write() callback.
            close_file: If ``True`` (the default), close the underlying file
                handle immediately after deregistering. Pass ``False`` to keep
                the file open for additional writes before closing manually.
        """
        logger.remove_log_callback(self.write)
        if close_file:
            self.f.close()
