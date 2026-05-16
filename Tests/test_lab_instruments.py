"""
Representative lab_instruments unit tests using i2c_dummy and VISA mocks.

This file demonstrates the pattern for testing instrument drivers without
hardware. I2C drivers use the i2c_dummy interface which stores register
data in a plain Python dict. VISA/SCPI instruments use unittest.mock.
"""
import pytest
from unittest.mock import MagicMock
from PyICe.lab_core import instrument
from PyICe.lab_utils.swap_endian import swap_endian
from PyICe.lab_instruments.TMP117 import TMP117
from PyICe.lab_instruments.AD5259 import AD5259
from PyICe.lab_instruments.ADT7410 import ADT7410
from PyICe.lab_instruments.AD5693R import AD5693R
from PyICe.lab_instruments.AD5272 import AD5272
from PyICe.lab_instruments.AD5667R import AD5667R
from PyICe.lab_instruments.PCF8574 import PCF8574
from PyICe.lab_instruments.CAT5140 import CAT5140
from PyICe.lab_instruments.agilent_34401a import agilent_34401a
from PyICe.lab_instruments.agilent_e36xxa import agilent_e36xxa
from PyICe.lab_instruments.BR24H64 import BR24H64
from PyICe.lab_instruments.smu import scpi_smu, keithley_2400, keithley_2600
from PyICe.lab_instruments.hameg_4040 import hameg_4040
from PyICe.lab_instruments.rigol_DG800 import rigol_DG800
from PyICe.lab_interfaces import interface_visa


@pytest.fixture
def twi(master_instance):
    """Create a deterministic TWI dummy interface via the interface factory."""
    iface = master_instance.get_twi_dummy_interface(delay=0, p_change=0)
    return iface


class TestTMP117:

    @pytest.fixture
    def tmp117(self, twi):
        return TMP117(interface_twi=twi, addr7=0x48)

    def test_instantiation(self, tmp117):
        assert tmp117.get_name().startswith('Analog Devices TMP117')

    def test_enable_writes_config(self, twi, tmp117):
        data = twi._cc_data.get(0x01)
        assert data is not None

    def test_read_temp_positive(self, twi, tmp117):
        # 25.0°C = 25.0 * 128 = 3200 = 0x0C80
        # TMP117 returns MSB-first, so register holds swap_endian(0x0C80, 2) =
        # 0x800C
        raw = swap_endian(3200, elementCount=2)
        twi._cc_data[0x00] = raw
        temp = tmp117.read_temp()
        assert temp == pytest.approx(25.0)

    def test_read_temp_negative(self, twi, tmp117):
        # -10.0°C = -10 * 128 = -1280
        # Two's complement 16-bit: 65536 - 1280 = 64256 = 0xFB00
        # Swap endian for MSB-first: swap_endian(0xFB00, 2) = 0x00FB
        from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
        code = signedToTwosComplement(-1280, 16)
        raw = swap_endian(code, elementCount=2)
        twi._cc_data[0x00] = raw
        temp = tmp117.read_temp()
        assert temp == pytest.approx(-10.0)

    def test_read_temp_zero(self, twi, tmp117):
        twi._cc_data[0x00] = 0x0000
        temp = tmp117.read_temp()
        assert temp == 0.0

    def test_read_id(self, twi, tmp117):
        # Device ID register: revision in [15:12], device in [11:0]
        # Example: revision=0x1, device=0x117
        twi._cc_data[0x0F] = (0x1 << 12) | 0x117
        result = tmp117.read_id()
        assert result['revision'] == 1
        assert result['device'] == 0x117

    def test_add_channel(self, twi, tmp117, master_instance):
        tmp117.add_channel('temperature')
        master_instance.add(tmp117)
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        temp = master_instance.read_channel('temperature')
        assert temp == pytest.approx(25.0)

    def test_shutdown_writes_config(self, twi, tmp117):
        tmp117.enable(False)
        config = twi._cc_data[0x01]
        assert (config >> 10) & 0x03 == 0b01


