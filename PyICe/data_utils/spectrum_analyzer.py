from scipy.fft import fft, fftfreq
from PyICe.data_utils.units_conversions import dBV
import numpy

class spectrum_analyzer():
    def __init__(self):
        '''This class uses the scipy FFT to emulate a spectrum analyzer.
           The main value of using this wrapper class is that it deals with the positive and negative frequency issue and computes the magnitude of the response directly.
           This absolves the user of having to work that out each time they need a specral analysis using the FFT making this "feel" more like a lab instrument.'''
    def compute_fft(self, signal):
        '''The argument "signal" should be a zipped list of (time,value) pairs upon which to compute the FFT.
           Requiring pre-zipping of the time,voltage series ensures that the user understands that there must be an equal number of each.
           A scale factor of 1/√2 was added because spectrum analyzers always reports in RMS but an FFT returns sine amplitude "A" as in A•sin(ωt).'''
        self.times, self.values = zip(*signal)
        self.npoints = len(self.values)
        self.yf = dBV(2.0 / self.npoints / 2**-0.5 * numpy.abs((fft(self.values))[0:self.npoints//2]))
        self.xf = fftfreq(self.npoints, self.times[1]-self.times[0])[:self.npoints//2] # Reconstruct time step, *** ALL TIME STEPS NEED TO BE THE SAME ***
        return self.xf, self.yf
    def get_RBW(self):
        '''Returns the effective Resolution Bandwidth which is the step between frequenices of the computed spectral record.
           This should also be equal to 1/(Tmax-Tmin) or the reciprocal of the time series duration.'''
        return self.xf[1]-self.xf[0]
    def get_record_duration(self):
        '''Returns the duration of the time series (Tmax-Tmin).
           This should be the reciprocal of the Resolution Bandwidth.'''
        return self.times[-1]-self.times[0]
    def get_record_length(self):
        '''Returns the number of points in the incoming record.
           The number of frequency points in the computed outgoing spectrum should be the same.'''
        return self.npoints