"""Unit least precision utility.

>>> from PyICe.lab_utils.unit_least_precision import unit_least_precision

"""
from .float_next import float_next
from .float_prior import float_prior


def unit_least_precision(val, increasing=True):
    """Return the magnitude of one ULP (unit of least precision) at a given value.

    The ULP is the gap between val and the next representable float — it grows
    with magnitude. Useful for setting tolerances that are meaningful relative
    to floating-point granularity rather than to absolute scale.

    >>> unit_least_precision(1.0)
    2.220446049250313e-16
    >>> unit_least_precision(1024.0) > unit_least_precision(1.0)
    True
    >>> unit_least_precision(1.0, increasing=False)
    1.1102230246251565e-16
    >>> unit_least_precision(0.0) > 0
    True

    Args:
        val: Value at which to measure floating-point granularity.
        increasing: If True (default), return the step to the next larger float;
            if False, return the step to the next smaller float.
    """
    if increasing:
        return float_next(val) - val
    else:
        return val - float_prior(val)