class TestAD5259:

    @pytest.fixture
    def pot(self, twi):
        return AD5259(interface_twi=twi, addr7=0x18,
                      full_scale_ohms=10000)

    def test_instantiation(self, pot):
        assert pot.get_name().startswith('Analog Devices')

    def test_invalid_address_raises(self, twi):
        with pytest.raises(ValueError, match="only supports"):
            AD5259(interface_twi=twi, addr7=0x99, full_scale_ohms=10000)

    def test_write_code(self, twi, pot):
        pot.add_channel_code('code')
        pot['code'].write(128)
        assert twi._cc_data[pot.WRITE_TO_RDAC] == 128

    def test_read_code(self, twi, pot):
        pot.add_channel_code_readback('readback')
        twi._cc_data[pot.READ_FROM_RDAC] = 200
        val = pot['readback'].read()
        assert val == 200

    def test_write_read_roundtrip(self, twi, pot):
        pot.add_channel_code('code')
        pot.add_channel_code_readback('readback')
        pot['code'].write(100)
        # Write goes to WRITE_TO_RDAC command, read comes from READ_FROM_RDAC
        # Both are command 0x00, so dummy stores them at the same key
        val = pot['readback'].read()
        assert val == 100

    def test_wiper_write_scaled(self, twi, pot):
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(0.5)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 128

    def test_wiper_write_zero(self, twi, pot):
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(0.0)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 0

    def test_wiper_write_full_scale(self, twi, pot):
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(1.0)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 255

    def test_wiper_read(self, twi, pot):
        pot.add_channel_wiper('wiper')
        twi._cc_data[pot.READ_FROM_RDAC] = 128
        val = pot['wiper'].read()
        assert val == pytest.approx(0.5)

    def test_add_all_channels(self, twi, pot, master_instance):
        pot.add_all_channels('pot')
        master_instance.add(pot)
        names = master_instance.get_all_channel_names()
        assert 'pot_wiper' in names
        assert 'pot_code' in names
        assert 'pot_code_readback' in names

    def test_wiper_out_of_range_raises(self, twi, pot):
        pot.add_channel_wiper('wiper')
        with pytest.raises(AssertionError):
            pot['wiper'].write(1.5)
        with pytest.raises(AssertionError):
            pot['wiper'].write(-0.1)


class TestADT7410:

    @pytest.fixture
    def sensor(self, twi):
        return ADT7410(interface_twi=twi, addr7=0x48)

    def test_instantiation(self, sensor):
        assert sensor.get_name().startswith('Analog Devices ADT7410')

    def test_enable_writes_config(self, twi, sensor):
        assert twi._cc_data[0x03] == (0b1 << 7)

    def test_read_temp_positive(self, twi, sensor):
        # 25.0°C = 25.0 * 128 = 3200; MSB-first → swap_endian
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        assert sensor.read_temp() == pytest.approx(25.0)

    def test_read_temp_negative(self, twi, sensor):
        from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
        code = signedToTwosComplement(-1280, 16)  # -10.0°C
        twi._cc_data[0x00] = swap_endian(code, elementCount=2)
        assert sensor.read_temp() == pytest.approx(-10.0)

    def test_read_temp_zero(self, twi, sensor):
        twi._cc_data[0x00] = 0x0000
        assert sensor.read_temp() == 0.0

    def test_read_id(self, twi, sensor):
        # revision in [2:0], manufacturer in [7:3]
        twi._cc_data[0x0B] = (0x19 << 3) | 0x05
        result = sensor.read_id()
        assert result['revision'] == 5
        assert result['manufacturer'] == 0x19

    def test_add_channel(self, twi, sensor, master_instance):
        sensor.add_channel('temperature')
        master_instance.add(sensor)
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        assert master_instance.read_channel(
            'temperature') == pytest.approx(25.0)

    def test_shutdown(self, twi, sensor):
        sensor.enable(False)
        config = twi._cc_data[0x03]
        assert (config >> 5) & 0x03 == 0b11


