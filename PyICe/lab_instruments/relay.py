from ..lab_core import *
import abc
    
    
class relay(instrument):
    @abc.abstractmethod
    def add_channel(self,channel_name, channel_number):
        '''placeholder'''

    @abc.abstractmethod
    def _set_relay(self, channel_number, state):
        '''placeholder'''
    
    @abc.abstractmethod
    def _get_state(self, channel_number):
        '''placeholder'''

    @abc.abstractmethod
    def _all_off(self):
        '''placeholder'''

class ftdi_relay(relay):
    def __init__(self, serial_number=None):
        self.VID = 0x0403                   # USB Vendor ID of FT245R and FT232
        self.PID = 0x6001                   # USB Product ID of FT245R and FT232
        self.PROD_STR = u'FT245R USB FIFO'  # differentiate from FT232 USB UART
        self.serial_number = serial_number

        self.rb = FT245R()

        findargs = {'find_all': True,
                    'idVendor': self.VID,
                    'idProduct': self.PID,
                    'product': self.PROD_STR,
                   }
        if serial_number is not None: findargs['serial_number'] = self.serial_number
        devs = list(usb.core.find(**findargs))
        assert len(devs) == 1, f'Device search returned {len(devs)} results (1 expected). Check serial number for uniqe ID. {[dev.serial_number for dev in devs]}'
        dev = devs[0]
        self.rb.connect(dev)
        super().__init__(f"relay_board {serial_number}")
        self._all_off()
        ## TODO : add exit cleanup method

    def add_channel(self,channel_name, channel_number):
        '''Adds a channel for a relay on the board'''
        assert self.rb.RELAY_MIN <= channel_number and channel_number <= self.rb.RELAY_MAX, f'Channel number must correspond to a relay between {self.rb.RELAY_MIN} and {self.rb.RELAY_MAX}.'
        new_channel = integer_channel(channel_name, size=2, write_function=lambda state, channel_number=channel_number: self._set_relay(channel_number,state))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        new_channel.add_preset('ON', True)
        new_channel.add_preset('OFF', False)
        return self._add_channel(new_channel)

    def _set_relay(self, channel_number, state):
        if state:
            self.rb.switchon(channel_number)
        else:
            self.rb.switchoff(channel_number)
        
    def _get_state(self, channel_number):
        return self.rb.getstatus(channel_number)

    def _all_off(self):
        [self._set_relay(i, False) for i in range(self.rb.RELAY_MIN,self.rb.RELAY_MAX+1)]





################################################################
# External Library
################################################################


