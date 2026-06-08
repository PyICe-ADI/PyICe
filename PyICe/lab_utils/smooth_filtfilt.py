"""Smooth filtfilt utility.

>>> from PyICe.lab_utils.smooth_filtfilt import smooth_filtfilt

"""
def smooth_filtfilt(rec_array):
    """Smooth a record array with zero-phase forward-backward filtering (not yet implemented).

    Intended to wrap ``scipy.signal.filtfilt`` for zero-phase-shift
    smoothing of lab data columns. This is a placeholder awaiting a
    concrete filter design.

    See https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html


    >>> from PyICe.lab_utils.smooth_filtfilt import smooth_filtfilt
    >>> callable(smooth_filtfilt)
    True

    Args:
        rec_array: Input numpy record array to be smoothed.
    """
