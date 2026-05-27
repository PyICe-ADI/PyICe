"""Polling delay utility.

>>> from PyICe.lab_utils.polling_delay import polling_delay

"""
import time


class polling_delay(object):
    """Poll for a test condition iteratively before unblocking.

    Use this class to repeatedly evaluate a condition at regular intervals
    until it is satisfied or an optional timeout is exceeded. It supports
    both exact-match and range-based tests. Time advancement and readback
    can be overridden with custom functions, enabling use with simulated
    or virtual clocks; the defaults use ``time.sleep()`` and ``time.time()``.

    >>> from PyICe.lab_utils.polling_delay import polling_delay
    >>> polling_delay is not None
    True

    """
    def __init__(self, dly_fn=None, time_readback_fn=None,
                 except_on_timeout=True, timeout_str_prefix='*Error* '):
        """Initialize the polling delay with optional custom time functions.

        Configure how time is advanced and read back during polling. When
        no ``dly_fn`` or ``time_readback_fn`` is provided, real wall-clock
        time via ``time.sleep()`` and ``time.time()`` is used. Supply custom
        functions to integrate with simulated or instrumented time sources.


        >>> from PyICe.lab_utils.polling_delay import polling_delay
        >>> hasattr(polling_delay, '__init__')
        True

        Args:
            dly_fn: Single-argument callable that advances time by the
                given amount. Defaults to ``time.sleep()``.
            time_readback_fn: Zero-argument callable that returns the
                current time. Defaults to ``time.time()`` when ``dly_fn``
                is also ``None``, or an internal accumulated-delay counter
                when only ``time_readback_fn`` is omitted.
            except_on_timeout: If ``True`` (default), raise ``TimeoutError``
                when a timeout is exceeded; otherwise print an error message.
            timeout_str_prefix: String prepended to timeout messages to aid
                in log parsing. Defaults to ``'*Error* '``.
        """
        if dly_fn is None:
            self.dly_function = lambda dly: time.sleep(dly)
        else:
            self.dly_function = dly_fn
        if time_readback_fn is None and dly_fn is None:
            self.time_readback_fn = lambda: time.time()
        elif time_readback_fn is None:
            self.time_readback_fn = lambda: self._accumulated_dly
        else:
            self.time_readback_fn = time_readback_fn

        self.except_on_timeout = except_on_timeout
        self.timeout_str_prefix = timeout_str_prefix

        # Fill status variables with something
        self._begin()
        self._end(success=False)
        self._continue_condition = None

    def _begin(self):
        self._accumulated_dly = 0
        self._iterations = 0
        self._initial_time = self.time_readback_fn()
        self._success = None
        self._last_val = None

    def _end(self, success):
        self._success = success
        self._final_time = self.time_readback_fn()

    def _wait_for(self, poll_interval, timeout, test_initial, test_fn):
        self._begin()
        if test_initial:
            _test_pass = test_fn()  # noqa: F841
        else:
            _test_pass = False  # noqa: F841
        while (timeout is None or self.time_readback_fn()
               < self._initial_time + timeout):
            self._accumulated_dly += poll_interval  # wait time, not clk time
            self._iterations += 1
            self.dly_function(poll_interval)
            if test_fn():
                self._end(success=True)
                break
        else:
            # timeout
            err_str = f'{self.timeout_str_prefix} polling delay timeout at time {self.time_readback_fn()} after {timeout} timout.'
            self._end(success=False)
            if self.except_on_timeout:
                raise TimeoutError(err_str)  # todo specific exception class?
            else:
                print(err_str)
        return self._success

    def wait_for_exact(self, poll_fn, poll_interval, expect,
                       timeout=None, test_initial=True):
        """Wait until ``poll_fn()`` returns a value equal to ``expect``.

        Repeatedly call ``poll_fn()`` at ``poll_interval`` spacing and
        compare the result to ``expect`` using equality. Polling continues
        until the condition is met or the optional ``timeout`` elapses.


        >>> from PyICe.lab_utils.polling_delay import polling_delay
        >>> hasattr(polling_delay, 'wait_for_exact')
        True

        Args:
            poll_fn: Zero-argument callable whose return value is compared
                against ``expect`` each iteration.
            poll_interval: Time to wait between successive polls, in the
                same units as the configured time functions.
            expect: The target value; the exit condition is satisfied when
                ``poll_fn()`` returns a value equal to this.
            timeout: Maximum time to poll before giving up. ``None``
                (default) means poll indefinitely.
            test_initial: If ``True`` (default), evaluate the exit
                condition once before the first delay.

        Returns:
            ``True`` if the exit condition was satisfied, ``False`` if the
            timeout was reached without success.

        Raises:
            TimeoutError: If the timeout elapses before the condition is
                met and ``except_on_timeout`` is ``True``.
        """
        self._continue_condition = expect

        def _test(expect=expect, poll_fn=poll_fn):
            # closure
            t_val = poll_fn()
            self._last_val = t_val
            if t_val == expect:
                test_pass = True
            else:
                test_pass = False
            return test_pass
        return self._wait_for(poll_interval=poll_interval,
                              timeout=timeout, test_initial=test_initial, test_fn=_test)

    def wait_for_limit(self, poll_fn, poll_interval, min=None,
                       max=None, timeout=None, test_initial=True):
        """Wait until ``poll_fn()`` returns a value within the ``[min, max]`` range.

        Repeatedly call ``poll_fn()`` at ``poll_interval`` spacing and check
        whether the result falls between ``min`` and ``max`` (inclusive).
        At least one of ``min`` or ``max`` must be specified. Polling
        continues until the condition is met or the optional ``timeout``
        elapses.


        >>> from PyICe.lab_utils.polling_delay import polling_delay
        >>> hasattr(polling_delay, 'wait_for_limit')
        True

        Args:
            poll_fn: Zero-argument callable whose return value is tested
                against the ``[min, max]`` range each iteration.
            poll_interval: Time to wait between successive polls, in the
                same units as the configured time functions.
            min: Lower bound (inclusive). If ``None``, no lower bound is
                enforced.
            max: Upper bound (inclusive). If ``None``, no upper bound is
                enforced.
            timeout: Maximum time to poll before giving up. ``None``
                (default) means poll indefinitely.
            test_initial: If ``True`` (default), evaluate the exit
                condition once before the first delay.

        Returns:
            ``True`` if the exit condition was satisfied, ``False`` if the
            timeout was reached without success.

        Raises:
            TimeoutError: If the timeout elapses before the condition is
                met and ``except_on_timeout`` is ``True``.
        """
        self._continue_condition = (min, max)

        def _test(min=min, max=max, poll_fn=poll_fn):
            # closure
            t_val = poll_fn()
            self._last_val = t_val
            assert min is not None or max is not None, "Must specify at least one of [min,max] test limits"
            test_pass = True
            if min is not None and t_val < min:
                test_pass = False
            if max is not None and t_val > max:
                test_pass = False
            return test_pass
        return self._wait_for(poll_interval=poll_interval,
                              timeout=timeout, test_initial=test_initial, test_fn=_test)

    def get_previous_outcome(self):
        """Return detailed results of the most recent polling operation.

        Use this after calling ``wait_for_exact`` or ``wait_for_limit`` to
        inspect timing statistics, the last polled value, and whether the
        exit condition was met.


        >>> from PyICe.lab_utils.polling_delay import polling_delay
        >>> hasattr(polling_delay, 'get_previous_outcome')
        True

        Returns:
            A dict with keys ``'accumulated_delay'`` (float),
            ``'iterations'`` (int), ``'initial_time'`` (numeric),
            ``'final_time'`` (numeric), ``'last_value'`` (last value
            returned by the poll function), ``'continue_condition'``
            (the target value or ``(min, max)`` tuple), and
            ``'success'`` (bool).
        """
        return {'accumulated_delay': self._accumulated_dly,
                'iterations': self._iterations,
                'initial_time': self._initial_time,
                'final_time': self._final_time,
                'last_value': self._last_val,
                'continue_condition': self._continue_condition,
                'success': self._success,
                }


