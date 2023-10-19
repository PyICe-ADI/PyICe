'''
Physical Communication Interfaces Hierarchy Manager
===================================================
Required for multithreaded communication.
'''
import sys, abc
try:
    import pyvisa
    visaMissing = False
except:
    visaMissing = True
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
'''
Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
'''
STR_ENCODING = 'latin-1'
def strify(bs):
    if not isinstance(bs, str):
        return bs.decode(STR_ENCODING)
    else:
        print(f"Unexpected stringification of non-byte string: {bs}. Contact PyICe-developers@analog.com for more information.")
        return bs
def byteify(s):
    if isinstance(s, str):
        return s.encode(STR_ENCODING)
    else:
        print(f"Unexpected byteification of byte string: {s}. Contact PyICe-developers@analog.com for more information")
        return s
from collections import OrderedDict
str_log_dict = OrderedDict()
import labcomm
from . import twi_interface
from . import spi_interface
#visa wrappers should probably go away and get merged in here
from . import visa_wrappers
import multiprocessing

try:
    import usb.core
    ubsMissing = False
except:
    ubsMissing = True
import logging
debug_logging = logging.getLogger(__name__)
# logfile_handler = logging.FileHandler(filename="lab_interfaces.debug.log", mode="w")
# debug_logging.addHandler(logfile_handler)
warn = debug_logging.warning
class communication_node(object):
    '''The purpose of this is to map a network of communication resources to each channel'''
    def __init__(self, *args, **kwargs):
        '''this should never explicity take arguments since it is silently created many ways.
        However, subclasses with multiple inheritance will have constructors needing to
        be called. We forward whatever arguments we get to the superclass constructor.'''
        super().__init__(*args, **kwargs)
        self._parent = None
        self._thread_safe = False
        self._children = []
        self._lock = multiprocessing.RLock()
    def debug_com_nodes(self, indent=""):
        print(f'{indent}{self}, child of {self._parent}. Thread_safe: {self._thread_safe}')
        for child in self._children:
            child.debug_com_nodes(indent=f"{indent}    ")
    def get_com_parent(self):
        return self._parent
    def set_com_node_parent(self,parent):
        if self._parent:    
            print("warning: changing a communication_node parent")
        self._parent = parent
        self._parent.com_node_register_child(self)
    def set_com_node_thread_safe(self, safe=True):
        self._thread_safe = safe
    def com_node_register_child(self,child):
        self._children.append(child)
    def com_node_get_root(self):
        if self._parent:
            return self._parent.com_node_get_root()
        else:
            return self
    def com_node_get_children(self):
        return self._children
    def com_node_get_all_descendents(self):
        descendents = set()
        for child in self.com_node_get_children():
            descendents.add(child)
            descendents = descendents.union( child.com_node_get_all_descendents() )
        return descendents
    def group_com_nodes_for_threads(self,sets=None):
        '''returns a list of sets of com_nodes, each set must be communicated with in 1 thread
        because upstream interfaces are not thread safe'''
        if sets==None:
            sets = list()
        if self._thread_safe:
            sets.append( set([self]) )
            for child in self.com_node_get_children():
                child.group_com_nodes_for_threads(sets) #will modify sets
        else:
            group =  self.com_node_get_all_descendents() 
            group.add(self)
            sets.append( group )
        return sets
    def group_com_nodes_for_threads_filter(self,com_node_list):
        '''takes a list of interfaces and returns a list of lists
        the returned list are interfaces that cannot be used concurrently
        each is an ideal candidate for a thread to handle
        make sure all interface's root resolves back here'''
        if len(set([interface.com_node_get_root() for interface in com_node_list])) > 1:
            print('lab_interfaces: ERROR, Too many COM node parents, either:')
            print(' 1. you did not get all your interfaces from the same master or interface_factory')
            print(' 2. you did not ask for threads from the root node')
            print(' 3. you are working on the interface library and broke something')
            print("known interfaces:")
            for interface in com_node_list:
                print(f"{interface} @ {interface.com_node_get_root()}")
            raise Exception(f"Too many COM node parents")
        #get a list of lists for all interfaces
        in_sets = self.group_com_nodes_for_threads()
        out_sets = []
        for in_set in in_sets:          
            out_group = []
            for item in in_set:
                if item in com_node_list:
                    out_group.append(item)
            if len(out_group):
                out_sets.append(out_group)
        return out_sets
    def lock(self):
        '''Lock this communication node to prevent concurrent use, then recursively
        acquire locks of this communication node's parents.'''
        self._lock.acquire()
        parent_com_node = self.get_com_parent()
        if isinstance(parent_com_node, communication_node):
            parent_com_node.lock()
        elif parent_com_node is None:
            return
        else:
            raise TypeError(f"While locking, found communication node parent with unexpected type '{type(parent_com_node)}'.\n"
                            "Expected 'communication_node' or 'None'")
    def unlock(self):
        '''Release all parent locks starting with this node's oldest ancestor. Finish by unlocking this com node.'''
        parent_com_node = self.get_com_parent()
        if isinstance(parent_com_node, communication_node):
            parent_com_node.unlock()
        elif parent_com_node is None:
            pass
        else:
            raise TypeError(f"While locking, found communication node parent with unexpected type '{type(parent_com_node)}'.\n"
                            "Expected 'communication_node' or 'None'")
        self._lock.release()
'''all communication is through one of these distinct interface classes
    interface_visa       (visa like communication regardless of physical interface)
    interface_twi        (i2c,smbus)
    interface_raw_serial (raw, low level serial)
    
    this probably covers most anything, new ones should only be added if the communication model doesn't fit any of these (SPI for example)
'''
''' this group of interface_* classes should not be directly created, create them only with the factory '''   
class interface(communication_node):
    '''base class all lab instruments should in some way talk to, all have a timeout whether or not it does anything'''
    def __init__(self, name, **kwargs):
        assert isinstance(name, str)
        self._interface_name = name if len(name) else "nameless interface"
        #cannot use hasattr since its sometimes a property
        if "timeout" not in dir(self):
            self.timeout = None
        super().__init__(**kwargs)
    def __str__(self):
        return self._interface_name
class interface_visa(interface):
    pass
class interface_twi(interface):
    pass
class interface_spi(interface):
    pass
class interface_bobbytalk(interface):
    '''Base class for all interfaces that talk bobbytalk packets
    and provide the bobbytalk API methods shown here.'''
    def __init__(self, name):
        super(interface_bobbytalk, self).__init__(name)
    def send_packet(self, src_id, dest_id, buffer):
        '''Returns immediately indicating SUCCESS (True) or FAIL (False).
           Returns SUCCESS if buffer successfully sent to the
           underlying interface.
           Otherwise FAIL, meaning the underlying interface
           couldn't accept buffer for some reason.'''
        raise NotImplementedError("Subclass must implement this.")
    def recv_packet(self, dest_id, timeout, src_id=None):
        '''Blocks for up to timeout waiting for packet matching dest_id
           and optionally src_id, continuing to receive and dispatch other
           incoming packets.
           Upon success, returns a bobbytalk_packet object.
           Upon timeout, returns None.'''
        raise NotImplementedError("Subclass must implement this.")
    def handle_comms(self):
        '''Call this periodically to receive packets from the underlying interface
           and dispatch to any registered packet handlers (or "modules")'''
        raise NotImplementedError("Subclass must implement this.")
    def register_handler(self, dest_id, handler_function):
        '''Sets the handler function for received packets with dest_id.
           handler_function will be called like this:
           handler_function(bobbytalk_packet)'''
        raise NotImplementedError("Subclass must implement this.")
