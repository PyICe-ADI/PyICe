from ..lab_core import *

class AD5259(instrument):
    '''Analog Devices Nonvolatile, I2C-Compatible 256-Position, Digital Potentiometer
    https://www.analog.com/media/en/technical-documentation/data-sheets/ad5259.pdf'''

    def __init__(self, interface_twi, addr7, full_scale_ohms):
        '''interface_twi is a PyICe interface_twi
        addr7 is the 7-bit I2C address of the AD5259 set by pinstrapping.
        '''
        instrument.__init__(self, f'Analog Devices I2C-Compatible 256-Position, Digital Potentiometer at {addr7:X}')
        self._base_name = 'AD5259'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        supported_addresses = [0x18, 0x1A, 0x4C, 0x4E]
        if addr7 not in supported_addresses:
            raise ValueError(f"\n\nPyICE Instrument Error: AD5259 only supports addresses: {supported_addresses}.")
        self.addr7 = addr7
        self.full_scale_ohms = full_scale_ohms
        # 3-Bit Commands left bit packed and added to 0b00000
        self.WRITE_TO_RDAC           = 0 << 5
        self.WRITE_TO_EEPROM         = 1 << 5
        self.ACTIVATE_WRITE_PROT     = 2 << 5
        self.STORE_RDAC_TO_EEPROM    = 6 << 5
        self.RESTORE_EEPROM_TO_RDAC  = 5 << 5
        self.READ_FROM_RDAC          = 0 << 5
        self.READ_FROM_EEPROM        = 1 << 5

    def add_all_channels(self, channel_base_name):
        self.add_channel_wiper(channel_base_name + "_wiper")
        self.add_channel_code(channel_base_name + "_code")
        self.add_channel_code_readback(channel_base_name + "_code_readback")

    def _write_word(self, command, value):
        assert value >= 0 and value <= 2**8-1
        try:
            self.twi.write_register(addr7=self.addr7, commandCode=command, data=value, data_size=8, use_pec=False)
        except Exception as e:
            self.twi.resync_communication()
            raise e

    def _read_byte(self, subaddr):
        try:
            result = self.twi.read_register(addr7=self.addr7, commandCode=subaddr, data_size=8, use_pec=False)
            return result
        except Exception as e:
            raise e
            self.twi.resync_communication()
            raise Exception("AD5259 Read EEProm Comunication Failed.")

    def _write_rdac(self, value):
        self._write_word(self.WRITE_TO_RDAC, value)

    def _read_rdac(self):
        return self._read_byte(subaddr=self.READ_FROM_RDAC)
            
    def _write_eeprom(self, value):
        self._write_word(self.WRITE_TO_EEPROM, value)

    def _read_eeprom(self):
        return self._read_byte(subaddr=self.READ_FROM_EEPROM)

    def add_channel_wiper(self, channel_name):
        def _write_wiper(value):
            '''value is between 0 and 1. DAC is biased toward 0 so that full scale is not achievable'''
            assert value >= 0 and value <= 1
            self._write_rdac(min(int(round(value * 2**8)), 2**8-1))
        self.wiper_channel = channel(channel_name, write_function=_write_wiper)
        def _read_wiper():
            return self._read_rdac() / 256
        self.wiper_channel._read = _read_wiper
        return self._add_channel(self.wiper_channel)

    def add_channel_code(self, channel_name):
        self.code_channel = channel(channel_name, write_function =self._write_rdac)
        self.code_channel.set_description('Raw 8-bit DAC code input')
        return self._add_channel(self.code_channel)

    def add_channel_code_readback(self, channel_name):
        self.code_readback_channel = channel(channel_name, read_function =self._read_rdac)
        return self._add_channel(self.code_readback_channel)