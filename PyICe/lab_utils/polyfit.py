"""Polyfit utility."""
import numpy


def polyfit(rec_array, degree=1):
    """Returns polynomial fit coefficients list, highest order first.

    https://docs.scipy.org/doc/numpy/reference/generated/numpy.polyfit.html

    Args:
        degree: Degree.
        rec_array: Rec array.

    Returns:
        Result value.
    """
    return numpy.polyfit(x=rec_array[rec_array.dtype.names[0]],
                         y=rec_array[rec_array.dtype.names[1]], deg=degree)
