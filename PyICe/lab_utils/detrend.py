import scipy

def _detrend(rec_array, **kwargs):
    '''http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.detrend.html'''
    return vector_transform(rec_array, [None, lambda col: scipy.signal.detrend(data=col, **kwargs)] * (len(rec_array.dtype.names)-1))
    
def detrend_constant(rec_array, **kwargs):
    '''Remove data mean from all columns except first one (assumed x-axis)
    http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.detrend.html
    '''
    return _detrend(rec_array, type='constant')
    
def detrend_linear(rec_array, **kwargs):
    '''Remove least squares fit line from all columns except first one (assumed x-axis)
    http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.detrend.html
    '''
    return _detrend(rec_array, type='linear')