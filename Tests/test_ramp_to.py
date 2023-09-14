from PyICe import lab_core, lab_instruments

def debug(val):
    print("Writing channel to {}".format(val))

m = lab_core.master()
rt = lab_instruments.ramp_to(verbose=True)
m.add(rt)
d = m.add_channel_virtual('d', write_function = debug)
d.write(0)
rb = rt.add_channel_binary('rb', d, 0.001, 20)
rl = rt.add_channel_linear('rl', d, 0.01)
ro = rt.add_channel_overshoot('ro', d, abstol=0.001, estimated_overshoot=11)


#rb.write(10)
#rb.write(-10)
rl.write(-9)
rb.write(100)
ro.write(50)
ro.write(60)
print(m.read_all_channels())