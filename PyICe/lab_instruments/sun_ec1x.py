from ..lab_core import *
from .sun_ecxx import sun_ecxx

class sun_ec1x(sun_ecxx):
    '''sun ec1x oven
        use wait_settle to wait for the soak to complete
        defaults to window = 1, soak=90
        extra data
           _sense - the sensed temperature
           _window - the temperature window
           _time - the total settling time (including soak)
           _soak - the programmed soak time

        upper_temp_limit (default 165) and lower_temp_limit (default -65) can be modified as properties of the sun_ec1x object outside the PyICe channel framework'''
    def __init__(self,interface_visa):
        self._base_name = 'sun_ec1x'
        sun_ecxx.__init__(self,interface_visa)
        self.upper_temp_limit = 165
        self.lower_temp_limit = -65
        self.get_interface().write('SINT=NNNNNNNNNN0')
        time.sleep(1)
        slag = self.get_interface().resync()
        print(f"Flushed {len(slag)} characters: {slag}.")
        self.shutdown(False)
        self._enable(True)
    def add_channel_user_sense(self,channel_name):
        '''channel_name represents secondary non-control thermocouple readback.'''
        new_channel = channel(channel_name,read_function=lambda: float(self.get_interface().ask("UCHAN?")))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_user_sense.__doc__)
        return self._add_channel(new_channel)
    def _write_temperature(self,value):
        '''Set named channel to new temperature "value"'''
        self.setpoint = value
        time.sleep(1)
        self.get_interface().write(f"SET={value}")
        time.sleep(1)
        self.time = 0
        self._wait_settle()
    def _enable(self, enable):
        '''individually control heat/cool outputs. Usually used through channel framework'''
        if enable==False or enable==0:
            time.sleep(0.5)
            self.get_interface().write('HOFF')
            time.sleep(0.5)
            self.get_interface().write('COFF')
            time.sleep(0.5)
        elif enable==True or enable==1:
            time.sleep(0.5)
            self.get_interface().write('HON')
            time.sleep(0.5)
            self.get_interface().write('CON')
            time.sleep(0.5)
        elif enable==2:
            #heat only
            time.sleep(0.5)
            self.get_interface().write('HON')
            time.sleep(0.5)
            self.get_interface().write('COFF')
            time.sleep(0.5)
        elif enable==3:
            #cool only
            time.sleep(0.5)
            self.get_interface().write('HOFF')
            time.sleep(0.5)
            self.get_interface().write('CON')
            time.sleep(0.5)
        else:
            raise Exception(f'Unknown oven enable value: {enable}')
    def shutdown(self, shutdown):
        '''turn entire temp controller on or off. This is different than enabling/disabling the heat and cool outputs'''
        if shutdown:
            time.sleep(0.5)
            self.get_interface().write('OFF')
            time.sleep(0.5)
        else:
            time.sleep(0.5)
            self.get_interface().write('ON')
            time.sleep(0.5)
    upper_temp_limit = property(lambda self: float(self.get_interface().ask('UTL?')), lambda self,temp: self.get_interface().write(f'UTL={temp}'))
    lower_temp_limit = property(lambda self: float(self.get_interface().ask('LTL?')), lambda self,temp: self.get_interface().write(f'LTL={temp}'))

