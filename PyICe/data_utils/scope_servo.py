"""Scope-in-the-loop (SCITL) servo utility.

Provides a generalized mechanism for servoing a stimulus channel until a
scope-measured quantity converges on a target value. The scope is armed,
the stimulus is applied, the waveform is captured and analyzed to extract
a scalar feedback measurement, and a binary/geometric search drives the
stimulus toward the desired target.

Usage:
    from PyICe.data_utils.scope_servo import scope_servo

    servo = scope_servo(
        name              = 'iload',
        stimulus_channel  = master['pulse_gen_high_voltage'],
        scope_time_channel= master['scope_timedata'],
        scope_data_channel= master['scope_ch1'],
        extraction_fn     = lambda wf: wf.average_out() - wf.average_in(),
        arm_fn            = lambda: master.write('scope_run_mode', 'SINGLE'),
        trigger_fn        = lambda: master.write('loadstep_trigger', 'TRIGGER'),
        minimum           = 0.1,
        maximum           = 1.8,
    )
    # The servo is an instrument owning '{name}_servo' (write) and '{name}_feedback' (read) channels.
    # Nothing is registered with the master until you add the servo yourself.
    master.add(servo)
    master.write('iload_servo', 2.0)  # Servo until scope reads 2.0A
    # The same operations are available directly, without a master:
    servo.run(2.0)
    amplitude = servo.read_feedback()  # Measure whatever is on the scope now

>>> from PyICe.data_utils.scope_servo import scope_servo

"""
import time
import numpy
from PyICe import virtual_instruments
from PyICe.lab_core import channel, instrument
from PyICe.data_utils.wave_analysis import waveform


class scope_servo(instrument):
    """Scope-in-the-loop servo.

    Wraps a simple_servo with scope acquisition logic: arm, trigger, capture,
    analyze. The user provides an extraction function that reduces a waveform
    to a scalar feedback value.

    Exposes '{name}_servo' (write a target to servo to it) and '{name}_feedback'
    (read the current scalar measurement) channels, which only reach a master
    when the caller adds this instrument to it.

    >>> from PyICe.data_utils.scope_servo import scope_servo
    >>> scope_servo is not None
    True

    """

    def __init__(self, name, stimulus_channel, scope_time_channel,
                 scope_data_channel, extraction_fn, arm_fn, trigger_fn,
                 minimum, maximum, reltol=0.02, abstol=None, settle_time=0.5,
                 max_tries=13, step_method="BINARY", verbose=True, debug=False):
        """Initialize scope_servo.

        Args:
            name: Label for the servo's internal channels and messages.
            stimulus_channel: Channel object or callable for the stimulus output.
            scope_time_channel: Channel object for the scope time axis data.
            scope_data_channel: Channel object for the scope waveform data.
            extraction_fn: Callable taking a waveform object, returning a scalar.
            arm_fn: Callable to arm the scope (e.g. set to single-shot mode).
            trigger_fn: Callable to trigger the acquisition.
            minimum: Lower bound for the stimulus search range.
            maximum: Upper bound for the stimulus search range.
            reltol: Relative tolerance for convergence.
            abstol: Absolute tolerance for convergence.
            settle_time: Seconds to wait between stimulus write and trigger.
            max_tries: Maximum servo iterations.
            step_method: Search method ("BINARY" or "GEOMETRIC").
            verbose: Print servo progress.
            debug: Also plot each waveform as it is captured. Failed runs always plot every attempt.
        """
        if isinstance(stimulus_channel, str):
            raise TypeError("stimulus_channel must be a channel object or callable, not a channel name.")
        self._base_name = 'scope_servo'
        instrument.__init__(self, f"Scope servo {name}")
        self._stimulus_channel = stimulus_channel
        self._scope_time_channel = scope_time_channel
        self._scope_data_channel = scope_data_channel
        self._extraction_fn = extraction_fn
        self._arm_fn = arm_fn
        self._trigger_fn = trigger_fn
        self._settle_time = settle_time
        self._debug = debug
        self._waveform_history = []
        self._last_stimulus_value = None

        stimulus_ch = channel(f"{name}_stimulus", write_function=self._write_stimulus)
        feedback_ch = channel(f"{name}_feedback", read_function=self.read_feedback)

        self.servo = virtual_instruments.simple_servo(
            fb_channel=feedback_ch,
            output_channel=stimulus_ch,
            minimum=minimum,
            maximum=maximum,
            reltol=reltol,
            abstol=abstol,
            verbose=verbose,
            step_method=step_method,
            max_tries=max_tries,
        )
        self._add_channel(channel(f"{name}_servo", write_function=self.run))
        self._add_channel(channel(f"{name}_feedback", read_function=self.read_feedback))

    def _write_stimulus(self, value):
        self._last_stimulus_value = value
        if callable(self._stimulus_channel) and not hasattr(self._stimulus_channel, 'write'):
            self._stimulus_channel(value)
        else:
            self._stimulus_channel.write(value)
        self._arm_fn()
        time.sleep(self._settle_time)
        self._trigger_fn()

    def read_feedback(self):
        """Measure the scalar feedback from the waveform currently on the scope.

        Returns 0 if the scope has no data (no trigger).
        """
        time_data = self._scope_time_channel.read()
        if time_data is None:
            return 0
        data = numpy.column_stack((time_data, self._scope_data_channel.read()))
        wf = waveform(data=data, debug=self._debug)
        self._waveform_history.append((self._last_stimulus_value, wf))
        result = self._extraction_fn(wf)
        if self._debug:
            wf.plot()
        return result

    def run(self, target):
        """Servo the stimulus until the extracted feedback matches target.

        Returns:
            The number of servo iterations used.

        Raises:
            ServoException: If the servo fails to converge. Every attempted
                waveform is plotted before the exception propagates.
        """
        self._waveform_history.clear()
        try:
            return self.servo.servo(target)
        except Exception:
            for i, (value, wf) in enumerate(self._waveform_history):
                wf.plt.title.text = f"attempt {i + 1}: {value}"
                wf._plot()
                wf.plot()
            raise

    @property
    def history(self):
        """Access the waveform history from the most recent servo run."""
        return list(self._waveform_history)

    def set_minimum(self, value):
        """Update the lower search bound."""
        self.servo.set_minimum(value)

    def set_maximum(self, value):
        """Update the upper search bound."""
        self.servo.set_maximum(value)

    def set_search_direction_override_fn(self, fn):
        """Set a custom search direction override for non-monotonic behavior.

        Args:
            fn: Callable accepting the keyword arguments and returning None, True or False,
                as documented on simple_servo.search_direction_override.
        """
        self.servo.set_search_direction_override_fn(fn)