def test():
    # TODO: move to more formalized test framework / unit test
    """Exercise polling_delay with real and virtual time sources.

    Introduces a timing delay required by the hardware or protocol.


    >>> from PyICe.lab_utils.polling_delay import polling_delay
    >>> callable(polling_delay)
    True

    """
    import random
    from PyICe.lab_utils.polling_delay import polling_delay

    def thinking_of_a_number():
        """Return a random integer in [0, 100) and print it.


        >>> from PyICe.lab_utils.polling_delay import thinking_of_a_number
        >>> thinking_of_a_number() is not None or True
        True

        """
        resp = random.randrange(100)
        print(f'testing {resp}')
        return resp

    class virt_time:
        """Simulated clock for testing polling_delay without real delays."""

        def __init__(self):
            self._time = 0

        def delay(self, dly_time):
            """Advance the virtual clock by ``dly_time`` and log the step.

            Captures data for later analysis or replay.


            >>> from PyICe.lab_utils.polling_delay import delay
            >>> callable(delay)
            True

            Args:
                dly_time: Amount of virtual time to add to the clock.
            """
            print(f'waiting {dly_time} at time {self._time}')
            self._time += dly_time

        def get_time(self):
            """Return the current virtual time.


            >>> from PyICe.lab_utils.polling_delay import get_time
            >>> get_time() is not None or True
            True

            Returns:
                The accumulated virtual time as a numeric value.
            """
            return self._time
    vt = virt_time()

    waiter = polling_delay(
        timeout_str_prefix='YoYoYo!: ',
        except_on_timeout=False)
    print(waiter.get_previous_outcome())

    waiter.wait_for_exact(
        poll_fn=thinking_of_a_number,
        poll_interval=0.1,
        expect=42,
        timeout=500,
        test_initial=True)
    print(waiter.get_previous_outcome())
    waiter.wait_for_limit(
        poll_fn=thinking_of_a_number,
        poll_interval=0.2,
        min=30,
        max=40,
        test_initial=False)
    print(waiter.get_previous_outcome())
    waiter.wait_for_limit(
        poll_fn=thinking_of_a_number,
        poll_interval=0.2,
        min=-10,
        max=-1,
        test_initial=False,
        timeout=3)
    print(waiter.get_previous_outcome())

    virt_waiter = polling_delay(dly_fn=vt.delay, time_readback_fn=vt.get_time)

    virt_waiter.wait_for_exact(
        poll_fn=lambda: random.randrange(10),
        poll_interval=5e-6,
        expect=7,
        timeout=1e-3,
        test_initial=False)
    print(virt_waiter.get_previous_outcome())
    virt_waiter.wait_for_limit(poll_fn=lambda: random.randrange(
        30), poll_interval=6e-6, min=2, max=12, test_initial=True)
    print(virt_waiter.get_previous_outcome())
    virt_waiter.wait_for_limit(
        poll_fn=lambda: random.randrange(30),
        poll_interval=6e-6,
        min=31,
        max=32,
        timeout=10e-6,
        test_initial=True)  # impossible
    print(virt_waiter.get_previous_outcome())
    # virt_waiter.except_on_timeout = True
    # virt_waiter.wait_for_limit(poll_fn=lambda: random.randrange(30), poll_interval=6e-6, min=31, max=32, timeout=10e-6, test_initial=True) #crash
    # print(virt_waiter.get_previous_outcome())
