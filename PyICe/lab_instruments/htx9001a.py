from ..lab_core import *
from .htx9001 import htx9001
str_encoding = 'latin-1'

## Default str to bytes encoding to use. latin-1 is the simplest encoding -- it requires all characters of a string to
## be amongst Unicode code points 0x000000 - 0x0000ff inclusive, and converts each code point value to a byte. Hence
## if s is a string, then: s.encode('latin-1') == bytes([ord(c) for c in s])

class htx9001a(htx9001):
    ''' HTX9001 Configurator Pro A(Steve Martin)
        Breakout/Edge connector board for ATE Bench, with i2c
        Supports 5 types of channels:
        gpio - 10 Channels, Possible values are 0,1(5V),Z (HiZ), P (Weak Pull Up)
        test_hook - 5 channels, 1,0 pullup to 12V NO CURRENT LIMIT
        relay - Channels 1-12, correspond to supply numbers, 0 or 1 (1 is supply connected)
        ammeter relay - Channels 5-8
        dvcc - Controls I2C/SMBus DVCC voltage
        '''
    def __init__(self,interface_visa, calibrating = False):
        '''Creates a htx9001a object'''
        self._base_name = 'htx9001a'
        scpi_instrument.__init__(self,f"HTX9001A {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.tries = 3
        self.test_hook_pins = {1:'PC6',2:'PC7',3:'PD2',4:'PD3',5:'PD4'}
        self.gpio_pins = {1:'PB0',2:'PB1',3:'PB2',4:'PB3',5:'PB4',6:'PB5',7:'PB6',8:'PB7',9:'PD5',10:'PD6','SCL':'PD0','SDA':'PD1'}
        self.relay_pins = {1:'PF4',2:'PD7',3:'PF5',4:'PE6',5:'PA4',6:'PA6',7:'PA5',8:'PA3',9:'PF6',10:'PF0',11:'PF7',12:'PF1'}
        self.irelay_pins = {5:'PE1',6:'PE0',7:'PF3',8:'PF2'}
        self.pwm_pins = {6:'PB5',7:'PB6',8:'PB7'}
        self.FCLK = 16e6 # crystal frequency
        self.initialized_pins = []
        self._write_gpio(list(self.gpio_pins.keys()),len(self.gpio_pins)*'Z') #HiZ all GPIO Pins
        self.check_calibration_valid(calibrating)
        self.pwm_duty_cycle = {}
        self.pwm_frequency = {}
        self.prescale = {}
        self.top = {}
        self.pwm_enable = {}
    def _disable_i2c(self):
        self.get_interface().write(":I2C:PORT:DISable;")
    def resync(self):
        line = self.get_interface().readline()
        while len(line):
            print(f"HTX9001 resync clearing out serial port data '{line}'")
            line = self.get_interface().readline()
    def add_channel_irelay(self,channel_name,irelay_number):
        '''Adds an irelay channel,
            channel_name is the name of the channel,
            irelay_number is the number of the irelay (same number as the supply being switched)
            valid irelays are 5-8'''
        if irelay_number not in self.irelay_pins:
            raise Exception(f"Invalid irelay number {irelay_number}")
        if self.irelay_pins[irelay_number] in self.initialized_pins:
            raise Exception(f"irelay number {irelay_number} already used in another channel!")
        new_channel = integer_channel(channel_name,size=1,write_function=lambda data: self._write_irelay(irelay_number,data))
        self._add_channel(new_channel)
        self.initialized_pins.append(self.irelay_pins[irelay_number])
        return new_channel
    def set_all_irelays(self,value):
        for irelay in self.irelay_pins:
            self._write_irelay(irelay,value)
    def get_resistor_calibration(self,resistor_number):
        read_str = f"CAL:DATA? {resistor_number};"
        self.get_interface().write(read_str)
        data = self.get_interface().readline()
        try:
            return float(data)
        except:
            return data # may return a string like "bad checksum"
    def _write_irelay(self,irelay_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for irelay: {value}')
        self._write_pin(self.irelay_pins[irelay_number],value)
    def _set_dvcc(self, voltage):
        self.get_interface().write(f"VOLT:DVCC {voltage}")
    def add_channel_pwm(self, channel_name, pin):
        if pin not in self.pwm_pins:
            raise Exception(f"Invalid HTX9001A PWM pin number {pin}. Must be one of: {self.pwm_pins}")
        if self.pwm_pins[pin] in self.initialized_pins:
            print(f"HTX9001A Warning: Non PWM pin {pin} being redefined as a PWM pin.")
            # raise Exception(f"HTX9001A pin number {pin} already in use by another channel!")
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
                raise Exception(f"Invalid HTX9001A frequency {value}. Must be between {flow} and {fhigh} Hz.")
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
                raise Exception(f'Bad value for HTX9001A pwm_enable: {value}. Try one of: 0,"0",False,1,"1",True.')
            self.pwm_enable[pin] = value
            self._update_pwm_channel(pin)
        new_channel = channel(channel_name, write_function=set_pwm_enable)
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
            raise Exception(f"Invalid HTX9001A servo pin number {servo_number}.")
        if self.pwm_pins[servo_number] in self.initialized_pins:
            print(f"HTX9001A Warning: Non Servo pin {self.pwm_pins[servo_number]} being redefined as a Servo pin.")
            # raise Exception(f"HTX9001A servo number {servo_number} already used in another channel!")
        new_channel = channel(channel_name,write_function=lambda value: self._write_servo(servo_number,value))
        self._write_servo_enable(servo_number, True)
        self._add_channel(new_channel)
        self.initialized_pins.append(self.pwm_pins[servo_number])
        return new_channel
    def add_channel_servo_enable(self,channel_name,servo_number):
        if servo_number not in self.pwm_pins:
            raise Exception(f"HTX9001A Invalid servo pin  number {servo_number}")
        new_channel = channel(channel_name,write_function=lambda value: self._write_servo_enable(servo_number,value))
        return self._add_channel(new_channel)
    def _write_servo_enable(self,servo_number,value):
        value = self._clean_value(value)
        if value not in [0,1]:
            raise Exception(f'Bad value for HTX9001A servo_enable: {value}.')
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
            raise Exception(f'Bad value for HTX9001A servo: {value}.')
        self.get_interface().write(f'PWM:COMPare ({self.pwm_pins[servo_number]},{value*2000+2000})')
    def set_all_relays(self,value):
        for relay in self.relay_pins:
            self._write_relay(relay, value)
        for relay in self.irelay_pins:
            self._write_irelay(relay, value)