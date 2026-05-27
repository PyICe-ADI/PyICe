"""Safe divide utility.

>>> from PyICe.lab_utils.safe_divide import safe_divide

"""
def safe_divide(a, b):
    """Divide a by b, returning None instead of raising on division-by-zero or type mismatch.

    Useful in data pipelines where missing or malformed readings should produce
    None rather than crash an entire sweep.

    >>> safe_divide(10, 2)
    5.0
    >>> safe_divide(1, 0) is None
    True
    >>> safe_divide('x', 2) is None
    True
    >>> safe_divide(7, 3)  # doctest: +ELLIPSIS
    2.333...

    Args:
        a: Numerator.
        b: Denominator.

    Returns:
        a/b as a float, or None if the division is undefined or the types
        are incompatible.
    """
    try:
        return a / b
    except (ZeroDivisionError, TypeError):
        return None
    except BaseException:
        raise
