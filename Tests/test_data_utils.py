import math
import numpy
import pytest
from PyICe.data_utils.units_conversions import dBV, dBm, Vpp_to_VRMS, VRMS_to_Vpp
from PyICe.data_utils.EMI_char_levels import (IEC61967_2_uppercase,
                                              IEC61967_2_digit,
                                              IEC61967_2_lowercase)
from PyICe.data_utils.signal_generator import signal_generator, lfsr_period_generator
from PyICe.data_utils.spectrum_analyzer import spectrum_analyzer


class TestUnitsConversions:

    def test_dBV_1V(self):
        """Perform test dBV 1V operation."""
        assert dBV(1.0) == pytest.approx(0.0)

    def test_dBV_10V(self):
        """Perform test dBV 10V operation."""
        assert dBV(10.0) == pytest.approx(20.0)

    def test_dBV_0p1V(self):
        """Perform test dBV 0p1V operation."""
        assert dBV(0.1) == pytest.approx(-20.0)

    def test_dBm_1V_50ohm(self):
        # 1 VRMS into 50 ohm = 20 mW = 10*log10(20) = 13.01 dBm
        """Perform test dBm 1V 50ohm operation."""
        assert dBm(1.0) == pytest.approx(13.0103, rel=1e-3)

    def test_dBm_0p224V(self):
        # 0.2236 VRMS into 50 ohm = 1 mW = 0 dBm
        """Perform test dBm 0p224V operation."""
        assert dBm(numpy.sqrt(0.05)) == pytest.approx(0.0, abs=0.01)

    def test_Vpp_to_VRMS(self):
        # 1 Vpp = 0.5 Vpeak = 0.5/sqrt(2) VRMS
        """Perform test Vpp to VRMS operation."""
        assert Vpp_to_VRMS(1.0) == pytest.approx(1.0 / (2 * math.sqrt(2)))

    def test_VRMS_to_Vpp(self):
        # 1 VRMS = sqrt(2) Vpeak = 2*sqrt(2) Vpp
        """Perform test VRMS to Vpp operation."""
        assert VRMS_to_Vpp(1.0) == pytest.approx(2 * math.sqrt(2))

    def test_roundtrip_Vpp_VRMS(self):
        """Perform test roundtrip Vpp VRMS operation."""
        assert VRMS_to_Vpp(Vpp_to_VRMS(3.3)) == pytest.approx(3.3)

    def test_dBV_array(self):
        """Perform test dBV array operation."""
        result = dBV(numpy.array([1.0, 10.0, 100.0]))
        expected = numpy.array([0.0, 20.0, 40.0])
        numpy.testing.assert_allclose(result, expected)


class TestEMICharLevels:

    def test_uppercase_A(self):
        """Perform test uppercase A operation."""
        result = IEC61967_2_uppercase('A', 1e6)
        assert result == 84

    def test_uppercase_B(self):
        """Perform test uppercase B operation."""
        result = IEC61967_2_uppercase('B', 1e6)
        assert result == 78

    def test_uppercase_6dB_spacing(self):
        """Perform test uppercase 6dB spacing operation."""
        a = IEC61967_2_uppercase('A', 1e6)
        b = IEC61967_2_uppercase('B', 1e6)
        assert a - b == 6

    def test_uppercase_frequency_independent(self):
        """Perform test uppercase frequency independent operation."""
        a_1m = IEC61967_2_uppercase('A', 1e6)
        a_10m = IEC61967_2_uppercase('A', 10e6)
        assert a_1m == a_10m

    def test_digit_at_1MHz(self):
        """Perform test digit at 1MHz operation."""
        result = IEC61967_2_digit(1, 1e6)
        assert result == (20 - 1) * 6

    def test_digit_20dB_per_decade(self):
        """Perform test digit 20dB per decade operation."""
        val_1m = IEC61967_2_digit(1, 1e6)
        val_10m = IEC61967_2_digit(1, 10e6)
        assert val_1m - val_10m == pytest.approx(20.0)

    def test_lowercase_40dB_per_decade(self):
        """Perform test lowercase 40dB per decade operation."""
        val_1m = IEC61967_2_lowercase('a', 1e6)
        val_10m = IEC61967_2_lowercase('a', 10e6)
        assert val_1m - val_10m == pytest.approx(40.0)

    def test_lowercase_a_at_1MHz(self):
        """Perform test lowercase a at 1MHz operation."""
        result = IEC61967_2_lowercase('a', 1e6)
        assert result == 150

    def test_lowercase_6dB_spacing(self):
        """Perform test lowercase 6dB spacing operation."""
        a = IEC61967_2_lowercase('a', 1e6)
        b = IEC61967_2_lowercase('b', 1e6)
        assert a - b == 6


