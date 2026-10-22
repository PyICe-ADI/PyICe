"""Demo script: build a few Test_Results objects and print the summary email."""

import sys
from PyICe.plugins.test_results import Test_Results, Failed_Eval, build_results_summary

# --- Test 1: all passing ---
tr1 = Test_Results(name='vout_regulation', module=None)
tr1.test_limits['vout_accuracy'] = {'lower_limit': 3.25, 'upper_limit': 3.35}
tr1.test_limits['vout_ripple'] = {'lower_limit': 0, 'upper_limit': 0.05}
tr1._evaluate_list('vout_accuracy', iter_data=[3.28, 3.31, 3.30], conditions={'temp': 25})
tr1._evaluate_list('vout_ripple', iter_data=[0.01, 0.02], conditions={'temp': 25})

# --- Test 2: one refid fails ---
tr2 = Test_Results(name='current_limits', module=None)
tr2.test_limits['ilimit_high'] = {'lower_limit': 0.9, 'upper_limit': 1.1}
tr2.test_limits['ilimit_low'] = {'lower_limit': 0.4, 'upper_limit': 0.6}
tr2._evaluate_list('ilimit_high', iter_data=[1.05], conditions={'temp': 25})
tr2._evaluate_list('ilimit_low', iter_data=[0.8], conditions={'temp': 25})  # fails

# --- Test 3: collection crashed (simulated via _failure_override) ---
tr3 = Test_Results(name='thermal_shutdown', module=None)
tr3._failure_override = True
tr3.test_limits['tsd_threshold'] = {'lower_limit': 145, 'upper_limit': 165}
tr3._evaluate_list('tsd_threshold', iter_data=[155], conditions={'temp': 25})

# --- Test 4: eval crashed ---
fe = Failed_Eval(test=tr1)  # just needs a test object for the name

# --- Corr results: one passing, one failing ---
cr1 = Test_Results(name='vout_vs_temp_corr', module=None)
cr1.test_limits['vout_tempco'] = {'lower_limit': -0.01, 'upper_limit': 0.01}
cr1._evaluate_list('vout_tempco', iter_data=[0.005], conditions={'temp': 25})

cr2 = Test_Results(name='current_vs_temp_corr', module=None)
cr2.test_limits['ilimit_tempco'] = {'lower_limit': -0.05, 'upper_limit': 0.05}
cr2._evaluate_list('ilimit_tempco', iter_data=[0.1], conditions={'temp': 25})  # fails

eval_results = [tr1, tr2, tr3, fe]
corr_results = [cr1, cr2]

subject, body = build_results_summary(eval_results, corr_results)
sys.stdout.reconfigure(encoding='utf-8')
print(f'SUBJECT: {subject}')
print()
print(body)
