from PyICe.lab_core import *
import time
class agilent_e36xxa(scpi_instrument):
    '''Generic base class for Agilent programmable DC power supply'''
    def add_channel_voltage(self,channel_name,num):
        voltage_channel = channel(channel_name,write_function=lambda voltage: self.set_voltage(num,voltage))
        voltage_channel.set_write_delay(self._default_write_delay)
        return self._add_channel(voltage_channel)
    def add_channel_current(self,channel_name,num):
        current_channel = channel(channel_name,write_function=lambda current: self.set_current(num,current))
        current_channel.set_write_delay(self._default_write_delay)
        return self._add_channel(current_channel)
    def add_channel_vsense(self,channel_name,num):
        vsense_channel = channel(channel_name,read_function=lambda: self.read_vsense(num))
        return self._add_channel(vsense_channel)
    def add_channel_isense(self,channel_name,num):
        isense_channel = channel(channel_name,read_function=lambda: self.read_isense(num))
        return self._add_channel(isense_channel)
    def set_voltage(self,num,voltage):
        self.get_interface().write(("INSTrument:SELect " + num))
        self.get_interface().write(("VOLTage " + str(voltage)))
        time.sleep(0.2)
    def set_current(self,num,current):
        self.get_interface().write(("INSTrument:SELect " + num))
        self.get_interface().write(("CURRent " + str(current)))
        time.sleep(0.2)
    def read_vsense(self,num):
        '''Query the instrument and return float representing actual measured terminal voltage.'''
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        self.get_interface().write((":INSTrument:SELect " + num))
        time.sleep(0.2)
        return float(self.get_interface().ask((":MEASure:VOLTage?")))
    def read_isense(self,num):
        '''Query the instrument and return float representing actual measured terminal current.'''
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        self.get_interface().write((":INSTrument:SELect " + num))
        time.sleep(0.2)
        return float(self.get_interface().ask(":MEASure:CURRent?"))
    def set_ilim(self,channel_name,ilim):
        raise Exception('removed, write to the appropriate channel instead')
    def enable_output(self,state):
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        if state:
            self.get_interface().write(":OUTput:STATe ON")
        else:
            self.get_interface().write(":OUTput:STATe OFF")
    def output_enabled(self):
        return self.get_interface().ask("OUTput:STATe?")
    def _set_remote_mode(self,remote=True):
        '''Required for RS-232 control.  Not allowed for GPIB control'''
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        if remote:
            self.get_interface().write(":SYSTem:REMote")
        else:
            self.get_interface().write(":SYSTem:LOCal")