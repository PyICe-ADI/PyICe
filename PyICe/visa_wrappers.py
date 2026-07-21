"""VISA emulation wrappers for physical instrument interfaces.

>>> from PyICe.visa_wrappers import strify

"""
import traceback
import struct
import re
import logging
debug_logging = logging.getLogger(__name__)
dbgprint = debug_logging.debug
try:
    import pyvisa as visa  # pylint: disable=import-error; optional dependency guarded by try/except
    visaMissing = False
except BaseException:
    visa = None  # type: ignore[assignment]
    visaMissing = True
try:
    ctypesMissing = False
except BaseException:
    ctypesMissing = True
try:
    import serial  # pylint: disable=import-error; optional dependency guarded by try/except
    serialMissing = False
except BaseException:
    serial = None  # type: ignore[assignment]
    serialMissing = True
try:
    import vxi11  # pylint: disable=import-error; optional dependency guarded by try/except
    vxi11Missing = False
except BaseException:
    vxi11 = None  # type: ignore[assignment]
    vxi11Missing = True
try:
    import usbtmc  # pylint: disable=import-error; optional dependency guarded by try/except
    usbtmcMissing = False
except BaseException:
    usbtmc = None  # type: ignore[assignment]
    usbtmcMissing = True
try:
    import telnetlib  # pylint: disable=import-error; optional dependency guarded by try/except
    telnetlibMissing = False
except BaseException:
    telnetlib = None  # type: ignore[assignment]
    telnetlibMissing = True

# Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
# be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
# if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
str_encoding = 'latin-1'


def strify(bs):
    """Convert a bytes object to a str using latin-1 encoding.

    Used throughout the VISA wrapper layer to normalize instrument responses
    into Python str objects. Latin-1 is used because it provides a lossless
    round-trip for all single-byte values (0x00–0xFF), which is essential
    for binary instrument data that may contain arbitrary byte values.

    >>> strify(b'hello')
    'hello'
    >>> strify(b'\\xff\\x00\\x80')  # arbitrary bytes round-trip safely
    '\\xff\\x00\\x80'
    >>> strify('already a string')  # strings pass through with a warning
    Unexpected stringification of non-byte string: already a string. Contact PyICe-developers@analog.com for more information.
    'already a string'

    Args:
        bs: A bytes-like object to decode, or a str that passes through
            with a diagnostic warning.

    Returns:
        The decoded string (latin-1), or the original str if already a string.
    """
    if not isinstance(bs, str):
        return bs.decode(str_encoding)
    else:
        print(
            f"Unexpected stringification of non-byte string: {bs}. Contact PyICe-developers@analog.com for more information.")
        return bs


def byteify(s):
    """Convert a str to bytes using latin-1 encoding.

    The inverse of ``strify``. Used when instrument drivers need to send
    raw byte data over a serial or TCP link that expects bytes objects.
    Latin-1 encoding preserves all single-byte code points losslessly.

    >>> byteify('hello')
    b'hello'
    >>> byteify('\\xff\\x00\\x80')  # arbitrary code points round-trip safely
    b'\\xff\\x00\\x80'
    >>> byteify(b'already bytes')  # bytes pass through with a warning
    Unexpected byteification of byte string: b'already bytes'. Contact PyICe-developers@analog.com for more information.
    b'already bytes'

    Args:
        s: A string to encode, or a bytes object that passes through
            with a diagnostic warning.

    Returns:
        The encoded bytes (latin-1), or the original bytes if already bytes.
    """
    if isinstance(s, str):
        return s.encode(str_encoding)
    else:
        print(
            f"Unexpected byteification of byte string: {s}. Contact PyICe-developers@analog.com for more information.")
        return s


class visaWrapperException(Exception):
    """Exception raised by VISA wrapper classes on communication errors.

    Raised when serial timeouts occur during reads, when binary transfer
    headers are malformed, or when other transport-level failures happen
    in the wrapper layer. Catching this exception (rather than generic
    Exception) lets callers distinguish wrapper-level I/O problems from
    instrument-level errors.

    >>> raise visaWrapperException('Serial timeout on port COM3!')
    Traceback (most recent call last):
        ...
    PyICe.visa_wrappers.visaWrapperException: Serial timeout on port COM3!
    """
    pass


