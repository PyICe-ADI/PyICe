from ..lab_core import *
import datetime

class htx9001(scpi_instrument):
    ''' HTX9001 Configurator Pro (Steve Martin)
        Breakout/Edge connector board for ATE Bench, with i2c
        Supports 4 types of channels:
        gpio - 10 Channels, Possible values are 0,1(5V),Z (HiZ), P (Weak Pull Up)
        test_hook - 5 channels, 1,0 pullup to 12V NO CURRENT LIMIT
        relay - Channels 1-4 and 9-12, correspond to supply numbers, 0 or 1 (1 is supply connected)
        dvcc - Controls I2C/SMBus DVCC voltage
        '''
    def __init__(self,interface_visa,interface_twi, calibrating = False):
        '''Creates a htx9001 object'''
        self._base_name = 'htx9001'
        #work with both serial port strings and pyserial objects
        scpi_instrument.__init__(self,f"HTX9001 {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.add_interface_twi(interface_twi)
        self._twi = interface_twi
        self.tries = 3
        self.test_hook_pins = {1:'PC6',2:'PC7',3:'PD2',4:'PD3',5:'PD4'}
        self.gpio_pins = {1:'PB0',2:'PB1',3:'PB2',4:'PB3',5:'PB4',6:'PB5',7:'PB6',8:'PB7',9:'PD5',10:'PD6'}
        self.relay_pins = {1:'PF4',2:'PD7',3:'PF5',4:'PE6',9:'PF6',10:'PF0',11:'PF7',12:'PF1'}
        self.initialized_pins = []
        self._write_gpio(list(self.gpio_pins.keys()),len(self.gpio_pins)*'Z') #HiZ all GPIO Pins
        self.check_calibration_valid(calibrating)
    def _disable_i2c(self):
        write_str = ':I2C:PORT:DISable;'
        self.get_interface().write(write_str)
    def add_channel_dvcc(self,channel_name):
        '''Adds a channel controlling the dvcc voltage'''
        dvcc = channel(channel_name,write_function=self._set_dvcc)
        dvcc.set_write_delay(0.2)
        return self._add_channel(dvcc)
    def add_channel_relay(self,channel_name,relay_number):
        '''Adds a relay channel,
            channel_name is the name of the channel,
            relay_number is the number of the relay (same number as the supply being switched)
            valid relays are 1-4 and 9-12'''
        if relay_number not in self.relay_pins:
            raise Exception(f"Invalid relay number {relay_number}")
        if self.relay_pins[relay_number] in self.initialized_pins:
            raise Exception(f"relay number {relay_number} already used in another channel!")
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_relay(relay_number,data))
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.2)
        self.initialized_pins.append(self.relay_pins[relay_number])
        return new_channel
    def add_channel_test_hook(self,channel_name,test_hook_number):
        '''Adds a test hook channel,
            channel_name is the name of the channel
            test_hook_number is the number of the test hook (valid test hooks are 1-5'''
        if test_hook_number not in self.test_hook_pins:
            raise Exception(f"Invalid test hook number {test_hook_number}")
        if self.test_hook_pins[test_hook_number] in self.initialized_pins:
            raise Exception(f"test hook number {test_hook_number} already used in another channel!")
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_test_hook(test_hook_number,data))
        self._add_channel(new_channel)
        self.initialized_pins.append(self.test_hook_pins[test_hook_number])
        return new_channel
    def add_channel_gpio(self,channel_name,gpio_list,output=True,pin_state = "Z"):
        '''Adds a GPIO channel, can be a single bit or a bus of bits
            channel_name is the name of the channel
            gpio pins is either a single integer for a single bit or a list of integers ordered msb to lsb
            valid gpio_numbers are 1-10,
            valid settings are [{integer},'z','Z','p','P','H','L']'''
        if not isinstance(gpio_list, list):
            gpio_list = [gpio_list]
        for gpio_pin in gpio_list:
            if gpio_pin not in self.gpio_pins:
                raise Exception(f"Invalid gpio {gpio_pin}")
            if self.gpio_pins[gpio_pin] in self.initialized_pins:
                print(f"HTX9001(A) Warning: Non GPIO pin {gpio_pin} being redefined as a GPIO pin.")
                # raise Exception(f"gpio number {gpio_pin} already used in another channel!")
            self.initialized_pins.append(self.gpio_pins[gpio_pin])
        if output:
            #can't use integer channel because of possible P,Z values.
            new_channel = channel(channel_name,write_function=lambda value: self._write_gpio(gpio_list,value))
            new_channel.write(pin_state)
        else:
            new_channel = channel(channel_name,read_function=lambda: self._read_pins_values(gpio_list))
            self._write_gpio(gpio_list, pin_state)
        return self._add_channel(new_channel)
    def _set_dvcc(self, voltage):
        for i in range(3):
            value = int(max(min(voltage, 5), 0.8) / 5.0 * 63.0) & 0x3F
            try:
                self._twi.send_byte(0x74, value)
                return
            except Exception as e:
                print("HTX9001 Configurator Communication error setting DVCC, retrying....")
                print(e)
                self._twi.resync_communication()
        print("Sorry, couldn't fix it with resync_communication()")
        raise e
    def read_channel_pin(self,channel_name):
        return self.read_channel_generic(channel_name,function=self.read_pins_values)
    def resync(self):
        self._twi.init_i2c()
    def _clean_value(self,value):
        if (value == True or value == 1 or value == '1'):
            value = 1
        elif (value == False or value == 0 or value == '0'):
            value = 0
        else:
            raise Exception(f"Can't parse htx9001 input: {value}")
        return value
    def _pin_response_valid(self,ret_str):
        if (len(ret_str) != 6):
            return False
        if (ret_str[4:] != '\r\n'):
            return False
        return True
    def _write_pin(self,pin,value,tries=0):
        if tries == self.tries:
            raise Exception(f"Failed to write pin {pin} to {value}")
        if value not in [0,1,'z','Z','p','P','H','L']:
            raise Exception(f'Bad value for pin: {value}')
        #set the pin and read back its state to make sure there were no usb communication problems
        value_str = str(value).upper()
        if value == 1:
            value_str = "H"
        elif value == 0:
            value_str = "L"
        write_str = ':SETPin:%s(@%s);:SETPin?(@%s);' % (value_str,pin,pin)
        self.get_interface().write(write_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str) or (ret_str[2] != str(value).upper()):
            self.resync()
            self._write_pin(pin,value,tries+1)
    def _read_pin_setting(self,pin,tries=0):
        if tries == self.tries:
            raise Exception(f"Failed to read pin {pin}")
        read_str = f':SETPin?(@{pin});'
        self.get_interface().write(read_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str):
            self.resync()
            self._read_pin_setting(pin,tries+1)
        try:
            ret_val = int(ret_str[2])
        except:
            ret_val = ret_str[2]
        return ret_val
    def _read_pin_value(self,pin,tries=0):
        if tries == self.tries:
            raise Exception(f"Failed to read pin {pin}")
        read_str = f':PINVal?(@{pin});'
        self.get_interface().write(read_str)
        ret_str = self.get_interface().readline()
        if not self._pin_response_valid(ret_str):
            self.resync()
            return self._read_pin_value(pin,tries+1)
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
                raise Exception(f"Bad data for pins {value}")
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
                    raise Exception(f"Bad data {out_list}")
        if out_list == None:
            raise Exception(f"Bad data for pins {value}")
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
    def _write_test_hook(self,test_hook,value):
        value = self._clean_value(value)
        if value not in [0,1,'z','Z']:
            raise Exception(f'Bad value for test hook: {value}')
        self._write_pin(self.test_hook_pins[test_hook],value)
    def _write_gpio(self,gpio_list,value):
        bit_list = self._to_bit_list(value,len(gpio_list))
        pin_values = list(zip(gpio_list,bit_list))
        for pin_name,pin_value in pin_values:
            self._write_pin(self.gpio_pins[pin_name],pin_value)
    def _write_relay(self,relay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for relay: {value}')
        if value == 0:
            value = 1
        elif value == 1:
            value = 0
        self._write_pin(self.relay_pins[relay_number],value)
    def _read_pins_values(self,pins,invert=False):
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
    def set_resistor_calibration(self,resistor_number,value):
        try:
            float(value)
        except:
            raise Exception("Invalid Calibration Data")
        write_str = f"CAL:DATA ({resistor_number},{value});"
        self.get_interface().write(write_str)
    def get_resistor_calibration(self,resistor_number):
        read_str = f"CAL:DATA?({resistor_number});"
        self.get_interface().write(read_str)
        data = self.get_interface().readline()
        return float(data)
    def get_calibration_date(self):
        datestr = self.get_interface().ask('CAL:DATE?') #datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            y,m,d = datestr.split('-')
            date = datetime.date(int(y),int(m),int(d))
            return date
        except:
            print(f'Board calibration date invalid: {datestr}.')
            return None
    def get_days_since_calibration(self):
        cal_date = self.get_calibration_date()
        if cal_date is not None:
            return (datetime.date.today()-cal_date).days
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
    def set_all_relays(self,value):
        for relay in self.relay_pins:
            self._write_relay(relay,value)
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