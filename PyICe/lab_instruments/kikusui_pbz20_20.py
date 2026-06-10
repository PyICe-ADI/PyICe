"""Kikusui pbz20 20 instrument driver.

>>> from PyICe.lab_instruments.kikusui_pbz20_20 import kikusui_pbz20_20

"""
from PyICe.lab_core import *  # noqa: F403
from .kikusui_pbz import kikusui_pbz


class kikusui_pbz20_20(kikusui_pbz):
    """Kikusui single channel 20V/20A bipolar power supply."""

    def __init__(self, interface_visa):
        """Initialize kikusui_pbz20_20.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = 'kikusui_pbz20_20'
        scpi_instrument.__init__(self, f"kikusui_pbz20-20 @ {interface_visa}")
        kikusui_pbz.__init__(self, interface_visa)
