from ..lab_core import *
from PyICe.lab_utils.eng_string import eng_string
import struct
import time
import datetime
try:
    from numpy import fromiter, dtype
    numpy_missing = False
except ImportError as e:
    numpy_missing = True

class u2300aBufferOverflowError(Exception):
    """Device ran out of memory."""
class u2300aBufferUnderflowError(Exception):
    """Python Deque is empty."""

class u2300a_scope(scpi_instrument,delegator):
    '''superclass of all Keysight U2300A series instruments treated as scope'''
    def __init__(self,interface_visa, force_trigger = False, timeout = 1, trigger_timeout=10):
        self._base_name = 'U2300A'
        scpi_instrument.__init__(self,f"{self._base_name} @ {interface_visa}")
        delegator.__init__(self)  # Clears self._interfaces list, so must happen before add_interface_visa(). --FL 12/21/2016
        self.add_interface_visa(interface_visa, timeout = timeout)
        self._configured_channels = {}
        self._last_scan_internal_addresses = None
        self._waveform_channel_types = ['ain_single_ended_bipolar', 'ain_diff_bipolar', 'ain_single_ended_unipolar', 'ain_diff_unipolar']
        self.reset()
        self._ain_configuration = {'sample_rate'      : 'MAX',
                                   'acquisition_time' : 'MIN',
                                  }
        self.set_trigger(None)
        self._states = [None, 'IDLE', 'ARMED'] #, 'TRIGGERED', 'ACQUISITION_COMPLETE']
        self._state = None
        self.set_burst_mode(True)
        self._trigger_timeout = trigger_timeout #None for no limit
    def _set_state(self, state):
        assert state in self._states
        #Check that transition is allowed
        if state == 'IDLE':
            assert self._state in ['ARMED']
        elif state == 'ARMED':
            assert self._state in ['IDLE', None]
        self._state = state
    def check_errors(self):
        err = self.get_interface().ask("SYST:ERR?")#Check that nothing has gone wrong with configuration
        if err != '+0,"No error"':
            breakpoint()
            raise Exception(err)
    def _get_state(self):
        return self._state
    def calibrate(self):
        print(f'Begin {self.get_name()} calibration.')
        self.get_interface().write('CALibration:BEGin')
        self.get_interface().ask('*OPC?')
        print(f'End {self.get_name()} calibration.')
    def set_burst_mode(self, state):
        # ACQuire:BURSt <mode>
            # This command is used to set the burst mode of a multiplexer DAQ device. This
            # mode enables the DAQ device to simulate in simultaneous mode. It would perform
            # sampling measurements at the highest speed of the product capabilities.
        # mode Boolean 0|OFF|1|ON 0
        self.get_interface().write(f'ACQuire:BURSt {"ON" if state else "OFF"}')
    def add_channel_timeout(self, channel_name):
        '''add trigger timeout control channel'''
        new_ch = channel(channel_name,write_function=lambda v: setattr(self, _trigger_timeout, v))
        new_ch.set_attribute('u2300a_type','trigger_control')
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_timeout.__doc__)
        return self._add_channel(new_ch)
    def add_channel_time(self, channel_name):
        '''add timebase readback channel'''
        new_ch = channel(channel_name,read_function=self.dummy_read)
        new_ch.set_attribute('u2300a_type','ain_time')
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_time.__doc__)
        if not numpy_missing:
            new_ch._set_type_affinity('PyICeBLOB')
        else:
            new_ch._set_type_affinity('PyICeFloatList')
        return self._add_channel(new_ch)
    def add_channel_ain_single_ended_bipolar(self, channel_name, channel_num, sig_range):
        '''Add single ended, bipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['single_ended']
        assert channel_num - max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_single_ended_bipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='BIPolar')
        # self._set_sigtype(new_ch, sig_mode='SING') #Return to AI_GND
        self._set_sigtype(new_ch, sig_mode='NRS') #Return to AI_SENSE
        new_ch.set_attribute('scale_fn', self._scale_fn(new_ch))
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_single_ended_bipolar.__doc__)
        if not numpy_missing:
            new_ch._set_type_affinity('PyICeBLOB')
        else:
            new_ch._set_type_affinity('PyICeFloatList')
        return self._add_channel(new_ch)
    def add_channel_ain_diff_bipolar(self, channel_name, channel_num, sig_range):
        '''Add differential, bipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['differential']
        assert channel_num + max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_diff_bipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='BIPolar')
        self._set_sigtype(new_ch, sig_mode='DIFF')
        new_ch.set_attribute('scale_fn', self._scale_fn(new_ch))
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_diff_bipolar.__doc__)
        if not numpy_missing:
            new_ch._set_type_affinity('PyICeBLOB')
        return self._add_channel(new_ch)
    def add_channel_ain_single_ended_unipolar(self, channel_name, channel_num, sig_range):
        '''Add single ended, unipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['single_ended']
        assert channel_num - max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_single_ended_unipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='UNIPolar')
        # self._set_sigtype(new_ch, sig_mode='SING') #Return to AI_GND
        self._set_sigtype(new_ch, sig_mode='NRS') #Return to AI_SENSE
        new_ch.set_attribute('scale_fn', self._scale_fn(new_ch))
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_single_ended_unipolar.__doc__)
        if not numpy_missing:
            new_ch._set_type_affinity('PyICeBLOB')
        else:
            new_ch._set_type_affinity('PyICeFloatList')
        return self._add_channel(new_ch)
    def add_channel_ain_diff_unipolar(self, channel_name, channel_num, sig_range):
        '''Add differential, unipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['differential']
        assert channel_num + max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_diff_unipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='UNIPolar')
        self._set_sigtype(new_ch, sig_mode='DIFF')
        new_ch.set_attribute('scale_fn', self._scale_fn(new_ch))
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_diff_unipolar.__doc__)
        if not numpy_missing:
            new_ch._set_type_affinity('PyICeBLOB')
        return self._add_channel(new_ch)
    def set_trigger(self, trigger_channel, mode='POST', delay_count=None, polarity_condition='AHIG', high_threshold=1, low_threshold=1):
        ''''''
        # TRIGger:SOURce <mode>
        # This command is used to set the trigger source for input operations.
        # The valid options are:
            # – NONE: Immediate triggering.
            # – EXTD: Selects the external digital trigger (EXTD_AI_TRIG) pin as the triggering
                # source.
            # – EXTA: Selects the external analog trigger as the triggering source. See
                # “TRIGger:ATRIGger:SOURce” on page 189 for more information on setting the
                # analog trigger source.
            # – STRG: Star triggering.

        # TRIGger:ATRIGger:SOURce <mode>
        # This command is used to set the analog trigger source for the AI trigger control.
        # The valid options are:
        # – EXTAP: Selects the external analog trigger (EXTA_TRIG) pin as the analog
        # triggering source.
        # – SONE: Selects the first scanned channel of the multiplexing DAQ device as the
        # analog triggering source. The first channel in the instrument scan list will be
        # set as the analog trigger source.
        # mode Discrete EXTAP|SONE EXTAP
        if trigger_channel is None:
            # Immediate mode
            self.get_interface().write('TRIGger:SOURce NONE')
            self._trigger_source = None
        elif trigger_channel == 'extd' or trigger_channel == 'EXTD':
            # Selects the external digital trigger (EXTD_AI_TRIG) pin as the triggering source.
            self.get_interface().write('TRIGger:SOURce EXTD')
            self.get_interface().write('TRIGger:TYPe MID') #TODO!
            # TRIGger:DTRiGger:POLarity <mode>
            # This command is used to set the polarity of the DIO trigger control.
            # The valid options are:
            # – POS (Positive-edge triggering): The trigger signal is generated when a rising edge is detected in the digital signal.
            # – NEG (Negative-edge triggering): The trigger signal is generated when a falling edge is detected in the digital signal.
            # mode Discrete POS|NEG POS
            assert polarity_condition in ['POS', 'NEG']
            self.get_interface().write(f'TRIGger:DTRiGger:POLarity {polarity_condition}')
            self._trigger_source = 'EXTD'
        elif trigger_channel == 'exta' or trigger_channel == 'EXTA':
            # Selects the external analog trigger (EXTA_TRIG) pin as the triggering source.
            self.get_interface().write('TRIGger:SOURce EXTA')
            self.get_interface().write('TRIGger:ATRIGger:SOURce EXTAP')
            # TRIGger:ATRIGger:HTHReshold <value>
            # This command sets the high-threshold voltage of the AI trigger control.
            # value Numeric –10 V to 10 V 0 V
            assert high_threshold >= -10 and high_threshold <= 10
            self.get_interface().write(f'TRIGger:ATRIGger:HTHReshold {high_threshold}')
            # TRIGger:ATRIGger:LTHReshold <value>
            # This command is used to set the low-threshold voltage of the AI trigger control.
            # value Numeric –10 V to 10 V 0 V
            assert low_threshold >= -10 and low_threshold <= 10
            self.get_interface().write(f'TRIGger:ATRIGger:LTHReshold {low_threshold}')
            # TRIGger:TYPe <mode>
            # This command is used to set the trigger type for input operations.
            # The valid options are:
                # – POST (Post-trigger): Input is acquired immediately after the trigger condition is met.
                # – PRE (Pre-trigger): Input is acquired immediately and is stopped when the trigger condition is met.
                # – MID (Mid-trigger): Input is acquired before and after the trigger condition is met. The sample points acquired before and after the trigger is equally divided.
                # – DEL (Delay-trigger): Input is acquired when the delay count reaches zero. The delay count starts immediately after the trigger condition is met.
            assert mode in ['POST', 'PRE', 'MID', 'DEL']
            self.get_interface().write(f'TRIGger:TYPe {mode}')
            if mode == 'DEL':
                # TRIGger:DCouNT <value>
                    # This command is used to set the delay counter value. When the count reaches
                    # zero, the counter stops and the DAQ device starts acquiring data. The count set in
                    # the <value> parameter will be used when the input trigger type is set to DEL
                    # (delay-trigger). Set the clock source using the CONFigure:TIMEbase:SOURce
                    # command.
                    # value Numeric 0 to 2147483647 (31-bits)[a] 0
                assert delay_count >= 0 and delay_count < 2**31
                self.get_interface().write(f'TRIGger:DCouNT {delay_count}')
            # TRIGger:ATRIGger:CONDition
            # Syntax
            # TRIGger:ATRIGger:CONDition <mode>
            # This command is used to set the trigger condition for the AI trigger control.
            # The valid options are:
            # – AHIG: Above-High-Level triggering selected. The trigger signal is generated when the analog signal is higher than the high-threshold voltage.
            # – BLOW: Below-Low-Level triggering selected. The trigger signal is generated when the analog signal is lower than the low-threshold voltage.
            # – WIND: Window (inside region) triggering selected. The trigger signal is generated when the analog signal falls within the range of the high-threshold and low-threshold voltages.
            assert polarity_condition in ['AHIG', 'BLOW', 'WIND']
            self.get_interface().write(f'TRIGger:ATRIGger:CONDition {polarity_condition}')
            self._trigger_source = 'EXTA'
        elif trigger_channel.get_attribute('u2300a_type') in ['ain_diff_bipolar', 'ain_diff_unipolar', 'ain_single_ended_bipolar', 'ain_single_ended_unipolar']:
            self.get_interface().write('TRIGger:SOURce EXTA')
            self.get_interface().write('TRIGger:ATRIGger:SOURce SONE')
            assert mode in ['POST'] #MID mode not allowed in SONE trigger mode. See programmer manual page 190 and conflicting guidance in user manual page 77.
            self.get_interface().write(f'TRIGger:TYPe {mode}')
            # TRIGger:ATRIGger:HTHReshold <value>
            # This command sets the high-threshold voltage of the AI trigger control.
            # value Numeric –10 V to 10 V 0 V
            assert high_threshold >= -10 and high_threshold <= 10
            self.get_interface().write(f'TRIGger:ATRIGger:HTHReshold {high_threshold}')
            # TRIGger:ATRIGger:LTHReshold <value>
            # This command is used to set the low-threshold voltage of the AI trigger control.
            # value Numeric –10 V to 10 V 0 V
            assert low_threshold >= -10 and low_threshold <= 10
            self.get_interface().write(f'TRIGger:ATRIGger:LTHReshold {low_threshold}')
            # TRIGger:ATRIGger:CONDition
            # Syntax
            # TRIGger:ATRIGger:CONDition <mode>
            # This command is used to set the trigger condition for the AI trigger control.
            # The valid options are:
            # – AHIG: Above-High-Level triggering selected. The trigger signal is generated when the analog signal is higher than the high-threshold voltage.
            # – BLOW: Below-Low-Level triggering selected. The trigger signal is generated when the analog signal is lower than the low-threshold voltage.
            # – WIND: Window (inside region) triggering selected. The trigger signal is generated when the analog signal falls within the range of the high-threshold and low-threshold voltages.
            assert polarity_condition in ['AHIG', 'BLOW', 'WIND']
            self.get_interface().write(f'TRIGger:ATRIGger:CONDition {polarity_condition}')
            self._trigger_source = trigger_channel
        else:
            raise Exception("I don't know what to do. Perhaps driver is incomplete.")
        self.check_errors()
    def add_channels_trigger(self, base_name):
        '''Channel-ize options otherwise availabe from set_trigger() method. Unclear if there's a required order of operations that complicates this process. Untested.'''
        def trigger_config_ch_write(write_channel, value):
            vals = {}
            for other_channel in write_channel.get_attribute('trigger_related_channels'):
                vals[other_channel.get_attribute('trigger_config_type')] = other_channel.read()
            vals[write_channel.get_attribute('trigger_config_type')] = value
            self.set_trigger(**vals)
        def trigger_arm_ch_write(value):
            if value == "ARM":
                self.arm_trigger()
             # elif value == "FORCE":

        trigger_arm_ch = channel(name=base_name)
        trigger_arm_ch.set_attribute('trigger_config_type', 'arm')
        trigger_arm_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_arm_ch._write = trigger_arm_ch_write
        trigger_arm_ch._read = lambda : None
        trigger_arm_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_arm_ch.add_preset(preset_value='ARM', preset_description='Arms the DAQ to take a new reading.')
        self._add_channel(trigger_arm_ch)

        trigger_source_ch = channel(name=f'{base_name}_source')
        trigger_source_ch.set_attribute('trigger_config_type', 'trigger_channel')
        trigger_source_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_source_ch._write = lambda val: trigger_config_ch_write(trigger_source_ch, val)
        trigger_source_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_source_ch.add_preset(preset_value=None, preset_description='Immediate triggering')
        trigger_source_ch.add_preset(preset_value='EXTD', preset_description='Selects the external digital trigger (EXTD_AI_TRIG) pin as the triggering source.')
        trigger_source_ch.add_preset(preset_value='EXTA', preset_description='Selects the external analog trigger (EXTA_TRIG) pin as the triggering source.')
        for ain_ch in self._configured_channels.values():
            trigger_source_ch.add_preset(preset_value=ain_ch, preset_description=ain_ch.get_name())
        trigger_source_ch._set_value(None)
        self._add_channel(trigger_source_ch)

        trigger_mode_ch = channel(name=f'{base_name}_mode')
        trigger_mode_ch.set_attribute('trigger_config_type', 'mode')
        trigger_mode_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_mode_ch._write = lambda val: trigger_config_ch_write(trigger_mode_ch, val)
        trigger_mode_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_mode_ch.add_preset(preset_value='POST', preset_description='(Post-trigger): Input is acquired immediately after the trigger condition is met.')
        trigger_mode_ch.add_preset(preset_value='PRE', preset_description='(Pre-trigger): Input is acquired immediately and is stopped when the trigger condition is met.')
        trigger_mode_ch.add_preset(preset_value='MID', preset_description='(Mid-trigger): Input is acquired before and after the trigger condition is met. The sample points acquired before and after the trigger is equally divided.')
        trigger_mode_ch.add_preset(preset_value='DEL', preset_description='(Delay-trigger): Input is acquired when the delay count reaches zero. The delay count starts immediately after the trigger condition is met.')
        trigger_mode_ch._set_value('POST')
        self._add_channel(trigger_mode_ch)
        
        trigger_delay_count_ch = channel(name=f'{base_name}_delay')
        trigger_delay_count_ch.set_attribute('trigger_config_type', 'delay_count')
        trigger_delay_count_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_delay_count_ch._write = lambda val: trigger_config_ch_write(trigger_delay_count_ch, val)
        trigger_delay_count_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_delay_count_ch.set_max_write_limit(2**31)
        trigger_delay_count_ch._set_value(None)
        self._add_channel(trigger_delay_count_ch)
        
        trigger_polarity_condition_ch = channel(name=f'{base_name}_condition')
        trigger_polarity_condition_ch.set_attribute('trigger_config_type', 'polarity_condition')
        trigger_polarity_condition_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_polarity_condition_ch._write = lambda val: trigger_config_ch_write(trigger_polarity_condition_ch, val)
        trigger_polarity_condition_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_polarity_condition_ch.add_preset(preset_value='AHIG', preset_description='Above-High-Level triggering selected. The trigger signal is generated when the analog signal is higher than the high-threshold voltage.')
        trigger_polarity_condition_ch.add_preset(preset_value='BLOW', preset_description='Below-Low-Level triggering selected. The trigger signal is generated when the analog signal is lower than the low-threshold voltage.')
        trigger_polarity_condition_ch.add_preset(preset_value='WIND', preset_description='Window (inside region) triggering selected. The trigger signal is generated when the analog signal falls within the range of the high-threshold and low-threshold voltages.')
        trigger_polarity_condition_ch.add_preset(preset_value='POS', preset_description='(Positive-edge triggering): The trigger signal is generated when a rising edge is detected in the digital signal.')
        trigger_polarity_condition_ch.add_preset(preset_value='NEG', preset_description='(Negative-edge triggering): The trigger signal is generated when a falling edge is detected in the digital signal.')
        trigger_polarity_condition_ch._set_value('AHIG')
        self._add_channel(trigger_polarity_condition_ch)
        
        trigger_high_threshold_ch = channel(name=f'{base_name}_high_threshold')
        trigger_high_threshold_ch.set_attribute('trigger_config_type', 'high_threshold')
        trigger_high_threshold_ch.set_attribute('u2300a_type', 'cccc')
        trigger_high_threshold_ch._write = lambda val: trigger_config_ch_write(trigger_high_threshold_ch, val)
        trigger_high_threshold_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_high_threshold_ch.set_max_write_limit(10)
        trigger_high_threshold_ch.set_min_write_limit(-10)
        trigger_high_threshold_ch._set_value(1)
        self._add_channel(trigger_high_threshold_ch)
        
        trigger_low_threshold_ch = channel(name=f'{base_name}_low_threshold')
        trigger_low_threshold_ch.set_attribute('trigger_config_type', 'low_threshold')
        trigger_low_threshold_ch.set_attribute('u2300a_type', 'trigger_control')
        trigger_low_threshold_ch._write = lambda val: trigger_config_ch_write(trigger_low_threshold_ch, val)
        trigger_low_threshold_ch.set_description(self.get_name() + ': ' + self.add_channels_trigger.__doc__)
        trigger_low_threshold_ch.set_max_write_limit(10)
        trigger_low_threshold_ch.set_min_write_limit(-10)
        trigger_low_threshold_ch._set_value(1)
        self._add_channel(trigger_low_threshold_ch)
        
        trigger_source_ch.set_attribute('trigger_related_channels', [trigger_mode_ch, trigger_delay_count_ch, trigger_polarity_condition_ch, trigger_high_threshold_ch, trigger_low_threshold_ch])
        trigger_mode_ch.set_attribute('trigger_related_channels', [trigger_source_ch, trigger_delay_count_ch, trigger_polarity_condition_ch, trigger_high_threshold_ch, trigger_low_threshold_ch])
        trigger_delay_count_ch.set_attribute('trigger_related_channels', [trigger_source_ch, trigger_mode_ch, trigger_polarity_condition_ch, trigger_high_threshold_ch, trigger_low_threshold_ch])
        trigger_polarity_condition_ch.set_attribute('trigger_related_channels', [trigger_source_ch, trigger_mode_ch, trigger_delay_count_ch, trigger_high_threshold_ch, trigger_low_threshold_ch])
        trigger_high_threshold_ch.set_attribute('trigger_related_channels', [trigger_source_ch, trigger_mode_ch, trigger_delay_count_ch, trigger_polarity_condition_ch, trigger_low_threshold_ch])
        trigger_low_threshold_ch.set_attribute('trigger_related_channels', [trigger_source_ch, trigger_mode_ch, trigger_delay_count_ch, trigger_polarity_condition_ch, trigger_high_threshold_ch])
        
        return trigger_arm_ch
    def add_channel_acquisition_time(self, name):
        '''Channel-ize option otherwise availabe from set_acquisition_time() method.'''
        acq_time_ch = channel(name, write_function=self.set_acquisition_time)
        acq_time_ch.set_attribute('u2300a_type', 'ain_acquisition_control')
        acq_time_ch.set_description(self.get_name() + ': ' + self.add_channel_acquisition_time.__doc__)
        self._add_channel(acq_time_ch)
    def set_acquisition_time(self, acquisition_time):
        '''additional option "MAX", to auto-compute max record length'''
        # Don't do any configuration until trigger time to make sure configuration is fully self-consistent.
        self._ain_configuration['acquisition_time'] = acquisition_time
    def _set_acquisition_time(self, acquisition_time, sample_rate, channel_count):
        # ACQuire:POINts <value>
        # This command is used to set the number of acquisition points for the single-shot acquisition process.
        # value Numeric Maximum of 8 Msa 500
        if acquisition_time == 'MAX':
            point_count = self._ai_channels['max_record_length'] // channel_count
        elif acquisition_time == 'MIN':
            point_count = 1
        else:
            point_count = acquisition_time * self._compute_sample_rate(sample_rate, channel_count)
        point_count = max(int(point_count),1)
        assert point_count * channel_count <= self._ai_channels['max_record_length']
        self.get_interface().write(f'ACQuire:POINts {point_count}') # This is per-channel!
        self._point_count = point_count
    def add_channel_sample_rate(self, name):
        '''Channel-ize option otherwise availabe from set_sample_rate() method.'''
        acq_time_ch = channel(name, write_function=self.set_sample_rate)
        acq_time_ch.set_attribute('u2300a_type', 'ain_acquisition_control')
        acq_time_ch.set_description(self.get_name() + ': ' + self.add_channel_sample_rate.__doc__)
        self._add_channel(acq_time_ch)
    def set_sample_rate(self, sample_rate):
        '''units of Hz
        additional option "MAX", to auto-compute max performace
        '''
        # Don't do any configuration until trigger time to make sure configuration is fully self-consistent.
        self._ain_configuration['sample_rate'] = sample_rate
    def _set_sample_rate(self, sample_rate, channel_count):
        sample_rate = self._compute_sample_rate(sample_rate, channel_count)
        self.get_interface().write(f'ACQuire:SRATe {sample_rate}')
        self._sample_rate = sample_rate
    def _compute_sample_rate(self, sample_rate, channel_count):
                # ACQuire:SRATe <value>
            # This command is used to set the sampling rate of the analog input (AI) channels.
        # value Numeric
        # – U2351A/52A/55A:
            # 3 Hz to 250000 Hz (250 kHz)
        # – U2353A/54A/56A:
            # 3 Hz to 500000 Hz (500 kHz)
        # – U2331A: 3 Hz to 3000000 Hz (3 MHz) #NOTE DJS: Only 1e6 if channels are multiplexed.
        if sample_rate == 'MAX':
            if channel_count==1:
                sample_rate = self._ai_channels['max_sample_rate_single']
            else:
                sample_rate = self._ai_channels['max_sample_rate'] // channel_count
        elif sample_rate == 'MIN':
            sample_rate = 3
        sample_rate = int(sample_rate)
        assert sample_rate * channel_count <= (self._ai_channels['max_sample_rate'] if channel_count>1 else self._ai_channels['max_sample_rate_single'])
        assert sample_rate >= 3
        return sample_rate
    def dummy_read(self):
        raise Exception('Delegation failure. Contact PyICe-developers@analog.com for more information.')
    def _set_range(self, channel, sig_range, polarity):
        # (ROUTe:CHANnel:POLarity)
        # ROUTe:CHANnel:POLarity <mode>, <ch_list>
        # This command is used to set the polarity of the AI or AO channel(s) specified in the
        # <ch_list> parameter.
        # The valid options are:
            # – BIPolar
            # – UNIPolar
        if polarity.lower() in [pol.lower() for pol in ['BIPolar', 'BIP']]:
            polarity = 'bipolar'
            
        elif polarity.lower() in [pol.lower() for pol in ['UNIPolar', 'UNIP']]:
            polarity = 'unipolar'
        else:
            raise Exception('Uknown polarity')
        channel.set_attribute('polarity', polarity)
        self.get_interface().write(f'ROUTe:CHANnel:POLarity {polarity}, (@{channel.get_attribute("internal_address")})')
        assert sig_range in self._ai_channels[polarity]['range']
        channel.set_attribute('sig_range', sig_range)
        self.get_interface().write(f"ROUTe:CHANnel:RANGe {sig_range}, (@{channel.get_attribute('internal_address')})")
    def _set_sigtype(self, channel, sig_mode):
        # (ROUTe:CHANnel:STYPe)
        # ROUTe:CHANnel:STYPe <mode>, <ch_list>
        # This command is used to set the input signal type (reference ground selection) for
        # the AI channel(s) specified in the <ch_list> parameter.
        # The valid options are:
            # – SING: Referenced single-ended mode; 16 or 64 channels common to the
                # ground system (AI_GND pin) on board.
            # – DIFF: Differential mode.
            # – NRS: Non-referenced single-ended mode; 16 or 64 channels common to the
                # AI_SENSE pin.
            valid_modes = ['SING', 'DIFF', 'NRS']
            assert sig_mode.upper() in [mode.upper() for mode in valid_modes]
            channel.set_attribute('sig_mode', sig_mode)
            self.get_interface().write(f'ROUTe:CHANnel:STYPe {sig_mode}, (@{channel.get_attribute("internal_address")})')
    def _scale_fn(self, channel):
        '''speed up. Closure around immutable variables to aviod a whole bunch of attribute lookups inside a tight time-critical loop'''
        gains = self._ai_channels[channel.get_attribute('polarity')]['range'][channel.get_attribute('sig_range')]
        offset = 0.5 * (gains['max'] + gains['min'])
        return lambda x,lsb=gains['lsb'], offset=offset, shift=self._ai_channels['bit_offset']: lsb*(x>>shift) + offset
    def _scale_point(self, adc_raw, channel):
        '''TODO remove!'''
        print("Shouldn't be here....")
        return channel.get_attribute('scale_fn')(adc_raw)
    def arm_trigger(self, channel_list=None):
        if channel_list is None:
            #Without channel list, let's compromise and acquire every channel that this instrument has registered to date
            channel_list = self.get_all_channels_list()
        scan_internal_addresses = [channel.get_attribute('internal_address') for channel in filter(lambda ch: ch.get_attribute('u2300a_type') in self._waveform_channel_types, channel_list)]
        scan_internal_addresses = list(set(scan_internal_addresses)) # remove duplicates #TODO why??
        if isinstance(self._trigger_source, channel):
            #Move the trigger channel to front of scanlist. Won't work if repeated in scanlist!!
            scan_internal_addresses.remove(self._trigger_source.get_attribute('internal_address'))
            scan_internal_addresses.insert(0, self._trigger_source.get_attribute('internal_address'))
        #Special dance to make sure setup is always allowable in any order. May be optimizable later with some experimentation
        self._set_sample_rate(sample_rate=3, channel_count=len(scan_internal_addresses))
        self._set_acquisition_time(acquisition_time=1e-6, sample_rate=3, channel_count=len(scan_internal_addresses))
        cmd = "ROUTe:SCAN (@"
        for internal_address in scan_internal_addresses:
            cmd += str(internal_address) + ','
        cmd = cmd.rstrip(',') + ")"
        self.get_interface().write(cmd)
        self._last_scan_internal_addresses = scan_internal_addresses
        self._set_sample_rate(sample_rate=self._ain_configuration['sample_rate'], channel_count=len(scan_internal_addresses))
        self._set_acquisition_time(acquisition_time=self._ain_configuration['acquisition_time'], sample_rate=self._ain_configuration['sample_rate'], channel_count=len(scan_internal_addresses))
        self.check_errors()
        self._set_state('ARMED')
        self.get_interface().write('DIGitize')
    def read_delegated_channel_list(self,channel_list):
        # breakpoint()
        if self._get_state() == 'ARMED':
            #Already armed manually!
            pass
        else:
            self.arm_trigger(channel_list)
        # resp = self.get_interface().ask('WAVeform:STATus?')
        # while resp != 'DATA':
            # print(f'...{self.get_name()}: {resp}')
            # time.sleep(0.1)
            # # TODO: timeout??
            # resp = self.get_interface().ask('WAVeform:STATus?')
        arm_time = time.time()
        resp = self.get_interface().ask('WAVeform:COMPlete?')
        while resp != 'YES' and (self._trigger_timeout is None or (time.time()-arm_time) <= self._trigger_timeout):
            print(f'...{self.get_name()}: {resp}')
            time.sleep(0.1)
            # TODO: timeout??
            resp = self.get_interface().ask('WAVeform:COMPlete?')
        if resp == 'YES':
            self.get_interface().write('WAVeform:DATA?')
            raw_data = self.get_interface().read_raw() #I don't know why the binary drivers aren't working right. I get a response only 9 points long... Workaround for now rather than debug.
            self._set_state('IDLE')
            header = raw_data[:10]
            raw_data = raw_data[10:]
            assert header[:2] == b'#8'
            resp_len = int(header[2:])
            int_data_len = resp_len // 2 #Points from all channels
            fmt_str = '<' + 'h'* self._point_count * len(self._last_scan_internal_addresses)
            int_data = struct.unpack(fmt_str, raw_data)
            #TODO: what if a channel address appears twice or more in the scanlist??
        else:
            self._set_state('IDLE') # ???
            int_data = None
            print(f'{self._trigger_timeout}s : No trigger detected') ##might leave scope state armed. Dave and Scott looked at this and is unknown
        results = results_ord_dict()
        for ch in channel_list:
            if ch.get_attribute('u2300a_type') == 'ain_time':
                trig_mode = self.get_interface().ask(f'TRIGger:TYPe?')
                if trig_mode == 'POST':
                    int_points = range(self._point_count)
                elif trig_mode == 'MID':
                    int_points = list((map(lambda i: i-self._point_count//2, range(self._point_count))))
                elif trig_mode == 'PRE':
                    int_points = range(-self._point_count+1, 0+1)
                elif trig_mode == 'DEL':
                    raise Exception('Unimplemented')
                else:
                    breakpoint()
                    raise Exception('What happened?')
                assert len(int_points) == self._point_count
                if not numpy_missing:
                    results[ch.get_name()] = fromiter(map(lambda idx: idx / self._sample_rate, int_points), dtype=dtype('<d'))
                else:
                    results[ch.get_name()] = list(map(lambda idx: idx / self._sample_rate, int_points))
            elif ch.get_attribute('u2300a_type') in self._waveform_channel_types:
                if int_data is not None:
                    ch_idx = self._last_scan_internal_addresses.index(ch.get_attribute('internal_address'))
                    ch_data = (int_data[i] for i in range(ch_idx, len(int_data), len(self._last_scan_internal_addresses)))
                    if not numpy_missing:
                        results[ch.get_name()] = fromiter(map(lambda point, scale_f=ch.get_attribute('scale_fn'): scale_f(point), ch_data), dtype=dtype('<d'))
                    else:
                        results[ch.get_name()] = list(map(lambda point, scale_f=ch.get_attribute('scale_fn'): scale_f(point), ch_data))
                else:
                    # failed trigger
                    results[ch.get_name()] = None
            elif ch.get_attribute('u2300a_type') == 'trigger_control':
                if channel.get_attribute('trigger_config_type') == 'trigger_channel':
                    results[ch.get_name()] = ch.read()
                else:
                    results[ch.get_name()] = ch.read()
            else:
                raise Exception("U2300A: Don't know what to do yet.")
        return results
    def get_all_settings(self):
        result = results_ord_dict()
        result["syst_error"        ] = self.get_interface().ask("SYST:ERR?")
        result["trigger_condition" ] = self.get_interface().ask("TRIGger:ATRIGger:CONDition?")
        result["trigger_source"    ] = self.get_interface().ask("TRIGger:SOURce?")
        result["atrigger_source"   ] = self.get_interface().ask("TRIGger:ATRIGger:SOURce?")
        result["atrigger_threshold"] = self.get_interface().ask("TRIGger:ATRIGger:HTHReshold?")
        result["ltrigger_threshold"] = self.get_interface().ask("TRIGger:ATRIGger:LTHReshold?")
        result["channel_polarity"  ] = self.get_interface().ask(f"ROUTe:CHANnel:POLarity? (@101:{max(self._ai_channels['single_ended'])})")
        result["channel_range"     ] = self.get_interface().ask(f"ROUTe:CHANnel:RANGe? (@101:{max(self._ai_channels['single_ended'])})")
        result["rout_channel_stype"] = self.get_interface().ask(f"ROUTe:CHANnel:STYPe? (@101:{max(self._ai_channels['single_ended'])})")
        result["Point Count"       ] = self.get_interface().ask("ACQuire:POINts?")
        result["Sample Rate"       ] = self.get_interface().ask("ACQuire:SRATe?")
        result["Scan List"         ] = self.get_interface().ask("ROUTe:SCAN?")
        result["Trigger Type"      ] = self.get_interface().ask("TRIGger:TYPe?")
        return result

class u2300a_datalogger(u2300a_scope):
    def __init__(self,interface_visa, table_name, database_file="data_log.sqlite", timeout = 10):
        super().__init__(interface_visa=interface_visa, force_trigger=False, timeout=timeout)
        self.point_idx = 0
        self.logger = logger(channel_master_or_group=None, database=database_file, use_threads=True)
        self.logger.set_journal_mode(synchronous='OFF')
        self.table_name = table_name
        self.set_burst_mode(True)
    def log(self, record_time=0):
        self.logger.add_data_channels({ch.get_name(): None for ch in self.get_all_channels_list()})
        self.logger.new_table(table_name=self.table_name,replace_table=False,warn=False)
        idx_primes=[ch.get_name() for ch in self.get_all_channels_list() if ch.get_attribute('u2300a_type') == 'ain_time']
        for idx_prime in idx_primes:
            self.logger.execute(f'CREATE INDEX IF NOT EXISTS {self.table_name}_{idx_prime}_idx ON {self.table_name} ({idx_prime})')
        self.logger.execute(f'CREATE INDEX IF NOT EXISTS {self.table_name}_datetime_idx ON {self.table_name} (datetime)')
        self._setup()
        self.stopping=False
        self.stopped=False
        unhandled_exception_occurred=False
        databank=collections.deque()
        time.sleep(10)
        self.get_interface().write('RUN')
        while self.get_interface().ask('WAVeform:STATus?') != 'DATA':
            print(self.get_interface().ask('WAVeform:STATus?'))
        print("TRIG'D!")
        try:
            start_time=datetime.datetime.utcnow()           ## This is one block away from where we triggered.
            self.time_since=time.time()
            reset_clock=time.time()
            while True if record_time is None else (datetime.datetime.utcnow()-start_time).total_seconds()<record_time:
                data = self.read_all_channels()
                data['datetime']=(start_time+datetime.timedelta(seconds=data[idx_prime])).strftime('%Y-%m-%dT%H:%M:%S.%fZ') ## Repair datetime by means of DAQ_time
                # data['datetime']=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                if data is not None:
                    databank.append(data)
                time_now=time.time()
                if time_now-reset_clock>1:
                    print(f'Logging {len(databank)} rows')
                    reset_clock=time_now
                    self.logger.log_many(databank.copy())
                    databank.clear()
        except (KeyboardInterrupt, ) as e:
            print('Bye!')
        except u2300aBufferOverflowError as e:
            print(e)
        except Exception as e:
            print(e)
            unhandled_exception_occurred=True
        finally:
            self.get_interface().write('STOP')
            self.stopping=True
            self.stopped=True
            print(f"Acquisition stopped. There are {len(databank)} row(s) in the log queue. Some still need processing. One moment please.")
            try:
                while True:
                    data = self.read_all_channels()
                    data['datetime']=(start_time+datetime.timedelta(seconds=data['DAQ_time'])).strftime('%Y-%m-%dT%H:%M:%S.%fZ') ## Repair datetime by means of DAQ_time
                    # data['datetime']=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                    databank.append(data)
            except u2300aBufferUnderflowError:
                print(f'All channels processed. Logging the last {len(databank)} rows now.')
                self.logger.log_many(databank)
                ## This is passing mutable data pass the boundary, but we promise not to mutate it until it does what it needs to do.
                print(f"All data has been sent to logger thread. It took {(datetime.datetime.utcnow()-start_time).total_seconds()} seconds to log {record_time} seconds from the start. Thank you for your patience.")
            self.logger.stop()
            print(f'Logger thread complete. It took {(datetime.datetime.utcnow()-start_time).total_seconds()} seconds from the start.')
            databank.clear()    ## We expect the threads to be joined by now. 
            if unhandled_exception_occurred:
                raise e
            return
    def _setup(self):  
        scan_internal_addresses = [channel.get_attribute('internal_address') for channel in filter(lambda ch: ch.get_attribute('u2300a_type') in self._waveform_channel_types, self.get_all_channels_list())]
        scan_internal_addresses = list(set(scan_internal_addresses)) # remove duplicates #TODO why??
        #Special dance to make sure setup is always allowable in any order. May be optimizable later with some experimentation
        # self._set_sample_rate(sample_rate=3, channel_count=len(scan_internal_addresses))
        if isinstance(self._trigger_source, channel):
            #Move the trigger channel to front of scanlist. Won't work if repeated in scanlist!!
            scan_internal_addresses.remove(self._trigger_source.get_attribute('internal_address'))
            scan_internal_addresses.insert(0, self._trigger_source.get_attribute('internal_address'))
        channels = [f'{ch}' for ch in scan_internal_addresses]
        ch_str = f'(@{",".join(channels)})'
        self.get_interface().write(f"ROUTe:SCAN {ch_str}")
        self._last_scan_internal_addresses = scan_internal_addresses
        self._set_sample_rate(sample_rate=self._ain_configuration['sample_rate'], channel_count=len(scan_internal_addresses))
        self.data_buffer = {ia: collections.deque() for ia in scan_internal_addresses}
        self._point_count = int(self.get_interface().ask('ACQuire:SRATe?'))
        self.get_interface().write(f'WAVeform:POINts {self._point_count}') #Target ~1s update??
    def read_delegated_channel_list(self,channel_list):
        if self.stopped and not self.stopping:                                        ## This is just flushing the python queue into the database without talking to the instrument anymore. RHM
            return self._read_assist(channel_list)
        data_in_waiting=bool(len(next(iter(self.data_buffer.values()))))
        if time.time()-self.time_since>0.5 or not data_in_waiting or self.stopping:
            while True:
                resp = self.get_interface().ask('WAVeform:STATus?')
                if resp == 'DATA':
                    # Indicates that at least one block of data is completed and ready to be read back.
                    self.get_interface().write('WAVeform:DATA?')
                    raw_data = self.get_interface().read_raw() #I don't know why the binary drivers aren't working right. I get a response only 9 points long... Workaround for now rather than debug.
                    header = raw_data[:10]
                    raw_data = raw_data[10:]
                    assert header[:2] == b'#8'
                    resp_len = int(header[2:])
                    int_data_len = resp_len // 2 #Points from all channels
                    # fmt_str = '<' + 'h' * self._point_count * len(self._last_scan_internal_addresses)        ### Manual disagrees with itself.
                    fmt_str = '<' + 'h' * int_data_len
                    int_data = struct.unpack(fmt_str, raw_data)
                    for i,a in enumerate(self._last_scan_internal_addresses):
                        ch_data = (int_data[i] for i in range(i, len(int_data), len(self._last_scan_internal_addresses)))
                        self.data_buffer[a].extend(ch_data) #just unscaled integer readings; rescale later!
                    self.time_since=time.time()
                    self.stopping=False
                    break
                elif resp == 'FRAG':
                    if data_in_waiting:
                        break
                    # Fragment, indicates that the instrument has started to acquire data, but has yet to complete a single block of data.
                elif resp == 'EPTY':
                    if data_in_waiting:
                        break
                    # Empty, indicates that there is no data captured.
                elif resp == 'OVER':
                    # Indicates that the buffer is full and the acquisition is stopped.
                    raise u2300aBufferOverflowError('Too slow!')
                else:
                    raise Exception('Eh?')
        return self._read_assist(channel_list=channel_list)
    def _read_assist(self, channel_list):
        #TODO: what if a channel address appears twice or more in the scanlist??
        results = results_ord_dict()
        try:
            for ch in channel_list:
                if ch.get_attribute('u2300a_type') == 'ain_time':
                    results[ch.get_name()] = self.point_idx / self._sample_rate
                elif ch.get_attribute('u2300a_type') in self._waveform_channel_types:
                    # results[ch.get_name()] = self._scale_point(self.data_buffer[ch.get_attribute('internal_address')].popleft(), ch)
                    results[ch.get_name()] = ch.get_attribute('scale_fn')(self.data_buffer[ch.get_attribute('internal_address')].popleft())
                else:
                    raise Exception("U2300A: Don't know what to do yet.")
            self.point_idx += 1
        except IndexError as e:
            raise u2300aBufferUnderflowError from e
        else:
            return results

class u2300a_DVM(scpi_instrument,delegator):
    '''superclass of all Keysight U2300A series instruments treated as DVM'''
    def __init__(self,interface_visa, timeout = 1):
        # self._base_name = str(type(self))
        self._base_name = 'u23xx_DVM_DAQ'
        scpi_instrument.__init__(self,f"{self._base_name} @ {interface_visa}")
        delegator.__init__(self)  # Clears self._interfaces list, so must happen before add_interface_visa(). --FL 12/21/2016
        self.add_interface_visa(interface_visa, timeout = timeout)
        self._configured_channels = {}
        self._last_scan_internal_addresses = None
        self._waveform_channel_types = ['ain_single_ended_bipolar', 'ain_diff_bipolar', 'ain_single_ended_unipolar', 'ain_diff_unipolar']
        self.reset()
    def check_errors(self):
        err = self.get_interface().ask("SYST:ERR?")#Check that nothing has gone wrong with configuration
        if err != '+0,"No error"':
            breakpoint()
            raise Exception(err)
    def calibrate(self):
        print(f'Begin {self.get_name()} calibration.')
        self.get_interface().write('CALibration:BEGin')
        self.get_interface().ask('*OPC?')
        print(f'End {self.get_name()} calibration.')
    def add_channel_ain_single_ended_bipolar(self, channel_name, channel_num, sig_range):
        '''Add single ended, bipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['single_ended']
        assert channel_num - max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_single_ended_bipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='BIPolar')
        # self._set_sigtype(new_ch, sig_mode='SING') #Return to AI_GND
        self._set_sigtype(new_ch, sig_mode='NRS') #Return to AI_SENSE
        new_ch.set_attribute('scale_fn', self._scale_fn(new_ch))
        new_ch.set_display_format_function(function = lambda float_data: eng_string(float_data, fmt=':3.6g',si=True) + 'V')
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_single_ended_bipolar.__doc__)
        return self._add_channel(new_ch)
    def add_channel_ain_diff_bipolar(self, channel_name, channel_num, sig_range):
        '''Add differential, bipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['differential']
        assert channel_num + max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_diff_bipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='BIPolar')
        self._set_sigtype(new_ch, sig_mode='DIFF')
        new_ch.set_display_format_function(function = lambda float_data: eng_string(float_data, fmt=':3.6g',si=True) + 'V')
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_diff_bipolar.__doc__)
        return self._add_channel(new_ch)
    def add_channel_ain_single_ended_unipolar(self, channel_name, channel_num, sig_range):
        '''Add single ended, unipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['single_ended']
        assert channel_num - max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_single_ended_unipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='UNIPolar')
        # self._set_sigtype(new_ch, sig_mode='SING') #Return to AI_GND
        self._set_sigtype(new_ch, sig_mode='NRS') #Return to AI_SENSE
        new_ch.set_display_format_function(function = lambda float_data: eng_string(float_data, fmt=':3.6g',si=True) + 'V')
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_single_ended_unipolar.__doc__)
        return self._add_channel(new_ch)
    def add_channel_ain_diff_unipolar(self, channel_name, channel_num, sig_range):
        '''Add differential, unipolar, channel to u23xx instrument.
            TODO: Better docstring.
        '''
        assert channel_num not in self._configured_channels
        assert channel_num in self._ai_channels['differential']
        assert channel_num + max(self._ai_channels['differential']) + 1 - 100 not in self._configured_channels
        new_ch = channel(channel_name,read_function=self.dummy_read)
        self._configured_channels[channel_num] = new_ch
        new_ch.set_attribute('internal_address', channel_num)
        new_ch.set_attribute('u2300a_type','ain_diff_unipolar')
        self._set_range(new_ch, sig_range=sig_range, polarity='UNIPolar')
        self._set_sigtype(new_ch, sig_mode='DIFF')
        new_ch.set_display_format_function(function = lambda float_data: eng_string(float_data, fmt=':3.6g',si=True) + 'V')
        new_ch.set_delegator(self)
        new_ch.set_description(self.get_name() + ': ' + self.add_channel_ain_diff_unipolar.__doc__)
        return self._add_channel(new_ch)
    def add_channel_current_sense(self,channel_name,channel_num,sig_range='AUTO',gain=1,resistance=None):
        '''Configure channel to return current measurement by scaling voltage measured across
            user-supplied sense resistor.  Specify either gain or its reciprocal resistance.'''
        channel = self.add_channel_ain_diff_bipolar(channel_name=channel_name,
                                                    channel_num=channel_num,
                                                    sig_range=sig_range)
        if resistance != None and gain != 1:
            raise Exception('Resistance and Gain cannot both be specified')
        if (resistance is not None):
            gain = 1.0/resistance
            channel.set_attribute("shunt_resistance", resistance)
        channel.set_attribute("gain", gain) #Picked up in delegated read
        #self._config_channel_scaling(channel,gain,0,"A")
        channel.set_description(self.get_name() + ': ' + self.add_channel_current_sense.__doc__)
        channel.set_display_format_function(function = lambda float_data: eng_string(float_data, fmt=':3.6g',si=True) + 'A')
        return channel
    def dummy_read(self):
        raise Exception('Delegation failure. Contact PyICe-developers@analog.com for more information.')
    def _set_range(self, channel, sig_range, polarity):
        # [SENSe:]VOLTage:RANGe <value>, <ch_list>
        # This command is used to set the range for the AI channel(s) specified in the
        # <ch_list> parameter. This command is applicable for polling mode operations.
            # value
                # U2331A:
                    # – Unipolar mode: {AUTO|10|5|4|2.5|2.0|1.0|0.5|0.4|0.1}
                    # – Bipolar mode: {AUTO|10|5|2.5|2.0|1.25|1.0|0.5|0.25|0.2|0.05}
                # U2351A/52A/53A/54A/55A/56A:
                    # – Unipolar/Bipolar mode: {AUTO|10|5|2.5|1.25}
            # ch_list
                # Single-ended mode:
                    # – U2351A/52A/53A/54A: (@101) to (@116)
                    # – U2355A/56A/31A: (@101) to (@164)
                # Differential mode:
                    # – U2351A/52A/53A/54A: (@101) to (@108)
                    # – U2355A/56A/31A: (@101) to (@132)
        # [SENSe:]VOLTage:POLarity <mode>, <ch_list>
        # This command is used to set the polarity of the AI channel(s) specified in the
        # <ch_list> parameter. This command is applicable for polling mode operations.
            # mode UNIPolar|BIPolar 
            # ch_list
                # Single-ended mode:
                    # – U2351A/52A/53A/54A: (@101) to (@116)
                    # – U2355A/56A/31A: (@101) to (@164)
                # Differential mode:
                    # – U2351A/52A/53A/54A: (@101) to (@108)
                    # – U2355A/56A/31A: (@101) to (@132)
        if polarity.lower() in [pol.lower() for pol in ['BIPolar', 'BIP']]:
            polarity = 'bipolar'
            
        elif polarity.lower() in [pol.lower() for pol in ['UNIPolar', 'UNIP']]:
            polarity = 'unipolar'
        else:
            raise Exception('Uknown polarity')
        channel.set_attribute('polarity', polarity)
        self.get_interface().write(f'SENSe:VOLTage:POLarity {polarity}, (@{channel.get_attribute("internal_address")})')
        if sig_range is None:
            sig_range = 'AUTO'
        elif sig_range == 'AUTO': #Case sensitive!
            pass
        else:
            # Should be an approved number!
            assert sig_range in self._ai_channels[polarity]['range']
        channel.set_attribute('sig_range', sig_range)
        self.get_interface().write(f"SENSe:VOLTage:RANGe {sig_range}, (@{channel.get_attribute('internal_address')})")
    def _set_sigtype(self, channel, sig_mode):
        # [SENSe]:VOLTage:STYPe <mode>, <ch_list>
        # This command is used to set the input signal type (reference ground selection) for
        # the AI channel(s) specified in the <ch_list> parameter. This command is
        # applicable for polling mode operations.
        # The valid options are:
        # – SING: Referenced single-ended mode; 16 or 64 channels common to the ground system (AI_GND pin) on board.
        # – DIFF: Differential mode.
        # – NRS: Non-referenced single-ended mode; 16 or 64 channels common to the AI_SENSE pin.
            # mode SING|DIFF|NRS
            # ch_list
            # Single-ended mode:
                # – U2351A/52A/53A/54A: (@101) to (@116)[a]
                # – U2355A/56A/31A: (@101) to (@164)[b]
            # Differential mode:
                # – U2351A/52A/53A/54A: (@101) to (@108)
                # – U2355A/56A/31A: (@101) to (@132)
            valid_modes = ['SING', 'DIFF', 'NRS']
            assert sig_mode.upper() in [mode.upper() for mode in valid_modes]
            channel.set_attribute('sig_mode', sig_mode)
            self.get_interface().write(f'SENSe:VOLTage:STYPe {sig_mode}, (@{channel.get_attribute("internal_address")})')
    def read_delegated_channel_list(self,channel_list):
        channels = [f'{ch.get_attribute("internal_address")}' for ch in channel_list]
        ch_str = f'(@{",".join(channels)})'
        # SORT???
        data = [float(v) for v in self.get_interface().ask(f'MEASure:VOLTage:DC? {ch_str}').split(',')]
        results = results_ord_dict()
        for idx, ch in enumerate(channel_list):
            # 999.9 special case
            # ch_data = (int_data[i] for i in range(ch_idx, len(int_data), len(self._last_scan_internal_addresses)))
            try:
                g = ch.get_attribute('gain')
            except ChannelAttributeException as e:
                g = 1
            results[ch.get_name()] = g*data[idx] if data[idx] != 999.9 else None
        return results
    # def get_all_settings(self):
        # result = results_ord_dict()
        # result["syst_error"        ] = self.get_interface().ask("SYST:ERR?")
        # ####
        # result["channel_polarity"  ] = self.get_interface().ask(f"ROUTe:CHANnel:POLarity? (@101:{max(self._ai_channels['single_ended'])})")
        # result["channel_range"     ] = self.get_interface().ask(f"ROUTe:CHANnel:RANGe? (@101:{max(self._ai_channels['single_ended'])})")
        # result["rout_channel_stype"] = self.get_interface().ask(f"ROUTe:CHANnel:STYPe? (@101:{max(self._ai_channels['single_ended'])})")
        # return result

class u2331a_base():
    '''12-bit analog input resolution with sampling rate up to 3 MSa/s per single channel'''
    # NOTE: LSB byte first, with upper nibble containing data. Reconstructed word needs 4-bit right shift to recover 12-bit ADC code.
    _ai_channels = {}
    _ai_channels['single_ended'] = range(101, 164+1) #Available channel numbers
    _ai_channels['differential'] = range(101, 132+1) #Avaiable channel numbers
    _ai_channels['bit_offset'] = 4 #12-bit, lsbyte first (little-endian), packed to left.
    _ai_channels['max_sample_rate'] = 1000000 #1e6 available when multiplexing.
    _ai_channels['max_sample_rate_single'] = 3000000 #3e6 available in single-channel mode.
    _ai_channels['max_record_length'] = 8000000 # Common to all models.
    _ai_channels['unipolar'] = {}
    _ai_channels['unipolar']['range'] = {} #max/min/lsb weight settins for each ain range
    _ai_channels['unipolar']['range'][10.] = {'max': 10.,
                                               'min': 0.,
                                               'lsb': 10/(2**12-1)
                                             }
    _ai_channels['unipolar']['range'][5.] = {'max': 5.,
                                             'min': 0.,
                                             'lsb': 5./(2**12-1)
                                            }
    _ai_channels['unipolar']['range'][4.] = {'max': 4.,
                                             'min': 0.,
                                             'lsb': 4./(2**12-1)
                                            }
    _ai_channels['unipolar']['range'][2.5] = {'max': 2.5,
                                              'min': 0.,
                                              'lsb': 2.5/(2**12-1)
                                             }
    _ai_channels['unipolar']['range'][2.] = {'max': 2.,
                                             'min': 0.,
                                             'lsb': 2./(2**12-1)
                                            }
    _ai_channels['unipolar']['range'][1.] = {'max': 1.,
                                             'min': 0.,
                                             'lsb': 1./(2**12-1)
                                            }
    _ai_channels['unipolar']['range'][0.5] = {'max': 0.5,
                                              'min': 0.,
                                              'lsb': 0.5/(2**12-1)
                                             }
    _ai_channels['unipolar']['range'][0.4] = {'max': 0.4,
                                              'min': 0.,
                                              'lsb': 0.4/(2**12-1)
                                             }
    _ai_channels['unipolar']['range'][0.1] = {'max': 2.5,
                                              'min': 0.,
                                              'lsb': 0.1/(2**12-1)
                                             }
    _ai_channels['bipolar'] = {}
    _ai_channels['bipolar']['range'] = {}
    _ai_channels['bipolar']['range'][10.] = {'max': 10,
                                             'min': -10,
                                             'lsb': 20./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][5.0] = {'max': 5,
                                             'min': -5,
                                             'lsb': 10./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][2.5] = {'max': 2.5,
                                             'min': -2.5,
                                             'lsb': 5./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][2.0] = {'max': 2,
                                             'min': -2,
                                             'lsb': 4./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][1.25] = {'max': 1.25,
                                              'min': -1.25,
                                              'lsb': 2.5/(2**12-1)
                                             }
    _ai_channels['bipolar']['range'][1.0] = {'max': 1.,
                                             'min': -1.,
                                             'lsb': 2./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][0.5] = {'max': 0.5,
                                             'min': -0.5,
                                             'lsb': 1./(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][0.25] = {'max': 0.25,
                                              'min': -0.25,
                                              'lsb': 0.5/(2**12-1)
                                             }
    _ai_channels['bipolar']['range'][0.2] = {'max': 0.2,
                                             'min': -0.2,
                                             'lsb': 0.4/(2**12-1)
                                            }
    _ai_channels['bipolar']['range'][0.05] = {'max': 0.05,
                                              'min': -0.05,
                                              'lsb': 0.1/(2**12-1)
                                             }
class u2331a(u2300a_scope, u2331a_base):
    '''Scope version of u2331'''
class u2331a_DVM(u2300a_DVM, u2331a_base):
    '''Voltmeter version of u2331'''
class u2331a_datalogger(u2300a_datalogger, u2331a_base):
    '''Continuous datalogger version of u2331'''

class u2351a():
    '''16-bit analog input resolution with sampling rate of 250 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 116+1)
    _ai_channels_diff = range(101, 108+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)