class interface_libusb(interface):
    '''Bulk transfer through LibUSB/WinUSB.
    Implementation may be overly specific to George B's Direct590 protocol and may need additional options or subclassing later.
    Transfers must be in multiples of this 64 byte payload size or will result in a babble error in the underlying library.
    Requires PyUSB: https://github.com/walac/pyusb'''
    def __init__(self, idVendor, idProduct, timeout):
        '''PyUSB requires installation of WinUSB filter driver. Use install-filter-win.exe under PyICe/deps/Direct590.
        Untested on linux; filter driver probably not required.
        '''
        interface.__init__(self, 'WinUSB Communication Interface')
        self.timeout = 1000 * timeout #ms
        #https://github.com/walac/pyusb/blob/master/docs/tutorial.rst
        # find our device
        self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        # was it found?
        if self.dev is None:
            raise ValueError('LibUSB Device not found. Is filter driver installed? (see docstring)')
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()
        # get an endpoint instance
        self.cfg = self.dev.get_active_configuration()
        self.intf = self.cfg[(0,0)]
        self.ep_out = usb.util.find_descriptor(
                                      self.intf, # match the first OUT endpoint
                                      custom_match = \
                                        lambda e: \
                                            usb.util.endpoint_direction(e.bEndpointAddress) == \
                                            usb.util.ENDPOINT_OUT
                                      )
        assert self.ep_out is not None
        self.ep_in = usb.util.find_descriptor(
                                      self.intf, # match the first OUT endpoint
                                      custom_match = \
                                        lambda e: \
                                            usb.util.endpoint_direction(e.bEndpointAddress) == \
                                            usb.util.ENDPOINT_IN
                                      )
        assert self.ep_in is not None
        #self.stream_in = ''
        # a.dev.configurations()[0].interfaces()[0].endpoints()[0].wMaxPacketSize
        self.write_packet_size = self.ep_out.wMaxPacketSize
        self.read_packet_size = self.ep_in.wMaxPacketSize
        print(self.dev)
    def read(self):
        ''''''
        resp = self.dev.read(self.ep_in, self.read_packet_size, self.timeout)
        while len(resp) == self.read_packet_size: #response split across packets
            resp += self.dev.read(self.ep_in, self.read_packet_size, self.timeout)
        return resp.tostring() #(resp,remain)
    def write(self, byte_list):
        '''Send byte_list across subclass-specific communication interface.'''
        self.dev.write(self.ep_out, byte_list)
class interface_stream(interface, metaclass=abc.ABCMeta): #(lab_interfaces.interface)
    '''Generic parent class of all stream-type interfaces. 
    Developed for DC590 board variants, but probably has more generic utility if moved into lab_interfaces
    Maybe consider change to inherit from https://docs.python.org/2/library/io.html
    '''
    @abc.abstractmethod
    def read(self, byte_count):
        '''Read and return tuple  (byte_count bytes, byte_count remaining_bytes) from subclass-specific communication interface.
        If fewer than byte_count bytes are available, return all available.
        '''
        pass
    @abc.abstractmethod
    def write(self, byte_list):
        '''Send byte_list across subclass-specific communication interface.'''
        pass
    @abc.abstractmethod
    def close(self):
        '''close the underlying interface if necessary'''
        pass
class interface_stream_serial(interface_stream):
    '''PySerial based stream wrapper.'''
    def __init__(self,interface_raw_serial):
        super().__init__('Serial Stream Communication Interface')
        self.ser = interface_raw_serial
    def read(self, byte_count):
        '''Read and return tuple  (byte_count bytes, byte_count remaining_bytes) from subclass-specific communication interface.
        If fewer than byte_count bytes are available, return all available.
        If byte_count is None, return all available.
        '''
        if byte_count is None:
            byte_count = self.ser.inWaiting()
        resp = self.ser.read(byte_count)
        remain = self.ser.inWaiting()
        return (resp,remain)
    def write(self, byte_list):
        '''Send byte_list across subclass-specific communication interface.'''
        self.ser.write(byte_list)
    def close(self):
        '''close the underlying interface'''
        self.ser.close()
class interface_ftdi_d2xx(interface_stream):
    '''write this if you want it
        https://pypi.python.org/pypi/pylibftdi'''
    def __init__(self): #need some kind of device descriptor....
        interface.__init__(self, 'FTDI D2XX Stream Communication Interface')
import array
import traceback
# Serial port debugging hack that uses undocumented calls in PySerial 3.4.
PYSERIAL_DEBUG = False
if serial.VERSION == '3.4' and PYSERIAL_DEBUG:
    s = serial.Serial()  # <--- This is needed for some reason, else SpySerial ports
                         # cannot be opened. There must be some kind of library initialization
                         # that happens when a regular serial.Serial object is first created.
                         # This sort of thing is expected when using undocumented calls.
    from serial.urlhandler.protocol_spy import Serial as SpySerial  # <--- UNDOCUMENTED CALL
    class serial_from_name_or_url(SpySerial):
        _has_PyICe_debug_capability = True
    '''     # def __init__(self, *args, **kwargs):
            #     if len(args) > 0:
            #         self._PyICe_port = args[0]
            #     elif "port" in kwargs:
            #         self._PyICe_port = kwargs["port"]
            #     else:
            #         self._PyICe_port = ""
            #     super().__init__(*args, **kwargs)
            #     self.port = self._PyICe_port'''
else:
    class serial_from_name_or_url(serial.Serial):
        _has_PyICe_debug_capability = False
