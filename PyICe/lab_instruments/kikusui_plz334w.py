"""Kikusui plz334w instrument driver.

>>> from PyICe.lab_instruments.kikusui_plz334w import kikusui_plz334w

"""
from .kikusui_plz import kikusui_plz


class kikusui_plz334w(kikusui_plz):
    """Single channel kikusui_plz334w electronic load."""

    def __init__(self, interface_visa):
        """Initialize kikusui_plz334w.
        Stores configuration in ``kikusui_high_threshold``,
        ``kikusui_low_threshold``, ``kikusui_plz_name`` for use by other
        methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self.kikusui_plz_name = 'kikusui_plz334w'
        self.kikusui_low_threshold = 0.66
        self.kikusui_high_threshold = 6.66
        kikusui_plz.__init__(self, interface_visa)
