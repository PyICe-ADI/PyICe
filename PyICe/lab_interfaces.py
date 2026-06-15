"""Physical Communication Interfaces Hierarchy Manager.

===================================================
Required for multithreaded communication.

>>> from PyICe.lab_interfaces import strify

"""
import time
import random
import array
from collections import OrderedDict
import logging
import multiprocessing
from . import visa_wrappers
from . import spi_interface
from . import twi_interface
from .lab_utils.StreamWindow import StreamWindow
import labcomm
import abc
try:
    import pyvisa  # noqa: F401 # pylint: disable=import-error; optional dependency guarded by try/except
    visaMissing = False
except BaseException:
    visaMissing = True
try:
    import serial  # pylint: disable=import-error; optional dependency guarded by try/except
    serialMissing = False
except BaseException:
    serial = None  # type: ignore[assignment]
    serialMissing = True
try:
    import vxi11  # noqa: F401 # pylint: disable=import-error; optional dependency guarded by try/except
    vxi11Missing = False
except BaseException:
    vxi11Missing = True
try:
    import usbtmc  # noqa: F401 # pylint: disable=import-error; optional dependency guarded by try/except
    usbtmcMissing = False
except BaseException:
    usbtmcMissing = True
try:
    import telnetlib  # noqa: F401 # pylint: disable=import-error; optional dependency guarded by try/except
    telnetlibMissing = False
except BaseException:
    telnetlibMissing = True
try:
    from . import bobbytalk
except ImportError:
    bobbytalk = None  # type: ignore[assignment]
'''
Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
'''
STR_ENCODING = 'latin-1'


def strify(bs):
    """Convert a bytes-like object to a str using latin-1 encoding.

    Used throughout PyICe to decode instrument responses from bytes to Python 3
    unicode strings.  Latin-1 is a lossless round-trip encoding for byte values
    0x00–0xFF, so no instrument data is lost in the conversion.

    >>> strify(b'hello')
    'hello'
    >>> strify(b'\\xff\\x00\\x80')  # arbitrary byte values survive
    '\\xff\\x00\\x80'
    >>> strify('already a string')  # passes through with a warning
    Unexpected stringification of non-byte string: already a string. Contact PyICe-developers@analog.com for more information.
    'already a string'

    Args:
        bs: Bytes or bytearray to decode into a str.

    Returns:
        The decoded string, or the original value if it was already a str.
    """
    if not isinstance(bs, str):
        return bs.decode(STR_ENCODING)
    else:
        print(
            f"Unexpected stringification of non-byte string: {bs}. Contact PyICe-developers@analog.com for more information.")
        return bs


def byteify(s):
    """Convert a str to bytes using latin-1 encoding.

    Used throughout PyICe to encode SCPI command strings into bytes for
    transmission over serial, TCP, or USB interfaces.  Latin-1 preserves
    the full 0x00–0xFF code-point range byte-for-byte.

    >>> byteify('hello')
    b'hello'
    >>> byteify('\\xff\\x00\\x80')  # code points map 1:1 to byte values
    b'\\xff\\x00\\x80'
    >>> byteify(b'already bytes')  # passes through with a warning
    Unexpected byteification of byte string: b'already bytes'. Contact PyICe-developers@analog.com for more information
    b'already bytes'

    Args:
        s: String to encode into bytes.

    Returns:
        The encoded bytes, or the original value if it was already bytes.
    """
    if isinstance(s, str):
        return s.encode(STR_ENCODING)
    else:
        print(
            f"Unexpected byteification of byte string: {s}. Contact PyICe-developers@analog.com for more information")
        return s


str_log_dict = OrderedDict()
# visa wrappers should probably go away and get merged in here

try:
    import usb.core  # pylint: disable=import-error; optional dependency guarded by try/except
    ubsMissing = False
except BaseException:
    usb = None  # type: ignore[assignment]
    ubsMissing = True
debug_logging = logging.getLogger(__name__)
# logfile_handler = logging.FileHandler(filename="lab_interfaces.debug.log", mode="w")
# debug_logging.addHandler(logfile_handler)
warn = debug_logging.warning


class communication_node(object):
    """Map a tree of communication resources to instrument channels.

    Each node tracks a parent interface and child interfaces, forming a
    hierarchy that mirrors the physical wiring (e.g. USB hub → GPIB adapter →
    instrument).  This tree lets PyICe group channels that share a non-thread-safe
    ancestor so they are accessed sequentially within a single thread during

    >>> from PyICe.lab_interfaces import communication_node
    >>> communication_node is not None
    True

    concurrent data collection."""

    def __init__(self, *args, **kwargs):
        """Initialize the communication node with no parent and an unlocked state.

        This constructor should never be called with explicit arguments because
        ``communication_node`` is silently mixed in via multiple inheritance.
        Any positional or keyword arguments are forwarded to the next class in
        the MRO so that cooperative multiple inheritance works correctly.


        >>> from PyICe.lab_interfaces import communication_node
        >>> communication_node is not None
        True

        Args:
            *args: Positional arguments forwarded to the super().__init__.
            **kwargs: Keyword arguments forwarded to the super().__init__.
        """
        super().__init__(*args, **kwargs)
        self._parent = None
        self._thread_safe = False
        self._children = []
        self._lock = multiprocessing.RLock()

    def debug_com_nodes(self, indent=""):
        """Print the communication-node tree to stdout for debugging.

        Recursively walks child nodes, indenting each level to visualise the
        parent/child hierarchy and thread-safety flags.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'debug_com_nodes')
        True

        Args:
            indent: Whitespace prefix for the current depth level.
        """
        print(
            f'{indent}{self}, child of {self._parent}. Thread_safe: {self._thread_safe}')
        for child in self._children:
            child.debug_com_nodes(indent=f"{indent}    ")

    def get_com_parent(self):
        """Return this node's parent communication node.
        Returns the stored com parent value from the object's internal state.
        Returns the stored com parent from the object's internal state.

        Returns the stored com parent from the object's internal state.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'get_com_parent')
        True

        Returns:
            The parent ``communication_node``, or ``None`` if this is the root.
        """
        return self._parent

    def set_com_node_parent(self, parent):
        """Assign a parent node and register this node as one of its children.

        Should only be called once per node.  Prints a warning if the parent
        is being changed after initial assignment.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'set_com_node_parent')
        True

        Args:
            parent: The ``communication_node`` that physically owns this interface.
        """
        if self._parent:
            print("warning: changing a communication_node parent")
        self._parent = parent
        self._parent.com_node_register_child(self)

    def set_com_node_thread_safe(self, safe=True):
        """Mark this communication node as thread-safe or thread-unsafe.

        Thread-safe nodes (e.g. a VISA library with its own locking) allow
        their children to be accessed concurrently from different threads.
        Thread-unsafe nodes force all descendants into the same thread group.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'set_com_node_thread_safe')
        True

        Args:
            safe: ``True`` if concurrent access through this node is safe.
        """
        self._thread_safe = safe

    def com_node_register_child(self, child):
        """Add a child node to this node's list of dependents.

        Called automatically by ``set_com_node_parent``; not typically invoked
        directly by user code.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'com_node_register_child')
        True

        Args:
            child: The ``communication_node`` to register as a child.
        """
        self._children.append(child)

    def com_node_get_root(self):
        """Walk up the parent chain and return the root communication node.

        Supports the ``communication_node`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'com_node_get_root')
        True

        Returns:
            The topmost ``communication_node`` in this hierarchy (often the
            ``interface_factory`` itself).
        """
        if self._parent:
            return self._parent.com_node_get_root()
        else:
            return self

    def com_node_get_children(self):
        """Return the immediate children of this communication node.

        Supports the ``communication_node`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'com_node_get_children')
        True

        Returns:
            A list of ``communication_node`` instances directly parented to
            this node.
        """
        return self._children

    def com_node_get_all_descendents(self):
        """Recursively collect every descendant of this node.

        Supports the ``communication_node`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'com_node_get_all_descendents')
        True

        Returns:
            A set of all ``communication_node`` instances reachable by
            walking down through children, grandchildren, etc.
        """
        descendents = set()
        for child in self.com_node_get_children():
            descendents.add(child)
            descendents = descendents.union(
                child.com_node_get_all_descendents())
        return descendents

    def group_com_nodes_for_threads(self, sets=None):
        """Partition the subtree into groups that must share a single thread.

        Thread-safe nodes create a new group for each of their children;
        thread-unsafe nodes lump themselves and all descendants into one group.
        The result drives PyICe's multithreaded data-collection scheduler.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'group_com_nodes_for_threads')
        True

        Args:
            sets: Accumulator list (used internally during recursion); pass
                ``None`` on the initial call.

        Returns:
            A list of sets, where each set contains ``communication_node``
            instances that must be accessed from the same thread.
        """
        if sets is None:
            sets = list()
        if self._thread_safe:
            sets.append(set([self]))
            for child in self.com_node_get_children():
                child.group_com_nodes_for_threads(sets)  # will modify sets
        else:
            group = self.com_node_get_all_descendents()
            group.add(self)
            sets.append(group)
        return sets

    def group_com_nodes_for_threads_filter(self, com_node_list):
        """Filter thread-grouping results to only the nodes the caller cares about.

        Given a list of interface nodes (typically the ones attached to lab
        instruments), partition them into sublists where each sublist must be
        serviced by a single thread because the members share a thread-unsafe
        ancestor.  All interfaces in *com_node_list* must trace back to the
        same root node (usually ``self``).


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'group_com_nodes_for_threads_filter')
        True

        Args:
            com_node_list: Flat list of ``communication_node`` interfaces to
                partition into thread-safe groups.

        Returns:
            A list of lists, each inner list containing nodes that must be
            accessed sequentially within one thread.

        Raises:
            Exception: If the nodes in *com_node_list* have more than one
                distinct root, indicating they were obtained from different
                ``interface_factory`` instances.
        """
        if len(set([interface.com_node_get_root()
               for interface in com_node_list])) > 1:
            print('lab_interfaces: ERROR, Too many COM node parents, either:')
            print(
                ' 1. you did not get all your interfaces from the same master or interface_factory')
            print(' 2. you did not ask for threads from the root node')
            print(' 3. you are working on the interface library and broke something')
            print("known interfaces:")
            for interface in com_node_list:
                print(f"{interface} @ {interface.com_node_get_root()}")
            raise Exception("Too many COM node parents")
        # get a list of lists for all interfaces
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
        """Acquire this node's reentrant lock, then recursively lock all ancestors.

        Locking from leaf to root ensures that no other thread can use any
        part of the shared communication path while this node is active.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'lock')
        True

        Raises:
            TypeError: If a parent node is neither a ``communication_node``
                nor ``None``, indicating a corrupted hierarchy.
        """
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
        """Release locks from the root ancestor down to this node.

        Unlocking in root-to-leaf order is the reverse of the lock-acquisition
        order, preventing deadlocks.


        >>> from PyICe.lab_interfaces import communication_node
        >>> hasattr(communication_node, 'unlock')
        True

        Raises:
            TypeError: If a parent node is neither a ``communication_node``
                nor ``None``, indicating a corrupted hierarchy.
        """
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
    """Base class for all physical communication interfaces.

    Every lab instrument ultimately communicates through a subclass of
    ``interface``.  Provides a human-readable name and a ``timeout``

    >>> from PyICe.lab_interfaces import interface
    >>> interface is not None
    True

    attribute used by transport-specific subclasses."""

    def __init__(self, name, **kwargs):
        """Initialize the interface with a descriptive name.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface
        >>> interface is not None
        True

        Args:
            name: Human-readable identifier for this interface (e.g.
                ``"interface_visa_tcp_ip @ 10.0.0.1:5025"``).
            **kwargs: Forwarded to ``communication_node.__init__`` for
                cooperative multiple-inheritance support.
        """
        assert isinstance(name, str)
        self._interface_name = name if len(name) else "nameless interface"
        # cannot use hasattr since its sometimes a property
        if "timeout" not in dir(self):
            self.timeout = None
        super().__init__(**kwargs)

    def __str__(self):
        """Return the human-readable interface name.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.


        >>> from PyICe.lab_interfaces import interface
        >>> hasattr(interface, '__str__')
        True

        Returns:
            The name string assigned at construction time.
        """
        return self._interface_name


