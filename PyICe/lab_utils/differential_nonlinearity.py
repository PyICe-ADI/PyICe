"""Differential nonlinearity utility."""
import numpy
from .scalar_transform import scalar_transform
from .vector_transform import vector_transform


def differential_nonlinearity(rec_array, lsb_size=1):
    """Compute differential nonlinearity (DNL) from (code, voltage) sweep data.

    DNL measures how much each step deviates from the ideal 1-LSB step size.
    A perfect converter has DNL = 0 everywhere. The result has one fewer row
    than the input (diff operation).

    >>> import numpy as np
    >>> data = np.rec.fromarrays([[0, 1, 2, 3], [0.0, 1.0, 2.0, 3.0]], names='code,voltage')
    >>> dnl = differential_nonlinearity(data, lsb_size=1.0)
    >>> dnl.voltage.tolist()
    [1.0, 1.0, 1.0]

    Args:
        rec_array: Two-column record array (code, measurement). Codes must be
            monotonically increasing.
        lsb_size: Ideal step size in the same units as the measurement column.
            Result is normalized by this value (default 1 = already in LSBs).
    """
    return scalar_transform(vector_transform(rec_array, [
                            lambda col: col[:-1], lambda col: numpy.diff(col)]), [None, lambda x: x / float(lsb_size)])
