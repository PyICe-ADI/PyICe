"""Manual oven instrument driver.

>>> from PyICe.lab_instruments.manual_oven import manual_oven

"""
from ..virtual_instruments import instrument_humanoid
from .temperature_chamber import temperature_chamber


class manual_oven(temperature_chamber, instrument_humanoid):
    """Manual_oven."""
    def __init__(self, temp_sense_channel=None):
        """Initialize manual_oven.
        Stores configuration in ``_base_name``, ``_temp_sense_channel`` for
        use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            temp_sense_channel: Temp sense channel to use.
        """
        self._base_name = 'manually controlled oven'
        temperature_chamber.__init__(self)
        instrument_humanoid.__init__(self)
        self._temp_sense_channel = temp_sense_channel

    def add_channels(self, channel_name):
        """Add a channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        self._temp_base_name = channel_name
        return temperature_chamber.add_channels(self, channel_name)

    def _write_temperature(self, value):
        """Program tempertaure setpoint to value.

        Internal implementation detail; see the public API for usage.

        Args:
            value: Value to set.
        """
        self.setpoint = value
        self._write(self[self._temp_base_name].get_name(), value)
        self._wait_settle()

    def _read_temperature_sense(self):
        """Read back actual chamber temperature.  Implement for specific hardware.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.

        Returns:
            The measured value.
        """
        if self._temp_sense_channel is None:
            return self._read(self[f'{self._temp_base_name}_sense'])
        else:
            return self._temp_sense_channel.read()

    def _enable(self, enable):
        """Enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.
        """
        self._write(self[f'{self._temp_base_name}_enable'].get_name(), enable)

    def shutdown(self, shutdown):
        """Separate method to turn off temperature chamber.

        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.

        Args:
            shutdown: Shutdown to use.
        """
        self._write(
            self[f'{self._temp_base_name}_shutdown'].get_name(), shutdown)
