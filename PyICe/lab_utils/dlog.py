import time


class dlog(object):
    """Dlog (object subclass)."""
    def __init__(self, filename="output.txt"):
        """Open filehandle to filename.  If omitted, filename defaults to "output.txt.

        Args:
            filename: File path.
        """
        self.errcnt = 0
        self.f = open(filename, 'w')
        # note the time.clock function won't work well for linux...
        # this is written for windows
        self.timezero = time.clock()
        # time/date stamp header
        self.log_notime(time.strftime("%a, %d %b %Y %H:%M:%S"))

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

    def log_notime(self, data):
        """Write data to file with trailing newline.

        Args:
            data: Data to write.
        """
        self.f.write(str(data) + "\n")
        print(data)

    def log(self, data):
        """Write data to file with timestamp and trailing newline.

        Args:
            data: Data to write.
        """
        self.log_notime(str(time.clock() - self.timezero) + str(data))

    def create_error(self):
        """This function doesn't appear to actually do much.  self.errcnt is never written to the dlog."""
        self.errcnt += 1

    def finish(self):
        """Write final timestamp and close filehandle."""
        self.log_notime(
            "Data log closed at {}.  Elapsed time: {}".format(
                time.strftime("%a, %d %b %Y %H:%M:%S"),
                time.clock() - self.timezero))
        self.f.close()
