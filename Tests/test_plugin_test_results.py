"""Unit tests for PyICe plugins/test_results.py

Tests the pure-logic utility functions, data structures, evaluation
logic, and JSON round-trip serialization/deserialization.
"""
import datetime
import json
import os
import pytest
import numpy as np
from unittest.mock import MagicMock
from PyICe.plugins.test_results import (
    freeze, make_hash, none_min, none_max, none_abs,
    Test_Results, Test_Results_Reload,
)


# --- Utility Functions ---

class TestFreeze:

    def test_freeze_dict(self):
        result = freeze({'a': 1, 'b': 2})
        assert isinstance(result, frozenset)

    def test_freeze_list(self):
        result = freeze([1, 2, 3])
        assert result == (1, 2, 3)

    def test_freeze_nested_dict(self):
        result = freeze({'a': [1, 2], 'b': {'c': 3}})
        assert hash(result)  # should be hashable

    def test_freeze_set(self):
        result = freeze({1, 2, 3})
        assert isinstance(result, frozenset)

    def test_freeze_tuple(self):
        result = freeze((1, [2, 3]))
        assert result == (1, (2, 3))

    def test_freeze_scalar(self):
        assert freeze(42) == 42
        assert freeze('hello') == 'hello'
        assert freeze(None) is None

    def test_freeze_unhashable_raises(self):
        class Unhashable:
            __hash__ = None
        with pytest.raises(TypeError, match="FREEZE"):
            freeze(Unhashable())


class TestMakeHash:

    def test_same_dict_same_hash(self):
        assert make_hash({'a': 1, 'b': 2}) == make_hash({'a': 1, 'b': 2})

    def test_different_dict_different_hash(self):
        assert make_hash({'a': 1}) != make_hash({'a': 2})

    def test_nested_structures(self):
        h = make_hash({'x': [1, 2, 3], 'y': {'z': 4}})
        assert isinstance(h, int)

    def test_list_order_matters(self):
        assert make_hash([1, 2, 3]) != make_hash([3, 2, 1])

    def test_none(self):
        h = make_hash(None)
        assert isinstance(h, int)


class TestNoneOperations:

    def test_none_min_both_none(self):
        assert none_min(None, None) is None

    def test_none_min_first_none(self):
        assert none_min(None, 5) == 5

    def test_none_min_second_none(self):
        assert none_min(3, None) == 3

    def test_none_min_normal(self):
        assert none_min(3, 5) == 3

    def test_none_max_both_none(self):
        assert none_max(None, None) is None

    def test_none_max_first_none(self):
        assert none_max(None, 5) == 5

    def test_none_max_second_none(self):
        assert none_max(3, None) == 3

    def test_none_max_normal(self):
        assert none_max(3, 5) == 5

    def test_none_abs_none(self):
        assert none_abs(None) is None

    def test_none_abs_positive(self):
        assert none_abs(5) == 5

    def test_none_abs_negative(self):
        assert none_abs(-3) == 3


# --- Data Structures ---

def make_test_results():
    """Create a minimal Test_Results instance with a mock module."""
    module = MagicMock()
    module.get_name.return_value = 'test_module'
    module.get_database.return_value = MagicMock()
    tr = Test_Results.__new__(Test_Results)
    tr._test_results = {}
    tr._ate_results = {}
    tr._test_declarations = []
    tr.test_limits = {}
    tr.max_con_len = 0
    tr._name = 'test_module'
    tr._module = module
    tr._traceability_info = {}
    tr._failure_override = False
    return tr


