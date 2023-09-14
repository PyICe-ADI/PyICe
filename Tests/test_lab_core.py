import pytest
from unittest.mock import patch
from PyICe.lab_core import channel, delegator, ChannelNameException, \
    ChannelAccessException, ChannelValueException, ChannelException
from PyICe.lab_core import integer_channel, channel_group, results_ord_dict


def read_function():
    return "Reading"


def write_function(write_val):
    return "Writing"


@pytest.fixture(scope='function')
def chan():
    return channel(name='empty_channel')


class TestChannelBaseFunctionality:

    def test_exception_read_write_defined(self):
        with pytest.raises(
                Exception):  # Ideally this would be a more specific exception
            c = channel(name='test', read_function=read_function,
                        write_function=write_function)

    def test_get_name(self, chan):
        assert chan.get_name() == "empty_channel"

    def test_set_name(self, chan):
        chan.set_name('new_name')
        assert chan.get_name() == 'new_name'

        with pytest.raises(ChannelNameException):
            chan.set_name('***')

    @pytest.mark.xfail
    def test_get_type_affinity(self, chan):  # should this have an exception?
        with pytest.raises(TypeError):
            chan._set_type_affinity('NOT_TYPE')

    def test_set_description(self, chan):
        assert chan is chan.set_description(
            'new description')  # how come? chaining commands?


class TestReadChannel:
    @pytest.fixture(scope='function')
    def chan_read(self):
        return channel(name='test', read_function=read_function)

    def test_read(self, chan_read):
        val = chan_read.read()
        assert val == "Reading"

    def test_read_without_delegator(self, chan_read):
        print(chan_read.read_without_delegator())

    def test_write(self, chan_read):
        with pytest.raises(ChannelAccessException):
            chan_read.write('test')

    @pytest.fixture
    def read_exception(self):
        def read_func():
            raise ValueError

        return channel(name='read_channel', read_function=read_func)

    @patch.object(delegator, 'unlock_interfaces')
    def test_exception_on_read(self, mock_unlock, read_exception):
        with pytest.raises(ValueError):
            read_exception.read()
        assert mock_unlock.called

    def test_add_preset_read_exception(self, chan_read):
        with pytest.raises(ChannelAccessException):
            chan_read.add_preset('TEST')


