"""Tests for lab core."""
import queue
import pytest
from unittest.mock import patch
from PyICe.lab_core import channel, delegator, ChannelNameException, \
    ChannelAccessException, ChannelValueException, ChannelException
from PyICe.lab_core import integer_channel, channel_group, results_ord_dict


def read_function():
    """Return read function result.

    Returns:
        Result value.
    """
    return "Reading"


def write_function(write_val):
    """Return write function result.

    Args:
        write_val: Write val.

    Returns:
        Result value.
    """
    return "Writing"


@pytest.fixture(scope='function')
def chan():
    """Return chan result.

    Returns:
        Result value.
    """
    return channel(name='empty_channel')


class TestChannelBaseFunctionality:
    """Tests for Channel Base Functionality."""

    def test_exception_read_write_defined(self):
        """Perform test exception read write defined operation."""
        with pytest.raises(
                Exception):  # Ideally this would be a more specific exception
            _c = channel(name='test', read_function=read_function,  # noqa: F841
                         write_function=write_function)

    def test_get_name(self, chan):
        """Perform test get name operation.

        Args:
            chan: Chan.
        """
        assert chan.get_name() == "empty_channel"

    def test_set_name(self, chan):
        """Perform test set name operation.

        Args:
            chan: Chan.
        """
        chan.set_name('new_name')
        assert chan.get_name() == 'new_name'

        with pytest.raises(ChannelNameException):
            chan.set_name('***')

    # permissive by design: value is interpolated directly into SQLite CREATE
    # TABLE, which accepts any affinity string (unknown types fall back to
    # BLOB). PyICeBLOB is an intentional custom affinity used throughout the
    # codebase.
    def test_get_type_affinity(self, chan):
        """Perform test get type affinity operation.

        Args:
            chan: Chan.
        """
        chan._set_type_affinity('NOT_TYPE')
        assert chan.get_type_affinity() == 'NOT_TYPE'

    def test_set_description(self, chan):
        """Perform test set description operation.

        Args:
            chan: Chan.
        """
        assert chan is chan.set_description(
            'new description')  # how come? chaining commands?


class TestReadChannel:
    """Tests for Read Channel."""
    @pytest.fixture(scope='function')
    def chan_read(self):
        """Return chan read result.

        Returns:
            Result value.
        """
        return channel(name='test', read_function=read_function)

    def test_read(self, chan_read):
        """Perform test read operation.

        Args:
            chan_read: Chan read.
        """
        val = chan_read.read()
        assert val == "Reading"

    def test_read_without_delegator(self, chan_read):
        """Perform test read without delegator operation.

        Args:
            chan_read: Chan read.
        """
        print(chan_read.read_without_delegator())

    def test_write(self, chan_read):
        """Perform test write operation.

        Args:
            chan_read: Chan read.
        """
        with pytest.raises(ChannelAccessException):
            chan_read.write('test')

    @pytest.fixture
    def read_exception(self):
        """Return read exception result.

        Returns:
            Result value.
        """
        def read_func():
            """Raise ValueError to simulate a read failure.

            Raises:
                ValueError: Always raised.
            """
            raise ValueError

        return channel(name='read_channel', read_function=read_func)

    @patch.object(delegator, 'unlock_interfaces')
    def test_exception_on_read(self, mock_unlock, read_exception):
        """Perform test exception on read operation.

        Args:
            mock_unlock: Mock unlock.
            read_exception: Read exception.
        """
        with pytest.raises(ValueError):
            read_exception.read()
        assert mock_unlock.called

    def test_add_preset_read_exception(self, chan_read):
        """Perform test add preset read exception operation.

        Args:
            chan_read: Chan read.
        """
        with pytest.raises(ChannelAccessException):
            chan_read.add_preset('TEST')


