from .float_next import float_next
from .float_prior import float_prior


def unit_least_precision(val, increasing=True):
    """Return positive increment/decrement to next representable floating point number above/below val.

    Args:
        increasing: Increasing.
        val: Val.

    Returns:
        Result value.
    """
    if increasing:
        return float_next(val) - val
    else:
        return val - float_prior(val)
