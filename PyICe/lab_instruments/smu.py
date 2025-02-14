from ..lab_core import *
import atexit
from functools import wraps
import pyvisa.errors
from abc import abstractmethod

#todo measure autorange
#todo range control channels???

class smu(instrument):
    def _fix_exclusive(self, ch, value):
        '''fix write cache of exclusive channel pair sibling'''
        if ch.get_attribute('channel_type') == 'vforce':
            pair_ch = self._configured_channels[ch.get_attribute('channel_number')]['i_force']
            if  pair_ch is not None:
                pair_ch._set_value(None)
        elif ch.get_attribute('channel_type') == 'iforce':
            pair_ch = self._configured_channels[ch.get_attribute('channel_number')]['v_force']
            if  pair_ch is not None:
                pair_ch._set_value(None)
        else:
            raise Exception('How did I get here?')
    def _init_channel(self, channel_number):
        #todo remote sense, high c?
        if channel_number in self._configured_channels:
            assert 'v_force' in self._configured_channels[channel_number]
            assert 'i_force' in self._configured_channels[channel_number]
            assert 'v_sense' in self._configured_channels[channel_number]
            assert 'i_sense' in self._configured_channels[channel_number]
            assert 'v_compl' in self._configured_channels[channel_number]
            assert 'i_compl' in self._configured_channels[channel_number]
        else:
            self._configured_channels[channel_number] = {'v_force': None,
                                                         'i_force': None,
                                                         'v_sense': None,
                                                         'i_sense': None,
                                                         'v_compl': None,
                                                         'i_compl': None,
                                                        }
    def add_channels(self, channel_name, channel_number=1):
        '''shortcut'''
        #todo remote sense, high c?
        return (self.add_channel_voltage_force(f'{channel_name}_vforce', channel_number),
                self.add_channel_current_force(f'{channel_name}_iforce', channel_number),
                self.add_channel_voltage_sense(f'{channel_name}_vsense', channel_number),
                self.add_channel_current_sense(f'{channel_name}_isense', channel_number),
                self.add_channel_voltage_compliance(f'{channel_name}_vcompl', channel_number),
                self.add_channel_current_compliance(f'{channel_name}_icompl', channel_number),
                )
    def add_channel_voltage_force(self, channel_name, channel_number=1):
        '''voltage force. Mutually exclusive at any moment with current force.'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda v, channel_number=channel_number: self._vforce(channel_number, v))
        self._configured_channels[channel_number]['v_force'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_force.__doc__)
        self._add_channel_voltage_force(channel_name, channel_number=1)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        return self._add_channel(new_channel)
        
    def add_channel_current_force(self, channel_name, channel_number=1):
        '''current force. Mutually exclusive at any moment with voltage force.'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._iforce(channel_number, i))
        self._configured_channels[channel_number]['i_force'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'iforce')
        new_channel.add_write_callback(self._fix_exclusive)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_force.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_current_force(channel_name, channel_number)
        return self._add_channel(new_channel)
    def add_channel_voltage_sense(self, channel_name, channel_number=1):
        '''voltage readback'''
        #range, nplc?
        self._init_channel(channel_number)
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._vsense(channel_number))
        self._configured_channels[channel_number]['v_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vsense')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_voltage_sense(channel_name, channel_number)
        return self._add_channel(new_channel)
    def add_channel_current_sense(self, channel_name, channel_number=1):
        '''current readback'''
        #range, nplc?
        self._init_channel(channel_number)
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._isense(channel_number))
        self._configured_channels[channel_number]['i_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'isense')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_sense.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'A')
        self._add_channel_current_sense(channel_name, channel_number)
        return self._add_channel(new_channel)
    def add_channel_voltage_compliance(self, channel_name, channel_number=1):
        '''max voltage in current forcing modes'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda v, channel_number=channel_number: self._vcompl(channel_number, v))
        self._configured_channels[channel_number]['v_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'vcompl')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        self._add_channel_voltage_compliance(channel_name, channel_number)
        return self._add_channel(new_channel)
    def add_channel_current_compliance(self, channel_name, channel_number=1):
        '''max current in voltage forcing modes'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._icompl(channel_number, i))
        self._configured_channels[channel_number]['i_compl'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'icompl')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current_compliance.__doc__)
        # new_channel.set_display_format_function(function = lambda float_data: lab_utils.eng_string(float_data, fmt=fmt,si=True) + 'V')
        self._add_channel_current_compliance(channel_name, channel_number)
        return self._add_channel(new_channel)
    def add_channel_remote_sense(self, channel_name, channel_number=1):
        '''remote (4-wire) sense enable control'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._remote_sense(channel_number, i))
        self._configured_channels[channel_number]['remote_sense'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'remote_sense')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_remote_sense.__doc__)
        self._add_channel_remote_sense(channel_name, channel_number)
        return self._add_channel(new_channel)
        #todo initial value?
    def add_channel_high_capacitance(self, channel_name, channel_number):
        '''stabilize forcing source for higher DUT capacitance, typically tens of uF'''
        self._init_channel(channel_number)
        new_channel = channel(channel_name,write_function=lambda i, channel_number=channel_number: self._high_capacitance(channel_number, i))
        self._configured_channels[channel_number]['high_capacitance'] = new_channel
        new_channel.set_attribute('channel_number', channel_number)
        new_channel.set_attribute('channel_type', 'high_capacitance')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_high_capacitance.__doc__)
        self._add_channel_high_capacitance(channel_name, channel_number)
        return self._add_channel(new_channel)
        #todo initial value?
    def _add_channel_voltage_force(self, channel_name, channel_number):
        '''voltage force. Mutually exclusive at any moment with current force.'''
    def _add_channel_current_force(self, channel_name, channel_number):
        '''current force. Mutually exclusive at any moment with voltage force.'''
    def _add_channel_voltage_sense(self, channel_name, channel_number):
        '''voltage readback'''
    def _add_channel_current_sense(self, channel_name, channel_number):
        '''current readback'''
    def _add_channel_voltage_compliance(self, channel_name, channel_number):
        '''max voltage in current forcing modes'''
    def _add_channel_current_compliance(self, channel_name, channel_number):
        '''max current in voltage forcing modes'''
    def _add_channel_remote_sense(self, channel_name, channel_number):
        '''remote (4-wire) sense enable control'''
    def _add_channel_high_capacitance(self, channel_name, channel_number):
        '''stabilize forcing source for higher DUT capacitance, typically tens of uF'''
    
class keithley_smu(smu):
    def _parse_float(self, val):
        f = float(val)
        if f == 9.91E37: #Keithley NaN
            f = float('nan')
        return f

class scpi_smu(scpi_instrument, smu):
    ''''''
    #todo abstract methods?
    def _output_off(self, channel_number):
        self.get_interface().write(f':SOURce{channel_number}:CLEar:IMMediate')
    def _vforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f':SOURce{channel_number}:VOLTage:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(f':SOURce{channel_number}:FUNCtion:MODE VOLTage')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['i_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _iforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f':SOURce{channel_number}:CURRent:LEVel:IMMediate:AMPLitude {value}')
            self.get_interface().write(f':SOURce{channel_number}:FUNCtion:MODE CURRent')
            self.get_interface().write(f':OUTPut{channel_number}:STATe ON')
        else:
            pair_ch = self._configured_channels[channel_number]['v_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _vsense(self, channel_number):
        # what about channel number parsing?!?!?!?
        # :FORMat:ELEMents [SENSe[1]] <item list> Specify data elements for data string
        # Parameters <item list> = VOLTageIncludes voltage reading
        # CURRentIncludes current reading
        # RESistance Includes resistance reading
        # TIMEIncludes timestamp
        # STATusIncludes status information
        #todo better message parsing
        #todo explicitly set format of response included elements
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(f':MEASure:VOLTage:DC?').split(',')
        return self._parse_float(voltage)
    def _isense(self, channel_number):
        # what about channel number parsing?!?!?!?
        (voltage, current, resistance, timestamp, status) = self.get_interface().ask(f':MEASure:CURRent:DC?').split(',')
        return self._parse_float(current)
    def _vcompl(self, channel_number, value):
        self.get_interface().write(f':SENSe{channel_number}:VOLTage:DC:PROTection:LEVel {value}')
    def _icompl(self, channel_number, value):
        self.get_interface().write(f':SENSe{channel_number}:CURRent:DC:PROTection:LEVel {value}')
    def _remote_sense(self, channel_number, value):
        '''ignores channel number!!!!!!!!!!!!!!!!!!!'''
        self.get_interface().write(f':SYSTem:RSENse {1 if value else 0}')
    def _high_capacitance(self, channel_number, value):
        raise Exception('Unimplemented. Contact PyICe developers.')
        

class keithley_2400(scpi_smu, keithley_smu):
    ''''''
    # todo NPLC config?
    # todo trigger source, pulse, sweep? Other instrument driver?
    # todo atexit cleanup?
    # todo V/I init to zero?, source off?
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'Keithley 2400'
        super(scpi_smu, self).__init__(f"Keithley 2400 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._configured_channels = {}
        self._output_off(channel_number=1)
        self.get_interface().write(':SOURce1:VOLTage:PROTection:LEVel 20') ##todo Dave fix
        atexit.register(self._output_off, channel_number=1) #TODO debug
    def _add_channel_voltage_force(self, channel_name, channel_number):
        '''voltage force. Mutually exclusive at any moment with current force.'''
        self.get_interface().write(f':SOURce{channel_number}:VOLTage:RANGe:AUTO ON')
        self.get_interface().write(f':SOURce{channel_number}:VOLTage:MODE FIXed')
        self.get_interface().write(f':SOURce{channel_number}:CLEar:AUTO OFF')
        # self.get_interface().write(f':SOURce{channel_number}:FUNCtion:SHAPe DC') #2430 only
    def _add_channel_current_force(self, channel_name, channel_number):
        '''current force. Mutually exclusive at any moment with voltage force.'''
        self.get_interface().write(f':SOURce{channel_number}:CURRent:RANGe:AUTO ON')
        self.get_interface().write(f':SOURce{channel_number}:CURRent:MODE FIXed')
        self.get_interface().write(f':SOURce{channel_number}:CLEar:AUTO OFF')
        # self.get_interface().write(f':SOURce{channel_number}:FUNCtion:SHAPe DC') #2430 only
    def _add_channel_voltage_sense(self, channel_name, channel_number):
        '''voltage readback'''
        # [:SENSe[1]]:VOLTage[:DC]:NPLCycles <n> Set speed (PLC)
    def _add_channel_current_sense(self, channel_name, channel_number):
        '''current readback'''
        #range, nplc?
        # [:SENSe[1]]:CURRent[:DC]:NPLCycles <n> Set speed (PLC)
    def _add_channel_voltage_compliance(self, channel_name, channel_number):
        '''max voltage in current forcing modes'''
        #there are two thresholds. Source compliance (OVP) and Sense compliance (true compliance). Ignoring the former for now....
        # these are very coarse. ie
        # <n> = -210 to 210 Specify V-Source limit
        # 20 Set limit to 20V
        # 40 Set limit to 40V 
        # 60 Set limit to 60V
        # 18-80 SCPI Command Reference 2400 Series SourceMeter® User’s Manual 
        # 80 Set limit to 80V
        # 100 Set limit to 100V 
        # 120 Set limit to 120V 
        # 160 Set limit to 160V 
        # 161 to 210 Set limit to 210V (NONE)
        # DEFault Set limit to 210V (NONE)
        # MINimum Set limit to 20V
        # MAXimum Set limit to 210V (NONE)'''
        # :SOURce[1]:VOLTage:PROTection[:LEVel] 
        # TODO if this is useful
    def _add_channel_current_compliance(self, channel_name, channel_number):
        '''max current in voltage forcing modes'''

