"""Test Equity 115 instrument driver.

>>> from PyICe.lab_instruments.TestEquity_115 import TestEquity_115

"""
from ..lab_core import *  # noqa: F403
from .temperature_chamber import temperature_chamber


class TestEquity_115(temperature_chamber):
    """TestEquity_115 with basic channels."""
    def __init__(self, interface_raw_serial):
        """Initialize test equity_115.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 4 instance attributes that configure the object's behavior.

        Args:
            interface_raw_serial: Raw serial interface instance for communication.
        """
        import minimalmodbus
        minimalmodbus.BAUDRATE = 9600
        minimalmodbus.TIMEOUT = 5
        # self._base_name = f"TestEquit115A @ {self.comport}"
        self._base_name = "TestEquit115A"
        temperature_chamber.__init__(self)
        self.sp = interface_raw_serial
        interface_raw_serial.write = interface_raw_serial.write_raw
        interface_raw_serial.read = interface_raw_serial.read_raw
        self.add_interface_raw_serial(interface_raw_serial)
        self.modbus_pid = minimalmodbus.Instrument(
            interface_raw_serial, slaveaddress=1)
        self.__scriptDebug = False

    def add_channels(self, channel_name):
        """Add a channels.
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
        temp_channel = temperature_chamber.add_channels(self, channel_name)
        return temp_channel

    def add_channel_enable_output(self, channel_name):
        """Enable/Disable heat and cool outputs.
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
        new_register = register(f'{channel_name}_enable',
                                size=1,
                                read_function=lambda: False if self.modbus_pid.read_register(
                                    2000, functioncode=3) else True,
                                write_function=self._enable)
        new_register.add_preset('Run', True)
        new_register.add_preset('Stop', False)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Enables')
        new_register.set_description(self.add_channel_enable_output.__doc__)
        return self._add_channel(new_register)

    def _enable(self, enable):
        self.modbus_pid.write_register(
            2000, 0 if enable else 1, functioncode=6)

    def _read_temperature_sense(self):
        temp = None
        while (temp is None):
            try:
                temp = self.modbus_pid.read_register(100, 1, 3, True)
            except (IOError, ValueError):
                if self.__scriptDebug is True:  # pylint: disable=E1101; __scriptDebug is initialized in __init__ but pylint cannot resolve the name-mangled attribute (_TestEquity_115__scriptDebug) through the class hierarchy
                    print("TE115A: get_temp communication error")
                time.sleep(5)
        return float(temp)

    def _write_temperature(self, value):
        self.modbus_pid.write_register(300, float(value), 1, 16, True)

    def instrumentInfoString(self):
        """Return the instrumentInfoString.

        Supports the ``TestEquity_115`` workflow by performing the described operation.

        Returns:
            The instrumentInfoString result.
        """
        # pylint: disable=no-member; attributes set externally before this method is called (incomplete interface stub)
        return "%s - %s - SN:%s - %s" % \
            (self._manufacturer, self._modelNumber,
             self._serialNumber, self._address)
