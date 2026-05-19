import math
import pytest
from PyICe.lab_utils.eng_string import eng_string
from PyICe.lab_utils.str2num import str2num
from PyICe.lab_utils.ordinalize import ordinalize
from PyICe.lab_utils.clean_unicode import clean_unicode
from PyICe.lab_utils.clean_ascii_code import clean_ascii_code
from PyICe.lab_utils.clean_sql import clean_sql


class TestEngString:

    @pytest.mark.parametrize('value, expected', [
        (1230, '1.23k'),
        (-1230000, '-1.23M'),
        (0.00123, '1.23m'),
        (0.00000123, '1.23µ'),
        (1.23e-9, '1.23n'),
        (1.23e-12, '1.23p'),
        (1.23e9, '1.23G'),
        (1.23e12, '1.23T'),
    ])
    def test_si_suffixes(self, value, expected):
        """Perform test si suffixes operation.

        Args:
            expected: Expected.
            value: Value to set.
        """
        assert eng_string(value, fmt=':.3g', si=True) == expected

    def test_zero(self):
        """Perform test zero operation."""
        result = eng_string(0)
        assert '0' in result

    def test_infinity(self):
        """Perform test infinity operation."""
        result = eng_string(math.inf)
        assert 'inf' in result

    def test_negative_infinity(self):
        """Perform test negative infinity operation."""
        result = eng_string(-math.inf)
        assert 'inf' in result

    def test_no_si(self):
        """Perform test no si operation."""
        result = eng_string(1230, si=False)
        assert 'e3' in result
        assert 'k' not in result

    def test_units_appended(self):
        """Perform test units appended operation."""
        result = eng_string(1000, si=True, units='V')
        assert result.endswith('V')
        assert 'k' in result or '1' in result

    def test_no_suffix_for_mid_range(self):
        """Perform test no suffix for mid range operation."""
        result = eng_string(123, si=True)
        assert result == '123'

    def test_non_number_raises(self):
        """Perform test non number raises operation."""
        with pytest.raises(AssertionError):
            eng_string("hello")


class TestStr2Num:

    def test_int_passthrough(self):
        """Perform test int passthrough operation."""
        assert str2num(42) == 42

    def test_float_passthrough(self):
        """Perform test float passthrough operation."""
        assert str2num(3.14) == 3.14

    def test_none_passthrough(self):
        """Perform test none passthrough operation."""
        assert str2num(None) is None

    def test_true_string(self):
        """Perform test true string operation."""
        assert str2num('True') is True

    def test_false_string(self):
        """Perform test false string operation."""
        assert str2num('False') is False

    def test_decimal_int(self):
        """Perform test decimal int operation."""
        assert str2num('123') == 123

    def test_hex_string(self):
        """Perform test hex string operation."""
        assert str2num('0xFF') == 255

    def test_octal_string(self):
        """Perform test octal string operation."""
        assert str2num('0o17') == 15

    def test_binary_string(self):
        """Perform test binary string operation."""
        assert str2num('0b1010') == 10

    def test_float_string(self):
        """Perform test float string operation."""
        assert str2num('3.14') == 3.14

    def test_scientific_notation(self):
        """Perform test scientific notation operation."""
        assert str2num('1.5e3') == 1500.0

    def test_invalid_raises(self):
        """Perform test invalid raises operation."""
        with pytest.raises(ValueError):
            str2num('not_a_number')

    def test_invalid_no_except(self):
        """Perform test invalid no except operation."""
        result = str2num('not_a_number', except_on_error=False)
        assert result == 'not_a_number'


