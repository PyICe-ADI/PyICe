"""Debug log utility.

>>> from PyICe.lab_utils.debug_log import debug_log

"""
import time


class debug_log(object):
    """Append timestamped messages to a log file, optionally echoing to the console.

    >>> from PyICe.lab_utils.debug_log import debug_log
    >>> debug_log is not None
    True

    """
    # This class used in most of Frank's tests.

    def __init__(self, log_file_name=__name__ + ".log", debug=False):
        """Open (or create) a log file for writing.
        Stores configuration in ``debug``, ``f``, ``fileno`` for use by other
        methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_utils.debug_log import debug_log
        >>> debug_log is not None
        True

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
        Sets up the context manager for ``with`` statement usage.

        Sets up the context manager for use in a ``with`` statement.


        >>> from PyICe.lab_utils.debug_log import debug_log
        >>> hasattr(debug_log, '__enter__')
        True

        Returns:
            This :class:`debug_log` instance.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the log file when exiting a ``with`` block.
        Tears down the context manager and handles exceptions.

        Cleans up resources when leaving a ``with`` block.


        >>> from PyICe.lab_utils.debug_log import debug_log
        >>> hasattr(debug_log, '__exit__')
        True

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


        >>> from PyICe.lab_utils.debug_log import debug_log
        >>> hasattr(debug_log, 'write')
        True

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
