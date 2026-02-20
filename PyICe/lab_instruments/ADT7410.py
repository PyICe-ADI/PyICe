from ..lab_core import *
from PyICe.lab_utils.swap_endian import swap_endian
from PyICe.lab_utils.twosComplementToSigned import twosComplementToSigned

class ADT7410(instrument):
    '''Analog Devices Silicon Temperature Sensor
    http://www.analog.com/static/imported-files/data_sheets/ADT7410.pdf'''
    def __init__(self, interface_twi, addr7):
        '''interface_twi is a interface_twi
        addr7 is the 7-bit I2C address of the ADT7410 set by pinstrapping.
        Choose addr7 from 0x48, 0x49, 0x4A, 0x4B
        '''
        instrument.__init__(self, f'Analog Devices ADT7410 Silicon Temperature Sensor at 0x{addr7:X}')
        self._base_name = 'ADT7410'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        self.addr7 = addr7
        self.registers = {}
        self.registers['t_msb'] = 0x00
        self.registers['t_lsb'] = 0x01
        self.registers['status'] = 0x02
        self.registers['config'] = 0x03
        self.registers['thigh_msb'] = 0x04
        self.registers['thigh_lsb'] = 0x05
        self.registers['tlow_msb'] = 0x06
        self.registers['tlow_lsb'] = 0x07
        self.registers['tcrit_msb'] = 0x08
        self.registers['tcrit_lsb'] = 0x09
        self.registers['t_hyst'] = 0x0A
        self.registers['ID'] = 0x0B
        self.registers['reset'] = 0x2F
        self.enable()
    def enable(self, enabled = True):
        '''Place ADT7410 into shutdown by writing enabled=False
        Re-enable by writing enabled=True'''
        if enabled:
            # self.twi.write_byte(self.addr7, self.registers['config'], (0b1<<7)) #16-bit mode
            self.twi.write_register(addr7=self.addr7, commandCode=self.registers['config'], data=(0b1<<7), data_size=8, use_pec=False)
        else: #shutdown
            # self.twi.write_byte(addr7=self.addr7, self.registers['config'], (0b1<<7 + 0b11<<5))
            self.twi.write_register(addr7=self.addr7, commandCode=self.registers['config'], data=(0b1<<7 + 0b11<<5), data_size=8, use_pec=False)
    def read_temp(self):
        '''Return free-running temperature conversion result.
        16-bit conversion result scaled to signed degrees Celsius'''
        # data = self.twi.read_word(self.addr7, self.registers['t_msb']) #command code counter autoincrements
        data = self.twi.read_register(addr7=self.addr7, commandCode=self.registers['t_msb'], data_size=16, use_pec=False)
        data = swap_endian(data, elementCount = 2)  #msb comes out first, not SMBus compatible!
        data = twosComplementToSigned(data, bitCount=16)
        return data / 128.0 #lsb size adjustment
    def read_id(self):
        '''Return Manufacturer ID and chip revision ID'''
        # data = self.twi.read_byte(self.addr7, self.registers['ID'])
        data = self.twi.read_register(addr7=self.addr7, commandCode=self.registers['ID'], data_size=8, use_pec=False)
        results = results_ord_dict()
        results['revision'] = data & 0b111
        results['manufacturer'] = data >> 3
        return results
    def add_channel(self,channel_name):
        temp_channel = channel(channel_name, read_function=self.read_temp)
        return self._add_channel(temp_channel)