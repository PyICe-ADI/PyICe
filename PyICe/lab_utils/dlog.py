"""Dlog utility."""
import time


class dlog(object):
    """Write timestamped data lines to a log file while echoing to the console."""
    def __init__(self, filename="output.txt"):
        """Open a log file and write a date/time header.

        Uses ``time.perf_counter()`` as the time base for per-line timestamps.

        Args:
            filename: Path to the output file (defaults to ``"output.txt"``).
        """
        self.errcnt = 0
        self.f = open(filename, 'w')
        # note the time.clock function won't work well for linux...
        # this is written for windows
        self.timezero = time.perf_counter()
        # time/date stamp header
        self.log_notime(time.strftime("%a, %d %b %Y %H:%M:%S"))

    def __enter__(self):
        """Enter the context manager, returning this instance for use in a ``with`` block.

        Returns:
            This :class:`dlog` instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the log file when exiting a ``with`` block.

        Args:
            exc_type: Type of the exception raised inside the block, or ``None``.
            exc_val: Exception instance, or ``None``.
            exc_tb: Traceback object, or ``None``.

        Returns:
            ``None`` (does not suppress exceptions).
        """
        self.f.close()
        return None

    def log_notime(self, data):
        """Write *data* to the log file and console without a timestamp prefix.

        Args:
            data: Value to log (converted to string via ``str()``).
        """
        self.f.write(str(data) + "\n")
        print(data)

    def log(self, data):
        """Write *data* to the log file and console, prefixed with elapsed seconds since construction.

        Args:
            data: Value to log (converted to string via ``str()``).
        """
        self.log_notime(str(time.perf_counter() - self.timezero) + str(data))

    def create_error(self):
        """Increment the internal error counter (counter is tracked but never written to the log)."""
        self.errcnt += 1

    def finish(self):
        """Write a closing timestamp with total elapsed time, then close the file."""
        self.log_notime(
            "Data log closed at {}.  Elapsed time: {}".format(
                time.strftime("%a, %d %b %Y %H:%M:%S"),
                time.perf_counter() - self.timezero))
        self.f.close()
