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

    def test_zero_returns_denorm_min(self):
        result = float_next(0)
        assert result > 0
        assert result == sys.float_info.epsilon * sys.float_info.min

    def test_one(self):
        result = float_next(1.0)
        assert result > 1.0
        assert result - 1.0 == sys.float_info.epsilon

    def test_negative(self):
        result = float_next(-1.0)
        assert result > -1.0

    def test_power_of_two(self):
        result = float_next(2.0)
        assert result > 2.0

    def test_inf_raises(self):
        with pytest.raises(AssertionError):
            float_next(math.inf)

    def test_nan_raises(self):
        with pytest.raises(AssertionError):
            float_next(math.nan)

    def test_max_raises(self):
        with pytest.raises(AssertionError):
            float_next(sys.float_info.max)


class TestFloatPrior:

    def test_zero_returns_negative_denorm_min(self):
        result = float_prior(0)
        assert result < 0
        assert result == -(sys.float_info.epsilon * sys.float_info.min)

    def test_one(self):
        result = float_prior(1.0)
        assert result < 1.0

    def test_negative(self):
        result = float_prior(-1.0)
        assert result < -1.0

    def test_power_of_two(self):
        result = float_prior(2.0)
        assert result < 2.0

    def test_inf_raises(self):
        with pytest.raises(AssertionError):
            float_prior(-math.inf)

    def test_nan_raises(self):
        with pytest.raises(AssertionError):
            float_prior(math.nan)


class TestFloatDistance:

    def test_same_value(self):
        assert float_distance(1.0, 1.0) == 0

    def test_adjacent_floats(self):
        assert float_distance(1.0, float_next(1.0)) == 1

    def test_adjacent_floats_reversed(self):
        assert float_distance(float_next(1.0), 1.0) == -1

    def test_two_steps(self):
        a = 1.0
        b = float_next(float_next(a))
        assert float_distance(a, b) == 2

    def test_zero_to_denorm_min(self):
        denorm_min = sys.float_info.epsilon * sys.float_info.min
        dist = float_distance(0, denorm_min)
        assert dist >= 1

    def test_symmetry(self):
        assert float_distance(1.0, 2.0) == -float_distance(2.0, 1.0)

    def test_negative_values(self):
        a = -2.0
        b = -1.0
        dist = float_distance(a, b)
        assert dist > 0


class TestSafeDivide:

    def test_normal_division(self):
        assert safe_divide(10, 2) == 5.0

    def test_float_division(self):
        assert safe_divide(1.0, 3.0) == pytest.approx(1 / 3)

    def test_divide_by_zero(self):
        assert safe_divide(1, 0) is None

    def test_type_error(self):
        assert safe_divide("a", 2) is None

    def test_none_numerator(self):
        assert safe_divide(None, 2) is None

    def test_both_none(self):
        assert safe_divide(None, None) is None


class TestInterpolator:

    @pytest.fixture
    def linear(self):
        return interpolator([[0, 0], [10, 100]])

    @pytest.fixture
    def multi_point(self):
        return interpolator([[0, 0], [1, 10], [2, 20], [3, 30]])

    def test_interpolate_midpoint(self, linear):
        assert linear(5) == 50.0

    def test_interpolate_at_point(self, linear):
        assert linear(0) == 0.0
        assert linear(10) == 100.0

    def test_extrapolate_below(self, linear):
        assert linear(-5) == -50.0

    def test_extrapolate_above(self, linear):
        assert linear(15) == 150.0

    def test_get_x_val(self, linear):
        assert linear.get_x_val(50) == 5.0

    def test_multi_point_interpolation(self, multi_point):
        assert multi_point(1.5) == 15.0

    def test_add_point(self):
        interp = interpolator()
        interp.add_point(0, 0)
        interp.add_point(10, 100)
        assert interp(5) == 50.0

    def test_insufficient_points_raises(self):
        interp = interpolator([[0, 0]])
        with pytest.raises(Exception, match="two points"):
            interp(5)

    def test_non_monotonic_raises(self):
        with pytest.raises(Exception, match="monotonically"):
            interpolator([[0, 0], [1, 10], [2, 5]])

    def test_duplicate_x_raises(self):
        with pytest.raises(Exception, match="duplicated x"):
            interpolator([[0, 0], [0, 10]])

    def test_decreasing_y(self):
        interp = interpolator([[0, 100], [10, 0]])
        assert interp(5) == 50.0

    def test_callable(self):
        interp = interpolator([[0, 0], [1, 1]])
        assert interp(0.5) == 0.5


class TestFloatRange:

    def test_basic(self):
        result = floatRange(0, 1, 0.25)
        assert len(result) == 4
        assert result[0] == 0.0
        assert result[-1] == pytest.approx(0.75)

    def test_single_arg(self):
        result = floatRange(5)
        assert result == [0, 1, 2, 3, 4]

    def test_negative_step(self):
        result = floatRange(1.0, 0.0, -0.25)
        assert len(result) == 4
        assert result[0] == 1.0


class TestFloatRangeInc:

    def test_includes_endpoint(self):
        result = floatRangeInc(0, 1.0, 0.25)
        assert result[-1] == 1.0

    def test_endpoint_already_included(self):
        result = floatRangeInc(0, 4, 1)
        assert result.count(4) <= 1


class TestLogRange:

    def test_steps_per_decade(self):
        result = logRange(1, 100, stepsPerDecade=10)
        assert result[0] == 1.0
        assert all(result[i] < result[i + 1] for i in range(len(result) - 1))
        assert result[-1] < 100

    def test_steps_per_octave(self):
        result = logRange(1, 8, stepsPerOctave=1)
        assert result[0] == 1.0
        assert len(result) == 3  # 1, 2, 4

    def test_no_step_arg_raises(self):
        with pytest.raises(Exception, match="exactly one"):
            logRange(1, 100)

    def test_both_step_args_raises(self):
        with pytest.raises(Exception, match="exactly one"):
            logRange(1, 100, stepsPerDecade=10, stepsPerOctave=3)


class TestLogRangeInc:

    def test_includes_endpoint(self):
        result = logRangeInc(1, 100, stepsPerDecade=10)
        assert result[-1] == 100


class TestDecadeListRange:

    def test_single_decade(self):
        result = decadeListRange([1, 2, 5], 1)
        assert result == [1, 2, 5]

    def test_two_decades(self):
        result = decadeListRange([1, 2, 5], 2)
        assert result == [1, 2, 5, 10, 20, 50]

    def test_three_decades(self):
        result = decadeListRange([1, 5], 3)
        assert result == [1, 5, 10, 50, 100, 500]