class u2352a_base():
    '''16-bit analog input resolution with sampling rate of 250 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 116+1)
    _ai_channels_diff = range(101, 108+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)
class u2353a_base():
    '''16-bit analog input resolution with sampling rate of 500 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 116+1)
    _ai_channels_diff = range(101, 108+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)
class u2354a_base():
    '''16-bit analog input resolution with sampling rate of 500 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 116+1)
    _ai_channels_diff = range(101, 108+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)
class u2355a_base():
    '''16-bit analog input resolution with sampling rate of 250 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 164+1)
    _ai_channels_diff = range(101, 132+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)
class u2356a_base():
    '''16-bit analog input resolution with sampling rate of 500 kSa/s'''
    # ROUTe:SCAN <ch_list>
    _ai_channels_se = range(101, 164+1)
    _ai_channels_diff = range(101, 132+1)
    # ROUTe:CHANnel:RANGe <value>, <ch_list>
    _ai_channels_se_range = (10., 5., 2.5, 1.25)
    _ai_channels_diff_range = (10., 5., 2.5, 1.25)

if __name__ == '__main__':
    from PyICe import lab_core
    m = master()
    # vif = m.get_visa_interface('USB0::0x0957::0x1518::TW55020037::0::INSTR', timeout=90)
    vif = m.get_visa_interface('USB0::0x0957::0x1518::TW56510006::0::INSTR', timeout=3)
    
    if False:
        #scope
        daq = u2331a(vif)
        # daq.add_channel_ain_diff('foo1', 101, sig_range=5)
        # daq.add_channel_ain_diff('foo3', 103, sig_range=5)
        # daq.add_channel_ain_diff('foo2', 102, sig_range=10)
        daq.add_channel_time('time')
        daq.add_channel_ain_single_ended_bipolar('foo1', 101, sig_range=5)
        daq.add_channel_ain_single_ended_unipolar('foo2', 102, sig_range=10)
        
        
        daq.set_trigger(daq['foo1'])
        m.add(daq)
        data = m.read_all_channels()
        
        import pandas
        import matplotlib.pyplot as plt
        
        pandas_df = pandas.DataFrame(zip(data['time'], data['foo1'], data['foo2']))
        pandas_dfi = pandas_df.set_index(0)
        ax = pandas_dfi[1].plot.line(title='Ch1 Test')
        ax = pandas_dfi[2].plot.line(title='Ch2 Test')
        ax.set_ylabel(u'Die Temp °C')
        ax.grid(True, which='both')
        plt.show()
    elif False:
        #DVM single ended
        dvm = u2331a_DVM(vif)
        m.add(dvm)
        dvm.add_channel_ain_single_ended_unipolar('v1', 101, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v2', 133, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v3', 102, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v4', 134, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v5', 103, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v6', 135, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v7', 104, sig_range=10)
        dvm.add_channel_ain_single_ended_unipolar('v8', 136, sig_range=10)
        data = m.read_all_channels()
        print(data)
        breakpoint()
    elif False:
        #DVM differential
        dvm = u2331a_DVM(vif)
        m.add(dvm)
        dvm.add_channel_ain_diff_unipolar('v1', 101, sig_range=10)
        dvm.add_channel_ain_diff_unipolar('v2', 102, sig_range=10)
        dvm.add_channel_ain_diff_unipolar('v3', 103, sig_range=10)
        dvm.add_channel_ain_diff_unipolar('v4', 104, sig_range=10)
        data = m.read_all_channels()
        print(data)
        breakpoint()
    elif True:
        dl = u2331a_datalogger(vif, table_name='foo')
        dl.set_sample_rate(3)
        dl.add_channel_time('time')
        dl.add_channel_ain_diff_unipolar('v1', 101, sig_range=10)
        dl.add_channel_ain_diff_unipolar('v2', 102, sig_range=10)
        dl.add_channel_ain_diff_unipolar('v3', 103, sig_range=10)
        dl.add_channel_ain_diff_unipolar('v4', 104, sig_range=10)
        dl.log()
        
    
    
