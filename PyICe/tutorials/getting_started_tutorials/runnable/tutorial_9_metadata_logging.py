if __name__ == '__main__':
    from PyICe import lab_core

    channel_master1 = lab_core.channel_master()
    logger = lab_core.logger(channel_master1)
    logger.new_table(table_name='tutorial_9_table', replace_table=True)

    channel_master2 = lab_core.channel_master()
    metadata_channels = {'bench_instruments':['HAMEG', 'CONFIG_XT'],
                         'DUT_ID': 7,
                         'test_runner': 'Joe Schmoe',
                         }
    for channel_name in metadata_channels:
        channel_master2.add_channel_dummy(channel_name)
    meta_logger = lab_core.logger(channel_master2)
    meta_logger.new_table(table_name='tutorial_9_table_metadata', replace_table=True)
    for channel_name in metadata_channels:
        meta_logger.write(channel_name, metadata_channels[channel_name])
    meta_logger.log()

    print("Logging all channels...")
    for measurement in range(10):
       print(f"Logging measurement number: {measurement}")
       logger.log()
    print("\n\nConsider opening data_log.sqlite with DB Browser https://sqlitebrowser.org/ and opening the [Browse Data] tab.")
   
