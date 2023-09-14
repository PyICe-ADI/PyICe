from ..lab_core import *

class rigol_DG800(scpi_instrument):
    ''' Function Generator
        The intrument will default to pulse generation (driver does not support other functions yet).
        A default instr_trigger channel will control sending of trigger for all active channels.
        The main channel will control the output enable and the extended channels will control pulse 
        parameters (low voltage, high voltage, pulse width, period, transition time and no. of cycles)'''
    def __init__(self,instrument_visa):
        '''instrument_visa'''
        self._base_name = 'Rigol_DG800'
        scpi_instrument.__init__(self,f"DG800 @ {instrument_visa}")
        self.add_interface_visa(instrument_visa)
        self.instrument = self.get_interface()
        self.instrument.write("*RST")
    def add_channel(self, channel_name, channel_number, function="PULSe", add_extended_channels=True):
        if function == "PULSe":
            self._config_pulse_func(channel_number, function)
        output_enable_channel = self.add_channel_enable(channel_name, channel_number)
        if add_extended_channels:
            self.add_channel_trigger(channel_name + "_trigger", channel_number)
            self.add_channel_low_voltage(channel_name + "_low_voltage", channel_number)
            self.add_channel_high_voltage(channel_name + "_high_voltage", channel_number)
            self.add_channel_pulse_width(channel_name + "_pulse_width", channel_number)
            self.add_channel_pulse_period(channel_name + "_period", channel_number)
            self.add_channel_rise_time(channel_name + "_risetime", channel_number)
            self.add_channel_fall_time(channel_name + "_falltime", channel_number)
            self.add_channel_cycle_count(channel_name + "_cycle_count", channel_number)
        else:
            print('Manually add channels for high_voltage, low_voltage, pulse_width, period, and/or transition')
        return output_enable_channel
    def _config_pulse_func(self, channel_number, function, high_voltage=3.3, low_voltage=0, period=500e-6, pulse_width=50e-6, cycle_count=1):
        '''Set instrument output function to pulse generation.'''
        self.instrument.write(f"SOURce{channel_number}:FUNCtion:SHAPe {function}")
        self.instrument.write(f"OUTPut{channel_number}:IMPedance 50")
        self.instrument.write(f"OUTPut{channel_number}:POLarity NORMal")
        self.instrument.write(f"SOURce{channel_number}:BURSt:MODE TRIGgered")
        self.instrument.write(f"SOURce{channel_number}:BURSt:TRIGger:SOURce MAN")
        self.instrument.write(f"SOURce{channel_number}:BURSt:STATe ON")
        self._write_high_voltage(channel_number, high_voltage)
        self._write_low_voltage(channel_number, low_voltage)
        self._write_pulse_period(channel_number, period)
        self._write_pulse_width(channel_number, pulse_width)
        self._write_cycle_count(channel_number, cycle_count)
        
        
        
        # pulse_generator.get_interface().write(":SOUR1:APPL:SIN 1000,5,0,0")
        # pulse_generator.get_interface().write(":SOUR1:BURS ON")
        # pulse_generator.get_interface().write(":SOUR1:BURS:MODE TRIG")
        # pulse_generator.get_interface().write(":SOUR1:BURS:NCYC 100")
        # pulse_generator.get_interface().write(":SOUR1:BURS:INT:PER 0.1")
        # pulse_generator.get_interface().write(":SOUR1:BURS:TRIG:SOUR INT")
        # pulse_generator.get_interface().write(":SOUR1:BURS:TRIG:TRIGO NEG")
        # pulse_generator.get_interface().write(":SOUR1:BURS:TDEL 0.01")
        # pulse_generator.get_interface().write(":OUTP1 ON")
        # pulse_generator.get_interface().write(":SOUR1:BURS:TRIG")

        
        
        # breakpoint()
    def config_sinusoid_func():
        pass
    def config_square_func():
        pass
    def config_ramp_func():
        pass
    def config_noise_func():
        pass
    def config_dc_func():
        pass
    def config_user_func():
        pass
    def add_channel_enable(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda output_enable: self._write_output_enable(channel_number, output_enable))
        new_channel.add_preset('ON', 'Output Enabled')
        new_channel.add_preset('OFF', 'Output Disabled')
        return self._add_channel(new_channel)
    def add_channel_low_voltage(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda low_voltage: self._write_low_voltage(channel_number, low_voltage))
        new_channel.add_preset('0', 'Default Value')
        return self._add_channel(new_channel)
    def add_channel_high_voltage(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda high_voltage: self._write_high_voltage(channel_number, high_voltage))
        new_channel.add_preset('3.3', 'Default Value')
        return self._add_channel(new_channel)
    def add_channel_pulse_width(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda pulse_width: self._write_pulse_width(channel_number, pulse_width))
        new_channel.add_preset('50e-6', 'Default Value')
        new_channel.set_min_write_limit(30e-9)
        return self._add_channel(new_channel)
    def add_channel_pulse_period(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda period: self._write_pulse_period(channel_number, period))
        new_channel.add_preset('500e-6', 'Default Value')
        return self._add_channel(new_channel)
    def add_channel_rise_time(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda transition: self._write_pulse_transition_leading(channel_number, transition))
        new_channel.add_preset('8e-9', 'Default Value')
        new_channel.set_min_write_limit(8e-9)
        return self._add_channel(new_channel)
    def add_channel_fall_time(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda transition: self._write_pulse_transition_trailing(channel_number, transition))
        new_channel.add_preset('8e-9', 'Default Value')
        new_channel.set_min_write_limit(8e-9)
        return self._add_channel(new_channel)
    def add_channel_trigger(self, channel_name, channel_number):
        self.trigger_channel = channel(channel_name, write_function=lambda value: self._send_trigger(channel_number, value))
        self.trigger_channel.add_preset('TRIGGER', 'Send Trigger')
        self.trigger_channel.add_preset('STANDBY', 'Waiting for Trigger')
        return self._add_channel(self.trigger_channel)
    def add_channel_cycle_count(self, channel_name, channel_number):
        new_channel = channel(channel_name, write_function=lambda cycle_count: self._write_cycle_count(channel_number, cycle_count))
        new_channel.add_preset('1', 'Default Value')
        return self._add_channel(new_channel)
    def _write_output_enable(self, channel_number, output_enable):
        self.instrument.write((f"OUTPut{channel_number}:STATE {output_enable}").encode())
    def _write_low_voltage(self, channel_number, low_voltage):
        self.instrument.write((f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:LOW {low_voltage}").encode())
    def _write_high_voltage(self, channel_number, high_voltage):
        self.instrument.write((f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:HIGH {high_voltage}").encode())
    def _write_pulse_width(self, channel_number, pulse_width):
        self.instrument.write((f"SOURce{channel_number}:PULSe:WIDTh {pulse_width}").encode())
    def _write_pulse_period(self, channel_number, period):
        self.instrument.write((f"SOURce{channel_number}:PULSe:PERiod {period}").encode())
    def _write_pulse_transition_leading(self, channel_number, transition):
        self.instrument.write((f"SOURce{channel_number}:PULSe:TRANsition:LEADing {transition}").encode())
    def _write_pulse_transition_trailing(self, channel_number, transition):
        self.instrument.write((f"SOURce{channel_number}:PULSe:TRANsition:TRAiling {transition}").encode())
    def _write_cycle_count(self, channel_number, cycle_count):
        self.instrument.write((f"SOURce{channel_number}:BURSt:NCYCles {cycle_count}").encode())
    def _send_trigger(self, channel_number, value):
        if value == "TRIGGER":
            self.instrument.write(f"TRIGger{channel_number}:IMMediate")
            # self.trigger()
            # self.operation_complete()
            self.trigger_channel.write("STANDBY") # sets the trigger channel back to STANDBY when OPeration Complete
            
            