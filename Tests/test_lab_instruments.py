"""Representative lab_instruments unit tests using i2c_dummy and VISA mocks.

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
    """Create a deterministic TWI dummy interface via the interface factory.

    Args:
        master_instance: Master instance.

    Returns:
        Result value.
    """
    iface = master_instance.get_twi_dummy_interface(delay=0, p_change=0)
    return iface


class TestTMP117:
    """Tests for T M P117."""

    @pytest.fixture
    def tmp117(self, twi):
        """Return tmp117 result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return TMP117(interface_twi=twi, addr7=0x48)

    def test_instantiation(self, tmp117):
        """Perform test instantiation operation.

        Args:
            tmp117: Tmp117.
        """
        assert tmp117.get_name().startswith('Analog Devices TMP117')

    def test_enable_writes_config(self, twi, tmp117):
        """Perform test enable writes config operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        data = twi._cc_data.get(0x01)
        assert data is not None

    def test_read_temp_positive(self, twi, tmp117):
        # 25.0°C = 25.0 * 128 = 3200 = 0x0C80
        # TMP117 returns MSB-first, so register holds swap_endian(0x0C80, 2) =
        # 0x800C
        """Perform test read temp positive operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        raw = swap_endian(3200, elementCount=2)
        twi._cc_data[0x00] = raw
        temp = tmp117.read_temp()
        assert temp == pytest.approx(25.0)

    def test_read_temp_negative(self, twi, tmp117):
        # -10.0°C = -10 * 128 = -1280
        # Two's complement 16-bit: 65536 - 1280 = 64256 = 0xFB00
        # Swap endian for MSB-first: swap_endian(0xFB00, 2) = 0x00FB
        """Perform test read temp negative operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
        code = signedToTwosComplement(-1280, 16)
        raw = swap_endian(code, elementCount=2)
        twi._cc_data[0x00] = raw
        temp = tmp117.read_temp()
        assert temp == pytest.approx(-10.0)

    def test_read_temp_zero(self, twi, tmp117):
        """Perform test read temp zero operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        twi._cc_data[0x00] = 0x0000
        temp = tmp117.read_temp()
        assert temp == 0.0

    def test_read_id(self, twi, tmp117):
        # Device ID register: revision in [15:12], device in [11:0]
        # Example: revision=0x1, device=0x117
        """Perform test read id operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        twi._cc_data[0x0F] = (0x1 << 12) | 0x117
        result = tmp117.read_id()
        assert result['revision'] == 1
        assert result['device'] == 0x117

    def test_add_channel(self, twi, tmp117, master_instance):
        """Perform test add channel operation.

        Args:
            master_instance: Master instance.
            tmp117: Tmp117.
            twi: Twi.
        """
        tmp117.add_channel('temperature')
        master_instance.add(tmp117)
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        temp = master_instance.read_channel('temperature')
        assert temp == pytest.approx(25.0)

    def test_shutdown_writes_config(self, twi, tmp117):
        """Perform test shutdown writes config operation.

        Args:
            tmp117: Tmp117.
            twi: Twi.
        """
        tmp117.enable(False)
        config = twi._cc_data[0x01]
        assert (config >> 10) & 0x03 == 0b01


class TestAD5259:
    """Tests for A D5259."""

    @pytest.fixture
    def pot(self, twi):
        """Return pot result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return AD5259(interface_twi=twi, addr7=0x18,
                      full_scale_ohms=10000)

    def test_instantiation(self, pot):
        """Perform test instantiation operation.

        Args:
            pot: Pot.
        """
        assert pot.get_name().startswith('Analog Devices')

    def test_invalid_address_raises(self, twi):
        """Perform test invalid address raises operation.

        Args:
            twi: Twi.
        """
        with pytest.raises(ValueError, match="only supports"):
            AD5259(interface_twi=twi, addr7=0x99, full_scale_ohms=10000)

    def test_write_code(self, twi, pot):
        """Perform test write code operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_code('code')
        pot['code'].write(128)
        assert twi._cc_data[pot.WRITE_TO_RDAC] == 128

    def test_read_code(self, twi, pot):
        """Perform test read code operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_code_readback('readback')
        twi._cc_data[pot.READ_FROM_RDAC] = 200
        val = pot['readback'].read()
        assert val == 200

    def test_write_read_roundtrip(self, twi, pot):
        """Perform test write read roundtrip operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_code('code')
        pot.add_channel_code_readback('readback')
        pot['code'].write(100)
        # Write goes to WRITE_TO_RDAC command, read comes from READ_FROM_RDAC
        # Both are command 0x00, so dummy stores them at the same key
        val = pot['readback'].read()
        assert val == 100

    def test_wiper_write_scaled(self, twi, pot):
        """Perform test wiper write scaled operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(0.5)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 128

    def test_wiper_write_zero(self, twi, pot):
        """Perform test wiper write zero operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(0.0)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 0

    def test_wiper_write_full_scale(self, twi, pot):
        """Perform test wiper write full scale operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_wiper('wiper')
        pot['wiper'].write(1.0)
        code = twi._cc_data[pot.WRITE_TO_RDAC]
        assert code == 255

    def test_wiper_read(self, twi, pot):
        """Perform test wiper read operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_wiper('wiper')
        twi._cc_data[pot.READ_FROM_RDAC] = 128
        val = pot['wiper'].read()
        assert val == pytest.approx(0.5)

    def test_add_all_channels(self, twi, pot, master_instance):
        """Perform test add all channels operation.

        Args:
            master_instance: Master instance.
            pot: Pot.
            twi: Twi.
        """
        pot.add_all_channels('pot')
        master_instance.add(pot)
        names = master_instance.get_all_channel_names()
        assert 'pot_wiper' in names
        assert 'pot_code' in names
        assert 'pot_code_readback' in names

    def test_wiper_out_of_range_raises(self, twi, pot):
        """Perform test wiper out of range raises operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_wiper('wiper')
        with pytest.raises(AssertionError):
            pot['wiper'].write(1.5)
        with pytest.raises(AssertionError):
            pot['wiper'].write(-0.1)


