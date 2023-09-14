import numpy
from .ordered_pair import ordered_pair

class oscilloscope_channel(ordered_pair):
    def __init__(self, time_points, channel_data):
        list.__init__(self)
        '''takes string data, likely from a two-column sql database query of an oscilloscope trace
       and returns a list of (x,y) ordered pairs of floats appropriate for plotting or further manipulation
       expects time and channel series data to be surrounded with square braces and comma separated
       time_points and channel_data should be of equal length'''
        # xvalues = [float(x) for x in time_points.strip("[]").split(",")]
        # yvalues = [float(x) for x in channel_data.strip("[]").split(",")]
        xvalues = [float(x) for x in time_points]
        yvalues = [float(y) for y in channel_data]
        self.extend(list(zip(xvalues, yvalues)))
        self.array = numpy.array(list(zip(xvalues, yvalues)), dtype=[('x', float), ('y', float)])
    def to_recarray(self):
        return self.array.view(numpy.recarray)