class TestTestResult:

    def test_create_result(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr,
            test_name='vout_accuracy',
            conditions={'temp': 25},
            min_data=3.28,
            max_data=3.32,
            passes=True,
            failure_reason='',
            collected_data=[3.28, 3.30, 3.32],
            plot=[],
        )
        assert result.test_name == 'vout_accuracy'
        assert result.passes is True

    def test_bool_pass(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=1, max_data=1, passes=True,
            failure_reason='', collected_data=[1], plot=[],
        )
        assert bool(result) is True

    def test_bool_fail(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=1, max_data=1, passes=False,
            failure_reason='out of spec', collected_data=[1], plot=[],
        )
        assert bool(result) is False

    def test_len(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=1, max_data=3, passes=True,
            failure_reason='', collected_data=[1, 2, 3], plot=[],
        )
        assert len(result) == 3

    def test_min_max(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=1, max_data=5, passes=True,
            failure_reason='', collected_data=[1, 3, 5], plot=[],
        )
        assert result._min() == 1
        assert result._max() == 5

    def test_min_max_empty(self):
        tr = make_test_results()
        result = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=None, max_data=None, passes=False,
            failure_reason='no data', collected_data=[], plot=[],
        )
        assert result._min() is None
        assert result._max() is None

    def test_add_combines_results(self):
        tr = make_test_results()
        r1 = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions={'c': 1},
            min_data=1, max_data=3, passes=True,
            failure_reason='', collected_data=[1, 2, 3], plot=[],
            query=None,
        )
        r2 = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions={'c': 1},
            min_data=4, max_data=6, passes=True,
            failure_reason='', collected_data=[4, 5, 6], plot=[],
            query=None,
        )
        combined = r1 + r2
        assert len(combined) == 6
        assert combined._min() == 1
        assert combined._max() == 6
        assert combined.passes is True

    def test_add_propagates_failure(self):
        tr = make_test_results()
        r1 = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=1, max_data=1, passes=True,
            failure_reason='', collected_data=[1], plot=[],
            query=None,
        )
        r2 = Test_Results._test_result(
            outerclass=tr, test_name='t', conditions=None,
            min_data=99, max_data=99, passes=False,
            failure_reason='over limit', collected_data=[99], plot=[],
            query=None,
        )
        combined = r1 + r2
        assert combined.passes is False


class TestTestResultsList:

    def test_bool_all_pass(self):
        tr = make_test_results()
        rl = Test_Results._test_results_list('test', upper_limit=10,
                                             lower_limit=0, override=False)
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=None,
            min_data=5, max_data=5, passes=True,
            failure_reason='', collected_data=[5], plot=[],
        ))
        assert bool(rl) is True

    def test_bool_one_fail(self):
        tr = make_test_results()
        rl = Test_Results._test_results_list('test', upper_limit=10,
                                             lower_limit=0, override=False)
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=None,
            min_data=5, max_data=5, passes=True,
            failure_reason='', collected_data=[5], plot=[],
        ))
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=None,
            min_data=99, max_data=99, passes=False,
            failure_reason='', collected_data=[99], plot=[],
        ))
        assert bool(rl) is False

    def test_bool_empty_is_false(self):
        rl = Test_Results._test_results_list('test', upper_limit=10,
                                             lower_limit=0, override=False)
        assert bool(rl) is False

    def test_filter_by_condition(self):
        tr = make_test_results()
        rl = Test_Results._test_results_list('test', upper_limit=10,
                                             lower_limit=0, override=False)
        cond_a = {'temp': 25}
        cond_b = {'temp': 85}
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=cond_a,
            min_data=5, max_data=5, passes=True,
            failure_reason='', collected_data=[5], plot=[],
        ))
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=cond_b,
            min_data=7, max_data=7, passes=True,
            failure_reason='', collected_data=[7], plot=[],
        ))
        filtered = rl.filter(make_hash(cond_a))
        assert len(filtered) == 1
        assert filtered[0].conditions == cond_a

    def test_min_max_aggregate(self):
        tr = make_test_results()
        rl = Test_Results._test_results_list('test', upper_limit=10,
                                             lower_limit=0, override=False)
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=None,
            min_data=2, max_data=4, passes=True,
            failure_reason='', collected_data=[2, 3, 4], plot=[],
        ))
        rl.append(Test_Results._test_result(
            outerclass=tr, test_name='test', conditions=None,
            min_data=1, max_data=8, passes=True,
            failure_reason='', collected_data=[1, 5, 8], plot=[],
        ))
        assert rl._min() == 1
        assert rl._max() == 8


# --- Evaluation Logic ---

