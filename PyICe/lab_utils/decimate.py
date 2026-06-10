"""Decimate utility.

>>> from PyICe.lab_utils.decimate import decimate

"""
import scipy
from .vector_transform import vector_transform


def decimate(rec_array, downsample_factor, **kwargs):
    """Downsample a record array by an integer factor with anti-alias filtering.

    Wraps ``scipy.signal.decimate`` column-by-column so every column
    (including the x-axis) is anti-alias filtered and then sub-sampled.
    By default an order-8 Chebyshev type I filter is applied; pass
    ``ftype='fir'`` for a 30-point FIR filter with Hamming window
    (recommended for most lab data).

    See https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.decimate.html


    >>> from PyICe.lab_utils.decimate import decimate
    >>> callable(decimate)
    True

    Args:
        rec_array: Input numpy record array whose rows will be reduced.
        downsample_factor: Integer factor by which to reduce the row count
            (e.g. 4 keeps every 4th sample after filtering).
        **kwargs: Forwarded to ``scipy.signal.decimate`` (e.g.
            ``ftype='fir'``, ``n`` for filter order).

    Returns:
        A new numpy record array with ``len(rec_array) // downsample_factor``
        rows and the same column names.
    """
    return vector_transform(rec_array, [lambda col: scipy.signal.decimate(
        x=col, q=downsample_factor, **kwargs)] * len(rec_array.dtype.names))
