from PyICe import lab_utils, lab_core, lab_instruments

###
# Under-the-hood tracing
###
import logging
logging.basicConfig(level=logging.DEBUG)#, format='%(asctime)s %(levelname)s:%(name)s:%(message)s')

###
# Database Vector expansion
###
db = lab_utils.sqlite_data(database_file='data_log_LTC6363.sqlite')

db.query('SELECT rowid,X,A FROM LTC6363_1_bandwidth_vs_freq00')
ra = db.expand_vector_data(csv_filename='LTC6363_1_bandwidth_vs_freq.csv')
pass


###
# Virtual instrument vector channel reduction
###
m = lab_core.master()
v = lab_instruments.vector_to_scalar_converter()
vector_channel = v._add_channel_dummy_random(channel_name='vector_dummy', vector_length=2000, max=1, min=0)
stdev = v.add_channel(channel_name='scalar_dummy', vector_data_channel=vector_channel, reduction_function=lab_instruments.vector_to_scalar_converter.stdev)

stdev_cb = v.add_channel_callback(channel_name='stdev', vector_data_channel=vector_channel, reduction_function=lab_instruments.vector_to_scalar_converter.stdev)
mean_cb = v.add_channel_callback(channel_name='mean', vector_data_channel=vector_channel, reduction_function=lab_instruments.vector_to_scalar_converter.mean)

m.add(v)