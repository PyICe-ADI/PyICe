import numpy

def differential_nonlinearity(rec_array, lsb_size=1):
    '''transform (code, voltage) data into DNL.
    optional lsb_size argument scales y-axis data from real units to lsb count.'''
    return scalar_transform(vector_transform(rec_array, [lambda col: col[:-1], lambda col: numpy.diff(col)]), [None, lambda x: x / float(lsb_size)])