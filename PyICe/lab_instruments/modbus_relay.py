"""Modbus relay instrument driver.

>>> from PyICe.lab_instruments.modbus_relay import modbus_relay

"""
from ..lab_core import *  # noqa: F403
from .modbus_instrument import modbus_register


class modbus_relay(instrument):
    """Modbus_relay (instrument subclass)."""
    def __init__(self, serial_port, modbus_address):
        """Initialize modbus_relay.
        Stores configuration in ``_base_name``, ``modbus_relay`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            modbus_address: Modbus address to use.
            serial_port: Serial port to use.
        """
        import minimalmodbus
        minimalmodbus.BAUDRATE = 9600
        minimalmodbus.TIMEOUT = 5
        # Untested. If there's a problem, it's probably here.
        serial_port.write = serial_port.write_raw
        serial_port.read = serial_port.read_raw
        self._base_name = '2-channel Modbus RTU relay'
        instrument.__init__(
            self, f"Modbus Dual Relay @ {serial_port}:{modbus_address}")
        self.modbus_relay = minimalmodbus.Instrument(
            serial_port, modbus_address)
        # self.modbus_relay.debug = True
        # self.modbus_relay.serial.stopbits = 1
        # self.modbus_relay.serial.timeout = 1

    def add_channel_relay1(self, channel_name='relay1'):
        """Add a channel relay1.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument and maps it to the underlying device register for read/write access.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_register = modbus_register(channel_name,
                                       read_function=lambda: self.modbus_relay.read_register(
                                           registeraddress=1, functioncode=3),
                                       write_function=lambda data, relay_number=1: self._write_relay(
                                           data, relay_number)
                                       )
        # new_register =  register(channel_name,
        # size=1,
        # read_function=lambda: self.modbus_relay.read_register(registeraddress=1, functioncode=3),
        # write_function=lambda data, relay_number=1: self._write_relay(data,
        # relay_number))
        new_register.set_category('relay')
        return self._add_channel(new_register)

    def add_channel_relay2(self, channel_name='relay2'):
        """Add a channel relay2.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument and maps it to the underlying device register for read/write access.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_register = register(channel_name,
                                size=1,
                                read_function=lambda: self.modbus_relay.read_register(
                                    registeraddress=2, functioncode=3),
                                write_function=lambda data, relay_number=2: self._write_relay(data, relay_number))
        new_register.set_category('relay')
        return self._add_channel(new_register)

    def _write_relay(self, data, relay_number):
        self.modbus_relay.write_register(
            registeraddress=relay_number, value=int(
                256 if data else 512), functioncode=6)

    def flush(self):
        """Return the flush.

        Supports the ``modbus_relay`` workflow by performing the described operation.

        Returns:
            The flush result.
        """
        return self.modbus_relay.serial.read(
            self.modbus_relay.serial.inWaiting())
