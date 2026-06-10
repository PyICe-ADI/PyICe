"""Sorensen dlm 60 10 instrument driver.

>>> from PyICe.lab_instruments.sorensen_dlm_60_10 import sorensen_dlm_60_10

"""
from ..lab_core import *  # noqa: F403
from .sorensen_generic_supply import *  # noqa: F403


class sorensen_dlm_60_10(sorensen_generic_supply):
    """Single channel sorensen_dlm_60_10."""

    def __init__(self, interface_visa):
        """Initialize sorensen_dlm_60_10.
        Stores configuration in ``_base_name``, ``sorensen_name`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self.sorensen_name = "sorensen_dlm_60_10"
        # for some reason the dlm_60_10 terminates with a carriage return and
        # no new-line...
        interface_visa.terminationCharacter = "\r"
        interface_visa.write("*CLS")
        interface_visa.write("*RST")
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_dlm_60_10'
        # have to wait a bit before doing any writes (such as writing ilim when
        # adding a channel) or they seem to get thrown away...
        time.sleep(1.0)

    def _enable_output(self):
        """DLM 60 10 can only be enabled/disabled by physical output enable button - so just pass here.

        Internal implementation detail; see the public API for usage.
        """

    def _write_voltage(self, voltage):
        """Set named channel to force voltage.
        Internal helper that sends the ``SOURce:VOLTage`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            voltage: Voltage value.
        """
        self.get_interface().write((f"SOURce:VOLTage {voltage}"))

    def _write_current(self, ilim):
        """Set named channel's compliance current.
        Internal helper that sends the ``SOURce:CURRent`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Args:
            ilim: Current limit.
        """
        self.get_interface().write((f"SOURce:CURRent {ilim}"))

    def _read_vsense(self):
        """Returns instrument's measured output voltage.
        Internal helper that sends the ``MEASure:VOLTage`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("MEASure:VOLTage?"))

    def _read_isense(self):
        """Returns instrument's measured output current.
        Internal helper that sends the ``MEASure:CURRent`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        Returns:
            The measured value.
        """
        return float(self.get_interface().ask("MEASure:CURRent?"))