class visa_wrapper(object):
    """Abstract base class defining the VISA-like instrument interface.

    Provides the common API surface (read, write, ask, trigger, clear, etc.)
    that all concrete wrapper subclasses must implement. Methods raise
    ``NotImplementedError`` by default so that any unimplemented transport
    operation fails loudly rather than silently returning garbage.

    Subclass one of the concrete wrappers (``visa_wrapper_serial``,
    ``visa_wrapper_tcp``, ``visa_wrapper_vxi11``, ``visa_wrapper_usbtmc``,
    ``visa_wrapper_telnet``) or ``visa_interface`` for real VISA libraries.

    >>> from PyICe.visa_wrappers import visa_wrapper
    >>> visa_wrapper is not None
    True

    """
    #    def __init__(self, address, timeout=5):
    #        raise NotImplementedError('Interface Not Fully Implemented: __init__()')
    def read(self):
        """Read a response string from the instrument.

        Subclasses must override this to receive data from the physical
        transport (serial, TCP, VXI-11, etc.) and return it as a string
        with trailing whitespace stripped.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'read')
        True

        Raises:
            NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError('Interface Not Fully Implemented: read()')

    def write(self, message):
        """Send a command or data string to the instrument.

        Subclasses must override this to transmit the message over their
        physical transport. The termination character is typically appended
        automatically by the subclass implementation.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'write')
        True

        Args:
            message: The SCPI command or data string to send.

        Raises:
            NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError('Interface Not Fully Implemented: write()')

    def read_values(self):
        """Read a comma-separated ASCII response and parse into a list of values.

        Used when an instrument returns measurement data as a comma-delimited
        ASCII string (e.g. ``"1.23,4.56,7.89\\n"``). Subclasses override to
        split and convert the response into a list of floats or strings.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'read_values')
        True

        Raises:
            NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError(
            'Interface Not Fully Implemented: read_values()')

    def read_values_binary(self, format_str='=B',
                           byte_order='=', terminationCharacter=''):
        """Read binary data in IEEE 488.2 Definite Length Arbitrary Block format.

        Parses the ``#<header_len><data_len><data>`` framing used by most
        SCPI instruments for bulk binary transfers (waveforms, screenshots,
        register dumps). The ``format_str`` and ``byte_order`` arguments are
        forwarded to ``struct.unpack`` to decode the raw bytes into numeric
        values. See https://docs.python.org/3/library/struct.html for format
        codes.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'read_values_binary')
        True

        Args:
            format_str: ``struct`` format character describing one data
                element (e.g. ``'B'`` for unsigned byte, ``'f'`` for float).
            byte_order: ``struct`` byte-order character (``'='`` native,
                ``'<'`` little-endian, ``'>'`` big-endian).
            terminationCharacter: Expected trailing character(s) after the
                binary payload (often empty or ``'\\n'``).

        Raises:
            NotImplementedError: Always; subclasses must override.
        """
        raise NotImplementedError(
            'Interface Not Fully Implemented: read_values_binary()')

    def ask(self, message):
        """Send a query and return the instrument's response.

        Convenience method that calls ``write(message)`` followed by
        ``read()``. This is the most common pattern for SCPI query commands
        (e.g. ``'*IDN?'``).


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'ask')
        True

        Args:
            message: The SCPI query string to send (typically ending in ``?``).

        Returns:
            The instrument's response string with trailing whitespace stripped.
        """
        self.write(message)
        return self.read()

    def ask_for_values(self, message):
        """Send a query and return the response parsed as a list of values.

        Combines ``write(message)`` and ``read_values()`` into a single call.
        Useful for SCPI queries that return comma-separated numeric data
        (e.g. ``'MEAS:VOLT?'`` on a multi-channel instrument).


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'ask_for_values')
        True

        Args:
            message: The SCPI query string to send.

        Returns:
            A list of parsed values from the instrument response.
        """
        self.write(message)
        return self.read_values()

    def ask_for_values_binary(
            self, message, format_str='B', byte_order='=', terminationCharacter=''):
        """Send a query and read the response as IEEE 488.2 binary block data.

        Combines ``write_raw(message)`` and ``read_values_binary()`` into a
        single call. The message must be a bytes object because it is sent
        via ``write_raw`` without termination-character processing.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'ask_for_values_binary')
        True

        Args:
            message: The SCPI query as a bytes object (e.g. ``b'CURV?\\n'``).
            format_str: ``struct`` format character for one data element.
            byte_order: ``struct`` byte-order character (``'='``, ``'<'``, or
                ``'>'``).
            terminationCharacter: Expected trailing character(s) after the
                binary payload.

        Returns:
            A tuple of unpacked numeric values from the binary response.
        """
        assert isinstance(message, bytes)
        self.write_raw(message)  # pylint: disable=no-member; write_raw is defined in subclasses (visa_wrapper_serial, visa_wrapper_vxi11, etc.) that actually use this method
        return self.read_values_binary(
            format_str, byte_order, terminationCharacter)

    def clear(self):
        """Clear buffered data and status registers.

        Restores the object or hardware to its default state.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'clear')
        True

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError('Interface Not Fully Implemented: clear()')

    def clear_errors(self):
        """Perform clear errors operation.

        Restores the object or hardware to its default state.

        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'clear_errors')
        True

        """
        print("Interface Not Fully Implemented: clear_errors()'")

    def trigger(self):
        """Run the trigger step.

        Initiates the action and notifies any registered observers.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'trigger')
        True

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError('Interface Not Fully Implemented: trigger()')

    def read_raw(self):
        """Perform read raw operation.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'read_raw')
        True

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError(
            'Interface Not Fully Implemented: read_raw()')

    def resync(self):
        """Flush buffers to resync after communication fault - usb-serial problem.

        Brings the cached state into agreement with the authoritative source.


        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'resync')
        True

        Returns:
            True if resynchronization succeeded.
        """
        return ''

    def close(self):
        """Close the connection and release resources.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.visa_wrappers import visa_wrapper
        >>> hasattr(visa_wrapper, 'close')
        True

        """
        pass

    def __getTimeout(self):
        raise NotImplementedError('Interface Not Fully Implemented: timeout')

    def __setTimeout(self, timeout):
        raise NotImplementedError('Interface Not Fully Implemented: timeout')
    timeout = property(__getTimeout, __setTimeout)

    def __getTerminationChars(self):
        raise NotImplementedError(
            'Interface Not Fully Implemented: term_chars')

    def __setTerminationChars(self, term_chars):
        raise NotImplementedError(
            'Interface Not Fully Implemented: term_chars')
    term_chars = property(__getTerminationChars, __setTerminationChars)


# Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
# be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
# if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])
str_encoding = 'latin-1'


class visa_wrapper_serial(visa_wrapper):
    """Visa_wrapper_serial.

    >>> from PyICe.visa_wrappers import visa_wrapper_serial
    >>> visa_wrapper_serial is not None
    True

    """
    def __init__(self, address_or_serial_obj,
                 timeout=5, baudrate=9600, **kwargs):
        """Initialize visa_wrapper_serial.
        Calls the parent class constructor and initializes instance-specific
        attributes for visa_wrapper_serial.

        Calls the parent constructor to inherit base behavior, and initializes 6 instance attributes that configure the object's behavior.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, '__init__')
        True

        Args:
            **kwargs: Additional keyword arguments.
            address_or_serial_obj: Address or serial obj to use.
            baudrate: Serial baud rate in bits per second.
            timeout: Timeout in seconds.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        serial_port_name = "(nameless serial port)"
        if isinstance(address_or_serial_obj, serial.SerialBase):
            self.ser = address_or_serial_obj
            serial_port_name = self.ser.port
        # TODO: migrate telnet library to use serial_for_url
        # rfc2217://<host>:<port>[?<option>[&<option>]] class rfc2217.Serial
        elif isinstance(address_or_serial_obj, telnetlib.Telnet):
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
            # self.terminationCharacter = "\n".encode(str_encoding) # readline
            # inherits from "io" which doesn't support termination character
            # readline inherits from "io" which doesn't support termination
            # character
            self.terminationCharacter = "\n"
        super().__init__(serial_port_name, **kwargs)
        self.serial_port_name = serial_port_name
        self.resync()

    def readline(self):
        # TODO: speed this up using buffered IO to wrap serial port
        # readline() of ser doesn't work correctly
        # https://docs.python.org/2/library/io.html#io.TextIOWrapper
        # http://pyserial.readthedocs.org/en/latest/shortintro.html#eol
        """Return the readline.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'readline')
        True

        Returns:
            The value read from the device or channel.

        Raises:
            visaWrapperException: If the operation fails.
        """
        dbgprint(
            "vvv-- visa_wrapper_serial.readline({}) entered".format(self.serial_port_name))
        # response = bytes()
        response = str()
        while True:
            char = self.ser.read(1)
            response += char
            if char == self.terminationCharacter:
                break
            elif len(char) == 0:
                raise visaWrapperException(
                    "Serial timeout on port {}!".format(
                        self.ser.port))
                # print "Serial timeout on port {}!".format(self.ser.port)
        dbgprint("^^^-- visa_wrapper_serial.readline({}) returns "
                 "{}".format(self.serial_port_name, repr(response)))
        return response
        # return strify(response)

    def read(self):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'read')
        True

        Returns:
            The value read from the device or channel.
        """
        dbgprint(
            "vvv-- visa_wrapper_serial.read({}) entered".format(self.serial_port_name))
        message = self.readline().rstrip()
        dbgprint("^^^-- visa_wrapper_serial.read({}) returns "
                 "{}".format(self.serial_port_name, repr(message)))
        return message

    def write(self, message):
        """Write a value to the channel.
        Sends the ``Unexpected`` SCPI command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'write')
        True

        Args:
            message: Human-readable message string.

        Raises:
            Exception: If an unexpected error occurs.
        """
        dbgprint("vvv-- visa_wrapper.serial.write({}, {}) "
                 "entered".format(self.serial_port_name, repr(message)))
        if isinstance(message, str):
            pass
        elif isinstance(message, (bytes, bytearray)):
            print("Unexpected byte array in visa_wrapper_serial.write. Contact PyICe-developers@analog.com for more information.")
            message = strify(message)
            # 2020-06-08 DJS: VISA itself seems to handle Unicode strings
            # silently and correctly, so we probably should too. Disabling
            # Frank's message. No reason to manage bytestrings manually within
            # instrument drivers.
            if False:  # Helpful for debugging during Python 2 to 3 porting.
                print(
                    "*** visa_wrapper_serial.write() was passed a Unicode str instead of bytes.")
                print("    {}{}".format(repr(message), type(message)))
                print()
                traceback.print_stack()
                print()
                print(
                    "I will convert str to bytes for you using {} encoding.".format(str_encoding))
                print("*" * 76)
                # input("Press ENTER to continue")
        else:
            raise Exception(
                f"Unexpected visa_wrapper_serial.write message type: {type(message)}")
        if self.terminationCharacter is not None:
            message = message.rstrip() + self.terminationCharacter
        self.ser.write(message)
        dbgprint("^^^-- visa_wrapper_serial.write({}, {}) "
                 "returns".format(self.serial_port_name, repr(message)))

    def read_values(self):
        """Return read values result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'read_values')
        True

        Returns:
            The value read from the device or channel.
        """
        dbgprint(
            "vvv-- visa_wrapper_serial.read_values({}) entered".format(self.serial_port_name))
        # valtup = self.read().decode(str_encoding).split(",")
        valtup = strify(self.read()).split(",")
        dbgprint(
            "^^^-- visa_wrapper_serial.read_values({}) returns {}".format(
                self.serial_port_name, valtup))
        return valtup

    def read_values_binary(self, format_str='B',
                           byte_order='=', terminationCharacter=''):
        """Follows Definite Length Arbitrary Block format.

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


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'read_values_binary')
        True

        Args:
            byte_order: Byte order to use.
            format_str: Format str to use.
            terminationCharacter: Terminationcharacter to use.

        Returns:
            The read values binary result.

        Raises:
            visaWrapperException: If the operation fails.
        """
        dbgprint(
            "vvv-- visa_wrapper_serial.read_values_binary({}) entered".format(self.serial_port_name))
        hash = self.ser.read(1)
        while hash != '#':
            if len(hash):
                print(
                    'Saw extra character code: {} in read_values_binary header'.format(
                        ord(hash)))
            else:  # timeout
                raise visaWrapperException(
                    'Timeout in read_values_binary header')
            hash = self.ser.read(1)
        header_len = int(self.ser.read(1))
        data_len = int(self.ser.read(header_len))
        data = self.ser.read(data_len).encode('latin-1')
        _term = self.ser.read(len(terminationCharacter))  # noqa: F841
        format_len = struct.calcsize(format_str)
        fmt = byte_order + format_str * (data_len // format_len)
        dbgprint("^^^-- visa_wrapper_serial.read_values_binary({}) "
                 "returns struct({})".format(self.serial_port_name, repr(fmt)))
        return struct.unpack(fmt, data)

    def read_raw(self):
        """Return read raw result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'read_raw')
        True

        Returns:
            The value read from the device or channel.
        """
        dbgprint(
            "vvv-- visa_wrapper_serial.read_raw({}) entered".format(self.serial_port_name))
        dbytes = self.readline()
        dbgprint("^^^-- visa_wrapper_serial.read_raw({}) returns "
                 "{}".format(self.serial_port_name, repr(dbytes)))
        return dbytes

    def write_raw(self, message):
        """Perform write raw operation.
        Formats and sends the command to the instrument.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'write_raw')
        True

        Args:
            message: Human-readable message string.
        """
        dbgprint("vvv-- visa_wrapper.serial.write_raw({}, {}) "
                 "entered".format(self.serial_port_name, repr(message)))
        # self.ser.write(message)
        # Incoming bytes. Strify enroute to serial
        self.ser.write(strify(message))
        dbgprint("^^^-- visa_wrapper_serial.write_raw({}, {}) "
                 "returns".format(self.serial_port_name, repr(message)))

    def flush(self):
        """Run the flush step.

        Supports the ``visa_wrapper_serial`` workflow by performing the described operation.

        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'flush')
        True

        """
        print(self.ser.flush())

    def resync(self):
        """Return the resync.

        Brings the cached state into agreement with the authoritative source.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'resync')
        True

        Returns:
            True if resynchronization succeeded.
        """
        return self.ser.read(self.ser.inWaiting())

    def close(self):
        """Close the connection and release resources.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'close')
        True

        """
        self.ser.close()

    def get_serial_port(self):
        """Returns the underlying serial port object.
        Returns the stored serial port value from the object's internal state.
        Returns the stored serial port from the object's internal state.

        Returns the stored serial port from the object's internal state.


        >>> from PyICe.visa_wrappers import visa_wrapper_serial
        >>> hasattr(visa_wrapper_serial, 'get_serial_port')
        True

        Returns:
            The current serial port.
        """
        return self.ser

    def __getTimeout(self):
        return self.ser.timeout

    def __setTimeout(self, timeout):
        self.ser.timeout = timeout
    timeout = property(__getTimeout, __setTimeout)


class visa_wrapper_tcp(visa_wrapper_serial):
    """Visa_wrapper_tcp (visa_wrapper_serial subclass).

    >>> from PyICe.visa_wrappers import visa_wrapper_tcp
    >>> visa_wrapper_tcp is not None
    True

    """
    def __init__(self, ip_address, port, timeout=5, **kwargs):
        """Initialize visa_wrapper_tcp.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.visa_wrappers import visa_wrapper_tcp
        >>> visa_wrapper_tcp is not None
        True

        Args:
            **kwargs: Additional keyword arguments.
            ip_address: Ip address to use.
            port: TCP/IP port number.
            timeout: Timeout in seconds.
        """
        port = serial.serial_for_url(
            'socket://{}:{}'.format(ip_address, port), timeout=timeout)
        visa_wrapper_serial.__init__(self, port, **kwargs)

    def resync(self):
        """Return the resync.

        Brings the cached state into agreement with the authoritative source.


        >>> from PyICe.visa_wrappers import visa_wrapper_tcp
        >>> hasattr(visa_wrapper_tcp, 'resync')
        True

        Returns:
            True if resynchronization succeeded.

        Raises:
            Exception: If an unexpected error occurs.
        """
        print('TCP Resync in progress.')
        resp_all = ''
        try:
            resp = self.readline()
            resp_all += resp
            while resp[-1:] == self.terminationCharacter:
                resp = self.readline()
                resp_all += resp
        except visaWrapperException:
            pass  # visaWrapperException is expected during resync; return what we have so far
        except Exception as e:
            raise e  # what happened???
        return resp_all  # moved out of finally block; exceptions now propagate instead of being silently swallowed

    def __getTimeout(self):
        return self.ser.timeout

    def __setTimeout(self, timeout):
        self.ser.timeout = timeout
    timeout = property(__getTimeout, __setTimeout)


class visa_wrapper_telnet(visa_wrapper_serial):
    """Visa_wrapper_telnet (visa_wrapper_serial subclass).

    >>> from PyICe.visa_wrappers import visa_wrapper_telnet
    >>> visa_wrapper_telnet is not None
    True

    """
    # TODO?: migrate telnet library to use serial_for_url
    # rfc2217://<host>:<port>[?<option>[&<option>]] class rfc2217.Serial
    def __init__(self, ip_address, port, timeout=5):
        """Initialize visa_wrapper_telnet.
        Stores configuration in ``_timeout`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.visa_wrappers import visa_wrapper_telnet
        >>> visa_wrapper_telnet is not None
        True

        Args:
            ip_address: Ip address to use.
            port: TCP/IP port number.
            timeout: Timeout in seconds.
        """
        port = telnetlib.Telnet(ip_address, port, timeout=timeout)
        self._timeout = timeout
        visa_wrapper_serial.__init__(self, port)

    def resync(self):
        """Return the resync.

        Brings the cached state into agreement with the authoritative source.


        >>> from PyICe.visa_wrappers import visa_wrapper_telnet
        >>> hasattr(visa_wrapper_telnet, 'resync')
        True

        Returns:
            True if resynchronization succeeded.
        """
        return self.ser.read_very_eager()

    def readline(self):
        """Return the readline.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_telnet
        >>> hasattr(visa_wrapper_telnet, 'readline')
        True

        Returns:
            The value read from the device or channel.
        """
        response = self.ser.read_until(
            self.terminationCharacter, self._timeout)
        if response[-1] != self.terminationCharacter:
            print("Telnet timeout on port {}!".format(self.ser.port))
            # prolly should raise exception here (I am Dave)
        return response

    def __getTimeout(self):
        return self._timeout

    def __setTimeout(self, timeout):
        self._timeout = timeout
    timeout = property(__getTimeout, __setTimeout)


class visa_wrapper_vxi11(visa_wrapper):
    """Visa_wrapper_vxi11.

    >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
    >>> visa_wrapper_vxi11 is not None
    True

    """
    def __init__(self, address, timeout=5):
        """Initialize visa_wrapper_vxi11.
        Stores configuration in ``terminationCharacter``, ``vxi_interface``
        for use by other methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> visa_wrapper_vxi11 is not None
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.
        """
        self.terminationCharacter = None
        self.vxi_interface = vxi11.Instrument(  # pylint: disable=unexpected-keyword-arg; timeout is accepted by python-vxi11 Instrument constructor
            address, term_char=self.terminationCharacter, timeout=timeout)

    def read(self):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'read')
        True

        Returns:
            The value read from the device or channel.
        """
        return self.vxi_interface.read()

    def write(self, message):
        # DJS Does this needs tom strify/byteify help???
        """Write a value to the channel.

        Writes data to the underlying target.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'write')
        True

        Args:
            message: Human-readable message string.
        """
        self.vxi_interface.write(message)

    def read_values(self):
        # ascii transfer only
        # see visa.py for binary parsing example
        """Return read values result.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'read_values')
        True

        Returns:
            The value read from the device or channel.
        """
        float_regex = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\d*\.\d+)"
                                 "(?:[eE][-+]?\\d+)?")
        return [float(raw_value) for raw_value in
                float_regex.findall(self.read())]

    def ask(self, message):
        """Return the ask.

        Supports the ``visa_wrapper_vxi11`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'ask')
        True

        Args:
            message: Human-readable message string.

        Returns:
            The instrument response string.
        """
        return self.vxi_interface.ask(message)

    def ask_for_values(self, message):
        """Return ask for values result.

        Supports the ``visa_wrapper_vxi11`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'ask_for_values')
        True

        Args:
            message: Human-readable message string.

        Returns:
            List of numeric values parsed from the instrument response.
        """
        self.write(message)
        return self.read_values()

    def clear(self):
        """Clear buffered data and status registers.

        Restores the object or hardware to its default state.


        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'clear')
        True

        Raises:
            NotImplementedError: If this method is not supported by the subclass.
        """
        raise NotImplementedError('Interface Not Fully Implemented: clear()')

    def trigger(self):
        """Run the trigger step.

        Initiates the action and notifies any registered observers.

        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'trigger')
        True

        """
        self.vxi_interface.trigger()

    def read_raw(self):
        """Perform read raw operation.

        Reads data from the underlying source and returns it.

        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'read_raw')
        True

        """
        self.vxi_interface.read_raw()

    def resync(self):
        """Flush buffers to resync after communication fault - usb-serial problem.

        Brings the cached state into agreement with the authoritative source.

        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'resync')
        True

        """

    def close(self):
        """Close the connection and release resources.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'close')
        True

        """
        self.vxi_interface.close()

    def open(self):
        """Run the open step.

        Establishes the connection or prepares the resource for use.

        >>> from PyICe.visa_wrappers import visa_wrapper_vxi11
        >>> hasattr(visa_wrapper_vxi11, 'open')
        True

        """
        self.vxi_interface.open()

    def __getTimeout(self):
        return self.vxi_interface.io_timeout

    def __setTimeout(self, timeout):
        # not sure if this will actually take effect
        self.vxi_interface.io_timeout = timeout
    timeout = property(__getTimeout, __setTimeout)


class visa_wrapper_usbtmc(visa_wrapper):
    """Visa_wrapper_usbtmc.

    >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
    >>> visa_wrapper_usbtmc is not None
    True

    """
    def __init__(self, address, timeout=5):
        """Initialize visa_wrapper_usbtmc.
        Stores configuration in ``terminationCharacter``,
        ``usbtmc_interface``, ``usbtmc_interfacetimeout`` for use by other
        methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> visa_wrapper_usbtmc is not None
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if usbtmcMissing:
            raise Exception(
                'USB Test and Measurment class init failed. Do you have PyUSB installed properly with a libusb (1.0 or 0.1) or OpenUSB backend?',
                'For Windows users, libusb 0.1 is provided through libusb-win32 package. Check the libusb website for updates (http://www.libusb.info).')
        self.terminationCharacter = None
        self.usbtmc_interface = usbtmc.Instrument(
            address, term_char=self.terminationCharacter)
        self.usbtmc_interfacetimeout = timeout

    def read(self):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'read')
        True

        Returns:
            The value read from the device or channel.
        """
        return self.usbtmc_interface.read()

    def write(self, message):
        """Write a value to the channel.

        Writes data to the underlying target.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'write')
        True

        Args:
            message: Human-readable message string.
        """
        self.usbtmc_interface.write(message)

    def read_values(self):
        # ascii transfer only
        # see visa.py for binary parsing example
        """Return read values result.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'read_values')
        True

        Returns:
            The value read from the device or channel.
        """
        float_regex = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\d*\.\d+)"
                                 "(?:[eE][-+]?\\d+)?")
        return [float(raw_value) for raw_value in
                float_regex.findall(self.read())]

    def ask(self, message):
        """Return the ask.

        Supports the ``visa_wrapper_usbtmc`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'ask')
        True

        Args:
            message: Human-readable message string.

        Returns:
            The instrument response string.
        """
        return self.usbtmc_interface.ask(message)

    def ask_for_values(self, message):
        """Return ask for values result.

        Supports the ``visa_wrapper_usbtmc`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'ask_for_values')
        True

        Args:
            message: Human-readable message string.

        Returns:
            List of numeric values parsed from the instrument response.
        """
        self.write(message)
        return self.read_values()

    def clear(self):
        """Clear buffered data and status registers.

        Restores the object or hardware to its default state.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'clear')
        True

        """
        self.usbtmc_interface.clear()

    def trigger(self):
        """Run the trigger step.

        Initiates the action and notifies any registered observers.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'trigger')
        True

        """
        self.usbtmc_interface.trigger()

    def read_raw(self):
        """Perform read raw operation.

        Reads data from the underlying source and returns it.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'read_raw')
        True

        """
        self.usbtmc_interface.read_raw()

    def resync(self):
        """Flush buffers to resync after communication fault - usb-serial problem.

        Brings the cached state into agreement with the authoritative source.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'resync')
        True

        """

    def close(self):
        """Close the connection and release resources.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'close')
        True

        """
        self.usbtmc_interface.close()

    def open(self):
        """Run the open step.

        Establishes the connection or prepares the resource for use.

        >>> from PyICe.visa_wrappers import visa_wrapper_usbtmc
        >>> hasattr(visa_wrapper_usbtmc, 'open')
        True

        """
        self.usbtmc_interface.open()

    def __getTimeout(self):
        return self.usbtmc_interface.timeout

    def __setTimeout(self, timeout):
        self.usbtmc_interface.timeout = timeout
    timeout = property(__getTimeout, __setTimeout)


class visa_interface(visa_wrapper):
    """Agilent visa strips trailing termination character, but NI VISA seems to leave them in response.

    >>> from PyICe.visa_wrappers import visa_interface
    >>> visa_interface is not None
    True

    """

    def __init__(self, address, timeout=5):
        """Initialize visa_interface.
        Stores configuration in ``timeout``, ``timeout_scale``,
        ``visaInterface`` for use by other methods.

        Initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> visa_interface is not None
        True

        Args:
            address: Network hostname or IP address string.
            timeout: Timeout in seconds.

        Raises:
            visaWrapperException: If the operation fails.
        """
        if visaMissing:
            raise visaWrapperException('VISA library missing from this system')
        elif "instrument" in dir(visa):  # Old API from PyVISA rev < 1.5
            self.visaInterface = visa.instrument(  # pylint: disable=no-member; runtime-guarded by dir() check above
                resource_name=address)  # , timeout=timeout)
            self.timeout_scale = 1
        else:  # Use new API PyVISA rev >= 1.5
            self.visaInterface = visa.ResourceManager().open_resource(address)
            self.timeout_scale = 1e-3
        self.timeout = timeout

    def read(self):
        """Read and return the current channel value.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'read')
        True

        Returns:
            The value read from the device or channel.
        """
        return self.visaInterface.read().rstrip()

    def write(self, message):
        """Write a value to the channel.

        Writes data to the underlying target.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'write')
        True

        Args:
            message: Human-readable message string.
        """
        if not isinstance(message, str):
            print(
                "fVisa write() message unexpectedly non-string ({type(message)}). Contact PyICe-developers@analog.com for more information.")
            message = message.decode(str_encoding)
            traceback.print_stack()
        self.visaInterface.write(message)

    def read_values(self):
        """Return read values result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'read_values')
        True

        Returns:
            The value read from the device or channel.
        """
        return self.visaInterface.read_values().rstrip()

    def ask(self, message):
        """Return the ask.

        Supports the ``visa_interface`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'ask')
        True

        Args:
            message: Human-readable message string.

        Returns:
            The instrument response string.
        """
        return self.visaInterface.query(message).rstrip()

    def ask_for_values(self, message):
        """Return ask for values result.

        Supports the ``visa_interface`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'ask_for_values')
        True

        Args:
            message: Human-readable message string.

        Returns:
            List of numeric values parsed from the instrument response.
        """
        return self.visaInterface.ask_for_values(message).rstrip()

    def ask_for_values_binary(
            self, message, format_str='B', byte_order='=', terminationCharacter=''):
        """Return ask for values binary result.

        Supports the ``visa_interface`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'ask_for_values_binary')
        True

        Args:
            byte_order: Byte order to use.
            format_str: Format str to use.
            message: Human-readable message string.
            terminationCharacter: Terminationcharacter to use.

        Returns:
            List of numeric values parsed from the instrument response.
        """
        if byte_order == '<':
            is_big_endian = False
        else:
            is_big_endian = True  # Maybe not quite right... '='?
        return self.visaInterface.query_binary_values(
            message, datatype=format_str, is_big_endian=is_big_endian)

    def clear(self):
        """Clear buffered data and status registers.

        Restores the object or hardware to its default state.

        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'clear')
        True

        """
        self.visaInterface.clear()

    def trigger(self):
        """Run the trigger step.

        Initiates the action and notifies any registered observers.

        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'trigger')
        True

        """
        self.visaInterface.trigger()

    def read_raw(self):
        # Response comes back as bytes from VISA lib
        """Return read raw result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'read_raw')
        True

        Returns:
            The value read from the device or channel.
        """
        return self.visaInterface.read_raw()

    def close(self):
        """Close the connection and release resources.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'close')
        True

        """
        self.visaInterface.close()

    def flush(self, buffer):
        """Run the flush step.

        Supports the ``visa_interface`` workflow by performing the described operation.


        >>> from PyICe.visa_wrappers import visa_interface
        >>> hasattr(visa_interface, 'flush')
        True

        Args:
            buffer: Buffer to use.

        Raises:
            ValueError: If buffer is not READ or WRITE.
        """
        if buffer == "READ":
            self.visaInterface.flush(visa.constants.VI_READ_BUF)
        elif buffer == "WRITE":
            self.visaInterface.flush(visa.constants.VI_WRITE_BUF_DISCARD)
        else:
            raise ValueError(
                f"visa_wrappers.py flush():  Don't know how to flush visa buffer: {buffer}")

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
    term_chars = property(__getTerminationChars, __setTerminationChars)
