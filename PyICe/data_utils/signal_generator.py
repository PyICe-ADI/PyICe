from PyICe.lab_utils.banners import print_banner
import numpy

class signal_generator():
    '''This tool can be used to generate sample wavefors that may be useful in signal analysis and waveform processing techniques.
       The goal is to generate zipped (time,value) tuples of N whole waveforms of the specified function (as of this writing, pulse and sine waves).
       The waveform period, sample rate and cycle count can be entered and simple state machines generate data until the desired cycle count is generated.
       
       The period_function can be used generate aperiodic waveforms such as spread spectrum or frequency modulated waveforms.
       For example, a spread spectrum function may be something like:
       
                period_function = lambda : random.uniform(PERIOD*(1-SPREAD_PERCENTAGE/2), PERIOD*(1+SPREAD_PERCENTAGE/2))
       '''
    def __init__(self, hi_value, lo_value, period, cyclecount, timestep, phase=0.10, period_function=None):
        self.period = period
        self.timestep = timestep
        self.hi_value = hi_value
        self.lo_value = lo_value
        self.cyclecount = cyclecount
        self.period_function = period_function
        self.phase = phase
        if not isinstance(cyclecount, int):
            print_banner("***WARNING***", f"Cycle count of {cyclecount} is not an integer.", "Taking an FFT will include significant skirt energy without windowing.")
    def pulse_wave(self, duty_cycle):
        '''Generates a pulsatile wafeform of arbitrary duty cycle, high and low amplitude values.'''
        times = []
        values = []
        time_now = 0
        cycles = 0
        while cycles < self.cyclecount:
            this_period = self.period if self.period_function is None else self.period_function()
            cycle_start_time = time_now
            cycle_end_time = cycle_start_time + this_period
            while time_now <= cycle_end_time and cycles < self.cyclecount:
                if time_now < cycle_start_time + duty_cycle * this_period:
                    values.append(self.hi_value)
                else:
                    values.append(self.lo_value)
                times.append(time_now)
                time_now += self.timestep
                cycles = time_now / this_period
        return zip(times, values)
    def sine_wave(self):
        '''Generates a sine wave. Frequency, sample rate, peak and trough values are prescribed by signal generator iniallizer.
           Phase is currently direspected.'''
        times = []
        values = []
        time_now = 0
        cycles = 0
        while cycles < self.cyclecount:
            this_period = self.period if self.period_function is None else self.period_function()
            cycle_start_time = time_now
            cycle_end_time = cycle_start_time + this_period
            while time_now <= cycle_end_time and cycles < self.cyclecount:
                values.append((self.hi_value+self.lo_value) / 2 + (self.hi_value-self.lo_value)*numpy.sin(2*numpy.pi/self.period*time_now))
                times.append(time_now)
                time_now += self.timestep
                cycles = time_now / this_period
        return zip(times, values)