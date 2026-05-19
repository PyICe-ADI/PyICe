from ..virtual_instruments import instrument_humanoid
from .temperature_chamber import temperature_chamber


class manual_oven(temperature_chamber, instrument_humanoid):
    def __init__(self, temp_sense_channel=None):
        self._base_name = 'manually controlled oven'
        temperature_chamber.__init__(self)
        instrument_humanoid.__init__(self)
        self._temp_sense_channel = temp_sense_channel

    def add_channels(self, channel_name):
        """Add a channels."""
        self._temp_base_name = channel_name
        return temperature_chamber.add_channels(self, channel_name)

    def _write_temperature(self, value):
        """Program tempertaure setpoint to value.

        Args:
            value: Value to set.
        """
        self.setpoint = value
        self._write(self[self._temp_base_name].get_name(), value)
        self._wait_settle()

    def _read_temperature_sense(self):
        """Read back actual chamber temperature.  Implement for specific hardware.

        Returns:
            Result value.
        """
        if self._temp_sense_channel is None:
            return self._read(self[f'{self._temp_base_name}_sense'])
        else:
            return self._temp_sense_channel.read()

    def _enable(self, enable):
        """Enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.

        Args:
            enable: Enable or disable.
        """
        self._write(self[f'{self._temp_base_name}_enable'].get_name(), enable)

    def shutdown(self, shutdown):
        """Separate method to turn off temperature chamber.

        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.

        Args:
            shutdown: Shutdown.
        """
        self._write(
            self[f'{self._temp_base_name}_shutdown'].get_name(), shutdown)
