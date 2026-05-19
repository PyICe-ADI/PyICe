"""Kikusui pwr800l instrument driver."""
from .kikusui_pwr import kikusui_pwr


class kikusui_pwr800l(kikusui_pwr):
    """Single channel kikusui PWR800l electronic load."""

    def __init__(self, addr, node, ch):
        self.kikusui_pwr_name = "kikusui_pwr800l"
        kikusui_pwr.__init__(self, addr, node, ch)
        self._base_name = 'kikusui_pwr800l'
