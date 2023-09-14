from PyICe import lab_core, lab_instruments, lab_utils
import time

m = lab_core.master()

if m.attach():
    #slave stuff
    def dummy_fn():
        print("Yo")
    foo = lab_utils.threaded_writer(verbose=True)
    #foo = lab_utils.threaded_writer()
    foo.add_function(function=dummy_fn, time_interval=20, start=True)
    foo.connect_channel(channel_name='a', time_interval=5, sequence=[11,12,13], start=True)
    b = foo.connect_channel(channel_name='b', time_interval=5, sequence=[1,2,3,4,5,6,7,8,9,10], start=False)
    
    m2 = lab_core.master()
    m2.attach()
    
    b_sq = foo.add_function(lambda: m2.write('b_sq', m2.read('b')**2), time_interval=1)
    time.sleep(2.2)
    b.start()
    time.sleep(10)
    b.stop()
    time.sleep(5)
    foo.stop_all()
    # while True:
        # print m.read_all_channels()
        # time.sleep(1)
else:
    #set up first instance
    m.add_channel_dummy('a').write(0)
    m.add_channel_dummy('b').write(1)
    m.add_channel_dummy('c').write(2)
    m.add_channel_dummy('b_sq')
    m.serve()