class TestAD5693R:

    @pytest.fixture
    def dac(self, twi):
        return AD5693R(interface_twi=twi, addr7=0x4C)

    def test_instantiation(self, dac):
        assert dac.get_name().startswith('Analog Devices AD5693R')

    def test_init_writes_control_reg(self, twi, dac):
        assert 0x40 in twi._cc_data

    def test_set_code(self, twi, dac):
        dac._set_code(0x8000)
        assert twi._cc_data[0x30] == swap_endian(0x8000, elementCount=2)

    def test_set_voltage_midscale(self, twi, dac):
        # Default gain=2, vref=2.5 → full scale=5.0V, midscale=2.5V →
        # code=32768
        dac._set_voltage(2.5)
        expected_code = int(2.5 / 2.0 / 2.5 * 65536)
        assert twi._cc_data[0x30] == swap_endian(expected_code, elementCount=2)

    def test_gain_setting(self, twi, dac):
        dac._set_gain(1)
        assert dac.gain_code == 0x0000
        dac._set_gain(2)
        assert dac.gain_code == 0x0800

    def test_invalid_gain_raises(self, dac):
        with pytest.raises(Exception, match="gain setting"):
            dac._set_gain(3)

    def test_output_impedance(self, twi, dac):
        dac._set_outputz("Z")
        assert dac.impedance == 0x6000
        dac._set_outputz(0)
        assert dac.impedance == 0x0000

    def test_add_channel_voltage(self, twi, dac, master_instance):
        dac.add_channel('vout')
        master_instance.add(dac)
        master_instance['vout'].write(1.0)
        expected_code = int(1.0 / 2.0 / 2.5 * 65536)
        assert twi._cc_data[0x30] == swap_endian(expected_code, elementCount=2)

    def test_add_channel_code(self, twi, dac, master_instance):
        dac.add_channel_code('code')
        master_instance.add(dac)
        master_instance['code'].write(1000)
        assert twi._cc_data[0x30] == swap_endian(1000, elementCount=2)


class TestAD5272:

    @pytest.fixture
    def pot(self, twi):
        return AD5272(interface_twi=twi, addr7=0x2C, full_scale_ohms=100000)

    def test_instantiation(self, pot):
        assert pot.get_name().startswith('Analog Devices')

    def test_invalid_address_raises(self, twi):
        with pytest.raises(ValueError, match="only supports"):
            AD5272(interface_twi=twi, addr7=0x30, full_scale_ohms=100000)

    def test_write_code(self, twi, pot):
        pot.set_output(512)
        # msbyte = 0x1<<2 | 512>>8 = 0x06, lsbyte = 0x00
        # Written via _write_byte → write_register(addr7, msbyte, lsbyte, 8)
        assert twi._cc_data[0x06] == 0x00

    def test_write_percent(self, twi, pot):
        pot._write_percent(0.5)
        # 0.5 * 1024 = 512 → msbyte=0x06, lsbyte=0x00
        assert twi._cc_data[0x06] == 0x00

    def test_add_channel_code(self, twi, pot, master_instance):
        pot.add_channel_code('code')
        master_instance.add(pot)
        master_instance['code'].write(100)
        # msbyte = 0x1<<2 | 0 = 0x04, lsbyte = 100
        assert twi._cc_data[0x04] == 100


class TestAD5667R:

    @pytest.fixture
    def dac(self, twi):
        return AD5667R(interface_twi=twi, addr7=0x0C)

    def test_instantiation(self, dac):
        assert dac.get_name().startswith('Analog Devices AD5667R')

    def test_write_dac_a_code(self, twi, dac):
        dac._write_dac_A_code(0x8000)
        # command = WRITE_DACn_UPDATE_DACn(0b011<<3) | DAC_A(0b000) = 0x18
        cmd = (0b011 << 3) | 0b000
        assert cmd in twi._cc_data

    def test_write_dac_a_voltage(self, twi, dac):
        # 2.5V → code = 2.5 / 2.0 / 2.5 * 65536 = 32768
        dac._set_dac_A_voltage(2.5)
        cmd = (0b011 << 3) | 0b000  # WRITE_DACn_UPDATE_DACn | DAC_A
        assert cmd in twi._cc_data

    def test_volts_to_code(self, dac):
        assert dac._volts_to_code(0.0) == 0
        assert dac._volts_to_code(2.5) == 32768

    def test_volts_out_of_range_raises(self, dac):
        with pytest.raises(Exception, match="out of range"):
            dac._volts_to_code(6.0)

    def test_add_channel_dac_a(self, twi, dac, master_instance):
        dac.add_channel_DAC_A('dac_a')
        master_instance.add(dac)
        master_instance['dac_a'].write(1.0)
        cmd = (0b011 << 3) | 0b000
        assert cmd in twi._cc_data


