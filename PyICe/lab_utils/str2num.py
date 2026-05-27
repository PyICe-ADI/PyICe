"""Str2num utility.

>>> from PyICe.lab_utils.str2num import str2num

"""
def str2num(str_in, except_on_error=True):
    """Convert a string to its most specific numeric type (int, float, or bool).

    Handles decimal, hex (0x), octal (0o), and binary (0b) integer formats via
    Python's ``int(s, 0)`` auto-base detection. Pass-through for values that are
    already numeric or None.

    >>> str2num('42')
    42
    >>> str2num('0xFF')
    255
    >>> str2num('3.14')
    3.14
    >>> str2num('True')
    True
    >>> str2num(None) is None
    True
    >>> str2num('hello', except_on_error=False)
    'hello'
    >>> str2num('0b1010')
    10

    Args:
        str_in: String to convert, or a value that is already numeric/None.
        except_on_error: If True (default), raise ValueError on unconvertible
            strings. If False, return the original string unchanged.

    Raises:
        ValueError: If the string cannot be parsed and except_on_error is True.
    """
    if isinstance(str_in, int) or isinstance(str_in, float) or str_in is None:
        return str_in
    if str_in == 'True':
        return True
    if str_in == 'False':
        return False
    try:
        return int(str_in, 0)  # automatically select base
    except ValueError:
        try:
            return float(str_in)
        except ValueError as e:
            if except_on_error:
                print(
                    "string failed to convert both to integer (automatic base selection) and float: {}".format(str))
                raise e
            else:
                # just return original string
                return str_in