'''
# relay_ft245r

*relay_ft245r* is a Python module to control relay boards based on the 
FTDI FT245R chip. A popular example is the Sainsmart USB relay board.

![Sainsmart 4-channel USB relay board](sainsmart_usb_4relay.jpg)

# How to use *relay_ft245r*

Example code:

```python
import relay_ft245r
import sys
import time

rb = relay_ft245r.FT245R()
dev_list = rb.list_dev()

# list of FT245R devices are returned
if len(dev_list) == 0:
    print('No FT245R devices found')
    sys.exit()
    
# Show their serial numbers
for dev in dev_list:
    print(dev.serial_number)

# Pick the first one for simplicity
dev = dev_list[0]
print('Using device with serial number ' + str(dev.serial_number))

# Connect and turn on relay 2 and 4, and turn off
rb.connect(dev)
rb.switchon(2)    
rb.switchon(4)
time.sleep(1.0)
rb.switchoff(2)    
time.sleep(1.0)
rb.switchoff(4)
```

# Installation

There's no need to "install" *relay_ft245r.py*. Just put it in the same
directory as the Python program that will call it.

But it does need PyUSB and, for Linux, a udev rule to be added or 
Windows, the libusb-win32 driver to be installed and configured.

## Installing PyUSB

relay_ft245r uses the PyUSB Python module to control USB devices. To add 
to your base Python installation, do:

```bash
sudo pip install pyusb
```

## Linux: Update udev rules

To control USB devices without having to be the root user, two things 
are required: 1) you must be part of the "plugdev" group, and 2) the 
FTDI device has to be part of the "plugdev" group.

### Adding user to plugdev

Check which groups your user login belongs to:

```bash
groups
```

If this list includes "plugdev", go on to the next step. Othewise, do 
this command except replace <user> with your user name:

```bash
sudo addgroup <user> plugdev
```

### Adding a udev rule

Add a file called */lib/udev/rules.d/60-relay_ft245r.rules* with the 
contents below. This example uses nano editor:

```bash
sudo nano /lib/udev/rules.d/60-relay_ft245r.rules
```

Enter the text below as a single line:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="660", ENV{MODALIAS}="ignore"
```

Unplug **All** FTDI devices from USB and reattach so that this new rule 
is executed for each FTDI device.

## Windows: Add libusb-win32 and configure

On Windows, PyUSB calls into the libusb-win32 driver. 

### Install Zadig

Zadig is the easiest way in Windows to install libusb-win32 and select
it as the driver assigned to the FT245R board. Go to 
http://zadig.akeo.ie/ and download and install Zadig.

* Run the program
* Click on "Options" and then "Show All Devices"
* Back on the main dialog, select "FT245R USB FIFO" in the dropdown
* Confirm that USB ID shows **0403** and **6001**
* In the pick list specify "libusb-win32"
* Click on the Replace Driver button
* Answer any popup dialogs that show up

This replaces WinUSB for libusb-win32 as the driver to control the board. The 
dialog should look like this before you press *Replace Driver*:

![Zadig dialog](images/Zadig_Replace_Driver.png)

# Troubleshooting

## ValueError: The device has no langid

This error happens in Linux when the program does not have permission to 
access the port. (The error is a side effect and is misleading.) Fix the 
udev rule as documented above.

To confirm it is a user permission issue, try using *sudo* in front of 
the command to run as superuser. If it works, then it is a permissions 
issue with the device.

Sometimes, you need to reboot the computer; logging in and out doesn't 
seem to set the new user permissions.

## usb.core.USBError: [[Errno 16]] Resource busy

Cannot take control of the USB device. Many possible causes:

* The device is attached to another driver (for example, if you are 
  running a virtual machine and the device is presently connected to that 
  virtual machine)

## TypeError: unbound method ... must be called with...

Correct:

```python
rb = relay_ft245r.FT245R()
```

Incorrect:

```python
rb = relay_ft245r.FT245R
```

The second one calls out the object template instead of an object instance.

# Origins

The original code for this came from https://github.com/xypron/pyrelayctl
authored by Heinrich Schuchardt.

I made these changes:

1. Cleaner implementation as object oriented code (didn't need to keep 
passing the device handle)

2. Made it compatible with Python on Windows

3. Fixed a race condition. On Windows, PyUSB runs slow and the relays
where not set reliably on some boards. Probably the bit
masking is not reliable (the USB readstatus() may be happening before
the previous USB write happened) so I restructured the code to only
read the relay state once on connect().

This was tested on Linux Mint 18.3 (Debian) and Windows 7 Professional. It 
should work fine on Raspberry Pi (Debian) and Windows 10, etc.

# License

```
# Copyright (c) 2016, Heinrich Schuchardt <xypron.glpk@gmx.de>
# Copyright (c) 2018, Vince Patron <vince@patronweb.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ORIGINAL: https://github.com/xypron/pyrelayctl
#
# CHANGELOG:
#   18/06/12 vpatron
#      Made compatible with Windows. Converted to object style. Excludes FT232
#      boards. See https://github.com/vpatron/relay_ft245r
```

'''

#!/usr/bin/env python
#
# Copyright (c) 2016, Heinrich Schuchardt <xypron.glpk@gmx.de>
# Copyright (c) 2018, Vince Patron <vince@patronweb.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# ORIGINAL: https://github.com/xypron/pyrelayctl
#
# CHANGELOG:
#   18/06/12 vpatron
#      Made compatible with Windows. Converted to object style. Excludes FT232
#      boards. See https://github.com/vpatron/relay_ft245r


