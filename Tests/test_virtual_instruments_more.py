"""Tests for virtual instruments more."""
import time
import pytest
from PyICe.virtual_instruments import (
    timer, integrator, differentiator, ramp_to,
)


class TestTimer:
    """Tests for Timer."""

    @pytest.fixture
    def tmr(self):
        """Return tmr result.

        Returns:
            Result value.
        """
        t = timer()
        t.add_channel_total_seconds('total_s')
        t.add_channel_delta_seconds('delta_s')
        return t

    def test_total_timer_increases(self, tmr):
        """Perform test total timer increases operation.

        Args:
            tmr: Tmr.
        """
        tmr['total_s'].read()
        time.sleep(0.05)
        val = tmr['total_s'].read()
        assert val >= 0.04

    def test_delta_timer_measures_interval(self, tmr):
        """Perform test delta timer measures interval operation.

        Args:
            tmr: Tmr.
        """
        tmr['delta_s'].read()
        time.sleep(0.05)
        val = tmr['delta_s'].read()
        assert val >= 0.04

    def test_reset_timer(self, tmr):
        """Perform test reset timer operation.

        Args:
            tmr: Tmr.
        """
        tmr['total_s'].read()
        time.sleep(0.05)
        tmr['total_s'].read()
        tmr.reset_timer()
        time.sleep(0.05)
        val = tmr['total_s'].read()
        assert val < 0.1

    def test_pause_resume(self, tmr):
        """Perform test pause resume operation.

        Args:
            tmr: Tmr.
        """
        tmr['total_s'].read()
        time.sleep(0.05)
        tmr.pause_timer()
        paused_val = tmr['total_s'].read()
        time.sleep(0.1)
        still_paused = tmr['total_s'].read()
        assert still_paused == paused_val
        tmr.resume_timer()
        time.sleep(0.05)
        resumed_val = tmr['total_s'].read()
        assert resumed_val > paused_val

    def test_total_minutes(self):
        """Perform test total minutes operation."""
        t = timer()
        t.add_channel_total_minutes('total_m')
        t['total_m'].read()
        time.sleep(0.06)
        val = t['total_m'].read()
        assert val >= 0.06 / 60.0

    def test_frequency_channel(self):
        """Perform test frequency channel operation."""
        t = timer()
        t.add_channel_frequency_hz('freq')
        t['freq'].read()
        time.sleep(0.05)
        freq = t['freq'].read()
        assert freq is not None
        assert freq > 0

    def test_add_to_master(self, master_instance):
        """Perform test add to master operation.

        Args:
            master_instance: Master instance.
        """
        t = timer()
        t.add_channel_total_seconds('elapsed')
        master_instance.add(t)
        master_instance.read_channel('elapsed')
        time.sleep(0.05)
        val = master_instance.read_channel('elapsed')
        assert val >= 0.04


class TestIntegrator:
    """Tests for Integrator."""

    @pytest.fixture
    def integ(self):
        """Return integ result.

        Returns:
            Result value.
        """
        ig = integrator(init=0)
        ig.add_channel_integration_seconds('integral')
        ig.add_channel_integrate('input')
        return ig

    def test_integration_accumulates(self, integ):
        """Perform test integration accumulates operation.

        Args:
            integ: Integ.
        """
        integ['input'].write(10)
        time.sleep(0.05)
        integ['input'].write(10)
        val = integ['integral'].read()
        assert val > 0

    def test_integration_zero_value(self, integ):
        """Perform test integration zero value operation.

        Args:
            integ: Integ.
        """
        integ['input'].write(0)
        time.sleep(0.05)
        integ['input'].write(0)
        val = integ['integral'].read()
        assert val == pytest.approx(0, abs=0.01)

    def test_initial_value(self):
        """Perform test initial value operation."""
        ig = integrator(init=100)
        ig.add_channel_integration_seconds('integral')
        ig.add_channel_integrate('input')
        integ = ig
        integ['input'].write(0)
        time.sleep(0.05)
        integ['input'].write(0)
        val = integ['integral'].read()
        assert val == pytest.approx(100, abs=1)

    def test_accumulate_method(self):
        """Perform test accumulate method operation."""
        ig = integrator(init=0)
        ig.add_channel_integration_seconds('integral')
        ig.accumulate(50)
        val = ig['integral'].read()
        assert val == pytest.approx(50, abs=0.1)


