from ..lab_core import *
from .temperature_chamber import temperature_chamber

class delta_9039(temperature_chamber):
    '''single channel delta 9039 oven
        use wait_settle to wait for the soak to complete
        defaults to window = 1, soak=90
        extra data
           _sense - the sensed temperature
           _window - the temperature window
           _time - the total settling time (including soak)
           _soak - the programmed soak time'''
    def __init__(self,interface_visa):
        self._base_name = 'delta_9039'
        temperature_chamber.__init__(self)
        self.add_interface_visa(interface_visa)
        self._enable(False)
        time.sleep(1)
    def _write_temperature(self,value):
        '''Set named channel to new temperature "value"'''
        self.setpoint = value
        self._enable(False)
        time.sleep(1)
        self.get_interface().write("SEtpoint " + str(self.setpoint))
        time.sleep(1)
        self._enable(True)
        self.time = 0
        self._wait_settle()
    def _read_temperature_sense(self):
        '''read back actual chamber temperature'''
        return float(self.get_interface().ask("Temperature?"))
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling'''
        if enable:
            self.get_interface().write("Active")
        else:
            self.get_interface().write("STANdby")