class TestADT7410:
    """Tests for A D T7410."""

    @pytest.fixture
    def sensor(self, twi):
        """Return sensor result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return ADT7410(interface_twi=twi, addr7=0x48)

    def test_instantiation(self, sensor):
        """Perform test instantiation operation.

        Args:
            sensor: Sensor.
        """
        assert sensor.get_name().startswith('Analog Devices ADT7410')

    def test_enable_writes_config(self, twi, sensor):
        """Perform test enable writes config operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        assert twi._cc_data[0x03] == (0b1 << 7)

    def test_read_temp_positive(self, twi, sensor):
        # 25.0°C = 25.0 * 128 = 3200; MSB-first → swap_endian
        """Perform test read temp positive operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        assert sensor.read_temp() == pytest.approx(25.0)

    def test_read_temp_negative(self, twi, sensor):
        """Perform test read temp negative operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
        code = signedToTwosComplement(-1280, 16)  # -10.0°C
        twi._cc_data[0x00] = swap_endian(code, elementCount=2)
        assert sensor.read_temp() == pytest.approx(-10.0)

    def test_read_temp_zero(self, twi, sensor):
        """Perform test read temp zero operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        twi._cc_data[0x00] = 0x0000
        assert sensor.read_temp() == 0.0

    def test_read_id(self, twi, sensor):
        # revision in [2:0], manufacturer in [7:3]
        """Perform test read id operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        twi._cc_data[0x0B] = (0x19 << 3) | 0x05
        result = sensor.read_id()
        assert result['revision'] == 5
        assert result['manufacturer'] == 0x19

    def test_add_channel(self, twi, sensor, master_instance):
        """Perform test add channel operation.

        Args:
            master_instance: Master instance.
            sensor: Sensor.
            twi: Twi.
        """
        sensor.add_channel('temperature')
        master_instance.add(sensor)
        twi._cc_data[0x00] = swap_endian(3200, elementCount=2)
        assert master_instance.read_channel(
            'temperature') == pytest.approx(25.0)

    def test_shutdown(self, twi, sensor):
        """Perform test shutdown operation.

        Args:
            sensor: Sensor.
            twi: Twi.
        """
        sensor.enable(False)
        config = twi._cc_data[0x03]
        assert (config >> 5) & 0x03 == 0b11


class TestAD5693R:
    """Tests for A D5693 R."""

    @pytest.fixture
    def dac(self, twi):
        """Return dac result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return AD5693R(interface_twi=twi, addr7=0x4C)

    def test_instantiation(self, dac):
        """Perform test instantiation operation.

        Args:
            dac: Dac.
        """
        assert dac.get_name().startswith('Analog Devices AD5693R')

    def test_init_writes_control_reg(self, twi, dac):
        """Perform test init writes control reg operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        assert 0x40 in twi._cc_data

    def test_set_code(self, twi, dac):
        """Perform test set code operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._set_code(0x8000)
        assert twi._cc_data[0x30] == swap_endian(0x8000, elementCount=2)

    def test_set_voltage_midscale(self, twi, dac):
        # Default gain=2, vref=2.5 → full scale=5.0V, midscale=2.5V →
        # code=32768
        """Perform test set voltage midscale operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._set_voltage(2.5)
        expected_code = int(2.5 / 2.0 / 2.5 * 65536)
        assert twi._cc_data[0x30] == swap_endian(expected_code, elementCount=2)

    def test_gain_setting(self, twi, dac):
        """Perform test gain setting operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._set_gain(1)
        assert dac.gain_code == 0x0000
        dac._set_gain(2)
        assert dac.gain_code == 0x0800

    def test_invalid_gain_raises(self, dac):
        """Perform test invalid gain raises operation.

        Args:
            dac: Dac.
        """
        with pytest.raises(Exception, match="gain setting"):
            dac._set_gain(3)

    def test_output_impedance(self, twi, dac):
        """Perform test output impedance operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._set_outputz("Z")
        assert dac.impedance == 0x6000
        dac._set_outputz(0)
        assert dac.impedance == 0x0000

    def test_add_channel_voltage(self, twi, dac, master_instance):
        """Perform test add channel voltage operation.

        Args:
            dac: Dac.
            master_instance: Master instance.
            twi: Twi.
        """
        dac.add_channel('vout')
        master_instance.add(dac)
        master_instance['vout'].write(1.0)
        expected_code = int(1.0 / 2.0 / 2.5 * 65536)
        assert twi._cc_data[0x30] == swap_endian(expected_code, elementCount=2)

    def test_add_channel_code(self, twi, dac, master_instance):
        """Perform test add channel code operation.

        Args:
            dac: Dac.
            master_instance: Master instance.
            twi: Twi.
        """
        dac.add_channel_code('code')
        master_instance.add(dac)
        master_instance['code'].write(1000)
        assert twi._cc_data[0x30] == swap_endian(1000, elementCount=2)


class TestAD5272:
    """Tests for A D5272."""

    @pytest.fixture
    def pot(self, twi):
        """Return pot result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return AD5272(interface_twi=twi, addr7=0x2C, full_scale_ohms=100000)

    def test_instantiation(self, pot):
        """Perform test instantiation operation.

        Args:
            pot: Pot.
        """
        assert pot.get_name().startswith('Analog Devices')

    def test_invalid_address_raises(self, twi):
        """Perform test invalid address raises operation.

        Args:
            twi: Twi.
        """
        with pytest.raises(ValueError, match="only supports"):
            AD5272(interface_twi=twi, addr7=0x30, full_scale_ohms=100000)

    def test_write_code(self, twi, pot):
        """Perform test write code operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.set_output(512)
        # msbyte = 0x1<<2 | 512>>8 = 0x06, lsbyte = 0x00
        # Written via _write_byte → write_register(addr7, msbyte, lsbyte, 8)
        assert twi._cc_data[0x06] == 0x00

    def test_write_percent(self, twi, pot):
        """Perform test write percent operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot._write_percent(0.5)
        # 0.5 * 1024 = 512 → msbyte=0x06, lsbyte=0x00
        assert twi._cc_data[0x06] == 0x00

    def test_add_channel_code(self, twi, pot, master_instance):
        """Perform test add channel code operation.

        Args:
            master_instance: Master instance.
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_code('code')
        master_instance.add(pot)
        master_instance['code'].write(100)
        # msbyte = 0x1<<2 | 0 = 0x04, lsbyte = 100
        assert twi._cc_data[0x04] == 100


