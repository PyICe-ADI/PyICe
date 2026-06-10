"""Fluke 45 instrument driver.

>>> from PyICe.lab_instruments.fluke_45 import fluke_45

"""
from ..lab_core import *  # noqa: F403


class fluke_45(scpi_instrument):
    """Single channel fluke_45 meter.

    defaults to dc voltage, note this instrument currently does not support using multiple measurement types at the same time
    """
    def __init__(self, interface_visa):
        """Interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'fluke_45'
        scpi_instrument.__init__(self, f"f25 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.config_dc_voltage()

    def config_dc_voltage(self, range="AUTO", rate="S"):
        """Configure meter for DC voltage measurement.

        Optionally set range and rate

        Args:
            range: Measurement or output range.
            rate: Rate of change (units per second).
        """
        self._config("VDC ", range, rate)

    def config_dc_current(self, range="AUTO", rate="S"):
        """Configure meter for DC current measurement.

        Optionally set range and rate

        Args:
            range: Measurement or output range.
            rate: Rate of change (units per second).
        """
        self._config("ADC ", range, rate)

    def config_ac_voltage(self, range="AUTO", rate="S"):
        """Configure meter for AC voltage measurement.

        Optionally set range and rate

        Args:
            range: Measurement or output range.
            rate: Rate of change (units per second).
        """
        self._config("VAC ", range, rate)

    def config_ac_current(self, range="AUTO", rate="S"):
        """Configure meter for AC current measurement.

        Optionally set range and rate

        Args:
            range: Measurement or output range.
            rate: Rate of change (units per second).
        """
        self._config("AAC ", range, rate)

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
        meter_channel = channel(channel_name, read_function=self.read_meter)
        return self._add_channel(meter_channel)

    def read_meter(self):
        """Return float representing meter measurement. Units are V,A,Ohm, etc depending on meter configuration.
        Sends the appropriate query to the instrument and parses the response.

        Reads data from the underlying source and returns it.

        Returns:
            The value read from the device or channel.
        """
        return float(self.get_interface().ask("MEAS1?"))

    def _config(self, command_string, range, rate):
        RANGE_SETTINGS = ["AUTO", 1, 2, 3, 4, 5, 6, 7]
        RATE_SETTINGS = ["S", "M", "F"]
        if range not in RANGE_SETTINGS:
            raise Exception(
                "Error: Not a valid range setting, valid settings are:" +
                str(RANGE_SETTINGS))
        if rate not in RATE_SETTINGS:
            raise Exception(
                "Error: Not a valid rate setting, valid settings are:" +
                str(RATE_SETTINGS))
        self.get_interface().write((command_string))
        self.get_interface().write(("AUTO " if range == "AUTO" else "RANGE " + str(range)))
        self.get_interface().write(("RATE " + str(rate)))
