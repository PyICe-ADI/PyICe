"""Sun ec1x instrument driver.

>>> from PyICe.lab_instruments.sun_ec1x import sun_ec1x

"""
from ..lab_core import *  # noqa: F403
from .sun_ecxx import sun_ecxx


class sun_ec1x(sun_ecxx):
    """Sun ec1x oven.

    use wait_settle to wait for the soak to complete
    defaults to window = 1, soak=90
    extra data
    _sense - the sensed temperature
    _window - the temperature window
    _time - the total settling time (including soak)
    _soak - the programmed soak time

    upper_temp_limit (default 165) and lower_temp_limit (default -65) can be modified as properties of the sun_ec1x object outside the PyICe channel framework
    """
    def __init__(self, interface_visa):
        """Initialize sun_ec1x.
        Stores configuration in ``_base_name``, ``lower_temp_limit``,
        ``upper_temp_limit`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'sun_ec1x'
        sun_ecxx.__init__(self, interface_visa)
        self.upper_temp_limit = 165
        self.lower_temp_limit = -65
        self.get_interface().write('SINT=NNNNNNNNNN0')
        time.sleep(1)
        slag = self.get_interface().resync()
        print(f"Flushed {len(slag)} characters: {slag}.")
        self.shutdown(False)
        self._enable(True)

    def add_channel_user_sense(self, channel_name):
        """Channel_name represents secondary non-control thermocouple readback.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output. Sends the appropriate SCPI configuration commands to the hardware.

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name, read_function=lambda: float(
                self.get_interface().ask("UCHAN?")))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_user_sense.__doc__)
        return self._add_channel(new_channel)

    def _write_temperature(self, value):
        """Set named channel to new temperature "value".
        Internal implementation detail; see the public API for usage.

        Internal implementation detail; see the public API for usage.

        Args:
            value: Value to set.
        """
        self.setpoint = value
        time.sleep(1)
        self.get_interface().write(f"SET={value}")
        time.sleep(1)
        self.time = 0
        self._wait_settle()

    def _enable(self, enable):
        """Individually control heat/cool outputs. Usually used through channel framework.
        Internal helper that sends the ``Unknown`` SCPI command.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if enable is False or enable == 0:
            time.sleep(0.5)
            self.get_interface().write('HOFF')
            time.sleep(0.5)
            self.get_interface().write('COFF')
            time.sleep(0.5)
        elif enable is True or enable == 1:
            time.sleep(0.5)
            self.get_interface().write('HON')
            time.sleep(0.5)
            self.get_interface().write('CON')
            time.sleep(0.5)
        elif enable == 2:
            # heat only
            time.sleep(0.5)
            self.get_interface().write('HON')
            time.sleep(0.5)
            self.get_interface().write('COFF')
            time.sleep(0.5)
        elif enable == 3:
            # cool only
            time.sleep(0.5)
            self.get_interface().write('HOFF')
            time.sleep(0.5)
            self.get_interface().write('CON')
            time.sleep(0.5)
        else:
            raise Exception(f'Unknown oven enable value: {enable}')

    def shutdown(self, shutdown):
        """Turn entire temp controller on or off. This is different than enabling/disabling the heat and cool outputs.

        Supports the ``sun_ec1x`` workflow by performing the described operation.

        Args:
            shutdown: Shutdown to use.
        """
        if shutdown:
            time.sleep(0.5)
            self.get_interface().write('OFF')
            time.sleep(0.5)
        else:
            time.sleep(0.5)
            self.get_interface().write('ON')
            time.sleep(0.5)
    upper_temp_limit = property(
        lambda self: float(
            self.get_interface().ask('UTL?')),
        lambda self,
        temp: self.get_interface().write(
            f'UTL={temp}'))
    lower_temp_limit = property(
        lambda self: float(
            self.get_interface().ask('LTL?')),
        lambda self,
        temp: self.get_interface().write(
            f'LTL={temp}'))
