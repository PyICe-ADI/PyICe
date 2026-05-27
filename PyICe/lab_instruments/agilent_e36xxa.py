"""Agilent e36xxa instrument driver.

>>> from PyICe.lab_instruments.agilent_e36xxa import agilent_e36xxa

"""
from PyICe.lab_core import *  # noqa: F403
import time


class agilent_e36xxa(scpi_instrument):
    """Generic base class for Agilent programmable DC power supply."""

    def add_channel_voltage(self, channel_name, num):
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
            num: Count or number.

        Returns:
            The newly created channel object.
        """
        voltage_channel = channel(
            channel_name,
            write_function=lambda voltage: self.set_voltage(
                num,
                voltage))
        voltage_channel.set_write_delay(self._default_write_delay)
        return self._add_channel(voltage_channel)

    def add_channel_current(self, channel_name, num):
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
            num: Count or number.

        Returns:
            The newly created channel object.
        """
        current_channel = channel(
            channel_name,
            write_function=lambda current: self.set_current(
                num,
                current))
        current_channel.set_write_delay(self._default_write_delay)
        return self._add_channel(current_channel)

    def add_channel_vsense(self, channel_name, num):
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
            num: Count or number.

        Returns:
            The newly created channel object.
        """
        vsense_channel = channel(channel_name,
                                 read_function=lambda: self.read_vsense(num))
        return self._add_channel(vsense_channel)

    def add_channel_isense(self, channel_name, num):
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
            num: Count or number.

        Returns:
            The newly created channel object.
        """
        isense_channel = channel(channel_name,
                                 read_function=lambda: self.read_isense(num))
        return self._add_channel(isense_channel)

    def set_voltage(self, num, voltage):
        """Set the voltage.
        Sends the ``INSTrument:SELect`` SCPI command to the instrument.
        Sends the appropriate SCPI command to configure the instrument's
        voltage.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            num: Count or number.
            voltage: Voltage value.
        """
        self.get_interface().write(("INSTrument:SELect " + num))
        self.get_interface().write(("VOLTage " + str(voltage)))
        time.sleep(0.2)

    def set_current(self, num, current):
        """Set the current.
        Sends the ``INSTrument:SELect`` SCPI command to the instrument.
        Sends the appropriate SCPI command to configure the instrument's
        current.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            current: Current value.
            num: Count or number.
        """
        self.get_interface().write(("INSTrument:SELect " + num))
        self.get_interface().write(("CURRent " + str(current)))
        time.sleep(0.2)

    def read_vsense(self, num):
        """Query the instrument and return float representing actual measured terminal voltage.
        Sends the appropriate command to the instrument and parses the
        response.
        Sends the ``:MEASure:VOLTage`` SCPI command to the instrument.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            num: Count or number.

        Returns:
            The value read from the device or channel.
        """
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        self.get_interface().write((":INSTrument:SELect " + num))
        time.sleep(0.2)
        return float(self.get_interface().ask((":MEASure:VOLTage?")))

    def read_isense(self, num):
        """Query the instrument and return float representing actual measured terminal current.
        Sends the appropriate command to the instrument and parses the
        response.
        Sends the ``:INSTrument:SELect`` SCPI command to the instrument.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            num: Count or number.

        Returns:
            The value read from the device or channel.
        """
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        self.get_interface().write((":INSTrument:SELect " + num))
        time.sleep(0.2)
        return float(self.get_interface().ask(":MEASure:CURRent?"))

    def set_ilim(self, channel_name, ilim):
        """Set the ilim.

        Updates the ilim in the object's internal state.

        Args:
            channel_name: Name for the new channel.
            ilim: Current limit.

        Raises:
            Exception: If an unexpected error occurs.
        """
        raise Exception('removed, write to the appropriate channel instead')

    def enable_output(self, state):
        """Enable output.
        Sends the ``:OUTput:STATe`` SCPI command to the instrument.
        Enables the output function.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            state: Desired state (True/False or instrument-specific value).
        """
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        if state:
            self.get_interface().write(":OUTput:STATe ON")
        else:
            self.get_interface().write(":OUTput:STATe OFF")

    def output_enabled(self):
        """Return output enabled result.
        Sends the ``OUTput:STATe`` SCPI command to the instrument.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The output enabled result.
        """
        return self.get_interface().ask("OUTput:STATe?")

    def _set_remote_mode(self, remote=True):
        """Required for RS-232 control.  Not allowed for GPIB control.
        Internal helper that sends the ``:SYSTem:LOCal`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            remote: Remote to use.
        """
        self.get_interface().write("\n")   # Clear out instrument's input buffer
        time.sleep(0.2)
        if remote:
            self.get_interface().write(":SYSTem:REMote")
        else:
            self.get_interface().write(":SYSTem:LOCal")
