"""Kikusui pbz40 10 instrument driver.

>>> from PyICe.lab_instruments.kikusui_pbz40_10 import kikusui_pbz40_10

"""
from PyICe.lab_core import *  # noqa: F403
from .kikusui_pbz import kikusui_pbz


class kikusui_pbz40_10(kikusui_pbz):
    """Kikusui single channel 40V/10A bipolar power supply."""

    def __init__(self, interface_visa):
        """Initialize kikusui_pbz40_10.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'kikusui_pbz40_10'
        scpi_instrument.__init__(self, f"kikusui_pbz40_10 @ {interface_visa}")
        kikusui_pbz.__init__(self, interface_visa)
