from ..lab_core import *
from ..virtual_instruments import instrument_humanoid
from .temperature_chamber import temperature_chamber

class manual_oven(temperature_chamber, instrument_humanoid):
    def __init__(self, temp_sense_channel=None):
        self._base_name = 'manually controlled oven'
        temperature_chamber.__init__(self)
        instrument_humanoid.__init__(self)
        self._temp_sense_channel = temp_sense_channel
    def add_channels(self, channel_name):
        self._temp_base_name = channel_name
        return temperature_chamber.add_channels(self, channel_name)
    def _write_temperature(self, value):
        '''Program tempertaure setpoint to value.'''
        self.setpoint = value
        self._write(self[self._temp_base_name].get_name(), value)
        self._wait_settle()
    def _read_temperature_sense(self):
        '''read back actual chamber temperature.  Implement for specific hardware.'''
        if self._temp_sense_channel is None:
            return self._read(self[f'{self._temp_base_name}_sense'])
        else:
            return self._temp_sense_channel.read()
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.'''
        self._write(self[f'{self._temp_base_name}_enable'].get_name(), enable)
    def shutdown(self, shutdown):
        '''separate method to turn off temperature chamber.
        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.
        '''
        self._write(self[f'{self._temp_base_name}_shutdown'].get_name(), shutdown)