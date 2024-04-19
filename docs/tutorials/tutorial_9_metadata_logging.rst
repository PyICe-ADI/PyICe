========================================
TUTORIAL 9 Logging MetaData to a SQLite File
========================================

Beyond collecting data for a test, it is prudent to collect data regarding how the data is collected, also known as metadata. For example, the serial numbers of the instruments used, the connections between the instruments in setup, the ID of the DUT, the name of person executing the test, etc. This metadata is unchanging throughout the test run, and so it would be redundant to write it to the same table as the test data every time the test data logged. Therefore, making a separate table in the same SQLite file purely for the metadata and logging that once can help keep data organized and avoid redundancies.

To do this, create two instances of channel_master, and have each one assigned to a different logger.

.. code-block:: python

   from PyICe import lab_core
   
   channel_master1 = lab_core.channel_master()
   logger = lab_core.logger(channel_master1)
   logger.new_table(table_name='tutorial_9_table', replace_table=True)
   
   channel_master2 = lab_core.channel_master()
   meta_logger = lab_core.logger(channel_master2)
   meta_logger.new_table(table_name='tutorial_9_table_metadata', replace_table=True)



Create channels to store the metadata, and log it once before the test begins collecting data.

.. code-block:: python

	metadata_channels = {'bench_instruments':['HAMEG', 'CONFIG_XT],
						 'DUT_ID': 7,
						 'test_runner': 'Joe Schmoe']
	for channel_name in metadata_channels:
		meta_master.add_channel_dummy(channel_name)
		meta_master.write(channel_name, metadata_channels[channel_name])
	meta_master.log()

The data collected when the logger logs will have no impact on the meta_logger, and both tables will be stored in the same SQLite file. 

.. code-block:: python

   print("Logging all channels...")
   for measurement in range(10):
       print(f"Logging measurement number: {measurement}")
       logger.log()
   print("\n\nConsider opening data_log.sqlite with DB Browser https://sqlitebrowser.org/ and opening the [Browse Data] tab.")
   
Going forward, be sure to keep these tables together.
