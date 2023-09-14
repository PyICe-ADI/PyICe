import numpy

def polyfit(rec_array, degree=1):
    '''returns polynomial fit coefficients list, highest order first
    https://docs.scipy.org/doc/numpy/reference/generated/numpy.polyfit.html
    '''
    return numpy.polyfit(x=rec_array[rec_array.dtype.names[0]], y=rec_array[rec_array.dtype.names[1]], deg=degree)