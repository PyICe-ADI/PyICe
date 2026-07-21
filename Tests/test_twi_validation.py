"""Tests for twi_interface Template Method validation."""
import pytest
from PyICe.twi_interface import twi_interface, i2c_dummy


class TestCheckSize:
    def test_valid(self):
        assert twi_interface.check_size(0, 8) is True
        assert twi_interface.check_size(255, 8) is True
        assert twi_interface.check_size(0x7F, 7) is True

    def test_overflow(self):
        with pytest.raises(ValueError, match="exceeds 8-bit range"):
            twi_interface.check_size(256, 8)

    def test_negative(self):
        with pytest.raises(ValueError, match="negative"):
            twi_interface.check_size(-1, 8)

    def test_none(self):
        with pytest.raises(TypeError, match="Expected integer"):
            twi_interface.check_size(None, 8)


class TestValidateWriteArgs:
    @pytest.fixture
    def dummy(self):
        return i2c_dummy(delay=0, p_change=0)

    def test_valid_write_byte(self, dummy):
        dummy.write_register(addr7=0x48, commandCode=0x05, data=0xAB, data_size=8, use_pec=False)

    def test_valid_write_word(self, dummy):
        dummy.write_register(addr7=0x48, commandCode=0x05, data=0xCAFE, data_size=16, use_pec=False)

    def test_addr7_too_wide(self, dummy):
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            dummy.write_register(addr7=0x80, commandCode=0x05, data=0xAB, data_size=8, use_pec=False)

    def test_data_too_wide(self, dummy):
        with pytest.raises(ValueError, match="exceeds 8-bit"):
            dummy.write_register(addr7=0x48, commandCode=0x05, data=0x1FF, data_size=8, use_pec=False)

    def test_send_byte_with_data(self, dummy):
        with pytest.raises(ValueError, match="data must be None"):
            dummy.write_register(addr7=0x48, commandCode=0x05, data=0x55, data_size=0, use_pec=False)

    def test_quick_command_with_cc(self, dummy):
        with pytest.raises(ValueError, match="commandCode must be None"):
            dummy.write_register(addr7=0x48, commandCode=0x05, data=None, data_size=-1, use_pec=False)

    def test_quick_command_with_data(self, dummy):
        with pytest.raises(ValueError, match="data must be None"):
            dummy.write_register(addr7=0x48, commandCode=None, data=0x55, data_size=-1, use_pec=False)

    def test_bad_data_size(self, dummy):
        with pytest.raises(ValueError, match="Unsupported data_size"):
            dummy.write_register(addr7=0x48, commandCode=0x05, data=0xAB, data_size=99, use_pec=False)

    def test_none_command_code(self, dummy):
        with pytest.raises(TypeError, match="commandCode is required"):
            dummy.write_register(addr7=0x48, commandCode=None, data=0xAB, data_size=8, use_pec=False)

    def test_none_data(self, dummy):
        with pytest.raises(TypeError, match="Expected integer, got None"):
            dummy.write_register(addr7=0x48, commandCode=0x05, data=None, data_size=8, use_pec=False)


class TestValidateReadArgs:
    @pytest.fixture
    def dummy(self):
        d = i2c_dummy(delay=0, p_change=0)
        d._do_write_register(addr7=0x48, commandCode=0x06, data=0x1234, data_size=16, use_pec=False)
        return d

    def test_valid_read_word(self, dummy):
        assert dummy.read_register(addr7=0x48, commandCode=0x06, data_size=16, use_pec=False) == 0x1234

    def test_addr7_too_wide(self, dummy):
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            dummy.read_register(addr7=0x80, commandCode=0x06, data_size=16, use_pec=False)

    def test_receive_byte_with_cc(self, dummy):
        with pytest.raises(ValueError, match="commandCode must be None"):
            dummy.read_register(addr7=0x48, commandCode=0x05, data_size=0, use_pec=False)

    def test_bad_data_size(self, dummy):
        with pytest.raises(ValueError, match="Unsupported data_size"):
            dummy.read_register(addr7=0x48, commandCode=0x05, data_size=99, use_pec=False)

    def test_none_command_code(self, dummy):
        with pytest.raises(TypeError, match="commandCode is required"):
            dummy.read_register(addr7=0x48, commandCode=None, data_size=16, use_pec=False)


class TestBackendContract:
    def test_protocol_method_validates(self):
        d = i2c_dummy(delay=0, p_change=0)
        with pytest.raises(ValueError, match="exceeds 8-bit"):
            d.write_byte(0x48, 0x05, 0x1FF)

    def test_abstract_enforcement(self):
        with pytest.raises(TypeError, match="abstract method"):
            class BadBackend(twi_interface):
                def start(self): pass
                def stop(self): pass
                def write(self, d): pass
                def read_ack(self): pass
                def read_nack(self): pass
            BadBackend()  # pylint: disable=abstract-class-instantiated

    def test_validation_cannot_be_bypassed_via_protocol_methods(self):
        d = i2c_dummy(delay=0, p_change=0)
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            d.write_word(0x80, 0x05, 0x1234)

    def test_read_32_routes_through_validation(self):
        d = i2c_dummy(delay=0, p_change=0)
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            d.read_32(0x80, 0x05)
