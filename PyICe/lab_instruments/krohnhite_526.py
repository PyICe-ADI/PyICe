from ..lab_core import *

class krohnhite_526(instrument):
    '''Krohn-Hite Model 526 Precision DC Source/Calibrator
    Driver uses 526 protocol (other protocols do not support LAN operation)
    Voltage Ranges are +/- 0.1V, 1V, 10V, 100V
    Current Ranges are +/- 10mA, 100mA
        CHAR   FN    ASCII CODE
        1      Polarity     + = Positive
                            0 = Crowbar
                            - = Negative
        2      MSD          0 to 10 (use 'J' for decimal 10)
        3      2SD          0 to 10 (use 'J' for decimal 10)
        4      3SD          0 to 10 (use 'J' for decimal 10)
        5      4SD          0 to 10 (use 'J' for decimal 10)
        6      5SD          0 to 10 (use 'J' for decimal 10)
        7      6SD          0 to 10 (use 'J' for decimal 10)
        8      Range        0 = 100mV
                            1 = 1V
                            2 = 10V
                            3 = 100V
                            4 = 10mA
                            5 = 100mA
        9(OPT) Sense        2 = 2-Wire Mode
                            4 = 4-Wire Mode

    '''
    def __init__(self,interface_visa):
        self._base_name = 'Krohn-Hite 526'
        instrument.__init__(self,f"{self._base_name} @ {interface_visa}" )
        self.add_interface_visa(interface_visa)
        self._valid_vranges = {0.1:0, 1:1, 10:2, 100:3}
        self._valid_iranges = {0.01:4, 0.1:5}
        self.v_channel = None
        self.i_channel = None
        self._set_vrange(10) # 10 V default range
        self._set_irange(0.01) # 10 mA default range
        self._sense = '2' # default to 2-wire mode
        self._voltage = 0
        self._current = 0
    def add_channel_current(self,channel_name):
        '''Write channel to switch instrument to current mode and program current. Default current range is +/-10mA.  Create a irange channel to adjust range to (10, 100)mA '''
        self.i_channel = channel(channel_name,write_function=self._write_current)
        self.i_channel.set_max_write_limit(self._irange)
        self.i_channel.set_min_write_limit(-self._irange)
        return self._add_channel(self.i_channel)
    def add_channel_irange(self,channel_name):
        '''Write channel to set current mode full scale range to +/-(10,100)mA.  Won't take effect until the current is programmed.'''
        new_channel = channel(channel_name,write_function=self._set_irange)
        return self._add_channel(new_channel)
    def _set_irange(self, range):
        if range not in self._valid_iranges:
            raise Exception(f'Current range {range} invalid for instrument {self.get_name()}. Valid ranges are {list(self._valid_iranges.keys())}')
        self._irange = range
        if self.i_channel is not None:
            self.i_channel.set_max_write_limit(self._irange)
            self.i_channel.set_min_write_limit(-self._irange)
        #write new range out to instrument here????
        #print self._irange
    def _write_current(self,current):
                #determine polarity and produce _pol_char
        if current >= 0:
            _pol_char = '+'
        elif current <0:
            _pol_char = '-'
        #always 7 digits of magnitude, decimal point ignored, pad left side with zeros
        if self._irange == 0.01:
            cmd = f'{current*1000:06.5f}'
            if current == 0.01:
                cmd = 'J' + f'{current*1000-10:05.4f}'
            if current == -0.01:
                cmd = 'J' + f'{current*1000+10:05.4f}'
        elif self._irange == 0.1:
            cmd = f'{current*100:07.5f}'
            if current == 0.1:
                cmd = 'J' + f'{current*100-10:06.4f}'
            if current == -0.1:
                cmd = 'J' + f'{current*100+10:06.4f}'
        cmd = str(cmd)
        cmd = cmd.replace('.','' )
        cmd = cmd.replace('-','' )
        command = f"{_pol_char}{cmd}{self._valid_iranges[self._irange]}{self._sense}"
        self.get_interface().write((command))
    def add_channel_voltage(self,channel_name):
        self.v_channel = channel(channel_name,write_function=self._write_voltage)
        self.v_channel.set_max_write_limit(self._vrange)
        self.v_channel.set_min_write_limit(-self._vrange)
        return self._add_channel(self.v_channel)
    def add_channel_vrange(self,channel_name):
        '''Write channel to set voltage mode full scale range to +/-(0.1,1,10,100)V or +/-(10,100)mA.  Won't take effect until the voltage is programmed.'''
        new_channel = channel(channel_name,write_function=self._set_vrange)
        return self._add_channel(new_channel)
    def _set_vrange(self, range):
        if range not in self._valid_vranges:
            raise Exception(f'Voltage range {range} invalid for instrument {self.get_name()}. Valid ranges are {list(self._valid_vranges.keys())}')
        self._vrange = range
        if self.v_channel is not None:
            self.v_channel.set_max_write_limit(self._vrange)
            self.v_channel.set_min_write_limit(-self._vrange)
        #write new range out to instrument here????
    def _write_voltage(self,voltage):
        #determine polarity and produce _pol_char
        if voltage >= 0:
            _pol_char = '+'
        elif voltage <0:
            _pol_char = '-'
        #always 7 digits of magnitude, decimal point ignored, pad left side with zeros
        if self._vrange == 0.1:
            #seven digits after decimal
            cmd = f'{voltage*10**7:06.0f}'
            if voltage == 0.1:
                cmd = 'J' + f'{voltage*10**7-1000000:05.0f}'
            if voltage == -0.1:
                cmd = 'J' + f'{voltage*10**7+1000000:05.0f}'
        elif self._vrange == 1:
            #two digits before decimal, five after
            cmd = f'{voltage*10:07.5f}'
            if voltage == 1:
                cmd = 'J' + f'{voltage*10-10:06.4f}'
            if voltage == -1:
                cmd = 'J' + f'{voltage*10+10:06.4f}'
        elif self._vrange == 10:
            #one digit before decimal, five after
            cmd = f'{voltage:07.5f}'
            if voltage == 10:
                cmd = 'J' + f'{voltage-10:06.4f}'
            if voltage == -10:
                cmd = 'J' + f'{voltage+10:06.4f}'
        elif self._vrange == 100:
            # #four digits before decimal, three after
            # cmd = f'{voltage:07.4f}'
            # if voltage == 100:
                # cmd = 'J' + f'{voltage-100:06.4f}'
            # if voltage == -100:
                # cmd = 'J' + f'{voltage+100:06.4f}'

            #four digits before decimal, three after
            if (voltage<0)|(voltage>-10):
                cmd = f'{voltage:08.4f}'
            elif voltage <= -10:
                cmd = f'{voltage:07.4f}'
            if voltage >= 0:
                cmd = f'{voltage:07.4f}'
            if voltage == 100:
                cmd = 'J' + f'{voltage-100:06.4f}'
            if voltage == -100:
                cmd = 'J' + f'{voltage+100:06.4f}'
        cmd = str(cmd)
        cmd = cmd.replace('.','' )
        cmd = cmd.replace('-','' )
        command = f"{_pol_char}{cmd}{self._valid_vranges[self._vrange]}{self._sense}"
        self.get_interface().write((command))
