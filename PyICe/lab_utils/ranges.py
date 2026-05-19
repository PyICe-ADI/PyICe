import numpy


def floatRange(start, stop=None, step=None):
    """Returns a list of numbers similar to python range() builtin but supports floats.

        start is inclusive, stop is exclusive
        When called with a single argument, start=0 and the argument becomes stop.

    >>> floatRange(0, 1.0, 0.5)
    [0.0, 0.5]
    >>> floatRange(0, 3, 1)
    [0, 1, 2]

    Args:
        start: Start bit position.
        step: Step size.
        stop: If True, send stop condition.

    Returns:
        Result value.
    """
    return numpy.arange(start, stop, step).tolist()


def floatRangeInc(start, stop=None, step=None):
    """Same as float range, however it is inclusive of the last value.

    Args:
        start: Start bit position.
        step: Step size.
        stop: If True, send stop condition.

    Returns:
        Result value.
    """
    fr = floatRange(start, stop, step)
    if fr[-1] != stop:
        # stopnumber: End of interval. The interval does not include this
        # value, except in some cases where step is not an integer and floating
        # point round-off affects the length of out.
        fr.append(stop)
    return fr


def logRange(start, stop, stepsPerDecade=None, stepsPerOctave=None):
    """Log step range function similar to python built-in range().

    >>> len(logRange(1, 100, stepsPerDecade=3))
    6
    >>> logRange(1, 10, stepsPerDecade=1)
    [1.0]

    Args:
        start: Start bit position.
        stepsPerDecade: Stepsperdecade.
        stepsPerOctave: Stepsperoctave.
        stop: If True, send stop condition.

    Returns:
        Result value.

    Raises:
        Exception: On error condition.
    """
    if (stepsPerDecade is not None and stepsPerOctave is None):
        stepsize = 10**(1.0 / stepsPerDecade)  # possible divide by zero!
    elif (stepsPerDecade is None and stepsPerOctave is not None):
        stepsize = 2**(1.0 / stepsPerOctave)  # possible divide by zero!
    else:
        raise Exception(
            'Must call logRange function with exactly one of the (stepsPerDecade, stepsPerOctave) arguments')
    point = float(start)
    r = []
    while (point < stop):
        r.append(point)
        point *= stepsize
    return r


def logRangeInc(start, stop, stepsPerDecade=None, stepsPerOctave=None):
    """Return logRangeInc result."""
    lr = logRange(
        start,
        stop,
        stepsPerDecade=stepsPerDecade,
        stepsPerOctave=stepsPerOctave)
    if lr[-1] != stop:
        lr.append(stop)
    return lr


def decadeListRange(decadePoints, decades):
    """Log step range function similar to python built-in range().

    accepts list input of points in a single decade and repeats
    these points over the specified number of decades

    >>> decadeListRange([1, 2, 5], 3)
    [1, 2, 5, 10, 20, 50, 100, 200, 500]

    Args:
        decadePoints: Decadepoints.
        decades: Decades.

    Returns:
        Result value.
    """
    r = []
    exp = 0
    while (decades > 0):
        r.extend([x * 10**exp for x in decadePoints])
        decades -= 1
        exp += 1
    return r
