import math
import pytest
from PyICe.lab_utils.swap_endian import swap_endian
from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
from PyICe.lab_utils.twosComplementToSigned import twosComplementToSigned
from PyICe.lab_utils.bounded import bounded
from PyICe.lab_utils.isclose import isclose
from PyICe.lab_utils.parse_list import parse_list
from PyICe.lab_utils.ordered_pair import ordered_pair


class TestSwapEndian:
    """Tests for Swap Endian."""

    def test_two_bytes(self):
        """Perform test two bytes operation."""
        assert swap_endian(0x1234, elementCount=2) == 0x3412

    def test_four_bytes(self):
        """Perform test four bytes operation."""
        assert swap_endian(0x12345678, elementCount=4) == 0x78563412

    def test_single_byte_no_change(self):
        """Perform test single byte no change operation."""
        assert swap_endian(0xAB, elementCount=1) == 0xAB

    def test_three_bytes(self):
        """Perform test three bytes operation."""
        assert swap_endian(0x010203, elementCount=3) == 0x030201

    def test_bit_reversal(self):
        # Reverse 4 bits: 0b1010 -> 0b0101
        """Perform test bit reversal operation."""
        assert swap_endian(0b1010, elementCount=4, elementSize=1) == 0b0101

    def test_bit_reversal_8(self):
        # 0b10000000 -> 0b00000001
        """Perform test bit reversal 8 operation."""
        assert swap_endian(0x80, elementCount=8, elementSize=1) == 0x01

    def test_zero(self):
        """Perform test zero operation."""
        assert swap_endian(0x0000, elementCount=2) == 0x0000

    def test_overflow_raises(self):
        """Perform test overflow raises operation."""
        with pytest.raises(AssertionError):
            swap_endian(0x1FF, elementCount=1)

    def test_negative_raises(self):
        """Perform test negative raises operation."""
        with pytest.raises(AssertionError):
            swap_endian(-1, elementCount=2)


class TestSignedToTwosComplement:
    """Tests for Signed To Twos Complement."""

    def test_positive_value(self):
        """Perform test positive value operation."""
        assert signedToTwosComplement(5, 8) == 5

    def test_zero(self):
        """Perform test zero operation."""
        assert signedToTwosComplement(0, 8) == 0

    def test_negative_one(self):
        """Perform test negative one operation."""
        assert signedToTwosComplement(-1, 8) == 0xFF

    def test_negative_128(self):
        """Perform test negative 128 operation."""
        assert signedToTwosComplement(-128, 8) == 0x80

    def test_max_positive(self):
        """Perform test max positive operation."""
        assert signedToTwosComplement(127, 8) == 127

    def test_16bit_negative(self):
        """Perform test 16bit negative operation."""
        assert signedToTwosComplement(-1, 16) == 0xFFFF

    def test_overflow_positive_raises(self):
        """Perform test overflow positive raises operation."""
        with pytest.raises(AssertionError):
            signedToTwosComplement(128, 8)

    def test_overflow_negative_raises(self):
        """Perform test overflow negative raises operation."""
        with pytest.raises(AssertionError):
            signedToTwosComplement(-129, 8)


class TestTwosComplementToSigned:
    """Tests for Twos Complement To Signed."""

    def test_positive_value(self):
        """Perform test positive value operation."""
        assert twosComplementToSigned(5, 8) == 5

    def test_zero(self):
        """Perform test zero operation."""
        assert twosComplementToSigned(0, 8) == 0

    def test_max_positive(self):
        """Perform test max positive operation."""
        assert twosComplementToSigned(127, 8) == 127

    def test_negative_one(self):
        """Perform test negative one operation."""
        assert twosComplementToSigned(0xFF, 8) == -1

    def test_most_negative(self):
        """Perform test most negative operation."""
        assert twosComplementToSigned(0x80, 8) == -128

    def test_16bit(self):
        """Perform test 16bit operation."""
        assert twosComplementToSigned(0xFFFF, 16) == -1

    def test_overflow_raises(self):
        """Perform test overflow raises operation."""
        with pytest.raises(ValueError):
            twosComplementToSigned(256, 8)

    def test_negative_input_raises(self):
        """Perform test negative input raises operation."""
        with pytest.raises(ValueError):
            twosComplementToSigned(-1, 8)


