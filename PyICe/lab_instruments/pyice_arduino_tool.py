from PyICe import lab_instruments, lab_core
from PyICe.lab_core import *
import math

'''
 --- PyICe Arduino Tool (PAT) USAGE --- 

    NOTE: to use the test hook function, the wall adapter must be plugged into the Arduino Zero. No other functions require this adapter.
'''


class pyice_arduino_tool(instrument):
    '''single channel agilent_34401a meter
        defaults to dc voltage, note this instrument currently does not support using multiple measurement types at the same time'''
    def __init__(self,interface,base_name='pat'):
        '''interface'''
        self._base_name = base_name
        instrument.__init__(self,f"PAT @ {interface}")
        self.add_interface_visa(interface, 60)
        self.init_channels(base_name)
        # self.map_pins()
        # self.reset_pins()         #TODO: Officially remove this
        # self.reset_settings()
    def init_channels(self, base_name): ##ADD BASENAME INPUT ARG
        #chip_data
        self.chip_uses_pec_channel = self._add_channel_chip_uses_pec(f'{base_name}_chip_uses_pec')
        self.chip_register_size_channel = self._add_channel_chip_register_size(f'{base_name}_chip_register_size')
        self.chip_address_channel = self._add_channel_chip_address(f'{base_name}_chip_address')
        self.chip_watchdog_q_command_code_channel = self._add_channel_chip_watchdog_q_command_code(f'{base_name}_chip_wd_q_cc')
        self.chip_watchdog_a_command_code_channel = self._add_channel_chip_watchdog_a_command_code(f'{base_name}_chip_wd_a_cc')
        
        #control_settings
        self.control_command_code_channel = self._add_channel_control_command_code(f'{base_name}_control_command_code')
        self.control_command_write_data_channel = self._add_channel_control_command_write_data(f'{base_name}_control_command_write_data')
        self.control_command_read_data_channel = self._add_channel_control_command_read_data(f'{base_name}_control_command_read_data')
        self.control_pin_number_channel = self._add_channel_control_pin_number(f'{base_name}_control_pin_number')
        self.control_pin_edge_channel = self._add_channel_control_pin_edge(f'{base_name}_control_pin_edge')
        self.control_command_write_channel = self._add_channel_control_command_write(f'{base_name}_control_command_write')
        self.control_command_read_channel = self._add_channel_control_command_read(f'{base_name}_control_command_read')
        self.control_pin_write_channel = self._add_channel_control_pin_write(f'{base_name}_control_pin_write')
        self.control_pin_read_channel = self._add_channel_control_pin_read(f'{base_name}_control_pin_read')
        self.control_test_hook_enable = self._add_channel_control_test_hook_enable(f'{base_name}_control_test_hook_enable')
        
        #test_settings
        self.test_timeout_channel_ms = self._add_channel_test_timeout_ms(f'{base_name}_test_timeout_ms')
        self.test_arm_channel = self._add_channel_test_arm(f'{base_name}_test_arm')
        self.test_run_channel = self._add_channel_test_run(f'{base_name}_test_run')
        self.test_data_ready_channel = self._add_channel_test_data_ready(f'{base_name}_test_data_ready')
        self.test_data_channel = self._add_channel_test_data(f'{base_name}_test_data')
        
        #trigger_settings
        self.trigger_select_channel = self._add_channel_trigger_select(f'{base_name}_trigger_select')
        self.trigger_type_channel = self._add_channel_trigger_type(f'{base_name}_trigger_type')
        self.trigger_command_code_channel = self._add_channel_trigger_command_code(f'{base_name}_trigger_command_code')
        self.trigger_command_write_data_channel = self._add_channel_trigger_command_write_data(f'{base_name}_trigger_command_write_data')
        self.trigger_command_read_data_channel = self._add_channel_trigger_command_read_data(f'{base_name}_trigger_command_read_data')
        self.trigger_pin_number_channel = self._add_channel_trigger_pin_number(f'{base_name}_trigger_pin_number')
        self.trigger_pin_edge_channel = self._add_channel_trigger_pin_edge(f'{base_name}_trigger_pin_edge')
        
        #actions
        self.action_queue_channel = self._add_channel_queue_action(f'{base_name}_action_queue')
        self.action_run_all_channel = self._add_channel_run_all_actions(f'{base_name}_action_run_all')
        self.action_flush_channel = self._add_channel_flush_actions(f'{base_name}_action_flush')
        self.action_type_channel = self._add_channel_action_type(f'{base_name}_action_type')
        self.action_delay_channel_us = self._add_channel_action_delay_us(f'{base_name}_action_delay_us')
        self.action_select_channel = self._add_channel_action_select(f'{base_name}_action_select')
        self.action_timestamp_channel_us = self._add_channel_action_timestamp_us(f'{base_name}_action_timestamp_us')
        self.action_command_write_data_channel = self._add_channel_action_command_write_data(f'{base_name}_action_command_write_data')
        self.action_command_code_channel = self._add_channel_action_command_code(f'{base_name}_action_command_code')
        self.action_pin_number_channel = self._add_channel_action_pin_number(f'{base_name}_action_pin_number')
        self.action_pin_edge_channel = self._add_channel_action_pin_edge(f'{base_name}_action_pin_edge')

        #pwm
        self.pwm_gclk_channel = self._add_channel_pwm_gclk(f'{base_name}_pwm_gclk_div')
        self.pwm_turbo_channel = self._add_channel_pwm_turbo(f'{base_name}_pwm_turbo')
        self.pwm_enable_channel = self._add_channel_pwm_enable(f'{base_name}_pwm_enable')
        self.pwm_output_dutycycle_channel = self._add_channel_pwm_output_dutycycle(f'{base_name}_pwm_duty')
        self.pwm_output_pin_channel = self._add_channel_pwm_output_pin(f'{base_name}_pwm_output_pin')
        self.pwm_tcc_div_channel = self._add_channel_pwm_tcc_div(f'{base_name}_pwm_tcc_div')
        self.pwm_tcc_steps_channel = self._add_channel_pwm_tcc_steps(f'{base_name}_pwm_steps')
        self.pwm_mode_channel = self._add_channel_pwm_mode(f'{base_name}_pwm_mode')

        #pat_settings
        self.enable_board_channel = self._add_channel_enable_board(f'{base_name}_board_enable')
        
        #run_channel
        # self.run_channel = channel(f'{base_name}_run_test',write_function=lambda x :self.run_test(x))
        # self._add_channel(self.run_channel)
        self.run_channel = self._add_channel(channel(f'{base_name}_run_test',write_function=lambda x :self.run_test(x)))
        
        #second unit corrections
        self.test_timeout_channel = self._add_channel(channel(f'{base_name}_test_timeout', write_function=lambda x :self.test_timeout_channel_ms.write(x * 1e3)))
        self.action_delay_channel = self._add_channel(channel(f'{base_name}_action_delay', write_function=lambda x :self.action_delay_channel_us.write(x * 1e6)))
        self.action_timestamp_channel = self._add_channel(channel(f'{base_name}_action_timestamp', read_function=lambda :float(self.action_timestamp_channel_us.read())/1e6)) 
    def map_pins(self):
        '''Give pins unique names specific to the application, ex. self.RST = 2'''
        print('YOU CAN OVERRIDE map_pins(). Use this to set board-specific names for each pin.')
    def reset_pins(self):
        '''Give pins default states specific to the application'''
        print('YOU CAN OVERRIDE reset_pins(). Use this to set the default state for each pin.')
    def reset_settings(self):
        self.action_flush_channel.read()
        self.enable_board_channel.write('False')
        self.test_timeout_channel.write(5)
