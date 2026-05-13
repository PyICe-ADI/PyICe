import pytest
from PyICe.lab_core import master, integer_channel
from PyICe.virtual_instruments import (
    dummy, dummy_read, dummy_write,
    expect, ExpectException, ExpectOverException, ExpectUnderException,
    servo, ServoException,
    accumulator, differencer,
)


class TestDummy:

    def test_dummy_write_channel(self):
        d = dummy()
        ch = d.add_channel_write('wch')
        ch.write(42)
        assert ch.read() == 42

    def test_dummy_read_channel_random(self):
        d = dummy()
        d.set_random_read(True)
        ch = d.add_channel_read('rch')
        val = ch.read()
        assert val is not None

    def test_dummy_read_channel_no_random(self):
        d = dummy()
        d.set_random_read(False)
        ch = d.add_channel_read('rch')
        val = ch.read()
        assert val is None

    def test_dummy_write_integer_channel(self):
        d = dummy()
        ch = d.add_channel_write('ich', integer_size=8)
        assert isinstance(ch, integer_channel)
        ch.write(100)
        assert ch.read() == 100

    def test_dummy_read_is_subclass(self):
        d = dummy_read()
        ch = d.add_channel('rch')
        assert not ch.is_writeable()

    def test_dummy_write_is_subclass(self):
        d = dummy_write()
        ch = d.add_channel('wch')
        assert ch.is_writeable()

    def test_dummy_verbose(self, capsys):
        d = dummy()
        d.set_verbose(True)
        d.add_channel_write('v')
        captured = capsys.readouterr()
        assert 'dummy write channel' in captured.out.lower()

    def test_add_to_master(self, master_instance):
        d = dummy()
        d.add_channel_write('dch')
        d['dch'].write(7)
        master_instance.add(d)
        assert master_instance.read_channel('dch') == 7


class TestExpectComparisons:

    def test_compare_exact_pass(self):
        assert expect.compare_exact(5, 5) is True

    def test_compare_exact_fail(self):
        assert expect.compare_exact(5, 6) is False

    def test_compare_pct_pass(self):
        assert expect.compare_pct(1.05, 1.0, 0.1) is True

    def test_compare_pct_fail(self):
        assert expect.compare_pct(1.2, 1.0, 0.1) is False

    def test_compare_abs_pass(self):
        assert expect.compare_abs(10.05, 10.0, 0.1) is True

    def test_compare_abs_fail(self):
        assert expect.compare_abs(10.5, 10.0, 0.1) is False

    def test_compare_pct_not_above(self):
        assert expect.compare_pct_not_above(1.05, 1.0, 0.1) is True
        assert expect.compare_pct_not_above(1.15, 1.0, 0.1) is False

    def test_compare_pct_not_below(self):
        assert expect.compare_pct_not_below(0.95, 1.0, 0.1) is True
        assert expect.compare_pct_not_below(0.85, 1.0, 0.1) is False

    def test_compare_abs_not_above(self):
        assert expect.compare_abs_not_above(10.05, 10.0, 0.1) is True
        assert expect.compare_abs_not_above(10.2, 10.0, 0.1) is False

    def test_compare_abs_not_below(self):
        assert expect.compare_abs_not_below(9.95, 10.0, 0.1) is True
        assert expect.compare_abs_not_below(9.8, 10.0, 0.1) is False

    def test_compare_strict(self):
        assert expect.compare_strict(10.0, 10.0, 0.01, 0.5) is True
        assert expect.compare_strict(10.5, 10.0, 0.01, 0.1) is False

    def test_compare_lenient(self):
        assert expect.compare_lenient(10.5, 10.0, 0.1, 0.1) is True
        assert expect.compare_lenient(20.0, 10.0, 0.01, 0.1) is False


