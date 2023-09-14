from ..lab_core import *

class sorensen_generic_supply(instrument):
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'sorensen_generic_supply'
        instrument.__init__(self,  f"{self.sorensen_name} @ {interface_visa}" )
        self.add_interface_visa(interface_visa)
        #initialize to instrument on, all voltages 0
        #self.get_interface().write(("VSET 0"))
        #self.get_interface().write(("ISET 0"))
        #self.get_interface().write(("OUT 1"))
        self._write_voltage(0.0)
        self._write_current(0.0)
        self._enable_output()
    def add_channel(self,channel_name,ilim=1,add_extended_channels=True):
        '''Helper method adds primary voltage forcing channel channe_name.
        optionally also adds _ilim forcing channel and _vsense and _isense readback channels.'''
        voltage_channel = self.add_channel_voltage(channel_name)
        if add_extended_channels:
            self.add_channel_current(channel_name + "_ilim")
            self.add_channel_vsense(channel_name + "_vsense")
            self.add_channel_isense(channel_name + "_isense")
            self.write_channel(channel_name + "_ilim", ilim)
        else:
            self._write_current(ilim)
        return voltage_channel
    def add_channel_voltage(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_voltage)
        self._add_channel(new_channel)
    def add_channel_current(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current)
        self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_vsense)
        self._add_channel(new_channel)
    def add_channel_isense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_isense)
        self._add_channel(new_channel)
    def _enable_output(self):
        '''Enable output'''
        self.get_interface().write(("OUT 1"))
    def _write_voltage(self,voltage):
        '''Set named channel to force voltage, optionally with ilim compliance current'''
        self.get_interface().write((f"VSET {voltage}"))
    def _write_current(self,ilim):
        '''Set named channel's compliance current'''
        self.get_interface().write((f"ISET {ilim}"))
    def _read_vsense(self,channel_name):
        '''Returns instrument's measured output voltage.'''
        return  float( self.get_interface().ask("VOUT?").lstrip("VOUT ") )
    def _read_isense(self,channel_name):
        '''Returns instrument's measured output current.'''
        return float( self.get_interface().ask("IOUT? ").lstrip("IOUT ") )