class interface_visa(interface):
    """VISA-style (SCPI query/response) communication interface base class.

    Subclasses provide the actual transport (TCP, serial, VXI-11, etc.)
    while instrument drivers program against the common VISA read/write/query

    >>> from PyICe.lab_interfaces import interface_visa
    >>> interface_visa is not None
    True

    API."""
    pass


class interface_twi(interface):
    """I²C / SMBus (Two-Wire Interface) communication base class.

    Subclasses implement the low-level byte-transfer protocol over various

    >>> from PyICe.lab_interfaces import interface_twi
    >>> interface_twi is not None
    True

    physical adapters (DC590, Bus Pirate, SCPI-controlled GPIO, etc.)."""
    pass


class interface_spi(interface):
    """SPI (Serial Peripheral Interface) communication base class.

    Subclasses handle chip-select management and clocking over specific

    >>> from PyICe.lab_interfaces import interface_spi
    >>> interface_spi is not None
    True

    adapters (DC590, Configurator Pro, dummy for simulation)."""
    pass


class interface_bobbytalk(interface):
    """Base class for interfaces that exchange bobbytalk packets.

    Bobbytalk is an ADI-internal framed packet protocol used over serial or
    TCP links to embedded targets.  Subclasses implement the abstract methods
    for the specific transport being used.

    >>> from PyICe.lab_interfaces import interface_bobbytalk
    >>> interface_bobbytalk is not None
    True

    """
    def __init__(self, name):
        """Initialize the bobbytalk interface with a descriptive name.
        Delegates to the parent class constructor.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_bobbytalk
        >>> interface_bobbytalk is not None
        True

        Args:
            name: Human-readable label for this bobbytalk link.
        """
        super(interface_bobbytalk, self).__init__(name)

    def send_packet(self, src_id, dest_id, buffer):
        """Transmit a bobbytalk packet and return immediately.

        Transmits data to the remote endpoint.


        >>> from PyICe.lab_interfaces import interface_bobbytalk
        >>> hasattr(interface_bobbytalk, 'send_packet')
        True

        Args:
            src_id: 16-bit source address identifying this endpoint.
            dest_id: 16-bit destination address for the remote endpoint.
            buffer: Payload bytes to send inside the packet.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement this.")

    def recv_packet(self, dest_id, timeout, src_id=None):
        """Block until a packet matching *dest_id* (and optionally *src_id*) arrives.

        While waiting, other incoming packets are received and dispatched to
        registered handlers.


        >>> from PyICe.lab_interfaces import interface_bobbytalk
        >>> hasattr(interface_bobbytalk, 'recv_packet')
        True

        Args:
            dest_id: 16-bit destination address to filter incoming packets.
            timeout: Maximum seconds to wait before returning ``None``.
            src_id: Optional 16-bit source address filter; ``None`` accepts
                any source.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement this.")

    def handle_comms(self):
        """Receive and dispatch pending packets from the underlying transport.

        Call periodically to service incoming packets when not blocked in
        ``recv_packet``.


        >>> from PyICe.lab_interfaces import interface_bobbytalk
        >>> hasattr(interface_bobbytalk, 'handle_comms')
        True

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement this.")

    def register_handler(self, dest_id, handler_function):
        """Register a callback for packets arriving with a given *dest_id*.

        The *handler_function* is invoked as ``handler_function(bobbytalk_packet)``
        whenever a matching packet is received.


        >>> from PyICe.lab_interfaces import interface_bobbytalk
        >>> hasattr(interface_bobbytalk, 'register_handler')
        True

        Args:
            dest_id: 16-bit destination address that triggers this handler.
            handler_function: Callable accepting a single ``bobbytalk_packet``
                argument.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError("Subclass must implement this.")


class interface_libusb(interface):
    """Bulk transfer through LibUSB/WinUSB.

    Implementation may be overly specific to George B's Direct590 protocol and may need additional options or subclassing later.
    Transfers must be in multiples of this 64 byte payload size or will result in a babble error in the underlying library.
    Requires PyUSB: https://github.com/walac/pyusb

    >>> from PyICe.lab_interfaces import interface_libusb
    >>> interface_libusb is not None
    True

    """
    def __init__(self, idVendor, idProduct, timeout):
        """Initialize PyUSB interface.

        Requires installation of WinUSB filter driver. Use install-filter-win.exe under PyICe/deps/Direct590.
        Untested on linux; filter driver probably not required.


        >>> from PyICe.lab_interfaces import interface_libusb
        >>> interface_libusb is not None
        True

        Args:
            idProduct: Idproduct to use.
            idVendor: Idvendor to use.
            timeout: Timeout in seconds.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        interface.__init__(self, 'WinUSB Communication Interface')
        self.timeout = 1000 * timeout  # ms
        # https://github.com/walac/pyusb/blob/master/docs/tutorial.rst
        # find our device
        self.dev = usb.core.find(idVendor=idVendor, idProduct=idProduct)
        # was it found?
        if self.dev is None:
            raise ValueError(
                'LibUSB Device not found. Is filter driver installed? (see docstring)')
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        self.dev.set_configuration()
        # get an endpoint instance
        self.cfg = self.dev.get_active_configuration()
        self.intf = self.cfg[(0, 0)]
        self.ep_out = usb.util.find_descriptor(
            self.intf,  # match the first OUT endpoint
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_OUT
        )
        assert self.ep_out is not None
        self.ep_in = usb.util.find_descriptor(
            self.intf,  # match the first OUT endpoint
            custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) ==
            usb.util.ENDPOINT_IN
        )
        assert self.ep_in is not None
        # self.stream_in = ''
        # a.dev.configurations()[0].interfaces()[0].endpoints()[0].wMaxPacketSize
        self.write_packet_size = self.ep_out.wMaxPacketSize
        self.read_packet_size = self.ep_in.wMaxPacketSize
        print(self.dev)

    def read(self):
        """Read data from the endpoint.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_interfaces import interface_libusb
        >>> hasattr(interface_libusb, 'read')
        True

        Returns:
            The value read from the device or channel.
        """
        resp = self.dev.read(self.ep_in, self.read_packet_size, self.timeout)
        while len(resp) == self.read_packet_size:  # response split across packets
            resp += self.dev.read(self.ep_in,
                                  self.read_packet_size,
                                  self.timeout)
        return resp.tostring()  # (resp,remain)

    def write(self, byte_list):
        """Send byte_list across subclass-specific communication interface.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import interface_libusb
        >>> hasattr(interface_libusb, 'write')
        True

        Args:
            byte_list: Byte list to use.
        """
        self.dev.write(self.ep_out, byte_list)


class interface_stream(
        interface, metaclass=abc.ABCMeta):  # (lab_interfaces.interface)
    """Generic parent class of all stream-type interfaces.

    Developed for DC590 board variants, but probably has more generic utility if moved into lab_interfaces
    Maybe consider change to inherit from https://docs.python.org/2/library/io.html

    >>> from PyICe.lab_interfaces import interface_stream
    >>> interface_stream is not None
    True

    """
    @abc.abstractmethod
    def read(self, byte_count):
        """Read and return tuple  (byte_count bytes, byte_count remaining_bytes) from subclass-specific communication interface.

        If fewer than byte_count bytes are available, return all available.


        >>> from PyICe.lab_interfaces import interface_stream
        >>> hasattr(interface_stream, 'read')
        True

        Args:
            byte_count: Byte count to use.
        """
        pass

    @abc.abstractmethod
    def write(self, byte_list):
        """Send byte_list across subclass-specific communication interface.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import interface_stream
        >>> hasattr(interface_stream, 'write')
        True

        Args:
            byte_list: Byte list to use.
        """
        pass

    @abc.abstractmethod
    def close(self):
        """Close the underlying interface if necessary.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.lab_interfaces import interface_stream
        >>> hasattr(interface_stream, 'close')
        True

        """
        pass


class interface_stream_serial(interface_stream):
    """PySerial based stream wrapper.

    >>> from PyICe.lab_interfaces import interface_stream_serial
    >>> interface_stream_serial is not None
    True

    """

    def __init__(self, interface_raw_serial):
        """Initialize interface_stream_serial.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_stream_serial.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_stream_serial
        >>> interface_stream_serial is not None
        True

        Args:
            interface_raw_serial: Raw serial interface instance for communication.
        """
        super().__init__('Serial Stream Communication Interface')
        self.ser = interface_raw_serial

    def read(self, byte_count):
        """Read and return tuple  (byte_count bytes, byte_count remaining_bytes) from subclass-specific communication interface.

        If fewer than byte_count bytes are available, return all available.
        If byte_count is None, return all available.


        >>> from PyICe.lab_interfaces import interface_stream_serial
        >>> hasattr(interface_stream_serial, 'read')
        True

        Args:
            byte_count: Byte count to use.

        Returns:
            The value read from the device or channel.
        """
        if byte_count is None:
            byte_count = self.ser.inWaiting()
        resp = self.ser.read(byte_count)
        remain = self.ser.inWaiting()
        return (resp, remain)

    def write(self, byte_list):
        """Send byte_list across subclass-specific communication interface.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import interface_stream_serial
        >>> hasattr(interface_stream_serial, 'write')
        True

        Args:
            byte_list: Byte list to use.
        """
        self.ser.write(byte_list)

    def close(self):
        """Close the underlying interface.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.lab_interfaces import interface_stream_serial
        >>> hasattr(interface_stream_serial, 'close')
        True

        """
        self.ser.close()


class interface_ftdi_d2xx(interface_stream):
    """Write this if you want it.

    https://pypi.python.org/pypi/pylibftdi

    >>> from PyICe.lab_interfaces import interface_ftdi_d2xx
    >>> interface_ftdi_d2xx is not None
    True

    """
    def __init__(self):  # need some kind of device descriptor....
        """Initialize interface_ftdi_d2xx.

        Calls the parent constructor to inherit base behavior.

        >>> from PyICe.lab_interfaces import interface_ftdi_d2xx
        >>> interface_ftdi_d2xx is not None
        True

        """
        interface.__init__(self, 'FTDI D2XX Stream Communication Interface')


# Serial port debugging hack that uses undocumented calls in PySerial 3.4.
PYSERIAL_DEBUG = False
if not serialMissing and serial.VERSION == '3.4' and PYSERIAL_DEBUG:  # type: ignore[union-attr]
    s = serial.Serial()  # <--- This is needed for some reason, else SpySerial ports
    # cannot be opened. There must be some kind of library initialization
    # that happens when a regular serial.Serial object is first created.
    # This sort of thing is expected when using undocumented calls.
    from serial.urlhandler.protocol_spy import Serial as SpySerial  # <--- UNDOCUMENTED CALL # pylint: disable=import-error; optional undocumented pyserial internals, guarded by version check

    class serial_from_name_or_url(SpySerial):
        """Serial_from_name_or_url (spy serial subclass)."""
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
    class serial_from_name_or_url(serial.Serial):  # type: ignore[union-attr]
        """Serial_from_name_or_url."""
        _has_PyICe_debug_capability = False


class interface_raw_serial(interface, serial_from_name_or_url):
    """Interface_raw_serial.

    >>> from PyICe.lab_interfaces import interface_raw_serial
    >>> interface_raw_serial is not None
    True

    """
    def __init__(self, port_name_or_url, baudrate, timeout, **kwargs):
        """Initialize interface_raw_serial.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_raw_serial.

        Calls the parent constructor to inherit base behavior, and initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> interface_raw_serial is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            baudrate: Serial baud rate in bits per second.
            port_name_or_url: Port name or url to use.
            timeout: Timeout in seconds.

        Raises:
            TypeError: If an argument has an incompatible type.
            ValueError: If the provided value is out of range or invalid.
        """
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
            # A string that isn't a valid URL, so assume we were passed a port
            # name.
            serial_port_name = port_name_or_url
            if self._has_PyICe_debug_capability:
                # self is subclass of SpySerial, so reformat superclass init
                # arg to "spy://" URL.
                port_name_or_url = f"spy://{serial_port_name}?file=log{serial_port_name}.txt"
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
        """Return the serial port name.
        Returns the stored serial port name value from the object's internal
        state.
        Returns the stored serial port name from the object's internal state.

        Returns the stored serial port name from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'get_serial_port_name')
        True

        Returns:
            The current serial port name.
        """
        return self._serial_port_name

    def write(self, msg, *args, **kw):
        # '''Attempt to intercept calls to PySerial write() and do str to bytes translation as needed'''
        # Intercept calls to abstract all byte-serialization from the rest of
        # PyICe. Work natively in Python3 unicode strings.
        """Write a value to the channel.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'write')
        True

        Args:
            **kw: Additional keyword arguments.
            *args: Additional positional arguments.
            msg: Message string to display.

        Returns:
            True if the write was acknowledged, False otherwise.

        Raises:
            Exception: If an unexpected error occurs.
        """
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
            # This eventually shouldn't happen. We're trying to migrate all of
            # PyICe instrument/I2C stuff to use Py3 Unicode strings.
            msgbytes = msg
            print(
                f"PyICe: lab_interfaces.interface_raw_serial.write() @{self.get_serial_port_name()} unexpectedly sending out byte array message: {msg}. Consider using write_raw() or contact PyICe-developers@analog.com for more information.")
        else:
            debug_logging.error("*** lab_interfaces.interface_raw_serial.write() called with first argument that was "
                                "neither str, bytes, nor bytearray:\n"
                                f"***   {repr(msg)}{type(msg)}")
            raise Exception(repr(msg), type(msg))
        return self.write_raw(msgbytes, *args, **kw)

    def read(self, size, *args, **kw):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'read')
        True

        Args:
            **kw: Additional keyword arguments.
            *args: Additional positional arguments.
            size: Size in bits.

        Returns:
            The value read from the device or channel.
        """
        resp = self.read_raw(size, *args, **kw)
        return strify(resp)

    def readline(self, *args, **kw):
        """Return the readline.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'readline')
        True

        Args:
            **kw: Additional keyword arguments.
            *args: Additional positional arguments.

        Returns:
            The value read from the device or channel.
        """
        resp = super(interface_raw_serial, self).readline(*args, **kw)
        return strify(resp)
    # Readlines, writelines, readinto, .... byte<->str wrappers
    # unimplemented!!!

    def write_raw(self, msgbytes, *args, **kw):
        """Return write raw result.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'write_raw')
        True

        Args:
            **kw: Additional keyword arguments.
            *args: Additional positional arguments.
            msgbytes: Msgbytes to use.

        Returns:
            True if the write was acknowledged, False otherwise.
        """
        return super(interface_raw_serial, self).write(msgbytes, *args, **kw)

    def read_raw(self, size, *args, **kw):
        """Return read raw result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, 'read_raw')
        True

        Args:
            **kw: Additional keyword arguments.
            *args: Additional positional arguments.
            size: Size in bits.

        Returns:
            The value read from the device or channel.
        """
        return super(interface_raw_serial, self).read(size, *args, **kw)

    def __del__(self):
        """Close interface (serial) port on exit.

        Performs cleanup when the object is garbage-collected.

        >>> from PyICe.lab_interfaces import interface_raw_serial
        >>> hasattr(interface_raw_serial, '__del__')
        True

        """
        self.close()


