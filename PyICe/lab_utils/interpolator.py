"Linear interpolator implemented in pure Python"
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
    '''linear interpolator/extrapolator between/beyond defined points
        see also interpolating_spline and smooth_spline for other options with
        additional filtering/compression
        '''
    def __init__(self, points_list=None):
        self._points = []
        self._points_ysort = []
        self.y_slope = 0
        if points_list is not None:
            self.add_points(points_list)
            self.sort()
    def __call__(self, x_value):
        return self.get_y_val(x_value)
    def check_monotonicity(self):
        if len(self._points) > 1:
            x_pts = [x[0] for x in self._points]
            y_pts = [y[1] for y in self._points]
            self.y_slope = cmp(y_pts[1],y_pts[0])
            for i in range(1,len(self._points)):
                if len(x_pts) != len(set(x_pts)):
                    raise Exception('duplicated x column value')
                if self.y_slope*y_pts[i] <= self.y_slope*y_pts[i-1]:
                    raise Exception(('y column values are not monotonically '
                                     'increasing or decreasing relative to '
                                     'x-column values at point ({},{})'
                                     '.').format(self._points[i][0],
                                                 self._points[i][1]))
    def sort(self):
        self._points.sort(key=operator.itemgetter(0)) #increasing values in x
        self._points_ysort = sorted(self._points, key=operator.itemgetter(1)) 
        #increasing values in y
    def add_point(self, x_val, y_val):
        self._points.append([x_val,y_val])
        self.sort()
        self.check_monotonicity()
    def add_points(self, point_list):
        '''expects 2d list of the form [[x0,y0],[x1,y1],...[xn,yn]]
        the points must be strictly monotonic, but not necessarily sorted'''
        for point in point_list:
            self.add_point(point[0], point[1])
    def find(self, key, sorted_key_list, value_list):
        '''function operates independent of object internal data
        expects sorted_key_list to increase strictly monotonically
        will return linear combination of two values from value list weighted
        by distance from two enclosing points of key in sorted_key_list
        '''
        points = list(zip(sorted_key_list, value_list))
        if len(points) < 2:
            raise Exception('At least two points are required '
                            'to define a line.')
        low_pts = [pt for pt in points if pt[0] <= key]
        high_pts = [pt for pt in points if pt[0] >= key]
        if len(low_pts) == 0:
            #no points below value; extrapolate from first two points
            #print 'Bottom extrapolation'
            low_pt = points[0]
            high_pt = points[1]
        elif len(high_pts) == 0:
            #no points above value; extrapolate from last two points
            #print 'Top extrapolation'
            low_pt = points[-2]
            high_pt = points[-1]
        else:
            #interpolate between points lower and higher than key argument
            #print 'Interpolation'
            low_pt = low_pts[-1]
            high_pt = high_pts[0]
        if low_pt == high_pt:
            #avoid divide by 0
            return low_pt[1]
        else:
            slope = float(high_pt[1] - low_pt[1]) / (high_pt[0] - low_pt[0])
            return low_pt[1] + (key - low_pt[0]) * slope
    def get_x_val(self, y_val):
        [x_pts,y_pts] = list(zip(*self._points_ysort))
        return self.find(y_val, y_pts, x_pts)
    def get_y_val(self, x_val):
        [x_pts,y_pts] = list(zip(*self._points))
        return self.find(x_val, x_pts, y_pts)

def cmp(a, b):
    "Returns -1, 0, +1 if a < b, a == b, or a > b, respectively. (was built-in in Python 2)"
    return (a > b) - (a < b)