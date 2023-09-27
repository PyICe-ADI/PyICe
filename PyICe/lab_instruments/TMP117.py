from ..lab_core import *
from PyICe.lab_utils.swap_endian import swap_endian
from PyICe.lab_utils.twosComplementToSigned import twosComplementToSigned

class TMP117(instrument):
    '''Analog Devices Silicon Temperature Sensor
    https://www.ti.com/lit/gpn/tmp117'''
    def __init__(self, interface_twi, addr7):
        '''interface_twi is a interface_twi
        addr7 is the 7-bit I2C address of the TMP117 set by pinstrapping ADD0.
        Choose addr7 from:
        ADD0 = GND:    0x48
        ADD0 = V+:     0x49
        ADD0 = SDA:    0x4A
        ADD0 = SCL:    0x4B
        '''
        instrument.__init__(self, f'Analog Devices TMP117 Silicon Temperature Sensor at {addr7:X}')
        self._base_name                 = 'TMP117'
        self.add_interface_twi(interface_twi)
        self.twi                        = interface_twi
        self.addr7                      = addr7
        self.registers                  = {}
        self.registers['Temp_Result']   = 0x00
        self.registers['Configuration'] = 0x01
        self.registers['THigh_Limit']   = 0x02
        self.registers['TLow_Limit']    = 0x03
        self.registers['EEPROM_UL']     = 0x04
        self.registers['EEPROM1']       = 0x05
        self.registers['EEPROM2']       = 0x06
        self.registers['Temp_Offset']   = 0x07
        self.registers['EEPROM3']       = 0x08
        self.registers['Device_ID']     = 0x0F
        self.enable()
    def enable(self, enable = True):
        '''Place TMP117 into shutdown by writing enabled=False
        Re-enable by writing enabled=True'''
        if enable:
            self.twi.write_register(addr7=self.addr7, commandCode=self.registers['Configuration'], data=0b00<<10 | 0b01<<5, data_size=16, use_pec=False) # Average 8 readings
        else: #shutdown
            self.twi.write_register(addr7=self.addr7, commandCode=self.registers['Configuration'], data=0b01<<10, data_size=16, use_pec=False)
    def read_temp(self):
        '''Return free-running temperature conversion result.
        Temperature is the signed result at 7.8125m°C/lsb'''
        data = self.twi.read_register(addr7=self.addr7, commandCode=self.registers['Temp_Result'], data_size=16, use_pec=False)
        data = swap_endian(data, elementCount = 2)                    # MSB comes out first, not SMBus compatible!
        return twosComplementToSigned(data, bitCount=16) / 128.0      # LSB size adjustment
    def read_id(self):
        '''Return REV ID and Device ID'''
        data = self.twi.read_register(addr7=self.addr7, commandCode=self.registers['Device_ID'], data_size=16, use_pec=False)
        results = results_ord_dict()
        results['revision'] = data >> 12
        results['device'] = data & 0x0FFF
        return results
    def add_channel(self,channel_name):
        temp_channel = channel(channel_name, read_function=self.read_temp)
        return self._add_channel(temp_channel)