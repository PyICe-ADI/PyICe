"""Modulate utility.

>>> from PyICe.lab_utils.modulate import modulate

"""
import numpy


def modulate(data1, data2):
    """Multiply two (x, y) datasets point-wise, interpolating to align x-axes.

    When the two datasets have different x-values, the shorter one is
    interpolated onto the longer one's x-axis before multiplication. Useful
    for applying a transfer function (gain vs. frequency) to a signal spectrum.

    >>> result = modulate([(0, 1), (1, 2), (2, 3)], [(0, 10), (2, 10)])
    >>> [(x, float(y)) for x, y in result]
    [(0, 10.0), (1, 20.0), (2, 30.0)]
    >>> result = modulate([(0, 2), (1, 3)], [(0, 5), (1, 4)])
    >>> [(x, float(y)) for x, y in result]
    [(0, 10.0), (1, 12.0)]

    Args:
        data1: List of (x, y) tuples for the first dataset.
        data2: List of (x, y) tuples for the second dataset.

    Returns:
        List of (x, y) tuples with the pointwise product, aligned to the
        longer dataset's x-axis.
    """
    independent = []
    product = []
    if len(data1) > len(data2):
        for value in data1:
            xvalue = value[0]
            data2_value = numpy.interp(xvalue, list(
                zip(*data2))[0], list(zip(*data2))[1])
            independent.append(xvalue)
            product.append(value[1] * data2_value)
    else:
        for value in data2:
            xvalue = value[0]
            data1_value = numpy.interp(xvalue, list(
                zip(*data1))[0], list(zip(*data1))[1])
            independent.append(xvalue)
            product.append(value[1] * data1_value)
    return list(zip(independent, product))
