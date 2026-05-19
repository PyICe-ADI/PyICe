"""Differential nonlinearity utility."""
import numpy
from .scalar_transform import scalar_transform
from .vector_transform import vector_transform


def differential_nonlinearity(rec_array, lsb_size=1):
    """Transform (code, voltage) data into DNL.

    optional lsb_size argument scales y-axis data from real units to lsb count.

    Args:
        lsb_size: Lsb size.
        rec_array: Rec array.

    Returns:
        Result value.
    """
    return scalar_transform(vector_transform(rec_array, [
                            lambda col: col[:-1], lambda col: numpy.diff(col)]), [None, lambda x: x / float(lsb_size)])
