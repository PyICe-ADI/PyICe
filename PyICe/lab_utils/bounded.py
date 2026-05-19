def bounded(value, min_value=None, max_value=None, key=None):
    """Clamp value between min_value and max_value.

    >>> bounded(5, min_value=0, max_value=10)
    5
    >>> bounded(-3, min_value=0, max_value=10)
    0
    >>> bounded(15, min_value=0, max_value=10)
    10
    >>> bounded(15, max_value=10)
    10
    >>> bounded(-3, min_value=0)
    0

    Args:
        key: Key.
        max_value: Max value.
        min_value: Min value.
        value: Value to set.

    Returns:
        Result value.
    """
    kwargs = {}
    if key is not None:
        kwargs['key'] = key
    if min_value is not None and max_value is not None:
        return max(min(value, max_value, **kwargs), min_value, **kwargs)
    elif min_value is None and max_value is not None:
        return min(value, max_value, **kwargs)
    elif min_value is not None and max_value is None:
        return max(value, min_value, **kwargs)
    return value
