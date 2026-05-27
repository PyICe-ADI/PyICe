"""Integral nonlinearity utility.

>>> from PyICe.lab_utils.integral_nonlinearity import integral_nonlinearity

"""
from .scalar_transform import scalar_transform
from .detrend import detrend_linear


def integral_nonlinearity(rec_array, lsb_size=1):
    """Compute integral nonlinearity (INL) from a converter transfer function.

    Removes the best-fit line from the y-column (via ``detrend_linear``)
    and scales the residual by *lsb_size*, converting raw voltage
    deviations into LSB counts. The x-column (typically digital codes)
    passes through unchanged.


    >>> from PyICe.lab_utils.integral_nonlinearity import integral_nonlinearity
    >>> callable(integral_nonlinearity)
    True

    Args:
        rec_array: Two-column numpy record array, typically (code, voltage),
            representing the measured transfer function.
        lsb_size: Size of one LSB in the same units as the y-column.
            Residuals are divided by this value to express INL in LSBs.
            Use 1 (default) to keep the y-axis in its original units.

    Returns:
        A new numpy record array with the x-column unchanged and the
        y-column replaced by the INL residual in LSBs.
    """
    return scalar_transform(detrend_linear(rec_array), [
                            None, lambda x: x / float(lsb_size)])
