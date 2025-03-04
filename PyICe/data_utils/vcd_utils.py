from vcdvcd import VCDVCD

from PyICe.data_utils.wave_analysis import waveform
from bokeh.plotting import figure, show #, output_file, show

import numpy

class vcd_reader():
    def __init__(self, file):
        self.vcd = VCDVCD(file)

    def get_signals(self):
        return self.vcd.get_signals()

    def get_raw_data(self,variable_name):
        if variable_name not in self.vcd.references_to_ids.keys():
            print(f'{variable_name} was not found in the vcd file provided. Available variables are {self.vcd.get_signals()}')
            return
        return self.vcd[variable_name].tv

    def process_data(self, variable_name, add_staircase_points=False):
        raw_data = self.get_raw_data(variable_name)
        xdata,ydata   = list(zip(*raw_data))
        real_ydata = []
        real_xdata = []
        if self.vcd[variable_name].var_type == 'wire' or self.vcd[variable_name].var_type == 'reg':
            for i, value in enumerate(ydata):
                if 'X' in value.upper():
                    real_ydata.append('X')
                elif 'Z' in value.upper():
                    real_ydata.append(None)
                else:
                    if add_staircase_points:
                        try:
                            real_ydata.append(last_y)
                            real_xdata.append(xdata[i]*self.vcd.get_timescale()['timescale'])
                        except UnboundLocalError as e:
                            pass
                    real_ydata.append(int(value,2))
                    last_y = int(value,2)
                real_xdata.append(xdata[i]*self.vcd.get_timescale()['timescale'])
        elif self.vcd[variable_name].var_type == 'real':
            for i, value in enumerate(ydata):
                if add_staircase_points:
                    try:
                        real_ydata.append(last_y)
                        real_xdata.append(xdata[i]*self.vcd.get_timescale()['timescale'])
                    except UnboundLocalError as e:
                        pass
                real_ydata.append(float(value))
                real_xdata.append(xdata[i]*self.vcd.get_timescale()['timescale'])
        else:
            raise Exception(f'Unexpected variable of type :{self.vcd[variable_name].var_type}')
        real_xdata = numpy.array(real_xdata)
        real_ydata = numpy.array(real_ydata)
        return [real_xdata,real_ydata]

    def get_data_as_waveform(self, variable_name):
        return waveform(data=self.process_data(variable_name, add_staircase_points=True))

    def get_value(self, variable_name, at_time):
        arrayed_data = self.process_data(variable_name)
        for i, time in enumerate(arrayed_data[0]):
            if time == at_time:
                print(f'Value Unknown. At time {at_time} {variable_name} changed from {arrayed_data[1][i-1]} to {arrayed_data[1][i]}')
                return None
            elif time > at_time:
                return arrayed_data[1][i-1]
        else:
            print(f'Requested time is beyond the last change in value of {variable_name}')
            return arrayed_data[1][-1]

    def plot_signal(self, variable_name):
        arrayed_data = self.process_data(variable_name)
        plt = figure(title=variable_name, frame_width=300, frame_height=300)
        plt.step(x=arrayed_data[0], y=arrayed_data[1], mode='after')
        show(plt)

    def plot_raw(self, variable_name, add_staircase_points=False):
        arrayed_data = self.process_data(variable_name=variable_name, add_staircase_points=add_staircase_points)
        plt = figure(title=variable_name, plot_width=300, plot_height=300)
        plt.line(x=arrayed_data[0], y=arrayed_data[1])
        show(plt)
 
    def plot_data(self, title, data):
        plt2 = figure(title=title, frame_width=300, frame_height=300)
        try:
            plt2.line(x=data[0], y=data[1])
        except TypeError as e:
            plt2.line(x=data.xdata, y=data.ydata)
        show(plt2)