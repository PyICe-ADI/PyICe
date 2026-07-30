"""Tests for timer delta behavior — verifies read-before-pause prevents accumulation."""
import time
from PyICe.virtual_instruments import timer


class TestTimerDelta:
    def test_delta_does_not_accumulate_with_read_before_pause(self):
        """Each resume/read/pause cycle should report only that interval's delta."""
        t = timer()
        t.add_channel_delta_seconds('delta_s')
        t.add_channel_total_seconds('total_s')

        # Interval 1: ~0.3s
        t.resume_timer()
        time.sleep(0.3)
        data1 = t.read_all_channels()
        t.pause_timer()

        # Interval 2: ~0.3s
        time.sleep(0.05)  # paused gap — should not count
        t.resume_timer()
        time.sleep(0.3)
        data2 = t.read_all_channels()
        t.pause_timer()

        # Interval 3: ~0.3s
        t.resume_timer()
        time.sleep(0.3)
        data3 = t.read_all_channels()
        t.pause_timer()

        # Each delta should be ~0.3s, NOT accumulating
        assert 0.1 < data1['delta_s'] < 0.5
        assert 0.1 < data2['delta_s'] < 0.5
        assert 0.1 < data3['delta_s'] < 0.5
        # Specifically, interval 3 should NOT be ~0.9s (accumulated)
        assert data3['delta_s'] < 0.6

    def test_delta_accumulates_without_read(self):
        """Without reading between resume/pause cycles, delta grows (demonstrates the bug pattern)."""
        t = timer()
        t.add_channel_delta_seconds('delta_s')

        # Interval 1: pause without reading
        t.resume_timer()
        time.sleep(0.3)
        t.pause_timer()

        # Interval 2: pause without reading
        t.resume_timer()
        time.sleep(0.3)
        t.pause_timer()

        # Now read — delta reflects time since last _compute_delta (i.e., since first resume)
        data = t.read_all_channels()
        # The delta is ~0.6s because no read advanced last_time between intervals
        assert data['delta_s'] > 0.5