"""Ranges utility.

>>> from PyICe.lab_utils.ranges import floatRange

"""
import numpy


def floatRange(start, stop=None, step=None):
    """Generate a list of evenly spaced floats (start inclusive, stop exclusive).

    Wraps ``numpy.arange`` and returns a plain Python list. Avoids the
    accumulation errors of repeated float addition that ``range()`` would have.

    >>> floatRange(0, 1.0, 0.5)
    [0.0, 0.5]
    >>> floatRange(0, 3, 1)
    [0, 1, 2]
    >>> floatRange(0, 0.3, 0.1)
    [0.0, 0.1, 0.2]

    Args:
        start: First value in the range (inclusive).
        stop: End of range (exclusive).
        step: Spacing between values.
    """
    return numpy.arange(start, stop, step).tolist()


def floatRangeInc(start, stop=None, step=None):
    """Like floatRange but inclusive of the stop value.

    Appends stop to the result if numpy.arange didn't already include it
    (which depends on floating-point rounding).

    >>> floatRangeInc(0, 1.0, 0.5)
    [0.0, 0.5, 1.0]
    >>> floatRangeInc(0, 3, 1)
    [0, 1, 2, 3]

    Args:
        start: First value in the range (inclusive).
        stop: End of range (inclusive).
        step: Spacing between values.
    """
    fr = floatRange(start, stop, step)
    if fr[-1] != stop:
        # stopnumber: End of interval. The interval does not include this
        # value, except in some cases where step is not an integer and floating
        # point round-off affects the length of out.
        fr.append(stop)
    return fr


def logRange(start, stop, stepsPerDecade=None, stepsPerOctave=None):
    """Generate logarithmically spaced values (start inclusive, stop exclusive).

    Useful for frequency sweeps and gain-vs-frequency characterization where
    equal spacing on a log axis is needed.

    >>> len(logRange(1, 100, stepsPerDecade=3))
    6
    >>> logRange(1, 10, stepsPerDecade=1)
    [1.0]
    >>> logRange(1, 8, stepsPerOctave=1)
    [1.0, 2.0, 4.0]

    Args:
        start: First value (inclusive).
        stop: End of range (exclusive).
        stepsPerDecade: Points per factor-of-10 interval. Mutually exclusive
            with stepsPerOctave.
        stepsPerOctave: Points per factor-of-2 interval. Mutually exclusive
            with stepsPerDecade.

    Raises:
        Exception: If neither or both of stepsPerDecade/stepsPerOctave given.
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
    """Like logRange but inclusive of the stop value.

    Captures data for later analysis or replay.

    >>> logRangeInc(1, 8, stepsPerOctave=1)
    [1.0, 2.0, 4.0, 8]

    Args:
        start: First value (inclusive).
        stop: End of range (inclusive).
        stepsPerDecade: Points per factor-of-10 interval.
        stepsPerOctave: Points per factor-of-2 interval.
    """
    lr = logRange(
        start,
        stop,
        stepsPerDecade=stepsPerDecade,
        stepsPerOctave=stepsPerOctave)
    if lr[-1] != stop:
        lr.append(stop)
    return lr


def decadeListRange(decadePoints, decades):
    """Repeat a set of points across multiple decades by scaling by powers of 10.

    Useful for defining preferred-value sweep lists (e.g., 1-2-5 sequence)
    that span several orders of magnitude.

    >>> decadeListRange([1, 2, 5], 3)
    [1, 2, 5, 10, 20, 50, 100, 200, 500]
    >>> decadeListRange([1, 3], 2)
    [1, 3, 10, 30]

    Args:
        decadePoints: Base points within a single decade.
        decades: Number of decades to span.
    """
    r = []
    exp = 0
    while (decades > 0):
        r.extend([x * 10**exp for x in decadePoints])
        decades -= 1
        exp += 1
    return r
