import numpy

def modulate(data1, data2):
    '''data1 and data2 are tuples of x and y data that may not have the same number of 'x' values. The result is interpolated up to the higher of the two.'''
    independent = []
    product = []
    if len(data1) > len(data2):
        for value in data1:
            xvalue = value[0]
            data2_value = numpy.interp(xvalue, list(zip(*data2))[0], list(zip(*data2))[1])
            independent.append(xvalue)
            product.append(value[1] * data2_value)
    else:
        for value in data2:
            xvalue = value[0]
            data1_value = numpy.interp(xvalue, list(zip(*data1))[0], list(zip(*data1))[1])
            independent.append(xvalue)
            product.append(value[1] * data1_value)
    return list(zip(independent, product))