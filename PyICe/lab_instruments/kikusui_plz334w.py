from PyICe.lab_core import *
from .kikusui_plz import kikusui_plz

class kikusui_plz334w(kikusui_plz):
    '''single channel kikusui_plz334w electronic load'''
    def __init__(self,interface_visa):
        self.kikusui_plz_name = 'kikusui_plz334w'
        self.kikusui_low_threshold = 0.66
        self.kikusui_high_threshold = 6.66
        kikusui_plz.__init__(self,interface_visa)