class TestWriteChannel:
    @pytest.fixture(scope='function')
    def simple_write(self):
        return channel(name='write_test', write_function=write_function)

    @pytest.mark.parametrize('write_arg', [1, 33.2, 'WOW', [1], (0, 0)])
    def test_write(self, write_arg, simple_write):
        assert simple_write.write(write_arg) == write_arg

    def test_write_history(self, simple_write):
        for val in range(0, 9):
            simple_write.write(val)
        assert simple_write.get_write_history() == list(range(0, 9))

        for val in range(0, 20):
            simple_write.write(val)
        assert simple_write.get_write_history() == list(range(10, 20))

    def test_set_max_write_limit(self, simple_write):
        simple_write.set_max_write_limit(10)
        assert simple_write._write_max == 10
        assert type(simple_write._write_max) is float
        simple_write.set_max_write_limit(None)
        assert simple_write._write_max is None

        with pytest.raises(Exception):
            simple_write.set_min_write_limit(" Not a num")

    @patch.object(delegator, 'unlock_interfaces')
    def test_write_above_max_limit(self, mock_unlock, simple_write):
        simple_write.set_max_write_limit(10)
        with pytest.raises(ChannelValueException):
            simple_write.write(11)
        assert mock_unlock.called

    @patch.object(delegator, 'unlock_interfaces')
    def test_write_below_min_limit(self, mock_unlock, simple_write):
        simple_write.set_min_write_limit(0)
        with pytest.raises(ChannelValueException):
            simple_write.write(-2)
        assert mock_unlock.called

    @pytest.fixture
    def write_exception(self):
        def write_func(val):
            raise ValueError

        return channel(name='write_channel', write_function=write_func)

    @patch.object(delegator, 'unlock_interfaces')
    def test_exception_on_write(self, mock_unlock, write_exception):
        with pytest.raises(ValueError):
            write_exception.write(3)
        assert mock_unlock.called

    def test_get_max_write_limit(self, simple_write):
        simple_write.set_max_write_limit(999)
        assert simple_write.get_max_write_limit() == 999

    def test_set_min_write_limit(self, simple_write):
        simple_write.set_min_write_limit(5)
        assert simple_write._write_min == 5
        assert type(simple_write._write_min) is float
        simple_write.set_min_write_limit(None)
        assert simple_write._write_min is None

        with pytest.raises(Exception):
            simple_write.set_min_write_limit(" Not a num")

    def test_get_min_write_limit(self, simple_write):
        simple_write.set_min_write_limit(1)
        assert simple_write.get_min_write_limit() == 1

    def test_set_max_write_warning(self, simple_write):
        simple_write.set_max_write_warning(10)
        assert simple_write._write_max_warning == 10
        assert type(simple_write._write_max_warning) is float
        simple_write.set_max_write_warning(None)
        assert simple_write._write_max_warning is None

        with pytest.raises(Exception):
            simple_write.test_set_max_write_warning("Not a num")

    def test_get_max_write_warning(self, simple_write):
        simple_write.set_max_write_warning(99)
        assert simple_write.get_max_write_warning() == 99

    def test_set_min_write_warning(self, simple_write):
        simple_write.set_min_write_warning(5)
        assert simple_write._write_min_warning == 5
        assert type(simple_write._write_min_warning) is float
        simple_write.set_min_write_warning(None)
        assert simple_write._write_min_warning is None

        with pytest.raises(Exception):
            simple_write.set_min_write_warning(" Not a num")

    def test_get_min_write_warning(self, simple_write):
        simple_write.set_min_write_warning(1)
        assert simple_write.get_min_write_warning() == 1

    def test_format_display(self, simple_write):
        data_str = simple_write.format_display(1)
        assert type(data_str) is str

    def test_set_display_format_str(self, simple_write):
        simple_write.set_display_format_str(2, 1, 3)
        assert simple_write._display_format_str == '1{:2}3'

    def test_get_min_write_warning(self, simple_write):
        simple_write.set_min_write_warning(30)
        assert simple_write.get_min_write_warning() == 30

    def test_get_channel_write_delay(self, simple_write):
        delay = simple_write.get_write_delay()
        assert delay == 0  # default write delay

    def test_read_exception(self, simple_write):
        simple_write.set_read_access(False)
        with pytest.raises(ChannelAccessException):
            simple_write.read()

    def test_add_preset(self, simple_write):
        simple_write.add_preset('TEST')
        with pytest.raises(ChannelException):
            simple_write.add_preset('TEST')

    def test_set_write_resolution(self, simple_write):
        simple_write.set_write_resolution(decimal_digits=9)
        assert simple_write._write_resolution == 9
        with pytest.raises(AssertionError):
            simple_write.set_write_resolution(decimal_digits=1.2)


def int_read_func():
    return 10


def int_write_func(val):
    return "writing"


@pytest.fixture(scope='function', params=[1, 5])
def int_read_chan(request):
    return integer_channel(name='int_read_channel',
                           size=request.param,
                           read_function=int_read_func)


@pytest.fixture(scope='function')
def int_write_chan():
    return integer_channel(name='int_write_channel',
                           size=5,
                           write_function=int_write_func)


