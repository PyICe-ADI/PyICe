from PyICe.lab_core import *
import nidcpower


class ni_dcpower(instrument):
    def __init__(self):
        instrument.__init__(self, None)
        self.session = None
        self.set_current_limit = None
        self.set_current_limit_range = None
        self.current_limits = None
        self.current_ranges = None
        self.voltage_limits = None
        self.voltage_ranges = None

    def get_output_function(self, channel_number):
        return self.session.channels[channel_number].output_function.name

    def get_compliance(self, channel_num):
        return self.session.channels[channel_num].query_in_compliance()

    def initiate_channel(self, channel_number):
        self.session.channels[channel_number].initiate()

    def abort_channel(self, channel_number):
        self.session.channels[channel_number].abort()

    def output_enabled(self, channel_number, state):
        if state=='ON':
            self.session.channels[channel_number].output_enabled = True
        else:
            self.session.channels[channel_number].output_enabled = False

    def set_voltage_level(self, channel_number, value):
        self.session.channels[channel_number].voltage_level = value
        self.output_enabled(channel_number, 'ON')

    def get_voltage_level(self, channel_number):
        return float(self.session.channels[channel_number].voltage_level)

    def set_voltage_level_range(self, channel_number, value):
        if value == "AUTO":
            self.session.channels[channel_number].abort()
            self.session.channels[channel_number].voltage_level_autorange = True
            self.session.channels[channel_number].initiate()
        else:
            self.session.channels[channel_number].voltage_level_range = value

    def get_voltage_level_range(self, channel_number):
        return float(self.session.channels[channel_number].voltage_level_range)

    '''Single Point DC_VOLTAGE Source Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # '''
    def add_channel_output(self, channel_name, channel_number):
        new_channel = channel(f"{channel_name}_enable_output", write_function=lambda state: self.output_enabled(channel_number, state))
        new_channel.add_preset("ON", "")
        new_channel.add_preset("OFF", "")
        return self._add_channel(new_channel)

    '''Single Point DC_VOLTAGE Source Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # '''
    def add_channel_voltage_force(self, channel_name, channel_number):
        new_channel = channel(f"{channel_name}_vforce", write_function=lambda value: self.set_voltage_level(channel_number, value))
        new_channel._write_min = self.voltage_limits['min']
        new_channel._write_max = self.voltage_limits['max']
        new_channel._set_value(self.get_voltage_level(channel_number))
        return self._add_channel(new_channel)

    def add_channel_voltage_force_readback(self, channel_name, channel_number):
        def read_voltage_force_readback(channel_num):
            return float(self.session.channels[channel_num].voltage_level)

        new_channel = channel(channel_name + "_vforce_readback", read_function=lambda: read_voltage_force_readback(channel_number))
        return self._add_channel(new_channel)

    def add_channel_voltage_range(self, channel_name, channel_number):
        new_channel = channel(f"{channel_name}_vrange", write_function=lambda value: self.set_voltage_level_range(channel_number, value))
        new_channel.add_preset("AUTO", "")
        for voltage_range in self.voltage_ranges:
            new_channel.add_preset(voltage_range, "")
        new_channel._set_value(self.session.channels[channel_number].voltage_level_range)
        return self._add_channel(new_channel)

    def add_channel_voltage_range_readback(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_vrange_readback", read_function=lambda: self.get_voltage_level_range(channel_number))
        return self._add_channel(new_channel)

    def add_channel_current_limit(self, channel_name, channel_number):
        def write_current_limit(channel_num, value):
            if self.current_limits['min'] <= value <= self.current_limits['max']:
                if not self.set_current_limit_range:
                    self.set_current_limit = True
                    for icompl_range in self.current_ranges:
                        if self.current_ranges[icompl_range]['min'] <= value <= self.current_ranges[icompl_range]['max']:
                            self.session.channels[channel_num].abort()
                            self.session.channels[channel_num].current_limit = value
                            self.write_channel(channel_name + "_ilim_range", icompl_range)
                            break
                else:
                    self.session.channels[channel_num].current_limit = value
                    self.set_current_limit_range = False
            else:
                raise ValueError(f"\n\nCurrent limit must be between {self.current_limits['min']} and {self.current_limits['max']}.")

        new_channel = channel(f"{channel_name}_icompl", write_function=lambda value: write_current_limit(channel_number, value))
        new_channel._set_value(self.session.channels[channel_number].current_limit)
        return self._add_channel(new_channel)

    def add_channel_current_limit_readback(self, channel_name, channel_number):
        def read_current_limit(channel_num):
            return float(self.session.channels[channel_num].current_limit)

        new_channel = channel(channel_name + "_ilim_readback", read_function=lambda: read_current_limit(channel_number))
        return self._add_channel(new_channel)

    def add_channel_current_limit_range(self, channel_name, channel_number):
        def write_current_limit_range(channel_num, value):
            if value not in self.current_ranges:
                raise ValueError(f"\n\nCurrent range must be one of: {', '.join(self.current_ranges)}.")

            if self.set_current_limit_range:
                self.session.channels[channel_num].current_limit_range = value
                self.session.channels[channel_num].initiate()
                self.set_current_limit = False
            else:
                self.set_current_limit_range = True
                for icompl_range in self.current_ranges:
                    if self.current_ranges[icompl_range]['min'] <= value <= self.current_ranges[icompl_range]['max']:
                        self.session.channels[channel_num].abort()

                        self.write_channel(channel_name + "_icompl", self.current_ranges[value]['max'])
                        self.session.channels[channel_num].current_limit_range = icompl_range
                        self.session.channels[channel_num].initiate()
                        break

        new_channel = channel(f"{channel_name}_ilim_range", write_function=lambda value: write_current_limit_range(channel_number, value))
        for current_range in self.current_ranges:
            new_channel.add_preset(current_range, "")
        new_channel._set_value(self.session.channels[channel_number].current_limit_range)
        return self._add_channel(new_channel)

    def add_channel_current_limit_range_readback(self, channel_name, channel_number):
        def read_current_limit_range(channel_num):
            return float(self.session.channels[channel_num].current_limit_range)

        new_channel = channel(channel_name + "_ilim_range_readback", read_function=lambda: read_current_limit_range(channel_number))
        return self._add_channel(new_channel)

    '''Single Point DC_CURRENT Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # '''
    def add_channel_current_force(self, channel_name, channel_number):
        def write_current_force(channel_num, value):
            if self.get_output_function(channel_num) != "DC_CURRENT":
                self.session.channels[channel_num].output_enabled = False
                self.session.channels[channel_num].abort()
                self.session.channels[channel_num].source_mode = nidcpower.SourceMode.SINGLE_POINT
                self.session.channels[channel_num].output_function = nidcpower.OutputFunction.DC_CURRENT
                self.session.channels[channel_num].initiate()

            self.session.channels[channel_num].current_level = value
            self.write_channel(channel_name + "_enable_output", "ON")

        new_channel = channel(f"{channel_name}_iforce", write_function=lambda value: write_current_force(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_current_range(self, channel_name, channel_number):

        def write_current_range(channel_num, value):
            if value not in self.current_ranges:
                raise ValueError(f"\n\nCurrent range must be one of: {', '.join(self.current_ranges)}.")

            self.session.channels[channel_num].current_level_range = value

        new_channel = channel(f"{channel_name}_irange", write_function=lambda value: write_current_range(channel_number, value))
        for current_range in self.current_ranges:
            new_channel.add_preset(current_range, "")
        new_channel._set_value(self.session.channels[channel_number].current_limit_range)
        return self._add_channel(new_channel)

    def add_channel_voltage_limit(self, channel_name, channel_number):
        def write_voltage_limit(channel_num, value):
            self.session.channels[channel_num].voltage_limit = value

        new_channel = channel(f"{channel_name}_vcompl", write_function=lambda value: write_voltage_limit(channel_number, value))
        new_channel._set_value(self.session.channels[channel_number].voltage_limit)
        return self._add_channel(new_channel)

    def add_channel_voltage_limit_range(self, channel_name, channel_number):
        """ Set voltage_limit_autorange = False is when using this channel. """
        def write_voltage_limit_range(channel_num, value):
            self.session.channels[channel_num].voltage_limit_range = value

        new_channel = channel(f"{channel_name}_vcompl_range", write_function=lambda value: write_voltage_limit_range(channel_number, value))
        for voltage_range in self.voltage_ranges:
            new_channel.add_preset(voltage_range, "")
        new_channel._set_value(self.session.channels[channel_number].voltage_limit_range)
        return self._add_channel(new_channel)

    '''Single Point SENSE Channels # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # '''
    def add_channel_nplc(self, channel_name, channel_number):
        def write_nplc(channel_num, value):
            self.session.channels[channel_num].output_enabled = False
            self.session.channels[channel_num].abort()
            self.session.channels[channel_num].aperture_time_units = nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
            self.session.channels[channel_num].aperture_time = value
            self.session.channels[channel_num].initiate()

        new_channel = channel(f"{channel_name}_nplc", write_function=lambda value: write_nplc(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_sensing(self, channel_name, channel_number):
        def write_sensing(channel_num, value):
            self.session.channels[channel_num].output_enabled = False
            self.session.channels[channel_num].abort()
            if value == "REMOTE":
                self.session.channels[channel_num].sense = nidcpower.Sense.REMOTE
            else:
                self.session.channels[channel_num].sense = nidcpower.Sense.LOCAL
            self.session.channels[channel_num].initiate()

        new_channel = channel(f"{channel_name}_sensing", write_function=lambda value: write_sensing(channel_number, value))
        new_channel.add_preset("LOCAL", "")
        new_channel.add_preset("REMOTE", "")
        return self._add_channel(new_channel)

    def add_channel_current_sense(self, channel_name, channel_number):
        def read_current_sense(channel_num):
            return float(self.session.channels[channel_num].measure(nidcpower.MeasurementTypes.CURRENT))

        new_channel = channel(channel_name + "_isense", read_function= lambda: read_current_sense(channel_number))
        return self._add_channel(new_channel)

    def add_channel_voltage_sense(self, channel_name, channel_number):
        def read_voltage_sense(channel_num):
            return float(self.session.channels[channel_num].measure(nidcpower.MeasurementTypes.VOLTAGE))

        new_channel = channel(channel_name + "_vsense", read_function= lambda: read_voltage_sense(channel_number))
        return self._add_channel(new_channel)

    def add_channel_compliance_sense(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_compliance", read_function= lambda: self.get_compliance(channel_number))
        return self._add_channel(new_channel)

    def __del__(self):
        self.session.output_enabled = False
        self.session.abort()
        self.session.close()