"""Detrend utility."""
import scipy
from .vector_transform import vector_transform


def _detrend(rec_array, **kwargs):
    """Apply ``scipy.signal.detrend`` to every column except the first.

    The first column is assumed to be the independent variable (x-axis)
    and is passed through unchanged. All remaining columns are detrended
    according to ``**kwargs`` (e.g. ``type='constant'`` or ``type='linear'``).

    See https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.detrend.html

    Args:
        rec_array: Input numpy record array. The first column is treated
            as the x-axis and left unchanged.
        **kwargs: Forwarded to ``scipy.signal.detrend`` (notably ``type``).

    Returns:
        A new numpy record array with detrended y-columns and the
        original x-column preserved.
    """
    return vector_transform(rec_array, [None, lambda col: scipy.signal.detrend(
        data=col, **kwargs)] * (len(rec_array.dtype.names) - 1))


def detrend_constant(rec_array, **kwargs):
    """Remove the DC offset (mean) from all y-columns, leaving the x-axis unchanged.

    Useful for centering measurement data around zero before spectral
    analysis or when comparing waveform shapes across different bias
    conditions.

    Args:
        rec_array: Input numpy record array. The first column is treated
            as the x-axis and left unchanged; all others have their mean
            subtracted.
        **kwargs: Forwarded to ``scipy.signal.detrend``.

    Returns:
        A new numpy record array with zero-mean y-columns.
    """
    return _detrend(rec_array, type='constant')


def detrend_linear(rec_array, **kwargs):
    """Remove a least-squares linear trend from all y-columns, leaving the x-axis unchanged.

    Useful for isolating residual nonlinearity or noise after removing a
    dominant first-order slope (e.g. computing INL from a DAC transfer
    function).

    Args:
        rec_array: Input numpy record array. The first column is treated
            as the x-axis and left unchanged; all others have their
            best-fit line subtracted.
        **kwargs: Forwarded to ``scipy.signal.detrend``.

    Returns:
        A new numpy record array with linearly-detrended y-columns.
    """
    return _detrend(rec_array, type='linear')
