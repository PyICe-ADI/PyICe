from ..lab_core import *

class fluke_45(scpi_instrument):
    '''single channel fluke_45 meter
        defaults to dc voltage, note this instrument currently does not support using multiple measurement types at the same time'''
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'fluke_45'
        scpi_instrument.__init__(self,f"f25 @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.config_dc_voltage()
    def config_dc_voltage(self, range="AUTO", rate="S"):
        '''Configure meter for DC voltage measurement.
        Optionally set range and rate'''
        self._config("VDC ", range, rate)
    def config_dc_current(self, range="AUTO", rate="S"):
        '''Configure meter for DC current measurement.
        Optionally set range and rate'''
        self._config("ADC ", range, rate)
    def config_ac_voltage(self, range="AUTO", rate="S"):
        '''Configure meter for AC voltage measurement.
        Optionally set range and rate'''
        self._config("VAC ", range, rate)
    def config_ac_current(self, range="AUTO", rate="S"):
        '''Configure meter for AC current measurement.
        Optionally set range and rate'''
        self._config("AAC ", range, rate)
    def add_channel(self,channel_name):
        '''Add named channel to instrument without configuring measurement type.'''
        meter_channel = channel(channel_name,read_function=self.read_meter)
        return self._add_channel(meter_channel)
    def read_meter(self):
        '''Return float representing meter measurement. Units are V,A,Ohm, etc depending on meter configuration.'''
        return float(self.get_interface().ask("MEAS1?"))
    def _config(self, command_string, range, rate):
        RANGE_SETTINGS = ["AUTO", 1, 2, 3, 4, 5, 6, 7]
        RATE_SETTINGS = ["S", "M", "F"]
        if range not in RANGE_SETTINGS:
            raise Exception("Error: Not a valid range setting, valid settings are:" + str(RANGE_SETTINGS))
        if rate not in RATE_SETTINGS:
            raise Exception("Error: Not a valid rate setting, valid settings are:" + str(RATE_SETTINGS))
        self.get_interface().write((command_string))
        self.get_interface().write(("AUTO " if range == "AUTO" else "RANGE " + str(range)))
        self.get_interface().write(("RATE " + str(rate)))
