from ..lab_core import *

class bk8500(instrument):
    '''
    The below license only applies to most of the code in the bk8500 instrument:

    Provides the interface to a 26 byte instrument along with utility
    functions.  This is based on provided drivers, minor style changes
    were made and lab.py fucntions were added.  The original license and
    documentation are included below.

    Open Source Initiative OSI - The MIT License:Licensing
    Tue, 2006-10-31 04:56 - nelson

    The MIT License

    Copyright (c) 2009 BK Precision

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.


    This python module provides a functional interface to a B&K DC load
    through the DCLoad object.  This object can also be used as a COM
    server by running this module as a script to register it.  All the
    DCLoad object methods return strings.  All units into and out of the
    DCLoad object's methods are in SI units.

    See the documentation file that came with this script.

    $RCSfile: dcload.py $
    $Revision: 1.0 $
    $Date: 2008/05/17 15:57:15 $
    $Author:  Don Peterson $

    '''
    def __init__(self, interface_raw_serial, address=0, remote_sense=False):
        self._base_name = 'bk8500'
        instrument.__init__(self,f"BK8500 @ {interface_raw_serial}")
        self.add_interface_raw_serial(interface_raw_serial,timeout=1)
        self.sp = interface_raw_serial
        self.address = address
        self._set_constants()
        self.SetRemoteControl()
        self.SetRemoteSense(remote_sense)
        self.mode = 'Off'
        self.nl = '\n' #debug output?
    def _set_constants(self):
        #most of this is from the manufacturer's class
        self.debug = 0  # Set to 1 to see dumps of commands and responses
        self.length_packet = 26  # Number of bytes in a packet
        self.convert_current = 1e4  # Convert current in A to 0.1 mA
        self.convert_voltage = 1e3  # Convert voltage in V to mV
        self.convert_power   = 1e3  # Convert power in W to mW
        self.convert_resistance = 1e3  # Convert resistance in ohm to mohm
        self.to_ms = 1000           # Converts seconds to ms
        self.retries = 5
        # Number of settings storage registers
        self.lowest_register  = 1
        self.highest_register = 25
        # Values for setting modes of CC, CV, CW, or CR
        self.modes = {"cc":0, "cv":1, "cw":2, "cr":3}
        self.out = sys.stdout.write
    def add_channel(self,channel_name,add_extended_channels=True):
        '''Sortcut function adds CC force channel.
        if add_extended_channels, additionally add _isense,_vsense,_psense,_mode readback channels
        Add CV,CW,CR,remote_sense channels separately if you need them.'''
        ch = self.add_channel_current(channel_name)
        ch.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        if add_extended_channels:
            self.add_channel_isense(channel_name + '_isense')
            self.add_channel_vsense(channel_name + '_vsense')
            self.add_channel_psense(channel_name + '_psense')
            self.add_channel_mode(channel_name + '_mode')
        return ch
    def add_channel_current(self,channel_name):
        '''add single CC forcing channel and force zero current'''
        new_channel = channel(channel_name,write_function=self._SetCCCurrent)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_current.__doc__)
        self._add_channel(new_channel)
        new_channel.set_write_delay(0.4)
        new_channel.set_write_resolution(decimal_digits=3) #1mA
        new_channel.write(0)
        return new_channel
    def add_channel_isense(self,channel_name):
        '''add single current readback channel'''
        new_channel = channel(channel_name,read_function=lambda: self._read_isense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_isense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_vsense(self,channel_name):
        '''add single voltage readback channel'''
        new_channel = channel(channel_name,read_function=lambda: self._read_vsense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_vsense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_psense(self,channel_name):
        '''read back computed power dissipated in load'''
        new_channel = channel(channel_name,read_function=lambda: self._read_psense(channel_name))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_psense.__doc__)
        return self._add_channel(new_channel)
    def add_channel_mode(self, channel_name):
        '''read back operating mode (Off, Constant Current, Constant Voltage, Constant Power, Constant Resistance)'''
        new_channel = channel(channel_name,read_function=lambda: self.mode)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_mode.__doc__)
        return self._add_channel(new_channel)
    def _read_vsense(self,channel_name):
        '''Return measured voltage float.'''
        return self.GetInputValues()['voltage']
    def _read_isense(self,channel_name):
        '''Return measured current float.'''
        return self.GetInputValues()['current']
    def _read_psense(self,channel_name):
        '''Return measured power float.'''
        return self.GetInputValues()['power']
    def add_channel_remote_sense(self,channel_name):
        '''Enable/disable remote voltage sense through rear panel connectors'''
        new_channel = integer_channel(channel_name, size=1, write_function=self.SetRemoteSense)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_remote_sense.__doc__)
        new_channel.write(True if self.GetRemoteSense() else False)
        return self._add_channel(new_channel)
    def add_channel_voltage(self,channel_name):
        '''add single CV forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCVVoltage)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_voltage.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mV
        return self._add_channel(new_channel)
    def add_channel_power(self,channel_name):
        '''add single CW forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCWPower)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_power.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mW
        return self._add_channel(new_channel)
    def add_channel_resistance(self,channel_name):
        '''add single CR forcing channel'''
        new_channel = channel(channel_name,write_function=self._SetCRResistance)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_resistance.__doc__)
        new_channel.set_write_resolution(decimal_digits=3) #1mOhm
        return self._add_channel(new_channel)
    def add_channel_battery_discharge(self, channel_name):
        '''add battery discharge mode enable forcing channel
        requires current and minimum battery voltage channels to be configured before enabling mode.
        Note that instrument does not respond to commands during discharge test.
        _en channel must be set false before instrument responds normally.'''
        min_bat_channel = channel(f'{channel_name}_min_v',write_function=self.SetBatteryTestVoltage)
        min_bat_channel.set_description(self.get_name() + ': Battery discharge termination threshold. Muse be written before discharge cycle begins.')
        min_bat_channel._set_value(self.GetBatteryTestVoltage())
        self._add_channel(min_bat_channel)
        discharge_in_progress_channel = integer_channel(f'{channel_name}_in_progress',size=1,read_function=self._battery_discharge_in_progress)
        discharge_in_progress_channel.set_description(self.get_name() + ': Battery discharge in-progress status readback.')
        self._add_channel(discharge_in_progress_channel)
        enable_channel = integer_channel(f'{channel_name}_en',size=1,write_function=self._enable_battery_discharge)
        enable_channel.set_description(self.get_name() + ': Battery discharge cycle enable command. Must write current and _min_v threshold channels before beginning discharge cycle. _min_v and current channels cannot be changed during cycle. When _in_progress channel indicates that cycle has finished, write _en channel back to False to regain normal control of instrument.')
        enable_channel.write(False)
        # enable_channel._set_value(GetFunction() == 'battery') #always disable on startup?
        return self._add_channel(enable_channel)
    def _battery_discharge_in_progress(self):
        return self.GetFunction() == 'battery' and self.GetDemandState() != 0
    def _enable_battery_discharge(self, enable):
        if enable:
            current = self.GetCCCurrent()
            min_v = self.GetBatteryTestVoltage()
            print(f"Discharge current set to {current}A")
            print(f"Discharge threshold set to {min_v}V")
            self.SetFunction('battery')
            #there's no indication that this is finished.
            #The front panel changes from 'CC' to 'OFF', but mode still returns 'CC'
            #Consider add demand_state register?
        else:
            self.SetFunction('fixed')
    def _SetCCCurrent(self, current):
        self.SetMode("cc")
        self.mode = 'Constant Current'
        if current == 0:
            self.TurnLoadOff() # Don't trust setting of 0 to not drop out load.
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
            self.TurnLoadOn() # Because it could be off
        self.SetCCCurrent(current)
    def _SetCVVoltage(self, voltage):
        self.SetMode("cv")
        self.mode = 'Constant Voltage'
        if voltage is None:
            self.TurnLoadOff()
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
            self.TurnLoadOn() # Because it could be off
        self.SetCVVoltage(voltage)
    def _SetCWPower(self, power):
        self.SetMode("cw")
        self.mode = 'Constant Power'
        if power == 0:
            self.TurnLoadOff()
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
            self.TurnLoadOn() # Because it could be off
        self.SetCWPower(power)
    def _SetCRResistance(self, resistance):
        self.SetMode("cr")
        self.mode = 'Constant Resistance'
        if resistance is None:
            self.TurnLoadOff()
        else:
            self.SetRemoteControl() #just in case somebody pushed front panel "Local" button
            self.TurnLoadOn() # Because it could be off
        self.SetCRResistance(resistance)

    # below is mostly code from manufacturer
    def DumpCommand(self, bytestr):
        '''Print out the contents of a 26 byte command.  Example:
            aa .. 20 01 ..   .. .. .. .. ..
            .. .. .. .. ..   .. .. .. .. ..
            .. .. .. .. ..   cb
        '''
        assert isinstance(bytestr, (bytes, bytearray))
        assert(len(bytestr) == self.length_packet)
        header = " "*3
        self.out(header)
        for i in range(self.length_packet):
            if i % 10 == 0 and i != 0:
                self.out(self.nl + header)
            if i % 5 == 0:
                self.out(" ")
            s = "%02x" % bytestr[i]
            if s == "00":
                # Use the decimal point character if you see an
                # unattractive printout on your machine.
                #s = "."*2
                # The following alternate character looks nicer
                # in a console window on Windows.
                s = chr(250)*2
            self.out(s)
        self.out(self.nl)
    def CommandProperlyFormed(self, cmd):
        '''Return 1 if a command is properly formed; otherwise, return 0.
        '''
        assert isinstance(cmd, (bytes, bytearray))
        commands = (
            0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29,
            0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33,
            0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D,
            0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47,
            0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51,
            0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B,
            0x5C, 0x5D, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65,
            0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x12
        )
        # Must be proper length
        if len(cmd) != self.length_packet:
            self.out("Command length = " + str(len(cmd)) + "-- should be " + \
                str(self.length_packet) + self.nl)
            return 0
        # First character must be 0xaa
        if cmd[0] != 0xaa:
            self.out("First byte should be 0xaa" + self.nl)
            return 0
        # Second character (address) must not be 0xff
        if cmd[1] == 0xff:
            self.out("Second byte cannot be 0xff" + self.nl)
            return 0
        # Third character must be valid command
        byte3 = "%02X" % cmd[2]
        if cmd[2] not in commands:
            self.out("Third byte not a valid command:  %s\n" % byte3)
            return 0
        # Calculate checksum and validate it
        checksum = self.CalculateChecksum(cmd)
        if checksum != cmd[-1]:
            self.out("Incorrect checksum" + self.nl)
            return 0
        return 1
    def CalculateChecksum(self, cmd):
        '''Return the sum of the bytes in cmd modulo 256.
        '''
        assert isinstance(cmd, bytes)
        assert ((len(cmd) == self.length_packet - 1) or (len(cmd) == self.length_packet))
        checksum = 0
        for i in range(self.length_packet - 1):
            checksum += cmd[i]
        checksum %= 256
        return checksum
    def StartCommand(self, byte):
        assert byte >= 0 and byte <= 255
        return bytes((0xaa, self.address, byte))
    def SendCommand(self, command):
        '''Sends the command to the serial stream and returns the 26 byte
        response.
        '''
        assert isinstance(command, (bytes, bytearray))
        assert(len(command) == self.length_packet)
        for attempt in range(self.retries):
            self.sp.write(command.decode("latin-1"))
            response = self.sp.read(self.length_packet)
            if len(response) == self.length_packet:
                success = True
                break
            else:
                success = False
                self.sp.read(self.sp.inWaiting())
        if not success:
            print("BK8500 bombed because these don't match:")
            print("command: ", end=' ')
            for byte in command:
                print(f'0x{byte:02x}', end=' ')
            print("\nresponse: ", end=' ')
            for byte in response:
                print(f'0x{byte:02x}', end=' ')
            print()
            print()
            print()
        assert(len(response) == self.length_packet)
        # return response
        return response.encode("latin-1")   #This is needed because the pyice serial driver stringifies everything.
    def ResponseStatus(self, response):
        '''Return a message string about what the response meant.  The
        empty string means the response was OK.
        '''
        assert isinstance(response, (bytes, bytearray))
        responses = {
            0x90 : "Wrong checksum",
            0xA0 : "Incorrect parameter value",
            0xB0 : "Command cannot be carried out",
            0xC0 : "Invalid command",
            0x80 : "",
        }
        assert(len(response) == self.length_packet)
        assert(response[2] == 0x12)
        return responses[response[3]]
    def CodeInteger(self, value, num_bytes=4):
        '''Construct a little endian string for the indicated value.  Two
        and 4 byte integers are the only ones allowed.
        '''
        assert(num_bytes == 1 or num_bytes == 2 or num_bytes == 4)
        value = int(value)  # Make sure it's an integer
        s  = bytes((value & 0xff,))
        if num_bytes >= 2:
            s += bytes(((value & (0xff << 8)) >> 8,))
            if num_bytes == 4:
                s += bytes(((value & (0xff << 16)) >> 16, (value & (0xff << 24)) >> 24))
                assert(len(s) == 4)
        return s
    def DecodeInteger(self, bytestr):
        '''Construct an integer from the little endian string. 1, 2, and 4 byte
        strings are the only ones allowed.
        '''
        assert isinstance(bytestr, (bytes, bytearray))
        assert(len(bytestr) == 1 or len(bytestr) == 2 or len(bytestr) == 4)
        n  = bytestr[0]
        if len(bytestr) >= 2:
            n += bytestr[1] << 8
            if len(bytestr) == 4:
                n += bytestr[2] << 16
                n += bytestr[3] << 24
        return n
    def GetReserved(self, num_used):
        '''Construct a string of nul characters of such length to pad a
        command to one less than the packet size (leaves room for the
        checksum byte.
        '''
        num = self.length_packet - num_used - 1
        assert(num > 0)
        return chr(0)*num
    def PrintCommandAndResponse(self, cmd, response, cmd_name):
        '''Print the command and its response if debugging is on.
        '''
        assert(cmd_name)
        if self.debug:
            self.out(cmd_name + " command:" + self.nl)
            self.DumpCommand(cmd)
            self.out(cmd_name + " response:" + self.nl)
            self.DumpCommand(response)
    def GetCommand(self, command, value, num_bytes=4):
        '''Construct the command with an integer value of 0, 1, 2, or
        4 bytes.
        '''
        cmd = self.StartCommand(command)
        if num_bytes > 0:
            r = num_bytes + 3
            cmd += self.CodeInteger(value)[:num_bytes] + self.Reserved(r)
        else:
            cmd += self.Reserved(0)
        cmd += bytes((self.CalculateChecksum(cmd),))
        assert(self.CommandProperlyFormed(cmd))
        return cmd
    def GetData(self, data, num_bytes=4):
        '''Extract the little endian integer from the data and return it.
        '''
        assert(len(data) == self.length_packet)
        if num_bytes == 1:
            return ord(data[3])
        elif num_bytes == 2:
            return self.DecodeInteger(data[3:5])
        elif num_bytes == 4:
            return self.DecodeInteger(data[3:7])
        else:
            raise Exception("Bad number of bytes:  %d" % num_bytes)
    def Reserved(self, num_used):
        assert(num_used >= 3 and num_used < self.length_packet - 1)
        return b'\x00'*(self.length_packet - num_used - 1)
    def SendIntegerToLoad(self, byte, value, msg, num_bytes=4):
        '''Send the indicated command along with value encoded as an integer
        of the specified size.  Return the instrument's response status.
        '''
        cmd = self.GetCommand(byte, value, num_bytes)
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, msg)
        return self.ResponseStatus(response)
    def GetIntegerFromLoad(self, cmd_byte, msg, num_bytes=4):
        '''Construct a command from the byte in cmd_byte, send it, get
        the response, then decode the response into an integer with the
        number of bytes in num_bytes.  msg is the debugging string for
        the printout.  Return the integer.
        '''
        assert(num_bytes == 1 or num_bytes == 2 or num_bytes == 4)
        cmd = self.StartCommand(cmd_byte)
        cmd += self.Reserved(3)
        cmd += bytes((self.CalculateChecksum(cmd),))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, msg)
        return self.DecodeInteger(response[3:3 + num_bytes])
    def TurnLoadOn(self):
        "Turns the load on"
        msg = "Turn load on"
        on = 1
        return self.SendIntegerToLoad(0x21, on, msg, num_bytes=1)
    def TurnLoadOff(self):
        "Turns the load off"
        msg = "Turn load off"
        off = 0
        return self.SendIntegerToLoad(0x21, off, msg, num_bytes=1)
    def SetRemoteControl(self):
        "Sets the load to remote control"
        msg = "Set remote control"
        remote = 1
        return self.SendIntegerToLoad(0x20, remote, msg, num_bytes=1)
    def SetLocalControl(self):
        "Sets the load to local control"
        msg = "Set local control"
        local = 0
        return self.SendIntegerToLoad(0x20, local, msg, num_bytes=1)
    def SetMaxCurrent(self, current):
        "Sets the maximum current the load will sink"
        msg = "Set max current"
        return self.SendIntegerToLoad(0x24, current*self.convert_current, msg, num_bytes=4)
    def GetMaxCurrent(self):
        "Returns the maximum current the load will sink"
        msg = "Set max current"
        return self.GetIntegerFromLoad(0x25, msg, num_bytes=4)/float(self.convert_current)
    def SetMaxVoltage(self, voltage):
        "Sets the maximum voltage the load will allow"
        msg = "Set max voltage"
        return self.SendIntegerToLoad(0x22, voltage*self.convert_voltage, msg, num_bytes=4)
    def GetMaxVoltage(self):
        "Gets the maximum voltage the load will allow"
        msg = "Get max voltage"
        return self.GetIntegerFromLoad(0x23, msg, num_bytes=4)/float(self.convert_voltage)
    def SetMaxPower(self, power):
        "Sets the maximum power the load will allow"
        msg = "Set max power"
        return self.SendIntegerToLoad(0x26, power*self.convert_power, msg, num_bytes=4)
    def GetMaxPower(self):
        "Gets the maximum power the load will allow"
        msg = "Get max power"
        return self.GetIntegerFromLoad(0x27, msg, num_bytes=4)/float(self.convert_power)
    def SetMode(self, mode):
        "Sets the mode (constant current, constant voltage, etc."
        if mode.lower() not in self.modes:
            raise Exception("Unknown mode")
        msg = "Set mode"
        return self.SendIntegerToLoad(0x28, self.modes[mode.lower()], msg, num_bytes=1)
    def GetMode(self):
        "Gets the mode (constant current, constant voltage, etc."
        msg = "Get mode"
        mode = self.GetIntegerFromLoad(0x29, msg, num_bytes=1)
        modes_inv = {0:"cc", 1:"cv", 2:"cw", 3:"cr"}
        return modes_inv[mode]
    def SetCCCurrent(self, current):
        "Sets the constant current mode's current level"
        msg = "Set CC current"
        return self.SendIntegerToLoad(0x2A, current*self.convert_current, msg, num_bytes=4)
    def GetCCCurrent(self):
        "Gets the constant current mode's current level"
        msg = "Get CC current"
        return self.GetIntegerFromLoad(0x2B, msg, num_bytes=4)/float(self.convert_current)
    def SetCVVoltage(self, voltage):
        "Sets the constant voltage mode's voltage level"
        msg = "Set CV voltage"
        return self.SendIntegerToLoad(0x2C, voltage*self.convert_voltage, msg, num_bytes=4)
    def GetCVVoltage(self):
        "Gets the constant voltage mode's voltage level"
        msg = "Get CV voltage"
        return self.GetIntegerFromLoad(0x2D, msg, num_bytes=4)/float(self.convert_voltage)
    def SetCWPower(self, power):
        "Sets the constant power mode's power level"
        msg = "Set CW power"
        return self.SendIntegerToLoad(0x2E, power*self.convert_power, msg, num_bytes=4)
    def GetCWPower(self):
        "Gets the constant power mode's power level"
        msg = "Get CW power"
        return self.GetIntegerFromLoad(0x2F, msg, num_bytes=4)/float(self.convert_power)
    def SetCRResistance(self, resistance):
        "Sets the constant resistance mode's resistance level"
        msg = "Set CR resistance"
        return self.SendIntegerToLoad(0x30, resistance*self.convert_resistance, msg, num_bytes=4)
    def GetCRResistance(self):
        "Gets the constant resistance mode's resistance level"
        msg = "Get CR resistance"
        return self.GetIntegerFromLoad(0x31, msg, num_bytes=4)/float(self.convert_resistance)
    def SetTransient(self, mode, A, A_time_s, B, B_time_s, operation="continuous"):
        '''Sets up the transient operation mode.  mode is one of
        "CC", "CV", "CW", or "CR".
        '''
        if mode.lower() not in self.modes:
            raise Exception("Unknown mode")
        opcodes = {"cc":0x32, "cv":0x34, "cw":0x36, "cr":0x38}
        if mode.lower() == "cc":
            const = self.convert_current
        elif mode.lower() == "cv":
            const = self.convert_voltage
        elif mode.lower() == "cw":
            const = self.convert_power
        else:
            const = self.convert_resistance
        cmd = self.StartCommand(opcodes[mode.lower()])
        cmd += self.CodeInteger(A*const, num_bytes=4)
        cmd += self.CodeInteger(A_time_s*self.to_ms, num_bytes=2)
        cmd += self.CodeInteger(B*const, num_bytes=4)
        cmd += self.CodeInteger(B_time_s*self.to_ms, num_bytes=2)
        transient_operations = {"continuous":0, "pulse":1, "toggled":2}
        cmd += self.CodeInteger(transient_operations[operation], num_bytes=1)
        cmd += self.Reserved(16)
        cmd += chr(self.CalculateChecksum(cmd))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Set %s transient" % mode)
        return self.ResponseStatus(response)
    def GetTransient(self, mode):
        "Gets the transient mode settings"
        assert isinstance(mode, str)
        if mode.lower() not in self.modes:
            raise Exception("Unknown mode")
        opcodes = {"cc":0x33, "cv":0x35, "cw":0x37, "cr":0x39}
        cmd = self.StartCommand(opcodes[mode.lower()])
        cmd += self.Reserved(3)
        cmd += chr(self.CalculateChecksum(cmd))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Get %s transient" % mode)
        A = self.DecodeInteger(response[3:7])
        A_timer_ms = self.DecodeInteger(response[7:9])
        B = self.DecodeInteger(response[9:13])
        B_timer_ms = self.DecodeInteger(response[13:15])
        operation = self.DecodeInteger(response[15])
        time_const = 1e3
        transient_operations_inv = {0:"continuous", 1:"pulse", 2:"toggled"}
        if mode.lower() == "cc":
            return str((A/float(self.convert_current), A_timer_ms/float(time_const),
                    B/float(self.convert_current), B_timer_ms/float(time_const),
                    transient_operations_inv[operation]))
        elif mode.lower() == "cv":
            return str((A/float(self.convert_voltage), A_timer_ms/float(time_const),
                    B/float(self.convert_voltage), B_timer_ms/float(time_const),
                    transient_operations_inv[operation]))
        elif mode.lower() == "cw":
            return str((A/float(self.convert_power), A_timer_ms/float(time_const),
                    B/float(self.convert_power), B_timer_ms/float(time_const),
                    transient_operations_inv[operation]))
        else:
            return str((A/float(self.convert_resistance), A_timer_ms/float(time_const),
                    B/float(self.convert_resistance), B_timer_ms/float(time_const),
                    transient_operations_inv[operation]))
    def SetBatteryTestVoltage(self, min_voltage):
        "Sets the battery test voltage"
        msg = "Set battery test voltage"
        return self.SendIntegerToLoad(0x4E, min_voltage*self.convert_voltage, msg, num_bytes=4)
    def GetBatteryTestVoltage(self):
        "Gets the battery test voltage"
        msg = "Get battery test voltage"
        return self.GetIntegerFromLoad(0x4F, msg, num_bytes=4)/float(self.convert_voltage)
    def SetLoadOnTimer(self, time_in_s):
        "Sets the time in seconds that the load will be on"
        msg = "Set load on timer"
        return self.SendIntegerToLoad(0x50, time_in_s, msg, num_bytes=2)
    def GetLoadOnTimer(self):
        "Gets the time in seconds that the load will be on"
        msg = "Get load on timer"
        return self.GetIntegerFromLoad(0x51, msg, num_bytes=2)
    def SetLoadOnTimerState(self, enabled=0):
        "Enables or disables the load on timer state"
        msg = "Set load on timer state"
        return self.SendIntegerToLoad(0x50, enabled, msg, num_bytes=1)
    def GetLoadOnTimerState(self):
        "Gets the load on timer state"
        msg = "Get load on timer"
        state = self.GetIntegerFromLoad(0x53, msg, num_bytes=1)
        if state == 0:
            return "disabled"
        else:
            return "enabled"
    def SetCommunicationAddress(self, address=0):
        '''Sets the communication address.  Note:  this feature is
        not currently supported.  The communication address should always
        be set to 0.
        '''
        msg = "Set communication address"
        return self.SendIntegerToLoad(0x54, address, msg, num_bytes=1)
    def EnableLocalControl(self):
        "Enable local control (i.e., key presses work) of the load"
        msg = "Enable local control"
        enabled = 1
        return self.SendIntegerToLoad(0x55, enabled, msg, num_bytes=1)
    def DisableLocalControl(self):
        "Disable local control of the load"
        msg = "Disable local control"
        disabled = 0
        return self.SendIntegerToLoad(0x55, disabled, msg, num_bytes=1)
    def SetRemoteSense(self, enabled=0):
        "Enable or disable remote sensing"
        msg = "Set remote sense"
        return self.SendIntegerToLoad(0x56, enabled, msg, num_bytes=1)
    def GetRemoteSense(self):
        "Get the state of remote sensing"
        msg = "Get remote sense"
        return self.GetIntegerFromLoad(0x57, msg, num_bytes=1)
    def SetTriggerSource(self, source="immediate"):
        '''Set how the instrument will be triggered.
        "immediate" means triggered from the front panel.
        "external" means triggered by a TTL signal on the rear panel.
        "bus" means a software trigger (see TriggerLoad()).
        '''
        trigger = {"immediate":0, "external":1, "bus":2}
        if source not in trigger:
            raise Exception("Trigger type %s not recognized" % source)
        msg = "Set trigger type"
        return self.SendIntegerToLoad(0x54, trigger[source], msg, num_bytes=1)
    def GetTriggerSource(self):
        "Get how the instrument will be triggered"
        msg = "Get trigger source"
        t = self.GetIntegerFromLoad(0x59, msg, num_bytes=1)
        trigger_inv = {0:"immediate", 1:"external", 2:"bus"}
        return trigger_inv[t]
    def TriggerLoad(self):
        '''Provide a software trigger.  This is only of use when the trigger
        mode is set to "bus".
        '''
        cmd = self.StartCommand(0x5A)
        cmd += self.Reserved(3)
        cmd += chr(self.CalculateChecksum(cmd))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Trigger load (trigger = bus)")
        return self.ResponseStatus(response)
    def SaveSettings(self, register=0):
        "Save instrument settings to a register"
        assert(self.lowest_register <= register <= self.highest_register)
        msg = "Save to register %d" % register
        return self.SendIntegerToLoad(0x5B, register, msg, num_bytes=1)
    def RecallSettings(self, register=0):
        "Restore instrument settings from a register"
        assert(self.lowest_register <= register <= self.highest_register)
        cmd = self.GetCommand(0x5C, register, num_bytes=1)
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Recall register %d" % register)
        return self.ResponseStatus(response)
    def SetFunction(self, function="fixed"):
        '''Set the function (type of operation) of the load.
        function is one of "fixed", "short", "transient", or "battery".
        Note "list" is intentionally left out for now.
        '''
        msg = "Set function to %s" % function
        functions = {"fixed":0, "short":1, "transient":2, "battery":4}
        return self.SendIntegerToLoad(0x5D, functions[function], msg, num_bytes=1)
    def GetFunction(self):
        "Get the function (type of operation) of the load"
        msg = "Get function"
        fn = self.GetIntegerFromLoad(0x5E, msg, num_bytes=1)
        functions_inv = {0:"fixed", 1:"short", 2:"transient", 4:"battery"}
        return functions_inv[fn]
    def GetInputValues(self):
        '''Returns voltage in V, current in A, and power in W, op_state byte,
        and demand_state byte.
        '''
        cmd = self.StartCommand(0x5F)
        cmd += self.Reserved(3)
        cmd += bytes((self.CalculateChecksum(cmd),))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Get input values")
        values = {}
        values["voltage"] = self.DecodeInteger(response[3:7])/float(self.convert_voltage)
        values["current"] = self.DecodeInteger(response[7:11])/float(self.convert_current)
        values["power"] = self.DecodeInteger(response[11:15])/float(self.convert_power)
        return values
    def GetProductInformation(self):
        "Returns model number, serial number, and firmware version"
        cmd = self.StartCommand(0x6A)
        cmd += self.Reserved(3)
        cmd += bytes((self.CalculateChecksum(cmd),))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Get product info")
        model = response[3:7]
        res_str = f'Model={model.decode()}'
        # fw = hex(ord(response[9]))[2:] + "."
        # fw += hex(ord(response[8]))[2:]
        serial_number = response[10:20]
        res_str += f'\tSerial #={serial_number.decode()}'
        # return join((str(model), str(serial_number), str(fw)), "\t")
        return res_str
    def GetDemandState(self):
        '''Returns demand_state byte. Add DJS 2017/11/13 for Bat Discharge'''
        cmd = self.StartCommand(0x5F)
        cmd += self.Reserved(3)
        cmd += chr(self.CalculateChecksum(cmd))
        assert(self.CommandProperlyFormed(cmd))
        response = self.SendCommand(cmd)
        self.PrintCommandAndResponse(cmd, response, "Get input values")
        #op_state = hex(self.DecodeInteger(response[15]))
        demand_state = self.DecodeInteger(response[16:18])
        return demand_state
    def identify(self):
        return self.GetProductInformation()
        
        
        
        
        
        
        
        
        
        
        