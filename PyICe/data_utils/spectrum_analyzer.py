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
        time, value = zip(*signal)    
        npoints = len(value)
        self.yf = self.dBV(2.0 / npoints * numpy.abs((fft(value))[0:npoints//2]))
        self.xf = fftfreq(npoints, time[1]-time[0])[:npoints//2] # Reconstruct time step, *** THEY ALL NEED TO BE THE SAME ***
        return self.xf, self.yf
    def get_RBW(self):
        return self.xf[1]-self.xf[0]