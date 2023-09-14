import numpy

def vector_transform(rec_array, column_vector_functions, column_names=None):
    '''Generic filter function.
    column_vector_functions is a list of functions for each column and should have a length equal to the number of columns.
    To leave a column unchanged, set column vector function to None.
    Each column vector function will be applied to the whole column vector.
    Thus it is appropriate for 1-d filtering and decimation where access to values in adjacent columns is not required.
    column_names is a list of names for each column in the returned record array.
    To leave a column name unchanged from input record array, set column name to None.
    To leave all column names unchanged from input record array, set column_names to None.
    To smooth data, use something like scipy.signal.filtfilt and scipy.signal.butter for the column_vector_functions
    http://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.filtfilt.html
    http://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.signal.butter.html
    '''
    assert len(rec_array.dtype.names) == len(column_vector_functions)
    if column_names is None:
        column_names = [None] * len(column_vector_functions)
    assert len(column_vector_functions) == len(column_names)
    filt_cols = []
    filt_names = []
    for i, column_name in enumerate(rec_array.dtype.names):
        if column_vector_functions[i] is not None:
            filt_cols.append(column_vector_functions[i](rec_array[column_name]))
        else:
            filt_cols.append(rec_array[column_name])
        if column_names[i] is not None:
            filt_names.append(column_names[i])
        else:
            filt_names.append(column_name) #use old name
    return numpy.core.records.fromarrays(filt_cols, names=filt_names)