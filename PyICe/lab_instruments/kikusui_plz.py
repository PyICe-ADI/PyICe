from PyICe.lab_core import *
import time

class kikusui_plz(scpi_instrument):
    '''Kikusui single channel electronic load superclass
        Instrument Family:
            PLZ 164W
            PLZ 164WA
            PLZ 334W
            PLZ 664WA
            PLZ1004W'''
    #note that this superclass was developed and tested with only the PLZ 334W instrument
    #some methods may need to be duplicated and moved to the instrument-specific classes
    #to resolve any operational/feature differences such as range selection
    def __init__(self,interface_visa):
        self._base_name = 'kikusui_plz'
        scpi_instrument.__init__(self,f"{self.kikusui_plz_name} @ {interface_visa}" )
        self.add_interface_visa(interface_visa)
        self.clear_status()
        self.reset()
        self.get_interface().write(('SOURce:FUNCtion:MODE CCCV'))
        #self.get_interface().write(("CCCR 1")) #constant current
        self.get_interface().write(("CURR 0"))
        self.get_interface().write(("VOLT 0"))
        self.get_interface().write(("OUTPUT 1"))
        #SM: Change from high range if you need it
        #self.get_interface().write(("CURRent:RANGe LOW"))
        #self.get_interface().write(("CURRent:RANGe MED")) #DJS This was inadvertantly changed by Greg in commit 2539. Changing back. Not sure what it should be.
        self._range = self._read_range()
        self._mode = self._read_mode()
    def add_channel(self,channel_name,add_sense_channels=True):
        '''Helper function adds primary current forcing channel of channel_name plus _vsense and _isense readback channels.'''
        self.add_channel_current(channel_name)
        if add_sense_channels:
            self.add_channel_vsense(channel_name + "_vsense")
            self.add_channel_isense(channel_name + "_isense")
            #the old add_channel added more, however I'm changing the default to this to speed up reading
            # add channels independently if you want something different
        self.write_channel(channel_name,0) #default to zero current
    def add_channel_current(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current)
        self._add_channel(new_channel)
    def add_channel_voltage(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_voltage)
        self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_vsense)
        self._add_channel(new_channel)
    def add_channel_isense(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_isense)
        self._add_channel(new_channel)
    def add_channel_power(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_power)
        self._add_channel(new_channel)
    def add_channel_range_readback(self,channel_name):
        new_channel = channel(channel_name,read_function=self._read_range)
        self._add_channel(new_channel)
    def add_channel_range(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_range)
        self._add_channel(new_channel)
    def add_channel_slew_rate(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_slew_rate)
        self._add_channel(new_channel)
    def add_channel_pulse_on(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_pulse_on)
        self._add_channel(new_channel)
    def add_channel_duty_cycle(self,channel_name):                                       # Duty cycle, frequency and current level are used for Switch operation
        new_channel = channel(channel_name,write_function=self._write_duty_cycle)
        self._add_channel(new_channel)
    def add_channel_frequency(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_frequency)
        self._add_channel(new_channel)
    def add_channel_current_level(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_current_level)
        self._add_channel(new_channel)
    def add_channel_short(self,channel_name):                                            # Short will only admit as much current as the current range. So before any short test
        new_channel = channel(channel_name,write_function=self._write_short)             # Remember to input a high current in your own code to force the change in Range
        self._add_channel(new_channel)
    def add_channel_enable(self,channel_name):
        new_channel = channel(channel_name,write_function=self._write_enable)
        self._add_channel(new_channel)
    def _read_vsense(self):
        '''Return channel measured voltage float.'''
        return float(self.get_interface().ask("MEAS:VOLT?"))
    def _read_power(self):
        '''Return channel measured power float.'''
        return float(self.get_interface().ask("MEAS:POW?"))
    def _read_isense(self):
        '''Return channel measured current float.'''
        return float(self.get_interface().ask("MEAS:CURR?"))
    def _read_range(self):
        '''Return channel range string.'''
        return self.get_interface().ask(("CURRent:RANGe?"))
    def _read_load(self):
        '''Return load state (1 -> "On", 0 -> "Off").'''
        return self.get_interface().ask(("OUTPut?"))
    def _read_mode(self):
        '''Return operation mode ( CC, CV, etc).'''
        return self.get_interface().ask(("SOURce:FUNCtion:MODE?"))
    def _write_current(self,current,autorange=False):
        '''Write channel to force value current.  Optionally set range manually.
            Valid ranges are "HIGH", "MED", and "LOW"'''
        self._write_mode("CC")
        self._mode = "CC"
        if autorange:
            if (current <= self.kikusui_low_threshold):
                best_range = "LOW"
            elif (current > self.kikusui_low_threshold and current <= self.kikusui_high_threshold):
                best_range = "MED"
            elif (current > self.kikusui_high_threshold):
                best_range = "HIGH"
            self._write_enable(0)
            time.sleep(0.3)
            self._write_range(best_range)
            self._write_enable(1)
        self.get_interface().write((f"CURR {current}"))
    def _write_voltage(self,voltage):
        if self._mode != "CV":
            self._write_enable(0)
            time.sleep(0.3)
            self._write_mode("CV")
            self._write_range("HIGH")
            self._write_enable(1)
        self.get_interface().write((f"VOLT {voltage}"))
    def _write_slew_rate(self,slew_rate):
        self.get_interface().write((f"CURR:SLEW {slew_rate}"))
    def _write_pulse_on(self,pulse_on):
        self.get_interface().write((f"PULSe {pulse_on}"))
    def _write_duty_cycle(self,duty_cycle):
        #duty_cycle is a percent from 5 to 95 %
        self.get_interface().write((f"PULSe:DCYCle {duty_cycle}"))
    def _write_frequency(self,frequency):
        self.get_interface().write((f"PULSe:FREQuency {frequency}"))
    def _write_current_level(self,current_level):
        self.get_interface().write((f"PULSe:LEVel:CURRent {current_level}"))
    def _write_short(self,short):
        self.get_interface().write((f"OUTPut:SHORt {short}"))
    def _write_enable(self,output):
        if output == True or output == 1:
            self.get_interface().write(("OUTPut 1"))
        if output == False or output == 0:
            self.get_interface().write(("OUTPut 0"))
        timeout1 = time.time() + .5
        while int(self._read_load()) != output:
            if timeout1 < time.time():
                print("Timeout1 for load on/off exceeded. Bump in lab_instruments.py if it is a consistent problem ")
    def _write_range(self,range):
        if (range is not None):
            if range.upper() in ["LOW", "MED", "HIGH"]:
                self._write_enable(0)
                time.sleep(0.3)
                self.get_interface().write((f"CURRent:RANGe {range.upper()}"))
                self._write_enable(1)
            else:
                raise Exception('Valid ranges are "HIGH", "MED", and "LOW"')
        self._range = self._read_range()
    def _write_mode(self,mode):
        self.get_interface().write((f"SOURce:FUNCtion:MODE {mode}"))
        self._mode = mode
