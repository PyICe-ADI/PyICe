'''
VISA Emulation Layer
====================

Interface wrappers to use various interfaces as if they were VISA resources
without requiring an installed VISA library. Facilitates seamless transition 
between physical inrefaces and operating systems.
'''

import time
import struct
import re
import logging
debug_logging = logging.getLogger(__name__)
dbgprint = debug_logging.debug
try:
    import pyvisa as visa
    visaMissing = False
except:
    visaMissing = True
try:
    import ctypes
    ctypesMissing = False
except:
    ctypesMissing = True
try:
    import serial
    serialMissing = False
except:
    serialMissing = True
try:
    import vxi11
    vxi11Missing = False
except:
    vxi11Missing = True
try:
    import usbtmc
    usbtmcMissing = False
except:
    usbtmcMissing = True
try:
    import telnetlib
    telnetlibMissing = False
except:
    telnetlibMissing = True

# Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
# be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
# if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
str_encoding = 'latin-1'
def strify(bs):
    if not isinstance(bs, str):
        return bs.decode(str_encoding)
    else:
        print(f"Unexpected stringification of non-byte string: {bs}. Contact PyICe-developers@analog.com for more information.")
        return bs
def byteify(s):
    if isinstance(s, str):
        return s.encode(str_encoding)
    else:
        print(f"Unexpected byteification of byte string: {s}. Contact PyICe-developers@analog.com for more information.")
        return s

class visaWrapperException(Exception):
    pass

class visa_wrapper(object):
#    def __init__(self, address, timeout=5):
#        raise NotImplementedError('Interface Not Fully Implemented: __init__()')
    def read(self):
        raise NotImplementedError('Interface Not Fully Implemented: read()')
    def write(self, message):
        raise NotImplementedError('Interface Not Fully Implemented: write()')
    def read_values(self):
        raise NotImplementedError('Interface Not Fully Implemented: read_values()')
    def read_values_binary(self, format_str='=B', byte_order='=', terminationCharacter=''):
        '''Follows Definite Length Arbitrary Block format
        ie ASCII header '#<heder_bytes_following><data_bytes_following><data0>...<dataN>
        eg #40003<byte0><byte1><byte2><byte3>
        format_str and byte_order are passed to struct library for to set word boundaries for unpacking and conversion to numeric types
        https://docs.python.org/2/library/struct.html#format-strings'''
        raise NotImplementedError('Interface Not Fully Implemented: read_values_binary()')
    def ask(self, message):
        self.write(message)
        return self.read()
    def ask_for_values(self, message):
        self.write(message)
        return self.read_values()
    def ask_for_values_binary(self, message, format_str='B', byte_order='=', terminationCharacter=''):
        '''Follows Definite Length Arbitrary Block format
        ie ASCII header '#<heder_bytes_following><data_bytes_following><data0>...<dataN>
        eg #40003<byte0><byte1><byte2><byte3>
        format_str and byte_order are passed to struct library for to set word boundaries for unpacking and conversion to numeric types
        https://docs.python.org/2/library/struct.html#format-strings'''
        assert isinstance(message, bytes)
        self.write_raw(message)
        return self.read_values_binary(format_str, byte_order, terminationCharacter)
    def clear(self):
        raise NotImplementedError('Interface Not Fully Implemented: clear()')
    def clear_errors(self):
        print("Interface Not Fully Implemented: clear_errors()'")
    def trigger(self):
        raise NotImplementedError('Interface Not Fully Implemented: trigger()')
    def read_raw(self):
        raise NotImplementedError('Interface Not Fully Implemented: read_raw()')
    def resync(self):
        '''flush buffers to resync after communication fault - usb-serial problem'''
        return ''
    def close(self):
        pass
    def __getTimeout(self):
        raise NotImplementedError('Interface Not Fully Implemented: timeout')
    def __setTimeout(self, timeout):
        raise NotImplementedError('Interface Not Fully Implemented: timeout')
    timeout = property(__getTimeout,__setTimeout)
    def __getTerminationChars(self):
        raise NotImplementedError('Interface Not Fully Implemented: term_chars')
    def __setTerminationChars(self, term_chars):
        raise NotImplementedError('Interface Not Fully Implemented: term_chars')
    term_chars = property(__getTerminationChars,__setTerminationChars)

