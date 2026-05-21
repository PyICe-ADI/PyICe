"""Vector transform utility."""
import numpy


def vector_transform(rec_array, column_vector_functions, column_names=None):
    """Apply per-column vector functions to a numpy record array.

    Each function receives the entire column as an array and returns a
    transformed array (which may differ in length for decimation/filtering).
    Use None for columns that should pass through unchanged. For element-wise
    operations, see scalar_transform instead.

    >>> import numpy as np
    >>> data = np.rec.fromarrays([[1, 2, 3], [10, 20, 30]], names='x,y')
    >>> result = vector_transform(data, [None, lambda col: col * 2])
    >>> result.y.tolist()
    [20, 40, 60]
    >>> result.x.tolist()
    [1, 2, 3]
    >>> renamed = vector_transform(data, [None, None], column_names=['a', 'b'])
    >>> renamed.dtype.names
    ('a', 'b')

    Args:
        rec_array: Input numpy record array.
        column_vector_functions: List of functions (one per column). Each
            receives the column as a numpy array. Use None to pass through.
        column_names: Optional list of new column names (None entries keep
            the original name).
    """
    assert len(rec_array.dtype.names) == len(column_vector_functions)
    if column_names is None:
        column_names = [None] * len(column_vector_functions)
    assert len(column_vector_functions) == len(column_names)
    filt_cols = []
    filt_names = []
    for i, column_name in enumerate(rec_array.dtype.names):
        if column_vector_functions[i] is not None:
            filt_cols.append(
                column_vector_functions[i](
                    rec_array[column_name]))
        else:
            filt_cols.append(rec_array[column_name])
        if column_names[i] is not None:
            filt_names.append(column_names[i])
        else:
            filt_names.append(column_name)  # use old name
    return numpy.rec.fromarrays(filt_cols, names=filt_names)
