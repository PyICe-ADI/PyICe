"""Banners utility."""
def print_banner(*message, offset=1, length=80):
    """Print a box-drawn banner to stdout. See build_banner for details."""
    print(build_banner(*message, offset=offset, length=length))


def build_banner(*message, offset=1, length=80):
    """Build a Unicode box-drawing banner around one or more lines of text.

    Used to create visually distinct section headers in console output during
    long test or measurement runs.

    >>> build_banner('Hello', length=20)
    '┌──────────────────┐\\n│ Hello            │\\n└──────────────────┘'
    >>> len(build_banner('Test', length=40).splitlines())
    3
    >>> len(build_banner('A', 'B', 'C', length=40).splitlines())
    5

    Args:
        *message: One or more lines of text to display inside the banner.
        offset: Left padding inside the box (default 1 space).
        length: Total width of the box including borders (default 80).
    """
    upper_left = u"\u250c"
    bar = u"\u2500"
    upper_right = u"\u2510"
    lower_left = u"\u2514"
    lower_right = u"\u2518"
    wall = u"\u2502"

    ret_str = f'{upper_left}{bar * (length - 2)}{upper_right}\n'
    for line in message:
        padding = (length - 2 - offset) - len(str(line))
        ret_str += f'{wall}{" " * offset}{str(line)}{" " * padding}{wall}\n'
    ret_str += f'{lower_left}{bar * (length - 2)}{lower_right}'
    return ret_str
