import math
import sys
import pytest
from PyICe.lab_utils.float_next import float_next
from PyICe.lab_utils.float_prior import float_prior
from PyICe.lab_utils.float_distance import float_distance
from PyICe.lab_utils.safe_divide import safe_divide
from PyICe.lab_utils.interpolator import interpolator
from PyICe.lab_utils.ranges import (floatRange, floatRangeInc,
                                    logRange, logRangeInc, decadeListRange)


class TestFloatNext:
    """Tests for Float Next."""

    def test_zero_returns_denorm_min(self):
        """Perform test zero returns denorm min operation."""
        result = float_next(0)
        assert result > 0
        assert result == sys.float_info.epsilon * sys.float_info.min

    def test_one(self):
        """Perform test one operation."""
        result = float_next(1.0)
        assert result > 1.0
        assert result - 1.0 == sys.float_info.epsilon

    def test_negative(self):
        """Perform test negative operation."""
        result = float_next(-1.0)
        assert result > -1.0

    def test_power_of_two(self):
        """Perform test power of two operation."""
        result = float_next(2.0)
        assert result > 2.0

    def test_inf_raises(self):
        """Perform test inf raises operation."""
        with pytest.raises(AssertionError):
            float_next(math.inf)

    def test_nan_raises(self):
        """Perform test nan raises operation."""
        with pytest.raises(AssertionError):
            float_next(math.nan)

    def test_max_raises(self):
        """Perform test max raises operation."""
        with pytest.raises(AssertionError):
            float_next(sys.float_info.max)


class TestFloatPrior:
    """Tests for Float Prior."""

    def test_zero_returns_negative_denorm_min(self):
        """Perform test zero returns negative denorm min operation."""
        result = float_prior(0)
        assert result < 0
        assert result == -(sys.float_info.epsilon * sys.float_info.min)

    def test_one(self):
        """Perform test one operation."""
        result = float_prior(1.0)
        assert result < 1.0

    def test_negative(self):
        """Perform test negative operation."""
        result = float_prior(-1.0)
        assert result < -1.0

    def test_power_of_two(self):
        """Perform test power of two operation."""
        result = float_prior(2.0)
        assert result < 2.0

    def test_inf_raises(self):
        """Perform test inf raises operation."""
        with pytest.raises(AssertionError):
            float_prior(-math.inf)

    def test_nan_raises(self):
        """Perform test nan raises operation."""
        with pytest.raises(AssertionError):
            float_prior(math.nan)


class TestFloatDistance:
    """Tests for Float Distance."""

    def test_same_value(self):
        """Perform test same value operation."""
        assert float_distance(1.0, 1.0) == 0

    def test_adjacent_floats(self):
        """Perform test adjacent floats operation."""
        assert float_distance(1.0, float_next(1.0)) == 1

    def test_adjacent_floats_reversed(self):
        """Perform test adjacent floats reversed operation."""
        assert float_distance(float_next(1.0), 1.0) == -1

    def test_two_steps(self):
        """Perform test two steps operation."""
        a = 1.0
        b = float_next(float_next(a))
        assert float_distance(a, b) == 2

    def test_zero_to_denorm_min(self):
        """Perform test zero to denorm min operation."""
        denorm_min = sys.float_info.epsilon * sys.float_info.min
        dist = float_distance(0, denorm_min)
        assert dist >= 1

    def test_symmetry(self):
        """Perform test symmetry operation."""
        assert float_distance(1.0, 2.0) == -float_distance(2.0, 1.0)

    def test_negative_values(self):
        """Perform test negative values operation."""
        a = -2.0
        b = -1.0
        dist = float_distance(a, b)
        assert dist > 0


class TestSafeDivide:
    """Tests for Safe Divide."""

    def test_normal_division(self):
        """Perform test normal division operation."""
        assert safe_divide(10, 2) == 5.0

    def test_float_division(self):
        """Perform test float division operation."""
        assert safe_divide(1.0, 3.0) == pytest.approx(1 / 3)

    def test_divide_by_zero(self):
        """Perform test divide by zero operation."""
        assert safe_divide(1, 0) is None

    def test_type_error(self):
        """Perform test type error operation."""
        assert safe_divide("a", 2) is None

    def test_none_numerator(self):
        """Perform test none numerator operation."""
        assert safe_divide(None, 2) is None

    def test_both_none(self):
        """Perform test both none operation."""
        assert safe_divide(None, None) is None


