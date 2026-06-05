"""Hp 3478a instrument driver.

>>> from PyICe.lab_instruments.hp_3478a import hp_3478a

"""
from PyICe.lab_core import *  # noqa: F403


class hp_3478a(instrument):
    """Single channel hp_3478a meter.

    defaults to dc voltage
    """
    def __init__(self, interface_visa):
        """Initialize hp_3478a.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'hp_3478a'
        instrument.__init__(self, "hp_3478a @ " + str(interface_visa))
        self.add_interface_visa(interface_visa)
        self.config_dc_voltage()

    def config_dc_voltage(self):
        """Configure meter for DC voltage measurement.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write(("F1"))

    def config_dc_current(self):
        """Configure meter for DC current measurement.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write(("F5"))

    def config_ac_voltage(self):
        """Configure meter for AC voltage measurement.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write(("F2"))

    def config_ac_current(self):
        """Configure meter for AC current measurement.

        Applies the specified configuration to the object or hardware.
        """
        self.get_interface().write(("F6"))

    def add_channel(self, channel_name):
        """Add named channel to instrument without configuring measurement type.
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
        meter_channel = channel(channel_name, read_function=self._read_meter)
        return self._add_channel(meter_channel)

    def _read_meter(self):
        """Return float representing meter measurement.  Units are V,A,Ohm, etc depending on meter configuration.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.

        Returns:
            The measured value.
        """
        return float(self.get_interface().read())
