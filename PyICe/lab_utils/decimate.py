def decimate(rec_array, downsample_factor, **kwargs):
    '''Reduce row count by factor of downsample_factor.
     By default an order 8 Chebyshev type I filter is used independently on each column.
     Set kwarg ftype='fir' to instead use a 30 point FIR filter with hamming window (recommended).
     http://docs.scipy.org/doc/scipy-0.16.1/reference/generated/scipy.signal.decimate.html
    '''
    return vector_transform(rec_array, [lambda col: scipy.signal.decimate(x=col,q=downsample_factor, **kwargs)] * len(rec_array.dtype.names))