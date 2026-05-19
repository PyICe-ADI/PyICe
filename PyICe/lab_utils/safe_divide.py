def safe_divide(a, b):
    '''try to divide a by b, returning None for ZeroDivision and Type errors

    >>> safe_divide(10, 2)
    5.0
    >>> safe_divide(1, 0) is None
    True
    >>> safe_divide('x', 2) is None
    True

    Args:
        a: A.
        b: B.

    Returns:
        Result value.

    Raises:
        BaseException: On error condition.
    '''
    try:
        return a / b
    except (ZeroDivisionError, TypeError):
        return None
    except BaseException:
        raise