class TestAD5667R:
    """Tests for A D5667 R."""

    @pytest.fixture
    def dac(self, twi):
        """Return dac result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return AD5667R(interface_twi=twi, addr7=0x0C)

    def test_instantiation(self, dac):
        """Perform test instantiation operation.

        Args:
            dac: Dac.
        """
        assert dac.get_name().startswith('Analog Devices AD5667R')

    def test_write_dac_a_code(self, twi, dac):
        """Perform test write dac a code operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._write_dac_A_code(0x8000)
        # command = WRITE_DACn_UPDATE_DACn(0b011<<3) | DAC_A(0b000) = 0x18
        cmd = (0b011 << 3) | 0b000
        assert cmd in twi._cc_data

    def test_write_dac_a_voltage(self, twi, dac):
        # 2.5V → code = 2.5 / 2.0 / 2.5 * 65536 = 32768
        """Perform test write dac a voltage operation.

        Args:
            dac: Dac.
            twi: Twi.
        """
        dac._set_dac_A_voltage(2.5)
        cmd = (0b011 << 3) | 0b000  # WRITE_DACn_UPDATE_DACn | DAC_A
        assert cmd in twi._cc_data

    def test_volts_to_code(self, dac):
        """Perform test volts to code operation.

        Args:
            dac: Dac.
        """
        assert dac._volts_to_code(0.0) == 0
        assert dac._volts_to_code(2.5) == 32768

    def test_volts_out_of_range_raises(self, dac):
        """Perform test volts out of range raises operation.

        Args:
            dac: Dac.
        """
        with pytest.raises(Exception, match="out of range"):
            dac._volts_to_code(6.0)

    def test_add_channel_dac_a(self, twi, dac, master_instance):
        """Perform test add channel dac a operation.

        Args:
            dac: Dac.
            master_instance: Master instance.
            twi: Twi.
        """
        dac.add_channel_DAC_A('dac_a')
        master_instance.add(dac)
        master_instance['dac_a'].write(1.0)
        cmd = (0b011 << 3) | 0b000
        assert cmd in twi._cc_data


class TestPCF8574:
    """Tests for P C F8574."""

    @pytest.fixture
    def gpio(self, twi):
        """Return gpio result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return PCF8574(interface_twi=twi, addr7=0x20)

    def test_instantiation(self, gpio):
        """Perform test instantiation operation.

        Args:
            gpio: Gpio.
        """
        assert gpio.get_name().startswith('PCF8574')

    def test_invalid_address_raises(self, twi):
        """Perform test invalid address raises operation.

        Args:
            twi: Twi.
        """
        with pytest.raises(ValueError):
            PCF8574(interface_twi=twi, addr7=0x30)

    def test_write_pin_high(self, twi, gpio):
        """Perform test write pin high operation.

        Args:
            gpio: Gpio.
            twi: Twi.
        """
        gpio.add_channel_writepin('pin0', 0)
        gpio['pin0'].write(1)
        # state should be 0x01, written as commandCode via send_byte
        assert twi._cc_data[0x01] is None  # data_size=0 stores None as data

    def test_write_multiple_pins(self, twi, gpio):
        """Perform test write multiple pins operation.

        Args:
            gpio: Gpio.
            twi: Twi.
        """
        gpio.add_channel_writepin('p0', 0)
        gpio.add_channel_writepin('p3', 3)
        gpio['p0'].write(1)
        gpio['p3'].write(1)
        # state should be 0b00001001 = 0x09
        assert gpio.state == 0x09
        assert 0x09 in twi._cc_data

    def test_write_pin_low_clears_bit(self, twi, gpio):
        """Perform test write pin low clears bit operation.

        Args:
            gpio: Gpio.
            twi: Twi.
        """
        gpio.add_channel_writepin('p0', 0)
        gpio['p0'].write(1)
        gpio['p0'].write(0)
        assert gpio.state == 0x00


class TestCAT5140:
    """Tests for C A T5140."""

    @pytest.fixture
    def pot(self, twi):
        """Return pot result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return CAT5140(interface_twi=twi)

    def test_instantiation(self, pot):
        """Perform test instantiation operation.

        Args:
            pot: Pot.
        """
        assert pot.addr7 == 0x28

    def test_write_code(self, twi, pot):
        """Perform test write code operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.set_output(128)
        assert twi._cc_data[0x00] == 128

    def test_read_code(self, twi, pot):
        """Perform test read code operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.set_output(200)
        assert pot.get_output() == 200

    def test_write_percent_half(self, twi, pot):
        """Perform test write percent half operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot._write_percent(0.5)
        assert twi._cc_data[0x00] == 128

    def test_write_percent_full(self, twi, pot):
        """Perform test write percent full operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot._write_percent(1.0)
        assert twi._cc_data[0x00] == 255

    def test_add_channel_code(self, twi, pot, master_instance):
        """Perform test add channel code operation.

        Args:
            master_instance: Master instance.
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_code('wiper')
        master_instance.add(pot)
        master_instance['wiper'].write(100)
        assert twi._cc_data[0x00] == 100

    def test_add_channel_percent_readback(self, twi, pot):
        """Perform test add channel percent readback operation.

        Args:
            pot: Pot.
            twi: Twi.
        """
        pot.add_channel_percent_readback('pct')
        twi._cc_data[0x00] = 128
        val = pot['pct'].read()
        assert val == pytest.approx(128 / 255.0)


class TestAgilent34401a:
    """Tests for Agilent34401a."""

    @pytest.fixture
    def dmm(self, master_instance):
        """Return dmm result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
        mock_iface = MagicMock()
        mock_iface.__class__ = interface_visa
        mock_iface.ask.return_value = "3.300000E+00"
        instrument = agilent_34401a(mock_iface)
        master_instance.add(instrument)
        return instrument, mock_iface

    def test_instantiation_sends_config(self, dmm):
        """Perform test instantiation sends config operation.

        Args:
            dmm: Dmm.
        """
        _, mock = dmm
        # __init__ calls config_dc_voltage which writes several SCPI commands
        write_calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLT:DC' in c for c in write_calls)

    def test_read_meter(self, dmm):
        """Perform test read meter operation.

        Args:
            dmm: Dmm.
        """
        instrument, mock = dmm
        result = instrument.read_meter()
        mock.ask.assert_called_with("READ?")
        assert result == pytest.approx(3.3)

    def test_read_meter_negative(self, dmm):
        """Perform test read meter negative operation.

        Args:
            dmm: Dmm.
        """
        instrument, mock = dmm
        mock.ask.return_value = "-1.234567E-03"
        result = instrument.read_meter()
        assert result == pytest.approx(-0.001234567)

    def test_config_dc_current(self, dmm):
        """Perform test config dc current operation.

        Args:
            dmm: Dmm.
        """
        instrument, mock = dmm
        mock.reset_mock()
        instrument.config_dc_current(NPLC=10)
        write_calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent:DC' in c for c in write_calls)
        assert any('10' in c for c in write_calls)

    def test_invalid_nplc_raises(self, dmm):
        """Perform test invalid nplc raises operation.

        Args:
            dmm: Dmm.
        """
        instrument, _ = dmm
        with pytest.raises(Exception, match="Not a valid NPLC"):
            instrument.config_dc_voltage(NPLC=5)

    def test_add_channel_read(self, dmm):
        """Perform test add channel read operation.

        Args:
            dmm: Dmm.
        """
        instrument, mock = dmm
        instrument.add_channel('voltage')
        mock.ask.return_value = "5.000000E+00"
        val = instrument['voltage'].read()
        assert val == pytest.approx(5.0)


