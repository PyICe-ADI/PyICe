"""Stream Window utility.

>>> from PyICe.lab_utils.StreamWindow import StreamWindow

"""
import sys
from .print_hex_bytes import print_hex_bytes


class StreamWindow(object):
    """Wrap a non-seekable stream with a FIFO buffer to provide rewindable peek access.

    Use StreamWindow when you need to inspect upcoming bytes from a stream
    without consuming them, then later read (consume) those same bytes. This
    is especially useful for packet parsing: call ``peek(n)`` with
    progressively larger *n* until a complete packet is identified, then
    ``read()`` to consume it.

    The wrapped *stream* can be any object that follows the ``io.RawIOBase``
    protocol (in particular, it must have a ``read()`` method), such as
    PySerial's ``serial.Serial`` objects or ``io.BytesIO``.

    ``io.BufferedReader`` in the Python 2.7.13 standard library has a broken
    ``peek()`` method — it refuses to read new bytes from the underlying
    stream as long as at least one valid byte remains in its internal
    buffer. This makes incremental peek-based parsing impossible.
    StreamWindow was developed to fill that gap.

    Examples:
        >>> import io
        >>> sw = StreamWindow(io.BytesIO(b'hello world'), buffer_size=64)
        >>> sw.peek(5)  # peek at first 5 bytes without consuming
        bytearray(b'hello')
        >>> sw.read(5)  # consume those 5 bytes
        bytearray(b'hello')
        >>> sw.peek(6)  # peek at remaining bytes
        bytearray(b' world')
        >>> len(sw)  # 6 bytes buffered from the peek
        6
        >>> sw.read(6)  # consume the rest
        bytearray(b' world')
    """
    # FYI: This class should be here in PyICe.lab_utils rather than corraled in labcomm
    # because it is generally applicable to any I/O stream that follows the io.RawIOBase
    # protocol, which is most of Python standard I/O. Indeed, the functionality of this class
    # arguably SHOULD have been built in to the Python standard library's io.BufferedReader,
    # but for whatever reason wasn't.  -- F. Lee 7/25/2017

    def __init__(self, stream, buffer_size=2**16, debug=False):
        """Initialize a StreamWindow around the given stream.

        Allocate a fixed-size FIFO buffer and attach it to *stream* so that
        subsequent ``peek()`` and ``read()`` calls can draw from either the
        buffer or the live stream transparently.

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'abc'), buffer_size=32)
            >>> len(sw)  # nothing buffered yet
            0

        Args:
            stream: Any object with a ``read(n)`` method (e.g.,
                ``io.BytesIO``, ``serial.Serial``). The stream to wrap.
            buffer_size: Maximum number of bytes the internal FIFO can
                hold. Determines how far ahead ``peek()`` can look.
            debug: When ``True``, print diagnostic messages about every
                ``read()`` and ``peek()`` operation to stdout.
        """
        assert hasattr(stream, "read"), ("stream argument provided to StreamWindow "
                                         "constructor must have a read() method.")
        assert isinstance(buffer_size, int) and buffer_size >= 1
        assert isinstance(debug, bool)
        self.stream = stream
        self.buf = bytearray(buffer_size * b'\x00')
        self.buffer_size = buffer_size
        self.content_size = 0
        self.debug = debug

    def _shift_buffer(self, num_bytes):
        """Discard the first *num_bytes* from the buffer by sliding remaining data forward.

        After this operation the first ``num_bytes`` positions in the buffer
        are freed for new data from the underlying stream. The valid content
        that was beyond *num_bytes* is moved to the front of the buffer.


        >>> from PyICe.lab_utils.StreamWindow import StreamWindow
        >>> hasattr(StreamWindow, '_shift_buffer')
        True

        Args:
            num_bytes: How many bytes to remove from the head of the
                internal buffer.
        """
        self.buf[:self.buffer_size - num_bytes] = self.buf[num_bytes:]

    def _read_buffer(self, num_bytes):
        """Consume and return *num_bytes* from the head of the FIFO buffer.

        The consumed bytes are removed from the buffer (via
        ``_shift_buffer``) and ``content_size`` is decremented accordingly.
        The caller must ensure *num_bytes* does not exceed ``content_size``.


        >>> from PyICe.lab_utils.StreamWindow import StreamWindow
        >>> hasattr(StreamWindow, '_read_buffer')
        True

        Args:
            num_bytes: How many bytes to extract from the front of the
                FIFO. Must be ``<= self.content_size``.

        Returns:
            A ``bytearray`` containing the consumed bytes.
        """
        assert num_bytes <= self.content_size
        # Save result bytes into new bytearray.
        result = bytearray(self.buf[:num_bytes])
        self._shift_buffer(num_bytes)
        self.content_size -= num_bytes
        return result

    def __len__(self):
        """Return the number of valid bytes currently in the FIFO buffer.

        Because the underlying stream has indefinite length, this reports
        only how many bytes have been buffered (via ``peek()``) and not yet
        consumed (via ``read()``).

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'abcdef'), buffer_size=32)
            >>> len(sw)  # nothing peeked yet
            0
            >>> sw.peek(4)  # buffer 4 bytes
            bytearray(b'abcd')
            >>> len(sw)  # now 4 bytes in the FIFO
            4

        Returns:
            The count of unread bytes sitting in the FIFO.
        """
        return self.content_size

    def __getitem__(self, k):
        """Return buffered bytes by integer index or slice without consuming them.

        Index ``0`` refers to the head (oldest) byte in the FIFO and ``-1``
        refers to the tail (newest) byte. Slices are automatically clamped
        to the valid content range.

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'abcde'), buffer_size=32)
            >>> sw.peek(5)  # fill the buffer
            bytearray(b'abcde')
            >>> sw[0]  # first byte
            97
            >>> sw[-1]  # last buffered byte
            101
            >>> sw[1:4]  # slice of buffered content
            bytearray(b'bcd')

        Args:
            k: An ``int`` index or ``slice`` selecting bytes from the
                FIFO buffer.

        Returns:
            A single byte value (``int``) for integer indexing, or a
            ``bytearray`` for slicing.

        Raises:
            IndexError: If an integer index is out of the valid buffered
                content range.
        """
        if isinstance(k, int):
            if (k > 0 and k >= self.content_size) or (
                    k < 0 and -k > self.content_size):
                raise IndexError
            k = k if k >= 0 else self.content_size + k
        elif isinstance(k, slice):
            # Need to adjust the slice argument based on content_size.
            start, stop, step = k.indices(self.content_size)
            k = slice(start, stop, step)
        return self.buf[k]

    def find(self, sub, start=0, end=None):
        """Return the lowest index in the FIFO buffer where *sub* is found.

        Search only the valid buffered content (ignoring any stale bytes
        beyond ``content_size``). Returns ``-1`` if *sub* is not present.

        Note: The *start* and *end* parameters are accepted for API
        compatibility but are not used; the search always covers the
        full valid buffer range ``[0, content_size)``.

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'hello world'), buffer_size=64)
            >>> sw.peek(11)  # buffer everything
            bytearray(b'hello world')
            >>> sw.find(b'world')  # find a subsequence
            6
            >>> sw.find(b'xyz')  # not found
            -1

        Args:
            sub: The byte sequence to search for (``bytes`` or
                ``bytearray``).
            start: Reserved for API compatibility; currently unused.
            end: Reserved for API compatibility; currently unused.

        Returns:
            The zero-based index of the first occurrence of *sub* within
            the buffered content, or ``-1`` if not found.
        """
        return self.buf.find(sub, 0, self.content_size)

    def read(self, num=1):
        """Read and consume up to *num* bytes from the FIFO-buffered stream.

        Bytes already in the FIFO are consumed first; if more are needed
        they are fetched directly from the underlying stream. The returned
        ``bytearray`` may be shorter than *num* if the stream is exhausted.

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'abcdef'), buffer_size=32)
            >>> sw.peek(3)  # buffer 3 bytes
            bytearray(b'abc')
            >>> sw.read(2)  # consume 2 from FIFO
            bytearray(b'ab')
            >>> sw.read(3)  # 1 from FIFO + 2 from stream
            bytearray(b'cde')

        Args:
            num: Maximum number of bytes to consume. Must be positive.

        Returns:
            A ``bytearray`` of up to *num* bytes composed of buffered
            bytes followed by any additional bytes read from the stream.
        """
        assert num > 0
        if self.debug:
            print(
                "read({}) called with {:d} bytes in FIFO".format(
                    num, self.content_size), end=' ')
            if self.content_size:
                print_hex_bytes(the_bytes=self[:], prefix=': ',
                                suffix="..." if self.content_size > 16 else "",
                                number_of_bytes_to_print=min(16, self.content_size))
            else:
                print()
        # First try to fill the request from the buffer.
        if self.content_size > 0:
            # Buffer not empty, so grab as many bytes as we need
            # from it, but only grab valid content.
            num_bytes_from_buffer = min(num, self.content_size)
            num_bytes_from_stream = num - num_bytes_from_buffer
            result = self._read_buffer(num_bytes_from_buffer)
        else:
            num_bytes_from_stream = num
            result = bytearray()
        # Do we need any additional bytes from the stream?
        if num_bytes_from_stream > 0:
            # Yes:
            new_bytes = self.stream.read(num_bytes_from_stream)
            result += new_bytes
            if self.debug:
                print(("  read({}) read {} new bytes from stream. "
                       ).format(num, len(result)))
        # Postcondition: result is a string of valid bytes from the buffer
        #     plus new bytes read from stream, and len(result) <= num.
        # Postcondition: result matches the regexp b*s* , where
        #     b matches any buffer byte and s matches any stream byte.
        return result

    def peek(self, num=1):
        """Return a copy of up to *num* bytes from the stream without consuming them.

        Peeked bytes are saved in the internal FIFO so that subsequent
        ``peek()`` or ``read()`` calls can see them again. If the FIFO is
        already full, only the bytes currently in the FIFO are returned and
        no new data is read from the stream — call ``read()`` first to free
        space.

        Examples:
            >>> import io
            >>> sw = StreamWindow(io.BytesIO(b'abcdef'), buffer_size=32)
            >>> sw.peek(3)  # look ahead 3 bytes
            bytearray(b'abc')
            >>> sw.peek(3)  # same 3 bytes, not consumed
            bytearray(b'abc')
            >>> sw.peek(6)  # extend the window
            bytearray(b'abcdef')

        Args:
            num: Maximum number of bytes to peek at. Clamped to
                ``buffer_size`` if larger. Must be positive.

        Returns:
            A ``bytearray`` containing up to *num* bytes from the head of
            the buffered stream. May be shorter if the stream is exhausted
            or the FIFO is full.
        """
        assert num > 0
        if num > self.buffer_size:
            num = self.buffer_size
        if self.debug:
            print(("peek({}) called with FIFO containing {:d} bytes"
                   ).format(num, self.content_size), end=' ')
            if self.content_size:
                print_hex_bytes(the_bytes=self[:], prefix=': ',
                                suffix="..." if self.content_size > 16 else "",
                                number_of_bytes_to_print=min(16, self.content_size))
            else:
                # Suppress leading whitespace in the print below.
                sys.stdout.write("")
                print(".")
        # Precondition: 0 < num <= buffer_size
        # First try to fill the request from the buffer,
        # adding fresh bytes from stream as needed.
        num_bytes_from_buffer = min(num, self.content_size)
        num_bytes_from_stream = num - num_bytes_from_buffer
        if num_bytes_from_stream > 0:
            # Try to read fresh stream bytes into the buffer
            # to satisfy the request. Read at least as many bytes as
            # the stream reports are immediately available, but stay
            # within free buf space.
            if hasattr(self.stream, "in_waiting"):
                available = self.stream.in_waiting  # PySerial >=3.0
            elif hasattr(self.stream, "inWaiting"):
                available = self.stream.inWaiting()  # PySerial <3.0
            else:
                available = 0  # Support streams without in(_w|W)aiting.
            how_many = max(available, num_bytes_from_stream)
            how_many = min(how_many, self.buffer_size - self.content_size)
            new_bytes = self.stream.read(how_many)
            self.buf[self.content_size:self.content_size +
                     len(new_bytes)] = new_bytes
            # Updated count of valid bytes in buffer.
            self.content_size += len(new_bytes)
            if self.debug:
                print(("  peek({}) read {} new bytes from stream. "
                       "FIFO now has {:d} bytes").format(num, len(new_bytes), self.content_size), end=' ')
                if self.content_size:
                    print_hex_bytes(the_bytes=self[:], prefix=': ',
                                    suffix="..." if self.content_size > 16 else "",
                                    number_of_bytes_to_print=min(16, self.content_size))
                else:
                    # Suppress leading whitespace in the print below.
                    sys.stdout.write("")
                    print(".")
        # The buffer now contains the bytes we'll return. Return a copy of
        # these bytes.
        num_bytes_to_return = min(num, self.content_size)
        result = bytearray(self.buf[:num_bytes_to_return])
        return result

    def close(self):
        """Close the underlying stream.

        Delegates to the wrapped stream's ``close()`` method, releasing
        any associated resources (file descriptors, serial ports, etc.).


        >>> from PyICe.lab_utils.StreamWindow import StreamWindow
        >>> hasattr(StreamWindow, 'close')
        True

        Returns:
            Whatever the underlying stream's ``close()`` method returns
            (typically ``None``).
        """
        return self.stream.close()
