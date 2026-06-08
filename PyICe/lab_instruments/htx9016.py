"""Htx9016 instrument driver.

>>> from PyICe.lab_instruments.htx9016 import htx9016

"""
from ..lab_core import *  # noqa: F403
import math


class htx9016(scpi_instrument):
    """5 Channel RF MUX Hypertronix (Steve Martin) HTX9016.

    DC Coupled or AC Coupled versions available.
    Should be good from 100Hz (AC) or 0Hz (DC) to about 1GHz.
    """
    def __init__(self, interface_visa):
        """Initialize htx9016.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'htx9016'
        scpi_instrument.__init__(self, f"HTX9016 {interface_visa}")
        self.add_interface_visa(interface_visa, timeout=0.5)

    def __del__(self):
        """Close interface (serial) port on exit.

        Performs cleanup when the object is garbage-collected.
        """
        self.get_interface().close()

    def _decode_readback(self):
        value = self.get_interface().ask(":SELEct:CHANnel?")
        if value == "0":
            return 0
        elif value in ["2", "4", "8", "16", "32"]:
            return math.log2(int(value))
        else:
            raise Exception(
                f"*** HTX9016 RF MUX *** CAUTION: Multiple channels are on, return value {value} should be a power of 2!")

    def add_channel(self, channel_name):
        """Add a channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:SELEct:CHANnel`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda ch: self.get_interface().write(
                f":SELEct:CHANnel {ch}"))
        new_channel._read = self._decode_readback
        # Axicom HF3 relay max operation time 6ms with diode. I doubled it SLM.
        new_channel.set_write_delay(0.012)
        new_channel.add_preset("1")
        new_channel.add_preset("2")
        new_channel.add_preset("3")
        new_channel.add_preset("4")
        new_channel.add_preset("5")
        new_channel.add_preset("OFF")
        new_channel.write("OFF")
        return self._add_channel(new_channel)

    def get_serial_number(self):
        """Return the serial number.
        Sends the ``:STORe:SERIalnum`` SCPI command to the instrument.
        Returns the stored serial number from the object's internal state.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The current serial number.
        """
        return self.get_interface().ask(":STORe:SERIalnum?")
