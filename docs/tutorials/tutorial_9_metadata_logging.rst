========================================
TUTORIAL 9 Logging MetaData to a SQLite File
========================================

Beyond collecting data for a test, it is prudent to collect data regarding how the data is collected, which is also known as a type of metadata. For example, the serial numbers of the instruments used, the connections between the instruments in setup, the ID of the DUT, the name of person executing the test, etc. This metadata is unchanging throughout the test run, and so it would be redundant to write it to the same table as the test data every time the test data is logged. Therefore, making a separate table in the same SQLite file purely for the metadata and logging that once can help keep data organized and avoid redundancies.

To do this, after creating the standard logger, create a second instance of a channel master and add the metadata channels to it.

.. code-block:: python

	from PyICe import lab_core

	data_master = lab_core.channel_master()
	logger = lab_core.logger(data_master)
	logger.new_table(table_name='tutorial_9_table', replace_table=True)

	meta_master = lab_core.channel_master()
	metadata_channels = {'bench_instruments':['HAMEG', 'CONFIG_XT'],
						 'DUT_ID': 7,
						 'test_runner': 'Joe Schmoe',
						}
	for channel_name in metadata_channels:
		meta_master.add_channel_dummy(channel_name)


Then make a second logger tied to the newly created channel master, make a table with an appropriate name, and write the metadata values to the channels. Log the metadata logger once.

.. code-block:: python

	meta_logger = lab_core.logger(meta_master)
	meta_logger.new_table(table_name='tutorial_9_metadata', replace_table=True)
	for channel in metadata_channels:
		meta_master.write(channel_name, metadata_channels[channel_name])
	meta_logger.log()

The data collected when the logger logs will have no impact on the meta_logger, and both tables will be stored in the same SQLite file. 

.. code-block:: python

   print("Logging all channels...")
   for measurement in range(10):
       print(f"Logging measurement number: {measurement}")
       logger.log()
   print("\n\nConsider opening data_log.sqlite with DB Browser https://sqlitebrowser.org/ and opening the [Browse Data] tab.")
   
Going forward, be sure to keep these tables together.
