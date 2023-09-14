from PyICe.lab_core import *
from .kikusui_pbz import kikusui_pbz

class kikusui_pbz40_10(kikusui_pbz):
    '''Kikusui single channel 40V/10A bipolar power supply.'''
    def __init__(self,interface_visa):
        self._base_name = 'kikusui_pbz40_10'
        scpi_instrument.__init__(self,f"kikusui_pbz40_10 @ {interface_visa}")
        kikusui_pbz.__init__(self,interface_visa)