import traceback

# Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
# be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
# if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
str_encoding = 'latin-1'

class visa_wrapper_serial(visa_wrapper):
    def __init__(self, address_or_serial_obj, timeout = 5, baudrate = 9600, **kwargs):
        serial_port_name = "(nameless serial port)"
        if isinstance(address_or_serial_obj, serial.SerialBase):
            self.ser = address_or_serial_obj
            serial_port_name = self.ser.port
        elif isinstance(address_or_serial_obj, telnetlib.Telnet): #TODO: migrate telnet library to use serial_for_url rfc2217://<host>:<port>[?<option>[&<option>]] class rfc2217.Serial
            self.ser = address_or_serial_obj
            serial_port_name = "telnetlib.Telnet emulated serial port"
        elif isinstance(address_or_serial_obj, (str, None)):
            self.ser = serial.Serial()
            self.ser.port = address_or_serial_obj		# open the specified serial port
            self.ser.timeout = timeout
            self.ser.baudrate = baudrate
            serial_port_name = self.ser.port
            self.ser.open()
        else:
            raise ValueError("visa_wrapper_serial() called with {}{} instead of expected address string "
                             "or serial.Serial object.".format(type(address_or_serial_obj), address_or_serial_obj))
        try:
            # self.terminationCharacter = kwargs['terminationCharacter'].encode(str_encoding)
            self.terminationCharacter = kwargs['terminationCharacter']
        except KeyError:
            # self.terminationCharacter = "\n".encode(str_encoding) # readline inherits from "io" which doesn't support termination character
            self.terminationCharacter = "\n" # readline inherits from "io" which doesn't support termination character
        super().__init__(serial_port_name, **kwargs)
        self.serial_port_name = serial_port_name
        self.resync()
    def readline(self):
        #TODO: speed this up using buffered IO to wrap serial port
        #readline() of ser doesn't work correctly
        #https://docs.python.org/2/library/io.html#io.TextIOWrapper
        #http://pyserial.readthedocs.org/en/latest/shortintro.html#eol
        dbgprint("vvv-- visa_wrapper_serial.readline({}) entered".format(self.serial_port_name))
        # response = bytes()
        response = str()
        while True:
            char = self.ser.read(1)
            response += char
            if char == self.terminationCharacter:
                break
            elif len(char) == 0:
                raise visaWrapperException("Serial timeout on port {}!".format(self.ser.port))
                #print "Serial timeout on port {}!".format(self.ser.port)
        dbgprint("^^^-- visa_wrapper_serial.readline({}) returns "
                 "{}".format(self.serial_port_name, repr(response)))
        return response
        # return strify(response)
    def read(self):
        dbgprint("vvv-- visa_wrapper_serial.read({}) entered".format(self.serial_port_name))
        message = self.readline().rstrip()
        dbgprint("^^^-- visa_wrapper_serial.read({}) returns "
                 "{}".format(self.serial_port_name, repr(message)))
        return message
    def write(self, message):
        dbgprint("vvv-- visa_wrapper.serial.write({}, {}) "
                 "entered".format(self.serial_port_name, repr(message)))
        if isinstance(message, str):
            pass
        elif isinstance(message, (bytes, bytearray)):
            print("Unexpected byte array in visa_wrapper_serial.write. Contact PyICe-developers@analog.com for more information.")
            message = strify(message)
            #2020-06-08 DJS: VISA itself seems to handle Unicode strings silently and correctly, so we probably should too. Disabling Frank's message. No reason to manage bytestrings manually within instrument drivers.
            if False:  # Helpful for debugging during Python 2 to 3 porting.
                print("*** visa_wrapper_serial.write() was passed a Unicode str instead of bytes.")
                print("    {}{}".format(repr(message), type(message)))
                print()
                traceback.print_stack()
                print()
                print("I will convert str to bytes for you using {} encoding.".format(str_encoding))
                print("*" * 76)
                # input("Press ENTER to continue")
        else:
            raise Exception(f"Unexpected visa_wrapper_serial.write message type: {type(message)}")
        if self.terminationCharacter is not None:
            message = message.rstrip() + self.terminationCharacter
        self.ser.write(message)
        dbgprint("^^^-- visa_wrapper_serial.write({}, {}) "
                 "returns".format(self.serial_port_name, repr(message)))
    def read_values(self):
        dbgprint("vvv-- visa_wrapper_serial.read_values({}) entered".format(self.serial_port_name))
        # valtup = self.read().decode(str_encoding).split(",")
        valtup = strify(self.read()).split(",")
        dbgprint("^^^-- visa_wrapper_serial.read_values({}) returns {}".format(self.serial_port_name, valtup))
        return valtup
    def read_values_binary(self, format_str='B', byte_order='=', terminationCharacter=''):
        '''Follows Definite Length Arbitrary Block format
        ie ASCII header '#<heder_bytes_following><data_bytes_following><data0>...<dataN>
        eg #40003<byte0><byte1><byte2><byte3>

        format_str is passed to struct library for to set word boundaries for unpacking and conversion to numeric types
        https://docs.python.org/2/library/struct.html#format-strings
        https://en.wikipedia.org/wiki/IEEE_754-1985
        'B': default unsigned single byte
        'b': signed single byte

        'H': unsigned short 2-byte integer
        'h': signed short 2-byte integer

        'I': unsigned 4-byte integer
        'i': signed 4-byte integer

        'Q': unsigned long long 8-byte integer
        'q': signed long long 8-byte integer

        'f': 4-byte IEEE_754-1985 float
        'd': 8-byte IEEE_754-1985 double precision float

        '<n>s': An <n>-byte long string

        byte_order sets endianness:
        '=': native
        '<': little-endian (LSByte first)
        '>': big-endian (MSByte first)
        '''
        dbgprint("vvv-- visa_wrapper_serial.read_values_binary({}) entered".format(self.serial_port_name))
        hash = self.ser.read(1)
        while hash != '#':
            if len(hash):
                print('Saw extra character code: {} in read_values_binary header'.format(ord(hash)))
            else: #timeout
                raise visaWrapperException('Timeout in read_values_binary header')
            hash = self.ser.read(1)
        header_len = int(self.ser.read(1))
        data_len = int(self.ser.read(header_len))
        data = self.ser.read(data_len).encode('latin-1')
        term = self.ser.read(len(terminationCharacter))
        format_len = struct.calcsize(format_str)
        fmt = byte_order + format_str * (data_len // format_len)
        dbgprint("^^^-- visa_wrapper_serial.read_values_binary({}) "
                 "returns struct({})".format(self.serial_port_name, repr(fmt)))
        return struct.unpack(fmt, data)
    def read_raw(self):
        dbgprint("vvv-- visa_wrapper_serial.read_raw({}) entered".format(self.serial_port_name))
        dbytes = self.readline()
        dbgprint("^^^-- visa_wrapper_serial.read_raw({}) returns "
                 "{}".format(self.serial_port_name, repr(dbytes)))
        return dbytes
    def write_raw(self, message):
        dbgprint("vvv-- visa_wrapper.serial.write_raw({}, {}) "
                 "entered".format(self.serial_port_name, repr(message)))
        # self.ser.write(message)
        # Incoming bytes. Strify enroute to serial
        self.ser.write(strify(message))
        dbgprint("^^^-- visa_wrapper_serial.write_raw({}, {}) "
                 "returns".format(self.serial_port_name, repr(message)))
    def flush(self):
        print(self.ser.flush())
    def resync(self):
        return self.ser.read(self.ser.inWaiting())
    def close(self):
        self.ser.close()
    def get_serial_port(self):
        "Returns the underlying serial port object."
        return self.ser
    def __getTimeout(self):
        return self.ser.timeout
    def __setTimeout(self, timeout):
        self.ser.timeout = timeout
    timeout = property(__getTimeout,__setTimeout)
    
class visa_wrapper_tcp(visa_wrapper_serial):
    def __init__(self, ip_address, port, timeout = 5, **kwargs):
        port = serial.serial_for_url('socket://{}:{}'.format(ip_address,port),timeout=timeout)
        visa_wrapper_serial.__init__(self, port, **kwargs)
    def resync(self):
        print('TCP Resync in progress.')
        resp_all = ''
        try:
            resp = self.readline()
            resp_all += resp
            while resp[-1:] == self.terminationCharacter:
                resp = self.readline()
                resp_all += resp
        except visaWrapperException as e:
            pass
        except Exception as e:
            raise e #what happened???
        finally:
            return resp_all
    def __getTimeout(self):
        return self.ser.timeout
    def __setTimeout(self, timeout):
        self.ser.timeout = timeout
    timeout = property(__getTimeout,__setTimeout)

class visa_wrapper_telnet(visa_wrapper_serial):
    #TODO?: migrate telnet library to use serial_for_url rfc2217://<host>:<port>[?<option>[&<option>]] class rfc2217.Serial
    def __init__(self, ip_address, port, timeout = 5):
        port = telnetlib.Telnet(ip_address,port,timeout=timeout)
        self._timeout = timeout
        visa_wrapper_serial.__init__(self, port)
    def resync(self):
        return self.ser.read_very_eager()
    def readline(self):
        response = self.ser.read_until(self.terminationCharacter, self._timeout)
        if response[-1] != self.terminationCharacter:
            print("Telnet timeout on port {}!".format(self.ser.port))
            # prolly should raise exception here (I am Dave)
        return response        
    def __getTimeout(self):
        return self._timeout
    def __setTimeout(self, timeout):
        self._timeout = timeout
    timeout = property(__getTimeout,__setTimeout)

class visa_wrapper_vxi11(visa_wrapper):
    def __init__(self, address, timeout=5):
        self.terminationCharacter = None
        self.vxi_interface = vxi11.Instrument(address, term_char=self.terminationCharacter, timeout=timeout)
    def read(self):
        return self.vxi_interface.read()
    def write(self, message):
        #DJS Does this needs tom strify/byteify help???
        self.vxi_interface.write(message)
    def read_values(self):
        #ascii transfer only
        #see visa.py for binary parsing example
        float_regex = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\d*\.\d+)"
                                     "(?:[eE][-+]?\d+)?")
        return [float(raw_value) for raw_value in
            float_regex.findall(self.read())]
    def ask(self, message):
        return self.vxi_interface.ask(message)
    def ask_for_values(self, message):
        self.write(message)
        return self.read_values()
    def clear(self):
        raise NotImplementedError('Interface Not Fully Implemented: clear()')
    def trigger(self):
        self.vxi_interface.trigger()
    def read_raw(self):
        self.vxi_interface.read_raw()
    def resync(self):
        '''flush buffers to resync after communication fault - usb-serial problem'''
        pass
    def close(self):
        self.vxi_interface.close()
    def open(self):
        self.vxi_interface.open()
    def __getTimeout(self):
        return self.vxi_interface.io_timeout
    def __setTimeout(self, timeout):
        #not sure if this will actually take effect
        self.vxi_interface.io_timeout = timeout
    timeout = property(__getTimeout,__setTimeout)
    