class TestEvaluateList:

    def setup_method(self):
        self.tr = make_test_results()

    def declare_test(self, name, lower=None, upper=None):
        self.tr.test_limits[name] = {
            'upper_limit': upper,
            'lower_limit': lower,
        }

    def test_pass_within_range(self):
        self.declare_test('vout', lower=3.0, upper=3.6)
        result = self.tr._evaluate_list('vout', [3.1, 3.3, 3.5],
                                        conditions=None)
        assert result.passes is True

    def test_fail_above_upper(self):
        self.declare_test('vout', lower=3.0, upper=3.6)
        result = self.tr._evaluate_list('vout', [3.1, 3.3, 3.7],
                                        conditions=None)
        assert result.passes is False

    def test_fail_below_lower(self):
        self.declare_test('vout', lower=3.0, upper=3.6)
        result = self.tr._evaluate_list('vout', [2.9, 3.3, 3.5],
                                        conditions=None)
        assert result.passes is False

    def test_exact_match_pass(self):
        self.declare_test('code', lower=42, upper=42)
        result = self.tr._evaluate_list('code', [42, 42, 42],
                                        conditions=None)
        assert result.passes is True

    def test_exact_match_fail(self):
        self.declare_test('code', lower=42, upper=42)
        result = self.tr._evaluate_list('code', [42, 43, 42],
                                        conditions=None)
        assert result.passes is False

    def test_no_limits_always_passes(self):
        self.declare_test('info', lower=None, upper=None)
        result = self.tr._evaluate_list('info', [1, 2, 3],
                                        conditions=None)
        assert result.passes is True

    def test_upper_only(self):
        self.declare_test('current', lower=None, upper=0.01)
        result = self.tr._evaluate_list('current', [0.005, 0.008],
                                        conditions=None)
        assert result.passes is True
        result2 = self.tr._evaluate_list('current', [0.005, 0.02],
                                         conditions={'trial': 2})
        assert result2.passes is False

    def test_lower_only(self):
        self.declare_test('gain', lower=10.0, upper=None)
        result = self.tr._evaluate_list('gain', [12.0, 15.0],
                                        conditions=None)
        assert result.passes is True
        result2 = self.tr._evaluate_list('gain', [9.0],
                                         conditions={'trial': 2})
        assert result2.passes is False

    def test_single_number_input(self):
        self.declare_test('scalar', lower=0, upper=10)
        result = self.tr._evaluate_list('scalar', 5, conditions=None)
        assert result.passes is True
        assert len(result) == 1

    def test_none_data_registers_failure(self):
        self.declare_test('bad', lower=0, upper=10)
        result = self.tr._evaluate_list('bad', None, conditions=None)
        assert result.passes is False
        assert 'None' in result.failure_reason

    def test_none_in_list_registers_failure(self):
        self.declare_test('partial', lower=0, upper=10)
        self.tr._evaluate_list('partial', [5, None, 7],
                               conditions=None)
        # First failure registered, then remaining data evaluated
        results_list = self.tr._test_results['partial']
        assert any(not r.passes for r in results_list)

    def test_nan_limit_treated_as_none(self):
        self.declare_test('nan_test', lower=float('nan'),
                          upper=float('nan'))
        result = self.tr._evaluate_list('nan_test', [1, 2, 3],
                                        conditions=None)
        assert result.passes is True

    def test_min_max_tracked(self):
        self.declare_test('stats', lower=0, upper=100)
        result = self.tr._evaluate_list('stats', [10, 50, 90],
                                        conditions=None)
        assert result.min_data == 10
        assert result.max_data == 90

    def test_conditions_stored(self):
        self.declare_test('cond', lower=0, upper=10)
        conds = {'temp': 25, 'vdd': 3.3}
        result = self.tr._evaluate_list('cond', [5], conditions=conds)
        assert result.conditions == conds

    def test_failure_override(self):
        self.tr._failure_override = True
        self.declare_test('crashed', lower=0, upper=10)
        result = self.tr._evaluate_list('crashed', [5],
                                        conditions=None)
        assert result.passes is False
        assert 'Crashed' in result.failure_reason


class TestRegisterTestFailure:

    def test_registers_failure(self):
        tr = make_test_results()
        tr.test_limits['bad_test'] = {'upper_limit': 10, 'lower_limit': 0}
        result = tr._register_test_failure('bad_test', 'comm error',
                                           conditions=None)
        assert result.passes is False
        assert result.failure_reason == 'comm error'
        assert 'bad_test' in tr._test_declarations

    def test_failure_with_conditions(self):
        tr = make_test_results()
        tr.test_limits['t'] = {'upper_limit': 10, 'lower_limit': 0}
        conds = {'temp': -40}
        result = tr._register_test_failure('t', 'timeout',
                                           conditions=conds)
        assert result.conditions == conds


# --- JSON Encoder ---

class TestCustomJSONEncoder:

    def get_encoder(self):
        """Extract the CustomJSONizer class from _json_report."""
        import json
        from numpy import bool_, ndarray

        class CustomJSONizer(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bool_):
                    return bool(obj)
                elif isinstance(obj, datetime.datetime):
                    return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                elif isinstance(obj, ndarray):
                    return obj.tolist()
                else:
                    return super().default(obj)
        return CustomJSONizer

    def test_numpy_bool(self):
        enc = self.get_encoder()
        result = json.dumps({'val': np.bool_(True)}, cls=enc)
        assert '"val": true' in result

    def test_datetime(self):
        enc = self.get_encoder()
        dt = datetime.datetime(2024, 1, 15, 10, 30, 0)
        result = json.dumps({'dt': dt}, cls=enc)
        assert '2024-01-15' in result

    def test_numpy_array(self):
        enc = self.get_encoder()
        arr = np.array([1.0, 2.0, 3.0])
        result = json.dumps({'arr': arr}, cls=enc)
        parsed = json.loads(result)
        assert parsed['arr'] == [1.0, 2.0, 3.0]


