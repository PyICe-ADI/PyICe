import time
import pytest
from PyICe.lab_core import (channel_master, channel, integer_channel,
                            results_ord_dict)
from PyICe.lab_interfaces import interface_factory


class TestChannelMasterFactoryMethods:

    def test_add_channel_dummy(self, master_instance):
        ch = master_instance.add_channel_dummy('my_dummy')
        ch.write(3.14)
        assert ch.read() == 3.14

    def test_add_channel_dummy_integer(self, master_instance):
        ch = master_instance.add_channel_dummy('my_int_dummy', integer_size=8)
        assert isinstance(ch, integer_channel)
        ch.write(200)
        assert ch.read() == 200
        assert ch.get_size() == 8

    def test_add_channel_dummy_none_default(self, master_instance):
        ch = master_instance.add_channel_dummy('empty')
        assert ch.read() is None

    def test_add_channel_virtual_read(self, master_instance):
        call_count = [0]

        def read_fn():
            call_count[0] += 1
            return 42

        ch = master_instance.add_channel_virtual('virt', read_function=read_fn)
        assert ch.read() == 42
        assert call_count[0] == 1

    def test_add_channel_virtual_write(self, master_instance):
        written = []

        def write_fn(v):
            written.append(v)

        ch = master_instance.add_channel_virtual('virt_w',
                                                 write_function=write_fn)
        ch.write(10)
        assert written == [10]
        assert ch.read() == 10

    def test_add_channel_virtual_integer(self, master_instance):
        ch = master_instance.add_channel_virtual('virt_int',
                                                 read_function=lambda: 5,
                                                 integer_size=4)
        assert isinstance(ch, integer_channel)
        assert ch.get_size() == 4
        assert ch.read() == 5

    def test_add_channel_virtual_caching_sets_delegator(self, master_instance):
        ch = master_instance.add_channel_virtual_caching(
            'cached', read_function=lambda: 77)
        assert ch.get_delegator() is master_instance

    def test_add_channel_delta_timer(self, master_instance):
        ch = master_instance.add_channel_delta_timer('dt')
        ch.read()
        time.sleep(0.05)
        second = ch.read()
        assert second > 0
        assert second >= 0.04

    def test_add_channel_total_timer(self, master_instance):
        ch = master_instance.add_channel_total_timer('total')
        t0 = ch.read()
        time.sleep(0.05)
        t1 = ch.read()
        assert t1 > t0
        assert t1 >= 0.04

    def test_add_channel_counter_default(self, master_instance):
        ch = master_instance.add_channel_counter('cnt')
        assert ch.read() == 0
        assert ch.read() == 1
        assert ch.read() == 2

    def test_add_channel_counter_custom_init_inc(self, master_instance):
        ch = master_instance.add_channel_counter('cnt2', init=10, inc=5)
        assert ch.read() == 10
        assert ch.read() == 15
        assert ch.read() == 20

    def test_add_channel_counter_write_resets(self, master_instance):
        ch = master_instance.add_channel_counter('cnt3')
        ch.read()  # 0
        ch.read()  # 1
        ch.write(100)
        assert ch.read() == 101


class TestChannelMasterCaching:

    def test_caching_channel_uses_cached_value(self, master_instance):
        m = master_instance
        call_count = [0]

        def expensive_read():
            call_count[0] += 1
            return 99

        m.add_channel_virtual('source', read_function=expensive_read)

        def cached_read():
            return m.read_channel('source') * 2

        m.add_channel_virtual_caching('derived', read_function=cached_read)

        results = m.read_all_channels()
        assert results['source'] == 99
        assert results['derived'] == 198
        assert call_count[0] == 1

    def test_caching_mode_resets_after_read(self, master_instance):
        m = master_instance
        m.add_channel_dummy('ch1')
        m['ch1'].write(5)
        m.read_all_channels()
        assert m._caching_mode == 0


class TestChannelMasterCallbacks:

    def test_add_read_callback(self, master_instance):
        m = master_instance
        m.add_channel_dummy('cb_ch')
        m['cb_ch'].write(7)
        received = []
        m.add_read_callback(lambda data: received.append(data))
        m.read_channel('cb_ch')
        assert len(received) == 1
        assert received[0]['cb_ch'] == 7

    def test_remove_read_callback(self, master_instance):
        m = master_instance
        m.add_channel_dummy('cb_ch')
        m['cb_ch'].write(1)
        received = []
        cb = lambda data: received.append(data)
        m.add_read_callback(cb)
        m.read_channel('cb_ch')
        m.remove_read_callback(cb)
        m.read_channel('cb_ch')
        assert len(received) == 1

    def test_add_write_callback(self, master_instance):
        m = master_instance
        m.add_channel_dummy('wch')
        received = []
        m.add_write_callback(lambda data: received.append(data))
        m.write_channel('wch', 42)
        assert len(received) == 1
        assert received[0]['wch'] == 42

    def test_remove_write_callback(self, master_instance):
        m = master_instance
        m.add_channel_dummy('wch')
        received = []
        cb = lambda data: received.append(data)
        m.add_write_callback(cb)
        m.write_channel('wch', 1)
        m.remove_write_callback(cb)
        m.write_channel('wch', 2)
        assert len(received) == 1


class TestChannelMasterThreading:

    @pytest.mark.threading
    def test_threaded_read_multiple_channels(self, master_instance):
        m = master_instance
        for i in range(5):
            m.add_channel_virtual(f'tch{i}', read_function=lambda i=i: i * 10)
        results = m.read_all_channels()
        for i in range(5):
            assert results[f'tch{i}'] == i * 10

    @pytest.mark.threading
    def test_non_threadable_channel(self, master_instance):
        m = master_instance
        ch = m.add_channel_virtual('no_thread', read_function=lambda: 'seq')
        ch.set_allow_threading(False)
        results = m.read_all_channels()
        assert results['no_thread'] == 'seq'

    @pytest.mark.threading
    def test_read_exception_propagates(self, master_instance):
        m = master_instance

        def bad_read():
            raise ValueError("simulated failure")

        m.add_channel_virtual('bad', read_function=bad_read)
        with pytest.raises(ValueError, match="simulated failure"):
            m.read_all_channels()


class TestMaster:

    def test_master_inherits_channel_master(self, master_instance):
        assert isinstance(master_instance, channel_master)

    def test_master_inherits_interface_factory(self, master_instance):
        assert isinstance(master_instance, interface_factory)

    def test_get_twi_dummy_interface(self, master_instance):
        iface = master_instance.get_twi_dummy_interface()
        assert iface is not None

    def test_get_dummy_clone(self, master_with_dummies):
        m = master_with_dummies
        clone = m.get_dummy_clone()
        clone_names = clone.get_all_channel_names()
        assert 'dummy_float' in clone_names
        assert 'dummy_int' in clone_names
        assert 'dummy_plain' in clone_names

    def test_read_all_channels_returns_results_ord_dict(self, master_with_dummies):
        results = master_with_dummies.read_all_channels()
        assert isinstance(results, results_ord_dict)
        assert results['dummy_float'] == 3.14
        assert results['dummy_int'] == 42


class TestResultsOrdDict:

    def test_is_ordered_dict(self):
        from collections import OrderedDict
        r = results_ord_dict()
        assert isinstance(r, OrderedDict)

    def test_str_formatting(self):
        r = results_ord_dict()
        r['voltage'] = 3.3
        r['current'] = 0.001
        s = str(r)
        assert 'voltage' in s
        assert 'current' in s

    def test_getstate(self):
        r = results_ord_dict()
        r['a'] = 1
        assert r.__getstate__() == {}
