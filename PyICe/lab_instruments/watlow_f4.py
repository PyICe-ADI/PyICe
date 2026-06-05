"""Watlow f4 instrument driver.

>>> from PyICe.lab_instruments.watlow_f4 import watlow_f4

"""

from .temperature_chamber import temperature_chamber
from .modbus_instrument import modbus_instrument, register_description as rd


class watlow_f4(temperature_chamber, modbus_instrument):
    """Watlow_f4."""
    REGISTERS = [
        rd('SV1', 300, readable=True, writeable=True,
           number_of_decimals=1, signed=True),
        rd('PV1', 100, readable=True, writeable=False,
           number_of_decimals=1, signed=True),
        rd('heat_power', 103, readable=True, writeable=False,
           number_of_decimals=2, signed=True),

        # 308 Idle Set Point, Channel 1, Power Out Action
        # 1206 Power-Out Action
        # 2072 Power On
        # 2073 Power Off
    ]

    def __init__(self, interface_raw_serial, modbus_address, baudrate=19200):
        """Initialize watlow_f4.
        Stores configuration in ``_base_name``, ``_pv``, ``_sv`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.

        Args:
            baudrate: Serial baud rate in bits per second.
            interface_raw_serial: Raw serial interface instance for communication.
            modbus_address: Modbus address to use.
        """
        self._base_name = 'Watlow F4'
        temperature_chamber.__init__(self)
        modbus_instrument.__init__(self,
                                   interface_raw_serial=interface_raw_serial,
                                   modbus_address=modbus_address,
                                   baudrate=baudrate,
                                   mode='rtu')  # second to preserve self._interfaces
        assert self.read_register(
            606) == 1, 'The decimal point register number must be set to one in order to use the watlow_f4 driver.'
        self.add_registers(type(self).REGISTERS)
        self._sv = self['SV1']
        self._pv = self['PV1']

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
        self.remove_channel(self._sv)
        self.remove_channel(self._pv)
        return super(watlow_f4, self).add_channels(channel_name)

    def _write_temperature(self, value):
        """Program tempertaure setpoint to value. Implement for specific hardware.

        Internal implementation detail; see the public API for usage.

        Args:
            value: Value to set.
        """
        self.setpoint = value
        self._sv.write(value)
        self._wait_settle()

    def _read_temperature_sense(self):
        """Read back actual chamber temperature.  Implement for specific hardware.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.

        Returns:
            The measured value.
        """
        return self._pv.read()

    def _enable(self, enable):
        """Enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.
        """
        if enable:
            pass  # ?
        else:
            self._sv.write(25)

    def shutdown(self, shutdown):
        """Separate method to turn off temperature chamber.

        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.

        Args:
            shutdown: Shutdown to use.
        """
        self._enable(not shutdown)
