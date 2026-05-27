"""Float prior utility."""
import math
import sys


def float_prior(val):
    """Return the largest representable float strictly less than val.

    Equivalent to ``math.nextafter(val, -math.inf)`` but ported from the
    Boost.Math algorithm for compatibility with older Python versions.

    >>> float_prior(1.0) < 1.0
    True
    >>> 1.0 - float_prior(1.0) < 1e-15
    True
    >>> float_prior(0.0) < 0.0
    True
    >>> float_prior(1.0) == 1.0 - 2**-53
    True
    >>> float_prior(-1.0) < -1.0
    True

    Args:
        val: Input value (must be finite and greater than -sys.float_info.max).
    """
    # algorithm copied from Boost:
    # http://www.boost.org/doc/libs/1_45_0/boost/math/special_functions/next.hpp
    assert not math.isinf(val)
    assert not math.isnan(val)
    assert not val <= -sys.float_info.max
    if val == 0:
        return -sys.float_info.epsilon * sys.float_info.min  # denorm min
    frac, expon = math.frexp(val)
    if frac == 0.5:
        expon -= 1  # when val is a power of two we must reduce the exponent
    diff = math.ldexp(1, expon - sys.float_info.mant_dig)
    if diff == 0:
        diff = sys.float_info.epsilon * sys.float_info.min  # denorm min
    return val - diff