class TestExpectChecks:

    @pytest.fixture
    def exp(self):
        return expect(verbose_pass=False)

    def test_check_exact_pass(self, exp):
        result = exp.check_exact(5, 5, en_assertion=False)
        assert result is True

    def test_check_exact_fail_no_assertion(self, exp):
        result = exp.check_exact(5, 6, en_assertion=False)
        assert result is False

    def test_check_exact_fail_with_assertion(self, exp):
        with pytest.raises(ExpectException):
            exp.check_exact(5, 6, en_assertion=True)

    def test_check_pct_pass(self, exp):
        result = exp.check_pct(1.0, 1.0, 0.1, en_assertion=False)
        assert result is True

    def test_check_pct_fail_over(self, exp):
        with pytest.raises(ExpectOverException):
            exp.check_pct(1.2, 1.0, 0.1, en_assertion=True)

    def test_check_pct_fail_under(self, exp):
        with pytest.raises(ExpectUnderException):
            exp.check_pct(0.8, 1.0, 0.1, en_assertion=True)

    def test_check_abs_pass(self, exp):
        result = exp.check_abs(10.05, 10.0, 0.1, en_assertion=False)
        assert result is True

    def test_check_abs_fail(self, exp):
        with pytest.raises(ExpectException):
            exp.check_abs(10.5, 10.0, 0.1, en_assertion=True)

    def test_custom_prefixes(self):
        exp = expect(verbose_pass=False, err_msg_prefix="ERROR: ",
                     pass_msg_prefix="OK: ")
        result = exp.check_exact(1, 2, en_assertion=False, name="test")
        assert result is False


class TestExpectChannels:

    def test_expect_channel_pct_immediate(self, master_instance):
        m = master_instance
        source = m.add_channel_dummy('source')
        source.write(10.0)

        exp = expect(verbose_pass=False)
        exp.add_channel_expect_pct('expect_ch', source,
                                   tolerance=0.1,
                                   en_immediate=True,
                                   en_assertion=False)
        m.add(exp)
        exp_ch = m.get_channel('expect_ch')
        exp_ch.write(10.0)
        result_ch = m.get_channel('expect_ch_pass')
        assert result_ch.read() is True

    def test_expect_channel_abs_immediate(self, master_instance):
        m = master_instance
        source = m.add_channel_dummy('source')
        source.write(5.0)

        exp = expect(verbose_pass=False)
        exp.add_channel_expect_abs('expect_ch', source,
                                   tolerance=0.5,
                                   en_immediate=True,
                                   en_assertion=False)
        m.add(exp)
        exp_ch = m.get_channel('expect_ch')
        exp_ch.write(5.2)
        result_ch = m.get_channel('expect_ch_pass')
        assert result_ch.read() is True

    def test_expect_channel_exact_immediate(self, master_instance):
        m = master_instance
        source = m.add_channel_dummy('source', integer_size=8)
        source.write(42)

        exp = expect(verbose_pass=False)
        exp.add_channel_expect_exact('expect_ch', source,
                                     en_immediate=True,
                                     en_assertion=False)
        m.add(exp)
        exp_ch = m.get_channel('expect_ch')
        exp_ch.write(42)
        result_ch = m.get_channel('expect_ch_pass')
        assert result_ch.read() is True

    def test_expect_channel_callback_mode(self, master_instance):
        m = master_instance
        source = m.add_channel_dummy('source')
        source.write(10.0)

        exp = expect(verbose_pass=False)
        exp.add_channel_expect_pct('expect_ch', source,
                                   tolerance=0.1,
                                   en_immediate=False,
                                   en_assertion=False)
        m.add(exp)
        exp_ch = m.get_channel('expect_ch')
        exp_ch.write(10.0)
        source.read()
        result_ch = m.get_channel('expect_ch_pass')
        assert result_ch.read() is True


class TestAccumulator:

    def test_basic_accumulation(self):
        acc = accumulator(init=0)
        acc.add_channel_accumulation('total')
        acc.add_channel_accumulate('add')
        assert acc['total'].read() == 0
        acc['add'].write(5)
        assert acc['total'].read() == 5
        acc['add'].write(3)
        assert acc['total'].read() == 8

    def test_initial_value(self):
        acc = accumulator(init=100)
        acc.add_channel_accumulation('total')
        assert acc['total'].read() == 100

    def test_negative_accumulation(self):
        acc = accumulator(init=10)
        acc.add_channel_accumulate('sub')
        acc.add_channel_accumulation('total')
        acc['sub'].write(-3)
        assert acc['total'].read() == 7

    def test_accumulate_method(self):
        acc = accumulator(init=0)
        acc.accumulate(10)
        acc.accumulate(20)
        assert acc.accumulation == 30

    def test_add_to_master(self, master_instance):
        m = master_instance
        acc = accumulator()
        acc.add_channel_accumulation('sum')
        acc.add_channel_accumulate('input')
        m.add(acc)
        m.write_channel('input', 7)
        assert m.read_channel('sum') == 7