class TestRoundtrip:
    """Verify signedToTwosComplement and twosComplementToSigned are inverses."""

    @pytest.mark.parametrize('value', [-128, -1, 0, 1, 127])
    def test_roundtrip_8bit(self, value):
        """Perform test roundtrip 8bit operation.

        Args:
            value: Value to set.
        """
        binary = signedToTwosComplement(value, 8)
        assert twosComplementToSigned(binary, 8) == value

    @pytest.mark.parametrize('value', [-32768, -1, 0, 1, 32767])
    def test_roundtrip_16bit(self, value):
        """Perform test roundtrip 16bit operation.

        Args:
            value: Value to set.
        """
        binary = signedToTwosComplement(value, 16)
        assert twosComplementToSigned(binary, 16) == value


class TestBounded:
    """Tests for Bounded."""

    def test_within_range(self):
        """Perform test within range operation."""
        assert bounded(5, min_value=0, max_value=10) == 5

    def test_clamp_above_max(self):
        """Perform test clamp above max operation."""
        assert bounded(15, min_value=0, max_value=10) == 10

    def test_clamp_below_min(self):
        """Perform test clamp below min operation."""
        assert bounded(-5, min_value=0, max_value=10) == 0

    def test_no_bounds(self):
        """Perform test no bounds operation."""
        assert bounded(999) == 999

    def test_only_min(self):
        """Perform test only min operation."""
        assert bounded(-5, min_value=0) == 0
        assert bounded(5, min_value=0) == 5

    def test_only_max(self):
        """Perform test only max operation."""
        assert bounded(15, max_value=10) == 10
        assert bounded(5, max_value=10) == 5

    def test_float_values(self):
        """Perform test float values operation."""
        assert bounded(3.7, min_value=1.0, max_value=3.5) == 3.5

    def test_equal_to_bounds(self):
        """Perform test equal to bounds operation."""
        assert bounded(10, min_value=10, max_value=10) == 10


class TestIsClose:
    """Tests for Is Close."""

    def test_equal_values(self):
        """Perform test equal values operation."""
        assert isclose(1.0, 1.0) is True

    def test_close_values(self):
        """Perform test close values operation."""
        assert isclose(1.0, 1.0 + 1e-10) is True

    def test_not_close(self):
        """Perform test not close operation."""
        assert isclose(1.0, 2.0) is False

    def test_relative_tolerance(self):
        """Perform test relative tolerance operation."""
        assert isclose(100.0, 101.0, rel_tol=0.02) is True
        assert isclose(100.0, 103.0, rel_tol=0.02) is False

    def test_absolute_tolerance(self):
        """Perform test absolute tolerance operation."""
        assert isclose(0.0, 0.001, abs_tol=0.01) is True
        assert isclose(0.0, 0.1, abs_tol=0.01) is False

    def test_nan_not_close(self):
        """Perform test nan not close operation."""
        assert isclose(math.nan, math.nan) is False

    def test_inf_close_to_itself(self):
        """Perform test inf close to itself operation."""
        assert isclose(math.inf, math.inf) is True

    def test_inf_not_close_to_finite(self):
        """Perform test inf not close to finite operation."""
        assert isclose(math.inf, 1e308) is False

    def test_negative_inf(self):
        """Perform test negative inf operation."""
        assert isclose(-math.inf, -math.inf) is True
        assert isclose(math.inf, -math.inf) is False

    def test_negative_tolerance_raises(self):
        """Perform test negative tolerance raises operation."""
        with pytest.raises(ValueError):
            isclose(1.0, 2.0, rel_tol=-0.1)

    def test_symmetry(self):
        """Perform test symmetry operation."""
        assert isclose(1.0, 1.1, rel_tol=0.2) == isclose(1.1, 1.0, rel_tol=0.2)

    def test_zero_comparison(self):
        """Perform test zero comparison operation."""
        assert isclose(0.0, 0.0) is True
        assert isclose(0.0, 1e-15) is False


class TestParseList:
    """Tests for Parse List."""

    def test_simple_list(self):
        """Perform test simple list operation."""
        assert parse_list("[1, 2, 3]") == [1, 2, 3]

    def test_nested_list(self):
        """Perform test nested list operation."""
        assert parse_list("[[1, 2], [3, 4]]") == [[1, 2], [3, 4]]

    def test_mixed_types(self):
        """Perform test mixed types operation."""
        assert parse_list("[1, 'hello', 3.14, True]") == [
            1, 'hello', 3.14, True]

    def test_empty_list(self):
        """Perform test empty list operation."""
        assert parse_list("[]") == []

    def test_non_string_raises(self):
        """Perform test non string raises operation."""
        with pytest.raises(Exception, match="isn't a string"):
            parse_list([1, 2, 3])

    def test_tuple(self):
        """Perform test tuple operation."""
        assert parse_list("(1, 2, 3)") == (1, 2, 3)


