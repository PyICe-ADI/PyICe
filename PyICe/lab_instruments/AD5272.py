"""A D5272 instrument driver.

>>> from PyICe.lab_instruments.AD5272 import AD5272

"""
from ..lab_core import *  # noqa: F403
from .. import twi_interface


class AD5272(instrument):
    """Analog Devices I2C Precision Potentiometer / Rheostat.

    http://www.analog.com/static/imported-files/data_sheets/AD5272_5274.pdf
    """
    def __init__(self, interface_twi, addr7, full_scale_ohms=100000):
        """Interface_twi is a interface_twi.

        addr7 is the 7-bit I2C address of the AD5272 set by pinstrapping.
        Choose addr7 from 0x2F, 0x2C, 0x2E

        Args:
            addr7: 7-bit I2C device address.
            full_scale_ohms: Full scale ohms to use.
            interface_twi: TWI/I2C interface instance.

        Raises:
            ValueError: If the provided value is out of range or invalid.
        """
        instrument.__init__(
            self, f'Analog Devices I2C 10-bit Potentiometer at 0x{addr7:X}')
        self._base_name = 'AD5272'
        self.add_interface_twi(interface_twi)
        self.twi = interface_twi
        if addr7 not in [0x2C, 0x2E, 0x2F]:
            raise ValueError(
                "\n\n\nAD5272 only supports addresses 0x2C, 0x2E, 0x2F")
        self.addr7 = addr7
        self.tries = 2
        self.enable()
        self.full_scale_ohms = full_scale_ohms

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
                        "AD5272 Communication Failed.") from e

    def enable(self, enable=True):
        """Place AD5272 into shutdown by writing enabled=False.

        Re-enable by writing enabled=True

        Args:
            enable: Enable or disable.
        """
        if enable:
            self._write_byte(self.addr7, 0x9 << 2, 0x00)
            # RDAC register write protect disable (allow i2c update)
            self._write_byte(self.addr7, 0x7 << 2, 0x02)
        else:  # shutdown
            # self.twi.write_byte(self.addr7, 0x9<<2, 0x01)
            self.twi.write_register(
                addr7=self.addr7,
                commandCode=0x9 << 2,
                data=0x01,
                data_size=8,
                use_pec=False)

    def set_output(self, value):
        """Set the output.

        Updates the output in the object's internal state.

        Args:
            value: Value to set.
        """
        assert value >= 0
        assert value <= 2**10 - 1
        value = int(value)
        lsbyte = value & 0xFF
        msbyte = 0x1 << 2 | value >> 8
        # RDAC register write protect disable (allow i2c update)
        self._write_byte(self.addr7, 0x7 << 2, 0x02)
        self._write_byte(self.addr7, msbyte, lsbyte)

    def get_output(self):
        """Return the current output.
        Queries the instrument for its current output and returns the parsed
        response.
        Queries the instrument for its current output and returns the parsed
        response.

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
                # self.twi.write_byte(self.addr7, 0x2<<2, 0x00)
                self.twi.write_register(
                    addr7=self.addr7,
                    commandCode=0x2 << 2,
                    data=0x00,
                    data_size=8,
                    use_pec=False)
                self.twi.start()
                self.twi.write(self.twi.read_addr(self.addr7))
                msbyte = self.twi.read_ack()
                lsbyte = self.twi.read_nack()
                self.twi.stop()
                return (msbyte & 0b11) << 8 | lsbyte
            except twi_interface.i2cError as e:
                traceback.print_exc()
                self.twi.resync_communication()
                if not tries:
                    raise twi_interface.i2cIOError(
                        "AD5272 Communication Failed.") from e

    def _write_percent(self, percent):
        """Value is between 0 and 1. DAC is biased toward 0 so that full scale is not achievable.

        Internal implementation detail; see the public API for usage.

        Args:
            percent: Percent to use.
        """
        assert percent >= 0
        assert percent <= 1
        code = min(int(round(percent * 2**10)), 2**10 - 1)
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
        code_channel.set_description('Raw 10-bit DAC code input')
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

    def add_channel_resistance(self, channel_name):
        """Add a channel resistance.
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
        resistance_channel = channel(
            channel_name, write_function=lambda resistance: self._write_percent(
                float(resistance) / self.full_scale_ohms))
        return self._add_channel(resistance_channel)

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
                2**10 -
                1))
        return self._add_channel(percent_channel)

    def add_channel_resistance_readback(self, channel_name):
        """Add a channel resistance readback.
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
        resistance_channel = channel(
            channel_name,
            read_function=lambda: self.get_output() *
            self.full_scale_ohms /
            float(
                2**10 -
                1))
        return self._add_channel(resistance_channel)

    def add_channel_enable(self, channel_name):
        """Add a channel enable.
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
        enable_channel = integer_channel(
            channel_name, size=1, write_function=self.enable)
        return self._add_channel(enable_channel)
