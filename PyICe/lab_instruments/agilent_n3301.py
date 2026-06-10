"""Agilent n3301 instrument driver.

>>> from PyICe.lab_instruments.agilent_n3301 import agilent_n3301

"""
from PyICe.lab_core import *  # noqa: F403


class agilent_n3301(scpi_instrument):
    """Agilent N3301 Electronic Load with two channels.

    This is a minimal class to interface with an Agilent N3301 electronic load.
    Only immediate constant current mode is supported, which means you can only control
    setting a constant current load and the new setpoint takes effect right away.
    """
    def __init__(self, interface_visa):
        """Constructor takes visa GPIB address or interface object (visa,rl1009, rs232) as parameter.  Ex: "GPIB0::3".
        Calls the parent class constructor and initializes instance-specific
        attributes for agilent_n3301.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'agilent_n3301'
        # instrument.__init__(self,f'n3300: @ {interface_visa}')
        super(agilent_n3301, self).__init__(f'n3300: @ {interface_visa}')
        self.add_interface_visa(interface_visa, timeout=5)
        # Reset the instrument to put it in a known state, turn
        # ON all the loads, and set them to zero.
        self.get_interface().write("*RST")

    def __del__(self):
        """Reset the instrument to quickly set all loads.

        to zero.  (Draw no power)
        """
        self.get_interface().write("*RST")
        self.get_interface().close()

    def add_channel(self, channel_name, channel_num, add_sense_channel=True):
        """Add current force writable channel. Optionally add current readback _isense channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            add_sense_channel: Add sense channel to use.
            channel_name: Name for the new channel.
            channel_num: Physical channel number.
        """
        self.add_channel_current(channel_name, channel_num)
        if add_sense_channel:
            self.add_channel_isense(channel_name + "_isense", channel_num)

    def add_channel_current(self, channel_name, channel_num):
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
            channel_num: Physical channel number.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda current: self._write_current(
                channel_num,
                current))
        self._add_channel(new_channel)

    def add_channel_isense(self, channel_name, channel_num):
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
            channel_num: Physical channel number.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._read_isense(channel_num))
        self._add_channel(new_channel)

    def _write_current(self, channel_num, current):
        self.get_interface().write(f"INSTRUMENT {channel_num}")
        self.get_interface().write(f"CURRENT {current}")

    def _read_isense(self, channel_num):
        self.get_interface().write(f"INSTRUMENT {channel_num}")
        self.get_interface().write("MEASURE:CURRENT?")
        return float(self.get_interface().read())
