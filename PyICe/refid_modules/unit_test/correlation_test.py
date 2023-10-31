import pytest
from PyICe.refid_modules.correlation.parser import STDFParser
from PyICe.refid_modules.correlation.correlation_analyzer import CorrelationAnalyzer

corr_ex = '../correlation/example_stdf/lot2.stdf'
stwe_ex = '../../../../../projects/stowe_eval/correlation/REVID7/2022-01-05/5627908_LT3390_25C_CLASS_PRI_FT_TRIM_LT3390_BOS-EAGLE1_20220105_102154.std_1'
#@pytest.fixture()
#def file_contents(request):
    # return CorrelationAnalyzer('../correlation/example_stdf/lot2.stdf')
    #return CorrelationAnalyzer('../../../../../projects/stowe_eval/correlation/REVID7/2023-04-14/ENG_LT3390-6J_25C_ENG_ENG_FT_TRIM_LT3390_ETS1UOJU4-00334_20230414_162608.std_1')
 #   return CorrelationAnalyzer(request.param[0])
    #with open('file', 'r') as f:
    #   stuff = f.read()
    #return stuff
@pytest.mark.parametrize('filename',[corr_ex, stwe_ex])
def test_ate_data_exists(filename):
    analyzer = CorrelationAnalyzer(filename)
    assert analyzer.all_ate_data

@pytest.mark.parametrize('filename,args',[(corr_ex, {'testname':'Src out I       <> EA_SRC', 'bench_data':[-0.0002], 'units':'A', 'upper_diff':1, 'lower_diff':-1}),
    (stwe_ex, {'testname':'VOUT CH1', 'bench_data':0.9,'units':'V', 'upper_diff':0.1, 'lower_diff':-0.1}),
    (stwe_ex, {'testname':'VOUT CH1', 'bench_data':[0.9],'units':'V', 'upper_diff':0.1, 'lower_diff':-0.1}),
    (stwe_ex, {'testname':'VOUT CH1', 'bench_data':[900],'units':'mV', 'upper_diff':0.1, 'lower_diff':-0.1}),
    (stwe_ex, {'testname':'VOUT CH1', 'bench_data':[0.9],'units':'V', 'percent':10})])
def test_verdict_abs(filename, args):
    analyzer = CorrelationAnalyzer(filename)
    assert analyzer.verdict(**args)

#@pytest.mark.parametrize('filename,args',[(corr_ex, {'testname':'Src out I       <> EA_SRC', 'bench_data':[0.0002], 'units':'A', 'upper_diff':0.0001, 'lower_diff':-0.0001}),
#    (stwe_ex, {'testname':'VOUT CH1', 'bench_data':[0.9],'units':'V', 'upper_diff':0.1, 'lower_diff':-0.1})])
#def test_verdict_pct(file_contents):
#    assert file_contents.verdict('VOUT CH1', [0.9], 'V', percent=3)