class visa_wrapper_usbtmc(visa_wrapper):
    def __init__(self, address, timeout=5):
        if usbtmcMissing:
            raise Exception('USB Test and Measurment class init failed. Do you have PyUSB installed properly with a libusb (1.0 or 0.1) or OpenUSB backend?', 'For Windows users, libusb 0.1 is provided through libusb-win32 package. Check the libusb website for updates (http://www.libusb.info).')
        self.terminationCharacter = None
        self.usbtmc_interface = usbtmc.Instrument(address, term_char=self.terminationCharacter)
        self.usbtmc_interfacetimeout = timeout
    def read(self):
        return self.usbtmc_interface.read()
    def write(self, message):
        self.usbtmc_interface.write(message)
    def read_values(self):
        #ascii transfer only
        #see visa.py for binary parsing example
        float_regex = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\d*\.\d+)"
                                     "(?:[eE][-+]?\d+)?")
        return [float(raw_value) for raw_value in
            float_regex.findall(self.read())]
    def ask(self, message):
        return self.usbtmc_interface.ask(message)
    def ask_for_values(self, message):
        self.write(message)
        return self.read_values()
    def clear(self):
        self.usbtmc_interface.clear()
    def trigger(self):
        self.usbtmc_interface.trigger()
    def read_raw(self):
        self.usbtmc_interface.read_raw()
    def resync(self):
        '''flush buffers to resync after communication fault - usb-serial problem'''
        pass
    def close(self):
        self.usbtmc_interface.close()
    def open(self):
        self.usbtmc_interface.open()
    def __getTimeout(self):
        return self.usbtmc_interface.timeout
    def __setTimeout(self, timeout):
        self.usbtmc_interface.timeout = timeout
    timeout = property(__getTimeout,__setTimeout)