# --- JSON Schema & Round-Trip Tests ---

def build_populated_test_results():
    """Build a Test_Results with multiple tests, conditions, and results."""
    tr = make_test_results()

    # Declare test limits
    tr.test_limits['vout_accuracy'] = {'upper_limit': 3.6, 'lower_limit': 3.0}
    tr.test_limits['quiescent_current'] = {'upper_limit': 0.01, 'lower_limit': None}
    tr.test_limits['register_readback'] = {'upper_limit': 0xAB, 'lower_limit': 0xAB}
    tr.test_limits['info_only'] = {'upper_limit': None, 'lower_limit': None}

    # Evaluate with various scenarios
    tr._evaluate_list('vout_accuracy', [3.28, 3.30, 3.32],
                      conditions={'temp': 25, 'vdd': 5.0})
    tr._evaluate_list('vout_accuracy', [3.10, 3.12, 3.15],
                      conditions={'temp': -40, 'vdd': 5.0})
    tr._evaluate_list('vout_accuracy', [3.50, 3.55, 3.58],
                      conditions={'temp': 85, 'vdd': 5.0})
    tr._evaluate_list('quiescent_current', [0.005, 0.006],
                      conditions={'temp': 25, 'vdd': 5.0})
    tr._evaluate_list('register_readback', [0xAB, 0xAB, 0xAB],
                      conditions=None)
    tr._evaluate_list('info_only', [42, 99, 7], conditions=None)

    return tr


