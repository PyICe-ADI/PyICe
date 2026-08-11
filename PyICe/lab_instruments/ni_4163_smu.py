""" NI PXIe-4124 24-Channel, 24V SMU instrument driver.

>>> from PyICe.lab_instruments.ni_4163_smu import pxie_4163

"""
import nidcpower
from PyICe.lab_instruments.ni_dcpower import ni_dcpower


class pxie_4163(ni_dcpower):
    def __init__(self, resource_name):
        self._base_name = "PXIe-4163"
        self.instr_name = f"{self._base_name} @ {resource_name}"
        super().__init__(self.instr_name, resource_name)

        self.current_limits = {'min': 10e-9, 'max': 50e-3}
        self.current_ranges = {
            10e-6: {'min': 1e-6, 'max': 10e-6},     # resolution = 100pA
            100e-6: {'min': 10e-6, 'max': 100e-6},  # resolution = 1nA
            1e-3: {'min': 100e-6, 'max': 1e-3},     # resolution = 10nA
            10e-3: {'min': 1e-3, 'max': 10e-3},     # resolution = 100nA
            30e-3: {'min': 10e-3, 'max': 30e-3},    # resolution = 100nA
            50e-3: {'min': 30e-3, 'max': 50e-3},    # resolution = 500nA
        }
        self.voltage_limits = {'min': -24, 'max': 24}
        self.voltage_ranges = {
            24: {'min': 0, 'max': 24},  # resolution = 200uV
        }

    def config_dc_voltage_source(self, channel_name, channel_number):
        self.session.channels[channel_number].current_limit_autorange = False
        self.session.channels[channel_number].voltage_level_autorange = True
        self.session.channels[channel_number].source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.channels[channel_number].output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self.session.channels[channel_number].initiate()
        self.add_channel_output(channel_name, channel_number)
        self.add_channel_voltage_force(channel_name, channel_number)
        self.add_channel_voltage_range(channel_name, channel_number)
        self.add_channel_current_limit(channel_name, channel_number)
        self.add_channel_current_limit_range(channel_name, channel_number)
        self.add_channel_nplc(channel_name, channel_number)
        self.add_channel_current_sense(channel_name, channel_number)
        self.add_channel_voltage_sense(channel_name, channel_number)
        self.add_channel_compliance_sense(channel_name, channel_number)
        self.add_channel_sensing(channel_name, channel_number)

    def config_dc_current_source(self, channel_name, channel_number):
        self.session.channels[channel_number].voltage_limit_autorange = True
        self.session.channels[channel_number].current_level_autorange = True
        self.session.channels[channel_number].source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.channels[channel_number].output_function = nidcpower.OutputFunction.DC_CURRENT
        self.session.channels[channel_number].initiate()
        self.add_channel_output(channel_name, channel_number)
        self.add_channel_current_force(channel_name, channel_number)
        self.add_channel_current_range(channel_name, channel_number)
        self.add_channel_voltage_limit(channel_name, channel_number)
        self.add_channel_voltage_limit_range(channel_name, channel_number)
        self.add_channel_nplc(channel_name, channel_number)
        self.add_channel_current_sense(channel_name, channel_number)
        self.add_channel_voltage_sense(channel_name, channel_number)
        self.add_channel_compliance_sense(channel_name, channel_number)
        self.add_channel_sensing(channel_name, channel_number)

    def config_dc_voltmeter(self, channel_name, channel_number):
        self.session.channels[channel_number].voltage_limit_autorange = True
        self.session.channels[channel_number].current_level_autorange = True
        self.session.channels[channel_number].source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.channels[channel_number].output_function = nidcpower.OutputFunction.DC_CURRENT
        self.session.channels[channel_number].initiate()
        self.add_channel_voltage_limit(channel_name, channel_number)
        self.add_channel_voltage_limit_range(channel_name, channel_number)
        self.add_channel_nplc(channel_name, channel_number)
        self.add_channel_current_sense(channel_name, channel_number)
        self.add_channel_voltage_sense(channel_name, channel_number)
        self.add_channel_compliance_sense(channel_name, channel_number)
        self.add_channel_sensing(channel_name, channel_number)
        self.session.channels[channel_number].current_level_range = 10e-6

    def setup_channels(self, smu_channels):
        for smu_channel in smu_channels:
            if smu_channel['config'] == "isource":
                self.config_dc_current_source(
                    channel_name=smu_channel['channel_name'], channel_number=smu_channel['channel_num']
                )
            elif smu_channel['config'] == "vsource":
                self.config_dc_voltage_source(
                    channel_name=smu_channel['channel_name'], channel_number=smu_channel['channel_num']
                )
            elif smu_channel['config'] == "vsense":
                self.config_dc_voltmeter(
                    channel_name=smu_channel['channel_name'], channel_number=smu_channel['channel_num']
                )
            else:
                raise ValueError("Channel mode must be one of: isource, isense, vsource, vsense.")
