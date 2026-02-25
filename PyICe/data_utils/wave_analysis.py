from PyICe.lab_utils.banners import print_banner
from statsmodels.tsa.stattools import adfuller
from operator import itemgetter
from scipy import stats
import numpy

warned_1_already = False
warned_2_already = False

class waveform(object):
    # @profile
    def __init__(self, data, trigger_sigma=10, trigger_level=None, leader_size=0.099, debug=False, stationarity_check=False):
        MAX_POINTS              = 10000
        LEADER_SIZE             = leader_size
        MAX_NONSTATIONARITY     = 1e-4
        global warned_2_already

        #Figure out transposition/zip status.
        # assume (x,y) paired unless proven otherwise for legacy compatibility
        # This is pretty hacky, but promises trememdous speed improvement when passing data straight from sqlite and numpy to here, compared with list(zip) operations to meet the legacy calling argument format, but are then immediately undone.
        def _zip(data):
            global warned_1_already
            # Let the nagging begin
            if not warned_1_already:
                print_banner("WARNING: The waveform class instantiated with (x,y) pair data (legacy format) N x 2.", "This is both expensive to zip together from independent database columns", "and expensive to unzip on the other side of the function call, for no net benefit.", "Consider sending data in instead as (x_data, y_data) 2 x N column tuple.", length=160)
                warned_1_already = True
            self.data               = data
            self.xdata,self.ydata   = list(zip(*data)) #TODO numpy array, not list!
        try:
            if len(data) == 2 and len(data[0]) > 2:
                #it's in columns
                self.data = zip(data) #list? necessary? Trying not to do too much work here.
                self.xdata = data[0] #This should be faster!
                self.ydata = data[1]
            else:
                # assume it's in pairs
                # there's one corner case here, if the waveform data is exactly 2x2.
                _zip(data)
        except TypeError as e:
            #zip objects (and maybe other generators) have no len
            _zip(data)
        # and then there was more nagging
        if type(self.xdata) != numpy.ndarray or type(self.ydata) != numpy.ndarray:
            if not warned_2_already:
                print_banner(f"WARNING: The waveform class initialized with non-numpy arrays ({type(self.xdata)},{type(self.ydata)}).", "They will be converted here to enable more computationally efficient internal methods, at some expense.", "Consider whether this data can travel from its source (SQLite?) to here without needing to become a Python list at any point in its journey.", "Contact pyice-developers@analog.com for help in converting column types and/or data.", "TODO box_filter, etc.", length=160)
                self.xdata = numpy.array(self.xdata)
                self.ydata = numpy.array(self.ydata)
                warned_2_already=True

        self.index_size         = int(len(self.xdata)*LEADER_SIZE)  # Leadin and leadout.
        leadin                  = self.ydata[:self.index_size]      # Rules require stationarity in and out...
        leadout                 = self.ydata[-self.index_size:]     # for at least 10% of the record size.
        self.warning            = 0

        if stationarity_check:
            self.stationarity_in    = 1-adfuller(leadin)[1]
            self.stationarity_out   = 1-adfuller(leadout)[1]
        
            if self.stationarity_in < 1 - MAX_NONSTATIONARITY:
                print_banner(f"Waveform Analyser ** WARNING **: Waveform is not stationary leading in, stationarity: {self.stationarity_in:0.5e}")
                self.warning = -1
            if self.stationarity_out < 1 - MAX_NONSTATIONARITY:
                print_banner(f"Waveform Analyser ** WARNING **: Waveform is not stationary leading out, stationarity: {self.stationarity_out:0.5e}")
                self.warning = -1
        else:
            self.stationarity_in    = None
            self.stationarity_out   = None
        self._average_in         = numpy.average(leadin)
        self._average_out        = numpy.average(leadout)
        self.stdev_in           = numpy.std(leadin)
        self.stdev_out          = numpy.std(leadout)
        self._trigger_sigma      = trigger_sigma
        self._trigger_level      = trigger_level
        self.index_10 = 0

        # Bokeh debug plots
        from bokeh.plotting import figure #, output_file, show
        self.plt = figure(title="Waveform Analyzer Data", width=300, height=300)
        self.debug = debug
        if self.debug:
            self._plot()
            self.dump_data()
            self.plot()

        # self.trigger()
        # if self._trigger_polarity == 0:
            # raise ValueError("\nWaveform Analyser: No discernable trigger found within data record.\n")
    def dump_data(self, filename='waveform_analyzer_debug_data.pkl'):
        import pickle
        with open(filename, 'ab') as f:
            pickle.dump(self.data, f)
            f.close()
    def _plot(self):
        from bokeh.models import Label
        # Show data that waveform analyzer sees (possibly hidden inside SCITL loop)
        self.plt.line(x=self.xdata, y=self.ydata)
        data_txt = ''
        for param_name in ['_average_in', '_average_out', 'stdev_in', 'stdev_out', '_trigger_sigma', '_trigger_level', 'stationarity_in' , 'stationarity_out']:
            param_value = getattr(self, param_name)
            data_txt = f'{data_txt}\n{param_name}: {param_value}'
        if self.index_10:
            data_txt = f'{data_txt}\n10%_point: [{self.xdata[self.index_10]},{round(self.ydata[self.index_10],3)}]'
            data_txt += f'\n90%_point: [{self.xdata[self.index_90]},{round(self.ydata[self.index_90],3)}]'
        data_label = Label( x=300,
                            y=70,
                            x_units='screen',
                            y_units='screen',
                            text=data_txt,
                            border_line_color='black',
                            border_line_alpha=1.0,
                            background_fill_color='white',
                            background_fill_alpha=1.0
                           )
        self.plt.add_layout(data_label)
    def plot(self):
            from bokeh.plotting import show
            show(self.plt)
    def trigger(self):
        for index,value in enumerate(self.ydata):
            if value > self._average_in + (self._trigger_sigma * self.stdev_in if self._trigger_level is None else self._trigger_level):
                self._trigger_polarity   = 1
                self._trigger_index      = index
                self._trigger_value      = value
                self.trigger_time       = self.xdata[index]
                from bokeh.models import Span
                self.plt.add_layout(Span(location=self.xdata[index],
                                         dimension='height',
                                         line_color='red',
                                         line_dash='dashed',
                                         line_width=3,
                                        )
                                   )
                return
            if value < self._average_in - (self._trigger_sigma * self.stdev_in if self._trigger_level is None else self._trigger_level):
                self._trigger_polarity   = -1
                self._trigger_index      = index
                self._trigger_value      = value
                self.trigger_time       = self.xdata[index]
                from bokeh.models import Span
                self.plt.add_layout(Span(location=self.xdata[index],
                                         dimension='height',
                                         line_color='red',
                                         line_dash='dashed',
                                         line_width=3,
                                        )
                                   )
                return
        self._trigger_polarity   = 0
        self._trigger_index      = -1
        self._trigger_value      = 0
        self.trigger_time        = None

    def trigger_10_90(self):
        ## This method determines if the waveform is a rising edge or a falling edge. Then 
        ## it finds the time (xdata), index and the value(ydata) when the waveform is at 10% of the average_out for a rising edge
        ## and at 90% of the average in for a falling edge.
        from bokeh.models import Span
        if self._average_out > self._average_in:
            self.trigger_10_90_polarity   = 1
        elif self._average_out < self._average_in:
            self.trigger_10_90_polarity   = -1
        else:
            self.trigger_10_90_polarity   = 0
        for index,value in enumerate(self.ydata):
            if self.trigger_10_90_polarity   ==  1 and value > 0.1*(self._average_out-self._average_in)+self._average_in:    # Use average_out b'cos that's what is servoed for a load step
                self.trigger_10_90_index      = index
                self.trigger_10_90_value      = value
                self.trigger_10_90_time       = self.xdata[index]
                self.plt.add_layout(Span(location   = self.xdata[index],
                                         dimension  = 'height',
                                         line_color = 'red',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )

                return
            elif self.trigger_10_90_polarity == -1 and value < 0.9*(self._average_in-self._average_out)+self._average_out:     # Use average_in b'cos that's what is servoed for a load release
                self.trigger_10_90_index      = index
                self.trigger_10_90_value      = value
                self.trigger_10_90_time       = self.xdata[index]
                self.plt.add_layout(Span(location   = self.xdata[index],
                                         dimension  = 'height',
                                         line_color = 'red',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                return
        self.trigger_10_90_polarity   = 0
        self.trigger_10_90_index      = -1
        self.trigger_10_90_value      = 0

    def settling_time(self, low_limit, high_limit):
        self.trigger()
        if self._trigger_polarity == 0:
            raise ValueError("\nWaveform Analyser: No discernable trigger found within data record.\n")
        xreverse = list(self.xdata)
        yreverse = list(self.ydata)
        xreverse.reverse()
        yreverse.reverse()
        for idx, value in enumerate(yreverse):
            if value >= high_limit or value <= low_limit:
                if idx == 0:
                    print_banner("Waveform Analyser: Warning, The waveform did not settle to the tolerance requested...", f"({low_limit}, {high_limit})")
                    return -1
                return xreverse[idx] - self.xdata[self._trigger_index]
        print_banner("Waveform Analyser: Warning, waveform was never outside the tolerance region requested...", f"({low_limit}, {high_limit})")
        return -1

    def settling_time_from_max_deviation(self, limit, deviation):
        ## This method calculates the time difference between the max deviation point (positive or negative) and the last time the waveform iss outside the limit
        if deviation is None:
            raise ValueError("\ndeviation should be 'pos' or 'neg'\n")
        elif deviation.lower() == 'neg':
            start_time = min(self.data,key=itemgetter(1))[0]
        elif deviation.lower() == 'pos':
            start_time = max(self.data,key=itemgetter(1))[0]
        else:
            raise ValueError("\ndeviation should be 'pos' or 'neg'\n")
        xreverse = list(self.xdata)
        yreverse = list(self.ydata)
        xreverse.reverse()
        yreverse.reverse()
        from bokeh.models import Span
        for idx, value in enumerate(yreverse):
            if value-self._average_in >= abs(limit) or value-self._average_in <= -1*abs(limit):
                if idx == 0:
                    print_banner("Waveform Analyser: Warning, The waveform did not settle to the tolerance requested...", f"{limit}")
                    return -1
                self.plt.add_layout(Span(location   = abs(limit)+self._average_in,
                                         dimension  = 'width',
                                         line_color = 'red',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = -1*abs(limit)+self._average_in,
                                         dimension  = 'width',
                                         line_color = 'red',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = start_time,
                                         dimension  = 'height',
                                         line_color = 'red',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = xreverse[idx],
                                         dimension  = 'height',
                                         line_color = 'red',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                return xreverse[idx] - start_time
        print_banner("Waveform Analyser: Warning, The waveform was never outside the tolerance region requested...", f"{limit}")
        return -1

    def settling_time_outside_limit(self, limit):
        ## This method calculates the time difference between the first time the waveform is outside limit to the last time the waveform is outside the limit.
        xreverse = list(self.xdata)
        yreverse = list(self.ydata)
        xreverse.reverse()
        yreverse.reverse()
        from bokeh.models import Span
        for idx, value in enumerate(self.ydata):
            if value-self._average_in >= abs(limit) or value-self._average_in <= -1*abs(limit):
                if idx == len(self.ydata)-1:
                    print_banner("Waveform Analyser: Warning, The waveform was always outside the tolerance requested...", f"{limit}")
                    return -1
                start_index = idx
                break
        for idx, value in enumerate(yreverse):
            if value-self._average_in >= abs(limit) or value-self._average_in <= -1*abs(limit):
                if idx == start_index:
                    print_banner("Waveform Analyser: Warning, The waveform did not settle to the tolerance requested...", f"{limit}")
                    return -1
                self.plt.add_layout(Span(location   = abs(limit)+self._average_in,
                                         dimension  = 'width',
                                         line_color = 'orange',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = -1*abs(limit)+self._average_in,
                                         dimension  = 'width',
                                         line_color = 'orange',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[start_index],
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = xreverse[idx],
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                return xreverse[idx]-self.xdata[start_index]
        print_banner("Waveform Analyser: Warning, The waveform was never outside the tolerance region requested...", f"{limit}")
        return -1

    def undershoot(self):
        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self._average_in,
                                 dimension  = 'width',
                                 line_color = 'pink',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        self.plt.add_layout(Span(location   = min(self.ydata),
                                 dimension  = 'width',
                                 line_color = 'pink',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        return min(self.ydata) - self._average_in

    def overshoot(self):
        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self._average_in,
                                 dimension  = 'width',
                                 line_color = 'purple',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        self.plt.add_layout(Span(location   = max(self.ydata),
                                 dimension  = 'width',
                                 line_color = 'purple',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        return max(self.ydata) - self._average_in

    def slew_rate(self):
        self.trigger_10_90()
        if self.trigger_10_90_polarity == 0:
            raise ValueError("\nWaveform Analyser: No discernable 10%/90% trigger found within data record to measure the slew rate.\n")
        if self.trigger_10_90_polarity == 1:
            rampend_index = next(idx for (idx,data) in enumerate(self.ydata) if data > 0.9*(self._average_out-self._average_in)+self._average_in)
        elif self.trigger_10_90_polarity == -1:
            rampend_index = next(idx for (idx,data) in enumerate(self.ydata) if data < 0.1*(self._average_in-self._average_out)+self._average_out)
        else:
            raise ValueError("\nWaveform Analyser: Reached unreachable code, contact Steve Martin.")
        self.rampstart_time     = self.xdata[self.trigger_10_90_index]
        self.rampend_time       = self.xdata[rampend_index]
        self.rampstart_value    = self.trigger_10_90_value
        self.rampend_value      = self.ydata[rampend_index]
        try:
            ramp                = stats.linregress(self.xdata[self.trigger_10_90_index:rampend_index], self.ydata[self.trigger_10_90_index:rampend_index])
        except Exception as e:
            self.plot()
            raise
        self.ramp_slope         = ramp.slope
        self.ramp_intercept     = ramp.intercept
        self.ramp_rvalue        = ramp.rvalue
        
        from bokeh.models import Span
        from bokeh.models import Label

        data_txt   = f'ramp slope={1e-6*self.ramp_slope}A/us'
        data_label = Label(x=300,
                           y=200,
                           x_units='screen',
                           y_units='screen',
                           text=data_txt,
                           border_line_color='black',
                           border_line_alpha=1.0,
                           background_fill_color='white',
                           background_fill_alpha=1.0
                           )
        self.plt.line(x=self.xdata[self.trigger_10_90_index:rampend_index], y=self.ydata[self.trigger_10_90_index:rampend_index], 
                      line_color='red', line_dash=[50,50], line_width=1
                     )
        self.plt.add_layout(data_label)
        self.plt.add_layout(Span(location   = self.xdata[rampend_index],
                                 dimension  = 'height',
                                 line_color = 'red',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        return self.ramp_slope

    def rise_time(self, low_percentage=0.1, high_percentage=0.9):
        from bokeh.models import Span
        from bokeh.models import Label
        amplitude = self._average_out - self._average_in
        for idx, value in enumerate(self.ydata):
            if value > self._average_in + low_percentage * amplitude:
                self.index_10 = idx
                break
        hline1 = Span(location=value, dimension='width',line_color='red', line_dash='dashed', line_width=1)
        vline1 = Span(location = self.xdata[self.index_10], dimension  = 'height',line_color = 'red', line_dash  = 'dashed', line_width = 1)
        for idx, value in enumerate(self.ydata):
            if value > self._average_in + high_percentage * amplitude:
                self.index_90 = idx
                break
        hline2 = Span(location=value, dimension='width',line_color='red', line_dash='dashed', line_width=1)
        vline2 = Span(location   = self.xdata[self.index_90], dimension  = 'height',line_color = 'red', line_dash  = 'dashed', line_width = 1)
        if self.debug:
            self.plt.renderers.extend([vline1, hline1,vline2,hline2])
            self._plot()
            self.plot()
        return self.xdata[self.index_90] - self.xdata[self.index_10]
        
    def fall_time(self, low_percentage=0.1, high_percentage=0.9):
        from bokeh.models import Span
        amplitude = self._average_in - self._average_out
        for idx, value in enumerate(self.ydata):
            if value < self._average_out + low_percentage * amplitude:
                self.index_10 = idx
                break
        hline1 = Span(location=value, dimension='width',line_color='red', line_dash='dashed', line_width=1)
        vline1 = Span(location = self.xdata[self.index_10], dimension  = 'height',line_color = 'red', line_dash  = 'dashed', line_width = 1)
        for idx, value in enumerate(self.ydata):
            if value < self._average_out + high_percentage * amplitude:
                self.index_90 = idx
                break
        hline2 = Span(location=value, dimension='width',line_color='red', line_dash='dashed', line_width=1)
        vline2 = Span(location   = self.xdata[self.index_90], dimension  = 'height',line_color = 'red', line_dash  = 'dashed', line_width = 1)
        if self.debug:
            self.plt.renderers.extend([vline1, hline1,vline2,hline2])
            self._plot()
            self.plot()
        return self.xdata[self.index_10] - self.xdata[self.index_90]

    def average_in(self):
        return self._average_in

    def average_out(self):
        return self._average_out

    def trigger_polarity(self):
        return self._trigger_polarity

    def trigger_value(self):
        return self._trigger_value

    def trigger_index(self):
        return self._trigger_index

    def trigger_sigma(self):
        return self._trigger_sigma

    def trigger_level(self):
        return self._trigger_level

    def amplitude(self):
        return max(self.ydata) - min(self.ydata)

    def find_grt_than_or_equal_to(self, vth, start_index, stop_index, increment):
        for i in range(start_index, stop_index+increment, increment):
            if self.ydata[i] >= vth:
                return i
        return -1 

    def find_less_than_or_equal_to(self, vth, start_index, stop_index, increment):
        for i in range(start_index, stop_index+increment, increment):
            if self.ydata[i] <= vth:
                return i
        return -1

    def find_first_rising_edge(self, vhigh, vlow=0, lvl=0.5, start_index=0):
    ### This method finds the first time when the waveform is at or above 0.5 or lvl of [vhigh-vlow] and returns the corresponding index.
    ### If it did not find the point, it returns -1.
    ### Input arg lvl should specified as a ratio of [vhigh-vlow], The default is 0.5 of [vhigh-vlow]
    ### Optional start_index sets the starting point for the search and must be within the range of waveform indexes
        if vhigh is None:
            raise ValueError("\nWaveform Analyser: input args vhigh must be specified.\n")
        elif vlow >=  vhigh:
            raise ValueError("\nWaveform Analyser: input arg vlow has to be less than vhigh.\n")
        elif start_index < 0 or start_index > len(self.ydata)-1:
            raise ValueError(f"\nWaveform Analyser: start_index is outside the range of the waveform data. Enter a value between 0 and {len(self.ydata)-1}\n")
        vth = vlow + lvl*(vhigh-vlow)
        if self.ydata[0] > vth:
            start_index = self.find_less_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
            if start_index == -1:
                return -1
            index       = self.find_grt_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
        else:
            index       = self.find_grt_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
        return index

    def find_first_falling_edge(self, vhigh, vlow=0, lvl=0.5, start_index=0):
    ### This method finds the first time when the waveform is at or 0.5 or lvl of [vhigh-vlow] and returns the corresponding index.
    ### If it did not find the point, it returns -1.
    ### Input arg lvl should specified as a ratio of [vhigh-vlow], The default is 0.5 of [vhigh-vlow]
    ### Optional start_index sets the starting point for the search and must be within the range of waveform indexes
        if vhigh is None:
            raise ValueError("\nWaveform Analyser: input args vhigh must be specified.\n")
        elif vlow >=  vhigh:
            raise ValueError("\nWaveform Analyser: input arg vlow has to be less than vhigh.\n")
        elif start_index < 0 or start_index > len(self.ydata)-1:
            raise ValueError(f"\nWaveform Analyser: start_index is outside the range of the waveform data. Enter a value between 0 and {len(self.ydata)-1}\n")
        vth = vlow + lvl*(vhigh-vlow)
        if self.ydata[0] < vth:
            start_index = self.find_grt_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
            if start_index == -1:
                return -1
            index       = self.find_less_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
        else:
            index       = self.find_less_than_or_equal_to(vth=vth, start_index=start_index, stop_index=len(self.ydata)-1, increment=1)
        return index

    def sw_rise_time(self, lo_lvl, hi_lvl, vhigh, vlow=0):
    ### This method calculates the rise time of the first rising edge of a waveform (e.g. SW node). 
    ### lo_lvl = Low threshold as a ratio of the [vhigh-vlow] to find the start time of rise time
    ### hi_lvl = High threshold as a ratio of the [vhigh-vlow] to find the stop time of rise time
    ### If successful, returns (real_lo_lvl, real_hi_lvl, rise time). If unable to find the 50%, lo_lvl or hi_lvl returns (-1,-1,-1)
        if lo_lvl is None or hi_lvl is None:
            raise ValueError("\nWaveform Analyser: input args lo_lvl and hi_lvl must be specified as a ratio of the amplitude (vhigh-vlow).\n")
        elif lo_lvl >=  hi_lvl:
            raise ValueError("\nWaveform Analyser: input arg lo_lvl has to be less than hi_lvl.\n")
        amplitude = vhigh - vlow
        
        index_50    = self.find_first_rising_edge(vhigh=vhigh, vlow=vlow, lvl=0.5)
        if index_50 == -1:
            print_banner("Waveform Analyser: The 50% level of a rising edge was not found in the data record")
            return (-1,-1,-1)
        real_50_lvl = round((self.ydata[index_50]-vlow)/amplitude,4)
        
        vth_lo = vlow + lo_lvl*amplitude
        if lo_lvl >= real_50_lvl:
            ### When lo_lvl is less than 50_lvl, the index returned is when the signal drops below the lo_lvl. 
            ### To be consistent with when lo_lvl< 50%, decreased the index by one 
            index_lo = self.find_grt_than_or_equal_to(vth=vth_lo, start_index=index_50, stop_index=len(self.ydata)-1, increment=1) - 1
        else:
            index_lo = self.find_less_than_or_equal_to(vth=vth_lo, start_index=index_50, stop_index=0, increment=-1)
        if index_lo == -1 or index_lo == -2:
            print_banner("Waveform Analyser", f"The {round(lo_lvl*100,1)}% level of the waveform was not found in the data record")
            return (-1,-1,-1)
        
        vth_hi = vlow + hi_lvl*amplitude
        if hi_lvl >= real_50_lvl:
            index_hi = self.find_grt_than_or_equal_to(vth=vth_hi, start_index=index_50, stop_index=len(self.ydata)-1, increment=1)
        else:
            ### When hi_lvl is greater than 50_lvl, the index returned is when the signal is above the hi_lvl. 
            ### To be consistent with when hi_lvl>50%, increased the index by one 
            index_hi = self.find_less_than_or_equal_to(vth=vth_hi, start_index=index_50, stop_index=0, increment=-1) + 1
        if index_hi == -1 or index_hi == 0:
            print_banner("Waveform Analyser", f"The {round(hi_lvl*100,1)}% level of the waveform was not found in the data record")
            return (-1,-1,-1)

        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self.xdata[index_lo],
                                 dimension  = 'height',
                                 line_color = 'red',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        self.plt.add_layout(Span(location   = self.xdata[index_hi],
                                 dimension  = 'height',
                                 line_color = 'red',
                                 line_dash  = 'dotted',
                                 line_width = 2,
                                )
                           )
        return (round((self.ydata[index_lo]-vlow)/amplitude,4), round((self.ydata[index_hi]-vlow)/amplitude,4), self.xdata[index_hi] - self.xdata[index_lo])

    def sw_fall_time(self, lo_lvl, hi_lvl, vhigh, vlow=0):
    ### This method calculates the fall time of the first falling edge of a waveform (e.g. SW node).
    ### hi_lvl = High threshold as a ratio of the [vhigh-vlow] to find the start time of fall time
    ### lo_lvl = Low threshold as a ratio of the [vhigh-vlow] to find the stop time of fall time
    ### If successful, returns (real_lo_lvl, real_hi_lvl, fall time). If unable to find the 50%, lo_lvl or hi_lvl returns (-1,-1,-1) 
        if lo_lvl is None or hi_lvl is None:
            raise ValueError("\nWaveform Analyser: input args lo_lvl and hi_lvl must be specified as a ratio of the amplitude (vhigh-vlow).\n")
        elif lo_lvl >=  hi_lvl:
            raise ValueError("\nWaveform Analyser: input arg lo_lvl has to be less than hi_lvl.\n")
        amplitude = vhigh - vlow
        
        index_50    = self.find_first_falling_edge(vhigh=vhigh, vlow=vlow, lvl=0.5)
        if index_50 == -1:
            print_banner("Waveform Analyser", "The 50% level of a falling  edge is not found in the data record")
            return (-1,-1,-1)
        real_50_lvl = round((self.ydata[index_50]-vlow)/amplitude,4)
        
        vth_lo = vlow + lo_lvl*amplitude
        if lo_lvl <= real_50_lvl:
            index_lo = self.find_less_than_or_equal_to(vth=vth_lo, start_index=index_50, stop_index=len(self.ydata)-1, increment=1)
        else:
            ### When lo_lvl is less than 50_lvl, the index returned is when the signal drops below the lo_lvl. 
            ### To be consistent with when lo_lvl< 50%, increased the index by one 
            index_lo = self.find_grt_than_or_equal_to(vth=vth_lo, start_index=index_50, stop_index=0, increment=-1) + 1
        if index_lo == -1 or index_lo == 0:
            print_banner("Waveform Analyser", f"The {round(lo_lvl*100,1)}% level of the waveform was not found in the data record")
            return (-1,-1,-1)
        
        vth_hi = vlow + hi_lvl*amplitude
        if hi_lvl <= real_50_lvl:
            ### When hi_lvl is greater than 50_lvl, the index returned is when the signal is above the hi_lvl. 
            ### To be consistent with when hi_lvl>50%, decreased the index by one 
            index_hi = self.find_less_than_or_equal_to(vth=vth_hi, start_index=index_50, stop_index=len(self.ydata)-1, increment=1) - 1
        else:
            index_hi = self.find_grt_than_or_equal_to(vth=vth_hi, start_index=index_50, stop_index=0, increment=-1)
        if index_hi == -1 or index_hi == -2:
            print_banner("Waveform Analyser", f"The {round(hi_lvl*100,1)}% level of the waveform was not found in the data record")
            return (-1,-1,-1)

        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self.xdata[index_lo],
                                 dimension  ='height',
                                 line_color ='blue',
                                 line_dash  ='dashed',
                                 line_width = 2,
                                )
                           )
        self.plt.add_layout(Span(location   = self.xdata[index_hi],
                                 dimension  ='height',
                                 line_color ='blue',
                                 line_dash  ='dotted',
                                 line_width = 2,
                                )
                           )
        return (round((self.ydata[index_lo]-vlow)/amplitude,4), round((self.ydata[index_hi]-vlow)/amplitude,4), self.xdata[index_lo] - self.xdata[index_hi])

    def sw_nol_rise(self, vth, vhigh, vlow=0):
        ### This method calculates two non-overlap (nol) times of the first rising edge of a waveform (e.g. SW node). 
        ### nol_low_side  = non-overlap time on the low side. vsw < vlow-vth
        ### nol_high_side = non-overlap time on the high side. vsw > vhigh+vth
        ### vth           = see the definitions for nol_low_side and nol_high_side
        ### If successful, returns (nol_low_side, nol_high_side). If not, returns (-1,-1)
        from bokeh.models import Span
        if vth is None:
            raise ValueError("\nWaveform Analyser: input arg vth has to be a positive value. nol_low_side = time duration for which vsw<vlow-vth. nol_high_side = time duration for which vsw>vhigh+vth.\n")
        elif vth < 0.0:
            raise ValueError("\nWaveform Analyser: input arg vth has to be a positive value. nol_low_side = time duration for which vsw<vlow-vth. nol_high_side = time duration for which vsw>vhigh+vth.\n")
        
        index_50    = self.find_first_rising_edge(vhigh=vhigh, vlow=vlow, lvl=0.5)
        if index_50 == -1:
            print_banner("Waveform Analyser", "The 50% level of a rising edge is not found in the data record")
            return (-1,-1)
        
        nol_low_side_start_index = self.find_less_than_or_equal_to(vth=vlow-vth, start_index=index_50, stop_index=0, increment=-1)
        if nol_low_side_start_index == -1:
            nol_low_side = 0
        else:
            nol_low_side_stop_index = self.find_grt_than_or_equal_to(vth=vlow-vth, start_index=nol_low_side_start_index, stop_index=0, increment=-1)
            if nol_low_side_stop_index == -1:
                print_banner("Waveform Analyser", "The waveform was below vlow - vth from the beginning of the scope shot to the first rising edge")
                nol_low_side = -1
            else:
                nol_low_side = self.xdata[nol_low_side_start_index] - self.xdata[nol_low_side_stop_index]
                self.plt.add_layout(Span(location   = vlow-vth,
                                         dimension  = 'width',
                                         line_color = 'orange',
                                         line_dash  = 'dotdash',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_low_side_start_index] ,
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_low_side_stop_index],
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
        
        nol_high_side_start_index = self.find_grt_than_or_equal_to(vth=vhigh+vth, start_index=index_50, stop_index=len(self.ydata)-1, increment=1)
        if nol_high_side_start_index == -1:
            nol_high_side = 0
        else:
            nol_high_side_stop_index = self.find_less_than_or_equal_to(vth=vhigh+vth, start_index=nol_high_side_start_index, stop_index=len(self.ydata)-1, increment=1)
            if nol_high_side_stop_index == -1:
                print_banner("Waveform Analyser", "The waveform was above vhigh +vth at the end of the scope shot")
                nol_high_side = -1
            else:
                nol_high_side = self.xdata[nol_high_side_stop_index] - self.xdata[nol_high_side_start_index]
                self.plt.add_layout(Span(location   = vhigh+vth,
                                         dimension  = 'width',
                                         line_color = 'green',
                                         line_dash  = 'dotdash',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_high_side_start_index],
                                         dimension  = 'height',
                                         line_color = 'green',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_high_side_stop_index],
                                         dimension  = 'height',
                                         line_color = 'green',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
        return (nol_low_side, nol_high_side)

    def sw_nol_fall(self, vth, vhigh, vlow=0):
        ### This method calculates two non-overlap (nol) times of the first falling edge of a waveform (e.g. SW node). 
        ### nol_low_side  = non-overlap time on the low side. vsw < vlow-vth
        ### nol_high_side = non-overlap time on the high side. vsw > vhigh+vth
        ### vth           = see the definitions for nol_low_side and nol_high_side
        ### If successful, returns (nol_low_side, nol_high_side). If not, returns (-1,-1)
        from bokeh.models import Span
        if vth is None:
            raise ValueError("\nWaveform Analyser: input arg vth has to be a positive value. nol_low_side = time duration for which vsw<vlow-vth. nol_high_side = time duration for which vsw>vhigh+vth.\n")
        elif vth < 0.0:
            raise ValueError("\nWaveform Analyser: input arg vth has to be a positive value. nol_low_side = time duration for which vsw<vlow-vth. nol_high_side = time duration for which vsw>vhigh+vth.\n")
        
        index_50    = self.find_first_falling_edge(vhigh=vhigh, vlow=vlow, lvl=0.5)
        if index_50 == -1:
            print_banner("Waveform Analyser", "The 50% level of a falling edge is not found in the data record")
            return (-1,-1)
        
        nol_low_side_start_index = self.find_less_than_or_equal_to(vth=vlow-vth, start_index=index_50, stop_index=len(self.ydata)-1, increment=1)
        if nol_low_side_start_index == -1:
            nol_low_side = 0
        else:
            nol_low_side_stop_index = self.find_grt_than_or_equal_to(vth=vlow-vth, start_index=nol_low_side_start_index, stop_index=len(self.ydata)-1, increment=1)
            if nol_low_side_stop_index == -1:
                print_banner("Waveform Analyser", "The waveform was below vlow - vth from the beginning of the scope shot to the first rising edge")
                nol_low_side = -1
            else:
                nol_low_side = self.xdata[nol_low_side_stop_index] - self.xdata[nol_low_side_start_index]
                self.plt.add_layout(Span(location   = vlow-vth,
                                         dimension  = 'width',
                                         line_color = 'orange',
                                         line_dash  = 'dotdash',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_low_side_start_index] ,
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_low_side_stop_index],
                                         dimension  = 'height',
                                         line_color = 'orange',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
        
        nol_high_side_start_index = self.find_grt_than_or_equal_to(vth=vhigh+vth, start_index=index_50, stop_index=0, increment=-1)
        if nol_high_side_start_index == -1:
            nol_high_side = 0
        else:
            nol_high_side_stop_index = self.find_less_than_or_equal_to(vth=vhigh+vth, start_index=nol_high_side_start_index, stop_index=0, increment=-1)
            if nol_high_side_stop_index == -1:
                print_banner("Waveform Analyser", "The waveform was above vhigh +vth at the end of the scope shot")
                nol_high_side = -1
            else:
                nol_high_side = self.xdata[nol_high_side_start_index] - self.xdata[nol_high_side_stop_index]
                self.plt.add_layout(Span(location   = vhigh+vth,
                                         dimension  = 'width',
                                         line_color = 'green',
                                         line_dash  = 'dotdash',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_high_side_start_index],
                                         dimension  = 'height',
                                         line_color = 'green',
                                         line_dash  = 'dashed',
                                         line_width = 2,
                                        )
                                   )
                self.plt.add_layout(Span(location   = self.xdata[nol_high_side_stop_index],
                                         dimension  = 'height',
                                         line_color = 'green',
                                         line_dash  = 'dotted',
                                         line_width = 2,
                                        )
                                   )
        return (nol_low_side, nol_high_side)
        
    def read_xdata(self, index):
        ### This method returns the xdata value for a given index.
        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self.xdata[index],
                                 dimension  = 'height',
                                 line_color = 'tomato',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        return self.xdata[index]
    
    def read_ydata(self, index):
        ### This method returns the ydata value for a given index.
        from bokeh.models import Span
        self.plt.add_layout(Span(location   = self.ydata[index],
                                 dimension  = 'width',
                                 line_color = 'teal',
                                 line_dash  = 'dashed',
                                 line_width = 2,
                                )
                           )
        return self.ydata[index]