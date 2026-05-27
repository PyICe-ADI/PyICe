"""Dont print utility."""
def dont_print(*args, **kwargs):
    """Accept and discard all arguments, producing no output.

    Pass this function wherever a ``print_to_screen``-style callback is
    expected in order to suppress all console output from that caller.

    >>> dont_print("hello", "world", linefeed=False)  # produces no output

    Args:
        *args: Positional arguments (ignored).
        **kwargs: Keyword arguments (ignored).
    """