class TestWriteChannel:
    """Tests for Write Channel."""
    @pytest.fixture(scope='function')
    def simple_write(self):
        """Return simple write result.

        Returns:
            Result value.
        """
        return channel(name='write_test', write_function=write_function)

    @pytest.mark.parametrize('write_arg', [1, 33.2, 'WOW', [1], (0, 0)])
    def test_write(self, write_arg, simple_write):
        """Perform test write operation.

        Args:
            simple_write: Simple write.
            write_arg: Write arg.
        """
        assert simple_write.write(write_arg) == write_arg

    def test_write_history(self, simple_write):
        """Perform test write history operation.

        Args:
            simple_write: Simple write.
        """
        for val in range(0, 9):
            simple_write.write(val)
        assert simple_write.get_write_history() == list(range(0, 9))

        for val in range(0, 20):
            simple_write.write(val)
        assert simple_write.get_write_history() == list(range(10, 20))

    def test_set_max_write_limit(self, simple_write):
        """Perform test set max write limit operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_max_write_limit(10)
        assert simple_write._write_max == 10
        assert type(simple_write._write_max) is float
        simple_write.set_max_write_limit(None)
        assert simple_write._write_max is None

        with pytest.raises(Exception):
            simple_write.set_min_write_limit(" Not a num")

    @patch.object(delegator, 'unlock_interfaces')
    def test_write_above_max_limit(self, mock_unlock, simple_write):
        """Perform test write above max limit operation.

        Args:
            mock_unlock: Mock unlock.
            simple_write: Simple write.
        """
        simple_write.set_max_write_limit(10)
        with pytest.raises(ChannelValueException):
            simple_write.write(11)
        assert mock_unlock.called

    @patch.object(delegator, 'unlock_interfaces')
    def test_write_below_min_limit(self, mock_unlock, simple_write):
        """Perform test write below min limit operation.

        Args:
            mock_unlock: Mock unlock.
            simple_write: Simple write.
        """
        simple_write.set_min_write_limit(0)
        with pytest.raises(ChannelValueException):
            simple_write.write(-2)
        assert mock_unlock.called

    @pytest.fixture
    def write_exception(self):
        """Return write exception result.

        Returns:
            Result value.
        """
        def write_func(val):
            """Perform write func operation.

            Args:
                val: Val.

            Raises:
                ValueError: Always raised.
            """
            raise ValueError

        return channel(name='write_channel', write_function=write_func)

    @patch.object(delegator, 'unlock_interfaces')
    def test_exception_on_write(self, mock_unlock, write_exception):
        """Perform test exception on write operation.

        Args:
            mock_unlock: Mock unlock.
            write_exception: Write exception.
        """
        with pytest.raises(ValueError):
            write_exception.write(3)
        assert mock_unlock.called

    def test_get_max_write_limit(self, simple_write):
        """Perform test get max write limit operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_max_write_limit(999)
        assert simple_write.get_max_write_limit() == 999

    def test_set_min_write_limit(self, simple_write):
        """Perform test set min write limit operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_min_write_limit(5)
        assert simple_write._write_min == 5
        assert type(simple_write._write_min) is float
        simple_write.set_min_write_limit(None)
        assert simple_write._write_min is None

        with pytest.raises(Exception):
            simple_write.set_min_write_limit(" Not a num")

    def test_get_min_write_limit(self, simple_write):
        """Perform test get min write limit operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_min_write_limit(1)
        assert simple_write.get_min_write_limit() == 1

    def test_set_max_write_warning(self, simple_write):
        """Perform test set max write warning operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_max_write_warning(10)
        assert simple_write._write_max_warning == 10
        assert type(simple_write._write_max_warning) is float
        simple_write.set_max_write_warning(None)
        assert simple_write._write_max_warning is None

        with pytest.raises(Exception):
            simple_write.test_set_max_write_warning("Not a num")

    def test_get_max_write_warning(self, simple_write):
        """Perform test get max write warning operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_max_write_warning(99)
        assert simple_write.get_max_write_warning() == 99

    def test_set_min_write_warning(self, simple_write):
        """Perform test set min write warning operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_min_write_warning(5)
        assert simple_write._write_min_warning == 5
        assert type(simple_write._write_min_warning) is float
        simple_write.set_min_write_warning(None)
        assert simple_write._write_min_warning is None

        with pytest.raises(Exception):
            simple_write.set_min_write_warning(" Not a num")

    def test_get_min_write_warning(self, simple_write):
        """Perform test get min write warning operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_min_write_warning(1)
        assert simple_write.get_min_write_warning() == 1

    def test_format_display(self, simple_write):
        """Perform test format display operation.

        Args:
            simple_write: Simple write.
        """
        data_str = simple_write.format_display(1)
        assert type(data_str) is str

    def test_set_display_format_str(self, simple_write):
        """Perform test set display format str operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_display_format_str(2, 1, 3)
        assert simple_write._display_format_str == '1{:2}3'

    def test_get_min_write_warning_2(self, simple_write):
        """Perform test get min write warning 2 operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_min_write_warning(30)
        assert simple_write.get_min_write_warning() == 30

    def test_get_channel_write_delay(self, simple_write):
        """Perform test get channel write delay operation.

        Args:
            simple_write: Simple write.
        """
        delay = simple_write.get_write_delay()
        assert delay == 0  # default write delay

    def test_read_exception(self, simple_write):
        """Perform test read exception operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_read_access(False)
        with pytest.raises(ChannelAccessException):
            simple_write.read()

    def test_add_preset(self, simple_write):
        """Perform test add preset operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.add_preset('TEST')
        with pytest.raises(ChannelException):
            simple_write.add_preset('TEST')

    def test_set_write_resolution(self, simple_write):
        """Perform test set write resolution operation.

        Args:
            simple_write: Simple write.
        """
        simple_write.set_write_resolution(decimal_digits=9)
        assert simple_write._write_resolution == 9
        with pytest.raises(AssertionError):
            simple_write.set_write_resolution(decimal_digits=1.2)


