""" NI PXIe-4139, 60V, 3A DC, 10A Pulsed, 40W SMU instrument driver.

>>> from PyICe.lab_instruments.ni_4139_smu import pxie_4139

"""
import nidcpower
from PyICe.lab_instruments.ni_dcpower import ni_dcpower


class pxie_4139(ni_dcpower):
    def __init__(self, resource_name):
        self._base_name = "PXIe-4139"
        self.instr_name = f"{self._base_name} @ {resource_name}"
        super().__init__(self.instr_name, resource_name)

        self.current_limits = {'min': 1e-6, 'max': 3}
        self.current_ranges = {
            1e-6: {'min': 100e-9, 'max': 1e-6},     # resolution = 100fA
            10e-6: {'min': 1e-6, 'max': 10e-6},      # resolution = 1pA
            100e-6: {'min': 10e-6, 'max': 100e-6},   # resolution = 10pA
            1e-3: {'min': 100e-6, 'max': 1e-3},      # resolution = 100pA
            10e-3: {'min': 1e-3, 'max': 10e-3},      # resolution = 1nA
            100e-3: {'min': 10e-3, 'max': 100e-3},   # resolution = 10nA
            1: {'min': 100e-3, 'max': 1},            # resolution = 100nA
            3: {'min': 100e-3, 'max': 3},            # resolution = 1uA
        }
        self.voltage_limits = {'min': 0, 'max': 60}
        self.voltage_ranges = {
            600e-3: {'min': 0, 'max': 600e-3},  # resolution = 100nV
            6: {'min': 0, 'max': 6},            # resolution = 1uV
            60: {'min': 0, 'max': 60},          # resolution = 10uV
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
        self.add_channel_compliance_sense(channel_name, channel_number)  # True or False
        self.add_channel_sensing(channel_name, channel_number)  # Local or Remote
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
