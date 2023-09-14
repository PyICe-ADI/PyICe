from PyICe.lab_core import *
from .agilent_e36xxa import agilent_e36xxa
import time

class agilent_e3631a(agilent_e36xxa):
    '''Triple-channel programmable DC power supply'''
    def __init__(self,interface_visa):
        self._base_name = 'agilent_e3631a'
        self.name = f'{_base_name} @ {interface_visa}'
        # instrument.__init__(self,self.name)
        super(agilent_e3631a, self).__init__(self.name)
        self.add_interface_visa(interface_visa)
        if isinstance(self.get_interface(), lab_interfaces.interface_visa_serial):
            self._set_remote_mode()
        time.sleep(0.05)
        self._default_write_delay = 0.5
        self.get_interface().write("*RST") # track function was being left enabled in some cases
        time.sleep(0.05)
        #initialize to instrument on, all voltages 0
        self.get_interface().write("APPLy P6V,  0.0, 0.0")
        self.get_interface().write("APPLy P25V, 0.0, 0.0")
        self.get_interface().write("APPLy N25V, 0.0, 0.0")
        time.sleep(0.05)
        self.enable_output(True)
    def add_channel(self,channel_name,num,ilim=1,add_sense_channels=True):
        '''Register a named channel with the instrument.
            channel_name is a user-supplied string
            num is "P6V", "P25V", "N25V", P50V has been removed, refer to virtual instrument
            optionally add _isense and _vsense readback channels'''
        num = num.upper()
        if num not in ['P6V','P25V','N25V']:
            raise Exception(f'Invalid channel number "{num}"')
        v_chan = self.add_channel_voltage(channel_name,num)
        self.add_channel_current(channel_name + "_ilim",num)
        self.write(channel_name + "_ilim",ilim)
        if add_sense_channels:
            self.add_channel_vsense(channel_name + "_vsense",num)
            self.add_channel_isense(channel_name + "_isense",num)
        return v_chan