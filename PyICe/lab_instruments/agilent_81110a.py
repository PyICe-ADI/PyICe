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