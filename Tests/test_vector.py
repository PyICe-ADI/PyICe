"""Tests for vector."""
from PyICe import lab_core
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.virtual_instruments import vector_to_scalar_converter

###
# Under-the-hood tracing
###
import logging
# , format='%(asctime)s %(levelname)s:%(name)s:%(message)s')
logging.basicConfig(level=logging.DEBUG)

###
# Database Vector expansion
###
db = sqlite_data(database_file='data_log_LTC6363.sqlite')

db.query('SELECT rowid,X,A FROM LTC6363_1_bandwidth_vs_freq00')
ra = db.expand_vector_data(csv_filename='LTC6363_1_bandwidth_vs_freq.csv')


###
# Virtual instrument vector channel reduction
###
m = lab_core.master()
v = vector_to_scalar_converter()
vector_channel = v._add_channel_dummy_random(
    channel_name='vector_dummy', vector_length=2000, max=1, min=0)
stdev = v.add_channel(
    channel_name='scalar_dummy',
    vector_data_channel=vector_channel,
    reduction_function=vector_to_scalar_converter.stdev)

stdev_cb = v.add_channel_callback(
    channel_name='stdev',
    vector_data_channel=vector_channel,
    reduction_function=vector_to_scalar_converter.stdev)
mean_cb = v.add_channel_callback(
    channel_name='mean',
    vector_data_channel=vector_channel,
    reduction_function=vector_to_scalar_converter.mean)

m.add(v)
