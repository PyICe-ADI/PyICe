"""Kikusui plz664wa instrument driver.

>>> from PyICe.lab_instruments.kikusui_plz664wa import kikusui_plz664wa

"""
from .kikusui_plz import kikusui_plz


class kikusui_plz664wa(kikusui_plz):
    """Single channel kikusui_plz664wa electronic load."""

    def __init__(self, interface_visa):
        """Initialize kikusui_plz664wa.
        Stores configuration in ``kikusui_high_threshold``,
        ``kikusui_low_threshold``, ``kikusui_plz_name`` for use by other
        methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.

        Args:
            interface_visa: VISA interface instance.
        """
        self.kikusui_plz_name = 'kikusui_plz664w'
        self.kikusui_low_threshold = 1.32
        self.kikusui_high_threshold = 13.2
        kikusui_plz.__init__(self, interface_visa)
