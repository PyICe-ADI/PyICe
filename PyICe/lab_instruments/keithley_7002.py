from ..lab_core import *

class keithley_7002(scpi_instrument):
    '''KEITHLEY 7002 SWITCH SYSTEM
        Superclass for the 7011S Quad 10 to 1 multiplexers
        Additional Cards possible in future
        note - this setup does not change channel types unless a config_ is called
    '''
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'keithley_7002'
        scpi_instrument.__init__(self, self._base_name)
        self.add_interface_visa(interface_visa,timeout=10)
        # why was this commented then not commited?
        # scpi_instrument.__init__(self,f"7002_mux @: {self.get_interface()}")
        self.get_interface().write(("*rst"))
    def add_channel_relay(self,channel_name,bay,number):
        '''Add named channel at bay and num
            bay valid range [1-10]
            number valid range [1-40] for 7011S Quad 10 to 1 multiplexer card
        '''
        relay_channel = channel(channel_name,write_function=lambda closed: self._set_relay(bay, number, closed) )
        return self._add_channel(relay_channel)
    def _close_relay(self,bay,number):
        '''close named channel relay'''
        self.get_interface().write((f"CLOSE (@{bay}!{number})" ))
    def _open_relay(self,bay,number):
        '''open named channel relay'''
        self.get_interface().write((f"OPEN (@{bay}!{number})" ))
    def _set_relay(self,bay,number,state):
        if state:
            self._close_relay(bay,number)
        else:
            self._open_relay(bay,number)
    def open_all(self,sync_channels=False):
        '''open all relays, set sync_channels to true to keep the channels synced (no need to do this if shutting down)'''
        if sync_channels:
            for relay_channel in self.get_all_channels_list():
                relay_channel.write(False)
        else:
            self.get_interface().write(("OPEN ALL"))
