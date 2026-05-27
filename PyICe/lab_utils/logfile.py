"""Logfile utility.

>>> from PyICe.lab_utils.logfile import logfile

"""
import time
from .print_to_screen import print_to_screen


class logfile(object):
    """Write text to a log file using the same API as ``print_to_screen()``.

    Provides :meth:`print_to_file` for silent logging and
    :meth:`print_to_file_and_screen` (aliased as :meth:`write`) to log and
    echo to the console simultaneously.  Intended as a drop-in *write*
    callback for utilities like :func:`print_hex_bytes`.

    >>> from PyICe.lab_utils.logfile import logfile
    >>> logfile is not None
    True

    """
    def __init__(self, filename=None):
        """Open (or create) a log file for writing.
        Stores configuration in ``f``, ``filename`` for use by other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_utils.logfile import logfile
        >>> logfile is not None
        True

        Args:
            filename: Path for the log file.  Defaults to a timestamped name
                like ``log-2024-03-15-1430.txt``.
        """
        self.filename = filename if filename is not None else time.strftime(
            "log-%Y-%m-%d-%H%M.txt")
        self.f = open(self.filename, "w")

    def print_to_file(self, *args, **kwargs):
        """Write arguments to the log file (without echoing to the console).

        Mirrors the ``print_to_screen`` calling convention: each positional
        argument is written, and a trailing newline is appended unless
        ``linefeed=False`` is passed.


        >>> from PyICe.lab_utils.logfile import logfile
        >>> hasattr(logfile, 'print_to_file')
        True

        Args:
            *args: Values to write to the file.
            **kwargs: Pass ``linefeed=False`` to suppress the trailing newline.

        Returns:
            The number of positional arguments written.
        """
        if args:
            for arg in args:
                self.f.write(arg)
        if "linefeed" not in kwargs or (
                "linefeed" in kwargs and kwargs["linefeed"] is True):
            self.f.write("\n")
        self.f.flush()
        return len(args)

    def print_to_file_and_screen(self, *args, **kwargs):
        """Write arguments to both the log file and the console.

        Delegates to ``print_to_screen`` for console output and
        :meth:`print_to_file` for file output, using identical arguments.


        >>> from PyICe.lab_utils.logfile import logfile
        >>> hasattr(logfile, 'print_to_file_and_screen')
        True

        Args:
            *args: Values to write.
            **kwargs: Pass ``linefeed=False`` to suppress the trailing newline.
        """
        print_to_screen(*args, **kwargs)
        self.print_to_file(*args, **kwargs)
    write = print_to_file_and_screen

    def close(self):
        """Flush and close the underlying log file.

        Captures data for later analysis or replay.

        >>> from PyICe.lab_utils.logfile import logfile
        >>> hasattr(logfile, 'close')
        True

        """
        self.__del__()

    def __del__(self):
        """Close the log file handle during garbage collection.

        Performs cleanup when the object is garbage-collected.

        >>> from PyICe.lab_utils.logfile import logfile
        >>> hasattr(logfile, '__del__')
        True

        """
        self.f.close()
