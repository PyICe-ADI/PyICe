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
        
class lfsr_period_generator():
    ''' ┌────┬────┬────┬────┬────┬────┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐
        │ 15 │ 14 │ 13 │ 12 │ 11 │ 10 │ 9 │ 8 │ 7 │ 6 │ 5 │ 4 │ 3 │ 2 │ 1 │ 0 │<──┐
        └──┬─┴──┬─┴────┴──┬─┴────┴────┴───┴───┴───┴───┴───┴───┴─┬─┴───┴───┴───┘   │
           │    │         │                                     │               ┌─O─┐XNOR
           │    │         │                                     └──────────────>│   │
           │    │         └────────────────────────────────────────────────────>│(+)│
           │    └──────────────────────────────────────────────────────────────>│   │
           └───────────────────────────────────────────────────────────────────>└───┘
    '''
    # https://en.wikipedia.org/wiki/Linear-feedback_shift_register
    # taps: 16 15 13 4; feedback polynomial: x^16 + x^15 + x^13 + x^4 + 1
    def __init__(self, nbits, freq_center, freq_range_percent):
        self.nbits = nbits
        self.poly = [value-1 for value in [16,15,13,4]] # Subtract one from each to start register at 0 (vs Wikipedia starting at 1)
        self.lfsr = 0 # Seed value
        self.max_freq = freq_center * (1 + freq_range_percent)
        self.min_freq = freq_center * (1 - freq_range_percent)
    def get_next_period(self):
        bit =   self.lfsr >> self.poly[0] & 1 ^ \
                self.lfsr >> self.poly[1] & 1 ^ \
                self.lfsr >> self.poly[2] & 1 ^ \
                self.lfsr >> self.poly[3] & 1
        bit = 1 if not bit else 0 # Invert for XNOR, allows all 0's on reset
        self.lfsr = (self.lfsr << 1) & 0xFFFF | bit
        code = self.lfsr & (2**self.nbits-1) # Just grab nbits
        freq = self.min_freq + (self.max_freq - self.min_freq) * code / 2**self.nbits
        return 1/freq