def int_read_func():
    """Return int read func result.

    Returns:
        Result value.
    """
    return 10


def int_write_func(val):
    """Return int write func result.

    Args:
        val: Val.

    Returns:
        Result value.
    """
    return "writing"


@pytest.fixture(scope='function', params=[1, 5])
def int_read_chan(request):
    """Return int read chan result.

    Args:
        request: Request.

    Returns:
        Result value.
    """
    return integer_channel(name='int_read_channel',
                           size=request.param,
                           read_function=int_read_func)


@pytest.fixture(scope='function')
def int_write_chan():
    """Return int write chan result.

    Returns:
        Result value.
    """
    return integer_channel(name='int_write_channel',
                           size=5,
                           write_function=int_write_func)


class TestIntegerReadChannel:
    """Tests for Integer Read Channel."""

    def test_get_size(self, int_read_chan):
        """Perform test get size operation.

        Args:
            int_read_chan: Int read chan.
        """
        assert int_read_chan.get_size() == int_read_chan._size

    def test_get_max_write_limit(self, int_write_chan):
        """Perform test get max write limit operation.

        Args:
            int_write_chan: Int write chan.
        """
        int_write_chan.set_max_write_limit(10)
        assert int_write_chan.get_max_write_limit() == 10

    def test_get_min_write_limit(self, int_write_chan):
        """Perform test get min write limit operation.

        Args:
            int_write_chan: Int write chan.
        """
        int_write_chan.set_min_write_limit(10)
        assert int_write_chan.get_min_write_limit() == 10

    def test_add_preset(self, int_read_chan):
        """Perform test add preset operation.

        Args:
            int_read_chan: Int read chan.
        """
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
        """Perform test set format operation.

        Args:
            format_type: Format type.
            int_read_chan: Int read chan.
        """
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
        """Perform test get format operation.

        Args:
            format_type: Format type.
            int_read_chan: Int read chan.
        """
        if int_read_chan.get_size() == 1:
            pass
        else:
            int_read_chan.set_format(format_type)
            assert int_read_chan.get_format() == format_type

    @pytest.mark.parametrize('data', [0, 4, 128, 1024, 89])
    @pytest.mark.parametrize('format', ['dec', 'hex', 'bin'])
    def test_format(self, data, format, int_write_chan):
        """Perform test format operation.

        Args:
            data: Data to write.
            format: Format name string.
            int_write_chan: Integer write channel fixture.
        """
        print(int_write_chan.format(data, format, use_presets=True))

    @pytest.mark.parametrize('data', [1, 15, 16, 31])
    def test_format_signed_dec(self, data, int_write_chan):
        """Perform test format signed dec operation.

        Args:
            data: Data to write.
            int_write_chan: Int write chan.
        """
        print(int_write_chan.format(data, 'signed dec', use_presets=True))

    def test_format_signed_dec_overflow(self, int_write_chan):
        """Perform test format signed dec overflow operation.

        Args:
            int_write_chan: Int write chan.
        """
        with pytest.raises(ValueError):
            int_write_chan.format(32, 'signed dec', use_presets=True)

    def test_sql_format(self, int_write_chan):
        """Perform test sql format operation.

        Args:
            int_write_chan: Int write chan.
        """
        int_write_chan.add_format('volts', lambda x: x * 0.01, lambda x: int(x / 0.01),
                                  xypoints=[(0, 0.0), (100, 1.0)])
        result = int_write_chan.sql_format('volts', use_presets=False)
        assert result is not None
        assert 'int_write_channel' in result

    def test_unformat_string(self, int_write_chan):
        """Perform test unformat string operation.

        Args:
            int_write_chan: Int write chan.
        """
        assert int_write_chan.unformat(string=None, format='dec',
                                       use_presets=False) is None

    def test_unformat_use_presets(self, int_write_chan):
        """Perform test unformat use presets operation.

        Args:
            int_write_chan: Int write chan.
        """
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
        """Perform test unformat specify format operation.

        Args:
            in_val: In val.
            int_write_chan: Int write chan.
            out_format: Out format.
            out_val: Out val.
        """
        int_write_chan.add_preset('ONE', out_val)
        assert int_write_chan.unformat(string=in_val, format=out_format,
                                       use_presets=False) == out_val

    @pytest.mark.parametrize('format_type, result', [('dec', '10'),
                                                     ('hex', '0x0A'),
                                                     ('bin', '0b01010'),
                                                     ('signed dec', '10')
                                                     ])
    def test_format_read(self, format_type, result, int_read_chan):
        """Perform test format read operation.

        Args:
            format_type: Format type.
            int_read_chan: Int read chan.
            result: Result.
        """
        if int_read_chan.get_size() != 1:
            int_read_chan.set_format(format_type)
            assert int_read_chan.format_read(10) == result

    @pytest.mark.parametrize('format_type, result', [('dec', '10'),
                                                     ('hex', '0x0A'),
                                                     ('bin', '0b01010'),
                                                     ('signed dec', '10')
                                                     ])
    def test_format_write(self, format_type, result, int_write_chan):
        """Perform test format write operation.

        Args:
            format_type: Format type.
            int_write_chan: Int write chan.
            result: Result.
        """
        int_write_chan.set_format(format_type)
        assert int_write_chan.format_write(result) == 10

    def test_write_size_1(self, int_write_chan):
        """Perform test write size 1 operation.

        Args:
            int_write_chan: Int write chan.
        """
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
        """Perform test write size greater 1 operation.

        Args:
            format_type: Format type.
            int_write_chan: Int write chan.
            result: Result.
        """
        int_write_chan.set_format(format_type)
        if result is None:
            assert int_write_chan.write(result) is None
        else:
            assert int_write_chan.write(result) == 10

    def test_write_unformatted_size_1(self, int_write_chan):
        """Perform test write unformatted size 1 operation.

        Args:
            int_write_chan: Int write chan.
        """
        chan = integer_channel('TEST', size=1,
                               write_function=write_function)
        assert chan.write_unformatted(True)
        assert not chan.write_unformatted(False)

    @pytest.mark.parametrize('data', [10, 1.1])
    def test_write_unformatted_size_greater_1(self, data, int_write_chan):
        """Perform test write unformatted size greater 1 operation.

        Args:
            data: Data to write.
            int_write_chan: Int write chan.
        """
        assert int_write_chan.write_unformatted(data) == int(data)


