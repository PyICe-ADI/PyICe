from .agilent_8110a import Agilent_8110a
from PyICe.lab_core import *

class Agilent_81110a(Agilent_8110a):
    '''
    HP 165MHz/330MHz Dual Channel Pattern Generator from the early 1990's
    The manual advises to use the short form of SCPI commands to save communication time since this thing has a lousy GPIB port (Dare I say, even, "HPIB" port?).
    It also advises to turn the display off but there doesn't seem to be a speed issue turning off seems ill advised for debug reasons.
    '''
    def __init__(self, interface_visa, plugin, debug_comms=False):
        self._debug_comms = debug_comms
        self._base_name = 'HP81110A'
        self.max_record_size = 16384
        instrument.__init__(self, f"HP81110A @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write("*RST")
        '''
        Minimum width of a pulse duration (1 or 0) in the digital pattern.
        Set by add_channel_pulse_period()
        '''
        speeds = {"HP81111A": 6.06e-9, "HP81112A": 3.03e-9} # Manual page 75
        assert plugin in speeds, f'''Agilent 81110A doesn't takee a plugin called "{plugin}" try one of: {speeds.keys()}'''
        self.timestep = speeds[plugin]

    def add_channel_pattern_update(self, channel_name):
        '''
        Enables or disables the automatic updating of the pattern as a new one is entered.
        Not sure if automatic causes automatic triggering of a pattern if set to manual or *TRG software mode but I think it does.
        '''
        def set_pattern_update(update):
            if update not in ["ON", "OFF", "ONCE"]:
                raise Exception(f"\n\nAgilent 8110A: Sorry don't know how to set pattern format to: '{update}', try 'ON', 'OFF' or 'ONCE'.\n\n")
            self.get_interface().write(f":DIG:STIM:PATT:UPD {update}")
        new_channel = channel(channel_name, write_function=set_pattern_update)
        new_channel.add_preset("ON", "Allow the pattern to update automatically upon being re-written.")
        new_channel.add_preset("OFF", "Prevent the pattern from updating automatically upon being re-written.")
        new_channel.add_preset("ONCE", "Update the pattern one time (once re-written)?")
        new_channel.set_write_delay(2.5) # HP81110A seems to generate wayward STROBE outputs during otherwise innocuous SCPI commands. This helps prevent scope arming and such.
        return self._add_channel(new_channel)