class TestPCF8574:

    @pytest.fixture
    def gpio(self, twi):
        return PCF8574(interface_twi=twi, addr7=0x20)

    def test_instantiation(self, gpio):
        assert gpio.get_name().startswith('PCF8574')

    def test_invalid_address_raises(self, twi):
        with pytest.raises(ValueError):
            PCF8574(interface_twi=twi, addr7=0x30)

    def test_write_pin_high(self, twi, gpio):
        gpio.add_channel_writepin('pin0', 0)
        gpio['pin0'].write(1)
        # state should be 0x01, written as commandCode via send_byte
        assert twi._cc_data[0x01] is None  # data_size=0 stores None as data

    def test_write_multiple_pins(self, twi, gpio):
        gpio.add_channel_writepin('p0', 0)
        gpio.add_channel_writepin('p3', 3)
        gpio['p0'].write(1)
        gpio['p3'].write(1)
        # state should be 0b00001001 = 0x09
        assert gpio.state == 0x09
        assert 0x09 in twi._cc_data

    def test_write_pin_low_clears_bit(self, twi, gpio):
        gpio.add_channel_writepin('p0', 0)
        gpio['p0'].write(1)
        gpio['p0'].write(0)
        assert gpio.state == 0x00


class TestCAT5140:

    @pytest.fixture
    def pot(self, twi):
        return CAT5140(interface_twi=twi)

    def test_instantiation(self, pot):
        assert pot.addr7 == 0x28

    def test_write_code(self, twi, pot):
        pot.set_output(128)
        assert twi._cc_data[0x00] == 128

    def test_read_code(self, twi, pot):
        pot.set_output(200)
        assert pot.get_output() == 200

    def test_write_percent_half(self, twi, pot):
        pot._write_percent(0.5)
        assert twi._cc_data[0x00] == 128

    def test_write_percent_full(self, twi, pot):
        pot._write_percent(1.0)
        assert twi._cc_data[0x00] == 255

    def test_add_channel_code(self, twi, pot, master_instance):
        pot.add_channel_code('wiper')
        master_instance.add(pot)
        master_instance['wiper'].write(100)
        assert twi._cc_data[0x00] == 100

    def test_add_channel_percent_readback(self, twi, pot):
        pot.add_channel_percent_readback('pct')
        twi._cc_data[0x00] = 128
        val = pot['pct'].read()
        assert val == pytest.approx(128 / 255.0)


