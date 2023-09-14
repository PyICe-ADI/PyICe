from ..lab_core import *

import math
import numpy as np
import nifgen
import sys
import time

class ni_pxi5413(scpi_instrument,delegator):
    '''NI PXI5413 16bit 20MHz AWG'''

    def __init__(self, interface_visa, force_trigger=True):
        '''interface_visa e.g. PXI1SLOT2"'''
        self._base_name = 'NI_PXI5413'
        delegator.__init__(self)
        scpi_instrument.__init__(self,f"NI_PXI5413 @ {interface_visa}")
        self.add_interface_visa(interface_visa,timeout=10)
        self.force_trigger = force_trigger
    
    #TODO - need to modify methods into PyICe fashion
    
    def create_trapzoid_signal(SampleN, width, slope, VOH, VOL, period):
        # function to generate custom pulse
        t = np.linspace(0, period, SampleN)
        amp = VOH - VOL
        offset = VOL
        a = slope*width*signal.sawtooth(2*math.pi*t/width, width=0.5)/4.
        a += slope*width/4.
        # clamp the top of the waveform
        a[a>amp] = amp
        # slice the pt
        idx_endpt = math.ceil(width/period*len(t))
        a[idx_endpt:]=0
        waveform_data = a + offset
        return waveform_data

    def main_method(resource_name, options, samples, gain, offset, gen_time):
        waveform_data = create_waveform_data(samples)
        # gen_time = period
        with nifgen.Session(resource_name=resource_name, options=options) as session:
            session.output_mode = nifgen.OutputMode.ARB
            waveform = session.create_waveform(waveform_data_array=waveform_data)
            session.configure_arb_waveform(waveform_handle=waveform, gain=gain, offset=offset)
            with session.initiate():
                time.sleep(gen_time)
