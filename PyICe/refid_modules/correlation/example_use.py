# import the CorrelationAnalyzer and CorrelationUtils from the PyICe correlation folder.
from PyICe.refid_modules.correlation.correlation_analyzer import CorrelationAnalyzer
from PyICe.refid_modules.correlation.correlation_utils import CorrelationUtils

if __name__ == '__main__':

    # Have an csv file that, on one line, has a dut id, the location of the stdf file with test info for the dut, and the part id of the dut.
    # Pass the location of that csv index file into the CorrelationUtils and call "get_stdf_info" with the identifying string of the dut being used.
    # That will result in a dictionary of test info that can be passed into the CorrelationAnalyzer.
    all_part_data = CorrelationUtils('example_stdf/part_index.csv').get_stdf_info("the_second_part")
    test_names = [x for x in all_part_data['TESTS'].keys()]
    analyzer = CorrelationAnalyzer(all_part_data["TESTS"])

    # Normally one would collect data in a test and supply it here. For this example, we have a test selected at random, and we're generating a value that is 4% from it's target. This test uses ohms for units.
    sample_bench_data = all_part_data['TESTS'][test_names[58]]['RESULT'] * 0.96              
    passes1 = analyzer.verdict(testname = test_names[58], bench_data = sample_bench_data, units = 'ohm', percent=5)                                 # Set limit to +-5%
    passes2 = analyzer.verdict(testname = test_names[58], bench_data = sample_bench_data, units = 'ohm', percent=3)                                 # Set limit to +-3%
    passes3 = analyzer.verdict(testname = test_names[58], bench_data = sample_bench_data, units = 'ohm', upper_diff=0.5, lower_diff=-0.5)           # Set limits
    passes4 = analyzer.verdict(testname = test_names[58], bench_data = sample_bench_data, units = 'ohm', upper_diff=0.00001, lower_diff=-0.00001)   # Set limits
    breakpoint()