class TestAgilent34401a:

    @pytest.fixture
    def dmm(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "3.300000E+00"
        instrument = agilent_34401a(mock_iface)
        master_instance.add(instrument)
        return instrument, mock_iface

    def test_instantiation_sends_config(self, dmm):
        _, mock = dmm
        # __init__ calls config_dc_voltage which writes several SCPI commands
        write_calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLT:DC' in c for c in write_calls)

    def test_read_meter(self, dmm):
        instrument, mock = dmm
        result = instrument.read_meter()
        mock.ask.assert_called_with("READ?")
        assert result == pytest.approx(3.3)

    def test_read_meter_negative(self, dmm):
        instrument, mock = dmm
        mock.ask.return_value = "-1.234567E-03"
        result = instrument.read_meter()
        assert result == pytest.approx(-0.001234567)

    def test_config_dc_current(self, dmm):
        instrument, mock = dmm
        mock.reset_mock()
        instrument.config_dc_current(NPLC=10)
        write_calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent:DC' in c for c in write_calls)
        assert any('10' in c for c in write_calls)

    def test_invalid_nplc_raises(self, dmm):
        instrument, _ = dmm
        with pytest.raises(Exception, match="Not a valid NPLC"):
            instrument.config_dc_voltage(NPLC=5)

    def test_add_channel_read(self, dmm):
        instrument, mock = dmm
        instrument.add_channel('voltage')
        mock.ask.return_value = "5.000000E+00"
        val = instrument['voltage'].read()
        assert val == pytest.approx(5.0)


class TestBR24H64:

    @pytest.fixture
    def eeprom(self, twi):
        return BR24H64(interface_twi=twi, addr7=0x50)

    def test_instantiation(self, eeprom):
        assert eeprom.get_name().startswith('64KBit')

    def test_invalid_address_raises(self, twi):
        with pytest.raises(ValueError):
            BR24H64(interface_twi=twi, addr7=0x60)

    def test_write_location(self, twi, eeprom):
        eeprom.write_location(0, 0xAB)
        # commandCode = location >> 8 = 0, data = (location & 0xff) + (data <<
        # 8)
        assert twi._cc_data[0x00] == (0x00) + (0xAB << 8)

    def test_write_location_high_address(self, twi, eeprom):
        eeprom.write_location(0x0100, 0x42)
        # commandCode = 0x0100 >> 8 = 1, data = (0x00) + (0x42 << 8)
        assert twi._cc_data[0x01] == (0x00) + (0x42 << 8)

    def test_write_out_of_range_raises(self, eeprom):
        with pytest.raises(Exception, match="outside physical media"):
            eeprom.write_location(9000, 0x00)

    def test_write_data_out_of_range_raises(self, eeprom):
        with pytest.raises(Exception, match="outside the range"):
            eeprom.write_location(0, 256)


class TestAgilentE36xxa:

    @pytest.fixture
    def supply(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "3.300000E+00"
        psu = agilent_e36xxa.__new__(agilent_e36xxa)
        instrument.__init__(psu, 'e36xxa_test')
        psu._base_name = 'e36xxa'
        psu._default_write_delay = 0
        psu._debug_comms = False
        psu.add_interface_visa(mock_iface)
        master_instance.add(psu)
        return psu, mock_iface

    def test_set_voltage(self, supply):
        psu, mock = supply
        psu.set_voltage("OUT1", 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INSTrument:SELect OUT1' in c for c in calls)
        assert any('VOLTage 3.3' in c for c in calls)

    def test_set_current(self, supply):
        psu, mock = supply
        psu.set_current("OUT1", 0.5)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent 0.5' in c for c in calls)

    def test_read_vsense(self, supply):
        psu, mock = supply
        mock.ask.return_value = "5.000000E+00"
        result = psu.read_vsense("OUT1")
        assert result == pytest.approx(5.0)

    def test_read_isense(self, supply):
        psu, mock = supply
        mock.ask.return_value = "1.234000E-01"
        result = psu.read_isense("OUT1")
        assert result == pytest.approx(0.1234)

    def test_add_channel_voltage(self, supply):
        psu, mock = supply
        psu.add_channel_voltage('vout', 'OUT1')
        psu['vout'].write(1.8)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage 1.8' in c for c in calls)

    def test_enable_output(self, supply):
        psu, mock = supply
        psu.enable_output(True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTput:STATe ON' in c for c in calls)


class TestScpiSmu:

    @pytest.fixture
    def smu_inst(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "1.000E+00,2.000E-03,9.91E+37,0.0,0"
        inst = scpi_smu.__new__(scpi_smu)
        instrument.__init__(inst, 'scpi_smu_test')
        inst._base_name = 'scpi_smu'
        inst._debug_comms = False
        inst._parse_float = float
        inst.add_interface_visa(mock_iface)
        inst._configured_channels = {}
        master_instance.add(inst)
        return inst, mock_iface

    def test_add_channels(self, smu_inst):
        inst, mock = smu_inst
        channels = inst.add_channels('smu')
        assert len(channels) == 6
        names = [ch.get_name() for ch in channels]
        assert 'smu_vforce' in names
        assert 'smu_iforce' in names
        assert 'smu_vsense' in names
        assert 'smu_isense' in names
        assert 'smu_vcompl' in names
        assert 'smu_icompl' in names

    def test_voltage_force(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_voltage_force('vf')
        inst['vf'].write(3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage' in c and '3.3' in c for c in calls)
        assert any('FUNCtion:MODE VOLTage' in c for c in calls)
        assert any('OUTPut' in c and 'ON' in c for c in calls)

    def test_current_force(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_current_force('if')
        inst['if'].write(0.001)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent' in c and '0.001' in c for c in calls)
        assert any('FUNCtion:MODE CURRent' in c for c in calls)

    def test_voltage_sense(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_voltage_sense('vs')
        mock.ask.return_value = "3.300E+00,1.000E-03,9.91E+37,0.0,0"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_current_sense(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_current_sense('is_ch')
        mock.ask.return_value = "5.000E+00,2.500E-03,9.91E+37,0.0,0"
        val = inst['is_ch'].read()
        assert val == pytest.approx(0.0025)

    def test_compliance_write(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_voltage_compliance('vcompl')
        inst['vcompl'].write(20)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:DC:PROTection:LEVel 20' in c for c in calls)

    def test_exclusive_vforce_clears_iforce(self, smu_inst):
        inst, mock = smu_inst
        inst.add_channel_voltage_force('vf')
        inst.add_channel_current_force('if')
        inst['if'].write(0.01)
        inst['vf'].write(5.0)
        # Writing vforce should clear iforce cached value
        assert inst['if'].read() is None


class TestHameg4040:

    @pytest.fixture
    def supply(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "1"
        inst = hameg_4040.__new__(hameg_4040)
        instrument.__init__(inst, 'hameg_test')
        inst._base_name = 'hameg_4040'
        inst._debug_comms = False
        inst.retries = 0
        inst.hameg_suck_time = 0
        inst.add_interface_visa(mock_iface)
        master_instance.add(inst)
        return inst, mock_iface

    def test_write_voltage(self, supply):
        inst, mock = supply
        inst._write_voltage(1, 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INST:NSEL 1' in c for c in calls)
        assert any('SOURce:VOLTage 3.3' in c for c in calls)

    def test_write_current(self, supply):
        inst, mock = supply
        inst._write_current(2, 0.5)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INST:NSEL 2' in c for c in calls)
        assert any('SOURce:CURRent 0.5' in c for c in calls)

    def test_read_vsense(self, supply):
        inst, mock = supply
        mock.ask.return_value = "3.300"
        val = inst._read_vsense(1)
        assert val == pytest.approx(3.3)

    def test_read_isense(self, supply):
        inst, mock = supply
        mock.ask.return_value = "0.125"
        val = inst._read_isense(1)
        assert val == pytest.approx(0.125)

    def test_write_enable(self, supply):
        inst, mock = supply
        inst._write_enable(1, True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPUT:STATE ON' in c for c in calls)

    def test_write_enable_off(self, supply):
        inst, mock = supply
        inst._write_enable(1, False)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPUT:STATE OFF' in c for c in calls)

    def test_master_enable(self, supply):
        inst, mock = supply
        inst._write_master_enable(True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut:GENeral ON' in c for c in calls)

    def test_add_channel_voltage(self, supply):
        inst, mock = supply
        inst.add_channel_voltage('ch1_v', 1)
        mock.reset_mock()
        mock.ask.return_value = "1"
        inst['ch1_v'].write(5.0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('SOURce:VOLTage 5.0' in c for c in calls)

    def test_voltage_limits(self, supply):
        inst, mock = supply
        ch = inst.add_channel_voltage('ch1_v', 1)
        assert ch.get_max_write_limit() == 32.05
        assert ch.get_min_write_limit() == 0


class TestRigolDG800:

    @pytest.fixture
    def funcgen(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        inst = rigol_DG800.__new__(rigol_DG800)
        instrument.__init__(inst, 'rigol_test')
        inst._base_name = 'Rigol_DG800'
        inst._debug_comms = False
        inst.add_interface_visa(mock_iface)
        inst.instrument = mock_iface
        master_instance.add(inst)
        return inst, mock_iface

    def test_write_high_voltage(self, funcgen):
        inst, mock = funcgen
        inst._write_high_voltage(1, 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel:IMMediate:HIGH 3.3' in c for c in calls)

    def test_write_low_voltage(self, funcgen):
        inst, mock = funcgen
        inst._write_low_voltage(1, 0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel:IMMediate:LOW 0' in c for c in calls)

    def test_write_pulse_width(self, funcgen):
        inst, mock = funcgen
        inst._write_pulse_width(1, 50e-6)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('PULSe:WIDTh 5e-05' in c for c in calls)

    def test_write_output_enable(self, funcgen):
        inst, mock = funcgen
        inst._write_output_enable(1, 'ON')
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut1:STATE ON' in c for c in calls)

    def test_add_channel_enable(self, funcgen):
        inst, mock = funcgen
        ch = inst.add_channel_enable('out1', 1)
        mock.reset_mock()
        ch.write('ON')
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut1:STATE ON' in c for c in calls)

    def test_add_channel_pulse_width(self, funcgen):
        inst, mock = funcgen
        ch = inst.add_channel_pulse_width('pw', 1)
        assert ch.get_min_write_limit() == 30e-9


class TestKeithley2400:

    @pytest.fixture
    def smu(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "1.000E+00,2.000E-03,9.91E+37,0.0,0"
        inst = keithley_2400.__new__(keithley_2400)
        instrument.__init__(inst, 'k2400_test')
        inst._base_name = 'Keithley 2400'
        inst._debug_comms = False
        inst.add_interface_visa(mock_iface)
        inst._configured_channels = {}
        master_instance.add(inst)
        return inst, mock_iface

    def test_add_channel_voltage_force(self, smu):
        inst, mock = smu
        ch = inst.add_channel_voltage_force('vf')
        assert ch.get_min_write_limit() == -200
        assert ch.get_max_write_limit() == 200
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('RANGe:AUTO ON' in c for c in calls)

    def test_add_channel_current_force(self, smu):
        inst, mock = smu
        ch = inst.add_channel_current_force('if')
        assert ch.get_min_write_limit() == -1
        assert ch.get_max_write_limit() == 1

    def test_voltage_force_sends_scpi(self, smu):
        inst, mock = smu
        inst.add_channel_voltage_force('vf')
        mock.reset_mock()
        inst['vf'].write(3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel' in c and '3.3' in c for c in calls)
        assert any('OUTPut' in c and 'ON' in c for c in calls)

    def test_voltage_sense(self, smu):
        inst, mock = smu
        inst.add_channel_voltage_sense('vs')
        mock.ask.return_value = "3.300E+00,1.000E-03,9.91E+37,0.0,0"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_current_sense(self, smu):
        inst, mock = smu
        inst.add_channel_current_sense('is_ch')
        mock.ask.return_value = "5.000E+00,2.500E-03,9.91E+37,0.0,0"
        val = inst['is_ch'].read()
        assert val == pytest.approx(0.0025)


class TestKeithley2600:

    @pytest.fixture
    def smu(self, master_instance):
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "3.300000e+00"
        mock_iface.read.return_value = ""
        inst = keithley_2600.__new__(keithley_2600)
        instrument.__init__(inst, 'k2600_test')
        inst._base_name = 'Keithley 2600'
        inst._debug_comms = False
        inst.add_interface_visa(mock_iface)
        inst._configured_channels = {}
        master_instance.add(inst)
        return inst, mock_iface

    def test_channel_id(self, smu):
        inst, _ = smu
        assert inst._channel_id(1) == 'a'
        assert inst._channel_id(2) == 'b'

    def test_voltage_force(self, smu):
        inst, mock = smu
        inst.add_channel_voltage_force('vf', channel_number=1)
        mock.reset_mock()
        inst['vf'].write(5.0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smua.source.levelv = 5.0' in c for c in calls)
        assert any('OUTPUT_DCVOLTS' in c for c in calls)
        assert any('OUTPUT_ON' in c for c in calls)

    def test_current_force_channel_b(self, smu):
        inst, mock = smu
        inst.add_channel_current_force('if', channel_number=2)
        mock.reset_mock()
        inst['if'].write(0.001)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smub.source.leveli = 0.001' in c for c in calls)
        assert any('OUTPUT_DCAMPS' in c for c in calls)

    def test_voltage_sense(self, smu):
        inst, mock = smu
        inst.add_channel_voltage_sense('vs', channel_number=1)
        mock.ask.return_value = "3.300000e+00"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_compliance_write(self, smu):
        inst, mock = smu
        inst.add_channel_current_compliance('icompl', channel_number=1)
        mock.reset_mock()
        inst['icompl'].write(0.1)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smua.source.limiti = 0.1' in c for c in calls)
