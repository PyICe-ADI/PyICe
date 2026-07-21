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

    def test_smbus_only_backend_no_primitives_needed(self):
        """Type B backend: no primitives, only _do_* overrides."""
        from PyICe.twi_interface import i2cUnimplementedError

        class SmBusOnly(twi_interface):
            def _do_write_register(self, addr7, commandCode, data, data_size, use_pec):
                if data_size == 8 and not use_pec:
                    return None
                raise i2cUnimplementedError("unsupported")

            def _do_read_register(self, addr7, commandCode, data_size, use_pec):
                if data_size == 8 and not use_pec:
                    return 0x42
                raise i2cUnimplementedError("unsupported")

        b = SmBusOnly()
        b.write_byte(0x48, 0x05, 0xAB)
        assert b.read_byte(0x48, 0x05) == 0x42
        with pytest.raises(i2cUnimplementedError):
            b.write_word(0x48, 0x05, 0x1234)
        with pytest.raises(i2cUnimplementedError):
            b.block_read(0x48, 0x10)

    def test_primitives_only_backend_works(self):
        class MinimalBackend(twi_interface):
            def start(self): return True
            def stop(self): return True
            def write(self, d): return True
            def read_ack(self): return 0
            def read_nack(self): return 0
        b = MinimalBackend()
        assert hasattr(b, 'write_register')
        assert hasattr(b, 'read_register')
        assert hasattr(b, 'write_byte')
        assert hasattr(b, 'block_read')

    def test_validation_cannot_be_bypassed_via_protocol_methods(self):
        d = i2c_dummy(delay=0, p_change=0)
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            d.write_word(0x80, 0x05, 0x1234)

    def test_read_32_routes_through_validation(self):
        d = i2c_dummy(delay=0, p_change=0)
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            d.read_32(0x80, 0x05)


