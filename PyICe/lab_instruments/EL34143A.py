from ..lab_core import *

class EL34143A(scpi_instrument):
    '''Electronic Load, model HMP 34143A
        Single Input DC Electronic Load; 150 V, 60 A, 350 W
    '''
    def __init__(self,interface_visa):
        self._base_name = 'EL34143A'
        super().__init__(f'EL34143A @  {interface_visa}')
        self.add_interface_visa(interface_visa)
        self.modes = ["CURR", "VOLT", "POW", "RES"]
        self.forcing_channels={"CURR":[], "VOLT":[], "POW":[], "RES":[]}
        self.curr_ranges = {'MIN':[0.0002,0.612],'MED':[0.002,6.12], 'MAX':[0.012,61.2]}
        self.volt_ranges = {'MIN':[0.003,15.3],'MAX':[0.015,153]}
        self.pow_ranges = {'MIN':[0.01,8.16],'MED':[0.3,35.7], 'MAX':[2,357]}
        time.sleep(1)
        self.clear_status()
        self.reset()
        self.TurnLoadOn()
    def add_channel(self,channel_name,add_extended_channels=True, set_range='AUTO'):
        '''Sortcut function adds CC force channel.
        if add_extended_channels, additionally add _isense,_vsense,_psense,_mode readback channels
        Add CV,CW,CR,remote_sense channels separately if you need them.'''
        ch = self.add_channel_current(channel_name, curr_range=set_range)
        ch.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        if add_extended_channels:
            self.add_channel_isense(channel_name + '_isense')
            self.add_channel_vsense(channel_name + '_vsense')
            self.add_channel_psense(channel_name + '_psense')
            self.add_channel_mode(channel_name + '_mode')
        return ch
    def add_channel_current(self,channel_name, curr_range='AUTO'):
        '''add single CC forcing channel and force zero current'''
        new_channel = channel(channel_name,write_function=self._SetCCCurrent)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current.__doc__)
        self.forcing_channels["CURR"].append(new_channel)
        self._add_channel(new_channel)
        self._add_channel_curr_range(channel_name, curr_range)
        new_channel.set_write_delay(0.4)
        new_channel.set_write_resolution(decimal_digits=3) #1mA
        new_channel.write(0)
        return new_channel
    def _add_channel_curr_range(self, channel_name, curr_range):
        '''add single range manipulation channel'''
        new_channel = channel(channel_name + '_range',write_function=self._SetCurrRange)
        new_channel.set_description(self.get_name() + ': ' + self._add_channel_curr_range.__doc__)
        new_channel.add_preset("MIN",    "Range 0.0002A to 0.612A")
        new_channel.add_preset("MED",    "Range 0.002A to 6.12A")
        new_channel.add_preset("MAX",    "Range 0.012A to 61.2A")
        new_channel.add_preset("AUTO",   "Determine appropriate range when necessary.")
        new_channel.write(curr_range)
        self.curr_range = curr_range
        return self._add_channel(new_channel)
    def add_channel_isense(self,channel_name):
        '''add single current readback channel'''
        new_channel = channel(channel_name,read_function=lambda: self._read_isense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_isense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        '''add single voltage readback channel'''
        new_channel = channel(channel_name,read_function=lambda: self._read_vsense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_vsense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_psense(self,channel_name):
        '''read back computed power dissipated in load'''
        new_channel = channel(channel_name,read_function=lambda: self._read_psense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_psense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_mode(self, channel_name):
        '''read back operating mode (Off, Constant Current, Constant Voltage, Constant Power, Constant Resistance)'''
        new_channel = channel(channel_name,read_function=lambda: self.GetMode())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_mode.__doc__)
        return self._add_channel(new_channel)
    def _read_vsense(self,channel_name):
        '''Return measured voltage float.'''
        return self.get_interface().ask("MEAS:VOLT?")
    def _read_isense(self,channel_name):
        '''Return measured current float.'''
        return self.get_interface().ask("MEAS:CURR?")
    def _read_psense(self,channel_name):
        '''Return measured power float.'''
        return self.get_interface().ask("MEAS:POW?")
    def add_channel_remote_sense(self,channel_name):
        '''Enable/disable remote voltage sense through panel connectors'''
        new_channel = integer_channel(channel_name, size=1, write_function=self.SetRemoteSense)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_remote_sense.__doc__)
        new_channel.write(True if self.GetRemoteSense() else False)
        return self._add_channel(new_channel)
    def add_channel_voltage(self,channel_name, volt_range='AUTO'):
        '''add single CV forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCVVoltage)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mV
        self.forcing_channels['VOLT'].append(new_channel)
        self._add_channel_volt_range(channel_name, volt_range)
        return self._add_channel(new_channel)
    def _add_channel_volt_range(self, channel_name, volt_range):
        '''add single range manipulation channel'''
        self.volt_range = volt_range
        assert volt_range in ['MIN', 'MAX', 'AUTO'], f"set_range must be 'MIN', 'MAX', or 'AUTO'. {volt_range} is unacceptable."
        new_channel = channel(channel_name + '_range',write_function=self._SetVoltRange)
        new_channel.set_description(self.get_name() + ': ' + self._add_channel_volt_range.__doc__)
        new_channel.add_preset("MIN",    "Range 0.003V to 15.3V")
        new_channel.add_preset("MAX",    "Range 0.015V to 153V")
        new_channel.add_preset("AUTO",   "Determine appropriate range when necessary.")
        new_channel.write(volt_range)
        return self._add_channel(new_channel)
    def add_channel_power(self,channel_name, pow_range='AUTO'):
        '''add single CW forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCWPower)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_power.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mW
        self.forcing_channels['POW'].append(new_channel)
        self._add_channel_pow_range(channel_name, pow_range)
        return self._add_channel(new_channel)
    def _add_channel_pow_range(self, channel_name, pow_range):
        '''add single range manipulation channel'''
        self.pow_range = pow_range
        assert pow_range in ['MIN', 'MED', 'MAX', 'AUTO'], f"set_range must be 'MIN', 'MED', 'MAX', or 'AUTO'. {pow_range} is unacceptable."
        new_channel = channel(channel_name + '_range',write_function= self._SetPowRange)
        new_channel.set_description(self.get_name() + ': ' + self._add_channel_volt_range.__doc__)
        new_channel.add_preset("MIN",    "Range 0.01W to 8.16W")
        new_channel.add_preset("MED",    "Range 0.3W to 35.7W")
        new_channel.add_preset("MAX",    "Range 2W to 357W")
        new_channel.add_preset("AUTO",   "Determine appropriate range when necessary.")
        new_channel.write(pow_range)
        return self._add_channel(new_channel)
    def add_channel_resistance(self,channel_name):
        '''add single CR forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCRResistance)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_resistance.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mOhm
        self.forcing_channels['RES'].append(new_channel)
        return self._add_channel(new_channel)
    def _add_channel_res_range(self, res_range):
        '''add single range manipulation channel'''
        self.res_range = res_range
        assert res_range in ['MIN', 'MED', 'MAX', 'AUTO'], f"set_range must be 'MIN', 'MED', 'MAX', or 'AUTO'. {res_range} is unacceptable."
        new_channel = channel(channel_name,read_function=lambda: self._SetResRange)
        new_channel.set_description(self.get_name() + ': ' + self._add_channel_volt_range.__doc__)
        new_channel.add_preset("MIN",    "Range 0.05Ω to 30Ω")
        new_channel.add_preset("MED",    "Range 10Ω to 1.25kΩ")
        new_channel.add_preset("MAX",    "Range 100Ω to 4kΩ")
        new_channel.add_preset("AUTO",   "Determine appropriate range when necessary.")
        new_channel.write(res_range)
        return self._add_channel(new_channel)

    def _SetCCCurrent(self, current):
        if current is None and self.GetMode() == 'CURR':
            return self.TurnLoadOff()
        elif current is None:
            return
        self.SetMode("CURR")
        if current == 0:
            return self.TurnLoadOff() # Don't trust setting of 0 to not drop out load.
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
        if self.curr_range == 'AUTO':
            present_range = self._find_current_range(float(self.GetCCCurrent()))
            if not self.curr_ranges[present_range][0] <= current <= self.curr_ranges[present_range][1]:                  ### Only change the range if necessary
                new_range = self._find_current_range(current)
                self.get_interface().write(f'CURR:RANG {new_range};CURR {current}')     ### Sending both range and value simultaneously SHOULD bypass conflicts.
            else:
                self.SetCCCurrent(current)
        elif self.curr_range in ['MIN','MED','MAX']:
            self.SetMaxCurrent(self.curr_ranges[self.curr_range][1])
            self.SetCCCurrent(current)
        self.TurnLoadOn() # Because it could be off
        if float(self.GetCCCurrent()) != current:
            print(f"WARNING! Failed to set the current to {current}A.\n{self.error()}")
    def _SetCVVoltage(self, voltage):
        if voltage is None and self.GetMode() == 'VOLT':
            return self.TurnLoadOff()
        elif voltage is None:
            return
        self.SetMode("VOLT")
        if voltage == 0:
            return self.TurnLoadOff() # Don't trust setting of 0 to not drop out load.
        self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
        
        if self.volt_range == 'AUTO':
            present_range = self._find_voltage_range(float(self.GetCVVoltage()))
            if not self.volt_ranges[present_range][0] <= voltage <= self.volt_ranges[present_range][1]:                  ### Only change the range if necessary
                new_range = self._find_voltage_range(voltage)
                if not self.volt_ranges[new_range][0] <= float(self.GetCVVoltage()) <= self.volt_ranges[new_range][1]:   ### Only step the voltage if necessary
                    self.SetCVVoltage(0.015)
                self.SetMaxVoltage(self.volt_ranges[new_range][1])
        elif self.volt_range in ['MIN','MAX']:
            self.SetMaxVoltage(self.volt_ranges[self.volt_range][1])
        self.SetCVVoltage(voltage)
        self.TurnLoadOn() # Because it could be off
        if float(self.GetCVVoltage()) != voltage:
            print(f"WARNING! Failed to set the voltage to {voltage}V.\n{self.error()}")
    def _SetCWPower(self, power):
        if power is None and self.GetMode() == 'POW':
            return self.TurnLoadOff()
        elif power is None:
            return
        self.SetMode("POW")
        if power == 0:
            self.TurnLoadOff()
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
        if self.pow_range == 'AUTO':
            present_range = self._find_power_range(float(self.GetCWPower()))
            if not self.pow_ranges[present_range][0] <= power <= self.pow_ranges[present_range][1]:                  ### Only change the range if necessary
                new_range = self._find_power_range(power)
                if not self.pow_ranges[new_range][0] <= float(self.GetCWPower()) <= self.pow_ranges[new_range][1]:   ### Only step the power if necessary
                    self.SetCWPower(0.015)
                self.SetMaxPower(self.pow_ranges[new_range][1])
        elif self.pow_range in ['MIN', 'MED', 'MAX']:
            self.get_interface().write(f'POW:RANG {self.pow_range}')
        self.SetCWPower(power)
        self.TurnLoadOn() # Because it could be off
    def _SetCRResistance(self, resistance):
        if resistance is None:
            return
        self.SetMode("RES")
        if resistance is None:
            self.TurnLoadOff()
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
        if self.res_range == 'AUTO':
            self.get_interface().write(f'RES:RANG {resistance}')
        elif self.res_range in ['MIN', 'MED', 'MAX']:
            self.get_interface().write(f'RES:RANG {self.res_range}')
        self.SetCRResistance(resistance)
        self.TurnLoadOn() # Because it could be off


    def TurnLoadOn(self):
        "Turns the load on"
        self.get_interface().write("INP 1")
    def TurnLoadOff(self):
        "Turns the load off"
        self.get_interface().write("INP 0")
    def SetRemoteControl(self):
        "Sets the load to remote control"
        return self.get_interface().write("SYST:COMM:RLST REM")
    def SetLocalControl(self):
        "Sets the load to local control"
        return self.get_interface().write("SYST:COMM:RLST LOC")

    def _find_current_range(self, value):
        if value >= 0.0002 and value <= 0.612:
            return 'MIN'
        if value >= 0.002 and value <= 6.12:
            return 'MED'
        if value >= 0.012 and value <= 61.2:
            return 'MAX'
        return 'Out of Range'
    def _find_voltage_range(self, value):
        if value >= 0.003 and value <= 15.3:
            return 'MIN'
        if value >= 0.015 and value <= 153:
            return 'MAX'
        return 'Out of Range'
    def _find_power_range(self, value):
        if value >= 0.01 and value <= 8.16:
            return 'MIN'
        if value >= 0.3 and value <= 35.7:
            return 'MED'
        if value >= 2 and value <= 357:
            return 'MAX'
        return 'Out of Range'
    def _find_resistance_range(self, value):
        if value >= 0.05 and value <= 30:
            return 'MIN'
        if value >= 10 and value <= 1250:
            return 'MED'
        if value >= 100 and value <= 4000:
            return 'MAX'
        return 'Out of Range'
    def _SetCurrRange(self, curr_range):
        self.curr_range = curr_range
        if curr_range != 'AUTO':
            self.get_interface().write(f'CURR:RANG {self.curr_ranges[curr_range][1]}')
    def SetMaxCurrent(self, current):
        "Sets the maximum current the load will sink"
        self.get_interface().write(f"CURR:RANG {current}")
    def GetMaxCurrent(self):
        "Returns the maximum current the load will sink"
        return self.get_interface().ask(f"CURR:RANG?")
    def _SetVoltRange(self, volt_range):
        self.volt_range = volt_range
        if volt_range != 'AUTO':
            self.get_interface().write(f'VOLT:RANG {self.volt_ranges[volt_range][1]}')
    def SetMaxVoltage(self, voltage):
        "Sets the maximum voltage the load will allow"
        self.get_interface().write(f"VOLT:RANG {voltage}")
    def GetMaxVoltage(self):
        "Gets the maximum voltage the load will allow"
        return self.get_interface().ask(f"VOLT:RANG?")
    def _SetPowRange(self, pow_range):
        self.pow_range = pow_range
        if pow_range != 'AUT0':
            self.get_interface().write(f'POW:RANG {self.pow_ranges[pow_range][1]}')
    def SetMaxPower(self, power):
        "Sets the maximum power the load will allow"
        self.get_interface().write(f"POW:RANG {power}")
    def GetMaxPower(self):
        "Gets the maximum power the load will allow"
        return self.get_interface().ask(f"POW:RANG?")
    def SetMode(self, mode):
        "Sets the mode (constant current, constant voltage, etc."
        if mode not in self.modes:
            raise Exception(f"Unknown mode. Expecting CURR, VOLT, POW, or RES. Not {mode}.")
        for other_modes in self.forcing_channels:
            if other_modes != mode:
                for channel in self.forcing_channels[other_modes]:
                    channel.write(None)
        return self.get_interface().write(f"MODE {mode}")
    def GetMode(self):
        "Gets the mode (constant current, constant voltage, etc."
        msg = "Get mode"
        return self.get_interface().ask("MODE?")
    def SetCCCurrent(self, current):
        "Sets the constant current mode's current level"
        self.get_interface().write(f"CURR {current}")
    def GetCCCurrent(self):
        "Gets the constant current mode's current level"
        return self.get_interface().ask("CURR?")
    def SetCVVoltage(self, voltage):
        "Sets the constant voltage mode's voltage level"
        self.get_interface().write(f"VOLT {voltage}")
    def GetCVVoltage(self):
        "Gets the constant voltage mode's voltage level"
        return self.get_interface().ask("VOLT?")
    def SetCWPower(self, power):
        "Sets the constant power mode's power level"
        self.get_interface().write(f"POW {power}")
    def GetCWPower(self):
        "Gets the constant power mode's power level"
        return self.get_interface().ask("POW?")
    def _SetResRange(self, res_range):
        self.res_range = res_range
        self.get_interface().write(f'RES:RANG {self.res_range}')
    def SetCRResistance(self, resistance):
        "Sets the constant resistance mode's resistance level"
        self.get_interface().write(f"RES {resistance}")
    def GetCRResistance(self):
        "Gets the constant resistance mode's resistance level"
        return self.get_interface().ask(f"RES?")
    def SetRemoteSense(self, enabled=0):
        "Enable or disable remote sensing"
        ernal = {0:'INT', 1:'EXT', False:'INT', True:'EXT', 'INT':'INT', 'EXT':'EXT'}
        self.get_interface().write(f"VOLT:SENS {ernal[enabled]}")
    def GetRemoteSense(self):
        "Get the state of remote sensing"
        return self.get_interface().ask("VOLT:SENS?")