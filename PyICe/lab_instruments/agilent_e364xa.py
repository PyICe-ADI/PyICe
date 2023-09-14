from PyICe.lab_core import *
from .agilent_e36xxa import agilent_e36xxa

class agilent_e364xa(agilent_e36xxa):
    '''Dual-channel programmable DC power supply'''
    def __init__(self,interface_visa,resetoutputs=True):
        self._base_name = 'agilent_e3648a'
        self.name = f'{self._base_name} @ {interface_visa}'
        # instrument.__init__(self,self.name)
        super(agilent_e364xa, self).__init__(self.name)
        self.add_interface_visa(interface_visa)
        if isinstance(self.get_interface(), lab_interfaces.interface_visa_serial):
            self._set_remote_mode()
        self._default_write_delay = 0.5
        #initialize to instrument on, all voltages 0
        if resetoutputs: #NB, original scpi was incorrect format
            self.get_interface().write(("INSTrument:SELect OUT1"))
            self.get_interface().write(("APPLy 0.0, 0.0"))
            self.get_interface().write(("INSTrument:SELect OUT2"))
            self.get_interface().write(("APPLy 0.0, 0.0"))
            self.enable_output(True)
    def add_channel(self,channel_name,num,ilim=1,add_extended_channels=True):
        '''Register a named channel with the instrument.
            channel_name is a user-supplied string
            num must be either "OUT1" or "OUT2"
            optionally add _ilim, _isense and _vsense channels'''
        num = num.upper()
        if num not in ['OUT1','OUT2']:
            raise Exception(f'Invalid channel number "{num}"')
        self.add_channel_voltage(channel_name,num)
        if add_extended_channels:
            self.add_channel_current(channel_name + "_ilim",num)
            self.write(channel_name + "_ilim",ilim)
            self.add_channel_vsense(channel_name + "_vsense",num)
            self.add_channel_isense(channel_name + "_isense",num)
        else:
            self.set_current(num,ilim)
    def set_ovp_voltage(self,voltage,num): #NB
        self.select_output(num)
        self.get_interface().write(f'VOLT:PROT {voltage}')
        self.get_interface().write('VOLT:PROT:STAT ON')
    def select_output(self,num): #NB
        num = num.upper()
        if num not in ['OUT1','OUT2']:
            raise Exception(f'Invalid channel number "{num}"')
        self.get_interface().write(f'INSTrument:SELect {num}')

class agilent_e3648a(agilent_e364xa):
    pass

class agilent_e3649a(agilent_e364xa):
    pass