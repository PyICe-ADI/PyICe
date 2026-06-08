"""Bounded utility.

>>> from PyICe.lab_utils.bounded import bounded

"""
def bounded(value, min_value=None, max_value=None, key=None):
    """Clamp a value to stay within [min_value, max_value].

    Either bound can be omitted to apply only a floor or only a ceiling.
    Useful for constraining DAC codes, voltage setpoints, or loop variables
    to safe operating limits.

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
    >>> bounded(42)  # no bounds applied
    42

    Args:
        value: The value to clamp.
        min_value: Lower bound (inclusive), or None for no floor.
        max_value: Upper bound (inclusive), or None for no ceiling.
        key: Optional comparison key function (passed to min/max builtins).
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
