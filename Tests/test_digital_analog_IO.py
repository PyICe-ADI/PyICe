from PyICe import lab_instruments, lab_core
import time, random, pdb


m = lab_core.master()
d = m.add_channel_dummy('domain')
d.write(5)
#d.set_write_delay(1)

d_read = m.add_channel_virtual('domain_read', read_function=lambda: 0.995 * d.read() + random.random() / 100)

rt = lab_instruments.ramp_to(verbose=True)
dr = rt.add_channel_linear('domain_ramp', forcing_channel=d, step_size = 0.1)
m.add(dr)
o = m.add_channel_dummy('output')
o.set_min_write_limit(0)
o.set_max_write_limit(10)
o.set_write_delay(0.01)
daio = lab_instruments.digital_analog_io(domain_channel=d, verbose=True)
# daio = lab_instruments.digital_analog_io(domain_channel=d_read, verbose=True)
# daio = lab_instruments.digital_analog_io()

ch_d = daio.add_channel_digital_output("dig_out", output_channel=o)
daio.add_digital_output_logic_state(ch_d, 2, vo_scale=1, vo_offset=1)
#daio.enable_digital_output_domain_read_callback(ch_d)
ch_th2 = daio.add_channel_digital_output("th", output_channel=o, voh_scale=1.2, voh_offset=0, vol_scale=1, vol_offset=0)
m.add(daio)

print(m['dig_out'].write(0))
print(m.read_all_channels())
print(m['dig_out'].write(1))
print(m.read_all_channels())
print(m['dig_out'].write(2))
print(m.read_all_channels())
print(m['domain'].write(6))
print(m.read_all_channels())
print(m['th'].write(1))
print(m.read_all_channels())
print(m['domain'].write(8))
print(m.read_all_channels())
print(m['dig_out'].write(1))
print(m.read_all_channels())
print(m['domain_ramp'].write(4))
print(m.read_all_channels())



daio.add_channel_digital_input('dig_in', o)
daio.add_channel_digital_input('dig_in_hys', o, hys_enable=True)
print(m['dig_in'].read())
print(m['dig_in_hys'].read())

m.gui()

