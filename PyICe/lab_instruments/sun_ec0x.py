from ..lab_core import *
from .sun_ecxx import sun_ecxx

class sun_ec0x(sun_ecxx):
    '''sun ec0 oven
        use wait_settle to wait for the soak to complete
        defaults to window = 1, soak=90
        extra data
           _sense - the sensed temperature
           _window - the temperature window
           _time - the total settling time (including soak)
           _soak - the programmed soak time'''
    def __init__(self,interface_visa):
        #instrument.__init__(self,f"sun_ec0x @ {interface_visa}")
        self._base_name = 'sun_ec0x'
        sun_ecxx.__init__(self,interface_visa)
    def _write_temperature(self,value):
        '''Set named channel to new temperature "value"'''
        #self._standby()
        self.setpoint = value
        time.sleep(1)
        self.get_interface().write(str(value)+"C")
        time.sleep(1)
        #self._active()
        self.time = 0
        self._wait_settle()
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling'''
        if enable:
            self.get_interface().write("ON")
        else:
            self.get_interface().write("OFF")