# ADD CHANNEL HELPERS -----------------------------------------------------------------------------------------------------
    def _add_read_channel(self,channel_name,command):
        '''Register a named channel. No configuration takes place. '''
        def read_mumbo(message):
            resp = self.get_interface().ask(message)
            extra = self.get_interface().resync()
            assert extra == '', f"{message} unexpected response. Should be empty. Saw {resp} then {extra}."
            return resp
        # str_encoding = 'latin-1'
        # new_channel = channel(channel_name,read_function=lambda: self.get_interface().ask(command))#.decode(str_encoding))
        new_channel = channel(channel_name,read_function=lambda: read_mumbo(command))#.decode(str_encoding))
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        return self._add_channel(new_channel)
    def _add_read_write_channel_with_param(self,channel_name,command):
        '''Register a named channel. No configuration takes place. '''
        def write_magic(message):
            resp = self.get_interface().ask(message)
            extra = self.get_interface().resync()
            assert extra == '', f"{message} unexpected response. Should be empty. Saw {resp} then {extra}."
        # new_channel = channel(channel_name,write_function=lambda param: self.get_interface().ask(f'{command} {param}'))
        new_channel = channel(channel_name,write_function=lambda param: write_magic(f'{command} {param}'))
        new_channel._read = lambda: self.get_interface().ask(f'{command}?')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        return self._add_channel(new_channel)
    ## We need a write-only channel, for the types that don't have a '?' equivalent.
    def _add_write_channel(self,channel_name,command):
        def write_jumbo(message):
            resp = self.get_interface().ask(message)
            extra = self.get_interface().resync()
            assert extra == '', f"{message} unexpected response. Should be empty. Saw {resp} then {extra}."
        new_channel = channel(channel_name,write_function=lambda param: write_jumbo(f'{command} {param}'))
        return self._add_channel(new_channel)