class interface_tcp_serial(interface):
    """Opens a new TCP socket to (IP, port) and presents.

    a PySerial-like PyICe interface to it.

    This class's API mimics enough of interface_raw_serial's API
    to be compatible with PyICe code expecting such.
    For example read(), write(), and timeouts are supported,
    but it is meaningless to set things like baudrate or parity bits.

    >>> from PyICe.lab_interfaces import interface_tcp_serial
    >>> interface_tcp_serial is not None
    True

    """
    def __init__(self, dest_ip_address, dest_tcp_portnum):
        """Initialize interface_tcp_serial.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_tcp_serial.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> interface_tcp_serial is not None
        True

        Args:
            dest_ip_address: Dest ip address to use.
            dest_tcp_portnum: Dest tcp portnum to use.
        """
        self.ser = serial.serial_for_url(
            f"socket://{dest_ip_address}:{dest_tcp_portnum}")
        super(interface_tcp_serial, self).__init__(self.ser.port)

    def get_serial_port_name(self):
        """Return the serial port name.
        Returns the stored serial port name value from the object's internal
        state.
        Returns the stored serial port name from the object's internal state.

        Returns the stored serial port name from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'get_serial_port_name')
        True

        Returns:
            The current serial port name.
        """
        return self.ser.port

    def read(self, *args, **kwargs):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'read')
        True

        Args:
            **kwargs: Additional keyword arguments.
            *args: Additional positional arguments.

        Returns:
            The value read from the device or channel.
        """
        return self.ser.read(*args, **kwargs)

    def write(self, *args, **kwargs):
        """Write a value to the channel.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'write')
        True

        Args:
            **kwargs: Additional keyword arguments.
            *args: Additional positional arguments.

        Returns:
            True if the write was acknowledged, False otherwise.
        """
        return self.ser.write(*args, **kwargs)

    def close(self, *args, **kwargs):
        """Return the close.
        Releases resources and closes the connection to the instrument.

        Releases resources and restores the system to a safe state.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'close')
        True

        Args:
            **kwargs: Additional keyword arguments.
            *args: Additional positional arguments.

        Returns:
            The close result.
        """
        return self.ser.close(*args, **kwargs)

    @property
    def timeout(self):
        """Return the timeout.

        Supports the ``interface_tcp_serial`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'timeout')
        True

        Returns:
            The timeout duration in seconds.
        """
        return self.ser.timeout

    @timeout.setter
    def timeout(self, new_timeout):
        """Run the timeout step.

        Supports the ``interface_tcp_serial`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'timeout')
        True

        Args:
            new_timeout: New timeout to use.
        """
        self.ser.timeout = new_timeout

    @property
    def in_waiting(self):
        """Return in waiting result.

        Introduces a timing delay required by the hardware or protocol.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'in_waiting')
        True

        Returns:
            Number of bytes waiting in the input buffer.
        """
        if hasattr(self.ser, "in_waiting"):
            return self.ser.in_waiting
        elif hasattr(self.ser, "inWaiting"):
            return self.ser.inWaiting()

    def inWaiting(self):
        """Returns in_waiting. Added for PySerial <3.0 compatibility.

        Introduces a timing delay required by the hardware or protocol.


        >>> from PyICe.lab_interfaces import interface_tcp_serial
        >>> hasattr(interface_tcp_serial, 'inWaiting')
        True

        Returns:
            Number of bytes waiting in the input buffer.
        """
        return self.in_waiting


class SerialTestHarness(object):
    """A harness for testing code that reads and parses input.

    from PySerial serial.Serial objects. A SerialTestHarness
    emulates a PySerial serial.Serial object by providing a read()
    method and a writable timeout property.
    bytestream is a generator function that yields one byte
    of test stimulus each time its next() method is called.
    WARNING: Not thread-safe.
    TODO: The write() method currently implemented does nothing.

    >>> from PyICe.lab_interfaces import SerialTestHarness
    >>> SerialTestHarness is not None
    True

    """
    def __init__(self, bytestream, max_bytes_returned_per_read=None):
        """Initialize serial test harness.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Initializes 4 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> SerialTestHarness is not None
        True

        Args:
            bytestream: Bytestream to use.
            max_bytes_returned_per_read: Max bytes returned per read to use.
        """
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
        """Return biased rng result.

        Supports the ``SerialTestHarness`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> callable(getattr(SerialTestHarness, 'biased_rng', None))
        True

        Args:
            max_val: Max val to use.
            min_val: Min val to use.

        Returns:
            The biased rng result.
        """
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
            result = random.randint(min_val + 2, max_val - 1)
        else:
            # 1/4 chance of returning max_val
            result = max_val
        return result

    def read(self, numbytes):
        """Returns up to numbytes bytes from our test suite's.

        bytestream generator, with random delay that's within timeout.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'read')
        True

        Args:
            numbytes: Numbytes to use.

        Returns:
            The value read from the device or channel.
        """
        # First note by what wallclock time we have to
        # return the requested bytes:
        treturn = time.time() + self.timeout * random.uniform(0, 1.0)
        # Document the requirements for numbytes.
        assert isinstance(numbytes, int) and numbytes >= 1
        # Randomly choose how many bytes to return:
        if self._in_waiting is None:
            retlength = SerialTestHarness.biased_rng(0, numbytes)
        else:
            # We promised at least self._in_waiting bytes are available.
            if numbytes > self._in_waiting:
                # Return at least the promised number of bytes.
                retlength = SerialTestHarness.biased_rng(
                    self._in_waiting, numbytes)
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
        """Write a value to the channel.

        Writes data to the underlying target.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'write')
        True

        Args:
            bytestring: Bytestring to use.
        """
        pass

    @property
    def timeout(self):
        """Return the timeout.

        Supports the ``SerialTestHarness`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'timeout')
        True

        Returns:
            The timeout duration in seconds.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, new_timeout):
        """Run the timeout step.

        Supports the ``SerialTestHarness`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'timeout')
        True

        Args:
            new_timeout: New timeout to use.
        """
        from numbers import Real
        assert isinstance(new_timeout, Real) and new_timeout >= 0
        self._timeout = new_timeout

    @property
    def max_bytes_returned_per_read(self):
        """Return max bytes returned per read result.

        Supports the ``SerialTestHarness`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'max_bytes_returned_per_read')
        True

        Returns:
            The max bytes returned per read result.
        """
        return self._max_bytes_returned_per_read

    @max_bytes_returned_per_read.setter
    def max_bytes_returned_per_read(self, new_max):
        """Perform max bytes returned per read operation.

        Supports the ``SerialTestHarness`` workflow by performing the described operation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'max_bytes_returned_per_read')
        True

        Args:
            new_max: New max to use.
        """
        assert isinstance(new_max, int) and new_max >= 0
        self._max_bytes_returned_per_read = new_max

    @property
    def in_waiting(self):
        """How many bytes we promise are available for reading.

        Generated randomly upon request, this
        will never exceed the max_bytes_returned_per_read
        optionally set during object instantiation.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'in_waiting')
        True

        Returns:
            Number of bytes waiting in the input buffer.
        """
        if self._in_waiting is not None:
            return self._in_waiting
        if self._max_bytes_returned_per_read is None:
            max_bytes = 4096  # Arbitrary but plausible value.
        else:
            max_bytes = self._max_bytes_returned_per_read
        self._in_waiting = SerialTestHarness.biased_rng(0, max_bytes)
        return self._in_waiting

    def inWaiting(self):
        """Returns in_waiting. Added for PySerial <3.0 compatibility.

        Introduces a timing delay required by the hardware or protocol.


        >>> from PyICe.lab_interfaces import SerialTestHarness
        >>> hasattr(SerialTestHarness, 'inWaiting')
        True

        Returns:
            Number of bytes waiting in the input buffer.
        """
        return self.in_waiting


