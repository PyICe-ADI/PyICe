from PyICe.lab_core import *
from PyICe.lab_instruments.ni_pps import ni_dcsupply
import nidcpower


class pxi_4110(ni_dcsupply):
    def __init__(self, resource_name):

        self._base_name = "PXI-4110_PPS"
        instrument.__init__(self, f"{self._base_name} @ {resource_name}")
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

if __name__ == "__main__":
    channels = master()
    from PyICe.lab_instruments.matrix_PEL8000 import matrix_PEL8000
    e_load = matrix_PEL8000(serial_port="COM7", baudrate=9600, timeout=10, parity="None", modbus_address=1)
    channels.add(e_load)
    e_load.add_channels("i_load")

    pps = pxi_4110("PXI1Slot8")
    channels.add(pps)
    pps.add_channels("CH0_force", 0)
    channels.write("CH0_force", 3.3)
    channels.write("CH0_force_ilim", 0.2)

    channels.write("i_load", 0.1)
    print(f'CH0_vsense={channels.read("CH0_force_vsense")}')
    print(f'i_load_vsense={channels.read("i_load_vsense")}')
    print(f'CH0_isense={channels.read("CH0_force_isense")}')
    print(f'i_load_isense={channels.read("i_load_isense")}')
    channels.read("CH0_force_ilim_readback")
    breakpoint()
    pps.clean_up()