# CHIP_DATA CHANNEL DEFS -----------------------------------------------------------------------------------------------------
    def _add_channel_chip_uses_pec(self,channel_name):
        '''Register the next test to be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CHIP:USEPec')
        new_channel.set_description(self.get_name() + f': {self._add_channel_chip_uses_pec.__doc__}')
        new_channel.add_preset('True', 'I2C uses PEC.')
        new_channel.add_preset('False', 'I2C does not use PEC.')
        return new_channel
    def _add_channel_chip_register_size(self,channel_name):
        '''Register the next test to be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CHIP:REGSize')
        new_channel.set_description(self.get_name() + f': {self._add_channel_chip_register_size.__doc__}')
        new_channel.add_preset('8', 'Registers are 8 bits.')
        new_channel.add_preset('16', 'Registers are 16 bits.')
        return new_channel
    def _add_channel_chip_address(self,channel_name):
        '''Register the next test to be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CHIP:ADDRess')
        new_channel.set_description(self.get_name() + f': {self._add_channel_chip_address.__doc__}')
        return new_channel
    def _add_channel_chip_watchdog_q_command_code(self,channel_name):
        '''Register the next test to be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CHIP:WDQcc')
        new_channel.set_description(self.get_name() + f': {self._add_channel_chip_watchdog_q_command_code.__doc__}')
        return new_channel
    def _add_channel_chip_watchdog_a_command_code(self,channel_name):
        '''Register the next test to be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CHIP:WDAcc')
        new_channel.set_description(self.get_name() + f': {self._add_channel_chip_watchdog_a_command_code.__doc__}')
        return new_channel
# CONTROL_SETTINGS CHANNEL DEFS -----------------------------------------------------------------------------------------------------
    def _add_channel_control_command_code(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CONTrol:COMMand:CODE')
        return new_channel
    def _add_channel_control_command_write_data(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CONTrol:COMMand:WDATa')
        return new_channel
    def _add_channel_control_command_read_data(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'CONTrol:COMMand:RDATa?')
        return new_channel
    def _add_channel_control_command_write(self,channel_name):
        '''Write the current control_settings to the chip'''
        new_channel = self._add_write_channel(channel_name,'CONTrol:COMMand:WRITe')
        new_channel.set_description(self.get_name() + f': {self._add_channel_control_command_write.__doc__}')
        return new_channel
    def _add_channel_control_command_read(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'CONTrol:COMMand:READ?')
        return new_channel
    def _add_channel_control_pin_number(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CONTrol:PIN:NUMBer')
        return new_channel
    def _add_channel_control_pin_edge(self,channel_name):
        '''Choose which edge will be used in the next test (how it is used depends on the test).'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CONTrol:PIN:EDGE')
        new_channel.set_description(self.get_name() + f': {self._add_channel_control_pin_edge.__doc__}')
        new_channel.add_preset('LOW', 'Logic low.')
        new_channel.add_preset('CHANGE', 'Any edge.')
        new_channel.add_preset('FALLING', 'Falling edge.')
        new_channel.add_preset('RISING', 'Rising edge.')
        new_channel.add_preset('HIGH', 'Logic high.')
        return new_channel
    def _add_channel_control_pin_write(self,channel_name):
        '''Write the current control_settings to the chip'''
        new_channel = self._add_write_channel(channel_name,'CONTrol:PIN:WRITe')
        new_channel.set_description(self.get_name() + f': {self._add_channel_control_pin_write.__doc__}')
        return new_channel
    def _add_channel_control_pin_read(self,channel_name):
        '''.'''
        new_channel = self._add_write_channel(channel_name,'CONTrol:PIN:READ')
        return new_channel
    def _add_channel_control_test_hook_enable(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'CONTrol:HOOK:ENABle')
        new_channel.add_preset('True', 'The test hook is enabled.')
        new_channel.add_preset('False', 'The test hook is not enabled.')
        return new_channel
