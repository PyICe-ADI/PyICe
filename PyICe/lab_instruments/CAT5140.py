"""C A T5140 instrument driver.

>>> from PyICe.lab_instruments.CAT5140 import CAT5140

"""
from ..lab_core import *  # noqa: F403
from .. import twi_interface


class CAT5140(instrument):
    """ONSemi/Catalyst I2C 256 Tap Potentiometer."""

    def __init__(self, interface_twi):
        """Initialize c a t5140.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 4 instance attributes that configure the object's behavior.

        Args:
            interface_twi: TWI/I2C interface instance.
        """
        self.addr7 = 0b0101000
        instrument.__init__(
            self, f'ONSemi/Catalyst I2C 8-bit Potentiometer at 0x{self.addr7:X}')
        self._base_name = 'CAT5140'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        self.tries = 2

    def _write_byte(self, addr7, subaddr, data):
        tries = self.tries
        while tries:
            try:
                tries -= 1
                # self.twi.write_byte(addr7, subaddr, data)
                self.twi.write_register(
                    addr7=addr7,
                    commandCode=subaddr,
                    data=data,
                    data_size=8,
                    use_pec=False)
                return
            except twi_interface.i2cError as e:
                traceback.print_exc()
                self.twi.resync_communication()
                if not tries:
                    raise twi_interface.i2cIOError(
                        "CAT5140 Communication Failed.") from e

    def set_output(self, value):
        """Set the output.

        Updates the output in the object's internal state.

        Args:
            value: Value to set.
        """
        assert value >= 0
        assert value <= 2**8 - 1
        self._write_byte(self.addr7, 0x00, value)

    def get_output(self):
        """Return the current output.
        Reads the corresponding register from the device via TWI/I2C.
        Returns the stored output from the object's internal state.

        Performs a register-level transaction over the communication bus.

        Returns:
            The current output.

        Raises:
            i2cIOError: If the operation fails.
        """
        tries = self.tries
        while tries:
            try:
                tries -= 1
                # value = self.twi.read_byte(self.addr7, 0x00)
                value = self.twi.read_register(
                    addr7=self.addr7, commandCode=0x00, data_size=8, use_pec=False)
                return value
            except twi_interface.i2cError as e:
                traceback.print_exc()
                self.twi.resync_communication()
                if not tries:
                    raise twi_interface.i2cIOError(
                        "CAT5140 Communication Failed.") from e

    def _write_percent(self, percent):
        """Value is between 0 and 1. DAC is biased toward 0 so that full scale is not achievable.

        Internal implementation detail; see the public API for usage.

        Args:
            percent: Percent to use.
        """
        assert percent >= 0
        assert percent <= 1
        code = min(int(round(percent * 2**8)), 2**8 - 1)
        self.set_output(code)

    def add_channel_code(self, channel_name):
        """Add a channel code.
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
        code_channel = channel(channel_name, write_function=self.set_output)
        return self._add_channel(code_channel)

    def add_channel_percent(self, channel_name):
        """Add a channel percent.
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
        percent_channel = channel(
            channel_name, write_function=self._write_percent)
        return self._add_channel(percent_channel)

    def add_channel_code_readback(self, channel_name):
        """Add a channel code readback.
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
        code_channel = channel(channel_name, read_function=self.get_output)
        return self._add_channel(code_channel)

    def add_channel_percent_readback(self, channel_name):
        """Add a channel percent readback.
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
        percent_channel = channel(
            channel_name,
            read_function=lambda: self.get_output() /
            float(
                2**8 -
                1))
        return self._add_channel(percent_channel)

    def _select_nonvolatile_register(self):
        # self.twi.write_byte(self.addr7, 0x08, 0x00)
        self.twi.write_register(
            addr7=self.addr7,
            commandCode=0x08,
            data=0x00,
            data_size=8,
            use_pec=False)

    def _select_volatile_register(self):
        # self.twi.write_byte(self.addr7, 0x08, 0x01)
        self.twi.write_register(
            addr7=self.addr7,
            commandCode=0x08,
            data=0x01,
            data_size=8,
            use_pec=False)

    def add_channel_select_nonvolatile_register(self, channel_name):
        """Add a channel select nonvolatile register.
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
        nvselect_channel = channel(
            channel_name,
            write_function=lambda x: self._select_nonvolatile_register())
        return self._add_channel(nvselect_channel)

    def add_channel_select_volatile_register(self, channel_name):
        """Add a channel select volatile register.
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
        volselect_channel = channel(
            channel_name,
            write_function=lambda x: self._select_volatile_register())
        return self._add_channel(volselect_channel)
