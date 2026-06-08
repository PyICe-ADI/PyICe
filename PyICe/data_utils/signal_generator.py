"""Signal generator utilities.

>>> from PyICe.data_utils.signal_generator import signal_generator

"""
from PyICe.lab_utils.banners import print_banner
import numpy


class signal_generator():
    """This tool can be used to generate sample wavefors that may be useful in signal analysis and waveform processing techniques.

    The goal is to generate zipped (time,value) tuples of N whole waveforms of the specified function (as of this writing, pulse and sine waves).
    The waveform period, sample rate and cycle count can be entered and simple state machines generate data until the desired cycle count is generated.

    The period_function can be used generate aperiodic waveforms such as spread spectrum or frequency modulated waveforms.
    For example, a spread spectrum function may be something like:

    period_function = lambda : random.uniform(PERIOD*(1-SPREAD_PERCENTAGE/2), PERIOD*(1+SPREAD_PERCENTAGE/2))

    >>> from PyICe.data_utils.signal_generator import signal_generator
    >>> signal_generator is not None
    True

    """
    def __init__(self, hi_value, lo_value, period, cyclecount,
                 timestep, phase=0.10, period_function=None):
        """Initialize signal_generator.
        Initializes 7 instance attributes that configure the object's
        behavior.

        Initializes 7 instance attributes that configure the object's behavior.


        >>> from PyICe.data_utils.signal_generator import signal_generator
        >>> hasattr(signal_generator, '__init__')
        True

        Args:
            cyclecount: Cyclecount to use.
            hi_value: Hi value to use.
            lo_value: Lo value to use.
            period: Signal period.
            period_function: Period function to use.
            phase: Signal phase in degrees.
            timestep: Timestep to use.
        """
        self.period = period
        self.timestep = timestep
        self.hi_value = hi_value
        self.lo_value = lo_value
        self.cyclecount = cyclecount
        self.period_function = period_function
        self.phase = phase
        if not isinstance(cyclecount, int):
            print_banner(
                "***WARNING***",
                f"Cycle count of {cyclecount} is not an integer.",
                "Taking an FFT will include significant skirt energy without windowing.")

    def pulse_wave(self, duty_cycle):
        """Generates a pulsatile wafeform of arbitrary duty cycle, high and low amplitude values.

        Supports the ``signal_generator`` workflow by performing the described operation.


        >>> from PyICe.data_utils.signal_generator import signal_generator
        >>> hasattr(signal_generator, 'pulse_wave')
        True

        Args:
            duty_cycle: Duty cycle to use.

        Returns:
            Array of pulse waveform samples.
        """
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
        """Generates a sine wave. Frequency, sample rate, peak and trough values are prescribed by signal generator initializer.

        Phase is currently direspected.


        >>> from PyICe.data_utils.signal_generator import signal_generator
        >>> hasattr(signal_generator, 'sine_wave')
        True

        Returns:
            Array of sinusoidal waveform samples.
        """
        times = []
        values = []
        time_now = 0
        cycles = 0
        while cycles < self.cyclecount:
            this_period = self.period if self.period_function is None else self.period_function()
            cycle_start_time = time_now
            cycle_end_time = cycle_start_time + this_period
            while time_now <= cycle_end_time and cycles < self.cyclecount:
                values.append((self.hi_value +
                               self.lo_value) /
                              2 +
                              (self.hi_value -
                               self.lo_value) *
                              numpy.sin(2 *
                              numpy.pi /
                              self.period *
                              time_now))
                times.append(time_now)
                time_now += self.timestep
                cycles = time_now / this_period
        return zip(times, values)


class lfsr_period_generator():
    """┌────┬────┬────┬────┬────┬────┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┐.

    │ 15 │ 14 │ 13 │ 12 │ 11 │ 10 │ 9 │ 8 │ 7 │ 6 │ 5 │ 4 │ 3 │ 2 │ 1 │ 0 │<──┐
    └──┬─┴──┬─┴────┴──┬─┴────┴────┴───┴───┴───┴───┴───┴───┴─┬─┴───┴───┴───┘   │
    │    │         │                                     │               ┌─O─┐XNOR
    │    │         │                                     └──────────────>│   │
    │    │         └────────────────────────────────────────────────────>│(+)│
    │    └──────────────────────────────────────────────────────────────>│   │
    └───────────────────────────────────────────────────────────────────>└───┘

    >>> from PyICe.data_utils.signal_generator import lfsr_period_generator
    >>> lfsr_period_generator is not None
    True

    """
    # https://en.wikipedia.org/wiki/Linear-feedback_shift_register
    # taps: 16 15 13 4; feedback polynomial: x^16 + x^15 + x^13 + x^4 + 1

    def __init__(self, nbits, freq_center, freq_range_percent):
        """Initialize lfsr_period_generator.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.data_utils.signal_generator import lfsr_period_generator
        >>> lfsr_period_generator is not None
        True

        Args:
            freq_center: Freq center to use.
            freq_range_percent: Freq range percent to use.
            nbits: Nbits to use.
        """
        self.nbits = nbits
        # Subtract one from each to start register at 0 (vs Wikipedia starting
        # at 1)
        self.poly = [value - 1 for value in [16, 15, 13, 4]]
        self.lfsr = 0  # Seed value
        self.max_freq = freq_center * (1 + freq_range_percent)
        self.min_freq = freq_center * (1 - freq_range_percent)

    def get_next_period(self):
        """Return the next period.
        Returns the stored next period from the object's internal state.

        Returns the stored next period from the object's internal state.


        >>> from PyICe.data_utils.signal_generator import lfsr_period_generator
        >>> hasattr(lfsr_period_generator, 'get_next_period')
        True

        Returns:
            The current next period.
        """
        bit = self.lfsr >> self.poly[0] & 1 ^ \
            self.lfsr >> self.poly[1] & 1 ^ \
            self.lfsr >> self.poly[2] & 1 ^ \
            self.lfsr >> self.poly[3] & 1
        bit = 1 if not bit else 0  # Invert for XNOR, allows all 0's on reset
        self.lfsr = (self.lfsr << 1) & 0xFFFF | bit
        code = self.lfsr & (2**self.nbits - 1)  # Just grab nbits
        freq = self.min_freq + \
            (self.max_freq - self.min_freq) * code / 2**self.nbits
        return 1 / freq

    def set_polynomial(self, ploynomial):
        """Takes a list ordered higest order term to the left, lowest to the right.

        The rightmost term starts from 0 not 1 whereas most math references start from index 1.


        >>> from PyICe.data_utils.signal_generator import lfsr_period_generator
        >>> hasattr(lfsr_period_generator, 'set_polynomial')
        True

        Args:
            ploynomial: Ploynomial to use.
        """
        self.poly = ploynomial
