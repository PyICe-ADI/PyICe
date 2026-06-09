"""Tests for PartialReadException and per-delegator read isolation."""
import pytest
from PyICe.lab_core import (ChannelReadException, PartialReadException,
                            delegator)


class TestChannelReadException:
    """Tests for enriched ChannelReadException."""

    def test_stores_original_exception(self):
        """ChannelReadException preserves the original cause."""
        orig = ValueError("bad value")
        cre = ChannelReadException('READ_ERROR', original_exception=orig,
                                   original_traceback="tb line 1\ntb line 2")
        assert cre.original_exception is orig
        assert "tb line 1" in cre.original_traceback

    def test_backward_compat_no_kwargs(self):
        """ChannelReadException works with just a message."""
        cre = ChannelReadException('READ_ERROR')
        assert cre.original_exception is None
        assert cre.original_traceback is None
        assert str(cre) == 'READ_ERROR'

    def test_equality_still_works(self):
        """Equality comparison is unaffected by new fields."""
        a = ChannelReadException('READ_ERROR')
        b = ChannelReadException('READ_ERROR', original_exception=RuntimeError("x"))
        assert a == b

    def test_inequality_with_different_message(self):
        """Different messages are not equal."""
        a = ChannelReadException('READ_ERROR')
        b = ChannelReadException('TIMEOUT')
        assert a != b


class TestPartialReadException:
    """Tests for PartialReadException structure and message."""

    def test_contains_results_and_failures(self):
        """PartialReadException carries full results and failure subset."""
        results = {'ch_ok': 3.14, 'ch_bad': ChannelReadException('READ_ERROR')}
        failures = {'ch_bad': results['ch_bad']}
        exc = PartialReadException(results, failures)
        assert exc.results is results
        assert exc.failures is failures

    def test_message_includes_cause(self):
        """Exception message names the original cause."""
        orig = IOError("device timeout")
        cre = ChannelReadException('READ_ERROR', original_exception=orig)
        exc = PartialReadException({'ch': cre}, {'ch': cre})
        assert "IOError" in str(exc) or "OSError" in str(exc)
        assert "device timeout" in str(exc)

    def test_message_without_cause(self):
        """Exception message works when no original_exception set."""
        cre = ChannelReadException('READ_ERROR')
        exc = PartialReadException({'ch': cre}, {'ch': cre})
        assert "1 channel(s) failed" in str(exc)


class TestPartialReadInMaster:
    """Integration tests using master with virtual channels."""

    def test_all_channels_succeed(self, master_instance):
        """No exception when all reads succeed.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        m.add_channel_virtual('a', read_function=lambda: 1.0)
        m.add_channel_virtual('b', read_function=lambda: 2.0)
        results = m.read_channel_list([m['a'], m['b']])
        assert results['a'] == 1.0
        assert results['b'] == 2.0

    def test_failing_channel_raises_partial(self, master_instance):
        """A failing read_function raises PartialReadException.

        Args:
            master_instance: Master instance.
        """
        m = master_instance

        def bad_read():
            raise RuntimeError("instrument disconnected")

        m.add_channel_virtual('good', read_function=lambda: 42)
        m.add_channel_virtual('bad', read_function=bad_read)
        with pytest.raises(PartialReadException) as exc_info:
            m.read_channel_list([m['good'], m['bad']])
        exc = exc_info.value
        assert 'bad' in exc.failures
        assert isinstance(exc.results['bad'], ChannelReadException)
        assert exc.results['bad'].original_exception is not None
        assert "instrument disconnected" in str(exc.results['bad'].original_exception)

    def test_gui_pattern_catches_partial(self, master_instance):
        """GUI-style code recovers partial results from exception.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        m.add_channel_virtual('ok_ch', read_function=lambda: 99)
        m.add_channel_virtual('err_ch', read_function=lambda: (_ for _ in ()).throw(IOError("timeout")))
        try:
            results = m.read_channel_list([m['ok_ch'], m['err_ch']])
        except PartialReadException as e:
            results = e.results
        assert results['ok_ch'] == 99
        assert isinstance(results['err_ch'], ChannelReadException)

    def test_scripted_pattern_crashes(self, master_instance):
        """Scripted sessions crash with PartialReadException if uncaught.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        m.add_channel_virtual('x', read_function=lambda: (_ for _ in ()).throw(ValueError("oops")))
        with pytest.raises(PartialReadException):
            m.read_channel_list([m['x']])


class TestPerDelegatorIsolation:
    """Tests that failures in one delegator don't affect another."""

    def test_two_delegators_one_fails(self, master_instance):
        """Channels on a healthy delegator are preserved when another fails.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        m.add_channel_dummy('healthy_ch').write(7.5)
        m.add_channel_virtual('broken_ch',
                              read_function=lambda: (_ for _ in ()).throw(
                                  RuntimeError("bus error")))
        with pytest.raises(PartialReadException) as exc_info:
            m.read_channel_list([m['healthy_ch'], m['broken_ch']])
        exc = exc_info.value
        assert exc.results['healthy_ch'] == 7.5
        assert isinstance(exc.results['broken_ch'], ChannelReadException)
        assert 'broken_ch' in exc.failures
        assert 'healthy_ch' not in exc.failures

    def test_multiple_good_channels_preserved(self, master_instance):
        """Many good channels survive a single bad one.

        Args:
            master_instance: Master instance.
        """
        m = master_instance
        for i in range(5):
            m.add_channel_dummy(f'ok_{i}').write(i * 10)
        m.add_channel_virtual('fail',
                              read_function=lambda: (_ for _ in ()).throw(
                                  OSError("gone")))
        channels = [m[f'ok_{i}'] for i in range(5)] + [m['fail']]
        with pytest.raises(PartialReadException) as exc_info:
            m.read_channel_list(channels)
        exc = exc_info.value
        for i in range(5):
            assert exc.results[f'ok_{i}'] == i * 10
        assert isinstance(exc.results['fail'], ChannelReadException)