"""relay_ft245r
relay_ft245r is a library to control FTDI FT245R based relay boards. This
includes the SainSmart 4-channel 5V USB relay board. The relays can be switched
on and off via USB.

The library depends on PyUSB (https://github.com/walac/pyusb).

On both Linux and Windows, PyUSB can be installed using Python's pip:

    python -m pip install pyusb

----------
FOR LINUX:
----------
In Debian, only members of plugdev can access the USB devices.

1) Add your users to plugdev. Change "username" to your user name.

    sudo adduser username plugdev

2) Add a udev rule to give the FT245R device to group "plugdev".

    sudo nano /lib/udev/rules.d/60-relay_ft245r.rules

Edit the file and add this line:

    SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", GROUP="plugdev", MODE="660", ENV{MODALIAS}="ignore"

Then reload the udev rules with

    udevadm control --reload-rules

PyRelayCtl is licensed under a modified BSD license.
"""

import usb.core
import usb.util
import platform

class FT245R:
    def __init__(self):
        self.VID = 0x0403                   # USB Vendor ID of FT245R and FT232
        self.PID = 0x6001                   # USB Product ID of FT245R and FT232
        self.PROD_STR = u'FT245R USB FIFO'  # differentiate from FT232 USB UART
        self.is_connected = False
        self.dev = None
        self.RELAY_MIN = 1
        self.RELAY_MAX = 8
        self.relay_state = 0                # 8 bits representing 8 relays


    def list_dev(self):
        """
        Returns the list of FT245R devices.
        @return: device list
        """
        ret = []
        for dev in usb.core.find(find_all=True,
                                 idVendor=self.VID,
                                 idProduct=self.PID):

            # Ignore FT232 UART. Has same VID and PID as FT245R.
            if dev.product == self.PROD_STR:
                ret.append(dev)
        return ret


    def disconnect(self):
        """
        Disables output to the device. Attaches the kernel driver if available.
                """
        self.is_connected = False
        if platform.system() != 'Windows':
            # If Linux OS already has control, there's nothing to do
            if self.dev.is_kernel_driver_active(0):
                return

        # Disable bitbang mode
        ret = self.dev.ctrl_transfer(0x40, 0x0b, 0x0000, 0x01, None, 500)
        if ret < 0:
            raise RuntimeError("relayctl: failure to disable bitbang mode")

        if platform.system() != 'Windows':
            try:
                self.dev.attach_kernel_driver(0)
            except:
                print ("relayctl: could not attach kernel driver")


    def connect(self, dev):
        """
        Enables output to the device. Detaches the kernel driver if attached.

        @param dev: device
        """
        # Save the device handler so user does not have to keep passing it
        self.dev = dev

        # Detach kernel driver
        if platform.system() != 'Windows':
            if dev.is_kernel_driver_active(0):
                try:
                    dev.detach_kernel_driver(0)
                except:
                    raise RuntimeError("relayctl: failure to detach kernel driver")

        if not self.is_connected:
            # Set the active configuration. Windows errors if this is not done.
            # But Linux errors if this is done more than once (without closing)
            dev.set_configuration()

            # Enable bitbang mode
            ret = dev.ctrl_transfer(0x40, 0x0b, 0x01ff, 0x01, None, 500)
            if ret < 0:
                raise RuntimeError("relayctl: failure to enable bitbang mode")
            self.is_connected = True
            self.relay_state = self._getstatus_byte()


    def _getstatus_byte(self):
        """
        Gets a byte which represents the status of all 8 relays.

        @return: status
        """

        # Check for errors
        if not self.is_connected:
            raise IOError('Must connect to device first')

        # Read status
        buf = bytes([0x00]);
        buf = self.dev.ctrl_transfer(0xC0, 0x0c, 0x0000, 0x01, buf, 500)
        if len(buf) == 0:
            raise RuntimeError("relayctl: failure to read status")

        return buf[0]


    def getstatus(self, relay_num):
        """
        Returns 1 if relay relay_num is on, 0 if off.

        @return: status
        """

        # Check for errors
        if relay_num < self.RELAY_MIN or relay_num > self.RELAY_MAX:
            raise ValueError(f'Relay number {relay_num} is invalid')
        if not self.is_connected:
            raise IOError('Must connect to device first')

        # Read status
        if self.relay_state & (1 << (relay_num - 1)):
            return 1
        return 0


    def setstate(self):
        """
        Sets all relays to the state in FT245R.relay_state.
        """

        # Check for errors
        if not self.is_connected:
            raise IOError('Must connect to device first')

        # Clear the bit representing relay_num and mask it into the existing
        # relay_state
        buf = [0]
        buf[0] = self.relay_state

        # Write status
        ret = self.dev.write(0x02, buf, 500)
        if ret < 0:
            raise RuntimeError("relayctl: failure to write status")
        return


    def switchoff(self, relay_num):
        """
        Switches relay relay_num off.

        @param relay_num: which relay
        """

        # Check for errors
        if relay_num < self.RELAY_MIN or relay_num > self.RELAY_MAX:
            raise ValueError(f'Relay number {relay_num} is invalid')
        if not self.is_connected:
            raise IOError('Must connect to device first')

        # Clear the bit representing relay_num and mask it into the existing
        # relay_state
        buf = [0]
        buf[0] = self.relay_state & ~(1 << (relay_num - 1))

        # Write status
        ret = self.dev.write(0x02, buf, 500)
        if ret < 0:
            raise RuntimeError("relayctl: failure to write status")

        # Save status
        self.relay_state = buf[0]
        return


    def switchon(self, relay_num):
        """
        Switches relay relay_num on.

        @param relay_num: which relay
        """

        # Check for errors
        if relay_num < self.RELAY_MIN or relay_num > self.RELAY_MAX:
            raise ValueError(f'Relay number {relay_num} is invalid')
        if not self.is_connected:
            raise IOError('Must connect to device first')

        # Set the bit representing relay_num and mask it into the existing
        # relay_state
        buf = [0]
        buf[0] = self.relay_state | (1 << (relay_num - 1))

        # Write status
        ret = self.dev.write(0x02, buf, 500)
        if ret < 0:
            raise RuntimeError("relayctl: failure to write status")

        # Save status
        self.relay_state = buf[0]
        return
















