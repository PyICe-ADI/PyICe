from scipy.fft import fft, fftfreq
import numpy

class spectrum_analyzer():
    def __init__(self):
        '''This class uses the scipy FFT to emulate a spectrum analyzer.
           The main value of using this wrapper class is that it deals with the positive and negative frequency issue and computes the magnitude of the response directly.
           This absolves the user of having to work that out each time they need a specral analysis using the FFT making this "feel" more like a lab instrument.'''
    def dBV(self, values):
        return [20*numpy.log10(value) for value in values]
    def compute_fft(self, signal):
        self.times, self.values = zip(*signal)    
        self.npoints = len(self.values)
        self.yf = self.dBV(2.0 / self.npoints * numpy.abs((fft(self.values))[0:self.npoints//2]))
        self.xf = fftfreq(self.npoints, self.times[1]-self.times[0])[:self.npoints//2] # Reconstruct time step, *** THEY ALL NEED TO BE THE SAME ***
        return self.xf, self.yf
    def get_RBW(self):
        return self.xf[1]-self.xf[0]
    def get_record_duration(self):
        return self.times[-1]-self.times[0]
    def get_record_length(self):
        return self.npoints