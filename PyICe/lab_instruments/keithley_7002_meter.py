from ..lab_core import *
from .keithley_7002 import *
import time

class keithley_7002_meter(keithley_7002):
    '''Combines 7002 switch system and any multimeter instrument into a virtual super 34970.'''
    def __init__(self, interface_visa, multimeter_channel):
        '''interface_visa for the Keithley 7002 mux system
            multimeter_channel is channel object, lb.get_channel(channel_name) or some_meter.get_channel(channel_name) will return ones
            delay is the number of seconds between closing the channel relay and triggering the meter measurement.
        '''
        keithley_7002.__init__(self, interface_visa)
        self._base_name = 'keithley_7002_meter'
        self.multimeter_channel = multimeter_channel
        self.open_all() #just to be sure...
    def add_channel_meter(self,channel_name,bay,num,pre_calls=[],post_calls=[],multimeter_channel=None,delay=0):
        '''add named channel to instrument
            bay is the switch system plugin bay. Valid range [1-10]
            num valid range [1-40] for 7011S Quad 10 to 1 multiplexer card
            pre_calls is a list of functions taking exactly 0 arguments to call after closing channel relay but before triggering multimeter measurement
            post_calls is a list of functions taking exactly 0 arguments to call after triggering multimeter measurement but before opening channel relay
            multimeter_channel is a channel with the meter on it, if not specified the instrument meter is used
        '''
        meter_channel = channel(channel_name, read_function= lambda: self._read_meter(multimeter_channel,bay,num,pre_calls,post_calls,delay))
        return self._add_channel(meter_channel)
    def _read_meter(self, multimeter_channel, bay, num, pre_calls, post_calls,delay):
        '''close relay to named channel, run any pre_calls associated with channel,
            trigger measurement, run any post_calls associated with channel, and return the measurment result

            pre_ and post_calls can be used, for example, to set different ranges
            or integration powerline cycles for different channels using the same multimeter.
        '''
        self.open_all() #just to be sure...
        self._close_relay(bay,num)
        for func in pre_calls:
            func()
        time.sleep(delay)
        if multimeter_channel is not None:
            result = multimeter_channel.read()
        else:
            result = self.multimeter_channel.read()
        for func in post_calls:
            func()
        self._open_relay(bay,num)
        return result
