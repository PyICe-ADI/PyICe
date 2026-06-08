"""Print hex bytes utility.

>>> from PyICe.lab_utils.print_hex_bytes import print_hex_bytes

"""
import collections
import collections.abc
from .print_to_screen import print_to_screen


def print_hex_bytes(the_bytes, number_of_bytes_per_line=16,
                    number_of_bytes_to_print=None, prefix='',
                    suffix='', show_offsets=False, write=None):
    """Print an iterable of bytes as formatted hexadecimal lines.

    Produces output like::

        0a 30 01 00 f0 ff 00 00 0a 30 01 00 f0 ff 00 00
        00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f

    Handy for inspecting TWI/I²C register dumps, firmware images, or raw
    serial traffic.  By default all bytes are printed 16 per line via
    ``print_to_screen``, but every aspect is configurable.


    >>> from PyICe.lab_utils.print_hex_bytes import print_hex_bytes
    >>> callable(print_hex_bytes)
    True

    Args:
        the_bytes: Any iterable yielding integer byte values (0–255).
        number_of_bytes_per_line: Bytes per output line.  ``None`` puts
            everything on a single line (caller must ensure finite input).
        number_of_bytes_to_print: Cap on total bytes printed.  ``None``
            means print all of them.
        prefix: String prepended to every output line.
        suffix: String appended to every output line.
        show_offsets: If ``True``, prefix each line with a six-digit hex
            byte offset (e.g. ``000010:``).
        write: Callable that accepts a single string for output.  Defaults
            to ``print_to_screen``; pass a ``logfile.print_to_file_and_screen``
            method to simultaneously log and display.
    """
    # Validate arguments.
    assert isinstance(the_bytes, collections.abc.Iterable)
    for v in (number_of_bytes_per_line, number_of_bytes_to_print):
        assert v is None or (isinstance(v, int) and v >= 0)
    if write is None:
        # By default, print to the screen.
        write = print_to_screen
    else:
        # Check that user-provided write() arg is actually callable.
        assert hasattr(write, "__call__"), "write() must be callable"
    bytestream = the_bytes.__iter__()
    bytes_printed = 0
    bytes_exhausted = False
    while (not bytes_exhausted and
            (bytes_printed < number_of_bytes_to_print
             or number_of_bytes_to_print is None)):
        bytelist = []  # List of bytes to print for this line.
        if number_of_bytes_per_line is None:
            # Print all the bytes on one line.
            bytelist = tuple(b for b in the_bytes)
            bytes_exhausted = True
        else:
            for i in range(number_of_bytes_per_line):
                try:
                    bytelist.append(next(bytestream))
                except StopIteration:
                    bytes_exhausted = True
                    break  # for i in xrange...
        line = " ".join("{:02x}".format(b) for b in bytelist)
        if len(bytelist):
            if show_offsets:
                line = "{:>06x}: ".format(bytes_printed) + line
            write(prefix + line + suffix)
        bytes_printed += len(bytelist)
