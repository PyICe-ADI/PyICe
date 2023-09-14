from PyICe.lab_core import *
from .kikusui_pbz import kikusui_pbz

class kikusui_pbz20_20(kikusui_pbz):
    '''Kikusui single channel 20V/20A bipolar power supply.'''
    def __init__(self,interface_visa):
        self._base_name = 'kikusui_pbz20_20'
        scpi_instrument.__init__(self,f"kikusui_pbz20-20 @ {interface_visa}")
        kikusui_pbz.__init__(self,interface_visa)
