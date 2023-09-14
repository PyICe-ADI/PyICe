from PyICe.lab_core import *

class chroma_63600(scpi_instrument):
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'chroma_63600'
        scpi_instrument.__init__(self,f"chroma_63600 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write(("*RL1"))
    def set_mode_and_range(self, num, mode, range):
        '''Sets the mode and range.
            Mode: a string of either CC, CR, CV, CP, or CZ
            Range: a string of either L, M, or H
        '''
        self._select_load_channel(num)
        self.get_interface().write(((f"MODE {mode}{range}").upper()))
    def _select_load_channel(self, num):
        '''Selects which load channel will receive subsequent commands.
            
            From the Chroma manual section 2.4.1:
        
            The channel number of the Load is determined by the module location in the Mainframe starting from the farthest left slot.
            As some Load (63610-80-20) has two channels in one module, channel 1 and 2 are always on the farthest left slot of the Mainframe, and channel 9and 10 on the farthest right.
            The channel number is fixed for Mainframe even the Load and 10 on the farthest right.
            The channel number is fixed for Mainframe even the Load module is empty.
            Figure 2-3 shows the channel assignments for a Chroma 63600-5 Mainframe containing two Loads of 63630-80-60 single channel module, and two Loads of 63610-80-20 dual channel module.
            Channel number is automatically assigned to 1, 3, 5, 6, 7, and 8.
            Channel 2 and 4 are skipped as single module is applied.
        '''
        self.get_interface().write((f"CHAN {num}"))
    # def add_channel_enable(self, channel_name, num):
        # new_channel = integer_channel(channel_name, size=1, write_function= lambda state, num=num: self._write_enable(num,state))
        # new_channel.set_attribute('chroma_number', num)
        # return self._add_channel(new_channel)
    def _write_enable(self, num, state):
        self._select_load_channel(num)
        if state:
            self.get_interface().write(("LOAD ON"))
        else:
            self.get_interface().write(("LOAD OFF"))
    def add_channel_current(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda current: self._write_current(num,current))
        new_channel.set_attribute('chroma_number',num)
        new_channel.set_max_write_limit(20) #only achievable in H (high) mode
        new_channel.set_min_write_limit(0)
        return self._add_channel(new_channel)
    def _write_current(self,num,current):
        self._write_enable(num, current!=0)          
        self.get_interface().write((f"CURR:STAT:L1 {current}"))
    def add_channel_voltage(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda voltage: self._write_voltage(num,voltage))
        new_channel.set_attribute('chroma_number',num)
        new_channel.set_max_write_limit(80) #only achievable in H (high) mode
        new_channel.set_min_write_limit(0)
        return self._add_channel(new_channel)
    def _write_voltage(self,num,voltage):
        self._select_load_channel(num)
        self.get_interface().write((f"VOLT:STAT:L1 {voltage}"))
    def add_channel_current_limit(self, channel_name, num): #current limit in CV  mode
        new_channel = channel(channel_name, write_function=lambda current_limit: self._write_current_limit(num,current_limit))
        new_channel.set_attribute('chroma_number',num)
        new_channel.set_max_write_limit(20) #only achievable in H (high) mode
        new_channel.set_min_write_limit(0)
        return self._add_channel(new_channel)
    def _write_current_limit(self,num,current_limit):
        self._select_load_channel(num)
        self.get_interface().write((f"VOLT:STAT:ILIM {current_limit}"))
    def add_channel_resistance(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda resistance: self._write_resistance(num,resistance))
        new_channel.set_attribute('chroma_number',num)
        new_channel.set_max_write_limit(12000) #only achievable in H (high) mode
        new_channel.set_min_write_limit(0.04) #only achievable in L (low) mode
        return self._add_channel(new_channel)
    def _write_resistance(self,num,resistance):
        self._select_load_channel(num)
        self.get_interface().write((f"RES:STAT:L1 {resistance}")) #TODO
    def add_channel_power(self, channel_name, num):
        new_channel = channel(channel_name, write_function=lambda power: self._write_power(num,power))
        new_channel.set_attribute('chroma_number',num)
        new_channel.set_max_write_limit(100) #only achievable in H (high) mode
        new_channel.set_min_write_limit(0)
        return self._add_channel(new_channel)
    def _write_power(self,num,power):
        self._select_load_channel(num)
        self.get_interface().write((f"POW:STAT:L1 {power}"))
    #no support for CZ mode at the moment...
    # def _set_measure_input(self,num):
        # self.get_interface().write((f"MEAS:INP {num}"))
    def add_channel_measured_current(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_measured_current(num))
        new_channel.set_attribute('chroma_number',num)
        return self._add_channel(new_channel)
    def _read_measured_current(self,num):
        self._select_load_channel(num)
        self.get_interface().write(("MEAS:INP LOAD"))
        return float(self.get_interface().ask("MEAS:CURR?")) # returns a string by default
    def add_channel_measured_voltage(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_measured_voltage(num))
        new_channel.set_attribute('chroma_number',num)
        return self._add_channel(new_channel)
    def _read_measured_voltage(self,num):
        self._select_load_channel(num)
        self.get_interface().write(("MEAS:INP UUT")) #UUT sets it to the sense terminals
        return float(self.get_interface().ask("MEAS:VOLT?")) # returns a string by default
    def add_channel_measured_power(self, channel_name, num):
        new_channel = channel(channel_name, read_function=lambda: self._read_measured_power(num))
        new_channel.set_attribute('chroma_number',num)
        return self._add_channel(new_channel)
    def _read_measured_power(self,num):
        self._select_load_channel(num)
        self.get_interface().write(("MEAS:INP LOAD"))
        return float(self.get_interface().ask("MEAS:POW?")) # returns a string by default
