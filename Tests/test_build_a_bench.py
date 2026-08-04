"""Unit tests for Master_Test_Template.build_a_bench and its dispatch in Plugin_Manager."""

import warnings
import functools
import pytest
from unittest.mock import MagicMock, patch
from PyICe.plugins.master_test_template import Master_Test_Template


class TestBuildABenchBase:
    """Tests for the base Master_Test_Template.build_a_bench method."""

    def test_returns_none(self):
        """The base implementation of build_a_bench returns None."""
        template = Master_Test_Template()
        assert template.build_a_bench() is None

    def test_identity_matches_base(self):
        """The base method is identical to Master_Test_Template.build_a_bench via identity."""
        template = Master_Test_Template()
        assert type(template).build_a_bench is Master_Test_Template.build_a_bench

    def test_overridden_identity_does_not_match_base(self):
        """An overridden method does not match Master_Test_Template.build_a_bench by identity."""
        class MyTest(Master_Test_Template):
            """Subclass that overrides build_a_bench."""

            def build_a_bench(self):
                pass

        test = MyTest()
        assert type(test).build_a_bench is not Master_Test_Template.build_a_bench


class TestBuildABenchDispatch:
    """Tests for how Plugin_Manager dispatches build_a_bench."""

    def _make_test_with_build_a_bench(self, side_effect=None):
        """Create a mock test object that has an overridden build_a_bench."""
        class CustomTest(Master_Test_Template):
            """Subclass that overrides build_a_bench with an optional side effect."""

            def __init__(self):
                pass

            def get_name(self):
                return "custom_test"

            def build_a_bench(self):
                if side_effect:
                    side_effect()

        return CustomTest()

    def _make_test_without_build_a_bench(self):
        """Create a mock test object using the base build_a_bench."""
        return Master_Test_Template()

    def test_override_is_detected(self):
        """A subclass that overrides build_a_bench is detected as an override."""
        test = self._make_test_with_build_a_bench()
        assert type(test).build_a_bench is not Master_Test_Template.build_a_bench

    def test_base_is_detected(self):
        """A subclass that does not override build_a_bench is detected as the base."""
        test = self._make_test_without_build_a_bench()
        assert type(test).build_a_bench is Master_Test_Template.build_a_bench

    def test_overridden_build_a_bench_is_called(self):
        """When an override is detected, calling build_a_bench executes the subclass body."""
        called = []
        test = self._make_test_with_build_a_bench(side_effect=lambda: called.append(True))

        if type(test).build_a_bench is not Master_Test_Template.build_a_bench:
            test.build_a_bench()

        assert called == [True]

    def test_base_build_a_bench_is_not_called_when_not_overridden(self):
        """When no override is detected, build_a_bench is skipped."""
        test = self._make_test_without_build_a_bench()
        fallback_called = []

        if type(test).build_a_bench is not Master_Test_Template.build_a_bench:
            test.build_a_bench()
        else:
            fallback_called.append(True)

        assert fallback_called == [True]

    def test_multiple_tests_emits_warning(self):
        """Simulates the plugin manager warning when multiple tests exist."""
        class Test1(Master_Test_Template):
            """First test with an overridden build_a_bench."""

            def __init__(self):
                pass

            def get_name(self):
                return "test_one"

            def build_a_bench(self):
                pass

        class Test2(Master_Test_Template):
            """Second test with an overridden build_a_bench."""

            def __init__(self):
                pass

            def get_name(self):
                return "test_two"

            def build_a_bench(self):
                pass

        tests = [Test1(), Test2()]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            if (type(tests[0]).build_a_bench is not
                    Master_Test_Template.build_a_bench):
                tests[0].build_a_bench()
                if len(tests) > 1:
                    warnings.warn(
                        f"Only the first test's "
                        f"({tests[0].get_name()}) "
                        f"build_a_bench() is used. "
                        f"The remaining {len(tests) - 1} "
                        f"test(s) will share this bench "
                        f"configuration.",
                        stacklevel=2)

        assert len(w) == 1
        assert "test_one" in str(w[0].message)
        assert "1 test(s) will share" in str(w[0].message)

    def test_subclass_can_access_pm_master(self):
        """Verifies that build_a_bench can access self.pm.master as documented."""
        class TestWithBench(Master_Test_Template):
            """Subclass that accesses self.pm.master inside build_a_bench."""

            def __init__(self):
                self.pm = MagicMock()
                self.pm.master = MagicMock()

            def build_a_bench(self):
                self.pm.master.add(MagicMock())

        test = TestWithBench()
        test.build_a_bench()
        test.pm.master.add.assert_called_once()

    def test_build_a_bench_exception_is_raised(self):
        """An exception in build_a_bench is wrapped in RuntimeError."""


        class FailingTest(Master_Test_Template):
            """Subclass whose build_a_bench raises."""

            def __init__(self):
                pass

            def get_name(self):
                return "failing_test"

            def build_a_bench(self):
                raise ValueError("instrument not found")

        test = FailingTest()
        with pytest.raises(RuntimeError, match="BENCH MAKER"):
            if type(test).build_a_bench is not Master_Test_Template.build_a_bench:
                try:
                    test.build_a_bench()
                except Exception as e:
                    raise RuntimeError(
                        f"BENCH MAKER: build_a_bench() failed in test '{test.get_name()}': {e}"
                    ) from e

    def test_deep_inheritance_still_detected_as_override(self):
        """A grandchild class override is still not Master_Test_Template."""
        class MiddleTemplate(Master_Test_Template):
            """Intermediate subclass that does not override build_a_bench."""

        class FinalTest(MiddleTemplate):
            """Grandchild that overrides build_a_bench."""

            def build_a_bench(self):
                pass

        test = FinalTest()
        assert type(test).build_a_bench is not Master_Test_Template.build_a_bench

    def test_inherited_but_not_overridden_still_detected_as_base(self):
        """A subclass that doesn't override build_a_bench keeps the base identity."""
        class MiddleTemplate(Master_Test_Template):
            """Intermediate subclass that does not override build_a_bench."""

        class FinalTest(MiddleTemplate):
            """Grandchild that also does not override build_a_bench."""

        test = FinalTest()
        assert type(test).build_a_bench is Master_Test_Template.build_a_bench

    def test_decorated_override_still_detected(self):
        """Identity check is immune to decorator wrapping unlike __qualname__."""
        def my_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            return wrapper

        class DecoratedTest(Master_Test_Template):
            """Subclass with a decorated build_a_bench override."""

            @my_decorator
            def build_a_bench(self):
                pass

        test = DecoratedTest()
        assert type(test).build_a_bench is not Master_Test_Template.build_a_bench


