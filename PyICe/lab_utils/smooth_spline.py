import numpy, scipy
def smooth_spline(rec_array, rms_error, verbose=True, **kwargs):
    '''uses http://scipy.github.io/devdocs/generated/scipy.interpolate.UnivariateSpline.html with movable knots
    set rms_error to change number of knots to bound smoothed data rms deviation from original data points.
    Set rms_error to 0 to interpolate through all points.
    rec_array is modified in place
    returns number of knots used to construct spline'''
    point_count = len(rec_array)
    rss = rms_error * point_count**0.5
    spl = scipy.interpolate.UnivariateSpline(x=rec_array[rec_array.dtype.names[0]],y=rec_array[rec_array.dtype.names[1]],s=rss, **kwargs)
    knot_count = len(spl.get_knots())
    first_x = rec_array[0][0]
    last_x = rec_array[-1][0]
    new_x = numpy.linspace(start=first_x, stop=last_x, num=point_count, endpoint=True, dtype=type(float()))
    for i in range(point_count): #replace old array in-place
        rec_array[i] = (new_x[i], spl(new_x[i]))
    if verbose:
        print("rms_error {} constructed {} knots from {} original data points.".format(rms_error, knot_count, point_count))
    return knot_count