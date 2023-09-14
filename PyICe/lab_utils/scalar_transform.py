def scalar_transform(rec_array, column_scalar_functions, column_names=None):
    '''Transform column data by processing through user-supplied function
    column_scalar_functions is a list of functions for each column and should have a length equal to the number of columns.
    To leave a column unchanged, set column scalar function to None.
    The column scalar function will be applied to each point in the column individually.
    Thus it is appropriate for scaling, offsetting changing data type, etc.
    This function cannot be used for filtering or convolution operations that need access to adjacent data points.
    Instead, use vector_transform().
    column_names is a list of names for each column in the returned record array.
    To leave a column name unchanged from input record array, set column name to None.
    To leave all column names unchanged from input record array, set column_names to None.
    '''
    column_vector_functions = []
    for csf in column_scalar_functions:
        if csf is None:
            column_vector_functions.append(None)
        else:
            column_vector_functions.append(lambda column, func=csf: [func(x) for x in column])
    return vector_transform(rec_array, column_vector_functions, column_names)