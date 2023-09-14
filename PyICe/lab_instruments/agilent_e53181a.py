from PyICe.lab_core import *

class agilent_e53181a(scpi_instrument):
    '''Agilent e53181a frequency counter
        single channel, only uses channel 1 (front)
        you may need to set an expected value for autotriggering
        not recommended below 20hz
        defaults to 1Meg input R, 10x attenuation'''
    def __init__(self,interface_visa):
        self._base_name = 'agilent_e53181a'
        # instrument.__init__(self,f"agilent_e53181a @ {interface_visa}")
        super(agilent_e53181a, self).__init__(f"agilent_e53181a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.config_expect(1e6)
        self.get_interface().write(("*CLS"))
        self.get_interface().write(("*RST"))
        self.config_input_attenuation_1x()
        self.config_input_impedance_1Meg()
    def config_input_attenuation_1x(self):
        '''set input attenuator to 1x'''
        self.get_interface().write((":INPut1:ATTenuation 1"))
    def config_input_attenuation_10x(self):
        '''set input attenuator to 10x (divide by 10)'''
        self.get_interface().write((":INPut1:ATTenuation 10"))
    def config_input_impedance_50(self):
        '''set input impedance to 50 Ohm'''
        self.get_interface().write((":INPut1:IMPedance 50"))
    def config_input_impedance_1Meg(self):
        '''set input impedance to 1 MegOhm'''
        self.get_interface().write((":INPut1:IMPedance 1e6"))
    def config_expect(self,expected_frequency):
        '''specify expected frequency to help with counting very low frequencies.'''
        t = 1000 * 1/float(expected_frequency)
        if t > 30:
            self.get_interface().timeout = int(t)
        else:
            self.get_interface().timeout = 30
        self.expect = expected_frequency
    def add_channel(self,channel_name):
        '''Add named channels to instrument.'''
        self.add_channel_dutycycle(channel_name + "_dutycycle")
        return self.add_channel_freq(channel_name)
    def add_channel_freq(self,channel_name):
        '''Add named frequency channel to instrument'''
        freq_channel = channel(channel_name,read_function=self.read_frequency)
        return self._add_channel(freq_channel)
    def add_channel_dutycycle(self,channel_name):
        '''Add named dutycycle channel to instrument'''
        dutycycle_channel = channel(channel_name,read_function=self.read_dutycycle)
        return self._add_channel(dutycycle_channel)
    def read_frequency(self,channel_name):
        '''Return float representing measured frequency of named channel.'''
        txt = ":MEASure:FREQuency? %3.0f, 1, (@1)" % self.expect
        while True:
            try:
                return(self.get_interface().ask(txt))
                break
            except Exception as e:
                print("Waiting on frequency meter")
                print(e)
    def read_dutycycle(self,channel_name):
        '''Return float representing measured duty cycle of named channel.'''
        txt = ":MEASure:DCYCle? %3.0f, 1, (@1)" % self.expect
        while True:
            try:
                return(self.get_interface().ask(txt))
                break
            except Exception as e:
                print("Waiting on frequency meter")
                print(e)
