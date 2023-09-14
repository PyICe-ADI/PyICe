
from PyICe import lab_core, lab_instruments, lab_utils


m = lab_core.master()

f = m.add_channel_dummy('force')
r = m.add_channel_virtual('readback', read_function=lambda: (f.read()-1)*2)

c = lab_instruments.calibrator(verbose=True)
cal_dict = c.calibrate(f, r, list(range(-5,5)), 'cal_file.pkl')
print(cal_dict)
#corrected = c.add_channel_calibrated_2point('corrected', forcing_channel=f, gain=cal_dict['gain'], offset=cal_dict['offset'])
corrected = c.add_channel_calibrated_2point('corrected', forcing_channel=f, **cal_dict)
corrected.write(3)
print("Wrote: {} Forced: {} Read: {}".format(corrected.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected.read(), r.read())

corrected.write(37)
print("Wrote: {} Forced: {} Read: {}".format(corrected.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected.read(), r.read())

corrected_file = c.add_channel_calibrated_2point('corrected_file', forcing_channel=f, calibration_filename='cal_file.pkl')
corrected_file.write(-5)
print("Wrote: {} Forced: {} Read: {}".format(corrected_file.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected_file.read(), r.read())

f.write(19) #test callback
print("Wrote force: {} Callback cal: {} Read: {}".format(f.read(), corrected_file.read(), r.read()))
assert lab_utils.isclose(corrected_file.read(), r.read())

corrected_file.write(-27)
print("Wrote: {} Forced: {} Read: {}".format(corrected_file.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected_file.read(), r.read())

corrected_spline_dict = c.add_channel_calibrated_spline('corrected_spline_dict', forcing_channel=f, **cal_dict)
corrected_spline_dict.write(-15)
print("Wrote: {} Forced: {} Read: {}".format(corrected_spline_dict.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected_spline_dict.read(), r.read())

corrected_spline_file = c.add_channel_calibrated_spline('corrected_spline_file', forcing_channel=f, calibration_filename='cal_file.pkl')
corrected_spline_file.write(22.3)
print("Wrote: {} Forced: {} Read: {}".format(corrected_spline_file.read(), f.read(), r.read()))
assert lab_utils.isclose(corrected_spline_file.read(), r.read())

f.write(13) #test callback
print("Wrote force: {} Callback cal: {} Read: {}".format(f.read(), corrected_spline_file.read(), r.read()))
assert lab_utils.isclose(corrected_spline_file.read(), r.read())

m.write_html('calibrator.html')
