from PyICe.lab_core import *
from .kikusui_plz import kikusui_plz

class kikusui_plz664wa(kikusui_plz):
    '''single channel kikusui_plz664wa electronic load'''
    def __init__(self,interface_visa):
        self.kikusui_plz_name = 'kikusui_plz664w'
        self.kikusui_low_threshold = 1.32
        self.kikusui_high_threshold = 13.2
        kikusui_plz.__init__(self,interface_visa)
