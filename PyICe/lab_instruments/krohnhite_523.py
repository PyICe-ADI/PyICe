"""Krohnhite 523 instrument driver.

>>> from PyICe.lab_instruments.krohnhite_523 import krohnhite_523

"""
from ..lab_core import *  # noqa: F403


class krohnhite_523(instrument):
    """Krohn-Hite Model 523 Precision DC Source/Calibrator."""

    def __init__(self, interface_visa):
        """Initialize krohnhite_523.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'krohnhite_523'
        instrument.__init__(self, f"krohnhite_523 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        # initialize to instrument on, value 0
        self.float_lo_terminal()  # float the lo terminal by default
        self.disable_crowbar()  # turn off crowbar by default

    def ground_lo_terminal(self):
        """Perform ground lo terminal operation.

        Supports the ``krohnhite_523`` workflow by performing the described operation.
        """
        self.get_interface().write(("g"))

    def float_lo_terminal(self):
        """Perform float lo terminal operation.

        Supports the ``krohnhite_523`` workflow by performing the described operation.
        """
        self.get_interface().write(("f"))

    def disable_crowbar(self):
        """Disable crowbar.

        Deactivates crowbar so that subsequent operations skip it.
        """
        self.get_interface().write(("v"))

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

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self._write_current)
        return self._add_channel(new_channel)

    def add_channel_voltage_compliance(self, channel_name):
        """Add a channel voltage compliance.
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
        new_channel = channel(channel_name,
                              write_function=self._write_compliance_voltage)
        return self._add_channel(new_channel)

    def _write_current(self, current):
        current = float(current) * 1000  # current must be specified in mA
        self.current = float(current)
        self.get_interface().write((f"{current}mA"))

    def _write_voltage(self, voltage):
        voltage = float(voltage)
        if voltage < 1e-3:
            self.get_interface().write((f"{voltage * 1e6}uV"))
        elif voltage < 1.0:
            self.get_interface().write((f"{voltage * 1e3}mV"))
        else:
            self.get_interface().write((f"{voltage}V"))

    def _write_compliance_voltage(self, compliance_voltage):
        compliance_voltage = int(float(compliance_voltage))
        if 1 <= compliance_voltage and compliance_voltage <= 110:
            self.get_interface().write((f"{compliance_voltage}C"))
        else:
            raise Exception(
                f"Krohn-Hite 523: Invalid Compliance voltage: {compliance_voltage}. Must be 1V to 110V")