class interface_raw_serial(interface, serial_from_name_or_url):
    def __init__(self, port_name_or_url, baudrate, timeout, **kwargs):
        super().__init__(name=port_name_or_url, **kwargs)
        from urllib.parse import urlparse
        assert isinstance(port_name_or_url, str)
        maybe_parsed_url = urlparse(port_name_or_url)
        if maybe_parsed_url.scheme == "spy":
            # We were passed a spy:// URL instead of a port name.
            if self._has_PyICe_debug_capability:
                serial_port_name = maybe_parsed_url.netloc
            else:
                raise TypeError(f"spy:// URL passed to interface_raw_serial() "
                                "constructor where port name expected instead:\n"
                                f"    {port_name_or_url}\n"
                                "Turn on serial_debug in boston_benches to use spy:// URLs"
                                "")
        elif isinstance(port_name_or_url, str) and len(port_name_or_url):
            # A string that isn't a valid URL, so assume we were passed a port name.
            serial_port_name = port_name_or_url
            if self._has_PyICe_debug_capability:
                # self is subclass of SpySerial, so reformat superclass init arg to "spy://" URL.
                port_name_or_url = f"spy://{port}?file=log{serial_port_name}.txt"
        elif isinstance(port_name_or_url, None) or (isinstance(port_name_or_url, str) and not len(port_name_or_url)):
            serial_port_name = ""
        else:
            raise ValueError(f"interface_raw_serial.__init__() passed a {type(port_name_or_url)}{port_name_or_url} when either a port name "
                             "or spy:// URL was expected")
        # interface.__init__(self,'interface_raw_serial @ {}'.format(port_name_or_url))
        if serial_port_name:
            self.port = port_name_or_url
            self.open()
        if baudrate:
            self.baudrate = baudrate
        if timeout:
            self.timeout = timeout
        self._serial_port_name = serial_port_name
    def get_serial_port_name(self):
        return self._serial_port_name
    def write(self, msg, *args, **kw):
        #'''Attempt to intercept calls to PySerial write() and do str to bytes translation as needed'''
        # Intercept calls to abstract all byte-serialization from the rest of PyICe. Work natively in Python3 unicode strings.
        if isinstance(msg, str):
            msgbytes = byteify(msg)
            # if True:  # Helpful for debugging during Python 2 to 3 porting.
                # stack_str_list = traceback.format_stack()
                # if tuple(stack_str_list) not in str_log_dict:
                    # str_log_dict[tuple(stack_str_list)] = msg
                    # warn("*** interface_raw_serial.write() was passed a Unicode str instead of bytes.")
                    # warn("    {}{}".format(repr(msg), type(msg)))
                    # for stack_str in stack_str_list:
                        # warn("  {}".format(stack_str))
                    # warn("I will convert str to bytes for you using {} encoding.".format(STR_ENCODING))
                    # warn("*" * 76)
        elif isinstance(msg, (bytes, bytearray, array.array)):
            # This eventually shouldn't happen. We're trying to migrate all of PyICe instrument/I2C stuff to use Py3 Unicode strings.
            msgbytes = msg
            print(f"PyICe: lab_interfaces.interface_raw_serial.write() @{self.get_serial_port_name()} unexpectedly sending out byte array message: {msg}. Consider using write_raw() or contact PyICe-developers@analog.com for more information.")
        else:
            debug_logging.error("*** lab_interfaces.interface_raw_serial.write() called with first argument that was "
                                "neither str, bytes, nor bytearray:\n"
                                f"***   {repr(msg)}{type(msg)}")
            raise Exception(repr(msg), type(msg))
        return self.write_raw(msgbytes, *args, **kw)
    def read(self, size, *args, **kw):
        resp = self.read_raw(size, *args, **kw)
        return strify(resp)
    def readline(self, *args, **kw):
        resp = super(interface_raw_serial, self).readline(*args, **kw)
        return strify(resp)
    # Readlines, writelines, readinto, .... byte<->str wrappers unimplemented!!!
    def write_raw(self, msgbytes, *args, **kw):
        return super(interface_raw_serial, self).write(msgbytes, *args, **kw)
    def read_raw(self, size, *args, **kw):
        return super(interface_raw_serial, self).read(size, *args, **kw)
    def __del__(self):
        '''Close interface (serial) port on exit'''
        self.close()
class interface_tcp_serial(interface):
    '''Opens a new TCP socket to (IP, port) and presents
    a PySerial-like PyICe interface to it.

    This class's API mimics enough of interface_raw_serial's API
    to be compatible with PyICe code expecting such.
    For example read(), write(), and timeouts are supported,
    but it is meaningless to set things like baudrate or parity bits.'''
    def __init__(self, dest_ip_address, dest_tcp_portnum):
        self.ser = serial.serial_for_url(f"socket://{dest_ip_address}:{dest_tcp_portnum}")
        super(interface_tcp_serial, self).__init__(self.ser.port)
    def get_serial_port_name(self):
        return self.ser.port
    def read(self, *args, **kwargs):
        return self.ser.read(*args, **kwargs)
    def write(self, *args, **kwargs):
        return self.ser.write(*args, **kwargs)
    def close(self, *args, **kwargs):
        return self.ser.close(*args, **kwargs)
    @property
    def timeout(self):
        return self.ser.timeout
    @timeout.setter
    def timeout(self, new_timeout):
        self.ser.timeout = new_timeout
    @property
    def in_waiting(self):
        if hasattr(self.ser, "in_waiting"):
            return self.ser.in_waiting
        elif hasattr(self.ser, "inWaiting"):
            return self.ser.inWaiting()
    def inWaiting(self):
        "Returns in_waiting. Added for PySerial <3.0 compatibility."
        return self.in_waiting
import random, time
class SerialTestHarness(object):
    '''A harness for testing code that reads and parses input
    from PySerial serial.Serial objects. A SerialTestHarness
    emulates a PySerial serial.Serial object by providing a read()
    method and a writable timeout property.
    bytestream is a generator function that yields one byte
    of test stimulus each time its next() method is called.
    WARNING: Not thread-safe.
    TODO: The write() method currently implemented does nothing.'''
    def __init__(self, bytestream, max_bytes_returned_per_read=None):
        self._timeout = 0.0
        self.bytestream = bytestream
        self._max_bytes_returned_per_read = max_bytes_returned_per_read
        # _in_waiting is the number of bytes we promise are available for
        # immediate read()'ing. In this implementation, we keep the
        # number undefined (=None) until someone tries to evaluate
        # self.in_waiting, whereupon the @property getter method below
        # randomly chooses a non-negative value
        # not exceeding max_bytes_returned_per_read. We remember the promised
        # value until the first read() call, whereupon we reset _in_waiting
        # back to None (i.e. undefined) again.
        self._in_waiting = None
        pass
    @staticmethod
    def biased_rng(min_val, max_val):
        assert isinstance(min_val, int)
        assert isinstance(max_val, int) and max_val > min_val
        choice = random.randint(0, 3)
        if choice <= 1:
            # 1/4 chance of returning min_val.
            # 1/4 chance of returning min_val + 1.
            result = choice + min_val
        elif choice == 2 and max_val - min_val >= 3:
            # 1/4 chance of returning an integer
            # in the closed interval [min_val+2, max_val-1].
            result = random.randint(min_val + 2, max_val-1)
        else:
            # 1/4 chance of returning max_val
            result = max_val
        return result
    def read(self, numbytes):
        '''Returns up to numbytes bytes from our test suite's
        bytestream generator, with random delay that's within timeout.'''
        # First note by what wallclock time we have to
        # return the requested bytes:
        treturn = time.time() + self.timeout*random.uniform(0, 1.0)
        # Document the requirements for numbytes.
        assert isinstance(numbytes, int) and numbytes >= 1
        # Randomly choose how many bytes to return:
        if self._in_waiting is None:
            retlength = SerialTestHarness.biased_rng(0, numbytes)
        else:
            # We promised at least self._in_waiting bytes are available.
            if numbytes > self._in_waiting:
                # Return at least the promised number of bytes.
                retlength = SerialTestHarness.biased_rng(self._in_waiting, numbytes)
            else:
                retlength = SerialTestHarness.biased_rng(0, numbytes)
            # Reset in_waiting to be undefined again.
            self._in_waiting = None
        # If requested, impose hard limit on max number of bytes returned.
        if self._max_bytes_returned_per_read is not None:
            retlength = min(retlength, self._max_bytes_returned_per_read)
        result = bytearray(retlength)
        for i in range(retlength):
            try:
                result[i] = next(self.bytestream)
            except StopIteration:
                # bytestream is out of data.
                # Truncate result because result[i:] isn't valid data.
                result = result[:i]
                break
        # Simulate time delay that is roughly within
        # our timeout setting.
        while True:
            twait = treturn - time.time()
            if twait <= 0:
                break
            time.sleep(twait)
        return result
    def write(self, bytestring):
        pass
    @property
    def timeout(self):
        return self._timeout
    @timeout.setter
    def timeout(self, new_timeout):
        from numbers import Real
        assert isinstance(new_timeout, Real) and new_timeout >= 0
        self._timeout = new_timeout
    @property
    def max_bytes_returned_per_read(self):
        return self._max_bytes_returned_per_read
    @max_bytes_returned_per_read.setter
    def max_bytes_returned_per_read(self, new_max):
        assert isinstance(new_max, int) and new_max >= 0
        self._max_bytes_returned_per_read = new_max
    @property
    def in_waiting(self):
        '''How many bytes we promise are available for reading.
        Generated randomly upon request, this
        will never exceed the max_bytes_returned_per_read
        optionally set during object instantiation.'''
        if self._in_waiting is not None:
            return self._in_waiting
        if self._max_bytes_returned_per_read is None:
            max_bytes = 4096  # Arbitrary but plausible value.
        else:
            max_bytes = self._max_bytes_returned_per_read
        self._in_waiting = SerialTestHarness.biased_rng(0, max_bytes)
        return self._in_waiting
    def inWaiting(self):
        "Returns in_waiting. Added for PySerial <3.0 compatibility."
        return self.in_waiting
