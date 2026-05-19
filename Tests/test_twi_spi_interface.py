import pytest
from collections import OrderedDict
from PyICe.twi_interface import twi_interface, i2c_dummy
from PyICe.spi_interface import shift_register


class TestTwiInterfaceUtilities:

    def test_read_addr(self):
        """Perform test read addr operation."""
        assert twi_interface.read_addr(0x50) == 0xA1

    def test_write_addr(self):
        """Perform test write addr operation."""
        assert twi_interface.write_addr(0x50) == 0xA0

    def test_check_size_valid(self):
        """Perform test check size valid operation."""
        twi_interface.check_size(0xFF, 8)
        twi_interface.check_size(0x00, 8)

    def test_check_size_overflow(self):
        """Perform test check size overflow operation."""
        with pytest.raises(Exception):
            twi_interface.check_size(0x100, 8)

    def test_get_byte(self):
        """Perform test get byte operation."""
        assert twi_interface.get_byte(0x1234, 0) == 0x34
        assert twi_interface.get_byte(0x1234, 1) == 0x12

    def test_word_from_bytes(self):
        """Perform test word from bytes operation."""
        assert twi_interface.word([0x34, 0x12]) == 0x1234

    def test_pec_calculation(self):
        """Perform test pec calculation operation."""
        result = twi_interface.pec([0xA0, 0x00, 0x12])
        assert isinstance(result, int)
        assert 0 <= result <= 0xFF


class TestI2CDummy:

    @pytest.fixture
    def dummy(self):
        """Return dummy result.

        Returns:
            Result value.
        """
        return i2c_dummy(delay=0, p_change=0, verbose=False)

    def test_start_returns_true(self, dummy):
        """Perform test start returns true operation.

        Args:
            dummy: Dummy.
        """
        assert dummy.start() is True

    def test_stop_returns_true(self, dummy):
        """Perform test stop returns true operation.

        Args:
            dummy: Dummy.
        """
        assert dummy.stop() is True

    def test_write_returns_true(self, dummy):
        """Perform test write returns true operation.

        Args:
            dummy: Dummy.
        """
        result = dummy.write(0x55)
        assert result is True

    def test_write_register_stores_data(self, dummy):
        """Perform test write register stores data operation.

        Args:
            dummy: Dummy.
        """
        dummy.write_register(addr7=0x50, commandCode=0x00,
                             data=0xAB, data_size=8, use_pec=False)
        result = dummy.read_register(addr7=0x50, commandCode=0x00,
                                     data_size=8, use_pec=False)
        assert result == 0xAB

    def test_write_register_16bit(self, dummy):
        """Perform test write register 16bit operation.

        Args:
            dummy: Dummy.
        """
        dummy.write_register(addr7=0x50, commandCode=0x10,
                             data=0x1234, data_size=16, use_pec=False)
        result = dummy.read_register(addr7=0x50, commandCode=0x10,
                                     data_size=16, use_pec=False)
        assert result == 0x1234

    def test_read_unwritten_register(self, dummy):
        """Perform test read unwritten register operation.

        Args:
            dummy: Dummy.
        """
        result = dummy.read_register(addr7=0x50, commandCode=0xFF,
                                     data_size=8, use_pec=False)
        assert isinstance(result, int)
        assert 0 <= result <= 255

    def test_read_register_list(self, dummy):
        """Perform test read register list operation.

        Args:
            dummy: Dummy.
        """
        dummy.write_register(0x50, 0x00, 10, 8, use_pec=False)
        dummy.write_register(0x50, 0x01, 20, 8, use_pec=False)
        results = dummy.read_register_list(
            0x50, [0x00, 0x01], 8, use_pec=False)
        assert results[0x00] == 10
        assert results[0x01] == 20

    def test_no_corruption_with_p_change_zero(self, dummy):
        """Perform test no corruption with p change zero operation.

        Args:
            dummy: Dummy.
        """
        dummy.write_register(0x50, 0x05, 0x42, 8, use_pec=False)
        for _ in range(100):
            assert dummy.read_register(0x50, 0x05, 8, use_pec=False) == 0x42


