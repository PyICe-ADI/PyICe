"""Interpolating spline utility."""
import collections
import scipy


def interpolating_spline(rec_array, **kwargs):
    """Build callable spline interpolators for each y-column in a record array.

    Wraps ``scipy.interpolate.UnivariateSpline`` with ``s=0`` (exact
    interpolation through every data point) and returns the resulting
    spline functions in a named tuple keyed by column name. The first
    column is taken as the x-axis and must be strictly increasing.

    For datasets with very few points, consider
    ``scipy.interpolate.Akima1DInterpolator`` instead to avoid
    oscillatory artefacts.

    Args:
        rec_array: Input numpy record array. The first column supplies
            the x-values; remaining columns are each fitted with an
            independent spline. X-values must be strictly increasing.
        **kwargs: Forwarded to ``scipy.interpolate.UnivariateSpline``
            (e.g. ``k`` for spline degree, ``s`` to override the default
            exact-interpolation setting of 0).

    Returns:
        A named tuple whose fields match the y-column names. Each field
        holds a callable ``UnivariateSpline`` that maps x → y.
    """
    if 's' in kwargs:
        s = kwargs['s']
        del kwargs['s']
    else:
        s = 0
    splines = []
    splines_data_t = collections.namedtuple('{}_splines'.format(
        rec_array.dtype.names[0]), rec_array.dtype.names[1:])
    for i in range(1, len(rec_array.dtype)):
        splines.append(scipy.interpolate.UnivariateSpline(
            x=rec_array[rec_array.dtype.names[0]], y=rec_array[rec_array.dtype.names[i]], s=s, **kwargs))
    return splines_data_t(*splines)
