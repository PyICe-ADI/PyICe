from .scalar_transform import scalar_transform
from .detrend import detrend_linear


def integral_nonlinearity(rec_array, lsb_size=1):
    '''transform (code, voltage) data into INL
    optional lsb_size argument scales y-axis data from real units to lsb count.

    Args:
        lsb_size: Lsb size.
        rec_array: Rec array.

    Returns:
        Result value.
    '''
    return scalar_transform(detrend_linear(rec_array), [
                            None, lambda x: x / float(lsb_size)])
