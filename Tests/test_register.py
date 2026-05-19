import pytest
from PyICe.lab_core import register, integer_channel


def make_register(size=8, init_value=0):
    """Create a register with in-memory read/write backing store.

    Args:
        init_value: Init value.
        size: Size in bits.

    Returns:
        Result value.
    """
    store = [init_value]

    def read_fn():
        """Return read fn result."""
        return store[0]

    def write_fn(val):
        """Perform write fn operation."""
        store[0] = val

    return register('test_reg', size=size,
                    read_function=read_fn, write_function=write_fn), store


class TestRegisterBasics:

    def test_register_is_integer_channel(self):
        """Perform test register is integer channel operation."""
        reg, _ = make_register()
        assert isinstance(reg, integer_channel)

    def test_register_read_and_write_access(self):
        """Perform test register read and write access operation."""
        reg, _ = make_register()
        assert reg.is_readable()
        assert reg.is_writeable()

    def test_register_read_returns_hardware_value(self):
        """Perform test register read returns hardware value operation."""
        reg, store = make_register(size=8, init_value=0xAB)
        assert reg.read() == 0xAB

    def test_register_write_stores_value(self):
        """Perform test register write stores value operation."""
        reg, store = make_register()
        reg.write(0x55)
        assert store[0] == 0x55

    def test_register_size(self):
        """Perform test register size operation."""
        reg, _ = make_register(size=16)
        assert reg.get_size() == 16

    def test_register_write_limits(self):
        """Perform test register write limits operation."""
        reg, _ = make_register(size=4)
        reg.write(15)
        assert reg.read() == 15
        from PyICe.lab_core import ChannelValueException
        with pytest.raises(ChannelValueException):
            reg.write(16)
        with pytest.raises(ChannelValueException):
            reg.write(-1)

    def test_register_formats(self):
        """Perform test register formats operation."""
        reg, store = make_register(size=8, init_value=10)
        reg.set_format('hex')
        assert reg.format_read(10) == '0x0A'

    def test_register_read_only(self):
        """Register with only read_function still readable."""
        store = [42]
        reg = register('ro_reg', size=8, read_function=lambda: store[0])
        assert reg.is_readable()
        assert not reg.is_writeable()
        assert reg.read() == 42


class TestRegisterCachedRead:

    def test_enable_cached_read(self):
        """Perform test enable cached read operation."""
        reg, store = make_register(size=8, init_value=0)
        reg.write(0x7F)
        reg.enable_cached_read()
        store[0] = 0xFF
        assert reg.read() == 0x7F

    def test_enable_cached_read_attribute(self):
        """Perform test enable cached read attribute operation."""
        reg, _ = make_register()
        assert reg.get_attribute('read_caching') is False
        reg.enable_cached_read()
        assert reg.get_attribute('read_caching') is True

    def test_enable_cached_read_requires_writable(self):
        """Perform test enable cached read requires writable operation."""
        store = [0]
        reg = register('ro_reg', size=8, read_function=lambda: store[0])
        with pytest.raises(Exception, match="non-writable"):
            reg.enable_cached_read()


