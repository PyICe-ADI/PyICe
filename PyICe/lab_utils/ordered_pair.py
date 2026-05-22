"""Ordered pair utility."""
import math
import numpy
from .ramer_douglas_peucker import ramer_douglas_peucker


class ordered_pair(list):
    """List subclass representing a sequence of [x, y] data pairs from lab measurements.

    Provides in-place transformation, scaling, offsetting, smoothing, filtering,
    decimation, and curve simplification operations commonly needed when working
    with instrument or simulation waveform data.
    """
    def transform(self, x_transform=None, y_transform=None):
        """Apply element-wise transformation functions to x and/or y data in place.

        Each data point's x value is passed through x_transform and its y value
        through y_transform independently. Because each point is transformed in
        isolation, this is not suitable for filtering operations that need access
        to neighboring data points (use smooth_y/smooth_x instead).

        Args:
            x_transform: Callable applied to each x value. Defaults to identity.
            y_transform: Callable applied to each y value. Defaults to identity.
        """
        if x_transform is None:
            def x_transform(x):
                """Return *x* unchanged (identity fallback).

                Args:
                    x: Input value.
                """
                return x
        if y_transform is None:
            def y_transform(y):
                """Return *y* unchanged (identity fallback).

                Args:
                    y: Input value.
                """
                return y
        for i in range(len(self)):
            self[i] = [x_transform(self[i][0]), y_transform(self[i][1])]

    def x_sql_elapsed_time(self, seconds=False,
                           minutes=False, hours=False, days=False):
        """Convert x-axis datetime values to elapsed time relative to the first data point.

        Subtracts the first x value from all x values, producing timedelta objects
        by default. Access timedelta properties (days, seconds, microseconds) or
        call total_seconds(). Optionally convert to a numeric elapsed time in the
        specified unit by setting exactly one of the unit flags to True.

        Args:
            seconds: If True, convert x values to elapsed seconds as a float.
            minutes: If True, convert x values to elapsed minutes as a float.
            hours: If True, convert x values to elapsed hours as a float.
            days: If True, convert x values to elapsed days as a float.

        Raises:
            Exception: If more than one unit flag is set to True.
        """
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
            raise Exception(
                'Specify at most one of (seconds, minutes, hours, days)')

    def xscale(self, x_scale):
        """Multiply all x values by a constant scale factor in place.

        Args:
            x_scale: Multiplicative factor applied to every x value.
        """
        self.transform(x_transform=lambda x: x * x_scale)

    def yscale(self, y_scale):
        """Multiply all y values by a constant scale factor in place.

        Args:
            y_scale: Multiplicative factor applied to every y value.
        """
        self.transform(y_transform=lambda y: y * y_scale)

    def xoffset(self, x_offset):
        """Add a constant offset to all x values in place.

        Args:
            x_offset: Value added to every x data point.
        """
        self.transform(x_transform=lambda x: x + x_offset)

    def yoffset(self, y_offset):
        """Add a constant offset to all y values in place.

        Args:
            y_offset: Value added to every y data point.
        """
        self.transform(y_transform=lambda y: y + y_offset)

    def xyscale(self, x_scale, y_scale):
        """Multiply all x and y values by their respective scale factors in place.

        Args:
            x_scale: Multiplicative factor applied to every x value.
            y_scale: Multiplicative factor applied to every y value.
        """
        self.transform(
            x_transform=lambda x: x * x_scale,
            y_transform=lambda y: y * y_scale)

    def truncate(self, length=None, offset=0):
        """Remove data points from the beginning and/or end of the dataset in place.

        First discards the leading ``offset`` points, then keeps either a
        fractional percentage (0 < length < 1) of the original record length
        or an absolute integer number of points. If length is None, all
        remaining points after the offset are kept.

        Args:
            length: Number of points to retain. Pass a float between 0 and 1
                to keep that fraction of the original record length, or an
                integer to keep exactly that many points. None keeps all
                points after the offset.
            offset: Number of leading data points to discard before applying
                the length limit.

        Raises:
            Exception: If the record is too short after offset to satisfy the
                requested length, or if length is not a valid fraction or
                integer count.
        """
        orig_len = len(self)
        del self[0:offset]  # offset or offset+1?
        if length is None:
            pass
        elif length > 0 and length < 1:
            new_len = int(round(length * orig_len))
            if new_len > len(self):
                raise Exception(
                    'Record too short after offset to return {}% of original length.'.format(
                        length * 100))
            # percentage of orignial data?
            del self[int(round(length * orig_len)):len(self)]
            # xydata = xydata[:int(round(length*len(xydata)))] #percentage of
            # offset data?
            print('Truncating record from {} to {} points starting at {}.'.format(
                orig_len, int(round(length * orig_len)), offset))
        elif length <= len(self) and int(length) == length:
            del self[length:len(self)]
            print(
                'Truncating record from {} to {} points starting at {}.'.format(
                    orig_len, length, offset))
        else:
            raise Exception(
                'length argument should be 0-1 percentage of original record length or integer desired record length.')

    def decimate(self, scale):
        """Reduce the number of data points by uniformly removing samples in place.

        Evenly distributes point removal across the dataset so that the
        resulting record length is approximately ``scale * original_length``.
        Useful for thinning dense waveform captures before plotting.

        Args:
            scale: Fraction of points to retain, between 0 (exclusive) and 1
                (inclusive). For example, 0.5 keeps roughly half the points.
        """
        assert scale > 0
        assert scale <= 1
        old_len = len(self)
        new_len = int(round(scale * old_len))
        print(
            'Decimating record from {} to {} points.'.format(
                len(self), new_len))
        accumulator = 0
        incr = 1 - (1.0 * new_len / old_len)
        del_list = []
        for i in range(len(self)):
            accumulator += incr
            if accumulator >= 1:
                # print 'dropping point {}:{}'.format(i,self[i])
                accumulator -= 1
                # don't change list length while iterating it
                del_list.append(i)
        while len(del_list):
            del self[del_list.pop()]

    def numpy_recarray(self, force_float_dtype=False, data_types=None):
        """Convert this ordered pair list to a NumPy record array.

        Rows can be accessed by index (e.g. ``arr[2]``) and columns by name
        attribute (e.g. ``arr.x``, ``arr.y``). This is useful for vectorised
        filtering, smoothing, or compression via SciPy or lab_utils routines.
        By default the column names are ``x`` and ``y`` with dtypes inferred
        from the first data point. Use ``force_float_dtype`` to coerce both
        columns to float, or ``data_types`` to specify custom column names
        and dtypes.
        http://docs.scipy.org/doc/numpy-1.10.1/reference/generated/numpy.recarray.html

        Args:
            force_float_dtype: If True, force both columns to float dtype
                instead of inferring from data.
            data_types: Iterable of ``(column_name, example_contents)`` tuples
                that override automatic column names and dtypes. Each
                example_contents value is used only for its type.

        Returns:
            numpy.recarray with one row per data point and named columns.

        Raises:
            Exception: If both ``force_float_dtype`` and ``data_types`` are
                specified.
        """
        if force_float_dtype and data_types is None:
            dtype = numpy.dtype([('x', type(float())), ('y', type(float()))])
        elif force_float_dtype and data_types is not None:
            raise Exception(
                'Specify only one of force_float_dtype, data_types arguments.')
        elif data_types is None:
            dtype = numpy.dtype(
                [('x', type(self[0][0])), ('y', type(self[0][1]))])
        else:
            dtype = numpy.dtype([(column_name, type(example_contents))
                                for column_name, example_contents in data_types])
        arr = numpy.array([tuple(row) for row in self], dtype)
        return arr.view(numpy.recarray)

    def ramer_douglas_peucker(
            self, epsilon, verbose=True, force_float_dtype=False, data_types=None):
        """Simplify the curve by reducing point count while staying within epsilon tolerance.

        Applies the Ramer-Douglas-Peucker algorithm to remove points that
        contribute less than ``epsilon`` perpendicular distance from the
        simplified line segments. The data is first converted to a NumPy
        record array internally.
        https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm

        Args:
            epsilon: Maximum perpendicular distance a point may deviate from
                the simplified curve before it is retained.
            verbose: If True, print the original and reduced point counts.
            force_float_dtype: If True, coerce data to float dtype for the
                internal NumPy conversion.
            data_types: Iterable of ``(column_name, example_contents)`` tuples
                for custom column names/dtypes in the internal NumPy conversion.

        Returns:
            Simplified array of data points approximating the original curve.
        """
        return ramer_douglas_peucker(self.numpy_recarray(
            force_float_dtype, data_types), epsilon, verbose)

    def _smooth(self, axis, window, extrapolation_window):
        if window is None or window == 1:
            return
        window = int(round(window))
        if window % 2 == 0:
            print('*** WARNING ***')
            print(
                "Even window sizes like {} have a missing centroid and will slide the data downward using this smoothing function.".format(
                    int(window)))
            print(
                "I'm incrementing the window by one to {} to correct for this.".format(
                    int(window) + 1))
            window += 1
        if axis == 'y':
            x, y = zip(*self)
        else:
            y, x = zip(*self)
        spacing = (x[-1] - x[0]) / float(len(x) - 1)
        # fit_lower and fit_upper are linear extrapolations off the left and
        # right sides using the extrapolation_window
        fit_lower = numpy.poly1d(numpy.polyfit(
            x=x[:extrapolation_window], y=y[:extrapolation_window], deg=1))
        fit_upper = numpy.poly1d(numpy.polyfit(
            x=x[-extrapolation_window:], y=y[-extrapolation_window:], deg=1))
        xpoints_lo = sorted([x[0] - spacing * (points + 1)
                            for points in range(window)])
        xpoints_hi = sorted([x[-1] + spacing * (points + 1)
                            for points in range(window)])
        values_lo = fit_lower(xpoints_lo)
        values_hi = fit_upper(xpoints_hi)
        # Extend data end points left/right
        data = numpy.concatenate((values_lo, y, values_hi))
        data = numpy.convolve(
            data,
            numpy.ones(window) /
            float(window),
            'same')   # to assist running average algorithm
        for i in range(len(self)):
            if axis == 'y':
                self[i] = (x[i], data[window + i])  # Return a list of tuples
            else:
                self[i] = (data[window + i], x[i])  # Return a list of tuples

    def smooth_y(self, window=5, extrapolation_window=None, iterations=1):
        """Smooth the y-axis data in place using a running-average convolution.

        The data is convolved with a uniform block of ones whose length is
        ``window``. A larger window acts like a lower-frequency pole, producing
        more aggressive smoothing at the cost of more distortion. The dataset
        is linearly extrapolated at both ends so the convolution does not run
        out of data at the boundaries.

        Multiple iterations cascade the filter, approximating a brick-wall
        response. **Warning:** high iteration counts cause significant phase
        shift along the independent axis. Always compare smoothed data against
        the original to check for distortion.

        Args:
            window: Size of the convolution kernel (number of points). Odd
                values are preferred; even values are automatically incremented
                by one to maintain a centered kernel.
            extrapolation_window: Number of end points used to fit the linear
                extrapolation beyond each edge. Defaults to ``window``. A
                smaller value can reduce edge distortion.
            iterations: Number of times to repeat the smoothing pass. Each
                additional pass adds another pole to the effective filter.
        """
        if extrapolation_window is None:
            extrapolation_window = window
        for i in range(iterations):
            self._smooth(
                axis='y',
                window=window,
                extrapolation_window=extrapolation_window)

    def smooth_x(self, window=5, extrapolation_window=None, iterations=1):
        """Smooth the x-axis data in place using a running-average convolution.

        The data is convolved with a uniform block of ones whose length is
        ``window``. A larger window acts like a lower-frequency pole, producing
        more aggressive smoothing at the cost of more distortion. The dataset
        is linearly extrapolated at both ends so the convolution does not run
        out of data at the boundaries.

        Multiple iterations cascade the filter, approximating a brick-wall
        response. **Warning:** high iteration counts cause significant phase
        shift along the independent axis. Always compare smoothed data against
        the original to check for distortion.

        Args:
            window: Size of the convolution kernel (number of points). Odd
                values are preferred; even values are automatically incremented
                by one to maintain a centered kernel.
            extrapolation_window: Number of end points used to fit the linear
                extrapolation beyond each edge. Defaults to ``window``. A
                smaller value can reduce edge distortion.
            iterations: Number of times to repeat the smoothing pass. Each
                additional pass adds another pole to the effective filter.
        """
        if extrapolation_window is None:
            extrapolation_window = window
        for i in range(iterations):
            self._smooth(
                axis='x',
                window=window,
                extrapolation_window=extrapolation_window)

    def box_filter(self, f3db, order, sampling_interval=None,
                   extrapolation_window=None):
        """Apply a box filter to the y-axis data with a specified -3 dB frequency and order.

        Computes the convolution window size N from the desired -3 dB cutoff
        frequency and the sampling interval, then delegates to ``smooth_y``.
        If the sampling interval is not provided explicitly, it is inferred
        from the spacing between the first two x data points (rounded to the
        nearest 10 ps).

        Args:
            f3db: Desired -3 dB cutoff frequency in Hz.
            order: Filter order (number of cascaded smoothing passes).
            sampling_interval: Time between consecutive samples. If None, it
                is estimated from the first two x values.
            extrapolation_window: Number of end points used for linear
                extrapolation at dataset edges. Passed through to ``smooth_y``.
        """
        if sampling_interval is None:
            # round to 10ps - scope at 4GSa/s is 250ps.  5GSa/s is 200ps.
            time_step = round(self[1][0] - self[0][0], 11)
        else:
            time_step = sampling_interval
        # calculate sampling frequency in radians
        w_3db = 2 * math.pi * f3db * time_step
        k = math.sqrt(2)**(1 / order)
        j = (w_3db / 2)**2
        radical = math.sqrt(1 - (6 * (k - 1) + j) / (5 * k))
        N = round(math.sqrt(10 / j * (1 - radical)))  # Calculate N
        N = N + 1 if N % 2 == 0 else N
        self.smooth_y(
            window=N,
            extrapolation_window=extrapolation_window,
            iterations=order)

    def x_extents(self):
        """Compute the minimum, maximum, and range of the x-axis data.

        Returns:
            Dict with keys ``"min"``, ``"max"``, and ``"diff"`` (max − min).
        """
        xdata = list(zip(*self))[0]
        return {"min": min(xdata), "max": max(
            xdata), "diff": max(xdata) - min(xdata)}

    def y_extents(self):
        """Compute the minimum, maximum, and range of the y-axis data.

        Returns:
            Dict with keys ``"min"``, ``"max"``, and ``"diff"`` (max − min).
        """
        ydata = list(zip(*self))[1]
        return {"min": min(ydata), "max": max(
            ydata), "diff": max(ydata) - min(ydata)}

    def interpolated_y_value(self, xvalue):
        """Return the linearly interpolated y value at the given x position.

        Uses ``numpy.interp`` to interpolate between existing data points.
        Values outside the x range are clamped to the nearest endpoint's y value.

        Args:
            xvalue: The x coordinate (or array of coordinates) at which to
                interpolate.

        Returns:
            Interpolated y value (float), or an ndarray if xvalue is array-like.
        """
        return numpy.interp(xvalue, list(zip(*self))[0], list(zip(*self))[1])
