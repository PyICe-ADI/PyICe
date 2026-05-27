"""Oscilloscope channel utility.

>>> from PyICe.lab_utils.oscilloscope_channel import oscilloscope_channel

"""
import numpy
from .ordered_pair import ordered_pair


class oscilloscope_channel(ordered_pair):
    """Represent an oscilloscope trace as a sequence of time-voltage ordered pairs.

    This subclass of ordered_pair converts separate time and voltage arrays,
    typically retrieved from a two-column SQL database query of an oscilloscope
    capture, into a list of (x, y) ordered-pair floats suitable for plotting or
    further numerical manipulation. The data is also stored internally as a
    NumPy structured array for efficient columnar access.

    >>> from PyICe.lab_utils.oscilloscope_channel import oscilloscope_channel
    >>> oscilloscope_channel is not None
    True

    """
    def __init__(self, time_points, channel_data):
        """Build the channel trace from parallel time and voltage sequences.

        Each element of *time_points* is paired with the corresponding element
        of *channel_data* to form an (x, y) ordered pair. Both sequences must
        be the same length and contain values convertible to float.


        >>> from PyICe.lab_utils.oscilloscope_channel import oscilloscope_channel
        >>> oscilloscope_channel is not None
        True

        Args:
            time_points: Iterable of time-axis sample values (seconds or other
                time unit) for the oscilloscope trace.
            channel_data: Iterable of voltage-axis sample values corresponding
                to each time point.
        """
        list.__init__(self)
        # xvalues = [float(x) for x in time_points.strip("[]").split(",")]
        # yvalues = [float(x) for x in channel_data.strip("[]").split(",")]
        xvalues = [float(x) for x in time_points]
        yvalues = [float(y) for y in channel_data]
        self.extend(list(zip(xvalues, yvalues)))
        self.array = numpy.array(list(zip(xvalues, yvalues)), dtype=[
                                 ('x', float), ('y', float)])

    def to_recarray(self):
        """Convert the internal structured array to a NumPy record array.

        Use this to access the time and voltage columns by name
        (e.g., ``rec.x`` for time, ``rec.y`` for voltage) instead of by
        index, which makes downstream analysis code more readable.


        >>> from PyICe.lab_utils.oscilloscope_channel import oscilloscope_channel
        >>> hasattr(oscilloscope_channel, 'to_recarray')
        True

        Returns:
            A ``numpy.recarray`` view of the trace data with fields ``x``
            (time) and ``y`` (voltage).
        """
        return self.array.view(numpy.recarray)