class TestOrdinalize:

    @pytest.mark.parametrize('num, expected', [
        (0, '0th'),
        (1, '1st'),
        (2, '2nd'),
        (3, '3rd'),
        (4, '4th'),
        (10, '10th'),
        (11, '11th'),
        (12, '12th'),
        (13, '13th'),
        (20, '20th'),
        (21, '21st'),
        (22, '22nd'),
        (23, '23rd'),
        (100, '100th'),
        (101, '101st'),
        (111, '111th'),
        (112, '112th'),
        (113, '113th'),
        (122, '122nd'),
    ])
    def test_ordinals(self, num, expected):
        """Perform test ordinals operation.

        Args:
            expected: Expected.
            num: Count or number.
        """
        assert ordinalize(num) == expected

    def test_negative_raises(self):
        """Perform test negative raises operation."""
        with pytest.raises(AssertionError):
            ordinalize(-1)

    def test_float_raises(self):
        """Perform test float raises operation."""
        with pytest.raises(AssertionError):
            ordinalize(1.5)


class TestCleanUnicode:

    @pytest.mark.parametrize('char, replacement', [
        ('®', '_REG_'),
        ('°', '_DEG_'),
        ('²', '_SQ_'),
        ('µ', '_MICRO_'),
        ('×', '_MUL_'),
        ('÷', '_DIV_'),
        ('Ω', '_OHM_'),
        ('β', '_BETA_'),
        ('≤', '_LTEQ_'),
        ('≥', '_GTEQ_'),
    ])
    def test_unicode_replacements(self, char, replacement):
        """Perform test unicode replacements operation.

        Args:
            char: Char.
            replacement: Replacement.
        """
        assert clean_unicode(f'test{char}val') == f'test{replacement}val'

    def test_ascii_passthrough(self):
        """Perform test ascii passthrough operation."""
        assert clean_unicode('hello_world123') == 'hello_world123'

    def test_unmapped_high_unicode_raises(self):
        """Perform test unmapped high unicode raises operation."""
        with pytest.raises(Exception, match="code point"):
            clean_unicode('test☃val')  # snowman


class TestCleanAsciiCode:

    @pytest.mark.parametrize('char, replacement', [
        (' ', '_'),
        ('\t', '_'),
        ('!', '_BANG_'),
        ('.', 'p'),
        ('-', '_MNS_'),
        ('+', '_PLS_'),
        ('/', '_DIV_'),
        (':', '_CLN_'),
        ('=', '_EQLS_'),
        ('<', '_LSS_THN_'),
        ('>', '_GRTR_THN_'),
        ('@', '_AT_'),
        ('|', '_OR_'),
        ('~', '_TIL_'),
    ])
    def test_ascii_replacements(self, char, replacement):
        """Perform test ascii replacements operation.

        Args:
            char: Char.
            replacement: Replacement.
        """
        result = clean_ascii_code(f'A{char}B')
        assert replacement in result

    def test_alphanumeric_passthrough(self):
        """Perform test alphanumeric passthrough operation."""
        assert clean_ascii_code('hello_123') == 'hello_123'

    def test_leading_digit_gets_underscore(self):
        """Perform test leading digit gets underscore operation."""
        result = clean_ascii_code('3volts')
        assert result.startswith('_3')

    def test_unicode_cleaned_first(self):
        """Perform test unicode cleaned first operation."""
        result = clean_ascii_code('µ')
        assert result == '_MICRO_'


class TestCleanSql:

    def test_valid_name_passes(self):
        """Perform test valid name passes operation."""
        assert clean_sql('voltage_out') == 'voltage_out'

    def test_reserved_keyword_raises(self):
        """Perform test reserved keyword raises operation."""
        with pytest.raises(Exception, match="reserved keyword"):
            clean_sql('SELECT')

    def test_keyword_case_insensitive_in_word_boundary(self):
        """Perform test keyword case insensitive in word boundary operation."""
        with pytest.raises(Exception):
            clean_sql('CREATE')

    def test_keyword_as_substring_passes(self):
        # "OR" as a word boundary would match, but embedded in a larger word
        # clean_ascii_code first processes the string
        """Perform test keyword as substring passes operation."""
        assert clean_sql('voltage_sensor') == 'voltage_sensor'

    def test_special_chars_cleaned_before_keyword_check(self):
        """Perform test special chars cleaned before keyword check operation."""
        result = clean_sql('my.voltage')
        assert result == 'mypvoltage'
