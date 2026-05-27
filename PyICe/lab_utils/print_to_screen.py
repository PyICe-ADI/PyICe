"""Print to screen utility."""
import sys


def print_to_screen(*args, **kwargs):
    """Print each positional argument to stdout, optionally suppressing the trailing newline.

    Unlike a bare ``print()`` call, this is a first-class function designed to
    be passed as a callback (e.g. to ``print_hex_bytes``'s *write* parameter or
    anywhere a ``dont_print``-compatible signature is expected).

    Args:
        *args: Values to print, each separated by a space.
        **kwargs: Pass ``linefeed=False`` to suppress the trailing newline.

    Returns:
        The number of positional arguments that were printed.
    """
    sys.stdout.write(
        # Needed to suppress possibility of print statement's default leading
        # whitespace.
        "")
    if args:
        for arg in args:
            # sys.stdout.write("") above avoids the possible leading whitespace
            # of this print.
            print(arg, end=' ')
    if "linefeed" not in kwargs or (
            "linefeed" in kwargs and kwargs["linefeed"] is True):
        print()
    return len(args)
