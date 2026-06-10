"""Sun ec0x instrument driver.

>>> from PyICe.lab_instruments.sun_ec0x import sun_ec0x

"""
from ..lab_core import *  # noqa: F403
from .sun_ecxx import sun_ecxx


class sun_ec0x(sun_ecxx):
    """Sun ec0 oven.

    use wait_settle to wait for the soak to complete
    defaults to window = 1, soak=90
    extra data
    _sense - the sensed temperature
    _window - the temperature window
    _time - the total settling time (including soak)
    _soak - the programmed soak time
    """
    def __init__(self, interface_visa):
        """Initialize sun_ec0x.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        # instrument.__init__(self,f"sun_ec0x @ {interface_visa}")
        self._base_name = 'sun_ec0x'
        sun_ecxx.__init__(self, interface_visa)

    def _write_temperature(self, value):
        """Set named channel to new temperature "value".
        Internal implementation detail; see the public API for usage.

        Internal implementation detail; see the public API for usage.

        Args:
            value: Value to set.
        """
        # self._standby()
        self.setpoint = value
        time.sleep(1)
        self.get_interface().write(str(value) + "C")
        time.sleep(1)
        # self._active()
        self.time = 0
        self._wait_settle()

    def _enable(self, enable):
        """Enable/disable temperature chamber heating and cooling.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.
        """
        if enable:
            self.get_interface().write("ON")
        else:
            self.get_interface().write("OFF")
