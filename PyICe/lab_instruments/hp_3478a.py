from PyICe.lab_core import *

class hp_3478a(instrument):
    '''single channel hp_3478a meter
        defaults to dc voltage'''
    def __init__(self,interface_visa):
        self._base_name = 'hp_3478a'
        instrument.__init__(self,"hp_3478a @ " + str(interface_visa))
        self.add_interface_visa(interface_visa)
        self.config_dc_voltage()
    def config_dc_voltage(self):
        '''Configure meter for DC voltage measurement'''
        self.get_interface().write(("F1"))
    def config_dc_current(self):
        '''Configure meter for DC current measurement'''
        self.get_interface().write(("F5"))
    def config_ac_voltage(self):
        '''Configure meter for AC voltage measurement'''
        self.get_interface().write(("F2"))
    def config_ac_current(self):
        '''Configure meter for AC current measurement'''
        self.get_interface().write(("F6"))
    def add_channel(self,channel_name):
        '''Add named channel to instrument without configuring measurement type.'''
        meter_channel = channel(channel_name,read_function=self._read_meter)
        return self._add_channel(meter_channel)
    def _read_meter(self):
        '''Return float representing meter measurement.  Units are V,A,Ohm, etc depending on meter configuration.'''
        return float(self.get_interface().read())