class TestPartialAccelerationFallback:
    """Verify that a backend can accelerate some protocols and fall back
    to bit-bang (via super()) for others."""

    def _make_partial_backend(self):
        """Create a backend that accelerates 8-bit writes but falls back
        for everything else."""
        class PartialBackend(twi_interface):
            def __init__(self):
                self.hw_calls = []
                self.bitbang_calls = []
                self._memory = {}

            def start(self): return True
            def stop(self): return True
            def write(self, data8):
                self.bitbang_calls.append(('write', data8))
                return True
            def read_ack(self): return 0x42
            def read_nack(self): return 0x42

            def _do_write_register(self, addr7, commandCode, data, data_size, use_pec):
                if data_size == 8 and not use_pec:
                    self.hw_calls.append(('hw_write_byte', addr7, commandCode, data))
                    self._memory[commandCode] = data
                else:
                    super()._do_write_register(addr7, commandCode, data, data_size, use_pec)

            def _do_read_register(self, addr7, commandCode, data_size, use_pec):
                if data_size == 8 and not use_pec:
                    self.hw_calls.append(('hw_read_byte', addr7, commandCode))
                    return self._memory.get(commandCode, 0)
                else:
                    return super()._do_read_register(addr7, commandCode, data_size, use_pec)

        return PartialBackend()

    def test_accelerated_path_used_for_8bit(self):
        b = self._make_partial_backend()
        b.write_byte(0x48, 0x05, 0xAB)
        assert b.hw_calls == [('hw_write_byte', 0x48, 0x05, 0xAB)]
        assert b.bitbang_calls == []

    def test_fallback_used_for_16bit(self):
        b = self._make_partial_backend()
        b.write_word(0x48, 0x05, 0x1234)
        assert b.hw_calls == []
        assert len(b.bitbang_calls) > 0

    def test_read_accelerated_path(self):
        b = self._make_partial_backend()
        b.write_byte(0x48, 0x10, 0xDE)
        result = b.read_byte(0x48, 0x10)
        assert result == 0xDE
        assert ('hw_read_byte', 0x48, 0x10) in b.hw_calls

    def test_read_fallback_uses_primitives(self):
        b = self._make_partial_backend()
        result = b.read_word(0x48, 0x10)
        assert b.hw_calls == []
        assert len(b.bitbang_calls) > 0
        assert result == 0x4242

    def test_validation_still_applied(self):
        b = self._make_partial_backend()
        with pytest.raises(ValueError, match="exceeds 7-bit"):
            b.write_byte(0x80, 0x05, 0xAB)
        assert b.hw_calls == []

    def test_read_register_list_rejects_bad_data_size(self):
        """data_size=7 should raise."""
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        with pytest.raises(Exception, match="Unimplemented data size"):
            d.read_register_list(0x48, [0x00], 7, False)

    def test_read_register_list_delegates_to_do_impl(self):
        """Verify _do_read_register_list is called by read_register_list."""
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        d.write_register(0x48, 0x10, 0xAB, 8, False)
        from unittest.mock import patch
        with patch.object(d, '_do_read_register_list', return_value={0x10: 0xAB}) as mock:
            result = d.read_register_list(0x48, [0x10], 8, False)
            mock.assert_called_once_with(0x48, [0x10], 8, False)
        assert result == {0x10: 0xAB}

    def test_deprecated_read_byte_list_warns(self):
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        d.write_register(0x48, 0x10, 0xAB, 8, False)
        with pytest.warns(DeprecationWarning, match="read_byte_list is deprecated"):
            d.read_byte_list(0x48, [0x10])

    def test_deprecated_read_word_list_warns(self):
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        d.write_register(0x48, 0x10, 0x1234, 16, False)
        with pytest.warns(DeprecationWarning, match="read_word_list is deprecated"):
            d.read_word_list(0x48, [0x10])

    def test_quick_command_wr_routes_through_write_register(self):
        """Verify quick_command_wr reaches _do_write_register with data_size=-1."""
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        from unittest.mock import patch
        with patch.object(d, '_do_write_register') as mock:
            d.quick_command_wr(0x48)
            mock.assert_called_once_with(0x48, None, None, -1, False)

    def test_quick_command_rd_routes_through_read_register(self):
        """Verify quick_command_rd reaches _do_read_register with data_size=-1."""
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        from unittest.mock import patch
        with patch.object(d, '_do_read_register', return_value=None) as mock:
            d.quick_command_rd(0x48)
            mock.assert_called_once_with(0x48, None, -1, False)

    def test_alert_response_routes_through_do_alert_response(self):
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        from unittest.mock import patch
        with patch.object(d, '_do_alert_response', return_value=0x48) as mock:
            result = d.alert_response()
            mock.assert_called_once_with(use_pec=False)
        assert result == 0x48

    def test_alert_response_pec_routes_through_do_alert_response(self):
        d = i2c_dummy(delay=0, p_change=0, seed=42)
        from unittest.mock import patch
        with patch.object(d, '_do_alert_response', return_value=0x48) as mock:
            result = d.alert_response_pec()
            mock.assert_called_once_with(use_pec=True)
        assert result == 0x48

    def test_protocol_methods_all_work_without_override(self):
        """A primitives-only backend handles all protocols via bit-bang."""
        class PrimitivesOnly(twi_interface):
            def start(self): return True
            def stop(self): return True
            def write(self, data8): return True
            def read_ack(self): return 0x55
            def read_nack(self): return 0xAA

        b = PrimitivesOnly()
        b.write_register(0x48, 0x05, 0xAB, 8, False)
        b.write_word(0x48, 0x05, 0x1234)
        b.write_32(0x48, 0x05, 0xDEADBEEF)
        assert b.read_byte(0x48, 0x05) == 0xAA
        assert b.read_word(0x48, 0x05) == 0xAA55
        b.process_call(0x48, 0x10, 0x5678)
        b.block_write(0x48, 0x10, [0x01, 0x02, 0x03])
