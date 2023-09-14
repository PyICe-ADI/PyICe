from PyICe import *

OFFSET = 70

def relU(input):
    return 0 if input < OFFSET else (input-OFFSET)*0.2

master = lab_core.master()
mr_slave = master.add_channel_dummy("mr_slave")
mr_slave.write(0)
mr_whip = master.add_channel_virtual("mr_whip", write_function=lambda value: mr_slave.write(relU(value)))
mr_whip.write(0)

servo = virtual_instruments.servo(  fb_channel      = mr_slave,
                                    output_channel  = mr_whip,
                                    minimum         = 0,
                                    maximum         = 125,
                                    abstol          = 0.001,
                                    reltol          = 0.001,
                                    verbose         = True,
                                    abort_on_sat    = False,
                                    max_tries       = 10)
                                    
servo.add_channel_target("mr_servo")
master.add(servo)

servo.check_enpoints()
master.write("mr_servo", 3)
print(master.read_all_channels())

master.write("mr_servo", 6)
print(master.read_all_channels())