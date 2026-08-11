""" NI PXIe-4130, 20V, 2A DC, 40W SMU instrument driver.

>>> from PyICe.lab_instruments.ni_4130_smu import pxie_4130

"""
import nidcpower
from PyICe.lab_instruments.ni_dcpower import ni_dcpower


class pxie_4130(ni_dcpower):
    def __init__(self, resource_name):
        self._base_name = "PXIe-4130"
        self.instr_name = f"{self._base_name} @ {resource_name}"
        super().__init__(self.instr_name, resource_name)

        self.current_limits = {'min': 200e-9, 'max': 2}
        self.current_ranges = {
            200e-6: {'min': 200e-9, 'max': 200e-6},  # resolution = 10nA / 1nA
            2e-3: {'min': 200e-6, 'max': 2e-3},      # resolution = 100nA / 10nA
            20e-3: {'min': 2e-3, 'max': 20e-3},      # resolution = 1uA / 0.1uA
            200e-3: {'min': 20e-3, 'max': 200e-3},   # resolution = 10uA / 1uA
            2: {'min': 200e-3, 'max': 2},            # resolution = 100uA / 10uA - Requires auxiliary power supply
        }
        self.voltage_limits = {'min': 0, 'max': 20}
        self.voltage_ranges = {
            6: {'min': 0, 'max': 6},  # resolution = 0.1mV / 0.10mV
            20: {'min': 0, 'max': 20},  # resolution = 0.33mV / 0.10mV
        }

    def config_dc_voltage_source(self, channel_name, channel_number=0):
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

    def config_dc_current_source(self, channel_name, channel_number=0):
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

    def config_dc_voltmeter(self, channel_name, channel_number=0):
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

    def config_dc_currentmeter(self, channel_name, channel_number):
        self.session.channels[channel_number].current_limit_autorange = False
        self.session.channels[channel_number].voltage_level_autorange = True
        self.session.channels[channel_number].source_mode = nidcpower.SourceMode.SINGLE_POINT
        self.session.channels[channel_number].output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self.session.channels[channel_number].initiate()
        self.add_channel_output(channel_name, channel_number)
        self.add_channel_current_limit(channel_name, channel_number)
        self.add_channel_current_limit_range(channel_name, channel_number)
        self.add_channel_nplc(channel_name, channel_number)
        self.add_channel_current_sense(channel_name, channel_number)
        self.add_channel_compliance_sense(channel_name, channel_number)
        self.add_channel_sensing(channel_name, channel_number)
        self.session.channels[channel_number].voltage_level = 0
        self.write_channel(f"{channel_name}_nplc", 8)
        self.write_channel(f"{channel_name}_sensing", "LOCAL")
        self.write_channel(f"{channel_name}_enable_output", "ON")

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
            elif smu_channel['config'] == "isense":
                self.config_dc_currentmeter(
                    channel_name=smu_channel['channel_name'], channel_number=smu_channel['channel_num']
                )
            else:
                raise ValueError("Channel mode must be one of: isource, isense, vsource, vsense.")
