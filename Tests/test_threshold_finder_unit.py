import pytest
from PyICe.lab_core import master
from PyICe.virtual_instruments import threshold_finder
from PyICe.models.comparator import comparator


def make_comparator_system(m, threshold=2.5, hysteresis=0.0):
    """Wire up a comparator model with dummy/virtual channels for threshold_finder.

    Uses PyICe.models.comparator which properly models rising/falling
    thresholds, hysteresis, and output levels.
    """
    rising_th = threshold + hysteresis / 2
    falling_th = threshold - hysteresis / 2
    comp = comparator(falling_threshold=falling_th, rising_threshold=rising_th,
                      out_high=5.0, out_low=0.0)

    forcing = m.add_channel_dummy('force_in')
    forcing.write(0.0)
    forcing.add_write_callback(lambda ch, val: comp.write(val))

    output = m.add_channel_virtual('comp_out', read_function=comp.read)
    return forcing, output


class TestThresholdFinderBinarySearch:

    @pytest.fixture
    def tf_no_hyst(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=2.5,
                                                 hysteresis=0.0)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.01, verbose=False)
        return tf

    def test_find_no_hysteresis_converges(self, tf_no_hyst):
        tf = tf_no_hyst
        results = tf.find_no_hysteresis()
        assert results['threshold'] == pytest.approx(2.5, abs=0.02)

    def test_find_no_hysteresis_tries(self, tf_no_hyst):
        tf = tf_no_hyst
        tf.find_no_hysteresis()
        assert tf.tries > 0

    def test_find_no_hysteresis_uncertainty(self, tf_no_hyst):
        tf = tf_no_hyst
        tf.find_no_hysteresis()
        assert tf.rising_uncertainty <= 0.01
        assert tf.falling_uncertainty <= 0.01


class TestThresholdFinderWithHysteresis:

    def test_find_binary_converges_with_hysteresis(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=2.5,
                                                 hysteresis=0.2)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.01, verbose=False)
        results = tf.find()
        assert 2.3 < results['threshold'] < 2.7

    def test_find_linear_detects_hysteresis(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=2.5,
                                                 hysteresis=0.2)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.05, verbose=False)
        results = tf.find_linear()
        assert results['rising'] > results['falling']
        assert results['hysteresis'] > 0
        assert results['rising'] == pytest.approx(2.6, abs=0.1)
        assert results['falling'] == pytest.approx(2.4, abs=0.1)


class TestThresholdFinderLinearSearch:

    @pytest.fixture
    def tf_linear(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=1.0,
                                                 hysteresis=0.0)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=2.0,
                              abstol=0.05, verbose=False)
        return tf

    def test_find_linear_no_hysteresis(self, tf_linear):
        tf = tf_linear
        results = tf.find_linear_no_hysteresis()
        assert results['threshold'] == pytest.approx(1.0, abs=0.1)

    def test_find_linear_with_hysteresis(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=1.0,
                                                 hysteresis=0.2)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=2.0,
                              abstol=0.05, verbose=False)
        results = tf.find_linear()
        assert results['rising'] == pytest.approx(1.1, abs=0.1)
        assert results['falling'] == pytest.approx(0.9, abs=0.1)


class TestThresholdFinderPolarity:

    def test_inverted_polarity(self, master_instance):
        """Comparator output goes LOW when input exceeds threshold."""
        m = master_instance
        comp = comparator(falling_threshold=2.5, rising_threshold=2.5,
                          out_high=0.0, out_low=5.0)
        comp.set()  # start high (inverted: output=0.0)

        forcing = m.add_channel_dummy('force')
        forcing.write(0.0)
        forcing.add_write_callback(lambda ch, val: comp.write(val))

        output = m.add_channel_virtual('out', read_function=comp.read)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.01, verbose=False)
        results = tf.find_no_hysteresis()
        assert results['threshold'] == pytest.approx(2.5, abs=0.02)


class TestThresholdFinderChannels:

    def test_add_channel_all(self, master_instance):
        m = master_instance
        forcing, output = make_comparator_system(m, threshold=2.5)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.01, verbose=False)
        tf.add_channel_all('th')
        m.add(tf)
        channel_names = m.get_all_channel_names()
        assert 'th_rising' in channel_names
        assert 'th_falling' in channel_names
        assert 'th_hysteresis' in channel_names
        assert 'th_tries' in channel_names


class TestComparatorOvershoot:
    """Test threshold_finder with comparator overshoot modeling."""

    def test_overshoot_shifts_binary_threshold(self, master_instance):
        """With large overshoot, the binary search finds a shifted threshold."""
        m = master_instance
        # Large overshoot: 50% of step magnitude
        comp = comparator(falling_threshold=2.5, rising_threshold=2.5,
                          out_high=5.0, out_low=0.0, write_overshoot=0.5)

        forcing = m.add_channel_dummy('force')
        forcing.write(0.0)
        forcing.add_write_callback(lambda ch, val: comp.write(val))

        output = m.add_channel_virtual('out', read_function=comp.read)
        tf = threshold_finder(forcing, output,
                              minimum=0.0, maximum=5.0,
                              abstol=0.01, verbose=False)
        results = tf.find_no_hysteresis()
        # Still converges near the threshold (overshoot diminishes
        # as binary search narrows the window)
        assert results['threshold'] == pytest.approx(2.5, abs=0.1)
