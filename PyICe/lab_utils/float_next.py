import math
import sys


def float_next(val):
    """Return next Python double precision floating point number larger than x.

    >>> float_next(1.0) > 1.0
    True
    >>> float_next(1.0) - 1.0 < 1e-15
    True
    >>> float_next(0.0) > 0.0
    True

    Args:
        val: Val.

    Returns:
        Result value.
    """
    # algorithm copied from Boost:
    # http://www.boost.org/doc/libs/1_45_0/boost/math/special_functions/next.hpp
    assert not math.isinf(val)
    assert not math.isnan(val)
    assert not val >= sys.float_info.max
    if val == 0:
        return sys.float_info.epsilon * sys.float_info.min  # denorm min
    frac, expon = math.frexp(val)
    if frac == -0.5:
        expon -= 1  # reduce exponent when val is a power of two, and negative.
    diff = math.ldexp(1, expon - sys.float_info.mant_dig)
    if diff == 0:
        diff = sys.float_info.epsilon * sys.float_info.min  # denorm min
    return val + diff
