from ..lab_core import *
from PyICe.lab_utils.swap_endian import swap_endian

class AD5693R(instrument):
    '''Analog Devices 16 bit DAC
    http://www.analog.com/en/products/digital-to-analog-converters/da-converters/ad5693r.html'''
    def __init__(self, interface_twi, addr7):
        '''interface_twi is a interface_twi
        addr7 is the 7-bit I2C address of the ADT5693R set by pinstrapping.
        A0 = 0: 1001100 (4C)
        A1 = 1: 1001110 (4E)
        '''
        instrument.__init__(self, f'Analog Devices AD5693R Digital to Analog Converter at 0x{addr7:X}')
        self._base_name = 'AD5693R'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        self.addr7              = addr7     # user's address input.
        self.dac_reg            = 0x30      # send dac codes to this address for auto update.
        self.control_reg        = 0x40      # sets up gain and power down modes.
        self.gain_code          = 0x0800    # 0 to 5V rather than 0 to 2.5V.
        self.impedance          = 0x0000    # start with output on, this sets and r to GND for disable mode.
        self.vref               = 2.5       # an internal constant.
        self.refenable          = 0         # default 0 is reference on, 1 is off.
        self.reset              = 0x8000    # Use carefully, gums up ACKs.
        self._update_controlreg()           # Clear the whole thing out.
        self._set_voltage(0)                # In lieu of using the reset bit which nukes the I2C port.
    def _update_controlreg(self):
        # self.twi.write_word(self.addr7, self.control_reg, swap_endian(self.impedance | self.refenable | self.gain_code, elementCount = 2))
        self.twi.write_register(addr7=self.addr7, commandCode=self.control_reg, data=swap_endian(self.impedance | self.refenable | self.gain_code, elementCount = 2), data_size=16, use_pec=False)
    def _set_code(self, code):
        '''Set the code of the AD5693R'''
        # self.twi.write_word(self.addr7, self.dac_reg, swap_endian(code, elementCount = 2))
        self.twi.write_register(addr7=self.addr7, commandCode=self.dac_reg, data=swap_endian(code, elementCount = 2), data_size=16, use_pec=False)
    def _set_gain(self, gain):
        if gain == 2:
            self.gain_code = 0x0800
        elif gain == 1:
            self.gain_code = 0x0000
        else:
            raise Exception("AD5693R gain setting should be either 1 or 2.")
        self._update_controlreg()
    def _set_outputz(self, z):
        if z in [0, "0"]:
            self.impedance = 0x0000
        elif z in ["1k", "1K", 1000, 1e3]:
            self.impedance = 0x2000
        elif z in ["100k", "100K", 100000, 1e5]:
            self.impedance = 0x4000
        elif z in ["z", "Z"]:
            self.impedance = 0x6000
        else:
            raise Exception(f'AD5693R impedance setting must be one of: {["0", "1k", "100k", "z"]}')
        self._update_controlreg()
    def _set_voltage(self, voltage):
        '''Set the voltage of the AD5693R'''
        code = self._volts_to_code(voltage)
        self._set_code(code)
    def _code_to_volts(self, code):
        if code > 65535 or code < 0:
            raise Exception(f"AD5693R code: {code} out of range 0 to 65535. Gain = {gain}, Requested voltage = {voltage}.")
        if self.gain_code == 0x0800:
            gain = 2.0
        else:
            gain = 1.0
        voltage = code * gain * self.vref / 65536.0
        return voltage
    def _volts_to_code(self, voltage):
        if self.gain_code == 0x0800:
            gain = 2.0
        else:
            gain = 1.0
        code = int(voltage / gain / self.vref * 65536.0)
        if code > 65535 or code < 0:
            raise Exception(f"AD5693R code: {code} out of range 0 to 65535. Gain = {gain}, Requested voltage = {voltage}.")
        return code
    def _sync_channels(self, channel, value):
        if channel.get_attribute('ch_type') == 'voltage':
            voltage = value
            code = self._volts_to_code(voltage)
        elif channel.get_attribute('ch_type') == 'code':
            code = value
            voltage = self._code_to_volts(code)
        else:
            raise Exception("I'm lost. Ask Dave.")
        for ch in self.get_all_channels_list(): 
            if ch is channel:
                continue 
            try:
                ch_type = ch.get_attribute('ch_type')
            except ChannelAttributeException:
                ch_type = None
            if ch_type == 'voltage':
                ch._set_value(voltage)
            elif ch_type == 'code':
                ch._set_value(code)
            else:
                pass
                #Todo gain channel syncing?
    def add_channel(self, channel_name):
        output = channel(channel_name, write_function=self._set_voltage)
        output.set_attribute('ch_type', 'voltage')
        output.add_write_callback(self._sync_channels)
        return self._add_channel(output)
    def add_channel_code(self, channel_name):
        int_output = integer_channel(channel_name, size=16, write_function=self._set_code)
        int_output.set_attribute('ch_type', 'code')
        int_output.add_write_callback(self._sync_channels)
        return self._add_channel(int_output)
    def add_channel_outputz(self, channel_name):
        output = channel(channel_name, write_function =self._set_outputz)
        return self._add_channel(output)
    def add_channel_gain(self, channel_name):
        output = channel(channel_name, write_function=self._set_gain)
        #TODO - sync up?
        return self._add_channel(output)