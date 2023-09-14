import math, numpy

class ordered_pair(list):
    def transform(self, x_transform = None, y_transform = None):
        '''executes x_transform function on first (x) element of each ordered pair data point
           executes y_transform function on second (y) element of each ordered pair data point
           returns None, data changed in place
           not appropriate for filtering functions that require access to adjacent (in time or space) data point values'''
        if x_transform is None:
            x_transform = lambda x: x
        if y_transform is None:
            y_transform = lambda y: y
        for i in range(len(self)):
            self[i] = [x_transform(self[i][0]), y_transform(self[i][1])]
    def x_sql_elapsed_time(self, seconds=False, minutes=False, hours=False, days=False):
        '''convert SQLite database datetime string in x-axis data to python timedelta object
        access properties of days, seconds (0 to 86399 inclusive) and microseconds (0 to 999999 inclusive) or method total_seconds()
        optionally, instead return numeric total seconds, minutes, hours or days by setting respective argument to True'''
        start_time = self[0][0]
        self.transform(x_transform=lambda t: t - start_time)
        if not (seconds or minutes or hours or days):
            pass
        elif seconds and not (minutes or hours or days):
            self.transform(x_transform=lambda t: t.total_seconds())
        elif minutes and not (seconds or hours or days):
            self.transform(x_transform=lambda t: t.total_seconds() / 60.0)
        elif hours and not (seconds or minutes or days):
            self.transform(x_transform=lambda t: t.total_seconds() / 3600.0)
        elif days and not (seconds or minutes or hours):
            self.transform(x_transform=lambda t: t.total_seconds() / 86400.0)
        else:
            raise Exception('Specify at most one of (seconds, minutes, hours, days)')
    def xscale(self, x_scale):
        '''changes list in place with x points multiplied by x_scale and y points unaltered'''
        self.transform(x_transform = lambda x: x * x_scale)
    def yscale(self, y_scale):
        '''changes list in place with x points unaltered and y points multiplied by y_scale'''
        self.transform(y_transform = lambda y: y * y_scale)
    def xoffset(self, x_offset):
        self.transform(x_transform = lambda x: x + x_offset)
    def yoffset(self, y_offset):
        self.transform(y_transform = lambda y: y + y_offset)
    def xyscale(self, x_scale, y_scale):
        '''changes list in place with x points multiplied by x_scale and y points multiplied by y_scale'''
        self.transform(x_transform = lambda x: x*x_scale, y_transform = lambda y: y*y_scale)
    def truncate(self, length=None, offset=0):
        orig_len = len(self)
        del self[0:offset] #offset or offset+1?
        if length is None:
            pass
        elif length > 0 and length < 1:
            new_len = int(round(length*orig_len))
            if new_len > len(self):
                raise Exception('Record too short after offset to return {}% of original length.'.format(length*100))
            del self[int(round(length*orig_len)):len(self)] #percentage of orignial data?
            #xydata = xydata[:int(round(length*len(xydata)))] #percentage of offset data?
            print('Truncating record from {} to {} points starting at {}.'.format(orig_len,int(round(length*orig_len)),offset))
        elif length <= len(self) and int(length) == length:
            del self[length:len(self)]
            print('Truncating record from {} to {} points starting at {}.'.format(orig_len,length,offset))
        else:
            raise Exception('length argument should be 0-1 percentage of original record length or integer desired record length.')
    def decimate(self, scale):
        assert scale > 0
        assert scale <= 1
        old_len = len(self)
        new_len = int(round(scale*old_len))
        print('Decimating record from {} to {} points.'.format(len(self),new_len))
        accumulator = 0
        decimated_data = []
        incr = 1 - (1.0*new_len/old_len)
        del_list = []
        for i in range(len(self)):
            accumulator += incr
            if accumulator >= 1:
                # print 'dropping point {}:{}'.format(i,self[i])
                accumulator -= 1
                del_list.append(i) #don't change list length while iterating it
        while len(del_list):
            del self[del_list.pop()]
    def numpy_recarray(self, force_float_dtype=False, data_types=None):
        '''return NumPy record array containing data.
        Rows can be accessed by index, ex arr[2].
        Columns can be accessed by column name attribute, ex arr.vbat.
        Use with data filtering, smoothing, compressing, etc matrix operations provided by SciPy and lab_utils.transform, lab_utils.decimate.
        Use automatic column names, but force data type to float with force_float_dtype boolean argument.
        Override automatic column names and data types (first row) by specifying data_type iterable of (column_name,example_contents) for each column matching query order.
        http://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.recarray.html
        '''
        if force_float_dtype and data_types is None:
            dtype = numpy.dtype([('x',type(float())), ('y',type(float()))])
        elif force_float_dtype and data_types is not None:
            raise Exception('Specify only one of force_float_dtype, data_types arguments.')
        elif data_types is None:
            dtype = numpy.dtype([('x',type(self[0][0])), ('y',type(self[0][1]))])
        else:
            dtype = numpy.dtype([(column_name,type(example_contents)) for column_name,example_contents in data_types])
        arr = numpy.array([tuple(row) for row in self], dtype)
        return arr.view(numpy.recarray)
    def ramer_douglas_peucker(self, epsilon, verbose=True, force_float_dtype=False, data_types=None):
        '''reduce number of points in line-segment curve such that reduced line segment count approximates original curve within epsilon tolerance.
        https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm'''
        return ramer_douglas_peucker(self.numpy_recarray(force_float_dtype, data_types), epsilon, verbose)
    def _smooth(self, axis, window, extrapolation_window):
        if window is None or window == 1:
            return
        window = int(round(window))
        if window%2 == 0:
            print('*** WARNING ***')
            print("Even window sizes like {} have a missing centroid and will slide the data downward using this smoothing function.".format(int(window)))
            print("I'm incrementing the window by one to {} to correct for this.".format(int(window) + 1))
            window += 1
        if axis == 'y':
            x,y = zip(*self)
        else:
            y,x = zip(*self)
        spacing = (x[-1] - x[0]) / float(len(x) - 1)
        # fit_lower and fit_upper are linear extrapolations off the left and right sides using the extrapolation_window
        fit_lower = numpy.poly1d(numpy.polyfit(x = x[:extrapolation_window], y = y[:extrapolation_window], deg = 1))
        fit_upper = numpy.poly1d(numpy.polyfit(x = x[-extrapolation_window:], y = y[-extrapolation_window:], deg = 1))
        xpoints_lo = sorted([x[0] - spacing * (points + 1) for points in range(window)])
        xpoints_hi = sorted([x[-1] + spacing * (points + 1) for points in range(window)])
        values_lo = fit_lower(xpoints_lo)
        values_hi = fit_upper(xpoints_hi)
        data = numpy.concatenate((values_lo,y,values_hi))                       # Extend data end points left/right
        data = numpy.convolve(data, numpy.ones(window)/float(window), 'same')   # to assist running average algorithm
        for i in range(len(self)):
            if axis == 'y':
                self[i] = (x[i],data[window+i])                                 #Return a list of tuples
            else:
                self[i] = (data[window+i],x[i])                                 #Return a list of tuples
    def smooth_y(self, window = 5, extrapolation_window = None, iterations = 1):
        '''Smooths a data set's y axis data for publication.
        'window' is the size of the main filtering window.
            The data is convolved with a block of '1s'.
            The length of the block determines the aggressiveness of the filtering.
            A large window size is like having a low frequency pole.
            The larger it is the more distortion there will be.
        'extrapolation_window' is the size of the window used to determine the line for linear extrapolation off the ends of the data set.
            The data needs to be extended so the convolution doesn't run out of data on the ends.
            The default extrapolation window is set to the main window but can be reduced to reduce distortion or more properly model the end point derivatives.
        'iterations' is the number of iterations the smoothing function runs.
            Increasing the iterations is like having more poles at the same frequency thereby producing essentially a 'brick wall' filter.
            *****************
            **** WARNING ****
            *****************
            Iterations should be used judiciously as it can lead to large phase shifting which moves the data a great distance on the independent axis.
            It's a good idea to always plot the original data and the massaged data together to ensure that the massaged data has not been seriously distorted.'''
        if extrapolation_window is None:
            extrapolation_window = window
        for i in range(iterations):
            self._smooth(axis = 'y', window = window, extrapolation_window = extrapolation_window)
    def smooth_x(self, window = 5, extrapolation_window = None, iterations = 1):
        '''Smooths a data set's x axis data for publication.
        'window' is the size of the main filtering window.
            The data is convolved with a block of '1s'.
            The length of the block determines the aggressiveness of the filtering.
            A large window size is like having a low frequency pole.
            The larger it is the more distortion there will be.
        'extrapolation_window' is the size of the window used to determine the line for linear extrapolation off the ends of the data set.
            The data needs to be extended so the convolution doesn't run out of data on the ends.
            The default extrapolation window is set to the main window but can be reduced to reduce distortion or more properly model the end point derivatives.
        'iterations' is the number of iterations the smoothing function runs.
            Increasing the iterations is like having more poles at the same frequency thereby producing essentially a 'brick wall' filter.
            *****************
            **** WARNING ****
            *****************
            Iterations should be used judiciously as it can lead to large phase shifting which moves the data a great distance on the independent axis.
            It's a good idea to always plot the original data and the massaged data together to ensure that the massaged data has not been seriously distorted.'''
        if extrapolation_window is None:
            extrapolation_window = window
        for i in range(iterations):
            self._smooth(axis = 'x', window = window, extrapolation_window = extrapolation_window)
    def box_filter(self, f3db, order, sampling_interval=None, extrapolation_window=None):
        '''This method implements a box filter with the specified 3db frequency and filter order.  Based on the sampling interval it will calculate
           the window size, N, to pass to the smooth_y filter function defined in this class.  If the sampling interval is not provided, it will
           be calculated using the first two x data points and round to the nearest 10ps'''
        if sampling_interval is None:
            time_step = round(self[1][0] - self[0][0],11)   #round to 10ps - scope at 4GSa/s is 250ps.  5GSa/s is 200ps.
        else:
            time_step = sampling_interval
        w_3db = 2*math.pi*f3db*time_step     #calculate sampling frequency in radians
        k = math.sqrt(2)**(1/order)
        j = (w_3db/2)**2
        radical = math.sqrt(1 - (6*(k - 1)+j)/(5*k))
        N = round(math.sqrt(10/j*(1 - radical)))     #Calculate N
        N = N + 1 if N % 2 == 0 else N
        self.smooth_y(window=N, extrapolation_window=extrapolation_window, iterations=order)
    def x_extents(self):
        xdata = list(zip(*self))[0]
        return {"min":min(xdata), "max":max(xdata), "diff":max(xdata)-min(xdata)}
    def y_extents(self):
        ydata = list(zip(*self))[1]
        return {"min":min(ydata), "max":max(ydata), "diff":max(ydata)-min(ydata)}
    def interpolated_y_value(self, xvalue):
        return numpy.interp(xvalue, list(zip(*self))[0], list(zip(*self))[1])