class interface_test_harness_serial(interface, SerialTestHarness):
    def __init__(self,serial_port_name, bytestream, max_bytes_returned_per_read=4096):
        SerialTestHarness.__init__(self, bytestream,
                                   max_bytes_returned_per_read=max_bytes_returned_per_read)
        interface.__init__(self,f'interface_raw_serial @ {serial_port_name}')
        self._serial_port_name = serial_port_name
    def get_serial_port_name(self):
        return self._serial_port_name
'''below are specific classes that inherit from the above general classes'''
class interface_visa_tcp_ip(interface_visa,visa_wrappers.visa_wrapper_tcp):
    def __init__(self,host_address,port,timeout,**kwargs):
        visa_wrappers.visa_wrapper_tcp.__init__(self,host_address,port,timeout,**kwargs)
        interface_visa.__init__(self, f"interface_visa_tcp_ip @ {host_address}:{port}")
class interface_visa_telnet(interface_visa,visa_wrappers.visa_wrapper_telnet):
    def __init__(self,host_address,port,timeout):
        visa_wrappers.visa_wrapper_telnet.__init__(self,host_address,port,timeout)
        interface_visa.__init__(self, f"interface_visa_telnet @ {host_address}:{port}")
class interface_visa_serial(visa_wrappers.visa_wrapper_serial, interface_visa):
    def __init__(self,interface_raw_serial_object):
        super().__init__(interface_raw_serial_object)
        # visa_wrappers.visa_wrapper_serial.__init__(self,interface_raw_serial_object)
        # interface_visa.__init__(self,'interface_visa_serial @ {}'.format(interface_raw_serial_object))
class interface_visa_vxi11(interface_visa,visa_wrappers.visa_wrapper_vxi11):
    def __init__(self,address,timeout):
        visa_wrappers.visa_wrapper_vxi11.__init__(self, address, timeout)
        interface_visa.__init__(self, f'interface_visa_vxi11 @ {address}')
class interface_visa_usbtmc(interface_visa,visa_wrappers.visa_wrapper_usbtmc):
    def __init__(self,address,timeout):
        visa_wrappers.visa_wrapper_usbtmc.__init__(self, address, timeout)
        interface_visa.__init__(self, f'interface_visa_usbtmc @ {address}')
class interface_visa_direct(interface_visa, visa_wrappers.visa_interface):
    def __init__(self, visa_address_string, timeout):
        super().__init__(visa_address_string, address=visa_address_string, timeout=timeout)
        # visa_wrappers.visa_interface.__init__(self,visa_address_string,timeout)
        # interface_visa.__init__(self,'interface_visa_direct @ {}'.format(visa_address_string) )
        self.visa_address_string = visa_address_string
class interface_bobbytalk_raw_serial(interface_bobbytalk):
    "Sends and receives bobbytalk packets over a raw serial interface."
    def __init__(self, raw_serial_interface, fifo_size=2**16, junk_bytes_dump=None, debug=False):
        '''Provides the bobbytalk packet API over a raw_serial_interface
        which must be an instance of interface_raw_serial or SerialTestHarness.
        junk_bytes_dump is an optional argument. It's a function of one argument that receives
        all the bytes discarded by the bobbytalk parser as non-packet-bytes.
        '''
        # Can't be interface_stream_serial because we need to be
        # able to change timeouts on every recv_packet() call.
        super(interface_bobbytalk_raw_serial, self).__init__(name=(f"bobbytalk Packet interface over {raw_serial_interface.get_serial_port_name()}"))
        assert isinstance(fifo_size, int) and fifo_size > 0
        assert hasattr(junk_bytes_dump, "__call__") or junk_bytes_dump is None
        assert isinstance(debug, bool)
        self.ser = raw_serial_interface
        self.fifo_size = fifo_size
        self.fifo = StreamWindow(stream=self.ser, buffer_size=fifo_size, debug=debug)
        self.timeout_cached = None  # Don't write to Pyserial.Serial.timeout unless we actually change the timeout value.
                                    # to avoid extra control traffic on USB on SAMD M0+ micros.
        self.debug = debug
        if junk_bytes_dump is None:
            # By default, discard junk bytes.
            def trash(junk_bytes):
                return
            self.dump = trash
        else:
            self.dump = junk_bytes_dump
    def _advance_fifo_to_SOP(self):
        '''Search through the FIFO buffer for the first occurrence of Start of Packet.
        For example, if the first byte is 'L' and the second is 'T', we need to handle
        the following cases of FIFO content:
        
               |<-- FIFO head       ----> FIFO tail
        Case 1: {0 or more non-SOP bytes}LT{0 or more bytes of any kind}
        Case 2: {0 or more non-SOP bytes}L
        Case 3: {0 or more non-SOP bytes}'''
        psbl_SOP_position = self.fifo.find(bobbytalk.packet.START_OF_PACKET_BYTEARRAY)
        if psbl_SOP_position > -1:
            read_how_many = psbl_SOP_position   # Case 1
        elif len(self.fifo) > 0 and self.fifo[-1] == bobbytalk.packet.START_OF_PACKET_HIGH_BYTE:
            read_how_many = len(self.fifo)-1    # Case 2
        else:
            read_how_many = len(self.fifo)      # Case 3
            self.fifo.peek(read_how_many+1)     #    Try to read new bytes into the FIFO.
        if read_how_many > 0:
            self.dump(self.fifo.read(read_how_many)) # Advance stream position if needed.
        return read_how_many
    def send_packet(self, src_id, dest_id, buffer):
        '''Returns immediately indicating SUCCESS (True) or FAIL (False).
           Returns SUCCESS if buffer successfully sent to the
           underlying interface.
           Otherwise FAIL, meaning the underlying interface
           couldn't accept buffer for some reason.'''
        pktbytes = bobbytalk.packet(src_id=src_id, dest_id=dest_id, length=len(buffer), data=buffer, crc=None).to_byte_array()
        result = bool(self.ser.write(pktbytes) == len(pktbytes))
        # self.ser.flush()
        if self.debug:
            bufstr = " ".join([hex(byte) for byte in bytearray(buffer)])
            print(f">>>>> send(buffer = {bufstr}) returned {result}")
        return result
    def recv_packet(self, dest_id, timeout, src_id=None, receive_tries=8):
        '''Blocks for up to timeout waiting for packet matching dest_id
           and optionally src_id, continuing to receive and dispatch other
           incoming packets.
           Upon success, returns a bobbytalk_packet object.
           Upon timeout, returns None.'''
        # Stuff we'll use from Python's standard library.
        from numbers import Real
        from struct import unpack_from, unpack
        import time
        # Sanity check arguments.
        assert isinstance(dest_id, int) and dest_id >= 0 and dest_id < 2**16
        assert isinstance(timeout, Real) and timeout >= 0
        assert src_id is None or (src_id >= 0 and src_id < 2**16)
        assert isinstance(receive_tries, int)
        # Actual receive logic begins here.
        tquit = time.time() + timeout  # Know when to give up trying to receive packets.
        new_ser_timeout = timeout / receive_tries
        if new_ser_timeout != self.timeout_cached:
            self.ser.timeout = new_ser_timeout  # How regularly to read from underlying stream.
            self.timeout_cached = new_ser_timeout
        result = None  # Default return value if we can't find a packet.
        for trynum in range(receive_tries):
            if time.time() >= tquit:
                # We used up too much time trying to parse a packet at this stream position,
                self.dump(self.fifo.read(1)) # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                break                        # and return None to the caller.
            # INITIAL READ / SEARCH FOR START OF PACKET.
            possible_hdr_bytes = self.fifo.peek(num=bobbytalk.packet.HEADER_SIZE)
            # If Start of Packet bytes aren't at our current stream position,
            # try to seek forward and consume bytes until they are.
            if self._advance_fifo_to_SOP() > 0:
                # No Start of Packet here so we advanced to the next possible one.
                possible_hdr_bytes = self.fifo.peek(num=bobbytalk.packet.HEADER_SIZE)
            # IF WE HAVE ENOUGH BYTES FOR A HEADER, PARSE THEM.
            if len(possible_hdr_bytes) < bobbytalk.packet.HEADER_SIZE:
                # Wasn't able to read in a full header.
                continue  # Try to read more bytes if we still have time.
            psbl_sop, psbl_src, psbl_dest, psbl_length = unpack(">HHHH", possible_hdr_bytes)
            # VERIFY START OF PACKET MARKER BYTES.
            if psbl_sop != bobbytalk.packet.START_OF_PACKET:
                self.dump(self.fifo.read(1)) # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                continue                     # and retry parsing.
            # TRY TO READ IN THE ENTIRE PACKET, taking no longer than (timeout/receive_tries).
            possible_packet_length = bobbytalk.packet.HEADER_SIZE + psbl_length + bobbytalk.packet.CRC_SIZE
            possible_packet = self.fifo.peek(possible_packet_length)
            if len(possible_packet) < possible_packet_length:
                # Didn't read enough bytes for the full alleged packet,
                continue  # so try reading in more bytes if there's time left.
            # CHECK THE CRC.
            calcd_crc = bobbytalk.packet.crc16(possible_packet[:-bobbytalk.packet.CRC_SIZE])
            (rcvd_crc,) = unpack(">H", possible_packet[-bobbytalk.packet.CRC_SIZE:])
            if calcd_crc != rcvd_crc:        # BAD CRC,
                self.dump(self.fifo.read(1)) # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                continue                     # and retry parsing.
            # ALL CHECKS PASS. VALID PACKET.
            result = self.fifo.read(possible_packet_length)  # Consume the packet from the stream.
            if dest_id != psbl_dest or (src_id != None and src_id != psbl_src):
                print("*" * 78)
                print("TODO: Implement dispatch table for non-matching packets.")
                print(f"      Want dest_id {dest_id:04x}, got {psbl_dest:04x}")
                srcstr = f"{src_id:04x}" if src_id is not None else "ANY"
                print(f"      Want src_id {srcstr}, got {psbl_src:04x}")
                print("*" * 78)
            break  # for trynum in range(receive_tries)  # Return packet as result.
        else:  # for trynum in range(receive_tries)
            # Ran out of receive tries and still couldn't fetch a full packet
            # at this stream position. Give up, consume 1 byte, and if necessary,
            # advance the stream to next SOP.
            self.dump(self.fifo.read(1))
            self._advance_fifo_to_SOP()
        # End of receive logic. All returning of results to the caller happens below:
        if result is None:
            return None
        else:
            # result is a string of bytes containing a valid packet,
            # so let's create and return a bobbytalk.packet object with the parsed bytes.
            packet = bobbytalk.packet(src_id=psbl_src, dest_id=psbl_dest,
                                    length=len(result)-bobbytalk.packet.HEADER_SIZE-bobbytalk.packet.CRC_SIZE,
                                    data=result[bobbytalk.packet.HEADER_SIZE:-bobbytalk.packet.CRC_SIZE],
                                    crc=rcvd_crc)
            return packet
    def handle_comms(self):
        '''Call this periodically to receive packets from the serial line
           and dispatch to any registered packet handlers ("modules") in
           the module_table.'''
        raise NotImplementedError("Subclass must implement this.")
    def register_handler(self, dest_id, handler_function):
        '''Sets the handler function for received packets with dest_id.
           handler_function will be called like this:
           handler_function(bobbytalk_packet)'''
        raise NotImplementedError("Subclass must implement this.")