class TestRegisterSpecialAccess:

    def test_RO(self):
        """Perform test RO operation."""
        reg, _ = make_register()
        reg.set_special_access('RO')
        assert reg.is_readable()
        assert not reg.is_writeable()

    def test_RW(self):
        """Perform test RW operation."""
        reg, _ = make_register()
        reg.set_special_access('RW')
        assert reg.is_readable()
        assert reg.is_writeable()

    def test_WO(self):
        """Perform test WO operation."""
        reg, _ = make_register()
        reg.set_special_access('WO')
        assert not reg.is_readable()
        assert reg.is_writeable()

    def test_W1C_sets_preset_and_attribute(self):
        """Perform test W1C sets preset and attribute operation."""
        reg, _ = make_register()
        reg.set_special_access('W1C')
        assert reg.get_attribute('special_access') == 'W1C'
        presets = reg.get_presets_dict()
        assert 'clear' in presets
        assert presets['clear'] == 2 ** 8 - 1

    def test_W0C_sets_preset_and_attribute(self):
        """Perform test W0C sets preset and attribute operation."""
        reg, _ = make_register()
        reg.set_special_access('W0C')
        assert reg.get_attribute('special_access') == 'W0C'
        presets = reg.get_presets_dict()
        assert 'clear' in presets
        assert presets['clear'] == 0

    def test_W1S_sets_preset_and_attribute(self):
        """Perform test W1S sets preset and attribute operation."""
        reg, _ = make_register()
        reg.set_special_access('W1S')
        assert reg.get_attribute('special_access') == 'W1S'
        presets = reg.get_presets_dict()
        assert 'set' in presets
        assert presets['set'] == 2 ** 8 - 1

    def test_W0S_sets_preset_and_attribute(self):
        """Perform test W0S sets preset and attribute operation."""
        reg, _ = make_register()
        reg.set_special_access('W0S')
        assert reg.get_attribute('special_access') == 'W0S'
        presets = reg.get_presets_dict()
        assert 'set' in presets
        assert presets['set'] == 0

    @pytest.mark.parametrize('access', ['RC', 'RS', 'WRC', 'WRS'])
    def test_unimplemented_read_side_effects_raise(self, access):
        """Perform test unimplemented read side effects raise operation."""
        reg, _ = make_register()
        with pytest.raises(Exception, match="unimplemented"):
            reg.set_special_access(access)

    @pytest.mark.parametrize('access', ['WC', 'WS', 'W1T', 'W0T'])
    def test_unimplemented_write_side_effects_raise(self, access):
        """Perform test unimplemented write side effects raise operation."""
        reg, _ = make_register()
        with pytest.raises(Exception, match="not yet implemented"):
            reg.set_special_access(access)

    def test_unknown_access_raises(self):
        """Perform test unknown access raises operation."""
        reg, _ = make_register()
        with pytest.raises(Exception, match="Unknown"):
            reg.set_special_access('INVALID')


class TestRegisterRMW:

    def test_no_special_access_returns_data(self):
        """Perform test no special access returns data operation."""
        reg, _ = make_register()
        assert reg.compute_rmw_writeback_data(0xAB) == 0xAB

    def test_W1C_returns_zero(self):
        """Perform test W1C returns zero operation."""
        reg, _ = make_register()
        reg.set_special_access('W1C')
        assert reg.compute_rmw_writeback_data(0xAB) == 0

    def test_W1S_returns_zero(self):
        """Perform test W1S returns zero operation."""
        reg, _ = make_register()
        reg.set_special_access('W1S')
        assert reg.compute_rmw_writeback_data(0xAB) == 0

    def test_W0C_returns_all_ones(self):
        """Perform test W0C returns all ones operation."""
        reg, _ = make_register(size=8)
        reg.set_special_access('W0C')
        assert reg.compute_rmw_writeback_data(0xAB) == 0xFF

    def test_W0S_returns_all_ones(self):
        """Perform test W0S returns all ones operation."""
        reg, _ = make_register(size=8)
        reg.set_special_access('W0S')
        assert reg.compute_rmw_writeback_data(0xAB) == 0xFF


class TestRegisterExpectReadback:

    def test_no_special_access(self):
        """Perform test no special access operation."""
        reg, _ = make_register()
        result = reg.compute_expect_readback_data(10)
        assert result == 10

    def test_W1C_data_1_returns_0(self):
        """Perform test W1C data 1 returns 0 operation."""
        reg, _ = make_register()
        reg.set_special_access('W1C')
        assert reg.compute_expect_readback_data(1) == 0

    def test_W1C_data_0_returns_none(self):
        """Perform test W1C data 0 returns none operation."""
        reg, _ = make_register()
        reg.set_special_access('W1C')
        assert reg.compute_expect_readback_data(0) is None

    def test_W1S_data_1_returns_1(self):
        """Perform test W1S data 1 returns 1 operation."""
        reg, _ = make_register()
        reg.set_special_access('W1S')
        assert reg.compute_expect_readback_data(1) == 1

    def test_W1S_data_0_returns_none(self):
        """Perform test W1S data 0 returns none operation."""
        reg, _ = make_register()
        reg.set_special_access('W1S')
        assert reg.compute_expect_readback_data(0) is None

    def test_W0C_data_0_returns_0(self):
        """Perform test W0C data 0 returns 0 operation."""
        reg, _ = make_register()
        reg.set_special_access('W0C')
        assert reg.compute_expect_readback_data(0) == 0

    def test_W0C_data_1_returns_none(self):
        """Perform test W0C data 1 returns none operation."""
        reg, _ = make_register()
        reg.set_special_access('W0C')
        assert reg.compute_expect_readback_data(1) is None

    def test_W0S_data_1_returns_1(self):
        """Perform test W0S data 1 returns 1 operation."""
        reg, _ = make_register()
        reg.set_special_access('W0S')
        assert reg.compute_expect_readback_data(1) == 1