class interface_test_harness_serial(interface, SerialTestHarness):
    """Interface_test_harness_serial.

    >>> from PyICe.lab_interfaces import interface_test_harness_serial
    >>> interface_test_harness_serial is not None
    True

    """
    def __init__(self, serial_port_name, bytestream,
                 max_bytes_returned_per_read=4096):
        """Initialize interface_test_harness_serial.
        Stores configuration in ``_serial_port_name`` for use by other
        methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_test_harness_serial
        >>> hasattr(interface_test_harness_serial, '__init__')
        True

        Args:
            bytestream: Bytestream to use.
            max_bytes_returned_per_read: Max bytes returned per read to use.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
        """
        SerialTestHarness.__init__(self, bytestream,
                                   max_bytes_returned_per_read=max_bytes_returned_per_read)
        interface.__init__(self, f'interface_raw_serial @ {serial_port_name}')
        self._serial_port_name = serial_port_name

    def get_serial_port_name(self):
        """Return the serial port name.
        Returns the stored serial port name value from the object's internal
        state.
        Returns the stored serial port name from the object's internal state.

        Returns the stored serial port name from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_test_harness_serial
        >>> hasattr(interface_test_harness_serial, 'get_serial_port_name')
        True

        Returns:
            The current serial port name.
        """
        return self._serial_port_name


'''below are specific classes that inherit from the above general classes'''


class interface_visa_tcp_ip(interface_visa, visa_wrappers.visa_wrapper_tcp):
    """Interface_visa_tcp_ip.

    >>> from PyICe.lab_interfaces import interface_visa_tcp_ip
    >>> interface_visa_tcp_ip is not None
    True

    """
    def __init__(self, host_address, port, timeout, **kwargs):
        """Initialize interface_visa_tcp_ip.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_visa_tcp_ip
        >>> interface_visa_tcp_ip is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            host_address: Network hostname or IP address of the remote host.
            port: TCP/IP port number.
            timeout: Timeout in seconds.
        """
        visa_wrappers.visa_wrapper_tcp.__init__(
            self, host_address, port, timeout, **kwargs)
        interface_visa.__init__(
            self, f"interface_visa_tcp_ip @ {host_address}:{port}")


class interface_visa_telnet(interface_visa, visa_wrappers.visa_wrapper_telnet):
    """Interface_visa_telnet.

    >>> from PyICe.lab_interfaces import interface_visa_telnet
    >>> interface_visa_telnet is not None
    True

    """
    def __init__(self, host_address, port, timeout):
        """Initialize interface_visa_telnet.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_visa_telnet
        >>> interface_visa_telnet is not None
        True

        Args:
            host_address: Network hostname or IP address of the remote host.
            port: TCP/IP port number.
            timeout: Timeout in seconds.
        """
        visa_wrappers.visa_wrapper_telnet.__init__(
            self, host_address, port, timeout)
        interface_visa.__init__(
            self, f"interface_visa_telnet @ {host_address}:{port}")


class interface_visa_serial(visa_wrappers.visa_wrapper_serial, interface_visa):
    """Interface_visa_serial.

    >>> from PyICe.lab_interfaces import interface_visa_serial
    >>> interface_visa_serial is not None
    True

    """
    def __init__(self, interface_raw_serial_object):
        """Initialize interface_visa_serial.
        Delegates to the parent class constructor.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_visa_serial
        >>> interface_visa_serial is not None
        True

        Args:
            interface_raw_serial_object: Interface raw serial object to use.
        """
        super().__init__(interface_raw_serial_object)
        # visa_wrappers.visa_wrapper_serial.__init__(self,interface_raw_serial_object)
        # interface_visa.__init__(self,'interface_visa_serial @ {}'.format(interface_raw_serial_object))


class interface_visa_vxi11(interface_visa, visa_wrappers.visa_wrapper_vxi11):
    """Interface_visa_vxi11.

    >>> from PyICe.lab_interfaces import interface_visa_vxi11
    >>> interface_visa_vxi11 is not None
    True

    """
    def __init__(self, address, timeout):
        """Initialize interface_visa_vxi11.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_visa_vxi11
        >>> interface_visa_vxi11 is not None
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.
        """
        visa_wrappers.visa_wrapper_vxi11.__init__(self, address, timeout)
        interface_visa.__init__(self, f'interface_visa_vxi11 @ {address}')


class interface_visa_usbtmc(interface_visa, visa_wrappers.visa_wrapper_usbtmc):
    """Interface_visa_usbtmc.

    >>> from PyICe.lab_interfaces import interface_visa_usbtmc
    >>> interface_visa_usbtmc is not None
    True

    """
    def __init__(self, address, timeout):
        """Initialize interface_visa_usbtmc.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_visa_usbtmc
        >>> interface_visa_usbtmc is not None
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.
        """
        visa_wrappers.visa_wrapper_usbtmc.__init__(self, address, timeout)
        interface_visa.__init__(self, f'interface_visa_usbtmc @ {address}')


class interface_visa_direct(interface_visa, visa_wrappers.visa_interface):
    """Interface_visa_direct.

    >>> from PyICe.lab_interfaces import interface_visa_direct
    >>> interface_visa_direct is not None
    True

    """
    def __init__(self, visa_address_string, timeout):
        """Initialize interface_visa_direct.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_visa_direct.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_visa_direct
        >>> interface_visa_direct is not None
        True

        Args:
            timeout: Timeout in seconds.
            visa_address_string: Visa address string to use.
        """
        super().__init__(
            visa_address_string,
            address=visa_address_string,
            timeout=timeout)
        # visa_wrappers.visa_interface.__init__(self,visa_address_string,timeout)
        # interface_visa.__init__(self,'interface_visa_direct @ {}'.format(visa_address_string) )
        self.visa_address_string = visa_address_string


class interface_bobbytalk_raw_serial(interface_bobbytalk):
    """Sends and receives bobbytalk packets over a raw serial interface.

    >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
    >>> interface_bobbytalk_raw_serial is not None
    True

    """

    def __init__(self, raw_serial_interface, fifo_size=2 **
                 16, junk_bytes_dump=None, debug=False):
        """Provides the bobbytalk packet API over a raw_serial_interface.

        which must be an instance of interface_raw_serial or SerialTestHarness.
        junk_bytes_dump is an optional argument. It's a function of one argument that receives
        all the bytes discarded by the bobbytalk parser as non-packet-bytes.


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, '__init__')
        True

        Args:
            debug: If True, enable debug output.
            fifo_size: Fifo size to use.
            junk_bytes_dump: Junk bytes dump to use.
            raw_serial_interface: Raw serial interface to use.
        """
        # Can't be interface_stream_serial because we need to be
        # able to change timeouts on every recv_packet() call.
        super(
            interface_bobbytalk_raw_serial,
            self).__init__(
            name=(
                f"bobbytalk Packet interface over {raw_serial_interface.get_serial_port_name()}"))
        assert isinstance(fifo_size, int) and fifo_size > 0
        assert hasattr(junk_bytes_dump, "__call__") or junk_bytes_dump is None
        assert isinstance(debug, bool)
        self.ser = raw_serial_interface
        self.fifo_size = fifo_size
        self.fifo = StreamWindow(
            stream=self.ser,
            buffer_size=fifo_size,
            debug=debug)
        # Don't write to Pyserial.Serial.timeout unless we actually change the
        # timeout value.
        self.timeout_cached = None
        # to avoid extra control traffic on USB on SAMD M0+ micros.
        self.debug = debug
        if junk_bytes_dump is None:
            # By default, discard junk bytes.
            def trash(junk_bytes):
                """Run the trash step.

                Performs the described operation on the object's internal state.


                >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
                >>> hasattr(interface_bobbytalk_raw_serial, 'trash')
                True

                Args:
                    junk_bytes: Junk bytes to use.
                """
                return
            self.dump = trash
        else:
            self.dump = junk_bytes_dump

    def _advance_fifo_to_SOP(self):
        """Search through the FIFO buffer for the first occurrence of Start of Packet.

        For example, if the first byte is 'L' and the second is 'T', we need to handle
        the following cases of FIFO content:

        |<-- FIFO head       ----> FIFO tail
        Case 1: {0 or more non-SOP bytes}LT{0 or more bytes of any kind}
        Case 2: {0 or more non-SOP bytes}L
        Case 3: {0 or more non-SOP bytes}


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, '_advance_fifo_to_SOP')
        True

        Returns:
            The advance fifo to SOP result.
        """
        psbl_SOP_position = self.fifo.find(
            bobbytalk.packet.START_OF_PACKET_BYTEARRAY)
        if psbl_SOP_position > -1:
            read_how_many = psbl_SOP_position   # Case 1
        elif len(self.fifo) > 0 and self.fifo[-1] == bobbytalk.packet.START_OF_PACKET_HIGH_BYTE:
            read_how_many = len(self.fifo) - 1    # Case 2
        else:
            read_how_many = len(self.fifo)      # Case 3
            # Try to read new bytes into the FIFO.
            self.fifo.peek(read_how_many + 1)
        if read_how_many > 0:
            # Advance stream position if needed.
            self.dump(self.fifo.read(read_how_many))
        return read_how_many

    def send_packet(self, src_id, dest_id, buffer):
        """Returns immediately indicating SUCCESS (True) or FAIL (False).

        Returns SUCCESS if buffer successfully sent to the
        underlying interface.
        Otherwise FAIL, meaning the underlying interface
        couldn't accept buffer for some reason.


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, 'send_packet')
        True

        Args:
            buffer: Buffer to use.
            dest_id: Destination identifier.
            src_id: Source identifier.

        Returns:
            The send packet result.
        """
        pktbytes = bobbytalk.packet(
            src_id=src_id,
            dest_id=dest_id,
            length=len(buffer),
            data=buffer,
            crc=None).to_byte_array()
        result = bool(self.ser.write(pktbytes) == len(pktbytes))
        # self.ser.flush()
        if self.debug:
            bufstr = " ".join([hex(byte) for byte in bytearray(buffer)])
            print(f">>>>> send(buffer = {bufstr}) returned {result}")
        return result

    def recv_packet(self, dest_id, timeout, src_id=None, receive_tries=8):
        """Blocks for up to timeout waiting for packet matching dest_id.

        and optionally src_id, continuing to receive and dispatch other
        incoming packets.
        Upon success, returns a bobbytalk_packet object.
        Upon timeout, returns None.


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, 'recv_packet')
        True

        Args:
            dest_id: Destination identifier.
            receive_tries: Receive tries to use.
            src_id: Source identifier.
            timeout: Timeout in seconds.

        Returns:
            The recv packet result.
        """
        # Stuff we'll use from Python's standard library.
        from numbers import Real
        from struct import unpack
        import time
        # Sanity check arguments.
        assert isinstance(dest_id, int) and dest_id >= 0 and dest_id < 2**16
        assert isinstance(timeout, Real) and timeout >= 0
        assert src_id is None or (src_id >= 0 and src_id < 2**16)
        assert isinstance(receive_tries, int)
        # Actual receive logic begins here.
        # Know when to give up trying to receive packets.
        tquit = time.time() + timeout
        new_ser_timeout = timeout / receive_tries
        if new_ser_timeout != self.timeout_cached:
            # How regularly to read from underlying stream.
            self.ser.timeout = new_ser_timeout
            self.timeout_cached = new_ser_timeout
        result = None  # Default return value if we can't find a packet.
        psbl_src = 0
        psbl_dest = 0
        rcvd_crc = 0
        for trynum in range(receive_tries):
            if time.time() >= tquit:
                # We used up too much time trying to parse a packet at this
                # stream position,
                self.dump(self.fifo.read(1))  # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                break                        # and return None to the caller.
            # INITIAL READ / SEARCH FOR START OF PACKET.
            possible_hdr_bytes = self.fifo.peek(
                num=bobbytalk.packet.HEADER_SIZE)
            # If Start of Packet bytes aren't at our current stream position,
            # try to seek forward and consume bytes until they are.
            if self._advance_fifo_to_SOP() > 0:
                # No Start of Packet here so we advanced to the next possible
                # one.
                possible_hdr_bytes = self.fifo.peek(
                    num=bobbytalk.packet.HEADER_SIZE)
            # IF WE HAVE ENOUGH BYTES FOR A HEADER, PARSE THEM.
            if len(possible_hdr_bytes) < bobbytalk.packet.HEADER_SIZE:
                # Wasn't able to read in a full header.
                continue  # Try to read more bytes if we still have time.
            psbl_sop, psbl_src, psbl_dest, psbl_length = unpack(
                ">HHHH", possible_hdr_bytes)
            # VERIFY START OF PACKET MARKER BYTES.
            if psbl_sop != bobbytalk.packet.START_OF_PACKET:
                self.dump(self.fifo.read(1))  # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                continue                     # and retry parsing.
            # TRY TO READ IN THE ENTIRE PACKET, taking no longer than
            # (timeout/receive_tries).
            possible_packet_length = bobbytalk.packet.HEADER_SIZE + \
                psbl_length + bobbytalk.packet.CRC_SIZE
            possible_packet = self.fifo.peek(possible_packet_length)
            if len(possible_packet) < possible_packet_length:
                # Didn't read enough bytes for the full alleged packet,
                continue  # so try reading in more bytes if there's time left.
            # CHECK THE CRC.
            calcd_crc = bobbytalk.packet.crc16(
                possible_packet[:-bobbytalk.packet.CRC_SIZE])
            (rcvd_crc,) = unpack(
                ">H", possible_packet[-bobbytalk.packet.CRC_SIZE:])
            if calcd_crc != rcvd_crc:        # BAD CRC,
                self.dump(self.fifo.read(1))  # so advance stream by 1 byte
                self._advance_fifo_to_SOP()  # then advance, if needed, to next Start of Packet
                continue                     # and retry parsing.
            # ALL CHECKS PASS. VALID PACKET.
            # Consume the packet from the stream.
            result = self.fifo.read(possible_packet_length)
            if dest_id != psbl_dest or (
                    src_id is not None and src_id != psbl_src):
                print("*" * 78)
                print("TODO: Implement dispatch table for non-matching packets.")
                print(f"      Want dest_id {dest_id:04x}, got {psbl_dest:04x}")
                srcstr = f"{src_id:04x}" if src_id is not None else "ANY"
                print(f"      Want src_id {srcstr}, got {psbl_src:04x}")
                print("*" * 78)
            # for trynum in range(receive_tries)  # Return packet as result.
            break
        else:  # for trynum in range(receive_tries)
            # Ran out of receive tries and still couldn't fetch a full packet
            # at this stream position. Give up, consume 1 byte, and if necessary,
            # advance the stream to next SOP.
            self.dump(self.fifo.read(1))
            self._advance_fifo_to_SOP()
        # End of receive logic. All returning of results to the caller happens
        # below:
        if result is None:
            return None
        else:
            # result is a string of bytes containing a valid packet,
            # so let's create and return a bobbytalk.packet object with the
            # parsed bytes.
            packet = bobbytalk.packet(src_id=psbl_src, dest_id=psbl_dest,
                                      length=len(
                                          result) - bobbytalk.packet.HEADER_SIZE - bobbytalk.packet.CRC_SIZE,
                                      data=result[bobbytalk.packet.HEADER_SIZE:-
                                                  bobbytalk.packet.CRC_SIZE],
                                      crc=rcvd_crc)
            return packet

    def handle_comms(self):
        """Call this periodically to receive packets from the serial line.

        and dispatch to any registered packet handlers ("modules") in
        the module_table.


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, 'handle_comms')
        True

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError("Subclass must implement this.")

    def register_handler(self, dest_id, handler_function):
        """Sets the handler function for received packets with dest_id.

        handler_function will be called like this:
        handler_function(bobbytalk_packet)


        >>> from PyICe.lab_interfaces import interface_bobbytalk_raw_serial
        >>> hasattr(interface_bobbytalk_raw_serial, 'register_handler')
        True

        Args:
            dest_id: Destination identifier.
            handler_function: Handler function to use.

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError("Subclass must implement this.")