class TestDifferentiator:
    """Tests for Differentiator."""

    @pytest.fixture
    def diff(self):
        """Return diff result.

        Returns:
            Result value.
        """
        d = differentiator()
        d.add_channel_differentiation_seconds('deriv')
        d.add_channel_differentiate('input')
        return d

    def test_first_call_returns_none(self, diff):
        """Perform test first call returns none operation.

        Args:
            diff: Diff.
        """
        diff['input'].write(10)
        val = diff['deriv'].read()
        assert val is None

    def test_constant_signal_zero_derivative(self, diff):
        """Perform test constant signal zero derivative operation.

        Args:
            diff: Diff.
        """
        diff['input'].write(10)
        time.sleep(0.05)
        diff['input'].write(10)
        val = diff['deriv'].read()
        assert val == pytest.approx(0, abs=1)

    def test_increasing_signal_positive_derivative(self, diff):
        """Perform test increasing signal positive derivative operation.

        Args:
            diff: Diff.
        """
        diff['input'].write(0)
        time.sleep(0.05)
        diff['input'].write(100)
        val = diff['deriv'].read()
        assert val > 0

    def test_decreasing_signal_negative_derivative(self, diff):
        """Perform test decreasing signal negative derivative operation.

        Args:
            diff: Diff.
        """
        diff['input'].write(100)
        time.sleep(0.05)
        diff['input'].write(0)
        val = diff['deriv'].read()
        assert val < 0


class TestRampTo:
    """Tests for Ramp To."""

    @pytest.fixture
    def ramp_system(self, master_instance):
        """Return ramp system result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
        m = master_instance
        forcing = m.add_channel_dummy('force')
        forcing.write(0.0)
        r = ramp_to(verbose=False)
        r.add_channel_binary('ramp_bin', forcing, abstol=0.001)
        r.add_channel_linear('ramp_lin', forcing, step_size=0.1)
        m.add(r)
        return m, forcing

    def test_binary_ramp_reaches_target(self, ramp_system):
        """Perform test binary ramp reaches target operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        m.write_channel('ramp_bin', 5.0)
        assert forcing.read() == pytest.approx(5.0)

    def test_binary_ramp_small_steps(self, ramp_system):
        """Perform test binary ramp small steps operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        m.write_channel('ramp_bin', 1.0)
        assert forcing.read() == pytest.approx(1.0)

    def test_linear_ramp_reaches_target(self, ramp_system):
        """Perform test linear ramp reaches target operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        m.write_channel('ramp_lin', 0.5)
        assert forcing.read() == pytest.approx(0.5)

    def test_binary_ramp_negative_direction(self, ramp_system):
        """Perform test binary ramp negative direction operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        forcing.write(10.0)
        m.write_channel('ramp_bin', 3.0)
        assert forcing.read() == pytest.approx(3.0)

    def test_linear_ramp_negative_direction(self, ramp_system):
        """Perform test linear ramp negative direction operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        forcing.write(1.0)
        m.write_channel('ramp_lin', 0.0)
        assert forcing.read() == pytest.approx(0.0)

    def test_binary_ramp_already_at_target(self, ramp_system):
        """Perform test binary ramp already at target operation.

        Args:
            ramp_system: Ramp system.
        """
        m, forcing = ramp_system
        forcing.write(5.0)
        m.write_channel('ramp_bin', 5.0)
        assert forcing.read() == pytest.approx(5.0)

    def test_max_step_limits_binary(self, master_instance):
        """Perform test max step limits binary operation.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        forcing = m.add_channel_dummy('force')
        forcing.write(0.0)
        r = ramp_to(verbose=False)
        r.add_channel_binary('ramp', forcing, abstol=0.001, max_step=1.0)
        m.add(r)
        m.write_channel('ramp', 10.0)
        assert forcing.read() == pytest.approx(10.0)
