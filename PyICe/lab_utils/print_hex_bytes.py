import collections

def print_hex_bytes(the_bytes, number_of_bytes_per_line=16,
                    number_of_bytes_to_print=None, prefix='',
                    suffix='', show_offsets=False, write=None):
    '''Given a list of bytes (or other iterable of bytes),
    print them like this:

    0a 30 01 00 f0 ff 00 00 0a 30 01 00 f0 ff 00 00
    00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f
    . . .

    Defaults to printing all the bytes given,
    in lines of 16 bytes each, using the built-in
    print statement. But this is all configurable.
    In particular, the write argument should be any function
    that accepts a string to be output, printed,
    or recorded in some way, such as
    lab_utils.logfile's print_to_file_and_screen() method.
    If number_of_bytes_per_line is None, then all bytes will
    be printed on one line AND the caller is responsible for
    ensuring that the_bytes is a finite number of bytes.'''
    # Validate arguments.
    assert isinstance(the_bytes, collections.Iterable)
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