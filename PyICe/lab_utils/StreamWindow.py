import sys

class StreamWindow(object):
    '''Wraps any non-seekable stream that has a read(number_of_bytes) method
    and provides a specifiable amount of rewindability via FIFO buffering.
    StreamWindow-wrapped streams offer a peek() method which effectively provides
    a "sliding window" over the head of the stream.

    stream can be any stream that follows the io.RawIOBase protocol,
    e.g., PySerial's serial.Serial objects.
    In particular, stream must support the read() method.

    It's really too bad that io.BufferedReader(RawIOBase, buffer_size) in the Python 2.7.13
    standard library has a broken peek() method! In testing, I found that
    io.BufferedReader refuses to read any bytes from stream into the FIFO
    as long as there is at least one valid byte in the FIFO.
    This makes it impossible to just keep calling peek(n) with larger
    and larger values of n until one peeks at a complete data packet, for the
    example use case of segmenting/parsing packets from a stream of bytes.

    StreamWindow was developed to fill this gap.'''
    # FYI: This class should be here in PyICe.lab_utils rather than corraled in labcomm
    # because it is generally applicable to any I/O stream that follows the io.RawIOBase
    # protocol, which is most of Python standard I/O. Indeed, the functionality of this class
    # arguably SHOULD have been built in to the Python standard library's io.BufferedReader,
    # but for whatever reason wasn't.  -- F. Lee 7/25/2017
    def __init__(self, stream, buffer_size=2**16, debug=False):
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
        '''Delete num_bytes of data from the front of buf, overwriting
        it with valid data slid over from the end of buf. This makes
        room at the end of buf for new data from stream.'''
        self.buf[:self.buffer_size-num_bytes] = self.buf[num_bytes:]
    def _read_buffer(self, num_bytes):
        "Consumes bytes from the FIFO buffer."
        assert num_bytes <= self.content_size
        result = bytearray(self.buf[:num_bytes]) # Save result bytes into new bytearray.
        self._shift_buffer(num_bytes)
        self.content_size -= num_bytes
        return result
    def __len__(self):
        '''Just return the number of valid bytes in the FIFO, as it is already
        known that streams have indefinite length.'''
        return self.content_size
    def __getitem__(self, k):
        '''Support x[i] indexing or x[i:j] slice peeking into the FIFO.
        0 indexes the head byte in the FIFO, -1 indexes the tail byte.'''
        if isinstance(k, int):
            if (k > 0 and k >= self.content_size) or (k < 0 and -k > self.content_size):
                raise IndexError
            k = k if k >= 0 else self.content_size + k
        elif isinstance(k, slice):
            # Need to adjust the slice argument based on content_size.
            start, stop, step = k.indices(self.content_size)
            k = slice(start, stop, step)
        return self.buf[k]
    def find(self, sub, start=0, end=None):
        '''Return the lowest index in FIFO buffer where subsection sub is found.
        Returns -1 if not found.'''
        return self.buf.find(sub, 0, self.content_size)
    def read(self, num=1):
        '''Try to read and consume num bytes from the FIFO-buffered stream.
        Returns at most num bytes as a string.'''
        assert num > 0
        if self.debug:
            print("read({}) called with {:d} bytes in FIFO".format(num, self.content_size), end=' ')
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
        '''Returns a copy of at most num bytes from stream but also saves them in a FIFO
        buffer to allow future peek()s and read()s to see them. If FIFO is full,
        peek() returns only what is in the FIFO and won't read from stream until
        space is made.
        Use read() to make some space in the FIFO to continue retrieving bytes from stream.'''
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
                sys.stdout.write("")  # Suppress leading whitespace in the print below.
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
                available = self.stream.inWaiting() # PySerial <3.0
            else:
                available = 0  # Support streams without in(_w|W)aiting.
            how_many = max(available, num_bytes_from_stream)
            how_many = min(how_many, self.buffer_size-self.content_size)
            new_bytes = self.stream.read(how_many)
            self.buf[self.content_size:self.content_size+len(new_bytes)] = new_bytes
            self.content_size += len(new_bytes)  # Updated count of valid bytes in buffer.
            if self.debug:
                print(("  peek({}) read {} new bytes from stream. "
                       "FIFO now has {:d} bytes").format(num, len(new_bytes), self.content_size), end=' ')
                if self.content_size:
                    print_hex_bytes(the_bytes=self[:], prefix=': ',
                                    suffix="..." if self.content_size > 16 else "",
                                    number_of_bytes_to_print=min(16, self.content_size))
                else:
                    sys.stdout.write("")  # Suppress leading whitespace in the print below.
                    print(".")
        # The buffer now contains the bytes we'll return. Return a copy of these bytes.
        num_bytes_to_return = min(num, self.content_size)
        result = bytearray(self.buf[:num_bytes_to_return])
        return result
    def close(self):
        "Closes the underlying stream."
        return self.stream.close()