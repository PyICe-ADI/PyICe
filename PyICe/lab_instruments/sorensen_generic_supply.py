"""Sorensen generic supply instrument driver.

>>> from PyICe.lab_instruments.sorensen_generic_supply import sorensen_generic_supply

"""
from ..lab_core import *  # noqa: F403


class sorensen_generic_supply(instrument):
    """Sorensen_generic_supply (instrument subclass)."""
    def __init__(self, interface_visa):
        """interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'sorensen_generic_supply'
        instrument.__init__(self, f"{self.sorensen_name} @ {interface_visa}")  # pylint: disable=E1101; sorensen_name is set by subclass __init__ (e.g. sorensen_dlm_60_10, sorensen_xt_250_25) before calling super().__init__
        self.add_interface_visa(interface_visa)
        # initialize to instrument on, all voltages 0
        # self.get_interface().write(("VSET 0"))
        # self.get_interface().write(("ISET 0"))
        # self.get_interface().write(("OUT 1"))
        self._write_voltage(0.0)
        self._write_current(0.0)
        self._enable_output()

    def add_channel(self, channel_name, ilim=1, add_extended_channels=True):
        """Helper method adds primary voltage forcing channel channe_name.

        optionally also adds _ilim forcing channel and _vsense and _isense readback channels.

        Args:
            add_extended_channels: If True, add sense and mode channels.
            channel_name: Name for the new channel.
            ilim: Current limit.

        Returns:
            The newly created channel object.
        """
        voltage_channel = self.add_channel_voltage(channel_name)
        if add_extended_channels:
            self.add_channel_current(channel_name + "_ilim")
            self.add_channel_vsense(channel_name + "_vsense")
            self.add_channel_isense(channel_name + "_isense")
            self.write_channel(channel_name + "_ilim", ilim)
        else:
            self._write_current(ilim)
        return voltage_channel

    def add_channel_voltage(self, channel_name):
        """Add a channel voltage.
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
        new_channel = channel(channel_name, write_function=self._write_voltage)
        return self._add_channel(new_channel)

    def add_channel_current(self, channel_name):
        """Add a channel current.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
        """
        new_channel = channel(channel_name, write_function=self._write_current)
        self._add_channel(new_channel)

    def add_channel_vsense(self, channel_name):
        """Add a channel vsense.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
        """
        new_channel = channel(channel_name, read_function=self._read_vsense)
        self._add_channel(new_channel)

    def add_channel_isense(self, channel_name):
        """Add a channel isense.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
        """
        new_channel = channel(channel_name, read_function=self._read_isense)
        self._add_channel(new_channel)

    def _enable_output(self):
        """Enable output.

        Internal implementation detail; see the public API for usage.
        """
        self.get_interface().write(("OUT 1"))

    def _write_voltage(self, voltage):
        """Set named channel to force voltage, optionally with ilim compliance current.

        Internal implementation detail; see the public API for usage.

        Args:
            voltage: Voltage value.
        """
        self.get_interface().write((f"VSET {voltage}"))

    def _write_current(self, ilim):
        """Set named channel's compliance current.

        Internal implementation detail; see the public API for usage.

        Args:
            ilim: Current limit.
        """
        self.get_interface().write((f"ISET {ilim}"))

    def _read_vsense(self, channel_name):
        """Returns instrument's measured output voltage.
        Internal helper that computes and returns a derived value.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("VOUT?").lstrip("VOUT "))

    def _read_isense(self, channel_name):
        """Returns instrument's measured output current.
        Internal helper that computes and returns a derived value.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("IOUT? ").lstrip("IOUT "))
