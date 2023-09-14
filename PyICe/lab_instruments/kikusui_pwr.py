from PyICe.lab_core import *

class kikusui_pwr(scpi_instrument):
    '''Kikusui single channel unipolar power supply superclass
        Instrument Family:
            PWR400L
            PWR400M
            PWR400H
            PWR800L
            PWR800M
            PWR800H
            PWR1600L
            PWR1600M
            PWR1600H'''
    #note that this superclass was developed and tested with only the PWR800l instrument
    #some methods may need to be duplicated and moved to the instrument-specific classes
    #to resolve any operational/feature differences such as range selection
    def __init__(self,interface_visa,node,ch):
        '''node is a ???
           ch is a ???'''
        self._base_name = 'kikusui_pwr'
        scpi_instrument.__init__(self,  f"kikusui_pwr800l {self.kikusui_pwr_name} @ {interface_visa}:Node {node}: Ch{ch}" )
        self.add_interface_visa(interface_visa)
        self.node = node
        self.ch = ch
        #initialize to instrument on, current 0
        self.get_interface().write((f"NODE {self.node};CH {self.ch};*CLS"))
        self.get_interface().write((f"NODE {self.node};CH {self.ch};*RST"))
        self.get_interface().write((f"NODE {self.node};CH {self.ch};VSET 0.000"))
        self.get_interface().write((f"NODE {self.node};CH {self.ch};ISET 0.000"))
        self.get_interface().write(("OUT 1"))
    def add_channel(self,channel_name,ilim=1,delay=0.5,add_extended_channels=True):
        '''Helper function adds primary voltage forcing channel channel_name
        optionally also adds _ilim forcing channel and _vsense and _isense readback channels.'''
        voltage_channel = self.add_channel_voltage(channel_name)
        self.write_channel(channel_name,0)
        voltage_channel.set_write_delay(delay)
        if add_extended_channels:
            current_channel = self.add_channel_current(channel_name + "_ilim")
            current_channel.set_write_delay(delay)
            self.add_channel_vsense(channel_name + "_vsense")
            self.add_channel_isense(channel_name + "_isense")
            self.write_channel(channel_name + "_ilim", ilim)
        else:
            self._write_current(ilim)
        return voltage_channel
    def add_channel_voltage(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_voltage)
        return self._add_channel(new_channel)
    def add_channel_current(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current)
        return self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_vsense)
        return self._add_channel(new_channel)
    def add_channel_isense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_isense)
        return self._add_channel(new_channel)
    def add_channel_power(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_power)
        return self._add_channel(new_channel)
    def add_channel_enable(self,channel_name):
        new_channel = channel(channel_name,write_function=self._enable)
        return self._add_channel(new_channel)
    def _write_voltage(self,voltage):
        self.get_interface().write((f"NODE {self.node};CH {self.ch};VSET {voltage}"))
    def _write_current(self,current):
        self.get_interface().write((f"NODE {self.node};CH {self.ch};ISET {current}"))
    def _enable(self,enable):
        if enable:
            self.get_interface().write((f"NODE {self.node};CH {self.ch};OUT 1"))
        else:
            self.get_interface().write((f"NODE {self.node};CH {self.ch};OUT 0"))
    def _read_vsense(self):
        '''Returns instrument's measured output voltage.'''
        return float(self.get_interface().ask(f"NODE {self.node};CH {self.ch};VOUT?"))
    def _read_power(self):
        '''Returns instrument's measured power output.'''
        return float(self.get_interface().ask(f"NODE {self.node};CH {self.ch};POUT?"))
    def _read_isense(self):
        '''Returns instrument's measured current output.'''
        return float(self.get_interface().ask(f"NODE {self.node};CH {self.ch};IOUT?"))
