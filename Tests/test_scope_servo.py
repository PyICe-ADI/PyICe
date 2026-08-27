"""Tests for scope_servo — scope-in-the-loop servo utility."""
import numpy
import pytest
from PyICe import lab_core, virtual_instruments
from PyICe.data_utils.scope_servo import scope_servo


def make_synthetic_pulse(amplitude, num_points=1000, duration=100e-6):
    """Generate a synthetic step waveform with given amplitude."""
    t = numpy.linspace(0, duration, num_points)
    y = numpy.zeros(num_points)
    y[num_points // 4:] = amplitude
    return t, y


class TestScopeServoConvergence:
    """Verify the servo converges on a target using synthetic scope data."""

    def setup_method(self):
        self.master = lab_core.master()
        self.stimulus_value = [0.0]
        self.arm_called = []
        self.trigger_called = []

        def write_stimulus(value):
            self.stimulus_value[0] = value

        self.time_ch = self.master.add_channel_virtual(
            'scope_time', read_function=lambda: make_synthetic_pulse(self.stimulus_value[0])[0])
        self.data_ch = self.master.add_channel_virtual(
            'scope_data', read_function=lambda: make_synthetic_pulse(self.stimulus_value[0])[1])

        self.servo = scope_servo(
            master=self.master,
            name='test',
            stimulus_channel=write_stimulus,
            scope_time_channel=self.time_ch,
            scope_data_channel=self.data_ch,
            extraction_fn=lambda wf: wf.average_out() - wf.average_in(),
            arm_fn=lambda: self.arm_called.append(True),
            trigger_fn=lambda: self.trigger_called.append(True),
            minimum=0.0,
            maximum=5.0,
            reltol=0.05,
            settle_time=0,
            max_tries=15,
            verbose=False,
        )

    def test_converges_on_target(self):
        """Servo should find a stimulus that produces feedback matching the target."""
        self.master.write('test_servo', 2.0)
        feedback = self.master.read('test_feedback')
        assert abs(feedback - 2.0) < 2.0 * 0.05

    def test_arm_and_trigger_called(self):
        """Each iteration should arm and trigger the scope."""
        self.master.write('test_servo', 1.0)
        assert len(self.arm_called) > 0
        assert len(self.trigger_called) > 0
        assert len(self.arm_called) == len(self.trigger_called)

    def test_history_populated(self):
        """Waveform history should contain entries from the servo run."""
        self.master.write('test_servo', 3.0)
        assert len(self.servo.history) > 0
        value, wf = self.servo.history[-1]
        assert value is not None


class TestScopeServoStimulusRouting:
    """Verify stimulus_channel accepts string, channel object, or callable."""

    def _make_master_with_scope_channels(self):
        master = lab_core.master()
        self.written_values = []
        master.add_channel_virtual('stim_by_name', write_function=lambda v: self.written_values.append(('name', v)))
        time_ch = master.add_channel_virtual('scope_time', read_function=lambda: make_synthetic_pulse(1.0)[0])
        data_ch = master.add_channel_virtual('scope_data', read_function=lambda: make_synthetic_pulse(1.0)[1])
        return master, time_ch, data_ch

    def test_string_stimulus(self):
        """A string stimulus_channel should write via master.write()."""
        master, time_ch, data_ch = self._make_master_with_scope_channels()
        servo = scope_servo(
            master=master, name='str_test', stimulus_channel='stim_by_name',
            scope_time_channel=time_ch, scope_data_channel=data_ch,
            extraction_fn=lambda wf: wf.average_out() - wf.average_in(),
            arm_fn=lambda: None, trigger_fn=lambda: None,
            minimum=0, maximum=5, settle_time=0, verbose=False,
        )
        master.write('str_test_servo', 1.0)
        assert any(mode == 'name' for mode, _ in self.written_values)

    def test_channel_object_stimulus(self):
        """A channel object stimulus should call .write() on it."""
        master, time_ch, data_ch = self._make_master_with_scope_channels()
        written = []
        ch_obj = master.add_channel_virtual('stim_obj', write_function=lambda v: written.append(v))
        servo = scope_servo(
            master=master, name='obj_test', stimulus_channel=ch_obj,
            scope_time_channel=time_ch, scope_data_channel=data_ch,
            extraction_fn=lambda wf: wf.average_out() - wf.average_in(),
            arm_fn=lambda: None, trigger_fn=lambda: None,
            minimum=0, maximum=5, settle_time=0, verbose=False,
        )
        master.write('obj_test_servo', 1.0)
        assert len(written) > 0

    def test_callable_stimulus(self):
        """A bare callable stimulus should be invoked directly."""
        master, time_ch, data_ch = self._make_master_with_scope_channels()
        written = []
        servo = scope_servo(
            master=master, name='fn_test', stimulus_channel=lambda v: written.append(v),
            scope_time_channel=time_ch, scope_data_channel=data_ch,
            extraction_fn=lambda wf: wf.average_out() - wf.average_in(),
            arm_fn=lambda: None, trigger_fn=lambda: None,
            minimum=0, maximum=5, settle_time=0, verbose=False,
        )
        master.write('fn_test_servo', 1.0)
        assert len(written) > 0


class TestScopeServoEdgeCases:
    """Edge cases: no trigger, bounds update."""

    def test_no_trigger_returns_zero(self):
        """When scope returns None (no trigger), feedback should be 0."""
        master = lab_core.master()
        time_ch = master.add_channel_virtual('scope_time', read_function=lambda: None)
        data_ch = master.add_channel_virtual('scope_data', read_function=lambda: None)
        servo = scope_servo(
            master=master, name='notrig', stimulus_channel=lambda v: None,
            scope_time_channel=time_ch, scope_data_channel=data_ch,
            extraction_fn=lambda wf: wf.average_out(),
            arm_fn=lambda: None, trigger_fn=lambda: None,
            minimum=0, maximum=5, settle_time=0, verbose=False,
        )
        feedback = master.read('notrig_feedback')
        assert feedback == 0

    def test_set_minimum_maximum(self):
        """set_minimum/set_maximum should update the underlying servo bounds."""
        master = lab_core.master()
        time_ch = master.add_channel_virtual('scope_time', read_function=lambda: make_synthetic_pulse(1.0)[0])
        data_ch = master.add_channel_virtual('scope_data', read_function=lambda: make_synthetic_pulse(1.0)[1])
        s = scope_servo(
            master=master, name='bounds', stimulus_channel=lambda v: None,
            scope_time_channel=time_ch, scope_data_channel=data_ch,
            extraction_fn=lambda wf: wf.average_out() - wf.average_in(),
            arm_fn=lambda: None, trigger_fn=lambda: None,
            minimum=0, maximum=10, settle_time=0, verbose=False,
        )
        s.set_minimum(2.0)
        s.set_maximum(8.0)
        assert s.servo.minimum == 2.0
        assert s.servo.maximum == 8.0
