from ..lab_core import *
from PyICe.lab_utils.banners import print_banner
from PyICe.lab_utils.eng_string import eng_string
import datetime

class htx9011(scpi_instrument):
    ''' HTX9011 ConfiguratorXT (Steve Martin)
        Breakout/Edge connector board for ATE Bench, with i2c
        Supports 4 types of channels:
        gpio - 10 Channels, Possible values are 0,1(5V),Z (HiZ), P (Weak Pull Up)
        relay - Channels 1-4 and 9-12, correspond to supply numbers, 0 or 1 (1 is supply connected)
        dvcc - Controls I2C/SMBus DVCC voltage
        '''
    def __init__(self, interface_visa, calibrating=False, serializing=False):
        '''Creates a htx9011 object'''
        self._base_name = 'htx9011'
        scpi_instrument.__init__(self,f"HTX9011 {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.tries = 3
        self.gpiox = PCF8574_on_ConfiguratorXT(interface_visa)
        self.gpiox.add_one_channel_per_pin()
        # self.gpiox.add_one_readback_channel_per_pin()
        self.gpio_pins = {1:'PB0',2:'PB1',3:'PB2',4:'PB3',5:'PB4',6:'PB5',7:'PB6',8:'PB7',9:'PD2',10:'PD3',11:'PD4',12:'PD5',13:'PD6',14:'PD7',15:'PE6'}
        self.pwm_pins = {6:'PB5',7:'PB6',8:'PB7'}
        self.interrupts = [2,3,6]
        self.pcints = range(8)
        self.FCLK = 16e6 # crystal frequency
        # self.initialized_pins = []
        # self._write_gpio(list(self.gpio_pins.keys()),len(self.gpio_pins)*'Z') #HiZ all GPIO Pins
        self.pwm_duty_cycle = {}
        self.pwm_frequency = {}
        self.prescale = {}
        self.top = {}
        self.pwm_enable = {}
        self.relay_pins_bypass = {1:'PF1',2:'PF5',3:'PF7',4:'PA2',5:'PA5',6:'PC6',7:'PC5',8:'PC1'}
        self.relay_pins_connect = {1:'NS1',2:'NS2',3:'NS3',4:'NS4',5:'PA6',6:'PA7',7:'PC3',8:'PC2'}
        self.relay_pins_range_H = {1:'PF2',2:'PF4',3:'PA1',4:'PA3',5:'PA4',6:'PC7',7:'PC4',8:'PC0'}
        self.relay_pins_range_M_LB = {1:'PF0',2:'PF3',3:'PF6',4:'PA0',5:'NS5',6:'NS6',7:'NS7',8:'NS8'}
        self.initialized_pins = []
        self._write_gpio(list(self.gpio_pins.keys()),len(self.gpio_pins)*'Z') #HiZ all GPIO Pins
        if not self.valid_serialnum() and not serializing:
            if datetime.datetime.now() > datetime.datetime(2021,1,31):
                print_banner("ERROR: ConfiguratorXT is not serialized!", "Please serialize it to continue.")
                exit()
            else:
                print_banner("WARNING: ConfiguratorXT is not serialized!", "Please serialize it before January 31, 2021.")
        #self.check_calibration_valid(calibrating)
        # self.add(self.gpiox)
    def _disable_i2c(self):
        write_str = ':I2C:PORT:DISable;'
        self.get_interface().write(write_str)
    def add_channel_dvcc(self,channel_name):
        '''Adds a channel controlling the dvcc voltage'''
        dvcc = channel(channel_name,write_function=self._set_dvcc)
        dvcc.set_write_delay(0.2)
        return self._add_channel(dvcc)
    def add_channel_relay_bypass(self,channel_name,relay_number):
        '''Adds a relay bypass channel,
            channel_name is the name of the channel,
            relay_number is the number of the relay
            valid bypass relays are 1-8'''
        if relay_number not in self.relay_pins_bypass:
            raise Exception(f'Invalid relay number {relay_number}')
        if self.relay_pins_bypass[relay_number] in self.initialized_pins:
            raise Exception(f'relay number {relay_number} already used in another channel!')
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_relay_bypass(relay_number,data))
        new_channel.set_description(f'Closes or opens bypass relay of channel {relay_number} when written to True or False, respectively')
        new_channel.add_preset('True', True, f"Close bypass relay of channel {relay_number}.")
        new_channel.add_preset('False', False, f"Open bypass relay of channel {relay_number}.")
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append(self.relay_pins_bypass[relay_number])
        return new_channel
    def add_channel_master_relay_bias(self,channel_name):
        '''Adds a Master Relay Arm Channel'''
        new_channel = integer_channel(channel_name, size=1, write_function=lambda value: self._write_master_relay_bias(value))
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append("PE3")
        return new_channel
    def add_channel_relay_connect(self,channel_name,relay_number):
        '''Adds a relay connect channel,
            channel_name is the name of the channel,
            relay_number is the number of the relay
            valid connect relays are 1-8'''
        if relay_number not in self.relay_pins_connect:
            raise Exception(f'Invalid relay number {relay_number}')
        if self.relay_pins_connect[relay_number] in self.initialized_pins:
            raise Exception(f'relay connect{relay_number} already used in another channel!')
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_relay_connect(relay_number,data))
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append(self.relay_pins_connect[relay_number])
        return new_channel
    def add_channel_relay_range_H(self,channel_name,relay_number):
        '''Adds a relay range_H channel,
            channel_name is the name of the channel,
            relay_number is the number of the relay
            valid range relays are 1-8'''
        if relay_number not in self.relay_pins_range_H:
            raise Exception(f'Invalid relay range_H{relay_number}')
        if self.relay_pins_range_H[relay_number] in self.initialized_pins:
            raise Exception(f'relay range_H{relay_number} already used in another channel!')
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_relay_range_H(relay_number,data))
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append(self.relay_pins_range_H[relay_number])
        return new_channel
    def add_channel_relay_range_M_LB(self,channel_name,relay_number):
        '''Adds a relay range_M_LB channel,
            channel_name is the name of the channel,
            relay_number is the number of the relay
            valid range relays are 1-8'''
        if relay_number not in self.relay_pins_range_M_LB:
            raise Exception(f'Invalid relay range_M_LB{relay_number}')
        if self.relay_pins_range_M_LB[relay_number] in self.initialized_pins:
            raise Exception(f'relay range_M_LB{relay_number} already used in another channel!')
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_relay_range_M_LB(relay_number,data))
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append(self.relay_pins_range_M_LB[relay_number])
        return new_channel
    def add_channel_range(self, channel_name, channel_number):
        if channel_number not in [1,2,3,4,5,6,7,8]:
            raise Exception(f'\n\nInvalid channel number:{channel_number}, needs to be in 1-8 for the ConfiguratorXT.\n\n')
        new_channel = channel(channel_name, write_function=lambda data:  self._set_range(channel_number, data))
        new_channel.add_preset("OPEN", f"Open all the relays of channel {channel_number}.")
        new_channel.add_preset("5mA", f"Set channel {channel_number} to 5mA Range.")
        new_channel.add_preset("500mA", f"Set channel {channel_number} to 500mA Range.")
        new_channel.add_preset("10A", f"Set channel {channel_number} to 10A Range.")
        new_channel.set_attribute('channel_number', channel_number)
        self._add_channel(new_channel)
        return new_channel
    def add_channel_isense_remapper(self, channel_name, channel_number, vmeter_high_range_channel, vmeter_med_range_channel, vmeter_low_range_channel, meter_ch_group):
        '''Facilitates remapping current sense channels based on range selected on ConfiguratorXT'''
        readback_channel = channel(channel_name, read_function=None) #get reference to this channel into read function to get attributes
        readback_channel.set_write_access(False)
        range_channel = self.add_channel_range(f'{channel_name}_range', channel_number)
        range_channel.write("OPEN")
        range_channel.set_attribute('readback_channel', readback_channel)
        readback_channel._read = lambda: self._read_range_v(readback_channel)
        readback_channel.set_attribute('channel_number', channel_number)
        readback_channel.set_attribute('range_channel', range_channel)
        readback_channel.set_attribute('vmeter_high_range_channel', vmeter_high_range_channel)
        readback_channel.set_attribute('vmeter_med_range_channel', vmeter_med_range_channel)
        readback_channel.set_attribute('vmeter_low_range_channel', vmeter_low_range_channel)
        readback_channel.set_description(self.get_name() + ': ' + self.add_channel_isense_remapper.__doc__)
        readback_channel.set_category(vmeter_high_range_channel.get_category())
        readback_channel.set_display_format_function(function = lambda float_data: f"{eng_string(float_data, fmt=':3.6g',si=True)}A")
        return meter_ch_group._add_channel(readback_channel) #Move channel to 3497x thread
    def _read_range_v(self, readback_channel):
        if readback_channel.get_attribute('range_channel').read().upper() == "OPEN":
            return None
        elif readback_channel.get_attribute('range_channel').read().upper() == "5MA":
            return readback_channel.get_attribute('vmeter_low_range_channel').read()
        elif readback_channel.get_attribute('range_channel').read().upper() == "500MA":
            return readback_channel.get_attribute('vmeter_med_range_channel').read()
        elif readback_channel.get_attribute('range_channel').read().upper() == "10A":
            return readback_channel.get_attribute('vmeter_high_range_channel').read()
        else:
            raise Exception("ConfiguratorXT: I shouldn't be here!")
    def _set_range(self, relay, irange):
        '''configures a channel's relays for a particular current range.
        Upon a range change the relays are switched such that the circuit remains closed using the bypass relay'''
        if relay not in range(1, 8+1):
            raise Exception(f'ConfiguratorXT: Invalid relay number:{relay}. Needs to be 1-8.')
        if irange.upper() == "10A":
            self._write_relay_bypass(relay_number=relay, value=True)          # Redundant path for high current mode - technically not needed
            self._write_relay_connect(relay_number = relay, value=True)       # Wraps the sense line around the sense resistors
            self._write_relay_range_H(relay_number=relay, value=True)         # Connects the force line (officially)
            self._write_relay_range_M_LB(relay_number=relay, value=False)     # This is a don't care in this mode
        elif irange.upper() == "500MA":
            self._write_relay_bypass(relay_number=relay, value=True)          # Keep the conducting path to prevent bad things
            self._write_relay_connect(relay_number = relay, value=True)       # Wraps the sense line around the sense resistors
            self._write_relay_range_H(relay_number=relay, value=False)        # Selects the path that allows the two low ranges
            self._write_relay_range_M_LB(relay_number=relay, value=False)     # Sets the medium range relay for medium mode
            self._write_relay_bypass(relay_number=relay, value=False)         # Remove the bypass line that prevented glitches in the previous changes
        elif irange.upper() == "5MA":
            self._write_relay_bypass(relay_number=relay, value=True)          # Keep the conducting path to prevent bad things
            self._write_relay_connect(relay_number = relay, value=True)       # Wraps the sense line around the sense resistors
            self._write_relay_range_H(relay_number=relay, value=False)        # Selects the path that allows the two low ranges
            self._write_relay_range_M_LB(relay_number=relay, value=True)      # Sets the low range relay for low mode
            self._write_relay_bypass(relay_number=relay, value=False)         # Remove the bypass line that prevented glitches in the previous changes
        elif irange.upper() == "OPEN":
            # self._write_relay_bypass(relay_number=relay, value=True)        # Maybe read state and transition through bypass if anybody else is on
            self._write_relay_connect(relay_number = relay, value=False)      # Wraps the sense line around the sense resistors
            self._write_relay_range_H(relay_number=relay, value=False)        # Selects the path that allows the two low ranges
            self._write_relay_range_M_LB(relay_number=relay, value=False)     # Don't care
            self._write_relay_bypass(relay_number=relay, value=False)         # Do this last to preven blowing up low current channel if current flow
        else:
            raise Exception(f'ConfiguratorXT: Invalid range setting:{range}. Needs to be one of OPEN, 5mA, 500mA, 10A')
    def add_channel_gpio(self, channel_name, gpio_list, output=True, pin_state="Z", integer=False):
        '''Adds a GPIO channel, can be a single bit or a bus of bits
            channel_name is the name of the channel
            gpio pins is either a single integer for a single bit or a list of integers ordered msb to lsb
            valid gpio_numbers are 1-10,
            valid settings are [{integer},'z','Z','p','P','H','L']
            if integer channel (bus), ZPHL won't work.
        '''
        gpio_list = gpio_list if isinstance(gpio_list, list) else [gpio_list]
        for gpio_pin in gpio_list:
            if gpio_pin not in self.gpio_pins:
                raise Exception(f'Invalid gpio {gpio_pin}')
            if self.gpio_pins[gpio_pin] in self.initialized_pins:
                # print(f"HTX9011 Warning: Non GPIO pin {gpio_pin} being redefined as a GPIO pin.")
                raise Exception(f'gpio number {gpio_pin} already used in another channel!')
            self.initialized_pins.append(self.gpio_pins[gpio_pin])
        if output:
            if integer:
                new_channel = integer_channel(name=channel_name, size=len(gpio_list), write_function=lambda value: self._write_gpio(gpio_list,value))
            else:
                new_channel = channel(channel_name,write_function=lambda value: self._write_gpio(gpio_list,value))
            new_channel.write(pin_state)
            self._add_readback_channel(channel_name, gpio_list)
        else: # It must be an Input
            if integer:
                new_channel = integer_channel(name=channel_name, size=len(gpio_list), read_function=lambda: self._read_pins_values(gpio_list))
            else:
                new_channel = channel(channel_name,read_function=lambda: self._read_pins_values(gpio_list))
            self._write_gpio(gpio_list, "Z") # Because you said it was an input
            # DJS TODO Z will need special handling for integer channels!
        return self._add_channel(new_channel)
    def _add_readback_channel(self, channel_name, gpio_list):
        new_channel = channel(f"{channel_name}_readback", read_function=lambda: self._read_pins_values(gpio_list))
        return self._add_channel(new_channel)
    def _set_dvcc(self, voltage):
        self.get_interface().write(f'VOLT:DVCC {voltage}')
    # def resync(self):
        # self._twi.init_i2c()
    def _clean_value(self,value):
        if (value == True or value == 1 or value == '1'):
            value = 1
        elif (value == False or value == 0 or value == '0'):
            value = 0
        else:
            raise Exception(f'\n\nCan not parse htx9011 input: {value}\n\n')
        return value
    def _pin_response_valid(self,ret_str):
        if (len(ret_str) != 6):
            print(f"HTX9011: Pin read or write response length incorrect. Should have been 6 characters, got {len(ret_str)} characters.")
            return False
        if (ret_str[4:] != '\r\n'):
            print(f"HTX9011: Pin read or write response improperly terminated. Should have ended with CRLF but didn't.")
            return False
        return True
    def _write_pin(self, pin, value, tries=0, ret_str=None):
        if pin[:2] == "NS":
            # This is a GPIO Expander pin.
            self.gpiox[pin].write(value)
            return
        # Otherwise, assume a regular MCU GPIO pin.
        if tries == self.tries:
            raise Exception(f"Failed to write pin {pin} to {value} after {tries} tries. Return value is {ret_str}.")
        if value not in [0,1,'z','Z','p','P','H','L']:
            raise Exception(f'HTX9011: Bad value requested for pin setting: {value}. Must be one of: [0,1,z,Z,p,P,H,L].')
        #set the pin and read back its state to make sure there were no usb communication problems
        value_str = str(value).upper()
        if value == 1:
            value_str = "H"
        elif value == 0:
            value_str = "L"
        write_str = f':SETPin:{value_str}(@{pin});:SETPin?(@{pin});'
        self.get_interface().write(write_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str) or (ret_str[2] != str(value).upper()):
            self._write_pin(pin, value, tries+1, ret_str)
            
    def _write_pins(self, pins, values):
        year,month,day = [int(value) for value in self.get_firmware_version().split(".")]
        assert year >=2024 and month >=11 and day >=6, "GPIO pin atomic handling requires HTX9011 firmware >= 2024.11.06"
        assert len(pins) == len(values)
        for pin in pins:
            assert pin[:2] != 'NS', "oops, wrong SCPI path. Contact PyICe developers."
        pinvals = ','.join([f'{pins[i]}={values[i]}' for i in range(len(pins))])
        write_str = f':SETPin (@{pinvals});'
        self.get_interface().write(write_str)
        # resp checking removed
        #ret_str = self.get_interface().readline()
        #if not self._pin_response_valid(ret_str) or (ret_str[2] != str(value).upper()):
        #    self._write_pin(pin, value, tries+1, ret_str)
    def _read_pin_setting(self,pin, tries=0, ret_str=None):
        if tries == self.tries:
            raise Exception(f"HTX9011: Failed to read pin: {pin} after {tries} tries. Return value is {ret_str}.")
        read_str = f':SETPin?(@{pin});'
        self.get_interface().write(read_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str):
            # self.resync()
            self._read_pin_setting(pin, tries+1, ret_str)
        try:
            ret_val = int(ret_str[2])
        except:
            ret_val = ret_str[2]
        return ret_val
    def _read_pin_value(self,pin,tries=0, ret_str=None):
        if tries == self.tries:
            raise Exception(f"HTX9011: Failed to read pin: {pin} after {tries} tries. Return value is {ret_str}.")
        read_str = f':PINVal?(@{pin});'
        self.get_interface().write(read_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str):
            # self.resync()
            return self._read_pin_value(pin, tries+1, ret_str)
        try:
            ret_val = int(ret_str[2])
        except:
            ret_val = ret_str[2]
        return ret_val
    def _to_bit_list(self,value,out_length):
        out_list = None
        if isinstance(value, bool):
            if value:
                out_list = [1]
            else:
                out_list = [0]
        if isinstance(value, float):
            if int(value) == value:
                value = int(value)
            else:
                raise Exception(f"HTX9011: Could not convert requested pin value to a proper integer.")
        if isinstance(value, int):
            value = bin(value).lstrip('0b').rjust(out_length,'0')
        if isinstance(value,str):
            out_list = []
            value = value.upper()
            for char in value:
                if char in ['T','H','1']:
                    char = 1
                if char in ['F','L','0']:
                    char = 0
                out_list.append(char)
            for item in out_list:
                if item not in [1,0,'P','Z']:
                    raise Exception(f"HTX9011: Bad value sent to pin list: {out_list}. All values must be one of [1,0,P,Z].")
        if out_list == None:
            raise Exception(f"HTX9011: Nonexistent list (Python None) sent to Configurator pin list.")
        while len(out_list) < out_length:
            out_list.reverse()
            out_list.append(0)
            out_list.reverse()
        while len(out_list) > out_length:
            out_list.reverse()
            out_list.pop()
            out_list.reverse()
        return out_list
    def _from_bit_list(self,bit_list):
        #attempt to build an integer from the bit list, otherwise return a string
        out = 0
        for value in bit_list:
            try:
                out *= 2
                out += int(value)
            except:
                out = None
                break
        if out == None:
            out = ""
            for value in bit_list:
                out += str(value)
        return out
    def _write_gpio(self,gpio_list,value):
        #no gpio pins are attached to bus expander, so redirecting all to new scpi path to write multiple pins.
        bit_list = self._to_bit_list(value,len(gpio_list))
        return self._write_pins([self.gpio_pins[p] for p in gpio_list], bit_list)
    def _write_relay_bypass(self,relay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for relay: {value}')
        self._write_pin(self.relay_pins_bypass[relay_number],value)
        time.sleep(0.1)
    def _write_relay_connect(self,relay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f"Bad value for connect{relay_number} relay: {value}")
        self._write_pin(self.relay_pins_connect[relay_number],value)
        time.sleep(0.1)
    def _write_relay_range_H(self,relay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for range_H{relay_number} relay: {value}')
        self._write_pin(self.relay_pins_range_H[relay_number],value)
        time.sleep(0.1)
    def _write_relay_range_M_LB(self,relay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for range_M_LB{relay_number} relay: {value}')
        self._write_pin(self.relay_pins_range_M_LB[relay_number],value)
        time.sleep(0.1)
    def _write_master_relay_bias(self,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception('Bad value for ConfiguratorXT Master Relay')
        self._write_pin("PE3",value)
        time.sleep(0.1)
    def _read_pins_values(self,pins,invert=False):
        #todo - read all pins at once for with single SCPI exchange for GPIO, rather than iterating.
        pin_names = [self.gpio_pins[pin] for pin in pins]
        return self._read_pins_generic(pin_names,invert=invert,function=self._read_pin_value)
    def _read_pins_generic(self,pins,invert=False,function=None):
        if not isinstance(pins, list):
            pins = [pins]
        output = []
        for pin in pins:
            value = function(pin)
            if invert:
                if value == 1:
                    value = 0
                elif value == 0:
                    value = 1
            output.append(value)
        return self._from_bit_list(output)
    def set_all_relays_bypass(self,value):
        for relay in self.relay_pins_bypass:
            self._write_relay_bypass(relay,value)
    def set_all_relays_connect(self,value):
        for relay in self.relay_pins_connect:
            self._write_relay_connect(relay,value)
    def set_all_relays_range_H(self,value):
        for relay in self.relay_pins_range_H:
            self._write_relay_range_H(relay,value)
    def set_all_relays_range_M_LB(self,value):
        for relay in self.relay_pins_range_M_LB:
            self._write_relay_range_M_LB(relay,value)
    def _rip(self,write_list):
        '''write_list format [(pin,value),(pin,value)....]
        this function uses raw pin names and builds a single query sting without readback for maximum speed
        there is currently no way to connect this with channels so the pin is the raw pin name like PB1 etc'''
        write_str = ''
        for pin,value in write_list:
            if value not in [0,1,'z','Z','p','P','H','L']:
                raise Exception(f'Bad value for pin: {value}')
            #set the pin and read back its state to make sure there were no usb communication problems
            value_str = str(value).upper()
            if value == 1:
                value_str = "H"
            elif value == 0:
                value_str = "L"
            write_str += ':SETPin:%s(@%s);' % (value_str,pin)
        self.get_interface().write(write_str)
    def add_channel_pwm(self, channel_name, pin):
        if pin not in self.pwm_pins:
            raise Exception(f"\n\nInvalid HTX9011 PWM pin number {pin}. Must be one of: {self.pwm_pins}\n\n")
        if self.pwm_pins[pin] in self.initialized_pins:
            print(f"\n\nHTX9011 Warning: Non PWM pin {pin} being redefined as a PWM pin.\n\n")
        else:
            self.initialized_pins.append(self.pwm_pins[pin])
        self._add_channel_pwm_frequency(channel_name+"_frequency", pin)
        self._add_channel_pwm_duty_cycle(channel_name+"_dutycycle", pin)
        self._add_channel_pwm_enable(channel_name+"_enable", pin)
        self._add_channel_pwm_freq_readback(channel_name+"_freq_readback", pin)
        self.pwm_duty_cycle[pin] = 0.5
        self.pwm_frequency[pin] = 1e6
        self.pwm_enable[pin] = 0
        self._update_pwm_channel(pin)
    def _add_channel_pwm_frequency(self, channel_name, pin):
        def set_pwm_frequency(value):
            flow    = 16e6/1024/65536
            fhigh   = 8e6 # datasheet, fmax = fclkio / 2
            if value < flow or value > fhigh:
                raise Exception(f"\n\nInvalid HTX9011 frequency {value}. Must be between {flow} and {fhigh} Hz.\n\n")
            self.pwm_frequency[pin] = value
            self._update_pwm_channel(pin)
        new_channel = channel(channel_name, write_function=set_pwm_frequency)
        self._add_channel(new_channel)
    def _add_channel_pwm_duty_cycle(self, channel_name, pin):
        def set_pwm_duty_cycle(value):
            self.pwm_duty_cycle[pin] = value
            self._update_pwm_channel(pin)
        new_channel = channel(channel_name, write_function=set_pwm_duty_cycle)
        self._add_channel(new_channel)
    def _add_channel_pwm_enable(self, channel_name, pin):
        def set_pwm_enable(value):
            value = self._clean_value(value)
            if value not in [0,1]:
                raise Exception(f'\n\nBad value for HTX9011 pwm_enable: {value}. Try one of: 0,"0",False,1,"1",True.\n\n')
            self.pwm_enable[pin] = value
            self._update_pwm_channel(pin)
        new_channel = channel(channel_name, write_function=set_pwm_enable)
        new_channel.add_preset("1", "Enables the pwm mode for this pin")
        new_channel.add_preset("0", "Disables the pwm mode for this pin")
        self._add_channel(new_channel)
    def _add_channel_pwm_freq_readback(self, channel_name, pin):
        def compute_f(pin):
            return self.FCLK / float(self.prescale[pin]) / float(1 + self.top[pin])
        new_channel = channel(channel_name, read_function = lambda: compute_f(pin))
        self._add_channel(new_channel)
    def _update_pwm_channel(self, pin):
        prescale_list = [1,8,64,256,1024]
        for prescale_choice in prescale_list[::-1]:
            top = int(round(self.FCLK / self.pwm_frequency[pin] / prescale_choice - 1))
            if top <= 65535 and top >= 0:
                self.prescale[pin] = prescale_choice
        self.top[pin] = int(round(self.FCLK / self.pwm_frequency[pin] / self.prescale[pin] - 1))
        compare = int(self.pwm_duty_cycle[pin] * self.top[pin])
        if self.pwm_enable[pin] == 1:
            self.get_interface().write(f'PWM:PREScale {int(self.prescale[pin])}')
            self.get_interface().write(f'PWM:TOP {self.top[pin]}')
            self.get_interface().write(f'PWM:COMPare ({self.pwm_pins[pin]},{compare})')
            self.get_interface().write(f'PWM:MODE ({self.pwm_pins[pin]},CLEAR)')
        else:
            self.get_interface().write(f'PWM:MODE ({self.pwm_pins[pin]},DISABLE)')
    def add_channel_servo(self,channel_name,servo_number):
        if servo_number not in self.pwm_pins:
            raise Exception(f"\n\nInvalid HTX9011 servo pin number {servo_number}.\n\n")
        if self.pwm_pins[servo_number] in self.initialized_pins:
            print(f"\n\nHTX9011 Warning: Non Servo pin {self.pwm_pins[servo_number]} being redefined as a Servo pin.\n\n")
        new_channel = channel(channel_name,write_function=lambda value: self._write_servo(servo_number,value))
        self._write_servo_enable(servo_number, True)
        self._add_channel(new_channel)
        self.initialized_pins.append(self.pwm_pins[servo_number])
        return new_channel
    def add_channel_servo_enable(self,channel_name,servo_number):
        if servo_number not in self.pwm_pins:
            raise Exception(f"\n\nHTX9011 Invalid servo pin number {servo_number}\n\n")
        new_channel = channel(channel_name,write_function=lambda value: self._write_servo_enable(servo_number,value))
        return self._add_channel(new_channel)
    def add_channel_interrupt(self, channel_name, interrupt_number):
        def _write_interrupt_control_channel(ch, value):
            command_list = ["DISABLE","ANYEDGE","RISING","FALLING"]
            if value.upper() not in command_list:
                raise Exception(f'\n\nBad value for HTX9011 interrupt channel {ch.get_attribute("INTERRUPT_NUMBER")}: {value.upper()}. Only {command_list} allowed.\n\n')
            self.get_interface().write(f'INTErrupt:INT{ch.get_attribute("INTERRUPT_NUMBER")} {value.upper()}')
            # Any mode change clears software accumulator. Should it?
            # Does mode change clear hardware accumulator? Should it? Should Python do a sacrificial read here????
        def _read_interrupt_count(ch):
            new_count = int(self.get_interface().ask(f'INTErrupt:INT{ch.get_attribute("INTERRUPT_NUMBER")}:COUNt?'))
            ch.set_attribute('INTERRUPT_COUNT_ACCUM', new_count + ch.get_attribute('INTERRUPT_COUNT_ACCUM'))
            return ch.get_attribute('INTERRUPT_COUNT_ACCUM')
        def _write_interrupt_count(ch, value):
            # TODO Warn if count is written while enabled? No, for now....
            previous_count = _read_interrupt_count(ch) # Flush
            # Discard previous_count. Can't really return it from this context.
            ch.set_attribute('INTERRUPT_COUNT_ACCUM', value)
        if interrupt_number not in self.interrupts:
            raise Exception(f"\n\nHTX9011 Invalid interrupt number {interrupt_number}. Only valid interrupts are: {self.interrupts}.\n\n")
        control_channel = channel(channel_name, write_function=lambda value: None) #temporary
        control_channel._write = lambda value: _write_interrupt_control_channel(control_channel, value) #self-reference
        control_channel.add_preset('DISABLE', f"Disable interrupt {channel_name}.")
        control_channel.add_preset('ANYEDGE', f"Set interrupt {channel_name} to count any detected edge.")
        control_channel.add_preset('RISING',  f"Set interrupt {channel_name} to detect all rising edges.")
        control_channel.add_preset('FALLING', f"Set interrupt {channel_name} to detect all falling edges.")
        control_channel.set_attribute('INTERRUPT_NUMBER', interrupt_number)
        self._add_channel(control_channel)
        readback_channel = channel(name=f"{channel_name}_count", read_function=lambda : None) #temporary
        readback_channel._read = lambda : _read_interrupt_count(readback_channel) #self-reference
        readback_channel._write = lambda v: _write_interrupt_count(readback_channel, v) #self-reference
        readback_channel.set_write_access(True)
        readback_channel.set_attribute('INTERRUPT_NUMBER', interrupt_number)
        readback_channel.set_attribute('INTERRUPT_COUNT_ACCUM', 0)
        self._add_channel(readback_channel)
        # Interlace the pair
        readback_channel.set_attribute('CONTROL_CHANNEL', control_channel)
        control_channel.set_attribute('READBACK_CHANNEL', readback_channel)
        control_channel.write('DISABLE')
        return control_channel # omits readback channel !?
    def add_channel_pcint(self, channel_name, pcint_number):
        '''Control channel for each PCINT. Silently creates captured value channel.'''
        def _write_pcint_control_channel(pcint_number, value):
            command_list = ["DISABLE","ANYEDGE"]
            if value.upper() not in command_list:
                raise Exception(f'\n\nBad value for HTX9011 PCINT channel {pcint_number}: {value.upper()}. Only {command_list} allowed.\n\n')
            self.get_interface().write(f'INTErrupt:PCINT{pcint_number} {value.upper()}')
        def _read_pcint_count(ch):
            new_count = int(self.get_interface().ask(f'INTErrupt:PCINT:COUNt?'))
            ch.set_attribute('INTERRUPT_COUNT_ACCUM', new_count + ch.get_attribute('INTERRUPT_COUNT_ACCUM'))
            return ch.get_attribute('INTERRUPT_COUNT_ACCUM')
        def _write_pcint_count(ch, value):
            previous_count = _read_pcint_count(ch) # Flush
            ch.set_attribute('INTERRUPT_COUNT_ACCUM', value)
        def _read_pcint_captured_value(ch):
            result = self.get_interface().ask('INTErrupt:PCINT:GETAll?')
            return (int(result) >> ch) &  1
        def _write_pcint_capture(value):
            value = value.upper()
            if value in ["ARM", ""]:
                reading = self.get_interface().ask(f'INTErrupt:PCINT:CAPTure? {value}')
                print(f"Bit Pos : 76543210")
                print(f"reading = {int(reading):08b}")
                print("The above is a debug output until PyICe-developers@analog.com can take a look at this.")
            else:
                raise Exception(f'\n\nBad value for HTX9011 PCINT channel capture command: {value}. Only ARM or "" allowed.\n\n')
            return
        def _read_capture_status():
            return self.get_interface().ask('INTErrupt:PCINT:CAPTure?')
        def _read_enabled_pcints():
            return int(self.get_interface().ask('INTErrupt:PCINT:PCINTS?'))
        if pcint_number not in self.pcints:
            raise Exception(f"\n\nHTX9011 Invalid interrupt number {pcint_number}. Only valid PCINTS are: {self.pcints}.\n\n")
        control_channel = channel(channel_name, write_function=lambda value: _write_pcint_channel(pcint_number, value))
        control_channel.add_preset('DISABLE', f"Disable interrupt {channel_name}.")
        control_channel.add_preset('ANYEDGE', f"Set interrupt {channel_name} to count all rising and falling edges.")
        control_channel.set_attribute('INTERRUPT_NUMBER', pcint_number)
        self._add_channel(control_channel)
        readback_channel = channel(name=f'{channel_name}_count', read_function=lambda : None)
        readback_channel._read = lambda : _read_pcint_count(readback_channel) #self-reference
        readback_channel._write = lambda v: _write_pcint_count(readback_channel, v) #self-reference
        readback_channel.set_write_access(True)
        readback_channel.set_attribute('INTERRUPT_NUMBER', pcint_number)
        self._add_channel(readback_channel)
        capture_channel = channel(name=f"{channel_name}_capture_control", write_function=lambda : None) #temporary
        capture_channel._write = lambda : _write_pcint_capture(pcint_number)
        capture_channel.add_preset('ARM', f"Arm the {channel_name} channel.")
        capture_channel.set_attribute('INTERRUPT_NUMBER', pcint_number)
        self.add_channel(capture_channel)
        capture_status_channel = channel(name=f'{channel_name}_capture_status', read_function=lambda : None)
        capture_status_channel._read = lambda : _read_capture_status()
        capture_status_channel.set_attribute('INTERRUPT_NUMBER', pcint_number)
        self.add_channel(capture_status_channel)
        enabled_pcints_channel = channel(name=f"{channel_basename}_enabled_pcints", read_function=lambda : None)
        enabled_pcints_channel._read = lambda : _read_enabled_pcints()
        enabled_pcints_channel.set_attribute('INTERRUPT_NUMBER', pcint_number)
        self.add_channel(enabled_pcints_channel)
        # Interlace the MAIN pair
        readback_channel.set_attribute('CONTROL_CHANNEL', control_channel)
        control_channel.set_attribute('READBACK_CHANNEL', readback_channel)
        control_channel.write('DISABLE')
        return control_channel

    def _write_servo_enable(self,servo_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'\n\nBad value for HTX9011 servo_enable: {value}.\n\n')
        if value:
            self.get_interface().write('PWM:TOP 39999')
            self.get_interface().write('PWM:PREScale 8')
            self.get_interface().write(f'PWM:COMPare ({self.pwm_pins[servo_number]},3000)')
            self.get_interface().write(f'PWM:MODE ({self.pwm_pins[servo_number]},CLEAR)')
        else:
            self.get_interface().write(f'PWM:MODE ({self.pwm_pins[servo_number]},DISABLE)')
    def _write_servo(self,servo_number,value):
        value = float(value)
        if value >= 1.51 or value <= -0.01:
            raise Exception(f'\n\nBad value for HTX9011 servo: {value}.\n\n')
        self.get_interface().write(f'PWM:COMPare ({self.pwm_pins[servo_number]},{value*2000+2000})')
    def get_system_version(self):
        '''This just returns the SCPI version:1999.0'''
        return self.get_interface().ask("SYSTem:VERSion?")
    def get_firmware_version(self):
        idnstr = self.get_interface().ask("*IDN?")
        return idnstr.split(",")[3]
    def is_calibrateable(self):
        year,month,day = [int(value) for value in self.get_firmware_version().split(".")]
        return datetime.datetime(year, month, day) >= datetime.datetime(2020,11,26)
    def set_serial_number(self, serialnum):
        self.get_interface().write(f"CALibration:BOArdrev {serialnum}")
    def get_serialnum(self):
        return self.get_interface().ask("CALibration:BOArdrev?")
    def valid_serialnum(self):
        serialnum = self.get_serialnum()
        return len(serialnum) == 10 and serialnum.isdigit()
    def get_idn(self):
        return self.get_interface().ask("*IDN?")
    def get_error(self):
        return self.get_interface().ask("SYStem:ERRor?")
    def set_resistor_calibration(self,resistor_number,value):
        try:
            float(value)
        except:
            raise Exception(f"\nHTX9011 - Invalid Calibration Data for resistor number {resistor_number}: {value}")
        self.get_interface().write(f"CALibration:DATA ({resistor_number},{value:0.10e});") # Memory location allows up to 16 digits.
    def get_resistor_calibration(self,resistor_number):
        return float(self.get_interface().ask(f"CALibration:DATA? {resistor_number};"))
    def set_calibration_date(self, now):
        self.get_interface().write(f"CALibration:DATE {now.strftime('%Y-%m-%d')}")
    def get_calibration_date(self):
        datestr = self.get_interface().ask('CALibration:DATE?') #datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            y,m,d = datestr.split('-')
            date = datetime.date(int(y),int(m),int(d))
            return date
        except:
            print(f'\nHTX9011 - Calibration date invalid: {datestr}.')
            return None
    def get_days_since_calibration(self):
        cal_date = self.get_calibration_date()
        if cal_date is not None:
            return (datetime.date.today()-cal_date).days
    def start_bootloader(self):
        self.get_interface().write("SYSTem:RST:BTLOader")
    def check_calibration_valid(self, calibrating):
        cal_duration = 365 #days
        days = self.get_days_since_calibration()
        if days is None and not calibrating:
            raise Exception("Current sense resistor calibration date invalid.  Was board ever calibrated?")
        elif days > cal_duration:
            for i in range(10):
                print("******** HTX9001 Calibration Expired ********")
                print(f"Current sense resistor calibration required every {cal_duration} days.")
                print(f"Calibration last performed {self.get_calibration_date()}.")
                print(f"Calibration overdue by {self.get_days_since_calibration()-cal_duration} days.")
            resp = input("Continue anyway?")
            if not resp.lower().startswith('y'):
                raise Exception(f'HTX9001 Calibration Expired.  Calibration required every {cal_duration} days')
      
from ..lab_core import *

class PCF8574_on_ConfiguratorXT(instrument):
    '''Multi-vendor 8bit I2C GPIO on Configurator XT.
    http://www.ti.com/lit/ds/symlink/pcf8574.pdf'''
    def __init__(self, interface_visa):
        '''Talks to the PCF8574 GPIO expander IC on the ConfiguratorXT via the ConfiguratorXT's VISA interface.
        ConfiguratorXT firmware rev 2019.12.18 or better required.'''
        instrument.__init__(self, 'PCF8574 GPIO expander IC on the ConfiguratorXT')
        self._base_name = 'XT GPIO expander'
        self.add_interface_visa(interface_visa)
        self.valid_pin_names = [f'NS{i}' for i in range(1, 8+1)]
        self.valid_pin_names_set = set(self.valid_pin_names)
        self._cached_port_value = None
    def add_channel_covering_all_pins(self, channel_name):
        new_channel = channel(channel_name, write_function=self.write_port)
        new_channel.set_description("Write a byte value to the 8 GPIO pins of ConfiguratorXT GPIO expander."
                                    "Pin NS1 is forced to the byte's lsb, NS2 outputs the next significant bit, etc., and "
                                    "pin NS8 outputs the msb.")
        return new_channel
    def add_readback_channel_covering_all_pins(self, channel_name):
        new_channel = channel(channel_name, read_function=self.read_port)
        new_channel.set_description("Reads the state of the 8 GPIO pins of the ConfiguratorXT GPIO expander. "
                                    "The returned byte's lsb is pin NS1's logic state. The returned byte's msb is pin NS8's state. "
                                    "The return type is an integer between 0 and 255 inclusive.")
    def add_one_channel_per_pin(self, channel_names=None):
        """Takes a list of 8 channel names and creates corresponding channels to write to pins NS1 thru NS8.
        The first channel writes NS1, the second NS2, etc., and the eighth channel writes NS8.
        If no channel names list given, defaults to creating channels NS1 thru NS8."""
        if channel_names is None:
            channel_names = self.valid_pin_names
        assert isinstance(channel_names, list)
        assert len(channel_names) == len(self.valid_pin_names)  # i.e. 8 for the PCF8574 on the ConfiguratorXT
        for pin_name, channel_name in zip(self.valid_pin_names, channel_names):
            new_channel = channel(channel_name, write_function=self.make_write_function(pin_name))
            new_channel.set_description(f"Write PCF8574 GPIO expander pin {pin_name} to logic low or high")
            self._add_channel(new_channel)
    def add_one_readback_channel_per_pin(self, channel_names=None):
        """Takes a list of 8 channel names and creates corresponding channels to read from pins NS1 thru NS8.
        The first channel reads NS1, the second NS2, etc., and the eighth channel reads NS8.
        If no channel names list is given, defaults to creating channels NS1_readback thru NS8_readback."""
        if channel_names is None:
            channel_names = [f"{pin_name}_readback" for pin_name in self.valid_pin_names]
        assert isinstance(channel_names, list)
        assert len(channel_names) == len(self.valid_pin_names)  # i.e. 8 for the PCF8574 on the ConfiguratorXT
        for pin_name, channel_name in zip(self.valid_pin_names, channel_names):
            if not isinstance(channel_name, str):
                raise ValueError(f"Expected a list of channel names in add_one_readback_channel_per_pin() but got {repr(channel_name)}")
            new_channel = channel(channel_name, read_function=self.make_read_function(pin_name))
            new_channel.set_description(f"Read logic state of ConfiguratorXT GPIO expander pin {pin_name}")
            self._add_channel(new_channel)
    def read_port(self):
        "Return integer representing a byte value, the bits of which correspond to the logic states of NS1 (lsb) through NS8 (msb)."
        resp_str = self.get_interface().ask(b"GPIOX:READ?")
        return int(resp_str, base=16)
    def write_port(self, data8):
        if isinstance(data8, int) and data8 > 0 and data8 <= 255:
            return self.get_interface().write(f"GPIOX:WRI {data8:02x}")
        else:
            raise ValueError(f"Unable to write {repr(data8)} to Configurator XT GPIO expander port. "
                             "Expected integer between 0 and 255 inclusive.")
    def make_write_function(self, pin_name):
        assert pin_name in self.valid_pin_names_set
        def _write_pin(databit):
            bit = None
            if isinstance(databit, str):
                if databit.lower() == "true" or databit.lower().startswith("t"):
                    bit = True
                elif databit.lower() == "false" or databit.lower().startswith("f"):
                    bit = False
            else:
                bit = bool(databit)
            if bit is None:
                raise ValueError(f"Unable to write {repr(databit)} to ConfiguratorXT GPIO expander pin {pin_name}. Expected boolean.")
            # else bit is either True or False, so proceed to set or clear the pin, respectively.
            if bit:
                self.set_pins([pin_name])
            else:
                self.clear_pins([pin_name])
        return _write_pin
    def make_read_function(self, pin_name):
        assert pin_name in self.valid_pin_names_set
        pin_num = int(pin_name[2]) - 1  # 0: NS1, 1: NS2, ..., 7: NS8
        mask = 1 << pin_num
        def _read_pin():
            portval = self.read_port()
            return bool(portval & mask)
        return _read_pin
    def set_pins(self, pin_list):
        "Force the listed pins logic high. Valid pin names are NS1 through NS8."
        self.validate_pin_list(pin_list)
        cmd_str = f'GPIOX:SETP:H? (@{",".join(pin_list)})'
        self.get_interface().ask(cmd_str)
    def clear_pins(self, pin_list):
        "Force the listed pins logic low. Valid pin names are NS1 through NS8."
        self.validate_pin_list(pin_list)
        cmd_str = f'GPIOX:SETP:L? (@{",".join(pin_list)})'
        try:
            value = self.get_interface().ask(cmd_str)
        except Exception as e:
            print("\n\nShouldn't be here but for a wierd timeout. Try typing self.get_interface().ask(cmd_str)")
            breakpoint()
            pass
    def validate_pin_list(self, pin_list):
        "Validates list of pin names. Raises ValueError if invalid pin(s) found."
        unknown_pins = set(pin_list) - self.valid_pin_names_set
        if unknown_pins:
            unknown_pins_str = ", ".join(list(unknown_pins).sort())
            raise ValueError("Called ConfiguratorXT GPIO expander set_pins() "
                             "with non-existent pins {}.\nValid values are: "
                             f'{unknown_pins_str, ", ".join(self.valid_pin_names)}')
        # We get here if all pin names in pin_list are OK.
        return True
        
        
