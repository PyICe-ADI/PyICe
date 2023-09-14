def integral_nonlinearity(rec_array, lsb_size=1):
    '''transform (code, voltage) data into INL
    optional lsb_size argument scales y-axis data from real units to lsb count.'''
    return scalar_transform(detrend_linear(rec_array), [None, lambda x: x / float(lsb_size)])