if __name__ == '__main__':
    # ftdi_relay(serial_number='AB0NX7L7')

    import usb.core
    import sys
    import time
    rb = FT245R()

    if len(sys.argv) == 1:
        #no args. Search for device
        dev_list = rb.list_dev()
        # list of FT245R devices are returned
        if len(dev_list) == 0:
            raise Exception('No FT245R devices found')
        # Show their serial numbers
        for dev in dev_list:
            print(dev.serial_number)
        # Pick the first one for simplicity
        dev = dev_list[0]
        print(f'Using device with serial number {dev.serial_number}')
    elif len(sys.argv) == 2:
        ser = sys.argv[1]
        dev_list = rb.list_dev(serial_number=ser)
        if len(dev_list) == 0:
            raise Exception(f'No FT245R device with serial {ser} found')
        # Show their serial numbers
        assert len(dev_list) == 1
        dev = dev_list[0]
    else:
        raise Exception(f'Unexpected command line arguments: {sys.argv[1:]}.')

    # Connect and turn on relay 2 and 4, and turn off
    rb.connect(dev)
    [rb.switchoff(i) for i in range(1,9)]
    for t in range(1):
        for i in range(1,9):
            print(f'Relay {i}')
            for j in range(i):
                rb.switchon(i)
                time.sleep(0.15)
                rb.switchoff(i)
                time.sleep(0.15)
            time.sleep(0.5)
    try:
        while True:
            for i in range(1,9):
                [rb.switchoff(j) for j in range(1,9)]
                rb.switchon(i)
                time.sleep(0.02)
    except KeyboardInterrupt as e:
        [rb.switchoff(i) for i in range(1,9)]
    try:
        while True:
            print('Odd')
            [rb.switchoff(i) for i in range(1,9)]
            [rb.switchon(i) for i in range(1,9,2)]
            time.sleep(.1)
            print('Even')
            [rb.switchoff(i) for i in range(1,9)]
            [rb.switchon(i) for i in range(2,9,2)]
            time.sleep(.1)
    except KeyboardInterrupt as e:
        [rb.switchoff(i) for i in range(1,9)]