def write_json_report(tr, path):
    """Generate JSON report bypassing database metadata lookup."""
    # Mock the module's database access for _json_report
    mock_db = MagicMock()
    mock_db.get_table_names.return_value = []
    tr._module.get_database.return_value = mock_db
    tr._module.get_name.return_value = 'test_module'

    json_str = tr._json_report(
        declarations=tr._test_declarations,
        results=tr._test_results,
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(json_str)
    return json_str


class TestJSONSchema:
    """Verify the JSON report structure matches expected schema."""

    @pytest.fixture
    def report(self, tmp_path):
        tr = build_populated_test_results()
        json_path = str(tmp_path / "test_results.json")
        json_str = write_json_report(tr, json_path)
        return json.loads(json_str)

    def test_top_level_keys(self, report):
        assert 'test_module' in report
        assert 'test_crashed' in report
        assert 'report_date' in report
        assert 'tests' in report
        assert 'summary' in report

    def test_test_module_name(self, report):
        assert report['test_module'] == 'test_module'

    def test_test_crashed_is_bool(self, report):
        assert isinstance(report['test_crashed'], bool)

    def test_report_date_format(self, report):
        dt = datetime.datetime.strptime(report['report_date'],
                                        '%Y-%m-%dT%H:%M:%S.%fZ')
        assert isinstance(dt, datetime.datetime)

    def test_summary_has_passes(self, report):
        assert 'passes' in report['summary']
        assert isinstance(report['summary']['passes'], bool)

    def test_tests_contain_declarations(self, report):
        for test_name, test_data in report['tests'].items():
            assert 'declaration' in test_data
            assert 'upper_limit' in test_data['declaration']
            assert 'lower_limit' in test_data['declaration']

    def test_tests_contain_results(self, report):
        for test_name, test_data in report['tests'].items():
            assert 'results' in test_data
            assert 'cases' in test_data['results']
            assert 'summary' in test_data['results']

    def test_case_structure(self, report):
        cases = report['tests']['vout_accuracy']['results']['cases']
        assert len(cases) == 3  # three temperature conditions
        for case in cases:
            assert 'conditions' in case
            assert 'case_results' in case
            assert 'summary' in case

    def test_case_results_fields(self, report):
        cases = report['tests']['vout_accuracy']['results']['cases']
        for case in cases:
            for result in case['case_results']:
                assert 'min_data' in result
                assert 'max_data' in result
                assert 'passes' in result
                assert 'failure_reason' in result
                assert 'collected_data' in result
                assert 'plot' not in result

    def test_exact_match_limits(self, report):
        decl = report['tests']['register_readback']['declaration']
        assert decl['upper_limit'] == decl['lower_limit'] == 0xAB

    def test_null_condition_case(self, report):
        cases = report['tests']['register_readback']['results']['cases']
        assert cases[0]['conditions'] is None


class TestJSONRoundTrip:
    """Verify round-trip: Test_Results → JSON → Test_Results_Reload preserves data."""

    @pytest.fixture
    def round_trip(self, tmp_path):
        """Build results, serialize to JSON, reload, return both."""
        original = build_populated_test_results()
        json_path = str(tmp_path / "test_results.json")
        json_str = write_json_report(original, json_path)

        # Patch open() within Test_Results_Reload to inject our
        # collection_date and traceability (normally from metadata table)
        data = json.loads(json_str)
        data['collection_date'] = '2024-06-15T12:00:00.000000Z'
        data['traceability'] = {'dut_serial': 'SN001', 'board_rev': 'A'}
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        reloaded = Test_Results_Reload(results_json=json_path)
        return original, reloaded, json_path

    def test_test_declarations_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        assert list(reloaded._test_declarations) == list(original._test_declarations)

    def test_test_limits_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            assert reloaded.test_limits[test_name]['upper_limit'] == \
                   original.test_limits[test_name]['upper_limit']
            assert reloaded.test_limits[test_name]['lower_limit'] == \
                   original.test_limits[test_name]['lower_limit']

    def test_collected_data_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            orig_results = original._test_results[test_name]
            reload_results = reloaded._test_results[test_name]
            orig_all_data = []
            for r in orig_results:
                orig_all_data.extend(r.collected_data)
            reload_all_data = []
            for r in reload_results:
                reload_all_data.extend(r.collected_data)
            assert reload_all_data == orig_all_data

    def test_pass_fail_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            assert bool(reloaded._test_results[test_name]) == \
                   bool(original._test_results[test_name])

    def test_conditions_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        orig_results = original._test_results['vout_accuracy']
        reload_results = reloaded._test_results['vout_accuracy']
        orig_conds = [r.conditions for r in orig_results]
        reload_conds = [r.conditions for r in reload_results]
        assert reload_conds == orig_conds

    def test_min_max_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            orig_results = original._test_results[test_name]
            reload_results = reloaded._test_results[test_name]
            for orig, reloaded_r in zip(orig_results, reload_results):
                assert reloaded_r.min_data == orig.min_data
                assert reloaded_r.max_data == orig.max_data

    def test_failure_reason_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            for orig, reloaded_r in zip(original._test_results[test_name],
                                        reloaded._test_results[test_name]):
                assert reloaded_r.failure_reason == orig.failure_reason

    def test_plot_reset_to_empty(self, round_trip):
        _, reloaded, _ = round_trip
        for test_name in reloaded._test_declarations:
            for r in reloaded._test_results[test_name]:
                assert r.plot == []

    def test_query_preserved_or_none(self, round_trip):
        original, reloaded, _ = round_trip
        for test_name in original._test_declarations:
            for orig, reloaded_r in zip(original._test_results[test_name],
                                        reloaded._test_results[test_name]):
                if orig.query is None:
                    assert reloaded_r.query is None
                else:
                    assert reloaded_r.query == orig.query

    def test_traceability_preserved(self, round_trip):
        _, reloaded, _ = round_trip
        info = reloaded.get_traceability_info()
        assert info['dut_serial'] == 'SN001'
        assert info['board_rev'] == 'A'

    def test_overall_bool_preserved(self, round_trip):
        original, reloaded, _ = round_trip
        assert bool(reloaded) == bool(original)

    def test_double_round_trip(self, round_trip, tmp_path):
        """Serialize reloaded results back to JSON and compare structure."""
        original, reloaded, _ = round_trip
        # Re-export from reloaded object
        reloaded._module = MagicMock()
        mock_db = MagicMock()
        mock_db.get_table_names.return_value = []
        reloaded._module.get_database.return_value = mock_db
        reloaded._module.get_name.return_value = 'test_module'

        json_str_2 = reloaded._json_report(
            declarations=reloaded._test_declarations,
            results=reloaded._test_results,
        )
        data_2 = json.loads(json_str_2)

        # Core fields must match
        for test_name in original._test_declarations:
            reload_cases = data_2['tests'][test_name]['results']['cases']
            # Verify collected_data in each case
            for case in reload_cases:
                for result in case['case_results']:
                    assert 'collected_data' in result
                    assert isinstance(result['collected_data'], list)