# TEST CHANNEL DEFS -----------------------------------------------------------------------------------------------------
    def _add_channel_test_timeout_ms(self,channel_name):
        '''Set the timeout (ms) of the test.'''
        return self._add_read_write_channel_with_param(channel_name,'TEST:TIMEout')
    def _add_channel_test_arm(self,channel_name):
        '''Set the next test that will be run.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TEST:ARM')
        new_channel.set_description(self.get_name() + f': {self._add_channel_test_arm.__doc__}')
        new_channel.add_preset('T1->T2', 'Measure the time delta between the start and stop triggers.')
        new_channel.add_preset('A->T1->T2', 'Perform queued actions, then measure the time delta between the start and stop triggers.')
        new_channel.add_preset('T1->A->T2', 'Measure the time delta between the start and stop triggers, peforming actions after start trigger fires.')
        new_channel.add_preset('A->T2?', 'Enable a non-blocking stop trigger (pin input only) and run all actions. Reports back time between start of actions and stop trigger.')
        new_channel.add_preset('T1->A->T2?', 'Await start trigger, then enable a non-blocking stop trigger (pin input only) and run all actions. Reports back time between triggers.')
        return new_channel
    def _add_channel_test_run(self,channel_name):
        '''Run the currently armed test.'''
        return self._add_read_channel(channel_name,'TEST:RUN')
    def _add_channel_test_data_ready(self,channel_name):
        '''Ask if the test has completed and data is ready.'''
        return self._add_read_channel(channel_name,'TEST:DRDY?')
    def _add_channel_test_data(self,channel_name):
        '''Ask if the test has completed and data is ready.'''
        return self._add_read_write_channel_with_param(channel_name,'TEST:DATA')
# TRIGGER_SETTINGS CHANNEL DEFS -----------------------------------------------------------------------------------------------------
    def _add_channel_trigger_select(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:SELect')
        new_channel.add_preset('START', 'Select the trigger which begins the measurement time.')
        new_channel.add_preset('STOP', 'Select the trigger which ends the measurement time.')
        return new_channel
    def _add_channel_trigger_type(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:TYPE')
        new_channel.add_preset('EXTERNAL', 'No trigger performed by PAT.')
        new_channel.add_preset('PIN_INPUT', 'Wait for pin input to go to the value defined by the pin edge setting, then timestamp (interrupt-based).')
        new_channel.add_preset('PIN_OUTPUT', 'Set the selected pin to the pin edge setting and timestamp.')
        new_channel.add_preset('WRITE', 'Write the write data value to the command code and timestamp.')
        new_channel.add_preset('READ_MATCH', 'Timestamp once the read data matches the value stored in write data.')
        new_channel.add_preset('READ_MISMATCH', 'Timestamp once the read data does not match the value stored in write data.')
        new_channel.add_preset('SERVICE_WATCHDOG', 'Service the watchdog and then timestamp.')
        new_channel.add_preset('BAD_SERVICE_WATCHDOG', 'Service the watchdog incorrectly (wrong CRC) and then timestamp.')
        return new_channel
    def _add_channel_trigger_command_code(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:COMMand:CODE')
        return new_channel
    def _add_channel_trigger_command_write_data(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:COMMand:WDATa')
        return new_channel
    def _add_channel_trigger_command_read_data(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'TRIGger:COMMand:RDATa?')
        return new_channel
    def _add_channel_trigger_pin_number(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:PIN:NUMBer')
        return new_channel
    def _add_channel_trigger_pin_edge(self,channel_name):
        '''Choose which edge will be used in the next test (how it is used depends on the test).'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'TRIGger:PIN:EDGE')
        new_channel.set_description(self.get_name() + f': {self._add_channel_trigger_pin_edge.__doc__}')
        new_channel.add_preset('LOW', 'Logic low.')
        new_channel.add_preset('CHANGE', 'Any edge.')
        new_channel.add_preset('FALLING', 'Falling edge.')
        new_channel.add_preset('RISING', 'Rising edge.')
        new_channel.add_preset('HIGH', 'Logic high.')
        return new_channel