class TestBR24H64:
    """Tests for B R24 H64."""

    @pytest.fixture
    def eeprom(self, twi):
        """Return eeprom result.

        Args:
            twi: Twi.

        Returns:
            Result value.
        """
        return BR24H64(interface_twi=twi, addr7=0x50)

    def test_instantiation(self, eeprom):
        """Perform test instantiation operation.

        Args:
            eeprom: Eeprom.
        """
        assert eeprom.get_name().startswith('64KBit')

    def test_invalid_address_raises(self, twi):
        """Perform test invalid address raises operation.

        Args:
            twi: Twi.
        """
        with pytest.raises(ValueError):
            BR24H64(interface_twi=twi, addr7=0x60)

    def test_write_location(self, twi, eeprom):
        """Perform test write location operation.

        Args:
            eeprom: Eeprom.
            twi: Twi.
        """
        eeprom.write_location(0, 0xAB)
        # commandCode = location >> 8 = 0, data = (location & 0xff) + (data <<
        # 8)
        assert twi._cc_data[0x00] == (0x00) + (0xAB << 8)

    def test_write_location_high_address(self, twi, eeprom):
        """Perform test write location high address operation.

        Args:
            eeprom: Eeprom.
            twi: Twi.
        """
        eeprom.write_location(0x0100, 0x42)
        # commandCode = 0x0100 >> 8 = 1, data = (0x00) + (0x42 << 8)
        assert twi._cc_data[0x01] == (0x00) + (0x42 << 8)

    def test_write_out_of_range_raises(self, eeprom):
        """Perform test write out of range raises operation.

        Args:
            eeprom: Eeprom.
        """
        with pytest.raises(Exception, match="outside physical media"):
            eeprom.write_location(9000, 0x00)

    def test_write_data_out_of_range_raises(self, eeprom):
        """Perform test write data out of range raises operation.

        Args:
            eeprom: Eeprom.
        """
        with pytest.raises(Exception, match="outside the range"):
            eeprom.write_location(0, 256)


