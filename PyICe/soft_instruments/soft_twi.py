from ..data_utils.pattern_generators import TWI
from ..lab_core import *

class Soft_TWI(instrument):
    '''Creates the channels needed to manipulate the timing parameters of an instrument capable of measuring a TWI port.'''

    def __init__(self, time_step):
        instrument.__init__(self, "Soft TWI Instrument")
        self._base_name = 'Soft TWI instrument'
        self.twi_pattern = TWI(time_step)

    def add_channel_time_step(self, channel_name):
        '''This channel tells the pattern generator what the time resolution of the underlying physical instrument is so it can allocate so many time slots to a parameter (such as clock high time, etc.).'''
        def _write_value(value):
            self.twi_pattern.time_step = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tbuf(self, channel_name):
        '''Controls the bus free time between STOPs and STARTs.'''
        def _write_value(value):
            self.twi_pattern.tbuf = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_thd_sta(self, channel_name):
        '''Controls the time between a START and when SCL may transition low.'''
        def _write_value(value):
            self.twi_pattern.thd_sta = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tlow(self, channel_name):
        '''Controls the low clock pulse width.'''
        def _write_value(value):
            self.twi_pattern.tlow = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_thd_dat(self, channel_name):
        '''Controls the hold time of the data after SCL goes low. This is allowed to go to 0 and part should respect a small negative setup time to be compliant.'''
        def _write_value(value):
            self.twi_pattern.thd_dat = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)

    def add_channel_thigh(self, channel_name):
        '''Controls the high clock pulse width. Data will generally be setup before this rises and held after it falls (notwithstanding testing for violations).'''
        def _write_value(value):
            self.twi_pattern.thigh = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tsu_dat(self, channel_name):
        '''Controls the setup time of the data before SCL goes high.'''
        def _write_value(value):
            self.twi_pattern.tsu_dat = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tsu_sta(self, channel_name):
        '''Controls the time SCL must high go before a ReStart.'''
        def _write_value(value):
            self.twi_pattern.tsu_sta = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tsu_sto(self, channel_name):
        '''Controls the time SCL must high go before a STOP.'''
        def _write_value(value):
            self.twi_pattern.tsu_sto = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)
        
    def add_channel_tsp(self, channel_name):
        '''Controls the spike width, high for d=0 and low for d=1. The port must be tolerant of (ignore) spikes on either data value such as 50ns.'''
        def _write_value(value):
            self.twi_pattern.tsp = value
        new_channel = channel(channel_name, write_function=_write_value)
        return self._add_channel(new_channel)