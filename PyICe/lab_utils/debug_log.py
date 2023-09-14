import time

class debug_log(object):
    '''Log messages into a file and optionally print to screen.'''
    # This class used in most of Frank's tests.
    def __init__(self, log_file_name=__name__+".log", debug=False):
        self.debug = debug
        self.f = open(log_file_name, "w")
        self.fileno = self.f.fileno
        # atexit.register(self.__del__)  # Tries to close the debug_log file if the program exits for any reason.
    def __enter__(self):
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        self.f.close()
        return None
    def write(self, msg):
        '''Add a message to the log file. Also print the message if debug is True'''
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