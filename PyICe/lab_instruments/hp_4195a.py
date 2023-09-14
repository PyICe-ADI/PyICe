from ..lab_core import *

class hp_4195a(scpi_instrument):
    '''HP4195A Network Analyzer
        Current Driver Only Collects Data; no configuration or measurement trigger'''
    def __init__(self, interface_visa):
        '''interface_visa'''
        self._base_name = 'hp_4195a'
        scpi_instrument.__init__(self,f"h4195a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
    def add_channel(self,channel_name,register):
        '''register must be
            X - frequency
            A - A register
            B - B register
            C - C register
            D - D register'''
        register = register.upper()
        if register.upper() not in ['X','A','B','C','D']:
            raise Exception(f'Bad register {register} for 4195a')
        new_channel = channel(channel_name,read_function = lambda: self._read_4195a_register(register))
        return self._add_channel(new_channel)
    def _read_4195a_register(self,register):
        '''read from one of the five hardware registers associated with this channel_name.  Return list of scalars representing points.'''
        data = self.get_interface().ask(('{register}?'))
        return list(map(float, data.split(',')))
    def config_network(self, start = 0.1, stop = 500e6, RBW = 'AUTO', NOP = 401, OSCA = -50):
        '''Configure the 4195 for network analysis  with start, stop, sweep type and resolution'''
        self.get_interface().write(("RST"))
        self.get_interface().write((f"OSC1={OSCA}"))
        self.get_interface().write(("FNC1")) #set Network
        self.get_interface().write((f"START={start}")) #start freq
        self.get_interface().write((f"STOP={stop}")) #stop freq
        if RBW == 'AUTO':
            self.get_interface().write(('CPL1'))
        else:
            self.get_interface().write((f"RBW={RBW}")) #resolution bandwidth
        self.get_interface().write((f"NOP={NOP}")) #number of points in sweet
        self.get_interface().write(("SWT2")) #log sweep
        self.get_interface().write(("SWM2")) #single trigger mode
    def config_spectrum(self, start = 0.1, stop = 500e6, RBW = 'AUTO', NOP = 401):
        '''Configure the 4195 for spectrum analysis (noise here) with start, stop, sweep type and resolution'''
        self.get_interface().write(("RST"))
        self.get_interface().write(("FNC2")) #set Spectrum
        self.get_interface().write((f"START={start}")) #start freq
        self.get_interface().write((f"STOP={stop}")) #stop freq
        if RBW == 'AUTO':
            self.get_interface().write(('CPL1'))
        else:
            self.get_interface().write((f"RBW={RBW}")) #resolution bandwidth
        self.get_interface().write((f"NOP={NOP}")) #number of points in sweet
        self.get_interface().write(("SWT2")) #log sweep
        self.get_interface().write(("SAP6")) #uv/rthz
        self.get_interface().write(("SWM2")) #singletrigger mode
    def trigger(self):
        '''Return the sweep time and trigger once'''
        ttime=self.get_interface().ask(('ST?'))
        self.get_interface().write(('SWTRG'))
        return ttime
