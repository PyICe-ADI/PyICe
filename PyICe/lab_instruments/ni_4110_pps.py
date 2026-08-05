""" NI PXI-4110, 3-Channel, 20V, 1A Programmable Power Supply instrument driver.

>>> from PyICe.lab_instruments.ni_4110_pps import pxi_4110

"""
from PyICe.lab_core import *  # noqa: F403
from PyICe.lab_instruments.ni_pps import ni_dcsupply
import nidcpower


class pxi_4110(ni_dcsupply):
    def __init__(self, resource_name):

        self._base_name = "PXI-4110_PPS"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")  # noqa: F405
        self.session = nidcpower.Session(resource_name=resource_name)
        self.session.output_enabled = False
        self.is_CH0_initiated = False
        self.is_CH1_initiated = False
        self.is_CH2_initiated = False
        self.CH0_voltage_ranges: dict = {
            6: {'min': 0, 'max': 6}                 # resolution = 12mV / 6mV
        }
        self.CH1_voltage_ranges: dict = {
            20: {'min': 0, 'max': 20}               # resolution = 40mV / 20mV
        }
        self.CH2_voltage_ranges: dict = {
            20: {'min': -20, 'max': 0}              # resolution = 40mV / 20mV
        }
        self.CH0_current_limits: dict = {'min': 0.0002, 'max': 1}
        self.CH0_current_ranges: dict = {
            1: {'min': 0.0002, 'max': 1},           # resolution = 0.02mA / 0.01mA
        }
        self.CH1_current_limits: dict = {'min': 0.0002, 'max': 1}
        self.CH1_current_ranges: dict = {
            0.02: {'min': 0.0002, 'max': 0.02},     # resolution = 0.40uA / 0.20uA
            1: {'min': 0.0002, 'max': 1},           # resolution = 0.02mA / 0.01mA
        }
        self.CH2_current_limits: dict = {'min': 0.0002, 'max': 1}
        self.CH2_current_ranges: dict = {
            0.02: {'min': 0.0002, 'max': 0.02},     # resolution = 0.40uA / 0.20uA
            1: {'min': 0.0002, 'max': 1},           # resolution = 0.02mA / 0.01mA
        }

    def add_channels(self, channel_name, channel_number):
        self.session.channels[channel_number].voltage_level_autorange = True
        self.session.channels[channel_number].current_limit_autorange = False
        self.session.channels[channel_number].source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.channels[channel_number].output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self.add_channel_voltage(channel_name, channel_number)
        self.add_channel_current(channel_name, channel_number)
        self.add_channel_current_readback(channel_name, channel_number)
        self.add_channel_current_range(channel_name, channel_number)
        self.add_channel_vsense(channel_name, channel_number)
        self.add_channel_isense(channel_name, channel_number)
        self.add_channel_enable(channel_name, channel_number)

    # NOTES # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # set_voltage_level can be set without initiate_channel
    # set_current_limit can be set without initiate_channel

    # NOT SUPPORTED PROPERTY in 4110
    # pps.session.channels[0].current_limit_high
    # pps.session.channels[0].current_limit_low
    # pps.session.channels[0].aperture_time_units (NPLC)
    # pps.session.channels[0].aperture_time (NPLC)