class TestOrderedPair:
    """Tests for Ordered Pair."""

    @pytest.fixture
    def sample(self):
        """Return sample result.

        Returns:
            Result value.
        """
        return ordered_pair([[0, 0], [1, 10], [2, 20], [3, 30], [4, 40]])

    def test_is_list(self, sample):
        """Perform test is list operation.

        Args:
            sample: Sample.
        """
        assert isinstance(sample, list)
        assert len(sample) == 5

    def test_xscale(self, sample):
        """Perform test xscale operation.

        Args:
            sample: Sample.
        """
        sample.xscale(2)
        assert sample[0] == [0, 0]
        assert sample[2] == [4, 20]

    def test_yscale(self, sample):
        """Perform test yscale operation.

        Args:
            sample: Sample.
        """
        sample.yscale(0.5)
        assert sample[1] == [1, 5.0]

    def test_xoffset(self, sample):
        """Perform test xoffset operation.

        Args:
            sample: Sample.
        """
        sample.xoffset(10)
        assert sample[0] == [10, 0]
        assert sample[4] == [14, 40]

    def test_yoffset(self, sample):
        """Perform test yoffset operation.

        Args:
            sample: Sample.
        """
        sample.yoffset(-5)
        assert sample[0] == [0, -5]
        assert sample[2] == [2, 15]

    def test_xyscale(self, sample):
        """Perform test xyscale operation.

        Args:
            sample: Sample.
        """
        sample.xyscale(2, 3)
        assert sample[1] == [2, 30]

    def test_transform(self, sample):
        """Perform test transform operation.

        Args:
            sample: Sample.
        """
        sample.transform(x_transform=lambda x: x ** 2,
                         y_transform=lambda y: y + 1)
        assert sample[2] == [4, 21]

    def test_transform_x_only(self, sample):
        """Perform test transform x only operation.

        Args:
            sample: Sample.
        """
        sample.transform(x_transform=lambda x: x * 10)
        assert sample[1] == [10, 10]
        assert sample[3] == [30, 30]

    def test_truncate_by_count(self, sample):
        """Perform test truncate by count operation.

        Args:
            sample: Sample.
        """
        sample.truncate(length=3)
        assert len(sample) == 3
        assert sample[0] == [0, 0]

    def test_truncate_with_offset(self, sample):
        """Perform test truncate with offset operation.

        Args:
            sample: Sample.
        """
        sample.truncate(length=2, offset=1)
        assert len(sample) == 2
        assert sample[0] == [1, 10]

    def test_decimate(self, sample):
        """Perform test decimate operation.

        Args:
            sample: Sample.
        """
        original_len = len(sample)
        sample.decimate(0.6)
        assert len(sample) < original_len
        assert len(sample) == 3

    def test_numpy_recarray(self, sample):
        """Perform test numpy recarray operation.

        Args:
            sample: Sample.
        """
        arr = sample.numpy_recarray(force_float_dtype=True)
        assert arr.x[0] == 0.0
        assert arr.y[2] == 20.0
        assert len(arr) == 5

    def test_x_extents(self, sample):
        """Perform test x extents operation.

        Args:
            sample: Sample.
        """
        ext = sample.x_extents()
        assert ext['min'] == 0
        assert ext['max'] == 4
        assert ext['diff'] == 4

    def test_y_extents(self, sample):
        """Perform test y extents operation.

        Args:
            sample: Sample.
        """
        ext = sample.y_extents()
        assert ext['min'] == 0
        assert ext['max'] == 40
        assert ext['diff'] == 40

    def test_interpolated_y_value(self, sample):
        """Perform test interpolated y value operation.

        Args:
            sample: Sample.
        """
        assert sample.interpolated_y_value(1.5) == pytest.approx(15.0)
        assert sample.interpolated_y_value(0) == pytest.approx(0.0)
        assert sample.interpolated_y_value(4) == pytest.approx(40.0)