class keithley_2600(keithley_smu):
    '''https://download.tek.com/manual/2600BS-901-01_C_Aug_2016_2.pdf'''
    def __init__(self,interface_visa):
        self._base_name = 'Keithley 2600'
        super(keithley_2600, self).__init__(f"{self._base_name} @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._configured_channels = {}
        self._output_off(channel_number=1)
        self._output_off(channel_number=2)
        self._high_capacitance(1, True)
        self._high_capacitance(2, True)
        self._remote_sense(1, True)
        self._remote_sense(2, True)
        # self.get_interface().write(':SOURce1:VOLTage:PROTection:LEVel 20') ##todo Dave fix
        atexit.register(self._output_off, channel_number=1)
        atexit.register(self._output_off, channel_number=2)
    def _channel_id(self, channel_number):
        if channel_number == 1:
            return 'a'
        elif channel_number == 2:
            return 'b'
        else:
            raise Exception(f'Unknown SMU channel number {channel_number}.')
    def _high_capacitance(self, channel_number, is_high_c):
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.highc = smu{self._channel_id(channel_number)}.{"ENABLE" if is_high_c else "DISABLE"}')
    def _remote_sense(self, channel_number, is_remote_sense):
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.sense = smu{self._channel_id(channel_number)}.{"SENSE_REMOTE" if is_remote_sense else "SENSE_LOCAL"}')
    def _output_off(self, channel_number):
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_HIGH_Z')
    def _vforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.levelv = {value}')
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.func = smu{self._channel_id(channel_number)}.OUTPUT_DCVOLTS')
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_ON')
        else:
            pair_ch = self._configured_channels[channel_number]['i_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _iforce(self, channel_number, value):
        if value is not None:
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.leveli = {value}')
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.func = smu{self._channel_id(channel_number)}.OUTPUT_DCAMPS')
            self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.output = smu{self._channel_id(channel_number)}.OUTPUT_ON')
        else:
            pair_ch = self._configured_channels[channel_number]['v_force']
            if pair_ch is not None and pair_ch.read() is None:
                self._output_off(channel_number=channel_number)
    def _vsense(self, channel_number):
        #smuX.measure.autorangeY
        return self._parse_float(self.get_interface().ask(f'print(smu{self._channel_id(channel_number)}.measure.v())'))
    def _isense(self, channel_number):
        # what about channel number parsing?!?!?!?
        return self._parse_float(self.get_interface().ask(f'print(smu{self._channel_id(channel_number)}.measure.i())'))
    def _vcompl(self, channel_number, value):
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.limitv = {value}')
    def _icompl(self, channel_number, value):
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.limiti = {value}')
    def _add_channel_voltage_force(self, channel_name, channel_number):
        '''voltage force. Mutually exclusive at any moment with current force.'''
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.autorangev =  smu{self._channel_id(channel_number)}.AUTORANGE_ON')
    def _add_channel_current_force(self, channel_name, channel_number):
        '''current force. Mutually exclusive at any moment with voltage force.'''
        self.get_interface().write(f'smu{self._channel_id(channel_number)}.source.autorangei =  smu{self._channel_id(channel_number)}.AUTORANGE_ON')
        
