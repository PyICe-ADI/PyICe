from ..lab_core import *

class modbus_register(channel):
    '''register in the sense of remote memory (read AND write functions), but without binary/2's comp features'''
    def __init__(self, name, read_function, write_function=None):
        channel.__init__(self, name=name, read_function=read_function)
        if write_function is not None:
            self._write = write_function
            self.set_write_access(True)