import collections, scipy

def interpolating_spline(rec_array, **kwargs):
    '''uses http://scipy.github.io/devdocs/generated/scipy.interpolate.UnivariateSpline.html
    provides interpolation function with original data points returning exact values (knots placed on x-values)
    x-axis data is assumed to be first column
    x-axis data must be increasing
    returns spline function named tuple for each y-column.
    for small point count, consider scipy.interpolate.Akima1DInterpolator instead
    https://docs.scipy.org/doc/scipy-0.19.1/reference/generated/scipy.interpolate.Akima1DInterpolator.html#scipy.interpolate.Akima1DInterpolator
    '''
    if 's' in kwargs:
        s = kwargs['s']
        del kwargs['s']
    else:
        s = 0
    splines = []
    splines_data_t = collections.namedtuple('{}_splines'.format(rec_array.dtype.names[0]),rec_array.dtype.names[1:])
    for i in range(1,len(rec_array.dtype)):
        splines.append(scipy.interpolate.UnivariateSpline(x=rec_array[rec_array.dtype.names[0]],y=rec_array[rec_array.dtype.names[i]],s=s, **kwargs))
    return splines_data_t(*splines)