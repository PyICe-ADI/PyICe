from ..lab_core import *

class agilent_e4433b(instrument):
    '''Agilent E4433B Signal Generator'''
    def __init__(self,interface_visa):
        self._base_name = 'agilent_e4433b'
        instrument.__init__(self,f"agilent_e4433b @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write(("*RST"))
    def add_channel(self,channel_name,add_extended_channels=True):
        new_channel = channel(channel_name,write_function=self.write_output)
        if add_extended_channels:
            self.add_channel_freq(channel_name + "_freq")
            self.add_channel_power(channel_name + "_power")
        return self._add_channel(new_channel)
    def write_output(self,freq,power):
        self._write_power(power)
        self._write_freq(freq)
    def _write_power(self,channel_name,power):
        self.get_interface().write(("POWER " + str(power) + " DBM"))
    def _write_freq(self,channel_name,freq):
        self.get_interface().write(("FREQuency " + str(freq) + "MHZ"))
    def add_channel_freq(self, channel_name):
        freq_channel = channel(channel_name,read_function=self.read_freq)
        return self._add_channel(freq_channel)
    def add_channel_power(self, channel_name):
        power_channel = channel(channel_name,read_function=self.read_power)
        return self._add_channel(power_channel)
    def read_freq(self):
        return self.get_interface().ask(("FREQ?"))
    def read_power(self):
        return self.get_interface().ask(("POWER?"))
    def enable_output(self):
        self.get_interface().write(("OUTP:STAT ON"))
    def disable_output(self):
        self.get_interface().write(("OUTP:STAT OFF"))
