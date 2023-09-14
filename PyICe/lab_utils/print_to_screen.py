import sys

def print_to_screen(*args, **kwargs):
    """Like Python 2's built-in print statement, but is a function instead of a statement
    and so can be passed as an argument in a function call.
    Pass keyword argument 'linefeed=False' to suppress the default trailing linefeed."""
    sys.stdout.write("")  # Needed to suppress possibility of print statement's default leading whitespace.
    if args:
        for arg in args:
            print(arg, end=' ')    # sys.stdout.write("") above avoids the possible leading whitespace of this print.
    if "linefeed" not in kwargs or ("linefeed" in kwargs and kwargs["linefeed"] is True):
        print()
    return len(args)