'''below are the specific cases of the twi interface'''
class interface_twi_dummy(interface_twi, twi_interface.i2c_dummy):
    def __init__(self,delay,**kwargs):
        twi_interface.i2c_dummy.__init__(self,delay,**kwargs)
        interface_twi.__init__(self,'interface_twi_dummy @ fake')
class interface_twi_mdump(interface_twi, twi_interface.mem_dict):
    def __init__(self,data_source=None,**kwargs):
        # twi_interface.mem_dict.__init__(self,data_source,**kwargs) #happens through super() below
        kwargs['data_source'] = data_source
        interface_twi.__init__(self,'interface_twi_dummy @ fake', **kwargs)
class interface_twi_scpi(twi_interface.i2c_scpi, interface_twi):
    def __init__(self, interface_serial, timeout):
        super().__init__(interface_serial)
        # twi_interface.i2c_scpi.__init__(self, interface_serial)
        # interface_twi.__init__(self,'interface_twi_scpi @ {}'.format(interface_serial))
        self.timeout = timeout
class interface_twi_scpi_sp(twi_interface.i2c_scpi_sp, interface_twi):
    def __init__(self, interface_serial, portnum, sclpin, sdapin, pullup_en=False, timeout=1):
        super().__init__(interface_serial, portnum, sclpin, sdapin, pullup_en)
        # twi_interface.i2c_scpi_sp.__init__(self, interface_serial, portnum, sclpin, sdapin, pullup_en)
        # interface_twi.__init__(self,'interface_twi_scpi @ {}'.format(interface_serial))
        self.timeout = timeout
class interface_twi_scpi_testhook(twi_interface.i2c_scpi_testhook, interface_twi):
    def __init__(self, interface_serial, timeout):
        twi_interface.i2c_scpi.__init__(self, interface_serial)
        interface_twi.__init__(self,f'interface_twi_scpi @ {interface_serial}') 
        self.timeout = timeout
class interface_twi_dc590_serial(twi_interface.i2c_dc590, interface_twi): #DJS TODO: fix interfaces to reconcile with DC590 cleanup
    def __init__(self, interface_serial, timeout):
        twi_interface.i2c_dc590.__init__(self, interface_serial) #DJS TODO: fix interfaces to reconcile with DC590 cleanup
        interface_twi.__init__(self,f'interface_twi_dc590_serial @ {interface_serial}') 
        self.timeout = timeout
class interface_twi_buspirate(twi_interface.i2c_buspirate, interface_twi):
    def __init__(self, interface_serial, timeout):
        twi_interface.i2c_buspirate.__init__(self, interface_serial)
        interface_twi.__init__(self,f'interface_twi_buspirate @ {interface_serial}') 
        self.timeout = timeout
class interface_twi_firmata(twi_interface.i2c_firmata, interface_twi):
    # Old. Consider Telemetrix instead.
    def __init__(self, firmata_instance):
        twi_interface.i2c_firmata.__init__(self, firmata_instance)
        interface_twi.__init__(self,f'interface_twi_firmata @ {firmata_instance}')
class interface_twi_bobbytalk(twi_interface.i2c_bobbytalk, interface_twi):
    def __init__(self, bobbytalk_interface, src_id, **kwargs):
        twi_interface.i2c_bobbytalk.__init__(self, bobbytalk_interface, src_id, **kwargs)
        interface_twi.__init__(self, name='interface_twi_bobytalk')