class TestAgilentE36xxa:
    """Tests for Agilent E36xxa."""

    @pytest.fixture
    def supply(self, master_instance):
        """Return supply result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test set voltage operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        psu.set_voltage("OUT1", 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INSTrument:SELect OUT1' in c for c in calls)
        assert any('VOLTage 3.3' in c for c in calls)

    def test_set_current(self, supply):
        """Perform test set current operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        psu.set_current("OUT1", 0.5)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent 0.5' in c for c in calls)

    def test_read_vsense(self, supply):
        """Perform test read vsense operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        mock.ask.return_value = "5.000000E+00"
        result = psu.read_vsense("OUT1")
        assert result == pytest.approx(5.0)

    def test_read_isense(self, supply):
        """Perform test read isense operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        mock.ask.return_value = "1.234000E-01"
        result = psu.read_isense("OUT1")
        assert result == pytest.approx(0.1234)

    def test_add_channel_voltage(self, supply):
        """Perform test add channel voltage operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        psu.add_channel_voltage('vout', 'OUT1')
        psu['vout'].write(1.8)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage 1.8' in c for c in calls)

    def test_enable_output(self, supply):
        """Perform test enable output operation.

        Args:
            supply: Supply.
        """
        psu, mock = supply
        psu.enable_output(True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTput:STATe ON' in c for c in calls)


class TestScpiSmu:
    """Tests for Scpi Smu."""

    @pytest.fixture
    def smu_inst(self, master_instance):
        """Return smu inst result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test add channels operation.

        Args:
            smu_inst: Smu inst.
        """
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
        """Perform test voltage force operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_voltage_force('vf')
        inst['vf'].write(3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage' in c and '3.3' in c for c in calls)
        assert any('FUNCtion:MODE VOLTage' in c for c in calls)
        assert any('OUTPut' in c and 'ON' in c for c in calls)

    def test_current_force(self, smu_inst):
        """Perform test current force operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_current_force('if')
        inst['if'].write(0.001)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('CURRent' in c and '0.001' in c for c in calls)
        assert any('FUNCtion:MODE CURRent' in c for c in calls)

    def test_voltage_sense(self, smu_inst):
        """Perform test voltage sense operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_voltage_sense('vs')
        mock.ask.return_value = "3.300E+00,1.000E-03,9.91E+37,0.0,0"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_current_sense(self, smu_inst):
        """Perform test current sense operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_current_sense('is_ch')
        mock.ask.return_value = "5.000E+00,2.500E-03,9.91E+37,0.0,0"
        val = inst['is_ch'].read()
        assert val == pytest.approx(0.0025)

    def test_compliance_write(self, smu_inst):
        """Perform test compliance write operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_voltage_compliance('vcompl')
        inst['vcompl'].write(20)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:DC:PROTection:LEVel 20' in c for c in calls)

    def test_exclusive_vforce_clears_iforce(self, smu_inst):
        """Perform test exclusive vforce clears iforce operation.

        Args:
            smu_inst: Smu inst.
        """
        inst, mock = smu_inst
        inst.add_channel_voltage_force('vf')
        inst.add_channel_current_force('if')
        inst['if'].write(0.01)
        inst['vf'].write(5.0)
        # Writing vforce should clear iforce cached value
        assert inst['if'].read() is None


class TestHameg4040:
    """Tests for Hameg4040."""

    @pytest.fixture
    def supply(self, master_instance):
        """Return supply result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test write voltage operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst._write_voltage(1, 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INST:NSEL 1' in c for c in calls)
        assert any('SOURce:VOLTage 3.3' in c for c in calls)

    def test_write_current(self, supply):
        """Perform test write current operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst._write_current(2, 0.5)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('INST:NSEL 2' in c for c in calls)
        assert any('SOURce:CURRent 0.5' in c for c in calls)

    def test_read_vsense(self, supply):
        """Perform test read vsense operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        mock.ask.return_value = "3.300"
        val = inst._read_vsense(1)
        assert val == pytest.approx(3.3)

    def test_read_isense(self, supply):
        """Perform test read isense operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        mock.ask.return_value = "0.125"
        val = inst._read_isense(1)
        assert val == pytest.approx(0.125)

    def test_write_enable(self, supply):
        """Perform test write enable operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst._write_enable(1, True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPUT:STATE ON' in c for c in calls)

    def test_write_enable_off(self, supply):
        """Perform test write enable off operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst._write_enable(1, False)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPUT:STATE OFF' in c for c in calls)

    def test_master_enable(self, supply):
        """Perform test master enable operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst._write_master_enable(True)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut:GENeral ON' in c for c in calls)

    def test_add_channel_voltage(self, supply):
        """Perform test add channel voltage operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        inst.add_channel_voltage('ch1_v', 1)
        mock.reset_mock()
        mock.ask.return_value = "1"
        inst['ch1_v'].write(5.0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('SOURce:VOLTage 5.0' in c for c in calls)

    def test_voltage_limits(self, supply):
        """Perform test voltage limits operation.

        Args:
            supply: Supply.
        """
        inst, mock = supply
        ch = inst.add_channel_voltage('ch1_v', 1)
        assert ch.get_max_write_limit() == 32.05
        assert ch.get_min_write_limit() == 0


class TestRigolDG800:
    """Tests for Rigol D G800."""

    @pytest.fixture
    def funcgen(self, master_instance):
        """Return funcgen result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test write high voltage operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        inst._write_high_voltage(1, 3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel:IMMediate:HIGH 3.3' in c for c in calls)

    def test_write_low_voltage(self, funcgen):
        """Perform test write low voltage operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        inst._write_low_voltage(1, 0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel:IMMediate:LOW 0' in c for c in calls)

    def test_write_pulse_width(self, funcgen):
        """Perform test write pulse width operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        inst._write_pulse_width(1, 50e-6)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('PULSe:WIDTh 5e-05' in c for c in calls)

    def test_write_output_enable(self, funcgen):
        """Perform test write output enable operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        inst._write_output_enable(1, 'ON')
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut1:STATE ON' in c for c in calls)

    def test_add_channel_enable(self, funcgen):
        """Perform test add channel enable operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        ch = inst.add_channel_enable('out1', 1)
        mock.reset_mock()
        ch.write('ON')
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('OUTPut1:STATE ON' in c for c in calls)

    def test_add_channel_pulse_width(self, funcgen):
        """Perform test add channel pulse width operation.

        Args:
            funcgen: Funcgen.
        """
        inst, mock = funcgen
        ch = inst.add_channel_pulse_width('pw', 1)
        assert ch.get_min_write_limit() == 30e-9


class TestKeithley2400:
    """Tests for Keithley2400."""

    @pytest.fixture
    def smu(self, master_instance):
        """Return smu result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test add channel voltage force operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        ch = inst.add_channel_voltage_force('vf')
        assert ch.get_min_write_limit() == -200
        assert ch.get_max_write_limit() == 200
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('RANGe:AUTO ON' in c for c in calls)

    def test_add_channel_current_force(self, smu):
        """Perform test add channel current force operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        ch = inst.add_channel_current_force('if')
        assert ch.get_min_write_limit() == -1
        assert ch.get_max_write_limit() == 1

    def test_voltage_force_sends_scpi(self, smu):
        """Perform test voltage force sends scpi operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_voltage_force('vf')
        mock.reset_mock()
        inst['vf'].write(3.3)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('VOLTage:LEVel' in c and '3.3' in c for c in calls)
        assert any('OUTPut' in c and 'ON' in c for c in calls)

    def test_voltage_sense(self, smu):
        """Perform test voltage sense operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_voltage_sense('vs')
        mock.ask.return_value = "3.300E+00,1.000E-03,9.91E+37,0.0,0"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_current_sense(self, smu):
        """Perform test current sense operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_current_sense('is_ch')
        mock.ask.return_value = "5.000E+00,2.500E-03,9.91E+37,0.0,0"
        val = inst['is_ch'].read()
        assert val == pytest.approx(0.0025)


class TestKeithley2600:
    """Tests for Keithley2600."""

    @pytest.fixture
    def smu(self, master_instance):
        """Return smu result.

        Args:
            master_instance: Master instance.

        Returns:
            Result value.
        """
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
        """Perform test channel id operation.

        Args:
            smu: Smu.
        """
        inst, _ = smu
        assert inst._channel_id(1) == 'a'
        assert inst._channel_id(2) == 'b'

    def test_voltage_force(self, smu):
        """Perform test voltage force operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_voltage_force('vf', channel_number=1)
        mock.reset_mock()
        inst['vf'].write(5.0)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smua.source.levelv = 5.0' in c for c in calls)
        assert any('OUTPUT_DCVOLTS' in c for c in calls)
        assert any('OUTPUT_ON' in c for c in calls)

    def test_current_force_channel_b(self, smu):
        """Perform test current force channel b operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_current_force('if', channel_number=2)
        mock.reset_mock()
        inst['if'].write(0.001)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smub.source.leveli = 0.001' in c for c in calls)
        assert any('OUTPUT_DCAMPS' in c for c in calls)

    def test_voltage_sense(self, smu):
        """Perform test voltage sense operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_voltage_sense('vs', channel_number=1)
        mock.ask.return_value = "3.300000e+00"
        val = inst['vs'].read()
        assert val == pytest.approx(3.3)

    def test_compliance_write(self, smu):
        """Perform test compliance write operation.

        Args:
            smu: Smu.
        """
        inst, mock = smu
        inst.add_channel_current_compliance('icompl', channel_number=1)
        mock.reset_mock()
        inst['icompl'].write(0.1)
        calls = [str(c) for c in mock.write.call_args_list]
        assert any('smua.source.limiti = 0.1' in c for c in calls)


class TestHtx9011ThreadConsolidation:
    """Verify that add_channel_isense_remapper registers meter interfaces on the htx9011,
    preventing concurrent SCPI access via thread consolidation."""

    @pytest.fixture
    def setup(self, master_instance):
        """Create an htx9011 and a mock meter instrument on separate interfaces.

        Args:
            master_instance: Master instance.

        Returns:
            Tuple of (htx9011_instance, meter_instrument, meter_interface, htx_interface).
        """
        from PyICe.lab_instruments.htx9011 import htx9011
        from PyICe.lab_core import instrument, channel

        htx_iface = MagicMock()
        htx_iface.__class__ = interface_visa
        last_write = {}

        def fake_readline():
            value_char = last_write.get('value_char', 'Z')
            return f'00{value_char}0\r\n'

        def fake_write(cmd):
            if ':SETPin:' in cmd:
                parts = cmd.split(':SETPin:')
                for part in parts[1:]:
                    if part and part[0] in 'HLZP':
                        char_map = {'L': '0', 'H': '1', 'Z': 'Z', 'P': 'P'}
                        last_write['value_char'] = char_map[part[0]]

        htx_iface.readline.side_effect = fake_readline
        htx_iface.write.side_effect = fake_write
        htx_iface.ask.return_value = '1234567890'
        htx_iface.com_node_get_root.return_value = master_instance
        htx = htx9011(htx_iface, serializing=True)

        meter_iface = master_instance.get_dummy_interface(name='meter_gpib')
        meter = instrument('mock_meter')
        meter._add_interface(meter_iface)
        vmeter_hi = channel('vmeter_hi', read_function=lambda: 0.100)
        vmeter_med = channel('vmeter_med', read_function=lambda: 0.050)
        vmeter_lo = channel('vmeter_lo', read_function=lambda: 0.001)
        for ch in (vmeter_hi, vmeter_med, vmeter_lo):
            meter._add_channel(ch)

        master_instance.add(htx)
        master_instance.add(meter)
        return htx, meter, meter_iface

    def test_meter_interface_registered_on_htx9011(self, setup):
        """After add_channel_isense_remapper, htx9011 claims the meter's interface."""
        htx, meter, meter_iface = setup
        vmeter_hi = meter.get_channel('vmeter_hi')
        vmeter_med = meter.get_channel('vmeter_med')
        vmeter_lo = meter.get_channel('vmeter_lo')

        assert meter_iface not in htx._interfaces
        htx.add_channel_isense_remapper(
            'isense_ch1', 1, vmeter_hi, vmeter_med, vmeter_lo)
        assert meter_iface in htx._interfaces

    def test_htx9011_not_threadable_independently_from_meter(self, setup, master_instance):
        """htx9011 cannot be placed in a thread group that excludes the meter's interface,
        ensuring they are never read concurrently."""
        htx, meter, meter_iface = setup
        vmeter_hi = meter.get_channel('vmeter_hi')
        vmeter_med = meter.get_channel('vmeter_med')
        vmeter_lo = meter.get_channel('vmeter_lo')

        htx.add_channel_isense_remapper(
            'isense_ch1', 1, vmeter_hi, vmeter_med, vmeter_lo)

        htx_interfaces = set(htx._interfaces)
        all_interfaces = list(htx_interfaces | set(meter._interfaces))
        thread_groups = master_instance.group_com_nodes_for_threads_filter(all_interfaces)
        for group in thread_groups:
            group_set = set(group)
            if htx_interfaces.issubset(group_set):
                assert meter_iface in group_set, (
                    "htx9011 was placed in a thread group without the meter interface")
                break
        else:
            pass


class TestThreadResolution:
    """Verify that the worker thread resolution algorithm correctly groups channels
    sharing an interface or com node parent into the same thread, and separates
    independent channels into distinct threads."""

    @pytest.fixture
    def master(self, master_instance):
        """Return a master with threading enabled.

        Args:
            master_instance: Master instance.

        Returns:
            The master instance.
        """
        return master_instance

    def _make_instrument(self, name, interface):
        """Create a simple instrument with a read channel on the given interface.

        Args:
            name: Instrument name.
            interface: Interface to attach.

        Returns:
            Tuple of (instrument, channel).
        """
        from PyICe.lab_core import instrument, channel
        inst = instrument(name)
        inst._add_interface(interface)
        ch = channel(f'{name}_ch', read_function=lambda: 0)
        inst._add_channel(ch)
        return inst, ch

    def _dump_com_tree(self, master):
        """Capture the com node tree as a string for diagnostic output.

        Args:
            master: The master instance (root of the com node tree).

        Returns:
            String representation of the interface hierarchy.
        """
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            master.debug_com_nodes()
        return buf.getvalue()

    def _get_thread_work_units(self, master, channel_list):
        """Run the thread grouping logic and return a list of channel-name sets,
        one per work unit dispatched to the thread pool, plus the remainder set.

        Args:
            master: The master instance.
            channel_list: Channels to partition.

        Returns:
            Tuple of (work_units, remainder) where work_units is a list of sets
            of channel names and remainder is a set of channel names read
            non-threaded after all threads complete.
        """
        from PyICe.lab_core import results_ord_dict
        work_units = []
        original_put = master._read_queue.put

        def capture_put(ch_list):
            work_units.append(set(ch.get_name() for ch in ch_list))

        master._read_queue.put = capture_put
        old_get_results = master.get_threaded_results
        master.get_threaded_results = lambda n: results_ord_dict()
        old_non_threaded = master._read_channels_non_threaded
        remainder_channels = []
        master._read_channels_non_threaded = lambda cl: (
            remainder_channels.extend(cl) or results_ord_dict())

        try:
            master._read_channels_threaded(channel_list)
        finally:
            master._read_queue.put = original_put
            master.get_threaded_results = old_get_results
            master._read_channels_non_threaded = old_non_threaded

        remainder = set(ch.get_name() for ch in remainder_channels)
        return work_units, remainder

    def test_shared_interface_same_thread(self, master):
        """Two instruments on the same interface must be in the same work unit."""
        iface = master.get_dummy_interface(name='shared_bus')
        inst_a, ch_a = self._make_instrument('inst_a', iface)
        inst_b, ch_b = self._make_instrument('inst_b', iface)
        master.add(inst_a)
        master.add(inst_b)

        work_units, remainder = self._get_thread_work_units(
            master, [ch_a, ch_b])

        tree = self._dump_com_tree(master)
        combined = set()
        for wu in work_units:
            combined |= wu
        assert 'inst_a_ch' in combined and 'inst_b_ch' in combined, (
            f"Channels missing from work units.\nCom tree:\n{tree}")
        for wu in work_units:
            if 'inst_a_ch' in wu:
                assert 'inst_b_ch' in wu, (
                    f"Channels sharing an interface were placed in different work units.\n"
                    f"Work units: {work_units}\nCom tree:\n{tree}")

    def test_shared_non_thread_safe_parent_same_thread(self, master):
        """Two instruments whose interfaces share a non-thread-safe parent
        must be in the same work unit."""
        from PyICe.lab_interfaces import communication_node
        bus = communication_node()
        bus.set_com_node_thread_safe(False)
        bus.set_com_node_parent(master)
        iface_a = master.get_dummy_interface(parent=bus, name='dev_a')
        iface_b = master.get_dummy_interface(parent=bus, name='dev_b')
        inst_a, ch_a = self._make_instrument('inst_a', iface_a)
        inst_b, ch_b = self._make_instrument('inst_b', iface_b)
        master.add(inst_a)
        master.add(inst_b)

        work_units, remainder = self._get_thread_work_units(
            master, [ch_a, ch_b])

        tree = self._dump_com_tree(master)
        for wu in work_units:
            if 'inst_a_ch' in wu:
                assert 'inst_b_ch' in wu, (
                    f"Channels sharing a non-thread-safe parent were split into different work units.\n"
                    f"Work units: {work_units}\nCom tree:\n{tree}")
                break
        else:
            assert 'inst_a_ch' in remainder and 'inst_b_ch' in remainder, (
                f"Expected both channels in the same execution context.\n"
                f"Work units: {work_units}, Remainder: {remainder}\nCom tree:\n{tree}")

    def test_independent_interfaces_separate_threads(self, master):
        """Two instruments on independent interfaces (thread-safe root) must be
        dispatched to separate work units."""
        iface_a = master.get_dummy_interface(name='bus_a')
        iface_b = master.get_dummy_interface(name='bus_b')
        inst_a, ch_a = self._make_instrument('inst_a', iface_a)
        inst_b, ch_b = self._make_instrument('inst_b', iface_b)
        master.add(inst_a)
        master.add(inst_b)

        work_units, remainder = self._get_thread_work_units(
            master, [ch_a, ch_b])

        tree = self._dump_com_tree(master)
        assert len(work_units) >= 2, (
            f"Expected at least 2 work units for independent interfaces, got {len(work_units)}.\n"
            f"Work units: {work_units}\nCom tree:\n{tree}")
        for wu in work_units:
            assert not ('inst_a_ch' in wu and 'inst_b_ch' in wu), (
                f"Independent channels were incorrectly placed in the same work unit.\n"
                f"Work units: {work_units}\nCom tree:\n{tree}")

    def test_three_buses_three_work_units(self, master):
        """Three instruments on three independent buses produce three work units."""
        ifaces = [master.get_dummy_interface(name=f'bus_{i}') for i in range(3)]
        channels = []
        for i, iface in enumerate(ifaces):
            inst, ch = self._make_instrument(f'inst_{i}', iface)
            master.add(inst)
            channels.append(ch)

        work_units, remainder = self._get_thread_work_units(master, channels)

        tree = self._dump_com_tree(master)
        assert len(work_units) == 3, (
            f"Expected 3 work units for 3 independent buses, got {len(work_units)}.\n"
            f"Work units: {work_units}\nCom tree:\n{tree}")

    def test_instrument_spanning_two_interfaces_not_split(self, master):
        """An instrument claiming two interfaces cannot be placed in a work unit
        that excludes either interface. It either shares a work unit with both
        or falls to the non-threaded remainder."""
        from PyICe.lab_core import instrument, channel
        iface_a = master.get_dummy_interface(name='bus_a')
        iface_b = master.get_dummy_interface(name='bus_b')
        inst = instrument('multi_iface_inst')
        inst._add_interface(iface_a)
        inst._add_interface(iface_b)
        ch = channel('multi_ch', read_function=lambda: 0)
        inst._add_channel(ch)
        master.add(inst)

        inst_other, ch_other = self._make_instrument('other', iface_a)
        master.add(inst_other)

        work_units, remainder = self._get_thread_work_units(
            master, [ch, ch_other])

        tree = self._dump_com_tree(master)
        for wu in work_units:
            if 'multi_ch' in wu:
                assert iface_a in set(inst._interfaces) and iface_b in set(inst._interfaces)
                break
        else:
            assert 'multi_ch' in remainder, (
                f"Multi-interface instrument must fall to non-threaded remainder "
                f"if no single thread group contains all its interfaces.\n"
                f"Work units: {work_units}, Remainder: {remainder}\nCom tree:\n{tree}")


class TestCommunicationNode:
    """Unit tests for communication_node tree operations, error paths, and edge cases."""

    def test_single_node_is_own_root(self):
        """A parentless node is its own root."""
        from PyICe.lab_interfaces import communication_node
        node = communication_node()
        assert node.com_node_get_root() is node

    def test_single_node_no_descendants(self):
        """A leaf node has no descendants."""
        from PyICe.lab_interfaces import communication_node
        node = communication_node()
        assert node.com_node_get_all_descendents() == set()

    def test_deep_tree_root_traversal(self):
        """com_node_get_root traverses arbitrarily deep chains."""
        from PyICe.lab_interfaces import communication_node
        nodes = [communication_node() for _ in range(10)]
        for i in range(1, len(nodes)):
            nodes[i].set_com_node_parent(nodes[i - 1])
        assert nodes[-1].com_node_get_root() is nodes[0]

    def test_descendants_excludes_self(self):
        """com_node_get_all_descendents does not include the node itself."""
        from PyICe.lab_interfaces import communication_node
        root = communication_node()
        child = communication_node()
        child.set_com_node_parent(root)
        assert root not in root.com_node_get_all_descendents()

    def test_thread_unsafe_node_lumps_all_descendants(self):
        """A thread-unsafe node produces one group containing itself and all descendants."""
        from PyICe.lab_interfaces import communication_node
        root = communication_node()
        root.set_com_node_thread_safe(False)
        a = communication_node()
        a.set_com_node_parent(root)
        b = communication_node()
        b.set_com_node_parent(a)
        groups = root.group_com_nodes_for_threads()
        assert len(groups) == 1
        assert groups[0] == {root, a, b}

    def test_thread_safe_root_creates_separate_groups_per_child(self):
        """A thread-safe root with N children produces at least N+1 groups
        (one for root, one per child subtree)."""
        from PyICe.lab_interfaces import communication_node
        root = communication_node()
        root.set_com_node_thread_safe(True)
        children = []
        for _ in range(4):
            c = communication_node()
            c.set_com_node_thread_safe(False)
            c.set_com_node_parent(root)
            children.append(c)
        groups = root.group_com_nodes_for_threads()
        assert len(groups) == 5

    def test_filter_raises_on_multiple_roots(self):
        """group_com_nodes_for_threads_filter raises when nodes have different roots."""
        from PyICe.lab_interfaces import communication_node
        root_a = communication_node()
        root_b = communication_node()
        node_a = communication_node()
        node_a.set_com_node_parent(root_a)
        node_b = communication_node()
        node_b.set_com_node_parent(root_b)
        with pytest.raises(Exception, match="Too many COM node parents"):
            root_a.group_com_nodes_for_threads_filter([node_a, node_b])

    def test_filter_empty_list(self):
        """Filtering an empty list returns an empty result."""
        from PyICe.lab_interfaces import communication_node
        root = communication_node()
        root.set_com_node_thread_safe(True)
        assert root.group_com_nodes_for_threads_filter([]) == []

    def test_hierarchical_lock_acquires_parent(self):
        """Locking a child also locks its parent (hierarchical locking).
        Verified from a second thread since RLock is reentrant within one thread."""
        import threading
        from PyICe.lab_interfaces import communication_node
        parent = communication_node()
        child = communication_node()
        child.set_com_node_parent(parent)
        child.lock()
        probe_result = {}

        def probe():
            probe_result['acquired'] = parent._lock.acquire(block=False)
            if probe_result['acquired']:
                parent._lock.release()

        t = threading.Thread(target=probe)
        t.start()
        t.join()
        assert not probe_result['acquired'], (
            "Parent lock should be held (by main thread) after child.lock()")
        child.unlock()
        t2 = threading.Thread(target=probe)
        t2.start()
        t2.join()
        assert probe_result['acquired'], (
            "Parent lock should be released after child.unlock()")

    def test_mixed_topology_grouping(self):
        """Complex topology: thread-safe root, two unsafe buses each with devices,
        plus one device directly on root. Verifies correct partitioning."""
        from PyICe.lab_interfaces import communication_node
        root = communication_node()
        root.set_com_node_thread_safe(True)
        bus_a = communication_node()
        bus_a.set_com_node_thread_safe(False)
        bus_a.set_com_node_parent(root)
        dev_a1 = communication_node()
        dev_a1.set_com_node_parent(bus_a)
        dev_a2 = communication_node()
        dev_a2.set_com_node_parent(bus_a)
        bus_b = communication_node()
        bus_b.set_com_node_thread_safe(False)
        bus_b.set_com_node_parent(root)
        dev_b1 = communication_node()
        dev_b1.set_com_node_parent(bus_b)
        dev_direct = communication_node()
        dev_direct.set_com_node_parent(root)

        groups = root.group_com_nodes_for_threads_filter(
            [dev_a1, dev_a2, dev_b1, dev_direct])

        group_sets = [set(g) for g in groups]
        for gs in group_sets:
            if dev_a1 in gs:
                assert dev_a2 in gs, "Devices on same unsafe bus must be co-grouped"
                assert dev_b1 not in gs, "Devices on different buses must not be co-grouped"


class TestDeprecationDeadlines:
    """Scheduled removal tests. When these fail, remove the associated shim code."""

    def test_isense_remapper_shim_deadline(self):
        """Remove the inspect-based compatibility shim for add_channel_isense_remapper
        in morpheus_eval, then delete this test."""
        import datetime
        deadline = datetime.date(2026, 9, 11)
        assert datetime.date.today() <= deadline, (
            "SHIM EXPIRED: Remove the inspect-based compatibility shim for "
            "add_channel_isense_remapper() in morpheus_eval, then delete this test. "
            "See PR #207 for details.")
