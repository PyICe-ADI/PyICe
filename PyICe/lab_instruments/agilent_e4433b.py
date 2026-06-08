"""Agilent e4433b instrument driver.

>>> from PyICe.lab_instruments.agilent_e4433b import agilent_e4433b

"""
from ..lab_core import *  # noqa: F403


class agilent_e4433b(instrument):
    """Agilent E4433B Signal Generator."""

    def __init__(self, interface_visa):
        """Initialize agilent_e4433b.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'agilent_e4433b'
        instrument.__init__(self, f"agilent_e4433b @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write(("*RST"))

    def add_channel(self, channel_name, add_extended_channels=True):
        """Add a channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            add_extended_channels: If True, add sense and mode channels.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self.write_output)
        if add_extended_channels:
            self.add_channel_freq(channel_name + "_freq")
            self.add_channel_power(channel_name + "_power")
        return self._add_channel(new_channel)

    def write_output(self, freq, power):
        """Perform write output operation.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.

        Args:
            freq: Freq to use.
            power: Power level.
        """
        self._write_power(power)
        self._write_freq(freq)

    def _write_power(self, power):
        self.get_interface().write(("POWER " + str(power) + " DBM"))

    def _write_freq(self, freq):
        self.get_interface().write(("FREQuency " + str(freq) + "MHZ"))

    def add_channel_freq(self, channel_name):
        """Add a channel freq.
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
        freq_channel = channel(channel_name, read_function=self.read_freq)
        return self._add_channel(freq_channel)

    def add_channel_power(self, channel_name):
        """Add a channel power.
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
        power_channel = channel(channel_name, read_function=self.read_power)
        return self._add_channel(power_channel)

    def read_freq(self):
        """Return read freq result.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The value read from the device or channel.
        """
        return self.get_interface().ask(("FREQ?"))

    def read_power(self):
        """Return read power result.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The value read from the device or channel.
        """
        return self.get_interface().ask(("POWER?"))

    def enable_output(self):
        """Enable output.

        Sends the corresponding SCPI command string to the instrument over the bus.
        """
        self.get_interface().write(("OUTP:STAT ON"))

    def disable_output(self):
        """Disable output.

        Sends the corresponding SCPI command string to the instrument over the bus.
        """
        self.get_interface().write(("OUTP:STAT OFF"))