class TestIntegerReadChannel:

    def test_get_size(self, int_read_chan):
        assert int_read_chan.get_size() == 5

    def test_get_max_write_limit(self, int_write_chan):
        int_write_chan.set_max_write_limit(10)
        assert int_write_chan.get_max_write_limit() == 10

    def test_get_min_write_limit(self, int_read_chan):
        int_write_chan.set_min_write_limit(10)
        assert int_write_chan.get_min_write_limit() == 10

    def test_add_preset(self, int_read_chan):
        int_read_chan.add_preset(preset_name='TEST_PRESET',
                                 preset_value=1)
        int_read_chan.add_preset(preset_name='TEST_PRESET2',
                                 preset_value=2)
        with pytest.raises(Exception):
            int_read_chan.add_preset(preset_name='TEST_PRESET3',
                                     preset_value=2.1)
        with pytest.raises(Exception):
            int_read_chan.add_preset(preset_name='TEST_PRESET',
                                     preset_value=3)
        int_read_chan.add_preset(preset_name='TEST_PRESET4', preset_value=4)

    @pytest.mark.parametrize('format_type', ['dec',
                                             'hex',
                                             'bin',
                                             'signed dec'])
    def test_set_format(self, format_type, int_read_chan):
        if int_read_chan.get_size() == 1:
            with pytest.raises(Exception):
                int_read_chan.set_format(format_type)

        elif int_read_chan.get_size() == 5:
            assert int_read_chan.set_format(format_type)

    @pytest.mark.parametrize('format_type', ['dec',
                                             'hex',
                                             'bin',
                                             'signed dec'])
    def test_get_format(self, format_type, int_read_chan):
        if int_read_chan.get_size() == 1:
            pass
        else:
            int_read_chan.set_format(format_type)
            assert int_read_chan.get_format() == format_type

    @pytest.mark.parametrize('data', [0, 4, 128, 1024, 89])
    @pytest.mark.parametrize('format', ['dec', 'hex', 'bin'])
    def test_format(self, data, format, int_write_chan):
        print(int_write_chan.format(data, format, use_presets=True))

    @pytest.mark.xfail
    @pytest.mark.parametrize('data', [bin(1)])
    def test_format_signed_dec(self, data, int_write_chan):
        print(int_write_chan.format(data, 'signed dec', use_presets=True))

    def test_sql_format(self):
        assert False

    def test_unformat_string(self, int_write_chan):
        assert int_write_chan.unformat(string=None, format='dec',
                                       use_presets=False) is None

    def test_unformat_use_presets(self, int_write_chan):
        int_write_chan.add_preset('ONE', 1)
        int_write_chan.add_preset('TWO', 2)
        assert int_write_chan.unformat(string='ONE', format='dec',
                                       use_presets=True) == 1
        assert int_write_chan.unformat(string='TWO', format='dec',
                                       use_presets=True) == 2
        with pytest.raises(ValueError):
            int_write_chan.unformat(string='HELP', format='dec',
                                    use_presets=True)

    @pytest.mark.parametrize('out_format, in_val, out_val', [('dec', 10, 10),
                                                             (
                                                                     'hex',
                                                                     '0xA',
                                                                     10),
                                                             ('bin', '0b1010',
                                                              10)])
    def test_unformat_specify_format(self, out_format, in_val, out_val,
                                     int_write_chan):

        int_write_chan.add_preset('ONE', out_val)
        assert int_write_chan.unformat(string=in_val, format=out_format,
                                       use_presets=False) == out_val

    @pytest.mark.parametrize('format_type, result', [('dec', '10'),
                                                     ('hex', '0x0A'),
                                                     ('bin', '0b01010'),
                                                     ('signed dec', '10')
                                                     ])
    def test_format_read(self, format_type, result, int_read_chan):
        if int_read_chan.get_size() != 1:
            int_read_chan.set_format(format_type)
            assert int_read_chan.format_read(10) == result

    @pytest.mark.parametrize('format_type, result', [('dec', '10'),
                                                     ('hex', '0x0A'),
                                                     ('bin', '0b01010'),
                                                     ('signed dec', '10')
                                                     ])
    def test_format_write(self, format_type, result, int_write_chan):
        int_write_chan.set_format(format_type)
        assert int_write_chan.format_write(result) == 10

    def test_write_size_1(self, int_write_chan):
        chan = integer_channel('TEST', size=1,
                               write_function=write_function)
        assert chan.write(True)
        assert not chan.write(False)

    @pytest.mark.parametrize('format_type, result', [('dec', '10'),
                                                     ('hex', '0x0A'),
                                                     ('bin', '0b01010'),
                                                     ('signed dec', '10'),
                                                     (None, None)
                                                     ])
    def test_write_size_greater_1(self, format_type, result, int_write_chan):
        int_write_chan.set_format(format_type)
        if result is None:
            assert int_write_chan.write(result) is None
        else:
            assert int_write_chan.write(result) == 10

    def test_write_unformatted_size_1(self, int_write_chan):
        chan = integer_channel('TEST', size=1,
                               write_function=write_function)
        assert chan.write_unformatted(True)
        assert not chan.write_unformatted(False)

    @pytest.mark.parametrize('data', [10, 1.1])
    def test_write_unformatted_size_greater_1(self, data, int_write_chan):
        assert int_write_chan.write_unformatted(data) == int(data)


