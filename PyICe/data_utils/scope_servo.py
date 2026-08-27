"""Scope-in-the-loop (SCITL) servo utility.

Provides a generalized mechanism for servoing a stimulus channel until a
scope-measured quantity converges on a target value. The scope is armed,
the stimulus is applied, the waveform is captured and analyzed to extract
a scalar feedback measurement, and a binary/geometric search drives the
stimulus toward the desired target.

Usage:
    from PyICe.data_utils.scope_servo import scope_servo

    servo = scope_servo(
        master            = master,
        name              = 'iload',
        stimulus_channel  = 'pulse_gen_high_voltage',
        scope_time_channel= master.get_channel('scope_timedata'),
        scope_data_channel= master.get_channel('scope_ch1'),
        extraction_fn     = lambda wf: wf.average_out() - wf.average_in(),
        arm_fn            = lambda: master.write('scope_run_mode', 'SINGLE'),
        trigger_fn        = lambda: master.write('loadstep_trigger', 'TRIGGER'),
        minimum           = 0.1,
        maximum           = 1.8,
    )
    # Adds '{name}_servo' write channel and '{name}_feedback' read channel to master.
    # Writing to '{name}_servo' triggers a servo loop converging on the written target.
    master.write('iload_servo', 2.0)  # Servo until scope reads 2.0A

>>> from PyICe.data_utils.scope_servo import scope_servo

"""
import time
import numpy
from PyICe import virtual_instruments
from PyICe.data_utils.wave_analysis import waveform


class scope_servo:
    """Scope-in-the-loop servo.

    Wraps a simple_servo with scope acquisition logic: arm, trigger, capture,
    analyze. The user provides an extraction function that reduces a waveform
    to a scalar feedback value.

    >>> from PyICe.data_utils.scope_servo import scope_servo
    >>> scope_servo is not None
    True

    """

    def __init__(self, master, name, stimulus_channel, scope_time_channel,
                 scope_data_channel, extraction_fn, arm_fn, trigger_fn,
                 minimum, maximum, reltol=0.02, abstol=None, settle_time=0.5,
                 max_tries=13, step_method="BINARY", verbose=True, debug=False):
        """Initialize scope_servo.

        Args:
            master: PyICe channel_master to register channels with.
            name: Base name for generated channels.
            stimulus_channel: Name (str) or channel object for the stimulus output.
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
            debug: Plot waveforms on failure.
        """
        self._master = master
        self._name = name
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

        stimulus_ch = master.add_channel_virtual(
            f"{name}_stimulus",
            write_function=self._write_stimulus,
        )
        feedback_ch = master.add_channel_virtual(
            f"{name}_feedback",
            read_function=self._read_feedback,
        )

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
        self.servo.add_channel_target(f"{name}_servo_target")
        master.add(self.servo)

        master.add_channel_virtual(
            f"{name}_servo",
            write_function=self._run_servo,
        )

    def _write_stimulus(self, value):
        self._last_stimulus_value = value
        if isinstance(self._stimulus_channel, str):
            self._master.write(self._stimulus_channel, value)
        else:
            self._stimulus_channel.write(value)
        self._arm_fn()
        time.sleep(self._settle_time)
        self._trigger_fn()

    def _read_feedback(self):
        time_ch_name = self._scope_time_channel.get_name()
        data_ch_name = self._scope_data_channel.get_name()
        scope_data = self._master.read_channels(
            (self._scope_time_channel, self._scope_data_channel))
        if scope_data[time_ch_name] is None:
            return 0
        data = numpy.column_stack((scope_data[time_ch_name], scope_data[data_ch_name]))
        wf = waveform(data=data, debug=self._debug)
        self._waveform_history.append((self._last_stimulus_value, wf))
        result = self._extraction_fn(wf)
        if self._debug:
            wf.plot()
        return result

    def _run_servo(self, target):
        self._waveform_history.clear()
        try:
            self._master.write(f"{self._name}_servo_target", target)
        except Exception:
            if self._debug:
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
        """Set a custom search direction override for non-monotonic behavior."""
        self.servo.set_search_direction_override_fn(fn)
