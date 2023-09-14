from PyICe.lab_core import *

class kikusui_pbz(scpi_instrument):
    '''single channel kikusui_pbz20-20, pbz40-10 bipolar power supply parent class'''
    def __init__(self,interface_visa):
        self.add_interface_visa(interface_visa)
        #initialize to instrument on, current 0
        self.clear_status()
        self.reset()
        self.get_interface().write(("CURR:LEV:IMM:AMPL 0.0A"))
        self.get_interface().write(("VOLT:LEV:IMM:AMPL 0V"))
        self._write_output_enable(True)
    def add_channel(self,channel_name,ilim=1,delay=0.5,add_extended_channels=True):
        '''Helper channel adds primary voltage forcing channel.
            Optionally specify channel current limit.  Valid range is [???-???]
            optionally also adds _ilim_source and _ilim_sink limit forcing channels'''
        voltage_channel = self.add_channel_voltage(channel_name)
        voltage_channel.set_write_delay(delay)
        if add_extended_channels:
            current_source_channel = self.add_channel_current_source(channel_name + "_ilim_source")
            current_source_channel.set_write_delay(delay)
            current_sink_channel = self.add_channel_current_sink(channel_name + "_ilim_sink")
            current_sink_channel.set_write_delay(delay)
            output_enable_channel = self.add_channel_output_enable(channel_name + "_enable")
            output_enable_channel.write(True)
            output_enable_channel.set_write_delay(delay)
            voltage_sense_channel = self.add_channel_vsense(channel_name + "_vsense")
            current_sense_channel = self.add_channel_isense(channel_name + "_isense")
            self.write_channel(channel_name + "_ilim_source", ilim)
            self.write_channel(channel_name + "_ilim_sink", -ilim)
        else:
            self._write_output_enable(True)
            self._write_current_source(ilim)
            self._write_current_sink(-ilim)
        return voltage_channel
    def add_channel_voltage(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_voltage)
        return self._add_channel(new_channel)
    def add_channel_current_source(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current_source)
        return self._add_channel(new_channel)
    def add_channel_current_sink(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current_sink)
        return self._add_channel(new_channel)
    def add_channel_output_enable(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_output_enable)
        return self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_vsense)
        return self._add_channel(new_channel)
    def add_channel_isense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_isense)
        return self._add_channel(new_channel)
    def add_channel_voltage_readback(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_voltage_readback)
        return self._add_channel(new_channel)
    def _write_current_source(self,current):
        self.get_interface().write((f"CURR:PROT:UPP {current}"))
    def _write_current_sink(self,current):
        self.get_interface().write((f"CURR:PROT:LOW {current}"))
    def _write_voltage(self,voltage):
        '''set output voltage'''
        self.get_interface().write((f"VOLTage {voltage}"))
    def _write_output_enable(self,enable):
        '''set output enable'''
        if enable:
            self.get_interface().write(("OUTP 1"))
        else:
            self.get_interface().write(("OUTP 0"))
    def _read_voltage_readback(self):
        '''Returns instrument's actual setopint.  May differ by commanded value by rounding/range error'''
        return float(self.get_interface().ask("VOLT?"))
    def _read_vsense(self):
        '''Returns instrument's measured output voltage.'''
        return float(self.get_interface().ask("MEAS:VOLT?"))
    def _read_isense(self):
        '''Returns instrument's measured current output.'''
        return float(self.get_interface().ask("MEAS:CURR?"))
