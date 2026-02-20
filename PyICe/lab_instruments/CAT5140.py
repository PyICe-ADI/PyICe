from ..lab_core import *

class CAT5140(instrument):
    '''ONSemi/Catalyst I2C 256 Tap Potentiometer'''
    def __init__(self, interface_twi):
        self.addr7 = 0b0101000
        instrument.__init__(self, f'ONSemi/Catalyst I2C 8-bit Potentiometer at 0x{self.addr7:X}')
        self._base_name = 'CAT5140'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        self.tries = 3
    def _write_byte(self, addr7, subaddr, data):
        tries = self.tries
        while tries:
            try:
                tries -= 1
                # self.twi.write_byte(addr7, subaddr, data)
                self.twi.write_register(addr7=addr7, commandCode=subaddr, data=data, data_size=8, use_pec=False)
                return
            except Exception as e:
                print(e)
                self.twi.resync_communication()
                if not tries:
                    raise e
    def set_output(self, value):
        assert value >= 0
        assert value <= 2**8-1
        self._write_byte(self.addr7, 0x00, value)
    def get_output(self):
        tries = self.tries
        while tries:
            try:
                tries -= 1
                # value = self.twi.read_byte(self.addr7, 0x00)
                value = self.twi.read_register(addr7=self.addr7, commandCode=0x00, data_size=8, use_pec=False)
                return value
            except Exception as e:
                raise e
                self.twi.resync_communication()
        raise Exception("CAT5140 Communication Failed.")
    def _write_percent(self,percent):
        '''value is between 0 and 1. DAC is biased toward 0 so that full scale is not achievable'''
        assert percent >= 0
        assert percent <= 1
        code = min(int(round(percent * 2**8)), 2**8-1)
        self.set_output(code)
    def add_channel_code(self,channel_name):
        code_channel = channel(channel_name, write_function =self.set_output)
        return self._add_channel(code_channel)
    def add_channel_percent(self, channel_name):
        percent_channel = channel(channel_name, write_function =self._write_percent)
        return self._add_channel(percent_channel)
    def add_channel_code_readback(self, channel_name):
        code_channel = channel(channel_name, read_function =self.get_output)
        return self._add_channel(code_channel)
    def add_channel_percent_readback(self, channel_name):
        percent_channel = channel(channel_name, read_function = lambda: self.get_output() / float(2**8 - 1))
        return self._add_channel(percent_channel)
    def _select_nonvolatile_register(self):
        # self.twi.write_byte(self.addr7, 0x08, 0x00)
        self.twi.write_register(addr7=self.addr7, commandCode=0x08, data=0x00, data_size=8, use_pec=False)
    def _select_volatile_register(self):
        # self.twi.write_byte(self.addr7, 0x08, 0x01)
        self.twi.write_register(addr7=self.addr7, commandCode=0x08, data=0x01, data_size=8, use_pec=False)
    def add_channel_select_nonvolatile_register(self, channel_name):
        nvselect_channel = channel(channel_name, write_function = lambda x: _select_nonvolatile_register())
        return self._add_channel(nvselect_channel)
    def add_channel_select_volatile_register(self, channel_name):
        volselect_channel = channel(channel_name, write_function = lambda x: _select_volatile_register())
        return self._add_channel(volselect_channel)