from ..lab_core import *
from .sorensen_generic_supply import *

class sorensen_dlm_60_10(sorensen_generic_supply):
    '''single channel sorensen_dlm_60_10'''
    def __init__(self,interface_visa):
        self.sorensen_name = "sorensen_dlm_60_10"
        interface_visa.terminationCharacter = "\r"  # for some reason the dlm_60_10 terminates with a carriage return and no new-line...
        interface_visa.write("*CLS")
        interface_visa.write("*RST")
        sorensen_generic_supply.__init__(self, interface_visa)
        self._base_name = 'sorensen_dlm_60_10'
        time.sleep(1.0) # have to wait a bit before doing any writes (such as writing ilim when adding a channel) or they seem to get thrown away...
    def _enable_output(self):
        '''DLM 60 10 can only be enabled/disabled by physical output enable button - so just pass here'''
        pass
    def _write_voltage(self,voltage):
        '''Set named channel to force voltage'''
        self.get_interface().write((f"SOURce:VOLTage {voltage}"))
    def _write_current(self,ilim):
        '''Set named channel's compliance current'''
        self.get_interface().write((f"SOURce:CURRent {ilim}"))
    def _read_vsense(self):
        '''Returns instrument's measured output voltage.'''
        return  float( self.get_interface().ask("MEASure:VOLTage?") )
    def _read_isense(self):
        '''Returns instrument's measured output current.'''
        return float( self.get_interface().ask("MEASure:CURRent?") )
