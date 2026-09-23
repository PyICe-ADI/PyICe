""" Base for NI Programmable Power Supply instrument driver.

>>> from PyICe.lab_instruments.ni_pps import ni_dcsupply

"""
import nidcpower
from PyICe.lab_core import instrument, channel


class ni_dcsupply(instrument):  # pylint: disable=too-many-public-methods

    def __init__(self, instr_name, resource_name=None):
        instrument.__init__(self, instr_name)
        self.session = nidcpower.Session(resource_name)

    # GENERAL #
    def get_output_function(self, channel_number):
        return self.session.channels[channel_number].output_function.name

    def get_compliance(self, channel_number):
        return self.session.channels[channel_number].query_in_compliance()

    def initiate_channel(self, channel_number):
        self.session.channels[channel_number].initiate()
        setattr(self, f'is_CH{channel_number}_initiated', True)

    def abort_channel(self, channel_number):
        self.session.channels[channel_number].abort()

    def output_enabled(self, channel_number, state="ON"):
        if state == "ON":
            self.session.channels[channel_number].output_enabled = True
        else:
            self.session.channels[channel_number].output_enabled = False

    def get_output_status(self, channel_number):
        return self.session.channels[channel_number].output_enabled

    # VOLTAGE
    def enable_voltage_limit_auto_range(self, channel_number):
        if not self.get_voltage_limit_auto_range(channel_number):
            if getattr(self, f'is_CH{channel_number}_initiated'):
                self.abort_channel(channel_number)
                self.session.channels[channel_number].voltage_level_autorange = True
                self.initiate_channel(channel_number)

    def get_voltage_limit_auto_range(self, channel_number):
        return self.session.channels[channel_number].voltage_level_autorange

    def get_voltage_limit_range(self, channel_number):
        return self.session.channels[channel_number].voltage_limit_range

    def set_voltage_level(self, channel_number, value):
        if not getattr(self, f'is_CH{channel_number}_initiated'):
            self.initiate_channel(channel_number)

        vlim = self.get_voltage_limit_range(channel_number)
        vlim_ranges = getattr(self, f'CH{channel_number}_voltage_ranges')
        if vlim_ranges[vlim]['min'] <= value <= vlim_ranges[vlim]['max']:
            if not self.get_output_status(channel_number):
                self.output_enabled(channel_number)
            self.session.channels[channel_number].voltage_level = value
        else:
            raise ValueError(
                f"The voltage_level {value}V on CH{channel_number} is outside the allowed "
                f"range of {vlim_ranges[vlim]['min']}V to {vlim_ranges[vlim]['max']}V."
            )

    def get_voltage_sense(self, channel_number):
        if not getattr(self, f'is_CH{channel_number}_initiated'):
            return None

        if self.get_compliance(channel_number):
            raise RuntimeError(
                f"Channel {channel_number} is reporting a fault condition "
                f"— VOLTAGE measurement data is invalid."
            )

        measurements = []
        for _ in range(20):
            value = float(self.session.channels[channel_number].measure(nidcpower.MeasurementTypes.VOLTAGE))
            measurements.append(value)
        return sum(measurements) / len(measurements)

    # CURRENT
    def enable_current_limit_auto_range(self, channel_number):
        if not self.get_current_limit_auto_range(channel_number):
            if getattr(self, f'is_CH{channel_number}_initiated'):
                self.abort_channel(channel_number)
            self.session.channels[channel_number].current_limit_autorange = True  # AUTO
            self.initiate_channel(channel_number)

    def get_current_limit_auto_range(self, channel_number):
        return self.session.channels[channel_number].current_limit_autorange

    def set_current_limit_range(self, channel_number, value):
        if value == "AUTO":
            self.enable_current_limit_auto_range(channel_number)
        else:
            ilim = self.get_current_limit(channel_number)
            ilim_ranges = getattr(self, f'CH{channel_number}_current_ranges')

            if value not in ilim_ranges:
                raise ValueError(
                    f"Valid current limit range on CH{channel_number} are: {list(ilim_ranges.keys())}."
                )

            if getattr(self, f'is_CH{channel_number}_initiated'):
                self.abort_channel(channel_number)
                self.session.channels[channel_number].current_limit_autorange = False  # MANUAL
                if ilim_ranges[value]['min'] >= ilim >= ilim_ranges[value]['max']:
                    self.set_current_limit(channel_number, ilim_ranges[value]['max'])
                self.session.channels[channel_number].current_limit_range = value
                self.initiate_channel(channel_number)

    def get_current_limit_range(self, channel_number):
        return self.session.channels[channel_number].current_limit_range

    def set_current_limit(self, channel_number, value):
        ilim_range = self.session.channels[channel_number].current_limit_range
        ilim_ranges = getattr(self, f'CH{channel_number}_current_ranges')[ilim_range]

        if ilim_ranges['min'] <= value <= ilim_ranges['max']:
            self.session.channels[channel_number].current_limit = value
        else:
            raise ValueError(
                f"The current_limit {value}A on CH{channel_number} is outside "
                f"the allowed range of {ilim_ranges['min']}A to {ilim_ranges['max']}A."
            )

    def get_current_limit(self, channel_number):
        return self.session.channels[channel_number].current_limit

    def get_current_sense(self, channel_number):
        if not getattr(self, f'is_CH{channel_number}_initiated'):
            return None

        if self.get_compliance(channel_number):
            raise RuntimeError(
                f"Channel {channel_number} is reporting a fault condition "
                f"— CURRENT measurement data is invalid."
            )

        measurements = []
        for _ in range(20):
            value = float(self.session.channels[channel_number].measure(nidcpower.MeasurementTypes.CURRENT))
            measurements.append(value)
        return sum(measurements) / len(measurements)

    # CHANNELS
    def add_channel_voltage(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda value: self.set_voltage_level(channel_number, value))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_ilim", write_function=lambda value: self.set_current_limit(channel_number, value)
        )
        new_channel._set_value(self.get_current_limit(channel_number))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_current_readback(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_ilim_readback", read_function=lambda: self.get_current_limit(channel_number)
        )
        self._add_channel(new_channel)
        new_channel._set_value(self.get_current_limit_range(channel_number))
        return new_channel

    def add_channel_current_range(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_ilim_range", write_function=lambda value: self.set_current_limit_range(channel_number, value)
        )
        new_channel.add_preset("AUTO", "")
        for ilim_range in getattr(self, f'CH{channel_number}_current_ranges'):
            new_channel.add_preset(ilim_range, "")
        new_channel._set_value(self.get_current_limit_range(channel_number))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_vsense(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_vsense", read_function=lambda: self.get_voltage_sense(channel_number)
        )
        self._add_channel(new_channel)
        return new_channel

    def add_channel_isense(self, channel_name, channel_number):
        new_channel = channel(channel_name + "_isense", read_function=lambda: self.get_current_sense(channel_number))
        self._add_channel(new_channel)
        return new_channel

    def add_channel_enable(self, channel_name, channel_number):
        new_channel = channel(
            channel_name + "_enable", write_function=lambda state: self.output_enabled(channel_number, state)
        )
        new_channel.add_preset("ON", "")
        new_channel.add_preset("OFF", "")
        new_channel._set_value(self.get_output_status(channel_number))  # pylint: disable=protected-access
        self._add_channel(new_channel)
        return new_channel

    def clean_up(self):
        self.session.output_enabled = False
        self.session.abort()
        self.session.close()
