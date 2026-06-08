"""Franken oven instrument driver.

>>> from PyICe.lab_instruments.Franken_oven import Franken_oven

"""
from .temperature_chamber import temperature_chamber
from .autonicstk import autonicstk


class Franken_oven(autonicstk, temperature_chamber):
    """Autonics controlled temperature chamber."""

    def __init__(self, interface_raw_serial, power_up=True):
        """Initialize franken_oven.
        Stores configuration in ``_base_name``, ``modbus_pid`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_raw_serial: Raw serial interface instance for communication.
            power_up: Power up to use.
        """
        import minimalmodbus
        minimalmodbus.BAUDRATE = 9600
        minimalmodbus.TIMEOUT = 5
        self._base_name = 'Autonics_Oven'
        # instrument.__init__(self,f"Autonics PID @ {interface_raw_serial}:1; relay @ {interface_raw_serial}:2")
        temperature_chamber.__init__(self)
        interface_raw_serial.write = interface_raw_serial.write_raw
        interface_raw_serial.read = interface_raw_serial.read_raw
        self.add_interface_raw_serial(interface_raw_serial)
        self.modbus_pid = minimalmodbus.Instrument(
            interface_raw_serial, slaveaddress=1)

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

    def _enable(self, enable):
        autonicstk._enable(self, enable)
        # The following uses the Alarm1 output relay to enable/disable the heat SSR and the Alarm2 output relay to enable/disable the cool SSR
        # Autonics Alarm wiring requires than modes both be set to "Absolute
        # High Limit"
        if enable == 1:
            # heat/cool
            autonicstk._write_alarm1_high(self, -199)  # alarm1 enables heat
            autonicstk._write_alarm2_high(self, -199)  # alarm2 enables cool
        if enable == 2:
            # heat only
            autonicstk._write_alarm1_high(self, -199)  # alarm1 enables heat
            autonicstk._write_alarm2_high(self, 300)  # ~alarm2 disables cool
        elif enable == 3:
            # cool only
            autonicstk._write_alarm1_high(self, 300)  # ~alarm1 disables heat
            autonicstk._write_alarm2_high(self, -199)  # alarm2 enables cool

    def _write_temperature(self, value):
        self.setpoint = value
        autonicstk._write_temperature(self, value)
        self._wait_settle()
