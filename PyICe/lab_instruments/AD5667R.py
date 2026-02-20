from ..lab_core import *

#################################################
# Immutable Commands (3 bit) Page 23 Datasheet  #
#################################################
COMMAND_OFFSET              = 3
WRITE_DACn                  = 0b000
UPDATE_DACn                 = 0b001
WRITE_DACn_UPDATE_ALL       = 0b010
WRITE_DACn_UPDATE_DACn      = 0b011
POWER_SETTING               = 0b100
RESET                       = 0b101
LDACB_SETTING               = 0b110
VREF_SETTING                = 0b111
#################################################
# S bit (DB22) (1 bit)                          #
#################################################
BYTE_MODE_OFFSET            = 6
TWO_BYTE_MODE               = 0b1
STANDARD_MODE               = 0b0
#################################################
# Internal Addresses (3 bit) Page 23 Datasheet  #
#################################################
DAC_SELECT_OFFSET           = 0
DAC_A_ADDR                  = 0b000
DAC_B_ADDR                  = 0b001
BOTH_DACS                   = 0b111
#################################################
# Dac Enable Enums  DS Figure 65                #
#################################################
DAC_ENABLE_OFFSET           = 0
DAC_A_ENABLE                = 0b01
DAC_B_ENABLE                = 0b10
#################################################
# Power State Settings (DB5/DB4)                #
#################################################
POWER_STATE_OFFSET          = 4
ON                          = 0b00
OFF_ONE_K                   = 0b01
OFF_ONE_HUNDRED_K           = 0b10
OFF_HIZ                     = 0b11
#################################################
# Internal LDACb Settings (DB1/DB0)             #
#################################################
LDAC_DAC_A_SETTING_OFFSET   = 0
LDAC_DAC_B_SETTING_OFFSET   = 1
LDAC_AUTOMATIC              = 1
#################################################
# Reference Settings (DB0)                      #
#################################################
VREF_SETTING_OFFSET         = 0
VREF_OFF                    = 0
VREF_ON                     = 1
#################################################
# Physical Constants                            #
#################################################
VREF                        = 2.5  # MSOP Package Only !!!!! 1.25V in QFN - Hah???
GAIN                        = 2.0
#################################################
# Don't Care                                    #
#################################################
DONT_CARE                   = 0

