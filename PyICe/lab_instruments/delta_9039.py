"""Delta 9039 instrument driver.

>>> from PyICe.lab_instruments.delta_9039 import delta_9039

"""
from ..lab_core import *  # noqa: F403
from .temperature_chamber import temperature_chamber


class delta_9039(temperature_chamber):
    """Single channel delta 9039 oven.

    use wait_settle to wait for the soak to complete
    defaults to window = 1, soak=90
    extra data
    _sense - the sensed temperature
    _window - the temperature window
    _time - the total settling time (including soak)
    _soak - the programmed soak time
    """
    def __init__(self, interface_visa):
        """Initialize delta_9039.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'delta_9039'
        temperature_chamber.__init__(self)
        self.add_interface_visa(interface_visa)
        self._enable(False)
        time.sleep(1)

    def _write_temperature(self, value):
        """Set named channel to new temperature "value".
        Internal implementation detail; see the public API for usage.

        Internal implementation detail; see the public API for usage.

        Args:
            value: Value to set.
        """
        self.setpoint = value
        self._enable(False)
        time.sleep(1)
        self.get_interface().write("SEtpoint " + str(self.setpoint))
        time.sleep(1)
        self._enable(True)
        self.time = 0
        self._wait_settle()

    def _read_temperature_sense(self):
        """Read back actual chamber temperature.
        Internal helper that computes and returns a derived value.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("Temperature?"))

    def _enable(self, enable):
        """Enable/disable temperature chamber heating and cooling.

        Internal implementation detail; see the public API for usage.

        Args:
            enable: Enable or disable.
        """
        if enable:
            self.get_interface().write("Active")
        else:
            self.get_interface().write("STANdby")
