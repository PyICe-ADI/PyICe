"""Delay loop utility."""
import time
import datetime


class delay_loop(object):
    """Maintain a constant loop period independent of loop processing time.

    Useful for constant-rate data collection loops or any periodic task where
    the work inside the loop takes a variable amount of time. Measures elapsed
    time at the beginning and end of each iteration and sleeps only the
    remaining balance so the total period stays fixed. Optionally compensates
    for overruns across cycles to prevent long-term timing drift.
    """
    def __init__(self, strict=False, begin=True, no_drift=True):
        """Initialize the delay loop timer.

        Timer will automatically begin when the object is instantiated if begin=True.
        To start timer only when ready, set begin=False and call begin() method to start timer.
        If no_drift=True, delay loop will manage loop time over-runs by debiting extra time from next cycle.
        This ensures long-term time stability at the expense of increased jitter.
        Windows task switching can add multi-mS uncertainty to each delay() call, which can accumulate if not accounted for.
        Set no_drift=False to ignore time over-runs when computing next delay time.

        Args:
            strict: If True, raise an Exception when loop processing
                exceeds the requested delay instead of printing a warning.
            begin: If True, start the internal timer immediately upon
                construction. Set to False to defer timing until the
                begin() method is called explicitly.
            no_drift: If True, compensate for overruns by debiting excess
                time from the next cycle, maintaining long-term timing
                accuracy. If False, each cycle's delay is computed
                independently, ignoring prior overruns.
        """
        self.strict = strict
        self.no_drift = no_drift
        self.count = 0
        self.begin_time = None
        self.delay_time = None  # last loop time for margin diagnostics.
        self.loop_time = None
        if begin:
            self.begin()

    def __call__(self, seconds):
        """Delegate to delay(), allowing the instance to be called directly.

        Provides a convenient shorthand so that ``dl(seconds)`` is equivalent
        to ``dl.delay(seconds)``.

        Args:
            seconds: Desired total loop period in seconds.

        Returns:
            The actual sleep time applied in seconds, as returned by delay().
        """
        return self.delay(seconds)

    def get_count(self):
        """Return the total number of times delay() has been called.

        Returns:
            The cumulative loop iteration count since construction.
        """
        return self.count

    def get_total_time(self):
        """Return the elapsed wall-clock time since the first delay.

        Returns:
            Total elapsed seconds as a float since the timer was first started.
        """
        return (datetime.datetime.now(datetime.timezone.utc) -
                self.start_time).total_seconds()

    def begin(self, offset=0):
        """Record the start timestamp for the current loop iteration.

        Called automatically at construction (when ``begin=True``) and after
        each call to delay(). Can also be called manually when deferred
        timing is needed.

        Args:
            offset: Time adjustment in seconds added to the recorded start
                time, used internally to compensate for overruns from the
                previous cycle.
        """
        if self.begin_time is None:
            self.start_time = datetime.datetime.now(datetime.timezone.utc)
        self.begin_time = datetime.datetime.now(
            datetime.timezone.utc) + datetime.timedelta(seconds=offset)

    def delay(self, seconds):
        """Sleep for the remaining balance of the requested loop period.

        Computes how much time has elapsed since begin() and sleeps only the
        difference so the total iteration duration equals ``seconds``. If the
        loop body already exceeded the requested period, a warning is printed
        (or an exception is raised when ``strict=True``). After sleeping, the
        timer is automatically restarted for the next iteration.

        Args:
            seconds: Desired total loop period in seconds, including both
                processing time and the compensating sleep.

        Returns:
            The actual sleep time in seconds. Negative values indicate the
            loop body exceeded the requested period (overrun).

        Raises:
            Exception: If ``strict`` is True and the loop processing time
                exceeded the requested delay.
        """
        if self.begin_time is None:
            raise Exception('Call begin() method before delay().')
        self.count += 1
        elapsed_time = datetime.datetime.now(datetime.timezone.utc) - self.begin_time
        self.delay_time = (
            datetime.timedelta(
                seconds=seconds) -
            elapsed_time).total_seconds()
        if (self.delay_time < 0):
            if (self.strict is True):
                raise Exception(
                    'Loop processing longer than requested delay by {:3.3f} seconds at {}.'.format(
                        -self.delay_time, datetime.datetime.now()))
            else:
                print(
                    'Warning! Loop processing longer than requested delay by {:3.3f} seconds at {}.'.format(
                        -self.delay_time, datetime.datetime.now()))
        else:
            time.sleep(self.delay_time)
        self.loop_time = (
            datetime.datetime.now(
                datetime.timezone.utc) -
            self.begin_time).total_seconds()
        if self.no_drift:
            # restart timer for next loop cycle, use offset to correct for over
            # run.
            self.begin(offset=seconds - self.loop_time)
        else:
            # restart timer for next loop cycle, ignore over run.
            self.begin(offset=0)
        return self.delay_time

    def time_remaining(self, loop_time):
        """Return how many seconds remain in the current loop period.

        Designed for use inside a ``while`` loop that performs work until the
        period expires. When the returned value reaches zero or below, the
        timer is automatically restarted for the next cycle.

        Args:
            loop_time: Desired total loop period in seconds against which
                the elapsed time is compared.

        Returns:
            Seconds remaining in the current period. A value of zero or
            less indicates the period has expired.

        Raises:
            Exception: If begin() has not been called before this method.
        """
        if self.begin_time is None:
            raise Exception('Call begin() method before time_remaining().')
        remaining_time = loop_time - \
            (datetime.datetime.now(datetime.timezone.utc) - self.begin_time).total_seconds()
        if remaining_time <= 0:
            # restart timer for next loop cycle, use offset to correct for over
            # run.
            self.begin(offset=remaining_time)
        return remaining_time

    def delay_margin(self):
        """Return the sleep time from the most recent call to delay().

        Useful for diagnosing how much margin remains before the loop body
        would exceed the requested period.

        Returns:
            The sleep duration in seconds that was (or would have been)
            applied on the last delay() call. Negative values indicate an
            overrun.
        """
        return self.delay_time

    def achieved_loop_time(self):
        """Return the actual wall-clock duration of the previous loop iteration.

        Includes any overrun beyond the requested period, so this value may
        exceed the target passed to delay().

        Returns:
            The measured loop duration in seconds from the most recent
            begin-to-end cycle, or None if delay() has not yet been called.
        """
        return self.loop_time