class TestDifferencer:

    def test_basic_difference(self):
        diff = differencer(init=0)
        diff.add_channel_read_difference('delta')
        diff.add_channel_compute_difference('val')
        diff['val'].write(10)
        assert diff['delta'].read() == 10
        diff['val'].write(15)
        assert diff['delta'].read() == 5

    def test_first_difference_with_no_init(self):
        diff = differencer(init=None)
        diff.add_channel_read_difference('delta')
        diff.add_channel_compute_difference('val')
        diff['val'].write(10)
        assert diff['delta'].read() is None
        diff['val'].write(15)
        assert diff['delta'].read() == 5

    def test_negative_difference(self):
        diff = differencer(init=10)
        diff.difference(5)
        assert diff.diff == -5

    def test_register_channel_callback(self, master_instance):
        m = master_instance
        source = m.add_channel_virtual('src', read_function=lambda: 42)
        diff = differencer(init=0)
        diff.add_channel_read_difference('delta')
        diff.register_difference_channel(source)
        m.add(diff)
        source.read()
        assert diff['delta'].read() == 42
        source.read()
        assert diff['delta'].read() == 0


class TestServo:

    @pytest.fixture
    def linear_system(self, master_instance):
        """Simulate a linear system: output = 2 * forcing."""
        m = master_instance
        forcing = m.add_channel_dummy('force')
        forcing.write(0)

        def read_feedback():
            return forcing.read() * 2.0

        feedback = m.add_channel_virtual('feedback',
                                         read_function=read_feedback)
        return m, forcing, feedback

    def test_servo_converges(self, linear_system):
        m, forcing, feedback = linear_system
        s = servo(feedback, forcing,
                  minimum=-100, maximum=100,
                  abstol=0.01, verbose=False)
        tries = s.servo(target=10.0)
        assert tries is not False
        assert abs(feedback.read() - 10.0) < 0.01

    def test_servo_channel(self, linear_system):
        m, forcing, feedback = linear_system
        s = servo(feedback, forcing,
                  minimum=-100, maximum=100,
                  abstol=0.01, verbose=False)
        s.add_channel_target('servo_target')
        m.add(s)
        m.write_channel('servo_target', 20.0)
        assert abs(feedback.read() - 20.0) < 0.01

    def test_servo_check_within_tolerance(self, linear_system):
        m, forcing, feedback = linear_system
        s = servo(feedback, forcing,
                  minimum=-100, maximum=100,
                  abstol=0.5, verbose=False)
        s.target = 10.0
        assert s.servo_check(readback=10.2) is True
        assert s.servo_check(readback=20.0) is False

    def test_servo_exceeds_max_tries(self, master_instance):
        m = master_instance
        forcing = m.add_channel_dummy('force')
        forcing.write(0)
        feedback = m.add_channel_virtual('fb', read_function=lambda: 0)
        s = servo(feedback, forcing,
                  minimum=-10, maximum=10,
                  abstol=0.001, max_tries=2,
                  except_on_fail=True, verbose=False)
        with pytest.raises(ServoException):
            s.servo(target=5.0)

    def test_servo_no_except_returns_false(self, master_instance):
        m = master_instance
        forcing = m.add_channel_dummy('force')
        forcing.write(0)
        feedback = m.add_channel_virtual('fb', read_function=lambda: 0)
        s = servo(feedback, forcing,
                  minimum=-10, maximum=10,
                  abstol=0.001, max_tries=2,
                  except_on_fail=False, verbose=False)
        result = s.servo(target=5.0)
        assert result is False

    def test_servo_reconfigure(self, linear_system):
        m, forcing, feedback = linear_system
        s = servo(feedback, forcing,
                  minimum=-100, maximum=100,
                  abstol=0.01, verbose=False)
        s.reconfigure(minimum=-50, maximum=50, abstol=0.1)
        assert s.minimum == -50
        assert s.maximum == 50
        assert s.abstol == 0.1
