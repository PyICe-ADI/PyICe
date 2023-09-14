
from PyICe import lab_core
import random
import time

m = lab_core.master()
for i in range(100):
    m.add_channel_dummy('channel_{:02d}'.format(i)).set_category('dummy').write(i)

m.add_channel_virtual('rand1', read_function=random.random).set_category('random')
m.add_channel_virtual('rand2', read_function=lambda: random.randint(0,255), integer_size=8).set_category('random')
m.add_channel_virtual('rand3', read_function=lambda: random.randint(0,65535), integer_size=16).set_category('random')
m.add_channel_virtual('rand4', read_function=lambda: random.uniform(-1,1)).set_category('random')
m.add_channel_virtual('rand5', read_function=lambda: random.triangular(-1,1)).set_category('random')
m.add_channel_virtual('rand6', read_function=lambda: random.gauss(mu=0, sigma=1)).set_category('random')
m.add_channel_virtual('rand_sel', read_function=lambda: random.randint(0,99), integer_size=7).set_category('random')

m.add_channel_virtual_caching('ch1_p_ch2', read_function=lambda: m.read('channel_01') + m.read('channel_02')).set_category('caching')
m.add_channel_virtual_caching('ch3_m_ch4', read_function=lambda: m.read('channel_03') - m.read('channel_04')).set_category('caching')
m.add_channel_virtual_caching('rand4_cp', read_function=lambda: m.read('rand4')).set_category('caching')
m.add_channel_virtual_caching('rand5_cp', read_function=lambda: m.read('rand5')).set_category('caching')
m.add_channel_virtual_caching('rand6_cp', read_function=lambda: m.read('rand6')).set_category('caching')
m.add_channel_virtual_caching('rand6_cp_cp', read_function=lambda: m.read('rand6_cp')).set_category('double_caching')

m.background_gui()
for i in range(1000):
    data = m.read_all_channels()
    assert data['rand4'] == data['rand4_cp']
    assert data['rand5'] == data['rand5_cp']
    assert data['rand6'] == data['rand6_cp']
    assert data['rand6'] == data['rand6_cp_cp']
    m['channel_{:02d}'.format(data['rand_sel'])].write(data['rand4'])
    time.sleep(0.02)
print(data)