class TestSignalGenerator:

    @pytest.fixture
    def gen(self):
        """Return gen result.

        Returns:
            Result value.
        """
        return signal_generator(
            hi_value=1.0, lo_value=0.0,
            period=1e-3, cyclecount=10,
            timestep=1e-5
        )

    def test_pulse_wave_generates_data(self, gen):
        """Perform test pulse wave generates data operation.

        Args:
            gen: Gen.
        """
        data = list(gen.pulse_wave(duty_cycle=0.5))
        assert len(data) > 0
        times, values = zip(*data)
        assert all(v in (0.0, 1.0) for v in values)

    def test_pulse_wave_duty_cycle(self, gen):
        """Perform test pulse wave duty cycle operation.

        Args:
            gen: Gen.
        """
        data = list(gen.pulse_wave(duty_cycle=0.5))
        times, values = zip(*data)
        hi_count = sum(1 for v in values if v == 1.0)
        lo_count = sum(1 for v in values if v == 0.0)
        ratio = hi_count / (hi_count + lo_count)
        assert ratio == pytest.approx(0.5, abs=0.05)

    def test_pulse_wave_100_pct_duty(self, gen):
        """Perform test pulse wave 100 pct duty operation.

        Args:
            gen: Gen.
        """
        data = list(gen.pulse_wave(duty_cycle=1.0))
        _, values = zip(*data)
        assert all(v == 1.0 for v in values)

    def test_sine_wave_generates_data(self, gen):
        """Perform test sine wave generates data operation.

        Args:
            gen: Gen.
        """
        data = list(gen.sine_wave())
        assert len(data) > 0

    def test_sine_wave_amplitude(self, gen):
        # sine formula: (hi+lo)/2 + (hi-lo)*sin(...)
        # with hi=1.0, lo=0.0: midpoint=0.5, amplitude=1.0
        # so max = 0.5 + 1.0 = 1.5, min = 0.5 - 1.0 = -0.5
        """Perform test sine wave amplitude operation.

        Args:
            gen: Gen.
        """
        data = list(gen.sine_wave())
        _, values = zip(*data)
        assert max(values) == pytest.approx(1.5, abs=0.05)
        assert min(values) == pytest.approx(-0.5, abs=0.05)

    def test_sine_wave_mean(self, gen):
        """Perform test sine wave mean operation.

        Args:
            gen: Gen.
        """
        data = list(gen.sine_wave())
        _, values = zip(*data)
        mean = sum(values) / len(values)
        assert mean == pytest.approx(0.5, abs=0.05)

    def test_sine_wave_point_count(self, gen):
        """Perform test sine wave point count operation.

        Args:
            gen: Gen.
        """
        data = list(gen.sine_wave())
        expected_points = int(gen.cyclecount * gen.period / gen.timestep)
        assert len(data) == pytest.approx(expected_points, rel=0.05)

    def test_custom_period_function(self):
        """Perform test custom period function operation."""
        gen = signal_generator(
            hi_value=3.3, lo_value=0.0,
            period=1e-3, cyclecount=5,
            timestep=1e-5,
            period_function=lambda: 1e-3
        )
        data = list(gen.pulse_wave(duty_cycle=0.5))
        assert len(data) > 0


