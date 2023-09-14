from PyICe import lab_core, lab_instruments
import random

def debug(val):
    pass
    #print "Writing channel to {}".format(val)

m = lab_core.master()
ic = lab_core.integer_channel(name='format_tester', size=8, write_function=debug)
ic.add_preset(preset_name='random_value', preset_value=223)
ic.add_format(format_name='x100', format_function=lambda x: x*100, unformat_function = lambda x: x * 0.01, signed=False, units='')
ic.set_format('hex')
ic.write('0x12')
ic.set_category('format')
m.add(ic)

ic2 = lab_core.integer_channel(name='one_bit', size=1, write_function=debug)
ic2.set_category('bits')
m.add(ic2)

pst = lab_core.integer_channel(name='preset_tester', size=8, write_function=debug)
pst.set_category('preset')
for i in range(2**8):
    pst.add_preset('{:03d}'.format(i), i)
m.add(pst)


ic3 = lab_core.integer_channel(name='another_bit', size=1, read_function=lambda: 1 if random.random() < 0.0001 else 0)
ic3.set_category('bits')
m.add(ic3)

m.add_channel_delta_timer('read_time')

print(m.get_all_channels_set(categories=['bits']) | m.get_all_channels_set(categories=['format']) - m.get_all_channels_set(categories=['preset']))

print(m.read_all_channels(categories=['bits', 'format']))

m.gui()