class visa_interface(visa_wrapper):
    '''agilent visa strips trailing termination character, but NI VISA seems to leave them in response.'''
    def __init__(self, address, timeout=5):
        if visaMissing:
            raise visaWrapperException('VISA library missing from this system')
        elif "instrument" in dir(visa):  # Old API from PyVISA rev < 1.5
            self.visaInterface = visa.instrument(resource_name=address)#, timeout=timeout)
            self.timeout_scale = 1
        else:  # Use new API PyVISA rev >= 1.5
            self.visaInterface = visa.ResourceManager().open_resource(address)
            self.timeout_scale = 1e-3
        self.timeout = timeout
    def read(self):
        return self.visaInterface.read().rstrip()
    def write(self, message):
        if not isinstance(message, str):
            print("fVisa write() message unexpectedly non-string ({type(message)}). Contact PyICe-developers@analog.com for more information.")
            message = message.decode(str_encoding)
            traceback.print_stack()
        self.visaInterface.write(message)
    def read_values(self):
        return self.visaInterface.read_values().rstrip()
    def ask(self, message):
        return self.visaInterface.query(message).rstrip()
    def ask_for_values(self, message):
        return self.visaInterface.ask_for_values(message).rstrip()
    def ask_for_values_binary(self, message, format_str='B', byte_order='=', terminationCharacter=''):
        if byte_order == '<':
            is_big_endian = False
        else:
            is_big_endian = True #Maybe not quite right... '='?
        return self.visaInterface.query_binary_values(message, datatype=format_str, is_big_endian=is_big_endian)
    def clear(self):
        self.visaInterface.clear()
    def trigger(self):
        self.visaInterface.trigger()
    def read_raw(self):
        return self.visaInterface.read_raw() # Response comes back as bytes from VISA lib
    def close(self):
        self.visaInterface.close()
    def flush(self, buffer):
        if buffer == "READ":
            self.visaInterface.flush(visa.constants.VI_READ_BUF)
        elif buffer == "WRITE":
            self.visaInterface.flush(visa.constants.VI_WRITE_BUF_DISCARD)
        else:
            raise(f"visa_wrappers.py flush():  Don't know how to flush visa buffer: {buffer}")
    def __getTimeout(self):
        return self.visaInterface.timeout * self.timeout_scale
    def __setTimeout(self, timeout):
        self.visaInterface.timeout = timeout / self.timeout_scale
    def __delTimeout(self):
        del self.visaInterface.timeout
    timeout = property(__getTimeout, __setTimeout, __delTimeout)
    def __getTerminationChars(self):
        return self.visaInterface.term_chars
    def __setTerminationChars(self, term_chars):
        self.visaInterface.term_chars = term_chars
    term_chars = property(__getTerminationChars,__setTerminationChars)