class TestLFSRPeriodGenerator:

    def test_generates_periods(self):
        """Perform test generates periods operation."""
        lfsr = lfsr_period_generator(nbits=8, freq_center=1e6,
                                     freq_range_percent=0.1)
        periods = [lfsr.get_next_period() for _ in range(100)]
        assert all(p > 0 for p in periods)

    def test_period_within_range(self):
        """Perform test period within range operation."""
        lfsr = lfsr_period_generator(nbits=8, freq_center=1e6,
                                     freq_range_percent=0.1)
        min_period = 1 / (1e6 * 1.1)
        max_period = 1 / (1e6 * 0.9)
        for _ in range(100):
            p = lfsr.get_next_period()
            assert min_period <= p <= max_period

    def test_pseudo_random_sequence(self):
        """Perform test pseudo random sequence operation."""
        lfsr = lfsr_period_generator(nbits=8, freq_center=1e6,
                                     freq_range_percent=0.1)
        periods = [lfsr.get_next_period() for _ in range(50)]
        assert len(set(periods)) > 1

    def test_set_polynomial(self):
        """Perform test set polynomial operation."""
        lfsr = lfsr_period_generator(nbits=4, freq_center=1e6,
                                     freq_range_percent=0.1)
        lfsr.set_polynomial([3, 2, 1, 0])
        p = lfsr.get_next_period()
        assert p > 0


class TestSpectrumAnalyzer:

    @pytest.fixture
    def pure_tone(self):
        """Generate a 1 kHz pure sine wave sampled at 100 kHz for 100 cycles.

        Returns:
            Result value.
        """
        gen = signal_generator(
            hi_value=1.0, lo_value=-1.0,
            period=1e-3, cyclecount=100,
            timestep=1e-5
        )
        return list(gen.sine_wave())

    def test_compute_fft_returns_frequencies_and_magnitudes(self, pure_tone):
        """Perform test compute fft returns frequencies and magnitudes operation.

        Args:
            pure_tone: Pure tone.
        """
        sa = spectrum_analyzer()
        xf, yf = sa.compute_fft(pure_tone)
        assert len(xf) == len(yf)
        assert len(xf) > 0

    def test_fft_peak_at_signal_frequency(self, pure_tone):
        """Perform test fft peak at signal frequency operation.

        Args:
            pure_tone: Pure tone.
        """
        sa = spectrum_analyzer()
        xf, yf = sa.compute_fft(pure_tone)
        peak_idx = numpy.argmax(yf)
        peak_freq = xf[peak_idx]
        assert peak_freq == pytest.approx(1000, rel=0.05)

    def test_get_RBW(self, pure_tone):
        """Perform test get RBW operation.

        Args:
            pure_tone: Pure tone.
        """
        sa = spectrum_analyzer()
        sa.compute_fft(pure_tone)
        rbw = sa.get_RBW()
        expected_rbw = 1.0 / sa.get_record_duration()
        assert rbw == pytest.approx(expected_rbw, rel=0.01)

    def test_get_record_duration(self, pure_tone):
        """Perform test get record duration operation.

        Args:
            pure_tone: Pure tone.
        """
        sa = spectrum_analyzer()
        sa.compute_fft(pure_tone)
        duration = sa.get_record_duration()
        assert duration == pytest.approx(0.1, rel=0.05)

    def test_get_record_length(self, pure_tone):
        """Perform test get record length operation.

        Args:
            pure_tone: Pure tone.
        """
        sa = spectrum_analyzer()
        sa.compute_fft(pure_tone)
        length = sa.get_record_length()
        assert length == len(pure_tone)

    def test_fft_dc_signal_peak_at_zero(self):
        """Perform test fft dc signal peak at zero operation."""
        dc_signal = list(zip(
            [i * 1e-5 for i in range(1000)],
            [1.0] * 1000
        ))
        sa = spectrum_analyzer()
        xf, yf = sa.compute_fft(dc_signal)
        peak_idx = numpy.argmax(yf)
        assert xf[peak_idx] == pytest.approx(0.0, abs=50)