# ACTION CHANNEL DEFS -----------------------------------------------------------------------------------------------------
    def _add_channel_queue_action(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'ACTIon:QUEUe')
        return new_channel
    def _add_channel_run_all_actions(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'ACTIon:RUNAll')
        return new_channel
    def _add_channel_flush_actions(self,channel_name):
        '''.'''
        new_channel = self._add_read_channel(channel_name,'ACTIon:FLUSh')
        return new_channel
    def _add_channel_action_type(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:TYPE')
        new_channel.add_preset('NONE', 'No action, just a dummy placeholder.')
        new_channel.add_preset('WAIT', 'Wait for the specified action delay in microseconds.')
        new_channel.add_preset('PIN_OUTPUT', 'Set the selected pin to the pin edge setting.')
        new_channel.add_preset('WRITE', 'Write the write data value to the command code.')
        new_channel.add_preset('SERVICE_WATCHDOG', 'Service the watchdog.')
        new_channel.add_preset('BAD_SERVICE_WATCHDOG', 'Service the watchdog incorrectly (wrong CRC).')
        return new_channel
    def _add_channel_action_delay_us(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:DELAy')
        return new_channel
    def _add_channel_action_select(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:SELect')
        new_channel.add_preset('0', 'Select action 0.')
        new_channel.add_preset('1', 'Select action 1.')
        new_channel.add_preset('2', 'Select action 2.')
        new_channel.add_preset('3', 'Select action 3.')
        new_channel.add_preset('4', 'Select action 4.')
        new_channel.add_preset('5', 'Select action 5.')
        new_channel.add_preset('6', 'Select action 6.')
        new_channel.add_preset('7', 'Select action 7.')
        new_channel.add_preset('8', 'Select action 8.')
        new_channel.add_preset('9', 'Select action 9.')
        new_channel.add_preset('NEXT', 'Select the next action, not in queue yet.')
        return new_channel
    def _add_channel_action_timestamp_us(self,channel_name):
        new_channel = self._add_read_channel(channel_name,'ACTIon:TIMEstamp?')
        return new_channel
    def _add_channel_action_command_code(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:COMMand:CODE')
        return new_channel
    def _add_channel_action_command_write_data(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:COMMand:WDATa')
        return new_channel
    def _add_channel_action_pin_number(self,channel_name):
        '''.'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:PIN:NUMBer')
        return new_channel
    def _add_channel_action_pin_edge(self,channel_name):
        '''Choose which edge will be used in the next test (how it is used depends on the test).'''
        new_channel = self._add_read_write_channel_with_param(channel_name,'ACTIon:PIN:EDGE')
        new_channel.set_description(self.get_name() + f': {self._add_channel_action_pin_edge.__doc__}')
        new_channel.add_preset('LOW', 'Logic low.')
        new_channel.add_preset('HIGH', 'Logic high.')
        return new_channel
# UTILITY CHANNELS -----------------------------------------------------------------------------------------------------
    def _add_channel_enable_board(self,channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'BOARd:ENABled')
        new_channel.add_preset('True', 'The adapter board is allowed to drive the ENABLE, WD_DISABLE, and SYNC pins.')
        new_channel.add_preset('False', 'ENABLE, WD_DISABLE, and SYNC pins are configured as high-Z inputs.')
        return new_channel

# PWM CHANNELS ---------------------------------------------------------------------------------------------------------
    def _add_channel_pwm_gclk(self, channel_name):
        new_channel=self._add_read_write_channel_with_param(channel_name, 'PWM:GCLKDiv')
        new_channel.set_min_write_limit(1)
        new_channel.set_max_write_limit(255)
        return new_channel

    def _add_channel_pwm_turbo(self, channel_name):
        new_channel=self._add_read_write_channel_with_param(channel_name, 'PWM:TURBo')
        new_channel.add_preset(True, 'Enable 96MHz base clock in ATSAMD21Gx chip')
        new_channel.add_preset(False, 'Enable 48MHz base clock in ATSAMD21Gx chip')
        return new_channel

    def _add_channel_pwm_enable(self, channel_name):
        new_channel=self._add_read_write_channel_with_param(channel_name, 'PWM:ENABle')
        new_channel.add_preset(True, 'Enable PWM')
        new_channel.add_preset(False, 'Disable PWM')
        return new_channel

    def _add_channel_pwm_output_dutycycle(self, channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'PWM:OUTPut:DUTYcycle')
        return new_channel

    def _add_channel_pwm_output_pin(self, channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'PWM:OUTPut:PIN')
        pwm_pins = (3, 4, 6, 8, 9, 10, 11, 12, 13)
        for pin in pwm_pins:
            new_channel.add_preset(pin, f'Output PWM on arduino zero pin {pin}')
        return new_channel

    def _add_channel_pwm_tcc_div(self, channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'PWM:TCC:DIV')
        new_channel.add_preset(1, 'Prescalar divider of 1 ')
        new_channel.add_preset(2, 'Prescalar divider of 2 ')
        new_channel.add_preset(4, 'Prescalar divider of 4 ')
        new_channel.add_preset(8, 'Prescalar divider of 8 ')
        new_channel.add_preset(16, 'Prescalar divider of 16 ')
        new_channel.add_preset(64, 'Prescalar divider of 64 ')
        new_channel.add_preset(256, 'Prescalar divider of 256 ')
        new_channel.add_preset(1024, 'Prescalar divider of 1024 ')
        return new_channel

    def _add_channel_pwm_tcc_steps(self, channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'PWM:TCC:STEPS')
        return new_channel
    def _add_channel_pwm_mode(self, channel_name):
        new_channel = self._add_read_write_channel_with_param(channel_name, 'PWM:TCC:MODE')
        new_channel.add_preset('NORMAL', 'Normal mode PWM')
        new_channel.add_preset('DUAL', 'Dual slope PWM, reduces PWM frequency by factor of 2, but guarantees frequency'
                                       'and phase')
        return new_channel

    def _add_channel_pwm_pulse_width(self, channel_name):
        new_channel = self._add_read_channel(channel_name, 'PWM:PULS?')
        return new_channel

    def _add_channel_pwm_frequency(self, channel_name):
        new_channel = self._add_read_channel(channel_name, 'PWM:FREQ?')
        return new_channel


# GROUP FUNCTIONS -----------------------------------------------------------------------------------------------------
    def set_chip_settings(self, uses_pec='True', register_size='8', address='0x00', wd_q_cc='0x00', wd_a_cc='0x00'):
        self.chip_uses_pec_channel.write(uses_pec)
        self.chip_register_size_channel.write(register_size)
        self.chip_address_channel.write(address)
        self.chip_watchdog_q_command_code_channel.write(wd_q_cc)
        self.chip_watchdog_a_command_code_channel.write(wd_a_cc)
    def write_chip(self, command_code, write_data):
        self.control_command_code_channel.write(command_code)
        self.control_command_write_data_channel.write(write_data)
        return self.control_command_write_channel.write("TRIG")
    def read_chip(self, command_code):
        self.control_command_code_channel.write(command_code)
        return self.control_command_read_channel.read()
    def get_bf_writeback_data(self, channels, channel_name, write_data):
        '''Read register data and calclate new register data with only relevant bits changed.
           NOTE: does not write the data back in case you want to write it with a trigger/action, etc.'''
        channel = channels.get_channel(channel_name)
        command_code = channel.get_attribute('command_code')
        offset = channel.get_attribute('offset')
        size = channel.get_attribute('size')
        word_size = channel.get_attribute('word_size')
        register_read_data = int(self.read_chip(command_code))
        def size_to_bitmask(size): return 2**size - 1
        bitmask = size_to_bitmask(word_size) - (size_to_bitmask(size) << offset) #bitmask the size of the register with relevant bits cleared
        write_data = (register_read_data & bitmask) + (write_data << offset) #writeback data with only relevant bits changed
        return write_data
    def write_pin(self, pin_num, pin_edge):
        self.control_pin_number_channel.write(pin_num)
        self.control_pin_edge_channel.write(pin_edge)
        self.control_pin_write_channel.write("TRIG")
    def read_pin(self, pin_num):
        self.control_pin_number_channel.write(pin_num)
        return self.control_pin_read_channel.write("TRIG")
    def set_pin_mode(self, pin_num, mode, output_state='LOW'): #mode is a string, 'INPUT' or 'OUTPUT'
        if mode == 'OUTPUT': self.write_pin(pin_num, output_state)
        else: self.read_pin(pin_num) #this sets it as an input, just throw away the read data
    def enable_test_hook(self, enable=True):
        self.control_test_hook_enable.write(enable)
    def set_trigger(self, trigger, type, cc=None, write_data=None, pin_num=None, pin_edge=None):
        self.trigger_select_channel.write(trigger)
        self.trigger_type_channel.write(type)
        if cc is not None: self.trigger_command_code_channel.write(cc)
        if write_data is not None: self.trigger_command_write_data_channel.write(write_data)
        if pin_num is not None: self.trigger_pin_number_channel.write(pin_num)
        if pin_edge is not None: self.trigger_pin_edge_channel.write(pin_edge)
    def set_trigger_cc(self, trigger, type, cc, write_data):
        self.trigger_select_channel.write(trigger)
        self.trigger_type_channel.write(type)
        self.trigger_command_code_channel.write(cc)
        self.trigger_command_write_data_channel.write(write_data)
    def set_trigger_pin_num(self, trigger, type, pin_num, pin_edge):
        self.trigger_select_channel.write(trigger)
        self.trigger_type_channel.write(type)
        self.trigger_pin_number_channel.write(pin_num)
        self.trigger_pin_edge_channel.write(pin_edge)
    def queue_action(self, type, delay_us=0, cc=None, write_data=None, pin_num=None, pin_edge=None):
        self.action_select_channel.write('NEXT') #switch to the action that is under edit
        self.action_type_channel.write(type)
        if delay_us != 0: self.action_delay_channel_us.write(delay_us)
        if cc is not None: self.action_command_code_channel.write(cc)
        if write_data is not None: self.action_command_write_data_channel.write(write_data)
        if pin_num is not None: self.action_pin_number_channel.write(pin_num)
        if pin_edge is not None: self.action_pin_edge_channel.write(pin_edge)
        self.action_queue_channel.read()
    def run_all_actions(self):
        self.action_run_all_channel.write("TRIG")
    def get_action_complete_timestamp_us(self, action_queue_index): #in microseconds
        self.action_select_channel.write(action_queue_index)
        return int(self.action_timestamp_channel_us.read())
    def run_test(self, test_name, timeout_ms=None):
        if timeout_ms is not None: self.test_timeout_channel_ms.write(timeout_ms)
        self.test_arm_channel.write(test_name)
        self.enable_board_channel.write('True')
        self.test_run_channel.read()
        if(self.test_data_ready_channel.read() != '1'):
            return "FAILURE"
        return self.test_data_channel.read()   
    def add_channel_pin_control(self, channel_name, pin_num):
        new_channel = channel(channel_name, write_function=lambda value: self.write_pin(pin_num, value))
        return self._add_channel(new_channel)

    @staticmethod
    def _setup_pwm(pin_num: int, freq: int):
        tcc_divs = [1, 2, 4, 8, 16, 64, 256, 1024]
        gclk_divs = [x for x in range(1, 256)]
        max_freq = 48e6
        if pin_num in [11, 13]:
            max_steps = 50000
        else:
            max_steps = 500000

        for tcc_div in tcc_divs:
            for gclk_div in gclk_divs:
                steps = int(max_freq/gclk_div/tcc_div/freq)
                if 0 < steps <= max_steps:
                    return gclk_div, tcc_div, steps
        raise ValueError(f'The PAT is not able to produce frequency {freq}')

    def add_channels_pwm(self, logger_instance, channel_name, pin_num, pwm_freq):
        gclk_div, tcc_div, steps = self._setup_pwm(pin_num=pin_num, freq=pwm_freq)

        self.pwm_output_pin_channel.write(pin_num)
        self.pwm_gclk_channel.write(gclk_div)
        self.pwm_tcc_div_channel.write(tcc_div)
        self.pwm_tcc_steps_channel.write(steps)
        new_channel = self._add_channel_pwm_output_dutycycle(channel_name + '_duty_cycle')
        # self._add_channel(new_channel)
        logger_instance.add(new_channel)
        new_channel = self._add_channel_pwm_frequency(channel_name + '_freq')
        logger_instance.add(new_channel)
        # self._add_channel(new_channel)
        new_channel = self._add_channel_pwm_pulse_width(channel_name + '_pulse_width')
        logger_instance.add(new_channel)
        new_channel = self._add_channel_pwm_enable(channel_name + '_enable')
        logger_instance.add(new_channel)
        # self._add_channel(new_channel)



