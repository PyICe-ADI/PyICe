"""Kikusui pwr800l instrument driver.

>>> from PyICe.lab_instruments.kikusui_pwr800l import kikusui_pwr800l

"""
from .kikusui_pwr import kikusui_pwr


class kikusui_pwr800l(kikusui_pwr):
    """Single channel kikusui PWR800l electronic load."""

    def __init__(self, addr, node, ch):
        """Initialize kikusui_pwr800l.
        Stores configuration in ``_base_name``, ``kikusui_pwr_name`` for use
        by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.

        Args:
            addr: Addr to use.
            ch: Channel number or channel object.
            node: Node to use.
        """
        self.kikusui_pwr_name = "kikusui_pwr800l"
        kikusui_pwr.__init__(self, addr, node, ch)
        self._base_name = 'kikusui_pwr800l'
