"""Float distance utility."""
import math
import sys


def float_distance(x, y):
    """Count how many representable floats lie between x and y (signed ULP distance).

    Useful for verifying that a computed result is within N ULPs of the expected
    value — a hardware-independent measure of floating-point accuracy. Ported from
    the Boost.Math library's ``next.hpp``.

    >>> float_distance(1.0, 1.0)
    0
    >>> float_distance(1.0, math.nextafter(1.0, math.inf))
    1
    >>> float_distance(1.0, math.nextafter(math.nextafter(1.0, math.inf), math.inf))
    2
    >>> float_distance(1.0, 2.0)  # 2^52 representable doubles in [1, 2)
    4503599627370496
    >>> float_distance(2.0, 1.0)  # sign convention: negative when x > y
    -4503599627370496
    >>> float_distance(0.0, sys.float_info.min)  # zero to smallest normal
    4503599627370496

    Args:
        x: First floating-point value.
        y: Second floating-point value.

    Returns:
        Signed integer count of representable floats between x and y.
    """
    # Boost library algorithm port:
    # http://www.boost.org/doc/libs/1_45_0/boost/math/special_functions/next.hpp
    if x > y:
        return -float_distance(y, x)
    elif x == y:
        return 0
    elif x == 0:
        return 1 + abs(float_distance(math.copysign(1, y) *
                       sys.float_info.epsilon * sys.float_info.min, y))  # denorm min
    elif y == 0:
        return 1 + abs(float_distance(math.copysign(1, x) *
                       sys.float_info.epsilon * sys.float_info.min, x))  # denorm min
    elif math.copysign(1, x) != math.copysign(1, y):
        return 2 + abs(float_distance(math.copysign(1, x) * sys.float_info.epsilon * sys.float_info.min, x)) + \
            abs(float_distance(math.copysign(1, y) *
                               sys.float_info.epsilon *
                               sys.float_info.min, y))  # denorm min
    # should have same sign now
    elif x < 0:
        return float_distance(-y, -x)
    assert x >= 0
    assert y >= x

    # Note that if a is a denorm then the usual formula fails because we
    # actually have fewer than tools::digits<T>() significant bits in the
    # representation:
    expon = math.frexp(x)[1]
    if expon < sys.float_info.min_exp:
        expon = sys.float_info.min_exp
    upper = math.ldexp(1, expon)
    result = 0
    # For floating-point types, this is the number of digits in the mantissa.
    expon = sys.float_info.mant_dig - expon
    # If b is greater than upper, then we *must* split the calculation as the
    # size of the ULP changes with each order of magnitude change:
    if (y > upper):
        result = float_distance(upper, y)
        y = upper
    # Use compensated double-double addition to avoid rounding errors in the
    # subtraction:
    X = x - y
    Z = X - x
    Y = (x - (X - Z)) - (y + Z)
    if X < 0:
        X = -X
        Y = -Y
    result += math.ldexp(X, expon) + math.ldexp(Y, expon)
    # Result must be an integer:
    assert (result == math.floor(result))
    return int(result)
