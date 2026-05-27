"""Isclose utility.

>>> from PyICe.lab_utils.isclose import isclose

"""
import math


def isclose(a, b, rel_tol=1e-9, abs_tol=0.0):
    """Determine whether two values are close using strong-symmetry comparison.

    Unlike ``math.isclose`` (which uses weak symmetry — order-dependent),
    this implementation requires the difference to be within rel_tol of *both*
    operands, so ``isclose(a, b) == isclose(b, a)`` always holds.

    Backported from PEP 485 reference implementation with strong symmetry
    modification. See https://www.python.org/dev/peps/pep-0485/

    >>> isclose(1.0, 1.0)
    True
    >>> isclose(1.0, 1.1)
    False
    >>> isclose(1.0, 1.0000000001)
    True
    >>> isclose(0.0, 0.001, abs_tol=0.01)
    True
    >>> isclose(float('inf'), float('inf'))
    True
    >>> isclose(float('-inf'), float('-inf'))
    True
    >>> isclose(float('inf'), float('-inf'))
    False
    >>> isclose(float('nan'), float('nan'))
    False
    >>> isclose(float('nan'), 1.0)
    False
    >>> isclose(1e-10, 2e-10, rel_tol=1e-9)  # near-zero needs abs_tol
    False
    >>> isclose(1e-10, 2e-10, abs_tol=1e-9)
    True

    Args:
        a: First value to compare.
        b: Second value to compare.
        rel_tol: Maximum allowed difference relative to the magnitude of both
            inputs (strong symmetry). Default 1e-9.
        abs_tol: Minimum absolute tolerance — needed for comparisons near zero
            where relative tolerance breaks down. Default 0.0.

    Raises:
        ValueError: If rel_tol or abs_tol is negative.
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

    return (((diff <= abs(rel_tol * b)) and  # DJS change from weak to strong symmetry so that argument order doesn't matter
             (diff <= abs(rel_tol * a))) or
            (diff <= abs_tol))
