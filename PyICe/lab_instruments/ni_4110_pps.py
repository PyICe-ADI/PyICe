""" NI PXI-4110, 3-Channel, 20V, 1A
    Programmable Power Supply instrument driver.

>>> from PyICe.lab_instruments.ni_4110_pps import pxi_4110

"""
import nidcpower
from PyICe.lab_instruments.ni_pps import ni_dcsupply


class pxi_4110(ni_dcsupply):
    # Channel specifications (class-level constants)
    _VOLTAGE_RANGES = {
        # Channel: {min: , max:}
        0: {6: {'min': 0, 'max': 6}},
        1: {20: {'min': 0, 'max': 20}},
        2: {20: {'min': -20, 'max': 0}},
    }
    _CURRENT_LIMITS = {'min': 0.0002, 'max': 1}
    _CURRENT_RANGES = {
        # Channel: {min: , max:}
        0: {1: {'min': 0.0002, 'max': 1}},
        1: {0.02: {'min': 0.0002, 'max': 0.02}, 1: {'min': 0.0002, 'max': 1}},
        2: {0.02: {'min': 0.0002, 'max': 0.02}, 1: {'min': 0.0002, 'max': 1}},
    }
    _NUM_CHANNELS = 3

    def __init__(self, resource_name):
        self._base_name = "PXI-4110_PPS"
        self.instr_name = f"{self._base_name} @ {resource_name}"
        super().__init__(self.instr_name, resource_name)

        # Initialize channel states and specs from class constants
        for ch in range(self._NUM_CHANNELS):
            setattr(self, f'is_CH{ch}_initiated', False)
            setattr(self, f'CH{ch}_voltage_ranges', self._VOLTAGE_RANGES[ch])
            setattr(self, f'CH{ch}_current_limits', self._CURRENT_LIMITS)
            setattr(self, f'CH{ch}_current_ranges', self._CURRENT_RANGES[ch])

    def add_channels(self, channel_name, channel_number):
        self.session.channels[channel_number].voltage_level_autorange = True
        self.session.channels[channel_number].current_limit_autorange = False
        self.session.channels[channel_number].source_mode = (
            nidcpower.SourceMode.SINGLE_POINT
        )
        self.session.channels[channel_number].output_function = (
            nidcpower.OutputFunction.DC_VOLTAGE
        )
        self.add_channel_voltage(channel_name, channel_number)
        self.add_channel_current(channel_name, channel_number)
        self.add_channel_current_readback(channel_name, channel_number)
        self.add_channel_current_range(channel_name, channel_number)
        self.add_channel_vsense(channel_name, channel_number)
        self.add_channel_isense(channel_name, channel_number)
        self.add_channel_enable(channel_name, channel_number)

    # NOT SUPPORTED PROPERTY in 4110
    # pps.session.channels[0].current_limit_high
    # pps.session.channels[0].current_limit_low
    # pps.session.channels[0].aperture_time_units (NPLC)
    # pps.session.channels[0].aperture_time (NPLC)