class interface_labcomm_raw_serial(interface):
    '''Sends and receives Labcomm packets over a raw serial interface.'''
    def __init__(self, raw_serial_interface, serial_port_name, src_id, dest_id):
        interface.__init__(self, f'interface_raw_serial @ {serial_port_name}')
        self.interface = raw_serial_interface
        self.src_id = src_id
        self.dest_id = dest_id
        self.talker = labcomm.labcomm_packet()
        self.parser = labcomm.labcomm_parser(raw_serial_interface)
    def set_source_id(self, src_id):
        self.src_id = src_id
    def set_destination_id(self, dest_id):
        self.dest_id = dest_id
    def send_payload(self, payload):
        self.interface.write_raw(self.talker.assemble(source=self.src_id, destination=self.dest_id, payload=payload))
    def receive_packet(self):
        return self.parser.read_message()
class interface_labcomm_twi_serial(twi_interface.i2c_labcomm, interface_twi):
    def __init__(self, raw_serial_interface, comport_name, src_id, dest_id):
        twi_interface.i2c_labcomm.__init__(self, raw_serial_interface)
        interface_twi.__init__(self, name='interface_labcomm_twi_port')
        self.interface = raw_serial_interface
        self.src_id = src_id
        self.dest_id = dest_id
        self.talker = labcomm.labcomm_packet()
        self.parser = labcomm.labcomm_parser(raw_serial_interface)
    def set_source_id(self, src_id):
        self.src_id = src_id
    def set_destination_id(self, dest_id):
        self.dest_id = dest_id
'''SPI interfaces'''
class interface_spi_dummy(interface_spi, spi_interface.spi_dummy):
    def __init__(self, delay=0):
        spi_interface.spi_dummy.__init__(self, delay)
        interface_spi.__init__(self, 'interface_spi_dummy @ fake')
class interface_spi_dc590(interface_spi, spi_interface.spi_dc590):
    def __init__(self, interface_stream, ss_ctrl=None):
        spi_interface.spi_dc590.__init__(self, interface_stream, ss_ctrl)
        interface_spi.__init__(self, f'interface_spi_dc590 @ {interface_stream}')
class interface_spi_cfgpro(interface_spi, spi_interface.spi_cfgpro):
    def __init__(self, visa_interface, CPOL, CPHA, baudrate=1e6, ss_ctrl=None):
        spi_interface.spi_cfgpro.__init__(self, visa_interface, CPOL, CPHA, baudrate, ss_ctrl)
        interface_spi.__init__(self, f'interface_spi_cfgpro @ {visa_interface}')
class gpib_adapter(communication_node):
    pass
class gpib_adapter_visa(gpib_adapter):
    pass

