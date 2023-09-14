#test_agilent_n3301.py
#Python test script to test class agilent_n3301 which provides a Python
#interface to a GPIB enabled Agilent N3300 series electronic load.
# John Cook August 2012
#
#This works as of August 13, 2012 with no issues.

import lab as lab
import time as time

#create a new lab bench

lb = lab.lab_bench()

#Create the instrument on the GPIB bus
n3301 = lab.agilent_n3301("GPIB0::3")
 
#add a couple of channels
n3301.add_channel("5V_output", 1)
n3301.add_channel("floating_output", 2)


#write some values to those channels
n3301.write_channel("5V_output", 2)
n3301.write_channel("floating_output", 3)

time.sleep(5)

n3301.write_channel("5V_output", 4)
n3301.write_channel("floating_output", 2)


#read back the setpoints
print(("5V_output setpoint: " , n3301.read_channel("5V_output")))
print(("floating_output setpoint: " , n3301.read_channel("floating_output")))


#read the measured values
print(("5V_output measured load: " , n3301.read_channel_sink("5V_output")))
print(("floating_output measured load: " , n3301.read_channel_sink("floating_output")))

#read everything
print()
print(n3301.read_channels())

exit()
      