'''below are the specific cases of the twi interface'''


class interface_twi_dummy(interface_twi, twi_interface.i2c_dummy):
    """Interface_twi_dummy.

    >>> from PyICe.lab_interfaces import interface_twi_dummy
    >>> interface_twi_dummy is not None
    True

    """
    def __init__(self, delay, **kwargs):
        """Initialize interface_twi_dummy.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_twi_dummy
        >>> interface_twi_dummy is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            delay: Delay time in seconds.
        """
        interface_twi.__init__(self, 'interface_twi_dummy @ fake')
        twi_interface.i2c_dummy.__init__(self, delay, **kwargs)


class interface_twi_mdump(interface_twi, twi_interface.mem_dict):
    """Interface_twi_mdump.

    >>> from PyICe.lab_interfaces import interface_twi_mdump
    >>> interface_twi_mdump is not None
    True

    """
    def __init__(self, data_source=None, **kwargs):
        """Initialize interface_twi_mdump.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_twi_mdump
        >>> interface_twi_mdump is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            data_source: Data source to use.
        """
        # twi_interface.mem_dict.__init__(self,data_source,**kwargs) #happens
        # through super() below
        kwargs['data_source'] = data_source
        interface_twi.__init__(self, 'interface_twi_dummy @ fake', **kwargs)


class interface_twi_scpi(twi_interface.i2c_scpi, interface_twi):
    """Interface_twi_scpi.

    >>> from PyICe.lab_interfaces import interface_twi_scpi
    >>> interface_twi_scpi is not None
    True

    """
    def __init__(self, interface_serial, timeout):
        """Initialize interface_twi_scpi.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_twi_scpi.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_twi_scpi
        >>> interface_twi_scpi is not None
        True

        Args:
            interface_serial: Serial interface instance for communication.
            timeout: Timeout in seconds.
        """
        super().__init__(interface_serial)
        # twi_interface.i2c_scpi.__init__(self, interface_serial)
        # interface_twi.__init__(self,'interface_twi_scpi @ {}'.format(interface_serial))
        self.timeout = timeout


class interface_twi_scpi_sp(twi_interface.i2c_scpi_sp, interface_twi):
    """Interface_twi_scpi_sp.

    >>> from PyICe.lab_interfaces import interface_twi_scpi_sp
    >>> interface_twi_scpi_sp is not None
    True

    """
    def __init__(self, interface_serial, portnum, sclpin,
                 sdapin, pullup_en=False, timeout=1):
        """Initialize interface_twi_scpi_sp.
        Calls the parent class constructor and initializes instance-specific
        attributes for interface_twi_scpi_sp.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_twi_scpi_sp
        >>> hasattr(interface_twi_scpi_sp, '__init__')
        True

        Args:
            interface_serial: Serial interface instance for communication.
            portnum: Portnum to use.
            pullup_en: Pullup en to use.
            sclpin: Sclpin to use.
            sdapin: Sdapin to use.
            timeout: Timeout in seconds.
        """
        super().__init__(interface_serial, portnum, sclpin, sdapin, pullup_en)
        # twi_interface.i2c_scpi_sp.__init__(self, interface_serial, portnum, sclpin, sdapin, pullup_en)
        # interface_twi.__init__(self,'interface_twi_scpi @ {}'.format(interface_serial))
        self.timeout = timeout


class interface_twi_scpi_testhook(
        twi_interface.i2c_scpi_testhook, interface_twi):
    """Interface_twi_scpi_testhook.

    >>> from PyICe.lab_interfaces import interface_twi_scpi_testhook
    >>> interface_twi_scpi_testhook is not None
    True

    """
    def __init__(self, interface_serial, timeout):
        """Initialize interface_twi_scpi_testhook.
        Stores configuration in ``timeout`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_twi_scpi_testhook
        >>> interface_twi_scpi_testhook is not None
        True

        Args:
            interface_serial: Serial interface instance for communication.
            timeout: Timeout in seconds.
        """
        twi_interface.i2c_scpi.__init__(self, interface_serial)
        interface_twi.__init__(
            self, f'interface_twi_scpi @ {interface_serial}')
        self.timeout = timeout


# DJS TODO: fix interfaces to reconcile with DC590 cleanup
class interface_twi_dc590_serial(twi_interface.i2c_dc590, interface_twi):
    """Interface_twi_dc590_serial.

    >>> from PyICe.lab_interfaces import interface_twi_dc590_serial
    >>> interface_twi_dc590_serial is not None
    True

    """
    def __init__(self, interface_serial, timeout):
        """Initialize interface_twi_dc590_serial.
        Stores configuration in ``timeout`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_twi_dc590_serial
        >>> interface_twi_dc590_serial is not None
        True

        Args:
            interface_serial: Serial interface instance for communication.
            timeout: Timeout in seconds.
        """
        # DJS TODO: fix interfaces to reconcile with DC590 cleanup
        twi_interface.i2c_dc590.__init__(self, interface_serial)
        interface_twi.__init__(
            self, f'interface_twi_dc590_serial @ {interface_serial}')
        self.timeout = timeout


class interface_twi_buspirate(twi_interface.i2c_buspirate, interface_twi):
    """Interface_twi_buspirate.

    >>> from PyICe.lab_interfaces import interface_twi_buspirate
    >>> interface_twi_buspirate is not None
    True

    """
    def __init__(self, interface_serial, timeout):
        """Initialize interface_twi_buspirate.
        Stores configuration in ``timeout`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_twi_buspirate
        >>> interface_twi_buspirate is not None
        True

        Args:
            interface_serial: Serial interface instance for communication.
            timeout: Timeout in seconds.
        """
        twi_interface.i2c_buspirate.__init__(self, interface_serial)
        interface_twi.__init__(
            self, f'interface_twi_buspirate @ {interface_serial}')
        self.timeout = timeout


class interface_twi_firmata(twi_interface.i2c_firmata, interface_twi):
    """Interface_twi_firmata.

    >>> from PyICe.lab_interfaces import interface_twi_firmata
    >>> interface_twi_firmata is not None
    True

    """
    # Old. Consider Telemetrix instead.
    def __init__(self, firmata_instance):
        """Initialize interface_twi_firmata.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_twi_firmata
        >>> interface_twi_firmata is not None
        True

        Args:
            firmata_instance: Firmata instance to use.
        """
        twi_interface.i2c_firmata.__init__(self, firmata_instance)
        interface_twi.__init__(
            self, f'interface_twi_firmata @ {firmata_instance}')


class interface_twi_bobbytalk(twi_interface.i2c_bobbytalk, interface_twi):
    """Interface_twi_bobbytalk.

    >>> from PyICe.lab_interfaces import interface_twi_bobbytalk
    >>> interface_twi_bobbytalk is not None
    True

    """
    def __init__(self, bobbytalk_interface, src_id, **kwargs):
        """Initialize interface_twi_bobbytalk.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_twi_bobbytalk
        >>> interface_twi_bobbytalk is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            bobbytalk_interface: Bobbytalk interface to use.
            src_id: Source identifier.
        """
        twi_interface.i2c_bobbytalk.__init__(
            self, bobbytalk_interface, src_id, **kwargs)
        interface_twi.__init__(self, name='interface_twi_bobytalk')


