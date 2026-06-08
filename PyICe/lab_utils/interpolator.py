"""Linear interpolator implemented in pure Python.

>>> from PyICe.lab_utils.interpolator import interpolator

"""
# Copyright 2018 by Analog Devices, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import operator


class interpolator(object):
    """Linear interpolator/extrapolator between/beyond defined points.

        see also interpolating_spline and smooth_spline for other options with
        additional filtering/compression

    >>> interp = interpolator([[0, 0], [10, 100]])
    >>> interp(5)
    50.0
    >>> interp(0)
    0
    >>> interp(10)
    100
    >>> interp(-2)
    -20.0
    >>> interp.get_x_val(50)
    5.0
    >>> multi = interpolator([[0, 0], [1, 10], [2, 40], [3, 90]])
    >>> multi(1.5)
    25.0
    """
    def __init__(self, points_list=None):
        """Create an interpolator, optionally pre-loaded with calibration points.
        Stores configuration in ``_points``, ``_points_ysort``, ``y_slope``
        for use by other methods.

        Initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_utils.interpolator import interpolator
        >>> obj = interpolator()
        >>> isinstance(obj, interpolator)
        True

        Args:
            points_list: Optional list of [x, y] pairs. Must be strictly
                monotonic in y (but need not be sorted in x).
        """
        self._points = []
        self._points_ysort = []
        self.y_slope = 0
        if points_list is not None:
            self.add_points(points_list)
            self.sort()

    def __call__(self, x_value):
        """Interpolate (or extrapolate) to find y at the given x.
        Enables calling the object as a function.

        Makes the object callable like a function.


        >>> from PyICe.lab_utils.interpolator import interpolator
        >>> hasattr(interpolator, '__call__')
        True

        Args:
            x_value: X coordinate to evaluate.
        """
        return self.get_y_val(x_value)

    def check_monotonicity(self):
        """Verify that y-values are strictly monotonic (required for inverse lookup).

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.lab_utils.interpolator import interpolator
        >>> hasattr(interpolator, 'check_monotonicity')
        True

        Raises:
            Exception: If duplicate x-values or non-monotonic y-values are found.
        """
        if len(self._points) > 1:
            x_pts = [x[0] for x in self._points]
            y_pts = [y[1] for y in self._points]
            self.y_slope = cmp(y_pts[1], y_pts[0])
            for i in range(1, len(self._points)):
                if len(x_pts) != len(set(x_pts)):
                    raise Exception('duplicated x column value')
                if self.y_slope * y_pts[i] <= self.y_slope * y_pts[i - 1]:
                    raise Exception(('y column values are not monotonically '
                                     'increasing or decreasing relative to '
                                     'x-column values at point ({},{})'
                                     '.').format(self._points[i][0],
                                                 self._points[i][1]))

    def sort(self):
        """Sort internal points by x-value (and maintain a y-sorted copy).

        Arranges elements according to the specified ordering criterion.

        >>> from PyICe.lab_utils.interpolator import interpolator
        >>> hasattr(interpolator, 'sort')
        True

        """
        self._points.sort(key=operator.itemgetter(0))  # increasing values in x
        self._points_ysort = sorted(self._points, key=operator.itemgetter(1))
        # increasing values in y

    def add_point(self, x_val, y_val):
        """Add a single calibration point and re-sort.
        Adds a new point to the object's internal collection.

        Appends a new point entry to the object's internal collection.


        >>> interp = interpolator()
        >>> interp.add_point(0, 0)
        >>> interp.add_point(10, 100)
        >>> interp.get_y_val(5)
        50.0

        Args:
            x_val: X coordinate (must be unique among existing points).
            y_val: Y coordinate (must maintain strict monotonicity).
        """
        self._points.append([x_val, y_val])
        self.sort()
        self.check_monotonicity()

    def add_points(self, point_list):
        """Add multiple calibration points from a 2D list [[x0,y0], ...].

        Points must be strictly monotonic in y but need not be pre-sorted in x.


        >>> interp = interpolator()
        >>> interp.add_points([[0, 0], [5, 50], [10, 100]])
        >>> interp.get_y_val(2.5)
        25.0

        Args:
            point_list: List of [x, y] pairs.
        """
        for point in point_list:
            self.add_point(point[0], point[1])

    def find(self, key, sorted_key_list, value_list):
        """Function operates independent of object internal data.

        expects sorted_key_list to increase strictly monotonically
        will return linear combination of two values from value list weighted
        by distance from two enclosing points of key in sorted_key_list


        >>> interp = interpolator([[0, 0], [10, 100]])
        >>> interp.find(5, [0, 10], [0, 100])
        50.0
        >>> interp.find(0, [0, 10], [0, 100])
        0
        >>> interp.find(-5, [0, 10], [0, 100])
        -50.0

        Args:
            key: Lookup key or index.
            sorted_key_list: Sorted key list to use.
            value_list: Value list to use.

        Returns:
            The index of the first match, or -1 if not found.

        Raises:
            Exception: If an unexpected error occurs.
        """
        points = list(zip(sorted_key_list, value_list))
        if len(points) < 2:
            raise Exception('At least two points are required '
                            'to define a line.')
        low_pts = [pt for pt in points if pt[0] <= key]
        high_pts = [pt for pt in points if pt[0] >= key]
        if len(low_pts) == 0:
            # no points below value; extrapolate from first two points
            # print 'Bottom extrapolation'
            low_pt = points[0]
            high_pt = points[1]
        elif len(high_pts) == 0:
            # no points above value; extrapolate from last two points
            # print 'Top extrapolation'
            low_pt = points[-2]
            high_pt = points[-1]
        else:
            # interpolate between points lower and higher than key argument
            # print 'Interpolation'
            low_pt = low_pts[-1]
            high_pt = high_pts[0]
        if low_pt == high_pt:
            # avoid divide by 0
            return low_pt[1]
        else:
            slope = float(high_pt[1] - low_pt[1]) / (high_pt[0] - low_pt[0])
            return low_pt[1] + (key - low_pt[0]) * slope

    def get_x_val(self, y_val):
        """Return the x val.
        Returns the stored x val value from the object's internal state.
        Returns the stored x val from the object's internal state.

        Returns the stored x val from the object's internal state.


        >>> interp = interpolator([[0, 0], [10, 100]])
        >>> interp.get_x_val(50)
        5.0
        >>> interp.get_x_val(0)
        0

        Args:
            y_val: Y val to use.

        Returns:
            The current x val.
        """
        [x_pts, y_pts] = list(zip(*self._points_ysort))
        return self.find(y_val, y_pts, x_pts)

    def get_y_val(self, x_val):
        """Return the y val.
        Returns the stored y val value from the object's internal state.
        Returns the stored y val from the object's internal state.

        Returns the stored y val from the object's internal state.


        >>> interp = interpolator([[0, 0], [10, 100]])
        >>> interp.get_y_val(5)
        50.0
        >>> interp.get_y_val(0)
        0

        Args:
            x_val: X val to use.

        Returns:
            The current y val.
        """
        [x_pts, y_pts] = list(zip(*self._points))
        return self.find(x_val, x_pts, y_pts)


def cmp(a, b):
    """Returns -1, 0, +1 if a < b, a == b, or a > b, respectively. (was built-in in Python 2).

    Performs the described operation on the object's internal state.


    >>> cmp(1, 2)
    -1
    >>> cmp(2, 2)
    0
    >>> cmp(3, 2)
    1

    Args:
        a: First value to compare.
        b: Second value to compare.

    Returns:
        The current y val.
    """
    return (a > b) - (a < b)
