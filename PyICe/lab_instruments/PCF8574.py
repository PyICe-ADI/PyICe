from ..lab_core import *

class PCF8574(instrument):
    def __init__(self, interface_twi, addr7):
        '''Multi-vendor 8bit I2C GPIO on Configurator XT. http://www.ti.com/lit/ds/symlink/pcf8574.pdf'''
        instrument.__init__(self, f'PCF8574 GPIO expander at 0x{addr7:X}')
        self._base_name = 'PCF8574'
        self.twi = interface_twi
        self.add_interface_twi(interface_twi)
        if addr7 not in range(0x20, 0x27+1):
            raise ValueError("\n\n\PCF8574 only supports addresses 0x20 - 0x27")
        self.addr7 = addr7
        self.state = 0
    def add_channel_writepin(self, channel_name, pin):
        '''Adds a single output pin to control. State is held locally since the pins are hi Z up they can't be relied upon to hold state.'''
        new_channel = channel(channel_name, write_function = lambda value: self._writepin(pin, value))
        new_channel.set_description(f"Write PCF8574 GPIO expander pin # {pin}")
        return self._add_channel(new_channel)
    def add_channel_readpin(self, channel_name, pin):
        '''Adds a single input pin to read back'''
        new_channel = channel(channel_name, read_function = lambda: self._readpin(pin))
        new_channel.set_description(f"Read back PCF8574 GPIO expander pin # {pin}")
        return self._add_channel(new_channel)
    def _writepin(self, pin, value):
        if value:
            self.state |= 2**pin
        else:
            self.state &= ~2**pin
        self.twi.write_register(addr7=self.addr7, commandCode=self.state, data=None, data_size=0, use_pec=False) # data_size=0 is secret code for sendbyte
    def _readpin(self, pin):
        return (data & 2**pin) >> pin