class interface_labcomm_raw_serial(interface):
    """Sends and receives Labcomm packets over a raw serial interface.

    >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
    >>> interface_labcomm_raw_serial is not None
    True

    """

    def __init__(self, raw_serial_interface,
                 serial_port_name, src_id, dest_id):
        """Initialize interface_labcomm_raw_serial.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
        >>> hasattr(interface_labcomm_raw_serial, '__init__')
        True

        Args:
            dest_id: Destination identifier.
            raw_serial_interface: Raw serial interface to use.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            src_id: Source identifier.
        """
        interface.__init__(self, f'interface_raw_serial @ {serial_port_name}')
        self.interface = raw_serial_interface
        self.src_id = src_id
        self.dest_id = dest_id
        self.talker = labcomm.labcomm_packet()
        self.parser = labcomm.labcomm_parser(raw_serial_interface)

    def set_source_id(self, src_id):
        """Set the source id.
        Updates the source id in the object's internal state.

        Updates the source id in the object's internal state.


        >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
        >>> hasattr(interface_labcomm_raw_serial, 'set_source_id')
        True

        Args:
            src_id: Source identifier.
        """
        self.src_id = src_id

    def set_destination_id(self, dest_id):
        """Set the destination id.
        Updates the destination id in the object's internal state.

        Updates the destination id in the object's internal state.


        >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
        >>> hasattr(interface_labcomm_raw_serial, 'set_destination_id')
        True

        Args:
            dest_id: Destination identifier.
        """
        self.dest_id = dest_id

    def send_payload(self, payload):
        """Perform send payload operation.

        Transmits data to the remote endpoint.


        >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
        >>> hasattr(interface_labcomm_raw_serial, 'send_payload')
        True

        Args:
            payload: Payload to use.
        """
        self.interface.write_raw(
            self.talker.assemble(
                source=self.src_id,
                destination=self.dest_id,
                payload=payload))

    def receive_packet(self):
        """Return receive packet result.

        Retrieves data from the remote endpoint.


        >>> from PyICe.lab_interfaces import interface_labcomm_raw_serial
        >>> hasattr(interface_labcomm_raw_serial, 'receive_packet')
        True

        Returns:
            The receive packet result.
        """
        return self.parser.read_message()


class interface_labcomm_twi_serial(twi_interface.i2c_labcomm, interface_twi):
    """Interface_labcomm_twi_serial.

    >>> from PyICe.lab_interfaces import interface_labcomm_twi_serial
    >>> interface_labcomm_twi_serial is not None
    True

    """
    def __init__(self, raw_serial_interface, comport_name, src_id, dest_id):
        """Initialize interface_labcomm_twi_serial.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_labcomm_twi_serial
        >>> interface_labcomm_twi_serial is not None
        True

        Args:
            comport_name: Comport name to use.
            dest_id: Destination identifier.
            raw_serial_interface: Raw serial interface to use.
            src_id: Source identifier.
        """
        twi_interface.i2c_labcomm.__init__(self, raw_serial_interface)
        interface_twi.__init__(self, name='interface_labcomm_twi_port')
        self.interface = raw_serial_interface
        self.src_id = src_id
        self.dest_id = dest_id
        self.talker = labcomm.labcomm_packet()
        self.parser = labcomm.labcomm_parser(raw_serial_interface)

    def set_source_id(self, src_id):
        """Set the source id.
        Updates the source id in the object's internal state.

        Updates the source id in the object's internal state.


        >>> from PyICe.lab_interfaces import interface_labcomm_twi_serial
        >>> hasattr(interface_labcomm_twi_serial, 'set_source_id')
        True

        Args:
            src_id: Source identifier.
        """
        self.src_id = src_id

    def set_destination_id(self, dest_id):
        """Set the destination id.
        Updates the destination id in the object's internal state.

        Updates the destination id in the object's internal state.


        >>> from PyICe.lab_interfaces import interface_labcomm_twi_serial
        >>> hasattr(interface_labcomm_twi_serial, 'set_destination_id')
        True

        Args:
            dest_id: Destination identifier.
        """
        self.dest_id = dest_id


'''SPI interfaces'''


class interface_spi_dummy(interface_spi, spi_interface.spi_dummy):
    """Interface_spi_dummy.

    >>> from PyICe.lab_interfaces import interface_spi_dummy
    >>> interface_spi_dummy is not None
    True

    """
    def __init__(self, delay=0):
        """Initialize interface_spi_dummy.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_spi_dummy
        >>> interface_spi_dummy is not None
        True

        Args:
            delay: Delay time in seconds.
        """
        spi_interface.spi_dummy.__init__(self, delay)
        interface_spi.__init__(self, 'interface_spi_dummy @ fake')


class interface_spi_dc590(interface_spi, spi_interface.spi_dc590):
    """Interface_spi_dc590.

    >>> from PyICe.lab_interfaces import interface_spi_dc590
    >>> interface_spi_dc590 is not None
    True

    """
    def __init__(self, interface_stream, ss_ctrl=None):
        """Initialize interface_spi_dc590.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_spi_dc590
        >>> interface_spi_dc590 is not None
        True

        Args:
            interface_stream: Interface stream to use.
            ss_ctrl: Slave-select control mode or pin assignment.
        """
        spi_interface.spi_dc590.__init__(self, interface_stream, ss_ctrl)
        interface_spi.__init__(
            self, f'interface_spi_dc590 @ {interface_stream}')


class interface_spi_cfgpro(interface_spi, spi_interface.spi_cfgpro):
    """Interface_spi_cfgpro.

    >>> from PyICe.lab_interfaces import interface_spi_cfgpro
    >>> interface_spi_cfgpro is not None
    True

    """
    def __init__(self, visa_interface, CPOL, CPHA, baudrate=1e6, ss_ctrl=None):
        """Initialize interface_spi_cfgpro.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_interfaces import interface_spi_cfgpro
        >>> interface_spi_cfgpro is not None
        True

        Args:
            CPHA: Clock phase.
            CPOL: Clock polarity.
            baudrate: Serial baud rate in bits per second.
            ss_ctrl: Slave-select control mode or pin assignment.
            visa_interface: Visa interface to use.
        """
        spi_interface.spi_cfgpro.__init__(
            self, visa_interface, CPOL, CPHA, baudrate, ss_ctrl)
        interface_spi.__init__(
            self, f'interface_spi_cfgpro @ {visa_interface}')


class gpib_adapter(communication_node):
    """Gpib_adapter (communication_node subclass).

    >>> from PyICe.lab_interfaces import gpib_adapter
    >>> gpib_adapter is not None
    True

    """
    pass


class gpib_adapter_visa(gpib_adapter):
    """Gpib_adapter_visa.

    >>> from PyICe.lab_interfaces import gpib_adapter_visa
    >>> gpib_adapter_visa is not None
    True

    """
    pass