class interface_factory(communication_node):
    '''The interface factory is a wrapper class that creates interfaces and the instruments inheriting from "communication_node", that they pass on to channels.
    
    Interfaces acquired through the interface factory have a notion of a "parent" which traces back to the physical port of the computer.
    The parent feature allows the user to request multiple interfaces from the factory without regard for possible collisions that may occur with multiple endpoints talking through the same physical channel (e.g. COM port, USB port, etc.).

    PyICe will ensure that channels that trace back to a common parent, with a common underlying hardware pointer, will be singulated serially within the threading (during logging for instance) such that all channels will be read sequentially with possibility of a collision in time.
    
    It should be clear from this that all requests for a physical interface should be made from the interface factory itself using these "get_xxx" methods rather than reaching around and grabbing raw interface handles directly. If you do that, you are on your own and PyICe won't help you with interface threading problems.
    
    This class ventures to be smart about the interfaces and to simplify their creation.
    Its purpose is also to encourage portable code, and to remove some low level responsibilities from the instruments.
    
    There are two use models that can be adopted:

    1) An interface_factory can be instantiated and all interfaces acquired from it using the getter methods. Lab instrument objects, created from the lab_instruments folder, then get their interface handles from interfaces acquired from the interface factory object. These instruments are then usually added to a lab core channel_master for channel aggregation.

    2) Alternatley, the project can go straight to creating a lab_core master (not channel_master). A lab_core master is merely a channel_master that inherits this interface_factory class. In this work flow, interfaces can be acquired from that master object directly (again using the getter methods in this class) without the requirement to create a disposable interface_factory instance. This method results in slightly compacted code but has an interface object flow that seems to double back on itself.
    '''
    _instantiated = False
    def __init__(self):
        communication_node.__init__(self)
        if self._instantiated == True:
            raise Exception("PyICe lab_interfaces: It's only appropriate to create one instance of an interface_factory. There already seems to be at least one.")
        self._instantiated = True
        self.set_com_node_thread_safe()
        #since there is only one visa
        if not visaMissing:
            self._visa_root = communication_node()
            self._visa_root.set_com_node_parent(self)
            self._visa_root.set_com_node_thread_safe() #visa is thread safe
        self._gpib_adapters = {} # communication_node indexed by adapter_number
        self._gpib_interfaces = {} #indexed by adapter number and address
        self._raw_serial_interfaces = []
        self._direct_visa_interfaces = []
        self._vxi11_interfaces = []
        self._usbtmc_interfaces = []
        self._visa_serial_interfaces = []
        self._tcp_ip_interfaces = []
        self._telnet_interfaces = []
        self._default_timeout = 2
    def get_visa_interface(self,visa_address_string,timeout=None):
        if visaMissing:
            raise Exception("pyVisa or VISA is missing on this computer, install one or both")
        if visa_address_string.lower().startswith('gpib'):
            print('\n\n\n\n\nDo not add gpib over visa directly for compatability with non visa framwork iterfaces')
            print(' for example replace: ')
            print('       .create_visa_interface("GBPIB0::5")')
            print(' with:')
            print('       .set_gpib_adapter_visa(0) # this can only be done once for 0')
            print('       .create_visa_gpib_interface(gpib_adapter_number=0,gpib_address_number=5)')
            raise Exception('User Error - see above text')
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_direct(visa_address_string,timeout)
        new_interface.set_com_node_parent(self._visa_root)
        self._direct_visa_interfaces.append(new_interface)
        return new_interface
    def get_visa_gpib_interface(self,gpib_adapter_number,gpib_address_number,timeout=None):
        timeout = self._set_timeout(timeout)
        if gpib_adapter_number not in list(self._gpib_adapters.keys()):
            print(f'\n\n\n\nAdapter number "{gpib_adapter_number}" not found in adapter list')
            print(f'It must be added first with .set_gpib_adapter_visa*({gpib_adapter_number},*)')
            print(f' for example:')
            print(f'       .set_gpib_adapter_visa({gpib_adapter_number})')
            raise Exception('Using undefined gpib adapter')
        #search for an existing gpib_interface
        if gpib_adapter_number in self._gpib_interfaces:
            if gpib_address_number in self._gpib_interfaces[gpib_adapter_number]:
                interface = self._gpib_interfaces[gpib_adapter_number][gpib_address_number]
                if timeout > interface.timeout:
                    interface.timeout = timeout
                return interface
        #determine the type of gpib adapter
        this_gpib_adapter = self._gpib_adapters[gpib_adapter_number]
        assert isinstance(this_gpib_adapter, gpib_adapter)
        new_interface = self._get_gpib_interface(gpib_adapter=this_gpib_adapter, gpib_adapter_number=gpib_adapter_number, gpib_address_number=gpib_address_number, timeout=timeout)
        new_interface.set_com_node_parent(this_gpib_adapter)
        self._gpib_interfaces[gpib_adapter_number][gpib_address_number] = new_interface
        return new_interface
    def _get_gpib_interface(self, gpib_adapter, gpib_adapter_number, gpib_address_number, timeout):        
        if isinstance(gpib_adapter, gpib_adapter_visa):
            visa_address_string = f"GPIB{gpib_adapter_number}::{gpib_address_number}"
            new_interface = interface_visa_direct(visa_address_string,timeout)
        else:
            raise Exception(f"{self._get_gpib_interface} received unexpected/unimplemented gpib_adapter argument of type {type(gpib_adapter)}.")
        return new_interface
    def get_visa_tcp_ip_interface(self,host_address,port,timeout=None,**kwargs):
        new_interface = interface_visa_tcp_ip(host_address,port,timeout,**kwargs)
        new_interface.set_com_node_parent(self)
        self._tcp_ip_interfaces.append(new_interface)
        return new_interface
    def get_visa_telnet_interface(self,host_address,port,timeout=None):
        if telnetlibMissing:
            raise Exception("telnetlib is missing on this computer")
        new_interface = interface_visa_telnet(host_address,port,timeout)
        new_interface.set_com_node_parent(self)
        self._telnet_interfaces.append(new_interface)
        return new_interface
    def get_visa_vxi11_interface(self,address,timeout):
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_vxi11(address,timeout)
        new_interface.set_com_node_parent(self)
        self._vxi11_interfaces.append(new_interface)
        return new_interface
    def get_visa_usbtmc_interface(self,address,timeout):
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_usbtmc(address,timeout)
        new_interface.set_com_node_parent(self)
        self._usbtmc_interfaces.append(new_interface)
        return new_interface
    def get_visa_serial_interface(self, serial_obj_or_port_name, baudrate=None, timeout=None, **kwargs):
        timeout = self._set_timeout(timeout)
        if isinstance(serial_obj_or_port_name, str):
            rawser = self.get_raw_serial_interface(serial_obj_or_port_name, baudrate, timeout, **kwargs)
        elif isinstance(serial_obj_or_port_name, interface_raw_serial):
            rawser = serial_obj_or_port_name
        new_interface = interface_visa_serial(rawser)
        new_interface.set_com_node_parent(rawser)
        self._visa_serial_interfaces.append(new_interface)
        return new_interface
    def get_raw_serial_interface(self,serial_port_name,baudrate=None,timeout=None,**kwargs):
        if serialMissing:
            raise Exception("pySerial is missing on this computer")
        timeout = self._set_timeout(timeout)
        for interface in self._raw_serial_interfaces:
            if interface.get_serial_port_name() == serial_port_name:
                if (baudrate != interface.baudrate) and (baudrate is not None):
                    raise Exception(f"Tried to create a second connection to serial port {serial_port_name} with different baudrate")
                if timeout > interface.timeout:
                    interface.timeout = timeout #auto extend time outs
                return interface
        new_interface = interface_raw_serial(serial_port_name,baudrate,timeout,**kwargs)
        new_interface.set_com_node_parent(self)
        #serial ports as we use them are not thread safe and never will be
        self._raw_serial_interfaces.append(new_interface)
        return new_interface
    def get_tcp_serial_interface(self, dest_ip_address, dest_tcp_portnum, timeout):
        if serialMissing:
            raise Exception("pySerial is missing on this computer")
        timeout = self._set_timeout(timeout)
        new_interface = interface_tcp_serial(dest_ip_address, dest_tcp_portnum)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_interface_test_harness_serial(self,serial_port_name,bytestream,timeout=1.0,max_bytes_returned_per_read=7):
        '''Get a PyICified SerialTestHarness, a hardware-free PySerial serial.Serial
        emulator that provides a read() method and a writable timeout property.
        bytestream is a generator function that yields one byte
        of test stimulus each time its next() method is called.'''
        timeout = self._set_timeout(timeout)
        new_interface = interface_test_harness_serial(serial_port_name,bytestream,max_bytes_returned_per_read)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_interface_libusb(self, idVendor=0x1272, idProduct=0x8004, timeout=1):
        new_interface = interface_libusb(idVendor=0x1272, idProduct=0x8004, timeout = 1)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_interface_stream_serial(self, interface_raw_serial):
        new_interface = interface_stream_serial(interface_raw_serial)
        new_interface.set_com_node_parent(interface_raw_serial)
        return new_interface
    def get_interface_ftdi_d2xx(self):
        new_interface = interface_ftdi_d2xx() #need some kind of device descriptor....
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_twi_dummy_interface(self,delay=0,timeout=None,**kwargs):
        new_interface = interface_twi_dummy(delay,**kwargs)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_twi_mdump_interface(self,data_source,**kwargs):
        new_interface = interface_twi_mdump(data_source,**kwargs)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_twi_scpi_interface(self,serial_port_name,baudrate=None,timeout=None):
        serial = self.get_visa_serial_interface(serial_port_name,baudrate,timeout)
        new_interface = interface_twi_scpi(serial,timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface
    def get_twi_scpi_sp_interface(self,serial_port_name,portnum,sclpin,sdapin,pullup=False,baudrate=None,timeout=None):
        serial = self.get_visa_serial_interface(serial_port_name,baudrate,timeout)
        new_interface = interface_twi_scpi_sp(interface_serial=serial,portnum=portnum,sclpin=sclpin,sdapin=sdapin,pullup_en=pullup,timeout=timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface
    def get_twi_scpi_testhook_interface(self,serial_port_name,baudrate=None,timeout=None):
        serial = self.get_visa_serial_interface(serial_port_name,baudrate,timeout)
        new_interface = interface_twi_scpi_testhook(serial,timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface 
    def get_twi_dc590_serial(self,serial_port_name,baudrate=None,timeout=None):
        if baudrate is None:
            baudrate = 115200 #DC590/Linduino default
        serial = self.get_raw_serial_interface(serial_port_name,baudrate,timeout)
        stream = self.get_interface_stream_serial(serial)
        new_interface = interface_twi_dc590_serial(stream,timeout)
        new_interface.set_com_node_parent(stream)
        return new_interface
    def get_twi_buspirate_interface(self,serial_port_name,baudrate=None,timeout=None):
        serial = self.get_raw_serial_interface(serial_port_name,baudrate,timeout)
        new_interface = interface_twi_buspirate(serial,timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface
    def get_twi_kernel_interface(self,bus_number):
        new_interface = interface_twi_kernel(bus_number)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_twi_firmata_interface(self,firmata_instance):
        # Old. Consider Telemetrix instead.
        new_interface = interface_twi_firmata(firmata_instance)
        new_interface.set_com_node_parent(self)
        return new_interface
    def get_twi_bobbytalk_raw_serial(self,serial_port_name,src_id,baudrate=None,
                                   fifo_size=16*(2**16), debug=False, **kwargs):
        '''serial_port_name:  "COM27" or "/dev/ttyS01", for example.
           src_id: 16-bit integer to use as the default source ID in outgoing bobbytalk packets.
           baudrate: sets the serial link baudrate.
           fifo_size: sets the size, in bytes, of the FIFO used to buffer packets
                      coming in over the serial link for packet validation, parsing , and dispatch.
           **kwargs: All other keyword arguments are passed to the twi_interface.i2c_bobbytalk constructor,
                     allowing optional settings like dest_id (defaults to 0x0020 SMBUS module),
                     recv_timeout, cmd_retries, per_cmd_recv_retries...
            For testing purposes, if a lab_interface.interface object is passed as the serial_port_name
            argument, it will be used as if it were a PySerial serial.Serial object. This allows
            injection of test bytes and other stimuli to the bobbytalk parser.'''
        if baudrate is None:
            baudrate = 115200 # bobbytalk Firmware default
        if isinstance(serial_port_name, str):
            raw_serial_intf = self.get_raw_serial_interface(serial_port_name, baudrate)
        elif isinstance(serial_port_name, interface):
            # testhook: allows interface_test_harness_serial
            raw_serial_intf = serial_port_name
        else:
            raise ValueError(f"lab_interfaces.get_twi_bobbytalk_raw_serial() called with "
                             f"first argument {repr(serial_port_name)}{type(serial_port_name)},\nwhich is neither "
                             "a (Unicode string) name of a serial port, nor an interface object")
        lc_intf = interface_bobbytalk_raw_serial(raw_serial_intf, fifo_size=fifo_size, debug=debug)
        lc_intf.set_com_node_parent(raw_serial_intf)
        twi_intf = interface_twi_bobbytalk(lc_intf, src_id, debug=debug, **kwargs)
        twi_intf.set_com_node_parent(lc_intf)
        return twi_intf       
    def get_twi_bobbytalk_tcp(self, dest_ip_address, dest_tcp_portnum, src_id, timeout=0.3,
                            fifo_size=16*(2**16), debug=False, **kwargs):
        '''Talk bobbytalk over TCP/IP given a destination IP address and TCP port number.
           Uses PySerial's "socket://" feature to open a TCP/IP socket.
           dest_ip_address:  "127.0.0.1" or "10.15.127.127", for example.
           dest_tcp_portnum:  65500, for example.
           src_id: 16-bit integer to use as the default source ID in outgoing bobbytalk packets.
           timeout: how long to wait on read or write requests before returning failure
           fifo_size: sets the size, in bytes, of the FIFO used to buffer packets
                      coming in over the serial link for packet validation, parsing , and dispatch.
           **kwargs: All other keyword arguments are passed to the twi_interface.i2c_bobbytalk constructor,
                     allowing optional settings like dest_id (defaults to 0x0020 SMBUS module),
                     recv_timeout, cmd_retries, per_cmd_recv_retries...
            For testing purposes, if a lab_interface.interface object is passed as the dest_ip_address
            argument, it will be used as if it were a PySerial serial.Serial object, and the dest_tcp_portnum
            is ignored. This allows injection of test bytes and other stimuli to the bobbytalk parser.'''
        if isinstance(dest_ip_address, str):
            serial_intf = self.get_tcp_serial_interface(dest_ip_address, dest_tcp_portnum, timeout)
        elif isinstance(dest_ip_address, interface):
            # testhook: allows interface_test_harness_serial
            serial_intf = dest_ip_address
        lc_intf = interface_bobbytalk_raw_serial(serial_intf, fifo_size=fifo_size, debug=debug)
        lc_intf.set_com_node_parent(serial_intf)
        twi_intf = interface_twi_bobbytalk(lc_intf, src_id, debug=debug, **kwargs)
        twi_intf.set_com_node_parent(lc_intf)
        return twi_intf
    def get_labcomm_raw_interface(self, comport_name, src_id, dest_id, baudrate, timeout):
        rawser = self.get_raw_serial_interface(comport_name, baudrate, timeout)
        new_interface = interface_labcomm_raw_serial(rawser, comport_name, src_id, dest_id)
        new_interface.set_com_node_parent(rawser)
        return new_interface
    def get_labcomm_twi_interface(self, comport_name, src_id, dest_id, baudrate, timeout):
        rawser = self.get_raw_serial_interface(comport_name, baudrate, timeout)
        new_interface = interface_labcomm_twi_serial(rawser, comport_name, src_id, dest_id)
        new_interface.set_com_node_parent(rawser)
        return new_interface
    def get_spi_dummy_interface(self, delay=0):
        iface_spi = interface_spi_dummy(delay)
        iface_spi.set_com_node_parent(self)
        return iface_spi
    def get_spi_dc590_interface(self, serial_port_name, uart_baudrate=None, uart_timeout=None, ss_ctrl=None, **kwargs):
        if uart_baudrate is None:
            uart_baudrate = 115200 #DC590/Linduino default
        iface_serial = self.get_raw_serial_interface(serial_port_name,baudrate=uart_baudrate,timeout=uart_timeout,**kwargs)
        iface_stream = self.get_interface_stream_serial(iface_serial)
        iface_spi = interface_spi_dc590(iface_stream, ss_ctrl)
        iface_spi.set_com_node_parent(iface_serial)
        return iface_spi
    def get_spi_cfgpro_interface(self, serial_port_name, uart_timeout=None, CPOL=0, CPHA=0, spi_baudrate=1e6, ss_ctrl=None):
        '''The configurator Pro (or XT) is an ADI specific breakout board that interfaces test equipment and ICs in a semi-standardized manner.'''
        iface_visa_serial = self.get_visa_serial_interface(serial_port_name,timeout=uart_timeout)
        iface_spi = interface_spi_cfgpro(iface_visa_serial, CPOL, CPHA, spi_baudrate, ss_ctrl)
        iface_spi.set_com_node_parent(iface_visa_serial)
        return iface_spi
    def get_dummy_interface(self,parent=None,name='dummy interface'):
        '''used only for testing the core lab functions'''
        new_interface = interface(name)
        if parent is None:
            new_interface.set_com_node_parent(self)
        else:
            new_interface.set_com_node_parent(parent)
        return new_interface
    def set_gpib_adapter_visa(self,adapter_number):
        if visaMissing:
            raise Exception("pyVisa or VISA is missing on this computer, install one or both. Cannot use visa for GPIB adapter")
        if adapter_number in list(self._gpib_adapters.keys()):
           if  self._gpib_adapters[adapter_number]._parent == self._visa_root:
               raise Exception(f"Attempting to re-define gpib adapter: {adapter_number}, the same way a second time.")
           else:
               raise Exception(f"GPIB adapter_number {adapter_number} was already defined as something other than visa.") 
        gpib_adapter = gpib_adapter_visa()
        gpib_adapter.set_com_node_thread_safe()
        gpib_adapter.set_com_node_parent(self._visa_root)
        self._gpib_adapters[adapter_number] = gpib_adapter
        if adapter_number not in self._gpib_interfaces:
            self._gpib_interfaces[adapter_number] = {}
    def _set_timeout(self,timeout):
        if timeout == None:
            return self._default_timeout
        else:
            return timeout
if __name__ == "__main__":
    c_root = communication_node()
    c_root.set_com_node_thread_safe(True)
    c_a = communication_node()
    c_a.set_com_node_thread_safe(False)
    c_a.set_com_node_parent(c_root)
    c_b = communication_node()
    c_b.set_com_node_thread_safe(True)
    c_b.set_com_node_parent(c_root)
    c_c = communication_node()
    c_c.set_com_node_thread_safe(False)
    c_c.set_com_node_parent(c_root)
    c_ca = communication_node()
    c_ca.set_com_node_thread_safe()
    c_ca.set_com_node_parent(c_c)
    c_cb = communication_node()
    c_cb.set_com_node_thread_safe()
    c_cb.set_com_node_parent(c_c)
    '''
    print c_root.com_node_get_all_descendents()
    print 'thread groups'
    for i in  c_root.group_com_nodes_for_threads():
        print '--------------------'
        print i
    '''    
    print('filtered')
    for i in  c_root.group_com_nodes_for_threads_filter([c_b,c_a,c_ca,c_cb]):
        print('--------------------')
        print(i)
