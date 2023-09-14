import math

def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    #backported from 3.5
    #https://github.com/PythonCHB/close_pep/blob/master/isclose.py
    #https://www.python.org/dev/peps/pep-0485/
    #https://docs.python.org/3/library/math.html#math.isclose
    #alternative tests here: https://github.com/PythonCHB/close_pep/blob/master/is_close.py
    """
    returns True if a is close in value to b. False otherwise
    :param a: one of the values to be tested
    :param b: the other value to be tested
    :param rel_tol=1e-9: The relative tolerance -- the amount of error
                         allowed, relative to the absolute value of the
                         larger input values.
    :param abs_tol=0.0: The minimum absolute tolerance level -- useful
        for comparisons to zero.
    NOTES:
    -inf, inf and NaN behave similarly to the IEEE 754 Standard. That
    is, NaN is not close to anything, even itself. inf and -inf are
    only close to themselves.
    The function can be used with any type that supports comparison,
    substratcion and multiplication, including Decimal, Fraction, and
    Complex
    Complex values are compared based on their absolute value.
    See PEP-0485 for a detailed description
    """

    if a == b:  # short-circuit exact equality
        return True

    if rel_tol < 0.0 or abs_tol < 0.0:
        raise ValueError('error tolerances must be non-negative')

    # use cmath so it will work with complex ot float
    if math.isinf(abs(a)) or math.isinf(abs(b)):
        # This includes the case of two infinities of opposite sign, or
        # one infinity and one finite number. Two infinities of opposite sign
        # would otherwise have an infinite relative tolerance.
        return False
    diff = abs(b - a)

    return (((diff <= abs(rel_tol * b)) and #DJS change from weak to strong symmetry so that argument order doesn't matter
             (diff <= abs(rel_tol * a))) or
            (diff <= abs_tol))