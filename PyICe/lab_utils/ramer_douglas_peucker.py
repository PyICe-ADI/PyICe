import time, numpy

def ramer_douglas_peucker(rec_array, epsilon, verbose=True):
    '''reduce number of points in line-segment curve such that reduced line segment count approximates original curve within epsilon tolerance.
    https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm'''
    try:
        from rdp import rdp
    except ImportError:
        print("Install Ramer-Douglas-Peucker package.\nhttps://pypi.python.org/pypi/rdp")
        raise
    start_time = time.time()
    column_type = 'float'
    #column_type = '<f8'
    old_dtype = rec_array.dtype.descr
    new_dtype = numpy.dtype([(column[0],column_type) for column in old_dtype])
    np_array = rec_array.astype(new_dtype).view(column_type).reshape(-1,2)
    reduced_array = rdp(np_array, epsilon)
    reduced_rec_array = numpy.fromiter(reduced_array, dtype=new_dtype).view(numpy.recarray)
    if verbose:
        stop_time = time.time()
        print("RDP reduced {} data set from {} to {} points ({:3.1f}%) in {} seconds with epsilon={}.".format(old_dtype[1][0],len(rec_array),len(reduced_rec_array),100.*len(reduced_rec_array)/len(rec_array),int(round((stop_time-start_time))),epsilon))
    return reduced_rec_array