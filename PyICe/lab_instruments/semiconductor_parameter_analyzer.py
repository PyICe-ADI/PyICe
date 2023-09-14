from ..lab_core import *
import time

class semiconductor_parameter_analyzer(scpi_instrument):
    '''Generic parameter analyzer speaking HP4145 Command Set in user mode (US page)'''
    def _set_user_mode(self):
        self.get_interface().write(('US'))
    def _set_smu_voltage(self,smu_number,v_output=None,i_compliance=None,v_output_range=None):
        '''set smu voltage and current compliance if enough arguments specified'''
        if smu_number not in list(self._smu_configuration.keys()):
            self._smu_configuration[smu_number] = {'v_output_range':0,'i_output_range':0}
        if v_output is not None:
            self._smu_configuration[smu_number]['v_output'] = v_output
        if i_compliance is not None:
            self._smu_configuration[smu_number]['i_compliance'] = i_compliance
        if v_output_range is not None:
            if isinstance(v_output_range, str) and v_output_range.upper() == 'AUTO':
                self._smu_configuration[smu_number]['v_output_range'] = 0
            else:
                self._smu_configuration[smu_number]['v_output_range'] = self._lookup_output_range(v_output_range, self._smu_voltage_range)
        if 'v_output' in list(self._smu_configuration[smu_number].keys()) and 'i_compliance' in list(self._smu_configuration[smu_number].keys()):
            self.get_interface().write((f"DV {self._smu_voltage_force_channels[smu_number]:G}, {self._smu_configuration[smu_number]['v_output_range']:G}, {self._smu_configuration[smu_number]['v_output']:G}, {self._smu_configuration[smu_number]['i_compliance']:G}"))
        else:
            print(f'SMU{smu_number} disabled.  Write both output_voltage and current_compliance channels to enable output')
            self._disable_smu(smu_number)
    def _set_smu_current(self,smu_number,i_output=None,v_compliance=None,i_output_range=None):
        '''set smu current and voltage compliance if enough arguments specified'''
        if smu_number not in list(self._smu_configuration.keys()):
            self._smu_configuration[smu_number] = {'i_output_range':0,'v_output_range':0}
        if i_output is not None:
            self._smu_configuration[smu_number]['i_output'] = i_output
        if v_compliance is not None:
            self._smu_configuration[smu_number]['v_compliance'] = v_compliance
        if i_output_range is not None:
            if isinstance(i_output_range, str) and i_output_range.upper() == 'AUTO':
                self._smu_configuration[smu_number]['i_output_range'] = 0
            else:
                self._smu_configuration[smu_number]['i_output_range'] = self._lookup_output_range(i_output_range, self._smu_current_range)
        if 'i_output' in list(self._smu_configuration[smu_number].keys()) and 'v_compliance' in list(self._smu_configuration[smu_number].keys()):
            self.get_interface().write((f"DI {smu_number:G}, {self._smu_configuration[smu_number]['i_output_range']:G}, {self._smu_configuration[smu_number]['i_output']:G}, {self._smu_configuration[smu_number]['v_compliance']:G}"))
            #print 'writing these values to current SMU:'
            #print self._smu_configuration[smu_number]
        else:
            print(f'SMU{smu_number} disabled.  Write both output_current and voltage_compliance channels to enable output')
            self._disable_smu(smu_number)
    def _disable_smu(self,smu_number):
        self.get_interface().write((f"DV {self._smu_voltage_force_channels[smu_number]}"))
    def _lookup_output_range(self, max, range_dict):
        import bisect
        ranges = sorted(range_dict.keys())
        index = bisect.bisect_left(ranges, abs(max))
        print(f'range select chose +/-{ranges[index]}:{range_dict[ranges[index]]} to match input of {max}')
        return range_dict[ranges[index]]
    def _set_vsource_voltage(self,vsource_number,output):
        '''set vsource voltage'''
        self.get_interface().write((f"DS {vsource_number:G}, {output:G}"))
    def _disable_vs(self,vs_number):
        self.get_interface().write((f"DS {vs_number}"))
    def shutdown(self):
        for smu in self.smu_numbers:
            self._disable_smu(smu)
        for vs in self.vs_numbers:
            self._disable_vs(vs)
    def _read_voltage(self,channel_number):
        ret_str = self.get_interface().ask((f"TV {channel_number}"))
        result = self._check_measurement_result(ret_str)
        if result is not None:
            print(result)
            #raise exception?
            #log in error channel?
        return float(ret_str[3:])
    def _read_current(self,channel_number):
        ret_str = self.get_interface().ask((f"TI {channel_number}"))
        result = self._check_measurement_result(ret_str)
        if result is not None:
            print(result)
            #raise exception?
            #log in error channel?
        return float(ret_str[3:])
    def _check_measurement_result(self,ret_str):
        if ret_str[0] == 'N':
            return
        if ret_str[2] == 'V':
            instrument_dict = self._voltage_measure_channels
        elif ret_str[2] == 'I':
            instrument_dict = self._current_measure_channels
        else:
            raise Exception(f'Unknown data format: {ret_str}')
        if ret_str[0] == 'L':
            return f'WARNING! {instrument_dict[ret_str[1]]}: Interval too short'
        if ret_str[0] == 'V':
            return f'WARNING! {instrument_dict[ret_str[1]]}: A/D Converter Saturated - Overflow'
        if ret_str[0] == 'X':
            return f'WARNING! {instrument_dict[ret_str[1]]}: Oscillation'
        if ret_str[0] == 'C':
            return f'WARNING! {instrument_dict[ret_str[1]]}: This channel in compliance'
        if ret_str[0] == 'T':
            return f'WARNING! {instrument_dict[ret_str[1]]}: Other channel in compliance'
        raise Exception(f'Unknown data format: {ret_str}')
    def _set_integration_time(self,time):
        if (isinstance(time,str) and time.upper() == "SHORT") or time == 1:
            self.get_interface().write(("IT1"))
        elif (isinstance(time,str) and time.upper() == "MEDIUM") or time == 2:
            self.get_interface().write(("IT2"))
        elif  (isinstance(time,str) and time.upper() == "LONG") or time == 3:
            self.get_interface().write(("IT3"))
        else:
            raise Exception('Valid integration times are "SHORT", "MEDIUM" or "LONG"')
    def _add_channels_smu_voltage(self,smu_number,voltage_force_channel_name,current_compliance_channel_name):
        voltage_force_channel = channel(voltage_force_channel_name,write_function = lambda output: self._set_smu_voltage(smu_number,v_output=output))
        voltage_force_channel.set_attribute('type', 'voltage_force')
        current_compliance_channel = channel(current_compliance_channel_name,write_function = lambda compliance: self._set_smu_voltage(smu_number,i_compliance=compliance))
        current_compliance_channel.set_attribute('type', 'current_compliance')
        self._add_channel(voltage_force_channel)
        self._add_channel(current_compliance_channel)
        return [voltage_force_channel,current_compliance_channel]
    def _add_channel_smu_voltage_output_range(self,smu_number,output_range_channel_name):
        output_range_channel = channel(output_range_channel_name,write_function = lambda output_range: self._set_smu_voltage(smu_number,v_output_range=output_range))
        output_range_channel.set_attribute('type', 'voltage_range')
        self._add_channel(output_range_channel)
        return output_range_channel
    def _add_channels_smu_current(self,smu_number,current_force_channel_name,voltage_compliance_channel_name):
        current_force_channel = channel(current_force_channel_name,write_function = lambda output: self._set_smu_current(smu_number,i_output=output))
        current_force_channel.set_attribute('type', 'current_force')
        voltage_compliance_channel = channel(voltage_compliance_channel_name,write_function = lambda compliance: self._set_smu_current(smu_number,v_compliance=compliance))
        voltage_compliance_channel.set_attribute('type', 'voltage_compliance')
        self._add_channel(current_force_channel)
        self._add_channel(voltage_compliance_channel)
        return [current_force_channel,voltage_compliance_channel]
    def _add_channel_smu_current_output_range(self,smu_number,output_range_channel_name):
        output_range_channel = channel(output_range_channel_name,write_function = lambda output_range: self._set_smu_current(smu_number,i_output_range=output_range))
        output_range_channel.set_attribute('type', 'current_range')
        self._add_channel(output_range_channel)
        return output_range_channel
    def _add_channel_smu_voltage_sense(self,smu_number,voltage_sense_channel_name):
        voltage_sense_channel = channel(voltage_sense_channel_name,read_function = lambda: self._read_voltage(self._smu_voltage_measure_channels[smu_number]))
        voltage_sense_channel.set_attribute('type', 'voltage_sense')
        self._add_channel(voltage_sense_channel)
        return voltage_sense_channel
    def _add_channel_smu_current_sense(self,smu_number,current_sense_channel_name):
        current_sense_channel = channel(current_sense_channel_name,read_function = lambda: self._read_current(self._smu_current_measure_channels[smu_number]))
        current_sense_channel.set_attribute('type', 'current_sense')
        self._add_channel(current_sense_channel)
        return current_sense_channel
    def _add_channel_vsource(self,vsource_number,vsource_channel_name):
        vsource_channel = channel(vsource_channel_name,write_function = lambda output: self._set_vsource_voltage(vsource_number,output))
        vsource_channel.set_attribute('type', 'voltage_force') #should be different from SMU vsource???
        self._add_channel(vsource_channel)
        return vsource_channel
    def _add_channel_vmeter(self,vmeter_number,vmeter_channel_name):
        vmeter_channel = channel(vmeter_channel_name,read_function = lambda: self._read_voltage(self._vm_voltage_measure_channels[vmeter_number]))
        vmeter_channel.set_attribute('type', 'voltage_sense')
        self._add_channel(vmeter_channel)
        return vmeter_channel
    def add_channel_integration_time(self,integration_time_channel_name):
        integration_time_channel = channel(integration_time_channel_name,write_function =self._set_integration_time)
        integration_time_channel.set_attribute('type', 'integration_time')
        self._add_channel(integration_time_channel)
        return integration_time_channel
