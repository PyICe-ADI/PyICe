#test_hmp4040_serial.py
#Simple test program for testing the Hameg 4040 lab supply software
#John Cook August 2012
#
#This script tests the python classes "hameg_4040_serial" and
#"hameg_4040_gpib" defined in file "lab.py".
#The hameg_4040 is a four output lab supply with an exchangable module for
#either a USB + RS232 or GPIB interface.
#
#To test either usb/virtual COM port or GPIB interface, simply comment out
#the appropiate class constructor.  The rest of the interface is identical
#in either class.

#This test works well as of Aug 10, 2012.  There is a rare bug that I think
#is in the underlying VISA interface code.  On some occasions that are not
#repeatable, the last command sent (which happens to be channel 4) looses
#some of its information.  The symptom is that when setting all four channels
#at the same time, the end of the command to channel 4 is lost somehow or
#the command to channel 4 is lost entirely.  So: sometimes the current limit
#to channel 4 is not set or sometimes channel 4 is not turned OFF by the
#destructor at the exit() of the program.

import lab as lab
import time as time


#create a new lab bench
lb = lab.lab_bench()

#Create the instrument on virtual com port "COM5"
#hmp4040 = lab.hameg_4040_serial("COM5")

#Create the instrument on the GPIB bus.
hmp4040 = lab.hameg_4040_gpib("GPIB0::30")

#add several output channels by name
#first param is name of channel, 2nd is instrument output number
hmp4040.add_channel("vout1",1)
hmp4040.add_channel("vout2",2)
hmp4040.add_channel("vout3",3)
hmp4040.add_channel("vout4",4)

vout1_setting = 1
vout2_setting = 2
vout3_setting = 3
vout4_setting = 4

#Set each output, voltage setting only.
hmp4040.write_channel("vout1", vout1_setting)
hmp4040.write_channel("vout2", vout2_setting)
hmp4040.write_channel("vout3", vout3_setting)
hmp4040.write_channel("vout4", vout4_setting)

time.sleep(5)

vout1_setting = 2
vout2_setting = 3
vout3_setting = 4
vout4_setting = 5

ilimit1_setting = 3
ilimit2_setting = 4
ilimit3_setting = 5
ilimit4_setting = 6

#Set each output, voltage and current limit settings.
hmp4040.write_channel("vout1", vout1_setting, ilimit1_setting)
hmp4040.write_channel("vout2", vout2_setting, ilimit2_setting)
hmp4040.write_channel("vout3", vout3_setting, ilimit3_setting)
hmp4040.write_channel("vout4", vout4_setting, ilimit4_setting)

time.sleep(5)

#exit()

#Read the voltage setting for each output, should be the same as what
#was set above
vout1_reading = hmp4040.read_channel("vout1")
vout2_reading = hmp4040.read_channel("vout2")
vout3_reading = hmp4040.read_channel("vout3")
vout4_reading = hmp4040.read_channel("vout4")


print(("vout1 set: ", vout1_setting, " vout1 reading: ", vout1_reading))
print(("vout2 set: ", vout2_setting, " vout2 reading: ", vout2_reading))
print(("vout3 set: ", vout3_setting, " vout3 reading: ", vout3_reading))
print(("vout4 set: ", vout4_setting, " vout4 reading: ", vout4_reading))

#exit()

#Read back everything and display it all
all_settings = hmp4040.read_channels()

print(all_settings)

exit()

