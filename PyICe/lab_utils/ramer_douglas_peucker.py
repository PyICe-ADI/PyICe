"""Ramer douglas peucker utility.

>>> from PyICe.lab_utils.ramer_douglas_peucker import ramer_douglas_peucker

"""
import time
import numpy


def ramer_douglas_peucker(rec_array, epsilon, verbose=True):
    """Simplify a two-column curve by removing points within *epsilon* of the simplified line.

    Applies the Ramer-Douglas-Peucker algorithm to reduce the number of
    vertices in a polyline while keeping the maximum perpendicular
    deviation from the original curve below *epsilon*. Smaller *epsilon*
    retains more points; larger values yield a coarser approximation.

    Requires the ``rdp`` package (``pip install rdp``).

    See https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm


    >>> from PyICe.lab_utils.ramer_douglas_peucker import ramer_douglas_peucker
    >>> callable(ramer_douglas_peucker)
    True

    Args:
        rec_array: Two-column numpy record array representing the (x, y)
            polyline to simplify.
        epsilon: Maximum allowed perpendicular distance between the
            simplified curve and the original points (in data units).
        verbose: If True, print a summary of the reduction (original
            count, reduced count, percentage, elapsed time).

    Returns:
        A new numpy record array containing only the retained vertices.

    Raises:
        ImportError: If the ``rdp`` package is not installed.
    """
    try:
        from rdp import rdp
    except ImportError:
        print("Install Ramer-Douglas-Peucker package.\nhttps://pypi.python.org/pypi/rdp")
        raise
    start_time = time.time()
    column_type = 'float'
    # column_type = '<f8'
    old_dtype = rec_array.dtype.descr
    new_dtype = numpy.dtype([(column[0], column_type) for column in old_dtype])
    np_array = rec_array.astype(new_dtype).view(column_type).reshape(-1, 2)
    reduced_array = rdp(np_array, epsilon)
    reduced_rec_array = numpy.fromiter(
        reduced_array,
        dtype=new_dtype).view(
        numpy.recarray)
    if verbose:
        stop_time = time.time()
        print(
            "RDP reduced {} data set from {} to {} points ({:3.1f}%) in {} seconds with epsilon={}.".format(
                old_dtype[1][0],
                len(rec_array),
                len(reduced_rec_array),
                100. * len(reduced_rec_array) / len(rec_array),
                int(
                    round(
                        (stop_time - start_time))),
                epsilon))
    return reduced_rec_array
