from ..lab_core import *
import time

class tektronix_afg3022(scpi_instrument):
    '''Arbitrary Function Generator - Tektronix AFG3022 '''
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'tektronix_afg3022'
        scpi_instrument.__init__(self,f"afg3022 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write("*RST")
        
    def add_channel_burst(self, channel_name, channel_number):
        enable_channel = self.add_generic_channels(channel_name, channel_number)    
        self.add_channel_burstwave_shape(channel_name + "_shape", channel_number)
        self.add_channel_burstwave_low_voltage(channel_name + "_low_voltage", channel_number)
        self.add_channel_burstwave_high_voltage(channel_name + "_high_voltage", channel_number)
        self.add_channel_burstwave_pulse_width(channel_name + "_pulse_width", channel_number)
        self.add_channel_burstwave_period(channel_name + "_period", channel_number)
        self.add_channel_burstwave_pulse_hold(channel_name + "_pulse_hold", channel_number)
        self.add_channel_burstwave_rise_time(channel_name + "_risetime", channel_number)
        self.add_channel_burstwave_fall_time(channel_name + "_falltime", channel_number)
        self.add_channel_burstwave_cycles(channel_name + "_cycles", channel_number)
        self.add_channel_burstwave_trigger(channel_name + "_trigger", channel_number)
        self.get_interface().write(f"SOURce{channel_number}:BURSt:MODE TRIGgered")
        self.get_interface().write(f"TRIGger:SEQuence:SOURce EXTernal")
        self.get_interface().write(f"SOURce{channel_number}:BURSt:STATe ON")
        return enable_channel

    def add_channel_continuous(self, channel_name, channel_number):
        enable_channel = self.add_generic_channels(channel_name, channel_number)
        self.add_channel_continuouswave_shape(channel_name + "_shape", channel_number)
        self.add_channel_continuouswave_low_voltage(channel_name + "_low_voltage", channel_number)
        self.add_channel_continuouswave_high_voltage(channel_name + "_high_voltage", channel_number)
        self.add_channel_continuouswave_width(channel_name + "_pulse_width", channel_number)
        self.add_channel_continuouswave_period(channel_name + "_period", channel_number)
        self.add_channel_continuouswave_pulse_hold(channel_name + "_pulse_hold", channel_number)
        self.add_channel_continuouswave_rise_time(channel_name + "_risetime", channel_number)
        self.add_channel_continuouswave_fall_time(channel_name + "_falltime", channel_number)
        return enable_channel
        
    def add_generic_channels(self, channel_name, channel_number):
        if channel_number not in [1,2]:
            raise(f"\n\nTektronix AFG3022 only has two channels, there's no channel {channel_number} to assign to {channel_name}.\n")
        enable_channel = self.add_channel_enable(channel_name + "_enable", channel_number)
        self.add_channel_outputz(channel_name + "_load", channel_number)
        return enable_channel

    def add_channel_enable(self, channel_name, channel_number):
        def _write_output_enable(channel_number, value):
            if value in [True, False]:
                value = 'ON' if value else 'OFF'
            if str(value).upper() in ["TRUE", "FALSE"]:
                value = 'ON' if str(value).upper()== 'TRUE' else 'OFF'
            if str(value).upper() not in ['ON','OFF']:
                value = 'ON' if value else 'OFF' # Best guess but at least no SCPI error.
            self.get_interface().write(f"OUTPut{channel_number}:STATE {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_output_enable(channel_number, value))
        new_channel.add_preset('ON', 'Output Enabled')
        new_channel.add_preset('OFF', 'Output Disabled')
        return self._add_channel(new_channel)
        
    def add_channel_outputz(self, channel_name, channel_number):        
        def _write_outputz(channel_number, value):
            self.high_voltage = self.get_interface().ask(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:HIGH?")
            self.low_voltage  = self.get_interface().ask(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:LOW?")
            if value in ["INF", "INFinity", "HZ"]: # 'HZ' siglent_SDG1000X valid argument
                value = "INFinity"
            self.get_interface().write(f"OUTPut{channel_number}:IMPedance {value}")
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:HIGH {self.high_voltage}")
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:LOW {self.low_voltage}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_outputz(channel_number, value))
        new_channel.add_preset(50, 'Expect a 50Ω load. Output voltage scaled accordingly given its fixed 50Ω source impedance.')
        new_channel.add_preset("MAXimum", 'Set load impedance to 10KΩ')
        new_channel.add_preset("INFinity", 'Set load impedance to >10KΩ')
        new_channel.add_preset("MINimum", 'Set load impedance to 1Ω')
        return self._add_channel(new_channel)
    
    def add_channel_burstwave_shape(self, channel_name, channel_number):
        '''Instrument supports SINusoid|SQUare|PULSe|RAMP|DC|SINC|GAUSsian|LORentz|ERISe|EDECay|HAVersine|USER[1]|USER2|USER3|USER4|EMEMory[1]|EMEMory2|EFILe}
        Driver currently supports SINusoid|SQUare|PULSe|RAMP only'''
        def _write_burstwave_shape(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:FUNCtion:SHAPe {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_shape(channel_number, value))
        new_channel.add_preset("SQUARE",    'Square Waveform')
        new_channel.add_preset("RAMP",      'Ramp Waveform')
        new_channel.add_preset("PULSE",     'Pulsatile Waveform')
        new_channel.add_preset("SINUSOID",     'Sinusoidal Waveform')
        return self._add_channel(new_channel)

    def add_channel_burstwave_low_voltage(self, channel_name, channel_number):
        def _write_burstwave_low_voltage(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:LOW {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_low_voltage(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_high_voltage(self, channel_name, channel_number):
        def _write_burstwave_high_voltage(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:HIGH {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_high_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_pulse_width(self, channel_name, channel_number):
        def _write_burstwave_width(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:WIDTh {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_width(channel_number, value))
        new_channel.add_preset('30e-9', 'Minimum Value')
        new_channel.set_min_write_limit(30e-9)
        return self._add_channel(new_channel)
    
    def add_channel_burstwave_period(self, channel_name, channel_number):
        def _write_burstwave_period(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:PERiod {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_period(channel_number, value))
        return self._add_channel(new_channel)
    
    def add_channel_burstwave_pulse_hold(self, channel_name, channel_number):
        def _write_burstwave_pulse_hold(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:HOLD {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_pulse_hold(channel_number, value))
        new_channel.add_preset("WIDTh",     "Hold Pulse Width")
        new_channel.add_preset("DUTY",      "Hold Duty Cycle")
        return self._add_channel(new_channel)
    
    def add_channel_burstwave_rise_time(self, channel_name, channel_number):
        def _write_burstwave_rise_time(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:TRANsition:LEADing {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_rise_time(channel_number, value))
        new_channel.add_preset('18e-9', 'Minimum Value')
        new_channel.set_min_write_limit(18e-9)
        return self._add_channel(new_channel)

    def add_channel_burstwave_fall_time(self, channel_name, channel_number):
        def _write_burstwave_fall_time(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:TRANsition:TRAiling {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_fall_time(channel_number, value))
        new_channel.add_preset('18e-9', 'Minimum Value')
        new_channel.set_min_write_limit(18e-9)
        return self._add_channel(new_channel)

    def add_channel_burstwave_cycles(self, channel_name, channel_number):
        def _write_burstwave_cycles(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:BURSt:NCYCles {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_cycles(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_trigger(self, channel_name, channel_number):
        '''Sends trigger for all active channels regardless of channel_name or channel_number'''
        def _send_burstwave_trigger(channel_number, value):
            if value.upper() == "TRIGGER":
                self.trigger()
                self.operation_complete()
            else:
                raise Exception(f"Valid value for Pulse trigger channel on channel #{channel_number} is TRIGGER, don't know what {value} is supposed to do.")
        self.trigger_channel = channel(channel_name, write_function=lambda value: _send_burstwave_trigger(channel_number, value))
        self.trigger_channel._read = lambda : "STANDBY"
        self.trigger_channel.add_preset('TRIGGER', 'Send Trigger')
        self.trigger_channel.add_preset('STANDBY', 'Waiting for Trigger')
        return self._add_channel(self.trigger_channel)

    def add_channel_continuouswave_shape(self, channel_name, channel_number):
        '''Instrument supports SINusoid|SQUare|PULSe|RAMP|PRNoise|DC|SINC|GAUSsian|LORentz|ERISe|EDECay|HAVersine|USER[1]|USER2|USER3|USER4|EMEMory[1]|EMEMory2|EFILe}
        Driver currently supports SINusoid|SQUare|PULSe|RAMP|PRNoise only'''
        def _write_continuouswave_shape(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:FUNCtion:SHAPe {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_shape(channel_number, value))
        new_channel.add_preset("SQUARE",    'Square Waveform')
        new_channel.add_preset("RAMP",      'Ramp Waveform')
        new_channel.add_preset("PULSE",     'Pulsatile Waveform')
        new_channel.add_preset("SINUSOID",     'Sinusoidal Waveform')
        new_channel.add_preset("PRNOISE",     'Noise Waveform')
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_low_voltage(self, channel_name, channel_number):
        def _write_continuouswave_low_voltage(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:LOW {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_low_voltage(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_continuouswave_high_voltage(self, channel_name, channel_number):
        def _write_continuouswave_high_voltage(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:VOLTage:LEVel:IMMediate:HIGH {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_high_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_width(self, channel_name, channel_number):
        def _write_continuouswave_width(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:WIDTh {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_width(channel_number, value))
        new_channel.add_preset('30e-9', 'Minimum Value')
        new_channel.set_min_write_limit(30e-9)
        return self._add_channel(new_channel)
    
    def add_channel_continuouswave_period(self, channel_name, channel_number):
        def _write_continuouswave_period(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:PERiod {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_period(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_pulse_hold(self, channel_name, channel_number):
        def _write_continuouswave_pulse_hold(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:HOLD {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_pulse_hold(channel_number, value))
        new_channel.add_preset("WIDTh",     "Hold Pulse Width")
        new_channel.add_preset("DUTY",      "Hold Duty Cycle")
        return self._add_channel(new_channel)
    
    def add_channel_continuouswave_rise_time(self, channel_name, channel_number):
        def _write_continuouswave_rise_time(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:TRANsition:LEADing {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_rise_time(channel_number, value))
        new_channel.add_preset('18e-9', 'Minimum Value')
        new_channel.set_min_write_limit(18e-9)
        return self._add_channel(new_channel)

    def add_channel_continuouswave_fall_time(self, channel_name, channel_number):
        def _write_continuouswave_fall_time(channel_number, value):
            self.get_interface().write(f"SOURce{channel_number}:PULSe:TRANsition:TRAiling {value}")
            self.operation_complete()
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_fall_time(channel_number, value))
        new_channel.add_preset('18e-9', 'Minimum Value')
        new_channel.set_min_write_limit(18e-9)
        return self._add_channel(new_channel)
