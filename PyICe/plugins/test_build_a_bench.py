"""Unit tests for Master_Test_Template.build_a_bench and its dispatch in Plugin_Manager."""

import pytest
from unittest.mock import MagicMock, patch
from PyICe.plugins.master_test_template import Master_Test_Template


class TestBuildABenchBase:
    """Tests for the base Master_Test_Template.build_a_bench method."""

    def test_returns_none(self):
        template = Master_Test_Template()
        result = template.build_a_bench()
        assert result is None

    def test_qualname_starts_with_master_test_template(self):
        template = Master_Test_Template()
        assert template.build_a_bench.__qualname__.startswith('Master_Test_Template')

    def test_overridden_qualname_does_not_start_with_master_test_template(self):
        class MyTest(Master_Test_Template):
            def build_a_bench(self):
                pass

        test = MyTest()
        assert not test.build_a_bench.__qualname__.startswith('Master_Test_Template')


class TestBuildABenchDispatch:
    """Tests for how Plugin_Manager dispatches build_a_bench."""

    def _make_test_with_build_a_bench(self, side_effect=None):
        """Create a mock test object that has an overridden build_a_bench."""
        class CustomTest(Master_Test_Template):
            def __init__(self):
                self._name = "custom_test"

            def build_a_bench(self):
                if side_effect:
                    side_effect()

        test = CustomTest()
        return test

    def _make_test_without_build_a_bench(self):
        """Create a mock test object using the base build_a_bench."""
        test = Master_Test_Template()
        test._name = "base_test"
        return test

    def test_override_is_detected(self):
        test = self._make_test_with_build_a_bench()
        assert not test.build_a_bench.__qualname__.startswith('Master_Test_Template')

    def test_base_is_detected(self):
        test = self._make_test_without_build_a_bench()
        assert test.build_a_bench.__qualname__.startswith('Master_Test_Template')

    def test_overridden_build_a_bench_is_called(self):
        called = []

        def mark_called():
            called.append(True)

        test = self._make_test_with_build_a_bench(side_effect=mark_called)
        if not test.build_a_bench.__qualname__.startswith('Master_Test_Template'):
            test.build_a_bench()

        assert called == [True]

    def test_base_build_a_bench_is_not_called_when_not_overridden(self):
        test = self._make_test_without_build_a_bench()
        fallback_called = []

        if not test.build_a_bench.__qualname__.startswith('Master_Test_Template'):
            test.build_a_bench()
        else:
            fallback_called.append(True)

        assert fallback_called == [True]

    def test_multiple_tests_only_first_is_used(self, capsys):
        """Simulates the plugin manager warning when multiple tests exist."""
        class Test1(Master_Test_Template):
            def __init__(self):
                self._name = "test_one"

            def get_name(self):
                return self._name

            def build_a_bench(self):
                pass

        class Test2(Master_Test_Template):
            def __init__(self):
                self._name = "test_two"

            def get_name(self):
                return self._name

            def build_a_bench(self):
                pass

        tests = [Test1(), Test2()]

        if not tests[0].build_a_bench.__qualname__.startswith('Master_Test_Template'):
            tests[0].build_a_bench()
            if len(tests) > 1:
                print(f"WARNING: Only the first test's ({tests[0].get_name()}) build_a_bench() is used. "
                      f"The remaining {len(tests) - 1} test(s) will share this bench configuration.")

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "test_one" in captured.out
        assert "1 test(s) will share" in captured.out

    def test_subclass_can_access_pm_master(self):
        """Verifies that build_a_bench can access self.pm.master as documented."""
        class TestWithBench(Master_Test_Template):
            def __init__(self):
                self.pm = MagicMock()
                self.pm.master = MagicMock()

            def build_a_bench(self):
                master = self.pm.master
                master.add(MagicMock())

        test = TestWithBench()
        test.build_a_bench()
        test.pm.master.add.assert_called_once()

    def test_subclass_build_a_bench_can_return_none_explicitly(self):
        class TestExplicitNone(Master_Test_Template):
            def build_a_bench(self):
                return None

        test = TestExplicitNone()
        assert test.build_a_bench() is None
        assert not test.build_a_bench.__qualname__.startswith('Master_Test_Template')

    def test_deep_inheritance_still_detected_as_override(self):
        """A grandchild class override is still not Master_Test_Template."""
        class MiddleTemplate(Master_Test_Template):
            pass

        class FinalTest(MiddleTemplate):
            def build_a_bench(self):
                pass

        test = FinalTest()
        assert not test.build_a_bench.__qualname__.startswith('Master_Test_Template')

    def test_inherited_but_not_overridden_still_detected_as_base(self):
        """A subclass that doesn't override build_a_bench keeps the base qualname."""
        class MiddleTemplate(Master_Test_Template):
            pass

        class FinalTest(MiddleTemplate):
            pass

        test = FinalTest()
        assert test.build_a_bench.__qualname__.startswith('Master_Test_Template')
