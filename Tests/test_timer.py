from PyICe import lab_instruments, lab_core
import time

timer = lab_instruments.timer()
timer.add_channel_total_seconds('total_s')
timer.add_channel_total_minutes('total_m')
timer.add_channel_delta_seconds('delta_s')


def sleep(sleep_time):
    print("Sleeping {}s".format(sleep_time))
    time.sleep(sleep_time)

sleep(2)
print("Unpause")
timer.resume_timer() #resume to start
sleep(2)
print("Pause")
timer.pause_timer()
print("Expect 2: {}".format(timer['total_s'].read()))
print("Expect 2t, 2d: {}".format(timer.read_all_channels()))
sleep(1)
print("Unpause")
timer.resume_timer()
print("Expect 2t, 2d: {}".format(timer.read_all_channels()))
sleep(2)
print("Expect 4t, 2d: {}".format(timer.read_all_channels()))
print("Pause")
timer.pause_timer()
sleep(2)
#print timer.read_all_channels()
print("Unpause")
timer.resume_timer()
sleep(1)
print("Expect 5t, 1d: {}".format(timer.read_all_channels()))
sleep(1)
print("Expect 6t, 1d: {}".format(timer.read_all_channels()))


print("\nIntegrator test")
integrator = lab_instruments.integrator()
integrator.add_channel_total_seconds('int_total_s')
integrator.add_channel_delta_seconds('int_delta_s')
integrator.add_channel_integration_seconds('int_s')
integrator.add_channel_integrate('int_input')

integrator['int_input'].write(1)
print(integrator.read_all_channels())
sleep(1)
integrator['int_input'].write(1)
print(integrator.read_all_channels())
print("Pause")
integrator.pause_timer()
sleep(2)
integrator['int_input'].write(1)
print(integrator.read_all_channels())
print("Unpause")
integrator.resume_timer()
integrator['int_input'].write(1)
print(integrator.read_all_channels())
sleep(1)
integrator['int_input'].write(1)
print(integrator.read_all_channels())


