from ..lab_core import *
from PyICe.lab_utils.banners import print_banner
from collections import OrderedDict # Not needed in Python 3 but signals to us that order matters.
from pyvisa.errors import VisaIOError
import time
    
class SiglentIOError(Exception):
    '''Unused at this time.'''

class siglent_SDG1000X(scpi_instrument):
    ''' Siglent Function Generator
        Since it's a two channel instrument reset() needs to be called manually rather than upon creation of each driver object.'''
        
    def __init__(self, instrument_visa):
        '''instrument_visa'''
        self._base_name = 'SDG1000X'
        scpi_instrument.__init__(self, f"SDG1000X @ {instrument_visa}")
        self.add_interface_visa(instrument_visa)
        self.instrument = self.get_interface()
        self.activity_log = OrderedDict()  # Keep an activity log in an attempt to recover from random I/O crashes.
        self.low_voltage = 0
        self.high_voltage = 0

    def append_activity_log(self, command, argument):
        if command in self.activity_log:
            self.activity_log.move_to_end(command)
        self.activity_log[command] = command + argument  # Now it's at the end either appened or edited

    def _try_command(self, command, argument):
        self.append_activity_log(command, argument)
        try:
            self.instrument.write(command+argument)
            self.operation_complete()
        except VisaIOError as e:
            print_banner("Siglent SDG1000X Crashed!!!","Attempting to Recover Siglent....", f"Last attempted command was: {command}")
            # input("\n\nThis Shouldn't be here!!! Used only for manual USB removal debugging method. See Steve. Hit Enter to Continue... ")
            try:
                self.instrument.read() # Super cheezy buffer flush? Siglent seems to like this.
            except:
                print_banner("Siglent extra read failed to clear stuck instrument.","Trying again...")
            # self.flush(buffer="READ")          # Doesn't seem to help here
            # self.flush(buffer="WRITE")         # Doesn't seem to help here
            # self.reset()
            self._try_command(command, argument)          # Recursion, possible maximum depth error if unrecoverable !!!
            # lab_utils.egg_timer(timeout=20, message=None, length=30, display_callback=None) # How long is really needed if any?
            # for entry in self.activity_log:
                # self._try_command(self.activity_log[entry])
            # raise SiglentIOError(lab_utils.build_banner('Siglent successfully reset and values restored after IO error.')) from e # REMOVE THIS !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            print_banner("Siglent SDG1000X Recovered!!!")

    def add_channel_burst(self, channel_name, channel_number):
        enable_channel = self.add_generic_channels(channel_name, channel_number)
        self.add_channel_phase_mode(channel_name + "_phase_mode")
        self.add_channel_burstwave_state(channel_name + "_state", channel_number)
        self.add_channel_burstwave_gate_ncyc(channel_name + "_gate_ncyc", channel_number)
        self.add_channel_burstwave_trigger_source(channel_name + "_trigger_source", channel_number)
        self.add_channel_burstwave_trigger_out_mode(channel_name + "_trigger_out_mode", channel_number)
        self.add_channel_burstwave_cycles(channel_name + "_cycles", channel_number)
        self.add_channel_burstwave_trigger_delay(channel_name + "_trigger_delay", channel_number)
        self.add_channel_burstwave_shape(channel_name + "_shape", channel_number)
        self.add_channel_burstwave_low_voltage(channel_name + "_low_voltage", channel_number)
        self.add_channel_burstwave_high_voltage(channel_name + "_high_voltage", channel_number)
        self.add_channel_burstwave_pulse_width(channel_name + "_pulse_width", channel_number)
        self.add_channel_burstwave_rise_time(channel_name + "_risetime", channel_number)
        self.add_channel_burstwave_fall_time(channel_name + "_falltime", channel_number)
        self.add_channel_burstwave_period(channel_name + "_period", channel_number)
        self.add_channel_burstwave_delay(channel_name + "_delay", channel_number)
        self.add_channel_burstwave_trigger(channel_name + "_trigger", channel_number)
        return enable_channel
        
    def add_channel_continuous(self, channel_name, channel_number):
        enable_channel = self.add_generic_channels(channel_name, channel_number)
        self.add_channel_continuouswave_shape(channel_name + "_shape", channel_number)
        self.add_channel_continuouswave_low_voltage(channel_name + "_low_voltage", channel_number)
        self.add_channel_continuouswave_high_voltage(channel_name + "_high_voltage", channel_number)
        self.add_channel_continuouswave_width(channel_name + "_pulse_width", channel_number)
        self.add_channel_continuouswave_period(channel_name + "_period", channel_number)
        self.add_channel_continuouswave_rise_time(channel_name + "_risetime", channel_number)
        self.add_channel_continuouswave_fall_time(channel_name + "_falltime", channel_number)
        return enable_channel
        
    def add_generic_channels(self, channel_name, channel_number):
        if channel_number not in [1,2]:
            raise(f"\n\nSiglent SDG1000X only has two channels, there's no channel {channel_number} to assign to {channel_name}.\n")
        enable_channel = self.add_channel_enable(f'{channel_name}_enable', channel_number)
        self.add_channel_outputz(f'{channel_name}_load', channel_number)
        return enable_channel
        
    def add_channel_enable(self, channel_name, channel_number):
        def _write_output_enable(channel_number, value):
            command     = f"C{channel_number}:OUTP"
            argument    = " ON" if value else " OFF"
            self._try_command(command, argument)
        new_channel = integer_channel(channel_name, size=1, write_function=lambda value: _write_output_enable(channel_number, value))
        new_channel.set_write_delay(0.1)
        return self._add_channel(new_channel)
        
    def add_channel_outputz(self, channel_name, channel_number):
        def _write_outputz(channel_number, value):
            command     = f"C{channel_number}:OUTP LOAD,"
            argument    = f"{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_outputz(channel_number, value))
        new_channel.add_preset(50, 'Expect a 50Ω load. Output voltage scaled accordingly given its fixed 50Ω source impedance.')
        new_channel.add_preset("HZ", 'Expect an infinite load. Output voltage scaled accordingly given its high impedance source impedance.')
        return self._add_channel(new_channel)
        
    def add_channel_DC(self, channel_name, channel_number):
        def _write_DC(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe WVTP,DC,OFST"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_DC(channel_number, value))
        new_channel.set_write_resolution(decimal_digits=6)
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_gate_ncyc(self, channel_name, channel_number):
        def _write_burstwave_gate_ncyc(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe GATE_NCYC"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_gate_ncyc(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_state(self, channel_name, channel_number):
        def _write_burstwave_state(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe STATE"
            argument    = ",ON" if value else ",OFF"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_state(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_trigger_source(self, channel_name, channel_number):
        def _write_burstwave_trigger_source(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe TRSR"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_trigger_source(channel_number, value))
        new_channel.add_preset("MAN", 'MAN')
        new_channel.add_preset("EXT", 'EXT')
        new_channel.add_preset("INT", 'INT')
        return self._add_channel(new_channel)

    def add_channel_burstwave_trigger_out_mode(self, channel_name, channel_number):
        def _write_burst_trigger_out_mode(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe TRMD"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burst_trigger_out_mode(channel_number, value))
        new_channel.add_preset('RISE', 'RISE')
        new_channel.add_preset('FALL', 'FALL')
        new_channel.add_preset('OFF', 'OFF')
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_cycles(self, channel_name, channel_number):
        def _write_burstwave_cycles(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe TIME" # When BursTWaVe GATE_NCYC,NCYC; 'TIME' is cycle count
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_cycles(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_trigger_delay(self, channel_name, channel_number):
        def _write_burstwave_trigger_delay(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe DLAY"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_trigger_delay(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_shape(self, channel_name, channel_number):
        def _write_burstwave_shape(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe CARR,WVTP"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_shape(channel_number, value))
        new_channel.add_preset("SINE",      'Sine Waveform')
        new_channel.add_preset("SQUARE",    'Square Waveform')
        new_channel.add_preset("RAMP",      'Ramp Waveform')
        new_channel.add_preset("PULSE",     'Pulsatile Waveform')
        new_channel.add_preset("NOISE",     'Noise Waveform')
        new_channel.add_preset("ARB",       'Arbitrary Waveform')
        new_channel.add_preset("DC",        'DC Waveform')
        new_channel.add_preset("PRBS",      'PRBS (?) Waveform')
        return self._add_channel(new_channel)

    def _set_offset_and_amplitude(self, channel_number):
        offset_command      = f"C{channel_number}:BursTWaVe CARR,OFST"
        offset_argument     = f",{(self.low_voltage+self.high_voltage)/2.}"
        self._try_command(offset_command, offset_argument)
        amplitude_command   = f"C{channel_number}:BursTWaVe CARR,AMP"
        amplitude_argument  = f",{self.high_voltage-self.low_voltage}"
        self._try_command(amplitude_command, amplitude_argument)
        
    def add_channel_burstwave_low_voltage(self, channel_name, channel_number):
        def _write_burstwave_low_voltage(channel_number, value):
            self.low_voltage = value
            self._set_offset_and_amplitude(channel_number)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_low_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_high_voltage(self, channel_name, channel_number):
        def _write_burstwave_high_voltage(channel_number, value):
            self.high_voltage = value            
            self._set_offset_and_amplitude(channel_number)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_high_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_pulse_width(self, channel_name, channel_number):
        def _write_burstwave_width(channel_number, value):
            frequency_command   = f"C{channel_number}:BursTWaVe CARR,FRQ"
            frequency_argument  = f",{0.5/value}"
            duty_command        = f"C{channel_number}:BursTWaVe CARR,DUTY"
            duty_argument       = f",{50}"
            self._try_command(frequency_command, frequency_argument)
            self._try_command(duty_command, duty_argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_width(channel_number, value))
        new_channel.add_preset('32.6e-9', 'Minimum Value')
        new_channel.set_min_write_limit(32.6e-9)
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_period(self, channel_name, channel_number):
        def _write_burstwave_period(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe CARR, PERI"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_period(channel_number, value))
        new_channel.set_write_resolution(decimal_digits=10) #100ps resolution
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_rise_time(self, channel_name, channel_number):
        def _write_burstwave_rise_time(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe CARR,RISE"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_rise_time(channel_number, value))
        new_channel.add_preset('16.8e-9', 'Minimum Value')
        new_channel.set_min_write_limit(16.8e-9)
        return self._add_channel(new_channel)
        
    def add_channel_burstwave_fall_time(self, channel_name, channel_number):
        def _write_burstwave_fall_time(channel_number, value):
            command = f"C{channel_number}:BursTWaVe CARR,FALL"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_fall_time(channel_number, value))
        new_channel.add_preset('16.8e-9', 'Minimum Value')
        new_channel.set_min_write_limit(16.8e-9)
        return self._add_channel(new_channel)

    def add_channel_burstwave_delay(self, channel_name, channel_number):
        def _write_burstwave_delay(channel_number, value):
            command     = f"C{channel_number}:BursTWaVe CARR,DLY"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_burstwave_delay(channel_number, value))
        return self._add_channel(new_channel)

    def add_channel_burstwave_trigger(self, channel_name, channel_number):
        def _send_burstwave_trigger(channel_number, value):
            if value.upper() == "TRIGGER":
                command     = f"C{channel_number}:BursTWaVe MTRIG"
                argument    = ""
                self._try_command(command, argument)
            else:
                raise Exception(f"\nValid value for Pulse trigger channel on channel #{channel_number} is TRIGGER, don't know what {value} is supposed to do.")
        self.trigger_channel = channel(channel_name, write_function=lambda value: _send_burstwave_trigger(channel_number, value))
        self.trigger_channel._read = lambda : "STANDBY"
        self.trigger_channel.add_preset('TRIGGER', 'Send Trigger')
        self.trigger_channel.add_preset('STANDBY', 'Waiting for Trigger')
        return self._add_channel(self.trigger_channel)
        
    def add_channel_continuouswave_shape(self, channel_name, channel_number):
        def _write_continuouswave_shape(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe WVTP"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_shape(channel_number, value))
        new_channel.add_preset("SINE",      'Sine Waveform')
        new_channel.add_preset("SQUARE",    'Square Waveform')
        new_channel.add_preset("RAMP",      'Ramp Waveform')
        new_channel.add_preset("PULSE",     'Pulsatile Waveform')
        new_channel.add_preset("NOISE",     'Noise Waveform')
        new_channel.add_preset("ARB",       'Arbitrary Waveform')
        new_channel.add_preset("DC",        'DC Waveform')
        new_channel.add_preset("PRBS",      'PRBS (?) Waveform')
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_low_voltage(self, channel_name, channel_number):
        def _write_continuouswave_low_voltage(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe LLEV"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_low_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_high_voltage(self, channel_name, channel_number):
        def _write_continuouswave_high_voltage(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe HLEV"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_high_voltage(channel_number, value))
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_width(self, channel_name, channel_number):
        def _write_continuouswave_width(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe WIDTH"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_width(channel_number, value))
        new_channel.add_preset('32.6e-9', 'Minimum Value')
        new_channel.set_min_write_limit(32.6e-9)
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_period(self, channel_name, channel_number):
        def _write_continuouswave_period(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe PERI"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_period(channel_number, value))
        new_channel.set_write_resolution(decimal_digits=10) #100ps resolution
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_rise_time(self, channel_name, channel_number):
        def _write_continuouswave_rise_time(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe RISE"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_rise_time(channel_number, value))
        new_channel.add_preset('16.8e-9', 'Minimum Value')
        new_channel.set_min_write_limit(16.8e-9)
        return self._add_channel(new_channel)
        
    def add_channel_continuouswave_fall_time(self, channel_name, channel_number):
        def _write_continuouswave_fall_time(channel_number, value):
            command     = f"C{channel_number}:BaSic_WaVe FALL"
            argument    = f",{value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_continuouswave_fall_time(channel_number, value))
        new_channel.add_preset('16.8e-9', 'Minimum Value')
        new_channel.set_min_write_limit(16.8e-9)
        return self._add_channel(new_channel)
        
    def add_channel_phase_mode(self, channel_name):
        def _write_phase_mode(value):
            if value.upper() not in ["INDEPENDENT", "PHASE-LOCKED"]:
                raise Exception(f"\nValid values for the Phase Mode channel are INDEPENDENT and PHASE-LOCKED, don't know what {value} is supposed to do.")
            command     = f"MODE"
            argument    = f" {value}"
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_phase_mode(value))
        new_channel.add_preset('INDEPENDENT', 'INDEPENDENT')
        new_channel.add_preset('PHASE-LOCKED', 'PHASE-LOCKED')
        return self._add_channel(new_channel)
        
    def add_channel_sync_out(self, channel_name, channel_number):
        def _write_sync_out(channel_number, value):
            command     = f"C{channel_number}:SYNC"
            argument    = f' {"ON" if value else "OFF"}'
            self._try_command(command, argument)
        new_channel = channel(channel_name, write_function=lambda value: _write_sync_out(channel_number, value))
        new_channel.add_preset('ON', 'ON')
        new_channel.add_preset('OFF', 'OFF')
        return self._add_channel(new_channel)

