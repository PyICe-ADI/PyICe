from ..lab_core import *
from .temperature_chamber import temperature_chamber

class sun_ecxx(temperature_chamber):
    '''sun ecXx oven instrument base class
        implements all methods common to sun ec0x and ec1x ovens'''
    def __init__(self,interface_visa):
        temperature_chamber.__init__(self)
        self.add_interface_visa(interface_visa)
    def _read_temperature_sense(self):
        '''read back actual chamber temperature'''
        return float(self.get_interface().ask("TEMP?"))
