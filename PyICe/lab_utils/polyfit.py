"""Polyfit utility."""
import numpy


def polyfit(rec_array, degree=1):
    """Fit a polynomial to the first two columns of a record array.

    Wraps ``numpy.polyfit`` treating the first column as x and the second
    as y. Useful for extracting gain, offset, or higher-order
    coefficients from measured transfer functions.

    Args:
        rec_array: Two-column numpy record array. The first column
            provides x-values, the second provides y-values.
        degree: Degree of the fitting polynomial (default 1 for a
            linear fit).

    Returns:
        Numpy array of polynomial coefficients, highest degree first
        (e.g. ``[slope, intercept]`` for ``degree=1``).
    """
    return numpy.polyfit(x=rec_array[rec_array.dtype.names[0]],
                         y=rec_array[rec_array.dtype.names[1]], deg=degree)
