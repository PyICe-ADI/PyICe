from ..lab_core import *
import time


'''This is old and not maintained. Consider Telemetrix instead.'''

class firmata(instrument):
    '''
    Firmata is a protocol for communicating with microcontrollers from software on a host computer.
    The protocol can be implemented in firmware on any microcontroller architecture as well as software on any host computer software package.
    The Arduino repository described here is a Firmata library for Arduino and Arduino-compatible devices. If you would like to contribute to Firmata, please see the Contributing section below.

    Usage
    The model supported by PyICe is to load a general purpose sketch called StandardFirmata
    on the Arduino board and then use the host computer exclusively to interact with the Arduino board.


    *** Arduino/Linduno specific:
    *** StandardFirmata is located in the Arduino IDE in File -> Examples -> Firmata.
    *** This sketch must be flashed onto the microcontroller board to use this instrument driver.

    *** Other microcontrollers:
    *** Must flash architechture-specific compiled embedded server.

    https://github.com/firmata/protocol/blob/master/README.md

    https://github.com/firmata/arduino/blob/master/readme.md

    https://github.com/MrYsLab/PyMata/blob/master/README.md
    '''
    def __init__(self,serial_port_name):
        '''
        1) note that this makes its own serial object. Can't use master.get_raw_serial_interface and this will read/write in its own thread.

        2) inherit from delegator and aggregate pin states with single query???

        '''
        print("Consider switching from Firmata to Telemetrix")
        try:
            from PyMata.pymata import PyMata
        except ImportError as e:
            print("*** Please install the Pymata module.")
            print("*** https://github.com/MrYsLab/PyMata/blob/master/README.md")
            print("*** Try typing 'pip install pymata' or 'python PyICe/deps/PyMata_v2.09/setup.py install'.")
            raise e

        class PyMata_Extensions(PyMata):
            """
            This sub class simply adds a method to reset serial commuications to the base class PyMata.
            Its done this way so when PyMata is updated to a newer version we keep the added functionality.
            """
            def reset_serial_communications(self):
                if self.verbose:
                    print('Resetting Serial Communications')
                """
                Close, re-open, and reset connection to the arduino.  This is needed in case the
                connection is lost somehow.
                """
                # Prepare to reset.  Stop the command handler thread, stop the serial communications thread,
                # block both threads and close the serial port.
                self._command_handler.stop()
                self.transport.stop()
                self._command_handler.join()
                self.transport.join()
                self.transport.close();
                # DIFF!
                # Commented out the sleep below, we don't need it.
                #time.sleep(2)

                # ALERT! This is the beginning of a cut and paste from the PyMata 2.14 constructor.
                # All the cut and pasted material performs the same setup of the PyMata internal
                # object for command handling and serial port setup, both of which are threads.
                # Note there some differences but they are all well commented.

                # DIFF!  Left out the two lines to initialize HC-06 Bluetooth here.

                # Attempt to open communications with the Arduino micro-controller
                self.transport.open(self.verbose)

                # DIFF! Left out three lines for HC-06 Bluetooth here.
                # This sleep is necessary to support Arduino Mega
                time.sleep(1)

                # DIFF!
                # Do not restart the data receive thread, threads only start once and it was already
                # started in the constructor.

                # DIFF!
                # Do not re-instansiate the command handler, the constructor did that.
                # Just reset it.
                self._command_handler.system_reset()

                ########################################################################
                # constants defined locally from values contained in the command handler
                ########################################################################

                # Data latch state constants to be used when accessing data returned from get_latch_data methods.
                # The get_latch data methods return [pin_number, latch_state, latched_data, time_stamp]
                # These three constants define possible values for the second item in the list, latch_state

                # this pin will be ignored for latching - table initialized with this value
                self.LATCH_IGNORE = self._command_handler.LATCH_IGNORE
                # When the next pin value change is received for this pin, if it matches the latch criteria
                # the data will be latched.
                self.LATCH_ARMED = self._command_handler.LATCH_ARMED
                # Data has been latched. Read the data to re-arm the latch.
                self.LATCH_LATCHED = self._command_handler.LATCH_LATCHED

                #
                # These constants are used when setting a data latch.
                # Latch threshold types
                #
                self.DIGITAL_LATCH_HIGH = self._command_handler.DIGITAL_LATCH_HIGH
                self.DIGITAL_LATCH_LOW = self._command_handler.DIGITAL_LATCH_LOW

                self.ANALOG_LATCH_GT = self._command_handler.ANALOG_LATCH_GT
                self.ANALOG_LATCH_LT = self._command_handler.ANALOG_LATCH_LT
                self.ANALOG_LATCH_GTE = self._command_handler.ANALOG_LATCH_GTE
                self.ANALOG_LATCH_LTE = self._command_handler.ANALOG_LATCH_LTE

                # constants to be used to parse the data returned from calling
                # get_X_latch_data()

                self.LATCH_PIN = 0
                self.LATCH_STATE = 1
                self.LATCHED_DATA = 2
                self.LATCHED_TIME_STAMP = 3

                # DIFF!
                # Do not start the command processor thread, the constructor already started it.
                # Command handler should now be prepared to receive replies from the Arduino, so go ahead
                # detect the Arduino board

                if self.verbose:
                    print('\nPlease wait while Arduino is being detected. This can take up to 30 seconds ...')

                # perform board auto discovery
                if not self._command_handler.auto_discover_board(self.verbose):
                    # board was not found so shutdown
                    if self.verbose:
                        print("Board Auto Discovery Failed!, Shutting Down")
                    self._command_handler.stop()
                    self.transport.stop()
                    self._command_handler.join()
                    self.transport.join()
                    #DIFF! commented out the sleep below, we don't need it.
                    # time.sleep(2)
                # End of cut and paste from Pymata constructor.
        # End of sub-class definition of PyMata_Extensions.

        # Below is remainder of class firmata constructor that uses class PyMata_Extensions
        self._base_name = 'Firmata'
        instrument.__init__(self,f"Firmata Client @ {serial_port_name}")
        self.ser_name = serial_port_name
        #verbose doesn't seem to print much except board capabilities upon init
        self.firmata_board = PyMata_Extensions(self.ser_name, bluetooth=False, verbose=True)
        self._configured_pins = {}
        self._configured_pins[self.firmata_board.ANALOG] = {}
        self._configured_pins[self.firmata_board.DIGITAL] = {}
    def _check_configure_pin(self, pin, channel):
        if pin in self._configured_pins[channel.get_attribute('pin_type')]:
            raise Exception(f"Cannot configure {'Analog' if channel.get_attribute('pin_type') == self.firmata_board.ANALOG else 'Digital'} pin {pin} as type {channel.get_attribute('channel_type')}. Pin already configured as type {self._configured_pins[channel.get_attribute('pin_type')][pin].get_attribute('channel_type')}.")
        else:
            self._configured_pins[channel.get_attribute('pin_type')][pin] = channel
            self.firmata_board.set_pin_mode(pin, mode=channel.get_attribute('mode'), pin_type=channel.get_attribute('pin_type'))
    def add_channel_digital_input(self, channel_name, pin, enable_pullup=False):
        '''Digital input pin.
        Use higher-numbered digital pin aliasing to use analog pins as digital.
        For Arduno Uno/Linduino:
        A0=14
        A1=15
        A2=16
        A3=17
        A4=18
        A5=19

        Set enable_pullup=True to enable on-board uC pullups. (~20k in Arduino Uno/Linduino AtMega328P)
        '''
        new_channel = integer_channel(channel_name, size=1, read_function=lambda: self.firmata_board.digital_read(pin))
        new_channel.set_attribute('channel_type','DIGITAL_INPUT')
        new_channel.set_attribute('pin',pin)
        new_channel.set_attribute('mode',self.firmata_board.INPUT)
        new_channel.set_attribute('pin_type',self.firmata_board.DIGITAL)
        new_channel.set_attribute('pullup_enabled',enable_pullup)
        self._check_configure_pin(pin, new_channel)
        self.firmata_board.digital_write(pin, 1 if enable_pullup else 0)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_digital_input.__doc__)
        return self._add_channel(new_channel)
    # def add_channel_digital_input_bus(self, channel_name, pin_list):
        # '''Multi-pin digital input bus.'''
        # raise Exception('Not yet implemented')
    def add_channel_digital_output(self, channel_name, pin):
        '''Digital output pin.
        analog_pin argument doesn't function. Use higher-numbered digital pin aliasing to use analog pins as digital.
        For Arduno Uno/Linduino:
        A0=14
        A1=15
        A2=16
        A3=17
        A4=18
        A5=19
        '''
        new_channel = integer_channel(channel_name, size=1, write_function=lambda value: self.firmata_board.digital_write(pin, value))
        new_channel.set_attribute('channel_type','DIGITAL_OUTPUT')
        new_channel.set_attribute('pin',pin)
        new_channel.set_attribute('mode',self.firmata_board.OUTPUT)
        new_channel.set_attribute('pin_type',self.firmata_board.DIGITAL)
        self._check_configure_pin(pin, new_channel)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_digital_output.__doc__)
        return self._add_channel(new_channel)
    # def add_channel_digital_output_bus(self, channel_name, pin_list):
        # '''Multi-pin digital output bus.'''
        # raise Exception('Not yet implemented')
    def add_channel_analog_input(self, channel_name, pin):
        '''Analog input pin.'''
        new_channel = integer_channel(channel_name, size=10, read_function=lambda: self.firmata_board.analog_read(pin)) #don't really know size, but it doesn't matter. 10-bit answer on Arduino hardware
        new_channel.set_attribute('channel_type','ANALOG_INPUT')
        new_channel.set_attribute('pin',pin)
        new_channel.set_attribute('mode',self.firmata_board.INPUT)
        new_channel.set_attribute('pin_type',self.firmata_board.ANALOG)
        self._check_configure_pin(pin, new_channel)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_analog_input.__doc__)
        new_channel.add_format(format_name='arduino_adc_5v', format_function=lambda code: code*5.0/1024, unformat_function=lambda analog: int(round(analog/5.0*1024)), signed=False, units='V')
        new_channel.add_format(format_name='arduino_adc_3v3', format_function=lambda code: code*3.3/1024, unformat_function=lambda analog: int(round(analog/3.3*1024)), signed=False, units='V')
        #Not sure if Firmata protocol allows ADC reference switch....
        #new_channel.add_format(format_name='arduino_adc_1v1', format_function=lambda code: code*1.1/1024, unformat_function=lambda analog: int(round(analog/1.1*1024)), signed=False, units='V')
        #new_channel.add_format(format_name='arduino_adc_2v56', format_function=lambda code: code*2.56/1024, unformat_function=lambda analog: int(round(analog/2.56*1024)), signed=False, units='V')
        return self._add_channel(new_channel)
    def add_channel_pwm_output(self, channel_name, pin):
        '''PWM output pin.
        Arduino UNO (Atmega328) compatible with digital pins 3,5,6,9,10,11.
        '''
        new_channel = integer_channel(channel_name, size=8, write_function=lambda value: self.firmata_board.analog_write(pin, value)) #8-bit hardware is Arduino specific (0-255 valide PWM values)
        new_channel.set_attribute('channel_type','PWM_OUTPUT')
        new_channel.set_attribute('pin',pin)
        new_channel.set_attribute('mode',self.firmata_board.PWM)
        new_channel.set_attribute('pin_type',self.firmata_board.DIGITAL)
        self._check_configure_pin(pin, new_channel)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_pwm_output.__doc__)
        new_channel.add_format(format_name='arduino_pwm_dc', format_function=lambda code: code*1.0/255, unformat_function=lambda analog: int(round(analog/1.0*255)), signed=False, units='')
        new_channel.add_format(format_name='arduino_pwm_5v', format_function=lambda code: code*5.0/255, unformat_function=lambda analog: int(round(analog/5.0*255)), signed=False, units='V')
        new_channel.add_format(format_name='arduino_pwm_3v3', format_function=lambda code: code*3.3/255, unformat_function=lambda analog: int(round(analog/3.3*255)), signed=False, units='V')
        return self._add_channel(new_channel)
    def add_channel_servo(self, channel_name, pin):
        '''RC servo control (544ms-2400ms PWM) output.'''
        raise Exception('Not yet implemented')
        #self.firmata_board.servo_config(pin, min_pulse=544, max_pulse=2400)
    def add_channel_digital_latch(self, channel_name, digital_input_channel, threshold_high=True):
        '''Latch transient signals on a digital input pin. Software logic appears to be edge-triggered.
        Input pin channel must have been previously configured with firmata.add_channel_digital_input().
        Pass channel object instance to digital_input_channel argument.
        latches rising edge by default. Set threshold_high=False to set latch sensitivity to logic low.
        this doesn't appear to have access to analog pins (A0-A5) used as digital IO.
        '''
        def read_latch_status(latch_channel):
            latch_status = self.firmata_board.get_digital_latch_data(latch_channel.get_attribute('pin'))
            latch_state = True if latch_status[1] == self.firmata_board.LATCH_LATCHED else False
            if latch_state:
                #re-arm latch
                self.firmata_board.set_digital_latch(pin=latch_channel.get_attribute('pin'), threshold_type=latch_channel.get_attribute('threshold_type'))
                return True
            return False
        new_channel = integer_channel(channel_name, size=1, read_function=lambda: None) #dummy read function until channel instance is created
        new_channel._read = lambda: read_latch_status(new_channel) #get reference back to channel for attribute lookup
        new_channel.set_attribute('channel_type','DIGITAL_LATCH')
        new_channel.set_attribute('pin',digital_input_channel.get_attribute('pin'))
        new_channel.set_attribute('threshold_type',self.firmata_board.DIGITAL_LATCH_HIGH if threshold_high else self.firmata_board.DIGITAL_LATCH_LOW)
        new_channel.set_attribute('parent_channel', digital_input_channel)
        assert digital_input_channel.get_attribute('channel_type') == 'DIGITAL_INPUT'
        self.firmata_board.set_digital_latch(pin=new_channel.get_attribute('pin'), threshold_type=new_channel.get_attribute('threshold_type'))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_digital_latch.__doc__)
        return self._add_channel(new_channel)
    def add_channel_analog_latch(self, channel_name, analog_input_channel, threshold, threshold_type='>'):
        '''Latch transient signals on an analog (ADC) input pin.
        Input pin channel must have been previously configured with firmata.add_channel_analog_input().
        Pass channel object instance to analog_input_channel argument.
        threshold is in Volts, assuming 5V Arduino ADC full scale (1023). Change format setting of _thresold channel to use raw (0-1023) or 3.3V ADC scales.
        latches high signal levels by default. Set threshold_type='>=', '<' or  to set latch sensitivity to logic low.
        '''
        def read_latch_status(latch_channel):
            latch_status = self.firmata_board.get_analog_latch_data(latch_channel.get_attribute('pin'))
            latch_state = True if latch_status[1] == self.firmata_board.LATCH_LATCHED else False
            if latch_state:
                #re-arm latch
                th_ch = latch_channel.get_attribute('threshold_channel')
                th_ch.write(th_ch.read())
                return True
            return False
        assert analog_input_channel.get_attribute('channel_type') == 'ANALOG_INPUT'
        latch_channel = integer_channel(channel_name, size=1, read_function=lambda: None) #dummy read function until channel instance is created
        latch_channel._read = lambda: read_latch_status(latch_channel) #get reference back to channel for attribute lookup
        latch_channel.set_attribute('channel_type','ANALOG_LATCH')
        latch_channel.set_attribute('pin',analog_input_channel.get_attribute('pin'))
        latch_channel.set_attribute('parent_channel', analog_input_channel)
        latch_channel.set_description(self.get_name() + ': ' + self.add_channel_analog_latch.__doc__)
        if threshold_type == '>':
            latch_channel.set_attribute('threshold_type',self.firmata_board.ANALOG_LATCH_GT)
        elif threshold_type == '<':
            latch_channel.set_attribute('threshold_type',self.firmata_board.ANALOG_LATCH_LT)
        elif threshold_type == '>=':
            latch_channel.set_attribute('threshold_type',self.firmata_board.ANALOG_LATCH_GTE)
        elif threshold_type == '<=':
            latch_channel.set_attribute('threshold_type',self.firmata_board.ANALOG_LATCH_LTE)
        else:
            raise Exception(f"threshold_type: {threshold_type} not in ['>', '<', '>=', '<=']")
        threshold_channel = integer_channel(channel_name + '_threshold', size=10, write_function=lambda threshold: self.firmata_board.set_analog_latch(pin=latch_channel.get_attribute('pin'),
                                                                                                                                                       threshold_type=latch_channel.get_attribute('threshold_type'),
                                                                                                                                                       threshold_value=threshold))
        threshold_channel.add_format(format_name='arduino_adc_5v', format_function=lambda code: code*5.0/1024, unformat_function=lambda analog: int(round(analog/5.0*1024)), signed=False, units='V')
        threshold_channel.add_format(format_name='arduino_adc_3v3', format_function=lambda code: code*3.3/1024, unformat_function=lambda analog: int(round(analog/3.3*1024)), signed=False, units='V')
        threshold_channel.set_format('arduino_adc_5v')
        threshold_channel.write(threshold)
        threshold_channel.set_attribute('threshold_type',threshold_type)
        threshold_channel.set_attribute('parent_channel', analog_input_channel)
        threshold_channel.set_attribute('latch_channel', latch_channel)
        latch_channel.set_attribute('threshold_channel', threshold_channel)
        self._add_channel(threshold_channel)
        return self._add_channel(latch_channel)
    def reset_serial_communications(self):
        return (self.firmata_board.reset_serial_communications())