class TestBuildABenchIntegration:
    """Integration tests exercising the actual Plugin_Manager.collect() dispatch."""

    def _make_plugin_manager_with_test(self, test_class):
        """Create a Plugin_Manager, add a test, and return the pm instance."""
        from PyICe.plugins.plugin_manager import Plugin_Manager

        pm = Plugin_Manager(settings={
            'plugins': [],
            'project_path': '.',
            'verbose': False,
        })
        pm.add_test(test_class)
        return pm

    def test_overridden_build_a_bench_called_in_collect(self):
        """Plugin_Manager.collect() calls build_a_bench when overridden."""
        called = []

        class TestWithBench(Master_Test_Template):
            """Test class that overrides build_a_bench to track calls."""

            def __init__(self):
                self.project_folder_name = "test_project"

            def build_a_bench(self):
                called.append(True)

            def collect(self):
                pass

        pm = self._make_plugin_manager_with_test(TestWithBench)

        with patch.object(pm, 'add_instrument_channels') as mock_aic:
            pm.collect(temperatures=[25])
            assert called == [True]
            mock_aic.assert_not_called()

    def test_base_build_a_bench_falls_back_to_add_instrument_channels(self):
        """Plugin_Manager.collect() calls add_instrument_channels when not overridden."""
        class TestWithoutBench(Master_Test_Template):
            """Test class that does not override build_a_bench."""

            def __init__(self):
                self.project_folder_name = "test_project"

            def collect(self):
                pass

        pm = self._make_plugin_manager_with_test(TestWithoutBench)

        with patch.object(pm, 'add_instrument_channels') as mock_aic:
            pm.collect(temperatures=[25])
            mock_aic.assert_called_once()

    def test_build_a_bench_exception_marks_test_as_crashed(self):
        """Plugin_Manager.collect() marks the test as crashed when build_a_bench raises."""
        class FailingBench(Master_Test_Template):
            """Test class whose build_a_bench raises an error."""

            def __init__(self):
                self.project_folder_name = "test_project"

            def build_a_bench(self):
                raise ValueError("bad instrument config")

            def collect(self):
                pass

        pm = self._make_plugin_manager_with_test(FailingBench)
        pm.collect(temperatures=[25])
        test_instance = pm.tests[0]
        assert test_instance._is_crashed is True
        exc_type, exc_value, _ = test_instance._crash_info
        assert exc_type is RuntimeError
        assert "BENCH MAKER" in str(exc_value)
        assert "bad instrument config" in str(exc_value)
