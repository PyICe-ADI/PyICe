from ..lab_core import *
import math

class htx9016(scpi_instrument):
    ''' 5 Channel RF MUX Hypertronix (Steve Martin) HTX9016
        DC Coupled or AC Coupled versions available.
        Should be good from 100Hz (AC) or 0Hz (DC) to about 1GHz.'''
    def __init__(self, interface_visa):
        self._base_name = 'htx9016'
        scpi_instrument.__init__(self,f"HTX9016 {interface_visa}")
        self.add_interface_visa(interface_visa, timeout=0.5)
    def __del__(self):
        '''Close interface (serial) port on exit'''
        self.get_interface().close()
    def _decode_readback(self):
        value = self.get_interface().ask(":SELEct:CHANnel?")
        if value == "0":
            return 0
        elif value in ["2","4","8","16","32"]:
            return math.log2(int(value))
        else:
            raise Exception(f"*** HTX9016 RF MUX *** CAUTION: Multiple channels are on, return value {value} should be a power of 2!")
    def add_channel(self, channel_name):
        new_channel = channel(channel_name, write_function=lambda ch : self.get_interface().write(f":SELEct:CHANnel {ch}"))
        new_channel._read = self._decode_readback
        new_channel.set_write_delay(0.012) # Axicom HF3 relay max operation time 6ms with diode. I doubled it SLM.
        new_channel.add_preset("1")
        new_channel.add_preset("2")
        new_channel.add_preset("3")
        new_channel.add_preset("4")
        new_channel.add_preset("5")
        new_channel.add_preset("OFF")
        new_channel.write("OFF")
        return self._add_channel(new_channel)
    def get_serial_number(self):
        return self.get_interface().ask(":STORe:SERIalnum?")