class AD5667R(instrument):
    '''Analog Devices Dual 16 bit DAC
    http://www.analog.com/en/products/digital-to-analog-converters/da-converters/AD5667R.html'''
    def __init__(self, interface_twi, addr7):
        '''
        addr7 is the 7-bit I²C address of the ADT5667R set by pin strapping.
        ADDR    A1  A0  Full Address    ADDR7
        VDD     0   0   7b0001100       0x0C
        FLOAT   1   0   7b0001110       0x0E
        GND     1   1   7b0001111       0x0F
        '''
        instrument.__init__(self, f'Analog Devices AD5667R Digital to Ananlog Converter at 0x{addr7:X}')
        self._base_name = 'AD5667R'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        self.addr7 = addr7
        self._configure_reference(reference_setting = VREF_ON)
        self._setup_LDAC_mode(dac_a_ldac_setting = LDAC_AUTOMATIC, dac_b_ldac_setting = LDAC_AUTOMATIC)
        self.write_power_state_DAC_A(power_state="Z")
        self.write_power_state_DAC_B(power_state="Z")

    def _write(self, command_code, msb, lsb):
        self.twi.write_register(addr7=self.addr7, commandCode=command_code, data=(lsb << 8) | msb, data_size=16, use_pec=False)

    def _configure_reference(self, reference_setting):
        self._write(command_code    = (STANDARD_MODE << BYTE_MODE_OFFSET) | (VREF_SETTING << COMMAND_OFFSET),
                    msb             = DONT_CARE,
                    lsb             = reference_setting << VREF_SETTING_OFFSET)

    def _setup_LDAC_mode(self, dac_a_ldac_setting, dac_b_ldac_setting):
        self._write(command_code    = (STANDARD_MODE << BYTE_MODE_OFFSET) |  (LDACB_SETTING << COMMAND_OFFSET),
                    msb             = DONT_CARE,
                    lsb             = (dac_b_ldac_setting << LDAC_DAC_B_SETTING_OFFSET) | (dac_a_ldac_setting << LDAC_DAC_A_SETTING_OFFSET))

    def _set_power_state(self, power_state, dac):
        if power_state in [0, "0"]:
            power_mode = ON
        elif power_state in ["1k", "1K", 1000, 1e3]:
            power_mode = OFF_ONE_K
        elif power_state in ["100k", "100K", 100000, 1e5]:
            power_mode = OFF_ONE_HUNDRED_K
        elif power_state in ["z", "Z"]:
            power_mode = OFF_HIZ
        else:
            raise Exception(f'AD5667R: Power setting must be one of: ["0", "1k", "100k", "z"], got: "{power_state}".')
        self._write(command_code    = (STANDARD_MODE << BYTE_MODE_OFFSET) | (POWER_SETTING << COMMAND_OFFSET),
                    msb             = DONT_CARE,
                    lsb             = (power_mode << POWER_STATE_OFFSET) | (dac << DAC_ENABLE_OFFSET))

    def write_power_state_DAC_A(self, power_state):
        self._set_power_state(power_state, dac=DAC_A_ENABLE)

    def write_power_state_DAC_B(self, power_state):
        self._set_power_state(power_state, dac=DAC_B_ENABLE)
 
    def _write_dac_code(self, code, dac):
        selected_dac = DAC_A_ADDR if dac=="A" else DAC_B_ADDR
        self._write(command_code    = (STANDARD_MODE << BYTE_MODE_OFFSET) | (WRITE_DACn_UPDATE_DACn << COMMAND_OFFSET) | (selected_dac << DAC_SELECT_OFFSET),
                    msb             = code >> 8,
                    lsb             = code & 0xFF)

    def _write_dac_A_code(self, code):
        self._write_dac_code(code, dac="A")

    def _write_dac_B_code(self, code):
        self._write_dac_code(code, dac="B")
    
    def _set_dac_A_voltage(self, voltage):
        self._write_dac_A_code(self._volts_to_code(voltage))

    def _set_dac_B_voltage(self, voltage):
        self._write_dac_B_code(self._volts_to_code(voltage))

    def _volts_to_code(self, voltage):
        code = round(voltage / GAIN / VREF * 65536)
        if code > 65535 or code < 0:
            raise Exception(f"AD5667R code: {code} out of range 0 to 65535. Requested voltage was: {voltage}V.")
        return code

    def _code_to_volts(self, code):
        if code > 65535 or code < 0:
            raise Exception(f"AD5667R code: {code} out of range 0 to 65535. Requested voltage was: {voltage}V.")
        return code * GAIN * VREF / 65536

    def add_channel_DAC_A(self, channel_name):
        output = channel(channel_name, write_function=self._set_dac_A_voltage)
        output.set_attribute('ch_type', 'voltage')
        output.add_write_callback(self._sync_channels)
        return self._add_channel(output)

    def add_channel_DAC_B(self, channel_name):
        output = channel(channel_name, write_function=self._set_dac_B_voltage)
        output.set_attribute('ch_type', 'voltage')
        output.add_write_callback(self._sync_channels)
        return self._add_channel(output)

    def add_channel_code_DAC_A(self, channel_name):
        int_output = integer_channel(channel_name, size=16, write_function=self._write_dac_A_code)
        int_output.set_attribute('ch_type', 'code')
        int_output.add_write_callback(self._sync_channels)
        return self._add_channel(int_output)

    def add_channel_code_DAC_B(self, channel_name):
        int_output = integer_channel(channel_name, size=16, write_function=self._write_dac_A_code)
        int_output.set_attribute('ch_type', 'code')
        int_output.add_write_callback(self._sync_channels)
        return self._add_channel(int_output)

    def add_channel_powerstate_DAC_A(self, channel_name):
        powerstate_channel = channel(channel_name, write_function =self.write_power_state_DAC_A)
        powerstate_channel.add_preset('0', 'ON')
        powerstate_channel.add_preset('1k', 'OFF 1kΩ PullDown')
        powerstate_channel.add_preset('100k', 'OFF 100kΩ PullDown')
        powerstate_channel.add_preset('Z', 'OFF Hi Z')
        return self._add_channel(powerstate_channel)

    def add_channel_powerstate_DAC_B(self, channel_name):
        powerstate_channel = channel(channel_name, write_function =self.write_power_state_DAC_B)
        powerstate_channel.add_preset('0', 'ON')
        powerstate_channel.add_preset('1k', 'OFF 1kΩ PullDown')
        powerstate_channel.add_preset('100k', 'OFF 100kΩ PullDown')
        powerstate_channel.add_preset('Z', 'OFF Hi Z')
        return self._add_channel(powerstate_channel)

    def _sync_channels(self, channel, value):
        '''Sync's Voltages and Codes to match each other after changes to either.'''
        if channel.get_attribute('ch_type') == 'voltage':
            voltage = value
            code = self._volts_to_code(voltage)
        elif channel.get_attribute('ch_type') == 'code':
            code = value
            voltage = self._code_to_volts(code)
        else:
            raise Exception("AD5667R Dual Dac driver has confused itself. Contact PyICe-developers@analog.com for more information.")
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
