"""Debug log utility."""
import time


class debug_log(object):
    """Log messages into a file and optionally print to screen."""
    # This class used in most of Frank's tests.

    def __init__(self, log_file_name=__name__ + ".log", debug=False):
        """Initialize debug_log.

        Args:
            debug: If True, enable debug output.
            log_file_name: Log file name.
        """
        self.debug = debug
        self.f = open(log_file_name, "w")
        self.fileno = self.f.fileno
        # atexit.register(self.__del__)  # Tries to close the debug_log file if
        # the program exits for any reason.

    def __enter__(self):
        """Enter the context manager.

        Returns:
            Result value.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager.

        Args:
            exc_tb: Exc tb.
            exc_type: Exc type.
            exc_val: Exc val.

        Returns:
            Result value.
        """
        self.f.close()
        return None

    def write(self, msg):
        """Add a message to the log file. Also print the message if debug is True.

        Args:
            msg: Msg.
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