class TestInterpolator:
    """Tests for Interpolator."""

    @pytest.fixture
    def linear(self):
        """Return linear result.

        Returns:
            Result value.
        """
        return interpolator([[0, 0], [10, 100]])

    @pytest.fixture
    def multi_point(self):
        """Return multi point result.

        Returns:
            Result value.
        """
        return interpolator([[0, 0], [1, 10], [2, 20], [3, 30]])

    def test_interpolate_midpoint(self, linear):
        """Perform test interpolate midpoint operation.

        Args:
            linear: Linear.
        """
        assert linear(5) == 50.0

    def test_interpolate_at_point(self, linear):
        """Perform test interpolate at point operation.

        Args:
            linear: Linear.
        """
        assert linear(0) == 0.0
        assert linear(10) == 100.0

    def test_extrapolate_below(self, linear):
        """Perform test extrapolate below operation.

        Args:
            linear: Linear.
        """
        assert linear(-5) == -50.0

    def test_extrapolate_above(self, linear):
        """Perform test extrapolate above operation.

        Args:
            linear: Linear.
        """
        assert linear(15) == 150.0

    def test_get_x_val(self, linear):
        """Perform test get x val operation.

        Args:
            linear: Linear.
        """
        assert linear.get_x_val(50) == 5.0

    def test_multi_point_interpolation(self, multi_point):
        """Perform test multi point interpolation operation.

        Args:
            multi_point: Multi point.
        """
        assert multi_point(1.5) == 15.0

    def test_add_point(self):
        """Perform test add point operation."""
        interp = interpolator()
        interp.add_point(0, 0)
        interp.add_point(10, 100)
        assert interp(5) == 50.0

    def test_insufficient_points_raises(self):
        """Perform test insufficient points raises operation."""
        interp = interpolator([[0, 0]])
        with pytest.raises(Exception, match="two points"):
            interp(5)

    def test_non_monotonic_raises(self):
        """Perform test non monotonic raises operation."""
        with pytest.raises(Exception, match="monotonically"):
            interpolator([[0, 0], [1, 10], [2, 5]])

    def test_duplicate_x_raises(self):
        """Perform test duplicate x raises operation."""
        with pytest.raises(Exception, match="duplicated x"):
            interpolator([[0, 0], [0, 10]])

    def test_decreasing_y(self):
        """Perform test decreasing y operation."""
        interp = interpolator([[0, 100], [10, 0]])
        assert interp(5) == 50.0

    def test_callable(self):
        """Perform test callable operation."""
        interp = interpolator([[0, 0], [1, 1]])
        assert interp(0.5) == 0.5


class TestFloatRange:
    """Tests for Float Range."""

    def test_basic(self):
        """Perform test basic operation."""
        result = floatRange(0, 1, 0.25)
        assert len(result) == 4
        assert result[0] == 0.0
        assert result[-1] == pytest.approx(0.75)

    def test_single_arg(self):
        """Perform test single arg operation."""
        result = floatRange(5)
        assert result == [0, 1, 2, 3, 4]

    def test_negative_step(self):
        """Perform test negative step operation."""
        result = floatRange(1.0, 0.0, -0.25)
        assert len(result) == 4
        assert result[0] == 1.0


class TestFloatRangeInc:
    """Tests for Float Range Inc."""

    def test_includes_endpoint(self):
        """Perform test includes endpoint operation."""
        result = floatRangeInc(0, 1.0, 0.25)
        assert result[-1] == 1.0

    def test_endpoint_already_included(self):
        """Perform test endpoint already included operation."""
        result = floatRangeInc(0, 4, 1)
        assert result.count(4) <= 1


class TestLogRange:
    """Tests for Log Range."""

    def test_steps_per_decade(self):
        """Perform test steps per decade operation."""
        result = logRange(1, 100, stepsPerDecade=10)
        assert result[0] == 1.0
        assert all(result[i] < result[i + 1] for i in range(len(result) - 1))
        assert result[-1] < 100

    def test_steps_per_octave(self):
        """Perform test steps per octave operation."""
        result = logRange(1, 8, stepsPerOctave=1)
        assert result[0] == 1.0
        assert len(result) == 3  # 1, 2, 4

    def test_no_step_arg_raises(self):
        """Perform test no step arg raises operation."""
        with pytest.raises(Exception, match="exactly one"):
            logRange(1, 100)

    def test_both_step_args_raises(self):
        """Perform test both step args raises operation."""
        with pytest.raises(Exception, match="exactly one"):
            logRange(1, 100, stepsPerDecade=10, stepsPerOctave=3)


class TestLogRangeInc:
    """Tests for Log Range Inc."""

    def test_includes_endpoint(self):
        """Perform test includes endpoint operation."""
        result = logRangeInc(1, 100, stepsPerDecade=10)
        assert result[-1] == 100


class TestDecadeListRange:
    """Tests for Decade List Range."""

    def test_single_decade(self):
        """Perform test single decade operation."""
        result = decadeListRange([1, 2, 5], 1)
        assert result == [1, 2, 5]

    def test_two_decades(self):
        """Perform test two decades operation."""
        result = decadeListRange([1, 2, 5], 2)
        assert result == [1, 2, 5, 10, 20, 50]

    def test_three_decades(self):
        """Perform test three decades operation."""
        result = decadeListRange([1, 5], 3)
        assert result == [1, 5, 10, 50, 100, 500]
