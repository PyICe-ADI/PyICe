from ..lab_core import *
from abc import ABCMeta, abstractmethod
        
class temperature_chamber(instrument, metaclass=ABCMeta):
    '''generic temperature chamber parent class to handle common tasks, like setting the soak time'''
    def __init__(self):
        instrument.__init__(self,self._base_name)
        self.setpoint = None
        self.soak = 450
        self.settle_time_limit = None
        self.window = 2.5
        self.time = 0
        self.set_blocking_mode(True)
    def add_channels(self,channel_name):
        '''Add most commonly used channels.
        channel_name represents temperature setpoint.
        Also adds _sense, _soak, _window, and _soak_settling_time channels.'''
        temp_ch = self.add_channel_temp(channel_name)
        self.add_channel_sense(channel_name + "_sense")
        self.add_channel_soak(channel_name + "_soak")
        self.add_channel_window(channel_name + "_window")
        self.add_channel_soak_settling_time(channel_name + "_soak_settling_time")
        self.add_channel_settle_time_limit(channel_name + "_settle_time_limit")
        self.add_channel_blocking(channel_name + "_blocking")
        self.add_channel_enable(channel_name + "_enable")
        return temp_ch
    def add_channel(self,channel_name):
        '''Adds just the main temperature setting setpoint channel.'''
        return self.add_channel_temp(channel_name)
    def add_channel_temp(self,channel_name):
        '''Channel_name represents PID loop forcing temperature setpoint.'''
        new_channel = channel(channel_name,write_function=self._write_temperature)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_temp.__doc__)
        new_channel.set_attribute('instrument', self)
        return self._add_channel(new_channel)
    def add_channel_sense(self,channel_name):
        '''channel_name represents primary PID control loop thermocouple readback.'''
        new_channel = channel(channel_name,read_function=self._read_temperature_sense)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_sense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_soak(self,channel_name):
        '''channel_name represents soak time setpoint in seconds. Soak timer runs while temperature is continuously within 'window' and resets to zero otherwise.'''
        new_channel = channel(channel_name,write_function=self._set_soak)
        new_channel.write(self.soak)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_soak.__doc__)
        return self._add_channel(new_channel)
    def add_channel_window(self,channel_name):
        '''channel_name represents width setpoint of tolerance window to start soak timer. Setpoint is total window width in degrees (temp must be +/-window/2).'''
        new_channel = channel(channel_name,write_function=self._set_window)
        new_channel.write(self.window)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_window.__doc__)
        return self._add_channel(new_channel)
    def add_channel_soak_settling_time(self,channel_name):
        '''channel_name represents soak timer elapsed time readback.'''
        new_channel = channel(channel_name,read_function=lambda: self.time )
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_soak_settling_time.__doc__)
        return self._add_channel(new_channel)
    def add_channel_settle_time_limit(self, channel_name):
        '''channel_name represents max time to wait for oven to settle to within window before raising Exception.'''
        new_channel = channel(channel_name,write_function=self._set_settle_time_limit)
        new_channel.write(self.settle_time_limit)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_settle_time_limit.__doc__)
        return self._add_channel(new_channel)
    def add_channel_blocking(self,channel_name):
        '''allow Python to continue immediately for gui/interactive use without waiting for slew/settle'''
        new_channel = integer_channel(channel_name,size=1, write_function=self.set_blocking_mode)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_blocking.__doc__)
        new_channel.write(self._blocking)
        return self._add_channel(new_channel)
    def add_channel_enable(self,channel_name):
        '''channel name represents oven enable/disable setting.  Accepts boolean and True enables the oven.
        Heat and cool only settings also accepted if temperature chamber supports that.'''
        new_channel = integer_channel(channel_name,size=2,write_function=self._enable)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_enable.__doc__)
        new_channel.add_preset('True', True)
        new_channel.add_preset('False', False)
        new_channel.add_preset('Heat_only', 2)
        new_channel.add_preset('Cool_only', 3)
        return self._add_channel(new_channel)
    def set_blocking_mode(self,blocking):
        '''allow Python to continue immediately for gui/interactive use without waiting for slew/settle'''
        self._blocking = blocking
    def _set_window(self,value):
        '''Set allowed window to start soak timer.'''
        self.window = value
    def _set_settle_time_limit(self, seconds):
        '''set oven to standby and raise exception if oven does not settle within
            specified time'''
        self.settle_time_limit = seconds
    def _set_soak(self,value):
        '''Set soak time in seconds'''
        self.soak = value
    def _wait_settle(self):
        '''Block until temperature has been within window for soak time.
            Optionally abort, set oven to standby, and raise exception if oven temp fails to converge in specified time'''
        if not self._blocking:
            return
        settled = 0
        self.time = 0
        progress_chars = ['-', '\\', '|', '/']
        while(settled <= self.soak):
            time.sleep(1)  # 1 second delay
            temp_current = self._read_temperature_sense()
            #print f"\rSettling {settled}/{self.soak}s  Current Temp:{temp_current}°C  Target Temp:{self.setpoint}±{self.window/2.0}°C Total time this setting:{self.time}s {progress_chars[self.time%len(progress_chars)]}" #comma supresses newline
            sys.stdout.flush() #print doesn't make it to screen in a timely fashion without newline; windows OEM codepage doesn't support UNICODE
            print(f"\rSettling {settled}/{self.soak}s Current Temp:{temp_current:3.1f}C Target Temp:{self.setpoint:3.1f}+/-{self.window/2.0:3.1f}C Total time this setting:{self.time:3d}s {progress_chars[self.time%len(progress_chars)]}", end=' ') #comma supresses newline
            sys.stdout.flush() #print doesn't make it to screen in a timely fashion without newline
            window_upper = float(self.setpoint) + float(self.window)/2
            window_lower = float(self.setpoint) - float(self.window)/2
            if (float(temp_current) < window_upper) and (float(temp_current) > window_lower):
                settled += 1
            else:
                settled = 0
                if (self.settle_time_limit is not None and self.time > self.settle_time_limit):
                    self._enable(False)
                    print()
                    raise Exception(f'Oven failed to settle to {self.setpoint}C in {self.time} seconds. Final Temp: {temp_current}C.\n Oven Disabled. Test aborted.')
            self.time += 1
        print() #newline avoids overwriting oven status message with next print
    @abstractmethod
    def _write_temperature(self, value):
        '''Program tempertaure setpoint to value. Implement for specific hardware.'''
        self.setpoint = value
    @abstractmethod
    def _read_temperature_sense(self):
        '''read back actual chamber temperature.  Implement for specific hardware.'''
    @abstractmethod
    def _enable(self, enable):
        '''enable/disable temperature chamber heating and cooling. Also accepts heat/cool only arguments if chamber supports it.'''
    def shutdown(self, shutdown):
        '''separate method to turn off temperature chamber.
        overload if possible for individual hardware.
        otherwise, default to disable heating and cooling.
        '''
        self._enable(not shutdown)
