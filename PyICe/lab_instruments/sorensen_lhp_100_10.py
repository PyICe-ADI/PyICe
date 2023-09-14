from ..lab_core import *
from .sorensen_generic_supply import *

class sorensen_lhp_100_10(sorensen_generic_supply):
    '''single channel sorensen_lhp_100_10'''
    def __init__(self,interface_visa):
        self.sorensen_name = "sorensen_lhp_100_10"
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_lhp_100_10'
