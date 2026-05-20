"""Tests for delay loop."""
import time
import pytest
from PyICe.lab_utils.delay_loop import delay_loop


class TestDelayLoop:
    """Tests for Delay Loop."""

    def test_basic_delay(self):
        """Perform test basic delay operation."""
        dl = delay_loop(strict=False)
        margin = dl.delay(0.05)
        assert margin >= 0

    def test_count_increments(self):
        """Perform test count increments operation."""
        dl = delay_loop()
        assert dl.get_count() == 0
        dl.delay(0.01)
        assert dl.get_count() == 1
        dl.delay(0.01)
        assert dl.get_count() == 2

    def test_total_time(self):
        """Perform test total time operation."""
        dl = delay_loop()
        dl.delay(0.05)
        dl.delay(0.05)
        total = dl.get_total_time()
        assert total >= 0.09

    def test_delay_margin_positive(self):
        """Perform test delay margin positive operation."""
        dl = delay_loop()
        dl.delay(0.1)
        margin = dl.delay_margin()
        assert margin >= 0

    def test_achieved_loop_time(self):
        """Perform test achieved loop time operation."""
        dl = delay_loop()
        dl.delay(0.05)
        loop_time = dl.achieved_loop_time()
        assert loop_time >= 0.04
        assert loop_time < 0.15

    def test_callable(self):
        """Perform test callable operation."""
        dl = delay_loop()
        margin = dl(0.05)
        assert margin >= 0
        assert dl.get_count() == 1

    def test_strict_mode_raises_on_overrun(self):
        """Perform test strict mode raises on overrun operation."""
        dl = delay_loop(strict=True, begin=True)
        time.sleep(0.05)
        with pytest.raises(Exception, match="longer than requested"):
            dl.delay(0.01)

    def test_begin_false_requires_manual_begin(self):
        """Perform test begin false requires manual begin operation."""
        dl = delay_loop(begin=False)
        with pytest.raises(Exception, match="begin"):
            dl.delay(0.05)
        dl.begin()
        dl.delay(0.05)
        assert dl.get_count() == 1

    def test_no_drift_compensates(self):
        """Perform test no drift compensates operation."""
        dl = delay_loop(no_drift=True)
        dl.delay(0.05)
        dl.delay(0.05)
        total = dl.get_total_time()
        assert total < 0.15

    def test_time_remaining(self):
        """Perform test time remaining operation."""
        dl = delay_loop()
        remaining = dl.time_remaining(0.1)
        assert remaining > 0
        time.sleep(0.05)
        remaining2 = dl.time_remaining(0.1)
        assert remaining2 < remaining