class TestShiftRegister:

    @pytest.fixture
    def reg(self):
        """Return reg result.

        Returns:
            Result value.
        """
        sr = shift_register('test_reg')
        sr.add_bit_field('field_a', 4)
        sr.add_bit_field('field_b', 2)
        sr.add_bit_field('field_c', 2)
        return sr

    def test_total_length(self, reg):
        """Perform test total length operation.

        Args:
            reg: Reg.
        """
        assert len(reg) == 8

    def test_field_bit_count(self, reg):
        """Perform test field bit count operation.

        Args:
            reg: Reg.
        """
        assert reg['field_a'] == 4
        assert reg['field_b'] == 2
        assert reg['field_c'] == 2

    def test_keys(self, reg):
        """Perform test keys operation.

        Args:
            reg: Reg.
        """
        assert reg.keys() == ['field_a', 'field_b', 'field_c']

    def test_pack(self, reg):
        """Perform test pack operation.

        Args:
            reg: Reg.
        """
        data = {'field_a': 0xF, 'field_b': 0x2, 'field_c': 0x1}
        packed, bits = reg.pack(data)
        assert bits == 8
        assert packed == 0b11111001  # 0xF9

    def test_unpack(self, reg):
        """Perform test unpack operation.

        Args:
            reg: Reg.
        """
        result = reg.unpack(0b11111001)
        assert result['field_a'] == 0xF
        assert result['field_b'] == 0x2
        assert result['field_c'] == 0x1

    def test_pack_unpack_roundtrip(self, reg):
        """Perform test pack unpack roundtrip operation.

        Args:
            reg: Reg.
        """
        data = {'field_a': 5, 'field_b': 3, 'field_c': 0}
        packed, bits = reg.pack(data)
        unpacked = reg.unpack(packed)
        assert unpacked['field_a'] == 5
        assert unpacked['field_b'] == 3
        assert unpacked['field_c'] == 0

    def test_pack_zero(self, reg):
        """Perform test pack zero operation.

        Args:
            reg: Reg.
        """
        data = {'field_a': 0, 'field_b': 0, 'field_c': 0}
        packed, bits = reg.pack(data)
        assert packed == 0

    def test_pack_all_ones(self, reg):
        """Perform test pack all ones operation.

        Args:
            reg: Reg.
        """
        data = {'field_a': 0xF, 'field_b': 0x3, 'field_c': 0x3}
        packed, bits = reg.pack(data)
        assert packed == 0xFF

    def test_unpack_preserves_order(self, reg):
        """Perform test unpack preserves order operation.

        Args:
            reg: Reg.
        """
        result = reg.unpack(0x00)
        assert isinstance(result, OrderedDict)
        assert list(result.keys()) == ['field_a', 'field_b', 'field_c']

    def test_add_duplicate_field_raises(self, reg):
        """Perform test add duplicate field raises operation.

        Args:
            reg: Reg.
        """
        with pytest.raises(ValueError):
            reg.add_bit_field('field_a', 4)

    def test_iteration(self, reg):
        """Perform test iteration operation.

        Args:
            reg: Reg.
        """
        fields = list(reg)
        assert fields == ['field_a', 'field_b', 'field_c']

    def test_get_name(self, reg):
        """Perform test get name operation.

        Args:
            reg: Reg.
        """
        assert reg.get_name() == 'test_reg'

    def test_concatenation(self):
        """Perform test concatenation operation."""
        sr1 = shift_register('r1')
        sr1.add_bit_field('high', 4)
        sr2 = shift_register('r2')
        sr2.add_bit_field('low', 4)
        combined = sr1 + sr2
        assert len(combined) == 8
        assert 'high' in combined.keys()
        assert 'low' in combined.keys()

    def test_copy(self, reg):
        """Perform test copy operation.

        Args:
            reg: Reg.
        """
        copied = reg.copy(prepend_str='pre_')
        assert 'pre_field_a' in copied.keys()
        assert len(copied) == len(reg)

    def test_16bit_register(self):
        """Perform test 16bit register operation."""
        sr = shift_register('wide')
        sr.add_bit_field('addr', 8)
        sr.add_bit_field('data', 8)
        packed, bits = sr.pack({'addr': 0xAB, 'data': 0xCD})
        assert bits == 16
        assert packed == 0xABCD

    def test_single_bit_fields(self):
        """Perform test single bit fields operation."""
        sr = shift_register('flags')
        sr.add_bit_field('enable', 1)
        sr.add_bit_field('direction', 1)
        sr.add_bit_field('mode', 2)
        packed, bits = sr.pack({'enable': 1, 'direction': 0, 'mode': 3})
        assert bits == 4
        assert packed == 0b1011
        result = sr.unpack(0b1011)
        assert result['enable'] == 1
        assert result['direction'] == 0
        assert result['mode'] == 3
