"""Hypertronix powermux instrument driver.

>>> from PyICe.lab_instruments.hypertronix_powermux import powermux

"""
from ..lab_core import scpi_instrument, channel


class powermux(scpi_instrument):
    """Boston Design Center 8x8 crosspoint relay mux + 4 aux channels, this needs an example of how to use AUX channels."""

    def __init__(self, interface_visa):
        """Initialize powermux.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 4 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'powermux'
        scpi_instrument.__init__(self, f"powermux @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.columns = {}
        self.columns["aux"] = 0  # aux relays are treated as x=0
        self.rows = {}
        self.board = 0

    def add_channel_relay_names(self, channel_name, column_name, row_name):
        """Add a channel relay names.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
            column_name: Name of the database column.
            row_name: Database row identifier or label.

        Returns:
            List of matching items.
        """
        relay_channel = channel(
            channel_name, write_function=lambda closed: self.set_relay(
                column_name, row_name, closed))
        return self._add_channel(relay_channel)

    def add_channel_relay(self, channel_name, column_number, row_number):
        """Add a channel relay.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        Args:
            channel_name: Name for the new channel.
            column_number: Column number to use.
            row_number: Row number to use.

        Returns:
            The newly created channel object.
        """
        relay_channel = channel(
            channel_name, write_function=lambda closed: self._set_relay(
                column_number, row_number, closed))
        return self._add_channel(relay_channel)

    def add_column(self, column_name, num):
        """Register named column. num is physical column number.  valid range is [1-8] and [0] for auxiliary channels.

            column "aux" is predefined

        Args:
            column_name: Name of the database column.
            num: Count or number.
        """
        self.columns[column_name] = num

    def add_row(self, row_name, num):
        """Register named row. num is physical row number.  valid range is [1-8] and [1-4] for auxiliary channels.

            column "aux" is predefined

        Args:
            num: Count or number.
            row_name: Database row identifier or label.
        """
        self.rows[row_name] = num

    def set_relay(self, column_name, row_name, closed):
        """Open and close a relay by row/column names.

        Updates the relay in the object's internal state.

        Args:
            closed: Closed to use.
            column_name: Name of the database column.
            row_name: Database row identifier or label.
        """
        if closed:
            self.close_relay(column_name, row_name)
        else:
            self.open_relay(column_name, row_name)

    def _set_relay(self, column_number, row_number, closed):
        cmd = f"{self.board}{column_number}{row_number}"
        if closed:
            self.get_interface().write((f"CLOSe (@{cmd})"))
        else:
            self.get_interface().write((f"OPEN (@{cmd})"))

    def close_relay(self, column_name, row_name):
        """Close relay at named (column, row).

        Releases resources and restores the system to a safe state.

        Args:
            column_name: Name of the database column.
            row_name: Database row identifier or label.
        """
        self._set_relay(
            self.columns[column_name],
            self.rows[row_name],
            closed=True)

    def open_relay(self, column_name, row_name):
        """Open relay at named (column, row).

        Establishes the connection or prepares the resource for use.

        Args:
            column_name: Name of the database column.
            row_name: Database row identifier or label.
        """
        self._set_relay(
            self.columns[column_name],
            self.rows[row_name],
            closed=False)

    def _set_relay_wdelay(self, delay, relay_list, closed):
        """Close or open list of relays at named (column, row) with delay between each.
        Internal helper that sends the ``:DELay`` SCPI command.

        Internal implementation detail; see the public API for usage.

        Args:
            closed: Closed to use.
            delay: Delay time in seconds.
            relay_list: Relay list to use.
        """
        if closed:
            command_string = "CLOSe"
        else:
            command_string = "OPEN"
        command_string += f":DELay (@{delay}"
        for relay in relay_list:
            column_number = relay[0]
            row_number = relay[1]
            command_string += f",{self.board}{column_number}{row_number}"
        command_string += ")"
        self.get_interface().write((command_string))

    def close_relay_wdelay(self, delay, relay_list):
        """Close list of relays at named (column, row) with delay between each.

        Releases resources and restores the system to a safe state.

        Args:
            delay: Delay time in seconds.
            relay_list: Relay list to use.
        """
        self._set_relay_wdelay(delay, relay_list, closed=True)

    def open_relay_wdelay(self, delay, relay_list):
        """Open list of relays at named (column, row) with delay between each.

        Establishes the connection or prepares the resource for use.

        Args:
            delay: Delay time in seconds.
            relay_list: Relay list to use.
        """
        self._set_relay_wdelay(delay, relay_list, closed=False)

    def open_all(self, sync_channels=False):
        """Open all relays, set sync_channels to true to keep the channels synced (no need to do this if shutting down).

        Establishes the connection or prepares the resource for use.

        Args:
            sync_channels: Sync channels to use.
        """
        if sync_channels:
            for relay_channel in self.get_all_channels_list():
                relay_channel.write(False)
        else:
            self.get_interface().write(("OPEN ALL"))

    def test(self):
        """Run the built in test routine.

        Sends the corresponding SCPI command string to the instrument over the bus.
        """
        self.get_interface().write(("*TST?"))