@pytest.fixture(scope='function')
def group():
    c = channel_group(name='New Group')
    return c

@pytest.fixture
def loaded_group_w_channels(group):
    sub_group1 = channel_group('subg1')
    sub_group2 = channel_group('subg2')

    sub_group1.add(c1 := channel(name=f'chan0',
                                 write_function=write_function))
    sub_group2.add(c2 := channel(name=f'chan1',
                                 write_function=write_function))
    c1.set_category('cat1')
    c2.set_category('cat2')
    group.add(sub_group1)
    group.add(sub_group2)
    group.add(c3 := channel(name='chan2', read_function=read_function))
    return group, [c1, c2, c3]

@pytest.fixture
def loaded_group(loaded_group_w_channels):
    g, chans = loaded_group_w_channels
    return g

@pytest.fixture
def thread_group(group):
    group.add(c0 := channel(name='chan0',
                            read_function=read_function))
    group.add(c1 := channel(name='chan1',
                            read_function=read_function))
    c1.set_allow_threading(False)
    group.add(c2 := channel(name='chan2',
                            read_function=read_function))
    c2.set_allow_threading(False)
    group.add(c3 := channel(name='chan3',
                            read_function=read_function))
    group.add(c4 := channel(name='chan4',
                            write_function=write_function))
    return group, [c0, c1, c2, c3, c4]

