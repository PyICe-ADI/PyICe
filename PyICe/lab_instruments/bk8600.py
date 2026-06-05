"""Bk8600 instrument driver.

>>> from PyICe.lab_instruments.bk8600 import bk8600

"""
from ..lab_core import *  # noqa: F403


class bk8600(scpi_instrument):
    """Single channel BK PRECISION 8600."""

    def __init__(self, interface_visa, remote_sense):
        """Initialize bk8600.
        Calls the parent class constructor and initializes instance-specific
        attributes for bk8600.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
            remote_sense: Remote sense to use.
        """
        self._base_name = 'bk8600'
        super(bk8600, self).__init__(f"BK8600 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        # initialize to instrument on, current 0
        self.clear_status()
        self.reset()
        self.get_interface().write(("CURR 0"))
        self.SetRemoteSense(remote_sense)
        self._write_output_enable(True)

    def add_channel(self, channel_name, add_extended_channels=True):
        """Helper channel adds primary current forcing channel.
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
        current_channel = self.add_channel_current(channel_name)
        current_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        if add_extended_channels:
            _voltage_sense_channel = self.add_channel_vsense(  # noqa: F841
                channel_name + "_vsense")
            _current_sense_channel = self.add_channel_isense(  # noqa: F841
                channel_name + "_isense")
            _power_sense_channel = self.add_channel_psense(  # noqa: F841
                channel_name + "_psense")
            _mode_channel = self.add_channel_mode(  # noqa: F841
                channel_name + "_mode")
        return current_channel

    def add_channel_voltage(self, channel_name):
        """Add single CV forcing channel.
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
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_voltage.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_vsense(self, channel_name):
        """Add output voltage reading channel.
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
        new_channel = channel(channel_name, read_function=self._read_vsense)
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_vsense.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_current(self, channel_name):
        """Add single CC forcing channel.
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
        new_channel = channel(channel_name, write_function=self._write_current)
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_current.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_isense(self, channel_name):
        """Add output current reading channel.
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
        new_channel = channel(channel_name, read_function=self._read_isense)
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_isense.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_power(self, channel_name):
        """Add single CW forcing channel.
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
        new_channel = channel(channel_name, write_function=self._write_power)
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_power.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_psense(self, channel_name):
        """Add output power reading channel.
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
        new_channel = channel(channel_name, read_function=self._read_psense)
        new_channel.set_description(
            self.get_name() +
            f': {self.add_channel_psense.__doc__}')
        return self._add_channel(new_channel)

    def add_channel_mode(self, channel_name):
        """Add a channel mode.
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
        new_channel = channel(channel_name, read_function=self._read_mode)
        return self._add_channel(new_channel)

    def add_channel_remote_sense(self, channel_name):
        """Enable/disable remote voltage sense through rear panel connectors.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = integer_channel(
            channel_name, size=1, write_function=self.SetRemoteSense)
        new_channel.set_description(self.get_name() +
                                    f': {self.add_channel_remote_sense.__doc__}')
        new_channel.write(self.GetRemoteSense())
        return self._add_channel(new_channel)

    def _write_voltage(self, voltage):
        """Set output voltage.

        Internal implementation detail; see the public API for usage.

        Args:
            voltage: Voltage value.
        """
        self.get_interface().write("FUNC VOLTage")
        self.get_interface().write(f"VOLTage {voltage}")

    def _write_current(self, current):
        """Set output current.

        Internal implementation detail; see the public API for usage.

        Args:
            current: Current value.
        """
        self.get_interface().write("FUNC CURRent")
        self.get_interface().write(f"CURR {current}")

    def _write_current_range(self, range=3):
        """Set current measurement range. Acceptable ranges are 3 and 30.
        Internal helper that sends the ``CURRent:RANGe`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            range: Measurement or output range.
        """
        self.get_interface().write(f"CURRent:RANGe {range}")

    def _write_power(self, power):
        """Set output power.

        Internal implementation detail; see the public API for usage.

        Args:
            power: Power level.
        """
        self.get_interface().write("FUNC POWer")
        self.get_interface().write(f"POWer {power}")

    def _write_output_enable(self, enable):
        """Set output enable.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.
        """
        if enable:
            self.get_interface().write("INPut 1")
        else:
            self.get_interface().write("INPut 0")

    def SetRemoteSense(self, remote_sense):
        """Set Remote Sense.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            remote_sense: Remote sense to use.
        """
        if remote_sense:
            self.get_interface().write("REMote:SENSe 1")
        else:
            self.get_interface().write("REMote:SENSe 0")

    def GetRemoteSense(self):
        """Return the GetRemoteSense.
        Sends the ``REMote:SENSe`` SCPI command to the instrument.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The GetRemoteSense result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        resp = self.get_interface().ask("REMote:SENSe?")
        if resp == '0':
            return False
        elif resp == '1':
            return True
        else:
            print(resp)
            raise Exception()

    def _read_vsense(self):
        """Returns instrument's measured output voltage.
        Internal helper that sends the ``MEAS:VOLT`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("MEAS:VOLT?"))

    def _read_isense(self):
        """Returns instrument's measured current output.
        Internal helper that sends the ``MEAS:CURR`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("MEAS:CURR?"))

    def _read_psense(self):
        """Returns instrument's measured power output.
        Internal helper that sends the ``FETCH:POW`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("FETCH:POW?"))

    def _read_mode(self):
        """Returns instrument's mode.
        Internal helper that computes and returns a derived value.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return self.get_interface().ask("FUNC?")
