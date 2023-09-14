from PyICe                      import lab_core, lab_instruments
from PyICe.models.comparator    import comparator

h = comparator(rising_threshold = 3.6, falling_threshold = 3.3, write_overshoot = 0.1)
m = lab_core.master()
i_f = m.add_channel_virtual('input_force', write_function = h.write)
i_f.write(0)
i_s = m.add_channel_virtual_caching('input_sense', read_function=lambda: i_f.read() / 1000.0)
o = m.add_channel_virtual('output', read_function = h.read)

tf = lab_instruments.threshold_finder(comparator_input_force_channel = i_f,
                                    comparator_output_sense_channel = o,
                                    minimum = 3,
                                    maximum = 37,
                                    abstol = .001,
                                    #comparator_input_sense_channel=None,
                                    comparator_input_sense_channel = i_s,
                                    forcing_overshoot = 0.10001,
                                    output_threshold = None,
                                    verbose = True)
                                    
print(tf.find(cautious=True))
#tf.find(cautious=False)
#tf.find_linear()
#tf.find_hybrid(linear_backtrack=None, max_step=0.01)
#tf.find_geometric(decades=None)
#res = tf.test_repeatability(linear_backtrack=None)

tf.reconfigure(comparator_input_force_channel = i_f,
            comparator_output_sense_channel = o,
            comparator_input_sense_channel = None)
print(tf.find())
tf.measure_input(i_s)

h2 = comparator(rising_threshold = 871, falling_threshold = 453)
i_f_int = m.add_channel_virtual('input_force_integer', write_function = h2.write, integer_size=10)
i_f_int.add_format(format_name='dummy', format_function=lambda x: x, unformat_function=lambda x: x)
i_f_int.set_format('dummy')
i_f_int.write(0)
o2 = m.add_channel_virtual('output2', read_function = h2.read)
tf.reconfigure(comparator_input_force_channel = i_f_int,
            comparator_output_sense_channel = o2,
            comparator_input_sense_channel = None,
            forcing_overshoot = 0,
            minimum = 0,
            maximum = 2**10-1,
            abstol = 1,
            )
print(tf.find(cautious=True))
h2.set_thresholds(415, 427)
tf.add_channel_all('threshold', auto_find=True)
m.add(tf)
# m.background_gui()

l = lab_core.logger(m, database="threshold_data.sqlite")
l.new_table(table_name='thresholds',replace_table='copy')
for i in range(10):
    l.log()
