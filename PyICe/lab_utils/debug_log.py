"""Debug log utility."""
import time


class debug_log(object):
    """Append timestamped messages to a log file, optionally echoing to the console."""
    # This class used in most of Frank's tests.

    def __init__(self, log_file_name=__name__ + ".log", debug=False):
        """Open (or create) a log file for writing.

        Args:
            log_file_name: Path to the log file.  Defaults to
                ``<module_name>.log``.
            debug: When ``True``, every :meth:`write` call also prints
                the message to stdout.
        """
        self.debug = debug
        self.f = open(log_file_name, "w")
        self.fileno = self.f.fileno
        # atexit.register(self.__del__)  # Tries to close the debug_log file if
        # the program exits for any reason.

    def __enter__(self):
        """Enter the context manager, returning this instance for use in a ``with`` block.

        Returns:
            This :class:`debug_log` instance.
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

    def write(self, msg):
        """Write a timestamped message to the log file, flushing immediately.

        If *debug* was set at construction, the message is also printed to
        stdout.

        Args:
            msg: The message text to log.
        """
        t_str = time.asctime()
        m_str = "{} :: {}\n".format(t_str, msg)
        if self.debug:
            print(m_str, end=' ')
        self.f.write(m_str)
        self.f.flush()

    # def __del__(self):
        # self.f.flush()
        # os.fsync(self.fileno)
        # self.f.close()
