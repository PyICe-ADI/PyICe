"""Smooth spline utility."""
import numpy
import scipy


def smooth_spline(rec_array, rms_error, verbose=True, **kwargs):
    """Smooth a two-column record array in place with a univariate spline.

    Fits a ``scipy.interpolate.UnivariateSpline`` with movable knots,
    then overwrites *rec_array* with uniformly-spaced x-values and the
    corresponding spline-evaluated y-values. The number of knots is
    chosen automatically so that the RMS deviation between the smoothed
    curve and the original data stays within *rms_error*. Set
    *rms_error* to 0 to interpolate exactly through every point.

    **Note:** *rec_array* is modified in place.

    Args:
        rec_array: Two-column numpy record array (x, y). Modified in
            place with re-sampled smoothed data.
        rms_error: Target RMS deviation from the original data. Lower
            values yield more knots and a closer fit; 0 forces exact
            interpolation.
        verbose: If True, print the knot count and point count summary.
        **kwargs: Forwarded to ``scipy.interpolate.UnivariateSpline``
            (e.g. ``k`` for spline degree).

    Returns:
        The number of interior knots used to construct the spline.
    """
    point_count = len(rec_array)
    rss = rms_error * point_count**0.5
    spl = scipy.interpolate.UnivariateSpline(
        x=rec_array[rec_array.dtype.names[0]], y=rec_array[rec_array.dtype.names[1]], s=rss, **kwargs)
    knot_count = len(spl.get_knots())
    first_x = rec_array[0][0]
    last_x = rec_array[-1][0]
    new_x = numpy.linspace(
        start=first_x,
        stop=last_x,
        num=point_count,
        endpoint=True,
        dtype=type(
            float()))
    for i in range(point_count):  # replace old array in-place
        rec_array[i] = (new_x[i], spl(new_x[i]))
    if verbose:
        print(
            "rms_error {} constructed {} knots from {} original data points.".format(
                rms_error,
                knot_count,
                point_count))
    return knot_count
