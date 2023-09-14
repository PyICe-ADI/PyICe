import time

class logfile(object):
    """Creates a file and allows writes to it using the same API as print_to_screen().
    Optionally can also print what is written to the screen."""
    def __init__(self, filename=None):
        self.filename = filename if filename is not None else time.strftime("log-%Y-%m-%d-%H%M.txt")
        self.f = open(self.filename, "w")
    def print_to_file(self, *args, **kwargs):
        if args:
            for arg in args:
                self.f.write(arg)
        if "linefeed" not in kwargs or ("linefeed" in kwargs and kwargs["linefeed"] is True):
            self.f.write("\n")
        self.f.flush()
        return len(args)
    def print_to_file_and_screen(self, *args, **kwargs):
        print_to_screen(*args, **kwargs)
        self.print_to_file(*args, **kwargs)
    write = print_to_file_and_screen
    def close(self):
        self.__del__()
    def __del__(self):
        self.f.close()