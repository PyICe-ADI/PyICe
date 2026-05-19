import numpy as np
from PyICe.lab_utils.detrend import detrend_constant, detrend_linear
from PyICe.lab_utils.decimate import decimate


def make_recarray(x, y):
    """Return make recarray result.

    Args:
        x: X.
        y: Y.

    Returns:
        Result value.
    """
    return np.rec.fromarrays([x, y], names=['x', 'y'])


class TestDetrendConstant:
    """Tests for Detrend Constant."""

    def test_removes_mean(self):
        """Perform test removes mean operation."""
        x = np.arange(10, dtype=float)
        y = np.ones(10) * 5.0 + np.random.randn(10) * 0.01
        arr = make_recarray(x, y)
        result = detrend_constant(arr)
        assert abs(np.mean(result.y)) < 0.02
        np.testing.assert_array_equal(result.x, x)

    def test_preserves_x_axis(self):
        """Perform test preserves x axis operation."""
        x = np.linspace(0, 1, 20)
        y = np.ones(20) * 10.0
        arr = make_recarray(x, y)
        result = detrend_constant(arr)
        np.testing.assert_array_equal(result.x, x)

    def test_zero_mean_unchanged(self):
        """Perform test zero mean unchanged operation."""
        x = np.arange(10, dtype=float)
        y = np.array([1, -1, 1, -1, 1, -1, 1, -1, 1, -1], dtype=float)
        arr = make_recarray(x, y)
        result = detrend_constant(arr)
        np.testing.assert_array_almost_equal(result.y, y)


class TestDetrendLinear:
    """Tests for Detrend Linear."""

    def test_removes_linear_trend(self):
        """Perform test removes linear trend operation."""
        x = np.arange(100, dtype=float)
        y = 2.0 * x + 10.0
        arr = make_recarray(x, y)
        result = detrend_linear(arr)
        np.testing.assert_array_almost_equal(
            result.y, np.zeros(100), decimal=10)

    def test_preserves_oscillation(self):
        """Perform test preserves oscillation operation."""
        x = np.linspace(0, 2 * np.pi, 100)
        y = np.sin(x) + 3.0 * x
        arr = make_recarray(x, y)
        result = detrend_linear(arr)
        assert np.std(result.y) > 0.3
        assert abs(np.mean(result.y)) < 0.1

    def test_preserves_x_axis(self):
        """Perform test preserves x axis operation."""
        x = np.arange(50, dtype=float)
        y = x * 0.5
        arr = make_recarray(x, y)
        result = detrend_linear(arr)
        np.testing.assert_array_equal(result.x, x)


class TestDecimate:
    """Tests for Decimate."""

    def test_reduces_length(self):
        """Perform test reduces length operation."""
        x = np.arange(100, dtype=float)
        y = np.sin(x * 0.1)
        arr = make_recarray(x, y)
        result = decimate(arr, 5, ftype='fir')
        assert len(result) == 20

    def test_preserves_columns(self):
        """Perform test preserves columns operation."""
        x = np.arange(100, dtype=float)
        y = np.ones(100)
        arr = make_recarray(x, y)
        result = decimate(arr, 2, ftype='fir')
        assert 'x' in result.dtype.names
        assert 'y' in result.dtype.names

    def test_factor_10(self):
        """Perform test factor 10 operation."""
        x = np.arange(1000, dtype=float)
        y = np.random.randn(1000)
        arr = make_recarray(x, y)
        result = decimate(arr, 10, ftype='fir')
        assert len(result) == 100
