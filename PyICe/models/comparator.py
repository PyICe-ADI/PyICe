

class comparator(object):
    '''Virtual comparator with programmable rising and falling input thresholds
    and programmable output high and low logic levels. Also models forcing
    instrument overshoot as a percentage of transition magnitude.

    Set falling_threshold or rising_threshold to None to implement latching behaviour.

    >>> comp = comparator(falling_threshold=1.0, rising_threshold=2.0,
    ...                   out_high=5.0, out_low=0.0)
    >>> comp.read()
    0.0
    >>> comp.write(2.5)
    >>> comp.read()
    5.0
    >>> comp.write(1.5)
    >>> comp.read()
    5.0
    >>> comp.write(0.5)
    >>> comp.read()
    0.0
    '''

    def __init__(self, falling_threshold, rising_threshold,
                 out_high=1, out_low=0, write_overshoot=0, verbose=False):
        '''Create a comparator model.

        >>> comp = comparator(falling_threshold=2.5, rising_threshold=2.5)
        >>> comp.read()
        0
        >>> comp.write(3.0)
        >>> comp.read()
        1
        '''
        self.state = False
        self.input = None
        self.set_thresholds(falling_threshold, rising_threshold)
        self.out_high = out_high
        self.out_low = out_low
        self.write_overshoot = write_overshoot
        self.verbose = verbose
        assert write_overshoot >= 0
        assert falling_threshold is not None or rising_threshold is not None

    def debug_print(self, msg):
        if self.verbose:
            print("*COMPARATOR*, {}".format(msg))

    def set_thresholds(self, falling_threshold, rising_threshold):
        '''Change thresholds on an existing comparator.

        >>> comp = comparator(falling_threshold=1.0, rising_threshold=2.0)
        >>> comp.write(1.5)
        >>> comp.read()
        0
        >>> comp.set_thresholds(falling_threshold=0.5, rising_threshold=1.0)
        >>> comp.write(1.5)
        >>> comp.read()
        1
        '''
        self.falling_threshold = falling_threshold
        self.rising_threshold = rising_threshold

    def write(self, value):
        if self.input is not None:
            # overshoot changes polarity naturally?
            overshoot = self.write_overshoot * (value - self.input)
        else:
            overshoot = 0
            if self.write_overshoot != 0:
                self.debug_print(
                    "Comparator input initialized for overshoot calculation")
        if self.write_overshoot != 0:
            overshoot_str = " after overshooting to: {}".format(
                value + overshoot)
        else:
            overshoot_str = ""
        self.debug_print(
            "Setting comparator input to: {}{}".format(
                value, overshoot_str))
        if self.state and self.falling_threshold is not None and value + \
                overshoot < self.falling_threshold:
            self.state = False
            self.debug_print("Comparator output transition low")
        elif not self.state and self.rising_threshold is not None and value + overshoot > self.rising_threshold:
            self.state = True
            self.debug_print("Comparator output transition high")
        self.input = value

    def reset(self):
        '''Force comparator output low regardless of input.

        >>> comp = comparator(falling_threshold=1.0, rising_threshold=2.0)
        >>> comp.write(3.0)
        >>> comp.read()
        1
        >>> comp.reset()
        >>> comp.read()
        0
        '''
        self.state = False
        self.debug_print("Forcing comparator output low.")

    def set(self):
        '''Force comparator output high regardless of input.

        >>> comp = comparator(falling_threshold=1.0, rising_threshold=2.0)
        >>> comp.read()
        0
        >>> comp.set()
        >>> comp.read()
        1
        '''
        self.state = True
        self.debug_print("Forcing comparator output high.")

    def read(self):
        '''Return current output level.

        >>> comp = comparator(falling_threshold=1.0, rising_threshold=2.0,
        ...                   out_high=3.3, out_low=0.0)
        >>> comp.read()
        0.0
        >>> comp.write(2.5)
        >>> comp.read()
        3.3
        '''
        return self.out_high if self.state else self.out_low