@pytest.fixture(scope='function')
def group():
    """Return group result.

    Returns:
        Result value.
    """
    c = channel_group(name='New Group')
    return c


@pytest.fixture
def loaded_group_w_channels(group):
    """Return loaded group w channels result.

    Args:
        group: Group.

    Returns:
        Result value.
    """
    sub_group1 = channel_group('subg1')
    sub_group2 = channel_group('subg2')

    sub_group1.add(c1 := channel(name='chan0',
                                 write_function=write_function))
    sub_group2.add(c2 := channel(name='chan1',
                                 write_function=write_function))
    c1.set_category('cat1')
    c2.set_category('cat2')
    group.add(sub_group1)
    group.add(sub_group2)
    group.add(c3 := channel(name='chan2', read_function=read_function))
    return group, [c1, c2, c3]


@pytest.fixture
def loaded_group(loaded_group_w_channels):
    """Return loaded group result.

    Args:
        loaded_group_w_channels: Loaded group w channels.

    Returns:
        Result value.
    """
    g, chans = loaded_group_w_channels
    return g


@pytest.fixture
def thread_group(group):
    """Return thread group result.

    Args:
        group: Group.

    Returns:
        Result value.
    """
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
    """Tests for Channel Group."""
    def test_copy(self, loaded_group):
        """Perform test copy operation.

        Args:
            loaded_group: Loaded group.
        """
        copied = loaded_group.copy()
        assert copied is not loaded_group
        assert copied.get_name() == loaded_group.get_name()
        assert set(
            copied.get_all_channel_names()) == set(
            loaded_group.get_all_channel_names())
        for name in loaded_group.get_all_channel_names():
            assert copied[name] is loaded_group[name]

    def test_get_name(self, group):
        """Perform test get name operation.

        Args:
            group: Group.
        """
        assert group.get_name() == 'New Group'

    def test_set_name(self, group):
        """Perform test set name operation.

        Args:
            group: Group.
        """
        group.set_name('New Name')
        assert group.get_name() == 'New Name'

    def test_get_categories(self, loaded_group):
        """Perform test get categories operation.

        Args:
            loaded_group: Loaded group.
        """
        cats = loaded_group.get_categories()
        assert 'cat1' in cats
        assert 'cat2' in cats

    def test_sort(self, group):
        """Perform test sort operation.

        Args:
            group: Group.
        """
        group.add(channel(name='zebra', read_function=read_function))
        group.add(channel(name='alpha', read_function=read_function))
        group.add(channel(name='middle', read_function=read_function))
        group.sort()
        names = list(group._channel_dict.keys())
        assert names == ['alpha', 'middle', 'zebra']

    def read_func1(self):
        """Return read func1 result.

        Returns:
            Result value.
        """
        return 1

    def read_func2(self):
        """Return read func2 result.

        Returns:
            Result value.
        """
        return 2

    def test_add(self, group):
        """Perform test add operation.

        Args:
            group: Group.
        """
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
        """Perform test  add channel operation.

        Args:
            chan: Chan.
            group: Group.
        """
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
        """Perform test merge in channel group operation.

        Args:
            group: Group.
        """
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
        """Perform test  add sub channel group operation.

        Args:
            group: Group.
        """
        with pytest.raises(Exception):
            group._add_sub_channel_group(0)
        group1 = channel_group('group1')
        group1.add([
            channel(name='c1'),
            channel(name='c2'),
        ])
        group2 = channel_group('group2')
        group2.add(
            channel(name='c2'),
        )
        group._add_sub_channel_group(group1)
        with pytest.raises(Exception):
            group._add_sub_channel_group(group2)

    def test_get_channel_groups(self, group):
        """Perform test get channel groups operation.

        Args:
            group: Group.
        """
        group.add(g1 := channel_group('name_test'))
        group.add(g2 := channel_group('name_test'))
        groups = group.get_channel_groups()
        assert groups == [g1, g2]

    def test_read(self, group):
        """Perform test read operation.

        Args:
            group: Group.
        """
        group.add(channel(name='test_channel',
                          read_function=read_function))
        assert group.read('test_channel') == 'Reading'
        with pytest.raises(ChannelAccessException):
            group.read(None)

    def test_write(self, group):
        """Perform test write operation.

        Args:
            group: Group.
        """
        group.add(channel(name='test_channel',
                          write_function=write_function))
        assert group.write('test_channel', 6) == 6

    def test_read_channels(self, group):
        """Perform test read channels operation.

        Args:
            group: Group.
        """
        chan_names = []
        for i in range(4):
            group.add(channel(name=f'chan{i}',
                              read_function=read_function))
            chan_names.append(f'chan{i}')
        result = group.read_channels(chan_names)
        assert result == {
            'chan0': 'Reading',
            'chan1': 'Reading',
            'chan2': 'Reading',
            'chan3': 'Reading',
        }

    def test_write_channels(self, group):
        """Perform test write channels operation.

        Args:
            group: Group.
        """
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
        """Perform test get channel operation.

        Args:
            group: Group.
        """
        with pytest.raises(ChannelAccessException):
            group.get_channel('doesnt_exhist')

    def test_get_flat_channel_group(self, group):
        """Perform test get flat channel group operation.

        Args:
            group: Group.
        """
        sub_group1 = channel_group('subg1')
        sub_group2 = channel_group('subg2')

        sub_group1.add(c1 := channel(name='chan0',
                                     write_function=write_function))
        sub_group2.add(c2 := channel(name='chan1',
                                     write_function=write_function))
        group.add(sub_group1)
        group.add(sub_group2)
        new_group = group.get_flat_channel_group()
        assert c1 in new_group
        assert c2 in new_group

    def test__resolve_channel(self, group):
        """Perform test  resolve channel operation.

        Args:
            group: Group.
        """
        sub_group1 = channel_group('subg1')
        sub_group1.add(c1 := channel(name='chan0',
                                     write_function=write_function))
        group.add(sub_group1)
        assert group._resolve_channel('chan0') is c1

    def test_get_all_channels_dict(self, loaded_group):
        """Perform test get all channels dict operation.

        Args:
            loaded_group: Loaded group.
        """
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
        """Perform test get all channel names operation.

        Args:
            loaded_group: Loaded group.
        """
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
        """Perform test get all channels list operation.

        Args:
            loaded_group_w_channels: Loaded group w channels.
        """
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
        """Perform test get all channels set operation.

        Args:
            loaded_group_w_channels: Loaded group w channels.
        """
        group, (c1, c2, c3) = loaded_group_w_channels
        chan_list = group.get_all_channels_list()
        assert c1 in chan_list
        assert c2 in chan_list
        assert c3 in chan_list

    def test_read_channel_list(self, thread_group):
        """Perform test read channel list operation.

        Args:
            thread_group: Thread group.
        """
        group, (c0, c1, c2, c3, c4) = thread_group
        results = group.read_channel_list([c0, c1, c2, c3])
        # non threaded
        assert results['chan0'] == 'Reading'
        assert results['chan1'] == 'Reading'
        assert results['chan2'] == 'Reading'
        assert results['chan3'] == 'Reading'

    def test__read_channels_non_threaded(self, thread_group):
        """Perform test  read channels non threaded operation.

        Args:
            thread_group: Thread group.
        """
        group, channels = thread_group
        readable = [
            c for c in channels if c.get_name() in (
                'chan0', 'chan1', 'chan3')]
        results = group._read_channels_non_threaded(readable)
        assert results['chan0'] == 'Reading'
        assert results['chan1'] == 'Reading'
        assert results['chan3'] == 'Reading'

    def test__read_channels_threaded(self, thread_group):
        # channel_group lacks group_com_nodes_for_threads_filter, so always
        # falls back to non-threaded
        """Perform test  read channels threaded operation.

        Args:
            thread_group: Thread group.
        """
        group, channels = thread_group
        readable = [c for c in channels if c.get_name() in ('chan0', 'chan3')]
        results = group._read_channels_threaded(readable)
        assert results['chan0'] == 'Reading'
        assert results['chan3'] == 'Reading'

    def test_start_threads(self, group):
        """Perform test start threads operation.

        Args:
            group: Group.
        """
        assert group._threaded is False
        group.start_threads(2)
        assert group._threaded is True
        assert group._threads == 2
        assert hasattr(group, '_read_queue')
        assert hasattr(group, '_read_results_queue')
        with pytest.raises(Exception, match='Threads already started'):
            group.start_threads(1)
        group._threaded = False
        for _ in range(2):
            group._read_queue.put([])

    def test_threaded_read_function(self, thread_group):
        """Perform test threaded read function operation.

        Args:
            thread_group: Thread group.
        """
        group, channels = thread_group
        group.start_threads(1)
        readable = [c for c in channels if c.get_name() == 'chan0']
        group._read_queue.put(readable)
        result = group._read_results_queue.get(timeout=2)
        assert result['chan0'] == 'Reading'
        group._threaded = False
        group._read_queue.put([])

    def test_get_threaded_results(self, group):
        """Perform test get threaded results operation.

        Args:
            group: Group.
        """
        group._read_results_queue = queue.Queue()
        r1 = results_ord_dict()
        r1['ch_a'] = 1
        r2 = results_ord_dict()
        r2['ch_b'] = 2
        group._read_results_queue.put(r1)
        group._read_results_queue.put(r2)
        results = group.get_threaded_results(2)
        assert results['ch_a'] == 1
        assert results['ch_b'] == 2
        group._read_results_queue.put(Exception('read error'))
        with pytest.raises(Exception):
            group.get_threaded_results(1)

    def test_read_all_channels(self, thread_group):
        """Perform test read all channels operation.

        Args:
            thread_group: Thread group.
        """
        group, channels = thread_group
        data = group.read_all_channels()
        assert 'chan0' in data
        assert 'chan1' in data
        assert 'chan2' in data
        assert 'chan3' in data
        assert 'chan4' in data

    def test_remove_channel(self, thread_group):
        """Perform test remove channel operation.

        Args:
            thread_group: Thread group.
        """
        group, channels = thread_group
        group.remove_channel(channels[0])

        chan = channels[1]
        chan.set_name('Notthere')
        assert channels[0] not in group
        with pytest.raises(Exception):
            group.remove_channel(chan)

    def test_remove_channel_group(self, group):
        """Perform test remove channel group operation.

        Args:
            group: Group.
        """
        sub_group1 = channel_group('subg1')
        sub_group2 = channel_group('subg2')

        sub_group1.add(
            c1 := channel(
                name='chan0',
                write_function=write_function))
        sub_group2.add(
            c2 := channel(
                name='chan1',
                write_function=write_function))
        group.merge_in_channel_group(sub_group1)
        group.merge_in_channel_group(sub_group2)

        assert c1 in group
        assert c2 in group

        group.remove_channel_group(sub_group1)

        assert c1 not in group
        assert c2 in group

    # @pytest.mark.xfail  # This one does not work because if you remove a channel group
    def test_remove_channel_by_name(self, loaded_group):
        """Perform test remove channel by name operation.

        Args:
            loaded_group: Loaded group.
        """
        loaded_group.add(c1 := channel(name='remove_chan'))
        assert c1 in loaded_group
        loaded_group.remove_channel_by_name('remove_chan')
        assert c1 not in loaded_group

    def test_remove_all_channels_and_sub_groups(self, loaded_group):
        """Perform test remove all channels and sub groups operation.

        Args:
            loaded_group: Loaded group.
        """
        loaded_group.remove_all_channels_and_sub_groups()
        assert not loaded_group._channel_dict
        assert not loaded_group._sub_channel_groups

    def test_remove_sub_channel_group(self, loaded_group):
        """Perform test remove sub channel group operation.

        Args:
            loaded_group: Loaded group.
        """
        sub_group = loaded_group._sub_channel_groups[0]
        loaded_group.remove_sub_channel_group(sub_group)
        assert sub_group not in loaded_group

    def test_remove_category(self, group):
        """Perform test remove category operation.

        Args:
            group: Group.
        """
        c1 = channel(name='a', read_function=read_function)
        c1.set_category('remove_me')
        c2 = channel(name='b', read_function=read_function)
        c2.set_category('keep')
        group.add(c1)
        group.add(c2)
        group.remove_category('remove_me')
        names = group.get_all_channel_names()
        assert 'a' not in names
        assert 'b' in names

    def test_remove_categories(self, group):
        """Perform test remove categories operation.

        Args:
            group: Group.
        """
        c1 = channel(name='a', read_function=read_function)
        c1.set_category('cat1')
        c2 = channel(name='b', read_function=read_function)
        c2.set_category('cat2')
        c3 = channel(name='c', read_function=read_function)
        c3.set_category('keep')
        group.add(c1)
        group.add(c2)
        group.add(c3)
        group.remove_categories('cat1', 'cat2')
        names = group.get_all_channel_names()
        assert 'a' not in names
        assert 'b' not in names
        assert 'c' in names

    def test_debug_print(self, loaded_group, capsys):
        """Perform test debug print operation.

        Args:
            capsys: Capsys.
            loaded_group: Loaded group.
        """
        loaded_group.debug_print()
        captured = capsys.readouterr()
        assert 'chan0' in captured.out or 'chan1' in captured.out

    def test_remove_channel_list(self, group):
        """Perform test remove channel list operation.

        Args:
            group: Group.
        """
        c1 = channel(name='rm1', read_function=read_function)
        c2 = channel(name='rm2', read_function=read_function)
        c3 = channel(name='keep', read_function=read_function)
        group.add(c1)
        group.add(c2)
        group.add(c3)
        group.remove_channel_list([c1, c2])
        assert c1 not in group
        assert c2 not in group
        assert c3 in group

    def test_resolve_channel_list(self, loaded_group_w_channels):
        """Perform test resolve channel list operation.

        Args:
            loaded_group_w_channels: Loaded group w channels.
        """
        group, (c1, c2, c3) = loaded_group_w_channels
        resolved = group.resolve_channel_list(['chan0', c2])
        assert c1 in resolved
        assert c2 in resolved

    def test_clone(self, loaded_group):
        """Perform test clone operation.

        Args:
            loaded_group: Loaded group.
        """
        cloned = loaded_group.clone()
        assert 'chan0' in cloned.get_all_channel_names()
        assert 'chan1' in cloned.get_all_channel_names()
        assert cloned is not loaded_group

    def test_write_html(self, loaded_group, tmp_path):
        """Perform test write html operation.

        Args:
            loaded_group: Loaded group.
            tmp_path: Tmp path.
        """
        import html5lib
        from bs4 import BeautifulSoup

        html = loaded_group.write_html()

        # html5lib: parse and check for spec parse errors
        parser = html5lib.HTMLParser()
        doc = parser.parse(html)
        assert doc is not None

        # BeautifulSoup: structural DOM assertions
        soup = BeautifulSoup(html, 'html5lib')
        table = soup.find('table')
        assert table is not None

        headers = [th.get_text() for th in table.find_all('th')]
        assert headers == ['Channel Name', 'Category', 'Description']

        rows = table.find_all('tr')
        # 1 header row + 1 row per channel
        channel_names = loaded_group.get_all_channel_names()
        assert len(rows) == 1 + len(channel_names)

        # Every channel name appears in the table body
        body_text = table.get_text()
        for name in channel_names:
            assert name in body_text

        # File output round-trip
        out_file = tmp_path / "channels.html"
        html2 = loaded_group.write_html(file_name=str(out_file))
        assert out_file.exists()
        assert out_file.read_bytes() == html2.encode('utf-8')

    def test_write_html_sort_categories(self, loaded_group_w_channels):
        """Perform test write html sort categories operation.

        Args:
            loaded_group_w_channels: Loaded group w channels.
        """
        from bs4 import BeautifulSoup

        group, _ = loaded_group_w_channels
        html = group.write_html(sort_categories=True)
        soup = BeautifulSoup(html, 'html5lib')
        rows = soup.find('table').find_all('tr')[1:]  # skip header
        cell_texts = [row.find_all('td')[1].get_text().strip() for row in rows]
        # Categories should be sorted: cat1, cat2, then None/empty for chan2
        assert cell_texts == sorted(cell_texts, key=str)

    def test_write_html_verbose_presets_and_attributes(self, tmp_path):
        """Perform test write html verbose presets and attributes operation.

        Args:
            tmp_path: Tmp path.
        """
        from bs4 import BeautifulSoup

        group = channel_group('verbose_group')
        int_ch = integer_channel(name='int_chan', size=8,
                                 write_function=write_function)
        int_ch.add_preset('LOW', 0)
        int_ch.add_preset('HIGH', 255)
        int_ch.set_attribute('units', 'counts')
        int_ch.set_description('An integer channel with presets')
        group._add_channel(int_ch)

        html = group.write_html(verbose=True)
        soup = BeautifulSoup(html, 'html5lib')

        # Presets rendered as <select> with correct options
        presets_select = soup.find('select', {'name': 'presets'})
        assert presets_select is not None
        options = presets_select.find_all('option')
        option_texts = [opt.get_text() for opt in options]
        assert any('LOW' in t for t in option_texts)
        assert any('HIGH' in t for t in option_texts)

        # Attributes rendered as <select>
        attrs_select = soup.find('select', {'name': 'attributes'})
        assert attrs_select is not None
        assert 'units' in attrs_select.get_text()

    def test_write_html_not_verbose(self, tmp_path):
        """Perform test write html not verbose operation.

        Args:
            tmp_path: Tmp path.
        """
        from bs4 import BeautifulSoup

        group = channel_group('quiet_group')
        int_ch = integer_channel(name='int_chan', size=8,
                                 write_function=write_function)
        int_ch.add_preset('LOW', 0)
        int_ch.set_attribute('units', 'counts')
        group._add_channel(int_ch)

        html = group.write_html(verbose=False)
        soup = BeautifulSoup(html, 'html5lib')
        assert soup.find('select', {'name': 'presets'}) is None
        assert soup.find('select', {'name': 'attributes'}) is None