class interface_factory(communication_node):
    """The interface factory is a wrapper class that creates interfaces and the instruments inheriting from "communication_node", that they pass on to channels.

    Interfaces acquired through the interface factory have a notion of a "parent" which traces back to the physical port of the computer.
    The parent feature allows the user to request multiple interfaces from the factory without regard for possible collisions that may occur with multiple endpoints talking through the same physical channel (e.g. COM port, USB port, etc.).

    PyICe will ensure that channels that trace back to a common parent, with a common underlying hardware pointer, will be singulated serially within the threading (during logging for instance) such that all channels will be read sequentially with possibility of a collision in time.

    It should be clear from this that all requests for a physical interface should be made from the interface factory itself using these "get_xxx" methods rather than reaching around and grabbing raw interface handles directly. If you do that, you are on your own and PyICe won't help you with interface threading problems.

    This class ventures to be smart about the interfaces and to simplify their creation.
    Its purpose is also to encourage portable code, and to remove some low level responsibilities from the instruments.

    There are two use models that can be adopted:

    1) An interface_factory can be instantiated and all interfaces acquired from it using the getter methods. Lab instrument objects, created from the lab_instruments folder, then get their interface handles from interfaces acquired from the interface factory object. These instruments are then usually added to a lab core channel_master for channel aggregation.

    2) Alternatley, the project can go straight to creating a lab_core master (not channel_master). A lab_core master is merely a channel_master that inherits this interface_factory class. In this work flow, interfaces can be acquired from that master object directly (again using the getter methods in this class) without the requirement to create a disposable interface_factory instance. This method results in slightly compacted code but has an interface object flow that seems to double back on itself.

    >>> from PyICe.lab_interfaces import interface_factory
    >>> interface_factory is not None
    True

    """
    _instantiated = False

    def __init__(self):
        """Initialize interface_factory.
        Initializes 12 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 12 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> obj = interface_factory()
        >>> isinstance(obj, interface_factory)
        True

        Raises:
            Exception: If an unexpected error occurs.
        """
        communication_node.__init__(self)
        if self._instantiated is True:
            raise Exception(
                "PyICe lab_interfaces: It's only appropriate to create one instance of an interface_factory. There already seems to be at least one.")
        self._instantiated = True
        self.set_com_node_thread_safe()
        # since there is only one visa
        if not visaMissing:
            self._visa_root = communication_node()
            self._visa_root.set_com_node_parent(self)
            self._visa_root.set_com_node_thread_safe()  # visa is thread safe
        self._gpib_adapters = {}  # communication_node indexed by adapter_number
        self._gpib_interfaces = {}  # indexed by adapter number and address
        self._raw_serial_interfaces = []
        self._direct_visa_interfaces = []
        self._vxi11_interfaces = []
        self._usbtmc_interfaces = []
        self._visa_serial_interfaces = []
        self._tcp_ip_interfaces = []
        self._telnet_interfaces = []
        self._default_timeout = 2

    def get_visa_interface(self, visa_address_string, timeout=None):
        """Return the visa interface.
        Returns the stored visa interface from the object's internal state.

        Returns the stored visa interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_interface')
        True

        Args:
            timeout: Timeout in seconds.
            visa_address_string: Visa address string to use.

        Returns:
            The current visa interface.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if visaMissing:
            raise Exception(
                "pyVisa or VISA is missing on this computer, install one or both")
        if visa_address_string.lower().startswith('gpib'):
            print('\n\n\n\n\nDo not add gpib over visa directly for compatability with non visa framwork iterfaces')
            print(' for example replace: ')
            print('       .create_visa_interface("GBPIB0::5")')
            print(' with:')
            print('       .set_gpib_adapter_visa(0) # this can only be done once for 0')
            print(
                '       .create_visa_gpib_interface(gpib_adapter_number=0,gpib_address_number=5)')
            raise Exception('User Error - see above text')
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_direct(visa_address_string, timeout)
        new_interface.set_com_node_parent(self._visa_root)
        self._direct_visa_interfaces.append(new_interface)
        return new_interface

    def get_visa_gpib_interface(
            self, gpib_adapter_number, gpib_address_number, timeout=None):
        """Return the visa gpib interface.
        Returns the stored visa gpib interface from the object's internal
        state.

        Returns the stored visa gpib interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_gpib_interface')
        True

        Args:
            gpib_adapter_number: Gpib adapter number to use.
            gpib_address_number: Gpib address number to use.
            timeout: Timeout in seconds.

        Returns:
            The current visa gpib interface.

        Raises:
            Exception: If an unexpected error occurs.
        """
        timeout = self._set_timeout(timeout)
        if visaMissing:
            raise Exception(
                "pyVisa or VISA is missing on this computer, install one or both. Cannot use visa for GPIB adapter")
        if gpib_adapter_number in list(self._gpib_adapters.keys()):
            if self._gpib_adapters[gpib_adapter_number]._parent == self._visa_root:
                raise Exception(
                    f"Attempting to re-define gpib adapter: {gpib_adapter_number}, the same way a second time.")
            else:
                raise Exception(
                    f"GPIB adapter_number {gpib_adapter_number} was already defined as something other than visa.")
        adapter = gpib_adapter_visa()
        adapter.set_com_node_thread_safe()
        adapter.set_com_node_parent(self._visa_root)
        self._gpib_adapters[gpib_adapter_number] = adapter
        if gpib_adapter_number not in self._gpib_interfaces:
            self._gpib_interfaces[gpib_adapter_number] = {}
        if gpib_adapter_number in self._gpib_interfaces:
            if gpib_address_number in self._gpib_interfaces[gpib_adapter_number]:
                interface = self._gpib_interfaces[gpib_adapter_number][gpib_address_number]
                if timeout > interface.timeout:
                    interface.timeout = timeout
                return interface
        this_gpib_adapter = self._gpib_adapters[gpib_adapter_number]
        assert isinstance(this_gpib_adapter, gpib_adapter)
        new_interface = self._get_gpib_interface(
            gpib_adapter=this_gpib_adapter,
            gpib_adapter_number=gpib_adapter_number,
            gpib_address_number=gpib_address_number,
            timeout=timeout)
        new_interface.set_com_node_parent(this_gpib_adapter)
        self._gpib_interfaces[gpib_adapter_number][gpib_address_number] = new_interface
        return new_interface

    def set_gpib_adapter_visa(self, adapter_number):
        """Deprectaed, I put this stuff in .get_visa_gpib_interface() since it asked for an adapter number anyway.

        Updates the gpib adapter visa in the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'set_gpib_adapter_visa')
        True

        Args:
            adapter_number: Adapter number to use.
        """
    def _get_gpib_interface(
            self, gpib_adapter, gpib_adapter_number, gpib_address_number, timeout):
        if isinstance(gpib_adapter, gpib_adapter_visa):
            visa_address_string = f"GPIB{gpib_adapter_number}::{gpib_address_number}"
            new_interface = interface_visa_direct(visa_address_string, timeout)
        else:
            raise Exception(
                f"{self._get_gpib_interface} received unexpected/unimplemented gpib_adapter argument of type {type(gpib_adapter)}.")
        return new_interface

    def get_visa_tcp_ip_interface(
            self, host_address, port, timeout=None, **kwargs):
        """Return the visa tcp ip interface.
        Returns the stored visa tcp ip interface from the object's internal
        state.

        Returns the stored visa tcp ip interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_tcp_ip_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            host_address: Network hostname or IP address of the remote host.
            port: TCP/IP port number.
            timeout: Timeout in seconds.

        Returns:
            The current visa tcp ip interface.
        """
        new_interface = interface_visa_tcp_ip(
            host_address, port, timeout, **kwargs)
        new_interface.set_com_node_parent(self)
        self._tcp_ip_interfaces.append(new_interface)
        return new_interface

    def get_visa_telnet_interface(self, host_address, port, timeout=None):
        """Return the visa telnet interface.
        Returns the stored visa telnet interface from the object's internal
        state.

        Returns the stored visa telnet interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_telnet_interface')
        True

        Args:
            host_address: Network hostname or IP address of the remote host.
            port: TCP/IP port number.
            timeout: Timeout in seconds.

        Returns:
            The current visa telnet interface.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if telnetlibMissing:
            raise Exception("telnetlib is missing on this computer")
        new_interface = interface_visa_telnet(host_address, port, timeout)
        new_interface.set_com_node_parent(self)
        self._telnet_interfaces.append(new_interface)
        return new_interface

    def get_visa_vxi11_interface(self, address, timeout):
        """Return the visa vxi11 interface.
        Returns the stored visa vxi11 interface from the object's internal
        state.

        Returns the stored visa vxi11 interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_vxi11_interface')
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.

        Returns:
            The current visa vxi11 interface.
        """
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_vxi11(address, timeout)
        new_interface.set_com_node_parent(self)
        self._vxi11_interfaces.append(new_interface)
        return new_interface

    def get_visa_usbtmc_interface(self, address, timeout):
        """Return the visa usbtmc interface.
        Returns the stored visa usbtmc interface from the object's internal
        state.

        Returns the stored visa usbtmc interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_usbtmc_interface')
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.

        Returns:
            The current visa usbtmc interface.
        """
        timeout = self._set_timeout(timeout)
        new_interface = interface_visa_usbtmc(address, timeout)
        new_interface.set_com_node_parent(self)
        self._usbtmc_interfaces.append(new_interface)
        return new_interface

    def get_visa_serial_interface(
            self, serial_obj_or_port_name, baudrate=None, timeout=None, **kwargs):
        """Return the visa serial interface.
        Returns the stored visa serial interface from the object's internal
        state.

        Returns the stored visa serial interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_visa_serial_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            baudrate: Serial baud rate in bits per second.
            serial_obj_or_port_name: Serial obj or port name to use.
            timeout: Timeout in seconds.

        Returns:
            The current visa serial interface.
        """
        timeout = self._set_timeout(timeout)
        if isinstance(serial_obj_or_port_name, str):
            rawser = self.get_raw_serial_interface(
                serial_obj_or_port_name, baudrate, timeout, **kwargs)
        elif isinstance(serial_obj_or_port_name, interface_raw_serial):
            rawser = serial_obj_or_port_name
        else:
            raise TypeError(f"serial_obj_or_port_name must be a str or interface_raw_serial, got {type(serial_obj_or_port_name)}")
        new_interface = interface_visa_serial(rawser)
        new_interface.set_com_node_parent(rawser)
        self._visa_serial_interfaces.append(new_interface)
        return new_interface

    def get_raw_serial_interface(
            self, serial_port_name, baudrate=None, timeout=None, **kwargs):
        """Return the raw serial interface.
        Returns the stored raw serial interface from the object's internal
        state.

        Returns the stored raw serial interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_raw_serial_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            baudrate: Serial baud rate in bits per second.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current raw serial interface.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if serialMissing:
            raise Exception("pySerial is missing on this computer")
        timeout = self._set_timeout(timeout)
        for interface in self._raw_serial_interfaces:
            if interface.get_serial_port_name() == serial_port_name:
                if (baudrate != interface.baudrate) and (baudrate is not None):
                    raise Exception(
                        f"Tried to create a second connection to serial port {serial_port_name} with different baudrate")
                if timeout > interface.timeout:
                    interface.timeout = timeout  # auto extend time outs
                return interface
        new_interface = interface_raw_serial(
            serial_port_name, baudrate, timeout, **kwargs)
        new_interface.set_com_node_parent(self)
        # serial ports as we use them are not thread safe and never will be
        self._raw_serial_interfaces.append(new_interface)
        return new_interface

    def get_tcp_serial_interface(
            self, dest_ip_address, dest_tcp_portnum, timeout):
        """Return the tcp serial interface.
        Returns the stored tcp serial interface from the object's internal
        state.

        Returns the stored tcp serial interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_tcp_serial_interface')
        True

        Args:
            dest_ip_address: Dest ip address to use.
            dest_tcp_portnum: Dest tcp portnum to use.
            timeout: Timeout in seconds.

        Returns:
            The current tcp serial interface.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if serialMissing:
            raise Exception("pySerial is missing on this computer")
        timeout = self._set_timeout(timeout)
        new_interface = interface_tcp_serial(dest_ip_address, dest_tcp_portnum)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_interface_test_harness_serial(
            self, serial_port_name, bytestream, timeout=1.0, max_bytes_returned_per_read=7):
        """Get a PyICified SerialTestHarness, a hardware-free PySerial serial.Serial.

        emulator that provides a read() method and a writable timeout property.
        bytestream is a generator function that yields one byte
        of test stimulus each time its next() method is called.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_interface_test_harness_serial')
        True

        Args:
            bytestream: Bytestream to use.
            max_bytes_returned_per_read: Max bytes returned per read to use.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current interface test harness serial.
        """
        timeout = self._set_timeout(timeout)
        new_interface = interface_test_harness_serial(
            serial_port_name, bytestream, max_bytes_returned_per_read)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_interface_libusb(self, idVendor=0x1272,
                             idProduct=0x8004, timeout=1):
        """Return the interface libusb.
        Returns the stored interface libusb from the object's internal state.

        Returns the stored interface libusb from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_interface_libusb')
        True

        Args:
            idProduct: Idproduct to use.
            idVendor: Idvendor to use.
            timeout: Timeout in seconds.

        Returns:
            The current interface libusb.
        """
        new_interface = interface_libusb(
            idVendor=0x1272, idProduct=0x8004, timeout=1)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_interface_stream_serial(self, interface_raw_serial):
        """Return the interface stream serial.
        Returns the stored interface stream serial from the object's internal
        state.

        Returns the stored interface stream serial from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_interface_stream_serial')
        True

        Args:
            interface_raw_serial: Raw serial interface instance for communication.

        Returns:
            The current interface stream serial.
        """
        new_interface = interface_stream_serial(interface_raw_serial)
        new_interface.set_com_node_parent(interface_raw_serial)
        return new_interface

    def get_interface_ftdi_d2xx(self):
        # need some kind of device descriptor....
        """Return the interface ftdi d2xx.
        Returns the stored interface ftdi d2xx from the object's internal
        state.

        Returns the stored interface ftdi d2xx from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_interface_ftdi_d2xx')
        True

        Returns:
            The current interface ftdi d2xx.
        """
        new_interface = interface_ftdi_d2xx()  # pylint: disable=abstract-class-instantiated; interface_ftdi_d2xx is an intentional stub class awaiting implementation of abstract methods
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_twi_dummy_interface(self, delay=0, timeout=None, **kwargs):
        """Return the twi dummy interface.
        Returns the stored twi dummy interface from the object's internal
        state.

        Returns the stored twi dummy interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_dummy_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            delay: Delay time in seconds.
            timeout: Timeout in seconds.

        Returns:
            The current twi dummy interface.
        """
        new_interface = interface_twi_dummy(delay, **kwargs)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_twi_mdump_interface(self, data_source, **kwargs):
        """Return the twi mdump interface.
        Returns the stored twi mdump interface from the object's internal
        state.

        Returns the stored twi mdump interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_mdump_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            data_source: Data source to use.

        Returns:
            The current twi mdump interface.
        """
        new_interface = interface_twi_mdump(data_source, **kwargs)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_twi_scpi_interface(
            self, serial_port_name, baudrate=None, timeout=None):
        """Return the twi scpi interface.
        Returns the stored twi scpi interface from the object's internal
        state.

        Returns the stored twi scpi interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_scpi_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current twi scpi interface.
        """
        serial = self.get_visa_serial_interface(
            serial_port_name, baudrate, timeout)
        new_interface = interface_twi_scpi(serial, timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface

    def get_twi_scpi_sp_interface(self, serial_port_name, portnum,
                                  sclpin, sdapin, pullup=False, baudrate=None, timeout=None):
        """Return the twi scpi sp interface.
        Returns the stored twi scpi sp interface from the object's internal
        state.

        Returns the stored twi scpi sp interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_scpi_sp_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            portnum: Portnum to use.
            pullup: Pullup to use.
            sclpin: Sclpin to use.
            sdapin: Sdapin to use.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current twi scpi sp interface.
        """
        serial = self.get_visa_serial_interface(
            serial_port_name, baudrate, timeout)
        new_interface = interface_twi_scpi_sp(
            interface_serial=serial,
            portnum=portnum,
            sclpin=sclpin,
            sdapin=sdapin,
            pullup_en=pullup,
            timeout=timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface

    def get_twi_scpi_testhook_interface(
            self, serial_port_name, baudrate=None, timeout=None):
        """Return the twi scpi testhook interface.
        Returns the stored twi scpi testhook interface from the object's
        internal state.

        Returns the stored twi scpi testhook interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_scpi_testhook_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current twi scpi testhook interface.
        """
        serial = self.get_visa_serial_interface(
            serial_port_name, baudrate, timeout)
        new_interface = interface_twi_scpi_testhook(serial, timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface

    def get_twi_dc590_serial(self, serial_port_name,
                             baudrate=None, timeout=None):
        """Return the twi dc590 serial.
        Returns the stored twi dc590 serial from the object's internal state.

        Returns the stored twi dc590 serial from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_dc590_serial')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current twi dc590 serial.
        """
        if baudrate is None:
            baudrate = 115200  # DC590/Linduino default
        serial = self.get_raw_serial_interface(
            serial_port_name, baudrate, timeout)
        stream = self.get_interface_stream_serial(serial)
        new_interface = interface_twi_dc590_serial(stream, timeout)
        new_interface.set_com_node_parent(stream)
        return new_interface

    def get_twi_buspirate_interface(
            self, serial_port_name, baudrate=None, timeout=None):
        """Return the twi buspirate interface.
        Returns the stored twi buspirate interface from the object's internal
        state.

        Returns the stored twi buspirate interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_buspirate_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            timeout: Timeout in seconds.

        Returns:
            The current twi buspirate interface.
        """
        serial = self.get_raw_serial_interface(
            serial_port_name, baudrate, timeout)
        new_interface = interface_twi_buspirate(serial, timeout)
        new_interface.set_com_node_parent(serial)
        return new_interface

    def get_twi_kernel_interface(self, bus_number):
        """Return the twi kernel interface.
        Returns the stored twi kernel interface from the object's internal
        state.

        Returns the stored twi kernel interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_kernel_interface')
        True

        Args:
            bus_number: Bus number to use.

        Returns:
            The current twi kernel interface.
        """
        new_interface = interface_twi_kernel(bus_number)  # type: ignore[possibly-undefined]  # noqa: F821 # pylint: disable=undefined-variable; class was removed from this module but method retained for API compatibility
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_twi_firmata_interface(self, firmata_instance):
        # Old. Consider Telemetrix instead.
        """Return the twi firmata interface.
        Returns the stored twi firmata interface from the object's internal
        state.

        Returns the stored twi firmata interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_firmata_interface')
        True

        Args:
            firmata_instance: Firmata instance to use.

        Returns:
            The current twi firmata interface.
        """
        new_interface = interface_twi_firmata(firmata_instance)
        new_interface.set_com_node_parent(self)
        return new_interface

    def get_twi_bobbytalk_raw_serial(self, serial_port_name, src_id, baudrate=None,
                                     fifo_size=16 * (2**16), debug=False, **kwargs):
        """Serial_port_name:  "COM27" or "/dev/ttyS01", for example.

        src_id: 16-bit integer to use as the default source ID in outgoing bobbytalk packets.
        baudrate: sets the serial link baudrate.
        fifo_size: sets the size, in bytes, of the FIFO used to buffer packets
        coming in over the serial link for packet validation, parsing , and dispatch.
        **kwargs: All other keyword arguments are passed to the twi_interface.i2c_bobbytalk constructor,
        allowing optional settings like dest_id (defaults to 0x0020 SMBUS module),
        recv_timeout, cmd_retries, per_cmd_recv_retries...
        For testing purposes, if a lab_interface.interface object is passed as the serial_port_name
        argument, it will be used as if it were a PySerial serial.Serial object. This allows
        injection of test bytes and other stimuli to the bobbytalk parser.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_bobbytalk_raw_serial')
        True

        Args:
            **kwargs: Additional keyword arguments.
            baudrate: Serial baud rate in bits per second.
            debug: If True, enable debug output.
            fifo_size: Fifo size to use.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            src_id: Source identifier.

        Returns:
            The current twi bobbytalk raw serial.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        if baudrate is None:
            baudrate = 115200  # bobbytalk Firmware default
        if isinstance(serial_port_name, str):
            raw_serial_intf = self.get_raw_serial_interface(
                serial_port_name, baudrate)
        elif isinstance(serial_port_name, interface):
            # testhook: allows interface_test_harness_serial
            raw_serial_intf = serial_port_name
        else:
            raise ValueError(f"lab_interfaces.get_twi_bobbytalk_raw_serial() called with "
                             f"first argument {repr(serial_port_name)}{type(serial_port_name)},\nwhich is neither "
                             "a (Unicode string) name of a serial port, nor an interface object")
        lc_intf = interface_bobbytalk_raw_serial(
            raw_serial_intf, fifo_size=fifo_size, debug=debug)
        lc_intf.set_com_node_parent(raw_serial_intf)
        twi_intf = interface_twi_bobbytalk(
            lc_intf, src_id, debug=debug, **kwargs)
        twi_intf.set_com_node_parent(lc_intf)
        return twi_intf

    def get_twi_bobbytalk_tcp(self, dest_ip_address, dest_tcp_portnum, src_id, timeout=0.3,
                              fifo_size=16 * (2**16), debug=False, **kwargs):
        """Talk bobbytalk over TCP/IP given a destination IP address and TCP port number.

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
        is ignored. This allows injection of test bytes and other stimuli to the bobbytalk parser.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_twi_bobbytalk_tcp')
        True

        Args:
            **kwargs: Additional keyword arguments.
            debug: If True, enable debug output.
            dest_ip_address: Dest ip address to use.
            dest_tcp_portnum: Dest tcp portnum to use.
            fifo_size: Fifo size to use.
            src_id: Source identifier.
            timeout: Timeout in seconds.

        Returns:
            The current twi bobbytalk tcp.
        """
        if isinstance(dest_ip_address, str):
            serial_intf = self.get_tcp_serial_interface(
                dest_ip_address, dest_tcp_portnum, timeout)
        elif isinstance(dest_ip_address, interface):
            # testhook: allows interface_test_harness_serial
            serial_intf = dest_ip_address
        else:
            raise TypeError(f"dest_ip_address must be a str or interface, got {type(dest_ip_address)}")
        lc_intf = interface_bobbytalk_raw_serial(
            serial_intf, fifo_size=fifo_size, debug=debug)
        lc_intf.set_com_node_parent(serial_intf)
        twi_intf = interface_twi_bobbytalk(
            lc_intf, src_id, debug=debug, **kwargs)
        twi_intf.set_com_node_parent(lc_intf)
        return twi_intf

    def get_labcomm_raw_interface(
            self, comport_name, src_id, dest_id, baudrate, timeout):
        """Return the labcomm raw interface.
        Returns the stored labcomm raw interface from the object's internal
        state.

        Returns the stored labcomm raw interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_labcomm_raw_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            comport_name: Comport name to use.
            dest_id: Destination identifier.
            src_id: Source identifier.
            timeout: Timeout in seconds.

        Returns:
            The current labcomm raw interface.
        """
        rawser = self.get_raw_serial_interface(comport_name, baudrate, timeout)
        new_interface = interface_labcomm_raw_serial(
            rawser, comport_name, src_id, dest_id)
        new_interface.set_com_node_parent(rawser)
        return new_interface

    def get_labcomm_twi_interface(
            self, comport_name, src_id, dest_id, baudrate, timeout):
        """Return the labcomm twi interface.
        Returns the stored labcomm twi interface from the object's internal
        state.

        Returns the stored labcomm twi interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_labcomm_twi_interface')
        True

        Args:
            baudrate: Serial baud rate in bits per second.
            comport_name: Comport name to use.
            dest_id: Destination identifier.
            src_id: Source identifier.
            timeout: Timeout in seconds.

        Returns:
            The current labcomm twi interface.
        """
        rawser = self.get_raw_serial_interface(comport_name, baudrate, timeout)
        new_interface = interface_labcomm_twi_serial(
            rawser, comport_name, src_id, dest_id)
        new_interface.set_com_node_parent(rawser)
        return new_interface

    def get_spi_dummy_interface(self, delay=0):
        """Return the spi dummy interface.
        Returns the stored spi dummy interface from the object's internal
        state.

        Returns the stored spi dummy interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_spi_dummy_interface')
        True

        Args:
            delay: Delay time in seconds.

        Returns:
            The current spi dummy interface.
        """
        iface_spi = interface_spi_dummy(delay)
        iface_spi.set_com_node_parent(self)
        return iface_spi

    def get_spi_dc590_interface(
            self, serial_port_name, uart_baudrate=None, uart_timeout=None, ss_ctrl=None, **kwargs):
        """Return the spi dc590 interface.
        Returns the stored spi dc590 interface from the object's internal
        state.

        Returns the stored spi dc590 interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_spi_dc590_interface')
        True

        Args:
            **kwargs: Additional keyword arguments.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            ss_ctrl: Slave-select control mode or pin assignment.
            uart_baudrate: Uart baudrate to use.
            uart_timeout: Uart timeout to use.

        Returns:
            The current spi dc590 interface.
        """
        if uart_baudrate is None:
            uart_baudrate = 115200  # DC590/Linduino default
        iface_serial = self.get_raw_serial_interface(
            serial_port_name, baudrate=uart_baudrate, timeout=uart_timeout, **kwargs)
        iface_stream = self.get_interface_stream_serial(iface_serial)
        iface_spi = interface_spi_dc590(iface_stream, ss_ctrl)
        iface_spi.set_com_node_parent(iface_serial)
        return iface_spi

    def get_spi_cfgpro_interface(
            self, serial_port_name, uart_timeout=None, CPOL=0, CPHA=0, spi_baudrate=1e6, ss_ctrl=None):
        """The configurator Pro (or XT) is an ADI specific breakout board that interfaces test equipment and ICs in a semi-standardized manner.
        Returns the stored spi cfgpro interface from the object's internal
        state.

        Returns the stored spi cfgpro interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_spi_cfgpro_interface')
        True

        Args:
            CPHA: Clock phase.
            CPOL: Clock polarity.
            serial_port_name: Serial port identifier (e.g. ``"COM3"`` or ``"/dev/ttyUSB0"``).
            spi_baudrate: Spi baudrate to use.
            ss_ctrl: Slave-select control mode or pin assignment.
            uart_timeout: Uart timeout to use.

        Returns:
            The current spi cfgpro interface.
        """
        iface_visa_serial = self.get_visa_serial_interface(
            serial_port_name, timeout=uart_timeout)
        iface_spi = interface_spi_cfgpro(
            iface_visa_serial, CPOL, CPHA, spi_baudrate, ss_ctrl)
        iface_spi.set_com_node_parent(iface_visa_serial)
        return iface_spi

    def get_dummy_interface(self, parent=None, name='dummy interface'):
        """Used only for testing the core lab functions.
        Returns the stored dummy interface from the object's internal state.

        Returns the stored dummy interface from the object's internal state.


        >>> from PyICe.lab_interfaces import interface_factory
        >>> hasattr(interface_factory, 'get_dummy_interface')
        True

        Args:
            name: Name identifier.
            parent: Parent object in the hierarchy.

        Returns:
            The current dummy interface.
        """
        new_interface = interface(name)
        if parent is None:
            new_interface.set_com_node_parent(self)
        else:
            new_interface.set_com_node_parent(parent)
        return new_interface

    def _set_timeout(self, timeout):
        if timeout is None:
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
    for i in c_root.group_com_nodes_for_threads_filter([c_b, c_a, c_ca, c_cb]):
        print('--------------------')
        print(i)
