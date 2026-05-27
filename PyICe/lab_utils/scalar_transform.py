"""Scalar transform utility.

>>> from PyICe.lab_utils.scalar_transform import scalar_transform

"""
from .vector_transform import vector_transform


def scalar_transform(rec_array, column_scalar_functions, column_names=None):
    """Apply per-column scalar functions element-wise to a numpy record array.

    Each function receives individual values (not the whole column) and returns
    the transformed value. Appropriate for scaling, offsetting, or type
    conversion. For operations needing adjacent data points (filtering,
    differentiation), use vector_transform instead.

    >>> import numpy as np
    >>> data = np.rec.fromarrays([[1, 2, 3], [100, 200, 300]], names='code,mv')
    >>> result = scalar_transform(data, [None, lambda x: x / 1000.0])
    >>> result.mv.tolist()
    [0.1, 0.2, 0.3]
    >>> result.code.tolist()
    [1, 2, 3]

    Args:
        rec_array: Input numpy record array.
        column_scalar_functions: List of functions (one per column). Each
            receives a single element and returns a transformed element.
            Use None to leave a column unchanged.
        column_names: Optional list of new column names (None entries keep
            the original name).
    """
    column_vector_functions = []
    for csf in column_scalar_functions:
        if csf is None:
            column_vector_functions.append(None)
        else:
            column_vector_functions.append(
                lambda column, func=csf: [
                    func(x) for x in column])
    return vector_transform(rec_array, column_vector_functions, column_names)
