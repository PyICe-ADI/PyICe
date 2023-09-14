from ..lab_core import *

class data_precision_8200(instrument):
    '''Data Precision GPIB controlled precision DC Voltage/Current Source
    Voltage Ranges are +/- 1V, 10V, 100V, 1000V
    Current Range is +/- 100mA
    '''
    def __init__(self,interface_visa):
        self._base_name = 'Data Precision 8200'
        instrument.__init__(self,f"{self._base_name} @ {interface_visa}")
        self.add_interface_visa(interface_visa)

        self._valid_vranges = (0.1,10,100,1000)
        self._vrange = 10 #volt
        self._voltage = None
        self._current = None
        self._mode = None
    def __del__(self):
        self.local_control()
        self.get_interface().close()
    def local_control(self):
        term_chars = self.get_interface().term_chars
        self.get_interface().term_chars = "" #need to remove any carriage return or line feed added by visa for this to work correctly
        self.get_interface().write(("L"))
        self.get_interface().term_chars = term_chars
    def add_channel_voltage(self,channel_name):
        '''Write channel to switch instrument to voltage mode and program voltage. Default voltage range is +/-10V.  Create a vrange channel to adjust range to (0.1,10,100,1000)V
        +/-100mV range has 0.1uV resolution, output impedance 100 Ohm
        +/-10V range has 10uV resolution, output impedance 10 mOhm, max current 100mA
        +/-100V range has 100uV resolution, output impedance 20 mOhm, max current 10mA
        +/-1000V range specifications are unknown
        '''
        new_channel = channel(channel_name,write_function=self._write_voltage)
        return self._add_channel(new_channel)
    def add_channel_current(self,channel_name):
        '''Write channel to switch instrument to current mode and program current between +/-100mA
        Voltage compliance is +/-10V'''
        new_channel = channel(channel_name,write_function=self._write_current)
        return self._add_channel(new_channel)
    def add_channel_vrange(self,channel_name):
        '''Write channel to set voltage mode full scale range to +/-(0.1,10,100,1000)V
        Takes immediate effect when in voltage mode, cached until switch to voltage mode when in current mode
        '''
        new_channel = channel(channel_name,write_function=self._set_vrange)
        return self._add_channel(new_channel)
    def add_channel_mode(self,channel_name):
        '''Channel returns 'V' when in Voltage mode and 'A' when in current mode'''
        new_channel = channel(channel_name,read_function=self._get_mode)
        return self._add_channel(new_channel)
    def _write_voltage(self,voltage):
        if voltage > self._vrange or voltage < -1*self._vrange:
             raise Exception(f'Voltage setting {voltage}V invalid for instrument {self.get_name()} range {vrange}V')
        #always 7 digits of magnitude, decimal point ignored
        if self._vrange == 0.1:
            #seven digits after decimal
            cmd = f'V0{(voltage*10**7):+08.0f}'
        elif self._vrange == 10:
            #two digits before decimal, five after
            cmd = f'V1{voltage:+09.5f}'
        elif self._vrange == 100:
            #three digits before decimal, four after
            cmd = f'V2{voltage:+09.4f}'
        elif self._vrange == 1000:
            #four digits before decimal, three after
            cmd = f'V3{voltage:+09.3f}'
        self._voltage = voltage
        self._current = None
        self._mode = 'V'
        self.get_interface().write((cmd))
    def _write_current(self,current):
        if current > 0.1 or current < -0.1:
             raise Exception(f'Current setting {current}A invalid for instrument {self.get_name()} (+/-100mA max)')
        #always 6 digits of magnitude, decimal point ignored
        cmd = f'A{current*10**6:+07.0f}'
        self._voltage = None
        self._current = current
        self._mode = 'A'
        self.get_interface().write((cmd))
    def _set_vrange(self, range):
        if range in self._valid_vranges:
            self._vrange = range
        else:
            raise Exception(f'Voltage range {range} invalid for instrument {self.get_name()}. Valid ranges are {self._valid_vranges}')
        if self._voltage is not None:
            self._write_voltage(self._voltage)
    def _get_mode(self):
        return self._mode