class TestChannelGroup:
    # def test_copy(self):
    #     assert False

    def test_get_name(self, group):
        assert group.get_name() == 'New Group'

    def test_set_name(self, group):
        group.set_name('New Name')
        assert group.get_name() == 'New Name'

    def test_get_categories(self):
        assert False

    def test_sort(self):
        assert False

    def read_func1(self):
        return 1

    def read_func2(self):
        return 2

    def test_add(self, group):
        c1 = channel(name='read1', read_function=self.read_func1)
        c2 = channel(name='read2', read_function=self.read_func2)
        l1 = [w1 := channel(name='write1', write_function=write_function),
              # walrus!!
              w2 := channel(name='write2', write_function=write_function)]
        g1 = channel_group(name='Group1')
        assert group.add(c1) is c1
        assert c1 in group
        assert group.add(c2) is c2
        assert c2 in group
        assert group.add(g1) is g1
        group.add(l1)
        assert w1 in group
        assert w2 in group
        with pytest.raises(TypeError):
            group.add(0)

    def test__add_channel(self, group, chan):
        assert chan is group._add_channel(chan)
        with pytest.raises(Exception):
            group._add_channel(0)
        group2 = channel_group('Group 2')
        group2.add(c := channel(name='new_channel'))
        assert chan is group._add_channel(chan)
        group.add(group2)
        with pytest.raises(Exception):
            group.add(c)

    def test_merge_in_channel_group(self, group):
        new_group = channel_group('new')
        new_group.add([
            c1 := channel(name='c1'),
            c2 := channel(name='c2'),
            c3 := channel(name='c3'),
        ])
        group.merge_in_channel_group(new_group)
        assert c1 in group
        assert c2 in group
        assert c3 in group
        with pytest.raises(Exception):
            group.merge_in_channel_group('Type')

    def test__add_sub_channel_group(self, group):
        with pytest.raises(Exception):
            group._add_sub_channel_group(0)
        group1 = channel_group('group1')
        group1.add([
            c1 := channel(name='c1'),
            c2 := channel(name='c2'),
        ])
        group2 = channel_group('group2')
        group2.add(
            c2_repeat := channel(name='c2'),
        )
        group._add_sub_channel_group(group1)
        with pytest.raises(Exception):
            group._add_sub_channel_group(group2)

    def test_get_channel_groups(self, group):
        group.add(g1 := channel_group('name_test'))
        group.add(g2 := channel_group('name_test'))
        groups = group.get_channel_groups()
        assert groups == [g1, g2]

    def test_read(self, group):
        group.add(c1 := channel(name='test_channel',
                                read_function=read_function))
        assert group.read('test_channel') == 'Reading'
        with pytest.raises(ChannelAccessException):
            group.read(None)

    def test_write(self, group):
        group.add(c1 := channel(name='test_channel',
                                write_function=write_function))
        assert group.write('test_channel', 6) == 6

    def test_read_channels(self, group):
        chan_names = []
        for i in range(4):
            group.add(channel(name=f'chan{i}',
                              read_function=read_function))
            chan_names.append(f'chan{i}');
        result = group.read_channels(chan_names)
        assert result == {
            'chan0': 'Reading',
            'chan1': 'Reading',
            'chan2': 'Reading',
            'chan3': 'Reading',
        }

    def test_write_channels(self, group):
        chan_names = []
        for i in range(4):
            group.add(channel(name=f'chan{i}',
                              write_function=write_function))
            chan_names.append(f'chan{i}')
        result = group.write_channels([
            ('chan1', 1),
            ('chan2', 2),
            ('chan2', 3),
        ])
        assert result == [1, 2, 3]

    def test_get_channel(self, group):
        with pytest.raises(ChannelAccessException):
            group.get_channel('doesnt_exhist')

    def test_get_flat_channel_group(self, group):
        sub_group1 = channel_group('subg1')
        sub_group2 = channel_group('subg2')

        sub_group1.add(c1 := channel(name=f'chan0',
                                     write_function=write_function))
        sub_group2.add(c2 := channel(name=f'chan1',
                                     write_function=write_function))
        group.add(sub_group1)
        group.add(sub_group2)
        new_group = group.get_flat_channel_group()
        assert c1 in new_group
        assert c2 in new_group

    def test__resolve_channel(self, group):
        sub_group1 = channel_group('subg1')
        sub_group1.add(c1 := channel(name=f'chan0',
                                     write_function=write_function))
        group.add(sub_group1)
        assert group._resolve_channel('chan0') is c1


    def test_get_all_channels_dict(self, loaded_group):
        chans = loaded_group.get_all_channels_dict()
        assert 'chan0' in chans
        assert 'chan1' in chans
        assert 'chan2' in chans

        chans_filtered = loaded_group.get_all_channels_dict(
            categories=['cat1'])
        assert 'chan0' in chans_filtered
        assert 'chan1' not in chans_filtered
        assert 'chan2' not in chans_filtered

    def test_get_all_channel_names(self, loaded_group):
        chans = loaded_group.get_all_channel_names()
        assert 'chan0' in chans
        assert 'chan1' in chans
        assert 'chan2' in chans

        chans_filtered = loaded_group.get_all_channel_names(
            categories=['cat1'])
        assert 'chan0' in chans_filtered
        assert 'chan1' not in chans_filtered
        assert 'chan2' not in chans_filtered

    def test_get_all_channels_list(self, loaded_group_w_channels):
        group, (c1, c2, c3) = loaded_group_w_channels
        chan_list = group.get_all_channels_list()
        assert c1 in chan_list
        assert c2 in chan_list
        assert c3 in chan_list
        chan_list = group.get_all_channels_list(categories=['cat2'])
        assert c1 not in chan_list
        assert c2 in chan_list
        assert c3 not in chan_list

    def test_get_all_channels_set(self, loaded_group_w_channels):
        group, (c1, c2, c3) = loaded_group_w_channels
        chan_list = group.get_all_channels_list()
        assert c1 in chan_list
        assert c2 in chan_list
        assert c3 in chan_list


    def test_read_channel_list(self, thread_group):
        group, (c0, c1, c2, c3, c4) = thread_group
        results = group.read_channel_list([c0, c1, c2, c3])
        # non threaded
        assert results['chan0'] == 'Reading'
        assert results['chan1'] == 'Reading'
        assert results['chan2'] == 'Reading'
        assert results['chan3'] == 'Reading'

    @pytest.mark.skip  # these will be covered in channel_master tests
    def test__read_channels_non_threaded(self):
        assert False

    @pytest.mark.skip  # these will be covered in channel_master tests
    def test__read_channels_threaded(self):
        assert False

    @pytest.mark.skip  # these will be covered in channel_master tests
    def test_start_threads(self):
        assert False

    @pytest.mark.skip  # these will be covered in channel_master tests
    def test_threaded_read_function(self):
        assert False

    @pytest.mark.skip  # these will be covered in channel_master tests
    def test_get_threaded_results(self):
        assert False

    def test_read_all_channels(self, thread_group):
        group, channels = thread_group
        data = group.read_all_channels()
        assert 'chan0' in data
        assert 'chan1' in data
        assert 'chan2' in data
        assert 'chan3' in data
        assert 'chan4' in data

    def test_remove_channel(self, thread_group):
        group, channels = thread_group
        group.remove_channel(channels[0])

        chan = channels[1]
        chan.set_name('Notthere')
        assert channels[0] not in group
        with pytest.raises(Exception):
            group.remove_channel(chan)

    @pytest.mark.xfail  # This one does not work because if you remove a channel group
    def test_remove_channel_group(self, group):
        sub_group1 = channel_group('subg1')
        sub_group2 = channel_group('subg2')

        sub_group1.add(c1 := channel(name=f'chan0',
                                     write_function=write_function))
        sub_group2.add(c2 := channel(name=f'chan1',
                                     write_function=write_function))
        group.add(sub_group1)
        group.add(sub_group2)

        group.remove_channel_group(sub_group1)

    # @pytest.mark.xfail  # This one does not work because if you remove a channel group
    def test_remove_channel_by_name(self, loaded_group):
        loaded_group.add(c1 := channel(name='remove_chan'))
        assert c1 in loaded_group
        loaded_group.remove_channel_by_name('remove_chan')
        assert c1 not in loaded_group

    def test_remove_all_channels_and_sub_groups(self, loaded_group):
        loaded_group.remove_all_channels_and_sub_groups()
        assert not loaded_group._channel_dict
        assert not loaded_group._sub_channel_groups

    def test_remove_sub_channel_group(self, loaded_group):
        sub_group = loaded_group._sub_channel_groups[0]
        loaded_group.remove_sub_channel_group(sub_group)
        assert sub_group not in loaded_group

    def test_remove_category(self):
        assert False

    def test_remove_categories(self):
        assert False

    def test_debug_print(self):
        assert False

    def test_remove_channel_list(self):
        assert False

    def test_resolve_channel_list(self):
        assert False

    def test_clone(self):
        assert False

