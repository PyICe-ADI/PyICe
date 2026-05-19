"""Delay loop utility."""
import time
import datetime


class delay_loop(object):
    """Make constant loop delay independent of loop processing time by measuring time at beginning.

    and end of loop and adding extra delay as necessary
    """
    def __init__(self, strict=False, begin=True, no_drift=True):
        """Set strict to True to raise an Exception if loop time is longer than requested delay.

        Timer will automatically begin when the object is instantiated if begin=True.
        To start timer only when ready, set begin=False and call begin() method to start timer.
        If no_drift=True, delay loop will manage loop time over-runs by debiting extra time from next cycle.
        This ensures long-term time stability at the expense of increased jitter.
        Windows task switching can add multi-mS uncertainty to each delay() call, which can accumulate if not accounted for.
        Set no_drift=False to ignore time over-runs when computing next delay time.

        Args:
            begin: Begin.
            no_drift: No drift.
            strict: Strict.
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
        """Call the instance.

        Args:
            seconds: Seconds.

        Returns:
            Result value.
        """
        return self.delay(seconds)

    def get_count(self):
        """Returns total number of times delay() method called.

        Returns:
            Result value.
        """
        return self.count

    def get_total_time(self):
        """Returns total number of seconds since first delay.

        Returns:
            Result value.
        """
        return (datetime.datetime.now(datetime.UTC) -
                self.start_time).total_seconds()

    def begin(self, offset=0):
        """Make note of begin time for loop measurement. Use offset to adjust the begin time in case of overrun on last cycle.

        Args:
            offset: Offset value.
        """
        if self.begin_time is None:
            self.start_time = datetime.datetime.now(datetime.UTC)
        self.begin_time = datetime.datetime.now(
            datetime.UTC) + datetime.timedelta(seconds=offset)

    def delay(self, seconds):
        """Delay extra time to make loop time constant.

        returns actual delay time achieved

        Args:
            seconds: Seconds.

        Returns:
            Result value.

        Raises:
            Exception: On error condition.
        """
        if self.begin_time is None:
            raise Exception('Call begin() method before delay().')
        self.count += 1
        elapsed_time = datetime.datetime.now(datetime.UTC) - self.begin_time
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
                datetime.UTC) -
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
        """Use this in a while loop to perform another function for duration loop_time. Test the result for 0 or less.

        Args:
            loop_time: Loop time.

        Returns:
            Result value.

        Raises:
            Exception: On error condition.
        """
        if self.begin_time is None:
            raise Exception('Call begin() method before time_remaining().')
        remaining_time = loop_time - \
            (datetime.datetime.now(datetime.UTC) - self.begin_time).total_seconds()
        if remaining_time <= 0:
            # restart timer for next loop cycle, use offset to correct for over
            # run.
            self.begin(offset=remaining_time)
        return remaining_time

    def delay_margin(self):
        """Return extra time remaining (ie sleep time) before last call to delay().

        Returns:
            Result value.
        """
        return self.delay_time

    def achieved_loop_time(self):
        """Return previous actual achieved loop time (including any overrun).

        Returns:
            Result value.
        """
        return self.loop_time
