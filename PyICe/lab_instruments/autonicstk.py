from ..lab_core import *
from .modbus_instrument import modbus_register

class autonicstk(instrument):
    def __init__(self, interface_raw_serial, modbus_address):
        import minimalmodbus
        #minimalmodbus.BAUDRATE = 38400
        minimalmodbus.BAUDRATE = 9600
        self._base_name = 'Autonics TK Series PID'
        instrument.__init__(self,f"Autonics PID @ {interface_raw_serial}:{modbus_address}")
        #self.add_interface_raw_serial(interface_raw_serial,timeout=5)
        self.sp = interface_raw_serial
        interface_raw_serial.write = interface_raw_serial.write_raw         #this is untested
        interface_raw_serial.read = interface_raw_serial.read_raw
        self.modbus_address = modbus_address
        self.modbus_pid = minimalmodbus.Instrument(interface_raw_serial,modbus_address)
        self.modbus_pid.serial.stopbits = 1
        self.modbus_pid.serial.timeout = 5
    def add_basic_channels(self, channel_name):
        self.add_channel_setpoint(channel_name)
        self.add_channel_measured(channel_name)
        self.add_channel_enable_output(channel_name)
    def add_advanced_channels(self, channel_name):
        self.add_channel_mode(channel_name)
        self.add_channel_units(channel_name)
        self.add_channel_presets(channel_name)
        self.add_channel_heat_mv(channel_name)
        self.add_channel_cool_mv(channel_name)
        self.add_channel_alarm1(channel_name)
        self.add_channel_alarm2(channel_name)
        self.add_channel_autotune(channel_name)
        self.add_channels_tuning(channel_name)
        self.add_channel_sensor_type(channel_name)
        self.add_channels_alarm_config(channel_name)
    def get_decimal(self):
        return self.modbus_pid.read_register(1001,functioncode=4)
    def add_channel_measured(self, channel_name):
        '''Measured Temperature Readback (PV)'''
        new_register = channel(f'{channel_name}_PV', read_function=self._read_temperature_sense)
        new_register.set_category('Measure')
        new_register.set_description(self.add_channel_measured.__doc__)
        return self._add_channel(new_register)
    def _read_temperature_sense(self):
        return self.modbus_pid.read_register(1000,number_of_decimals=self.get_decimal(),functioncode=4,signed=True)
    def add_channel_units(self, channel_name):
        '''Select Celsius or Farenheit. CAUTION: Units also change PID gains.'''
        new_register = register(f'{channel_name}_Units',
                                size=1,
                                read_function=lambda: self.modbus_pid.read_register(151,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(151,int(data),functioncode=6))
        new_register.add_preset('Celsius',0)
        new_register.add_preset('Farenheit',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Set')
        new_register.set_description(self.add_channel_units.__doc__)
        return self._add_channel(new_register)
    def add_channel_setpoint(self, channel_name):
        '''Target Temperature Setpoint (SV)'''
        new_register = modbus_register(channel_name,
                                read_function=lambda: self.retry(lambda: self.modbus_pid.read_register(0,number_of_decimals=self.get_decimal(),functioncode=3,signed=True), retry_count=1),
                                write_function=self._write_temperature)
        new_register.set_category('Set')
        new_register.set_description(self.add_channel_setpoint.__doc__)
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(165)
        return self._add_channel(new_register)
    def _write_temperature(self, value):
        self.modbus_pid.write_register(0,float(value),number_of_decimals=self.get_decimal(),functioncode=6,signed=True)
    def add_channel_heat_mv(self, channel_name):
        '''Heater percent power manipulated variable (MV). Can be written directly in manual mode.'''
        new_register = modbus_register(f'{channel_name}_MV_Heat',
                                read_function=lambda: self.modbus_pid.read_register(1,number_of_decimals=1,functioncode=3,signed=False),
                                write_function=lambda data: self.modbus_pid.write_register(1,float(data),number_of_decimals=1,functioncode=6,signed=False))
        new_register.set_category('Heat')
        new_register.set_description(self.add_channel_heat_mv.__doc__)
        return self._add_channel(new_register)
    def add_channel_cool_mv(self, channel_name):
        '''Cooler percent power manipulated variable (MV). Can be written directly in manual mode.'''
        new_register = modbus_register(f'{channel_name}_MV_Cool',
                                read_function=lambda: self.modbus_pid.read_register(2,number_of_decimals=1,functioncode=3,signed=False),
                                write_function=lambda data: self.modbus_pid.write_register(2,float(data),number_of_decimals=1,functioncode=6,signed=False))
        new_register.set_category('Cool')
        new_register.set_description(self.add_channel_cool_mv.__doc__)
        return self._add_channel(new_register)
    def add_channel_mode(self, channel_name):
        '''Automatic/Manual mode selector. Automatic uses temperature setpoint (SV). Manual uses heat and cool MV setpoints.'''
        new_register = register(f'{channel_name}_Mode',
                                size=1,
                                read_function=lambda: self.modbus_pid.read_register(3,functioncode=3,signed=False),
                                write_function=lambda data: self.modbus_pid.write_register(3,int(data),functioncode=6,signed=False))
        new_register.add_preset('Auto',0)
        new_register.add_preset('Manual',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Enables')
        new_register.set_description(self.add_channel_mode.__doc__)
        return self._add_channel(new_register)
    def add_channel_presets(self, channel_name):
        '''Select one of 4 pre-selected temperatures.'''
        new_register = register(f'{channel_name}_Preset',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(51,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(51,int(data),functioncode=6))
        #new_register.add_preset('Beef',0)
        #new_register.add_preset('Pork',1)
        #new_register.add_preset('Vegetable',2)
        #new_register.add_preset('Yogurt',3)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Set')
        new_register.set_description(self.add_channel_presets.__doc__)
        return self._add_channel(new_register)
    def add_channel_alarm1(self, channel_name):
        '''Alarm 1 output status.'''
        new_register = integer_channel(f'{channel_name}_Alarm1',
                                       size=1,
                                       read_function=lambda: self.modbus_pid.read_register(1006,functioncode=4)>>9&1)
        new_register.add_preset('OK',0)
        new_register.add_preset('Alarm',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Alarm1')
        new_register.set_description(self.add_channel_alarm1.__doc__)
        return self._add_channel(new_register)
    def add_channel_alarm2(self, channel_name):
        '''Alarm 2 output status.'''
        new_register = integer_channel(f'{channel_name}_Alarm2',
                                       size=1,
                                       read_function=lambda: self.modbus_pid.read_register(1006,functioncode=4)>>10&1)
        new_register.add_preset('OK',0)
        new_register.add_preset('Alarm',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Alarm2')
        new_register.set_description(self.add_channel_alarm2.__doc__)
        return self._add_channel(new_register)
    def add_channel_enable_output(self, channel_name):
        '''Enable/Disable heat and cool outputs.'''
        new_register = register(f'{channel_name}_enable',
                                size=1,
                                read_function=lambda: False if self.modbus_pid.read_register(50,functioncode=3) else True,
                                write_function=self._enable)
        new_register.add_preset('Run',True)
        new_register.add_preset('Stop',False)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Enables')
        new_register.set_description(self.add_channel_enable_output.__doc__)
        return self._add_channel(new_register)
    def _enable(self, enable):
        self.modbus_pid.write_register(50,0 if enable else 1,functioncode=6)
    def add_channel_heat_cool_mode(self, channel_name):
        '''enable heat only, cool only or heat-cool mode'''
        new_register = register(f'{channel_name}_heat_cool_mode',
                                size=2,
                                read_function=lambda: self.modbus_pid.read_register(162,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(162,int(data),functioncode=6))
        new_register.add_preset('Heat',0)
        new_register.add_preset('Cool',1)
        new_register.add_preset('Heat-Cool',2)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Enables')
        new_register.set_description(self.add_channel_heat_cool_mode.__doc__)
        return self._add_channel(new_register)
    def add_channel_autotune(self, channel_name):
        '''Start autotune sequence.'''
        new_register = register(f'{channel_name}_Autotune',
                                size=1,
                                read_function=lambda: self.modbus_pid.read_register(100,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(100,int(data),functioncode=6))
        new_register.add_preset('Run',1)
        new_register.add_preset('Stop',0)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('PID_tuning')
        new_register.set_description(self.add_channel_autotune.__doc__)
        return self._add_channel(new_register)
    def add_channels_tuning(self, channel_name):
        '''PID control gain settings. See: https://en.wikipedia.org/wiki/PID_controller#Alternative_nomenclature_and_PID_forms'''
        new_channels = []
        new_register = modbus_register(f'{channel_name}_Heat_Proportional',
                                read_function=lambda: self.modbus_pid.read_register(101,number_of_decimals=1,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(101,float(data),number_of_decimals=1,functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Reciprocal heat proportional gain. Number of degrees over which the heat output transistion from 0%-100% output due to proportional error alone.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Cool_Proportional',
                                read_function=lambda: self.modbus_pid.read_register(102,number_of_decimals=1,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(102,float(data),number_of_decimals=1,functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Reciprocal cool proportional gain. Number of degrees over which the heat output transistion from 100%-0% output due to proportional error alone.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Heat_Integral',
                                read_function=lambda: self.modbus_pid.read_register(103,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(103,int(data),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Heat integral time. Number of seconds over which the (measured) process variable will change from proportial residual error to zero error.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Cool_Integral',
                                read_function=lambda: self.modbus_pid.read_register(104,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(104,int(data),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Cool integral time. Number of seconds over which the (measured) process variable will change from proportial residual error to zero error.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Heat_Derivative',
                                read_function=lambda: self.modbus_pid.read_register(105,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(105,int(data),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Heat derivitive time. Scaling constant to map degrees/s (rate) into degrees of apparent error.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Cool_Derivative',
                                read_function=lambda: self.modbus_pid.read_register(106,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(106,int(data),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Cool derivitive time. Scaling constant to map degrees/s (rate) into degrees of apparent error.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Heat_Hysteresis',
                                         read_function=lambda: self.modbus_pid.read_register(109,number_of_decimals=self.get_decimal(),functioncode=3),
                                         write_function=lambda data: self.modbus_pid.write_register(109,float(data),number_of_decimals=self.get_decimal(),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Heat hysteresis. Dead band for heat loop only. Not used with PID proportional output mode.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Cool_Hysteresis',
                                         read_function=lambda: self.modbus_pid.read_register(111,number_of_decimals=self.get_decimal(),functioncode=3),
                                         write_function=lambda data: self.modbus_pid.write_register(111,float(data),number_of_decimals=self.get_decimal(),functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description('Cool hysteresis. Dead band for cool loop only. Not used with PID proportional output mode.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Deadband',
                                         read_function=lambda: self.modbus_pid.read_register(107,number_of_decimals=self.get_decimal(),functioncode=3,signed=True),
                                         write_function=lambda data: self.modbus_pid.write_register(107,float(data),number_of_decimals=self.get_decimal(),functioncode=6,signed=True))
        new_register.set_category('PID_tuning')
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(150)
        new_register.set_description('Dead band between heat and cool loops. Negative value causes class-A operation.')
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = register(f'{channel_name}_SSR1_Mode',
                                         size=2,
                                         read_function=lambda: self.modbus_pid.read_register(166,functioncode=3),
                                         write_function=lambda data: self.modbus_pid.write_register(166,int(data),functioncode=6))
        new_register.add_preset('Standard',0)
        new_register.add_preset('Cycle',1)
        new_register.add_preset('Phase',2)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('PID_tuning')
        new_register.set_description("Heat PWM mode. 'Standard' uses 'Heating_Control_Time' setting. 'Cycle' powers/unpowers the heater over whole power line cycles. 'Phase' synchronously dims the heater by delaying turn-on during each power line cycle.")
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Heating_Control_Time',
                                         read_function=lambda: self.modbus_pid.read_register(170,number_of_decimals=1,functioncode=3),
                                         write_function=lambda data: self.modbus_pid.write_register(170,float(data),number_of_decimals=1,functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description("Heat control PWM period when in 'Standard' SSR1_Mode.")
        self._add_channel(new_register)
        new_channels.append(new_register)
        new_register = modbus_register(f'{channel_name}_Cooling_Control_Time',
                                read_function=lambda: self.modbus_pid.read_register(171,number_of_decimals=1,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(171,float(data),number_of_decimals=1,functioncode=6))
        new_register.set_category('PID_tuning')
        new_register.set_description("Cool control PWM period.")
        self._add_channel(new_register)
        new_channels.append(new_register)
        return new_channels
    def add_channel_sensor_type(self, channel_name):
        new_register = register(f'{channel_name}_Sensor',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(150,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(150,int(data),functioncode=6))
        new_register.add_preset('Thermocouple_K_high',0)
        new_register.add_preset('Thermocouple_K_low',1)
        new_register.add_preset('DIN_Pt100_high',24)
        new_register.add_preset('DIN_Pt100_low',25)

        #new_register.add_preset('PT100',0)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('PID_tuning')
        new_register.set_description('Temperature sensor type selection.')
        self._add_channel(new_register)
    def _write_alarm1_high(self, data):
        self.modbus_pid.write_register(54,float(data),number_of_decimals=self.get_decimal(),functioncode=6,signed=True)
    def _write_alarm2_high(self, data):
        self.modbus_pid.write_register(56,float(data),number_of_decimals=self.get_decimal(),functioncode=6,signed=True)
    def add_channels_alarm_config(self, channel_name):
        new_register = modbus_register(f'{channel_name}_Alarm1_low_limit',
                                read_function=lambda: self.modbus_pid.read_register(53,number_of_decimals=self.get_decimal(),functioncode=3,signed=True),
                                write_function=lambda data: self.modbus_pid.write_register(53,float(data),number_of_decimals=self.get_decimal(),functioncode=6,signed=True))
        new_register.set_category('Alarm_config')
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(500)
        self._add_channel(new_register)
        new_register = modbus_register(f'{channel_name}_Alarm1_high_limit',
                                read_function=lambda: self.modbus_pid.read_register(54,number_of_decimals=self.get_decimal(),functioncode=3,signed=True),
                                write_function=self._write_alarm1_high)
        new_register.set_category('Alarm_config')
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(500)
        self._add_channel(new_register)
        new_register = modbus_register(f'{channel_name}_Alarm1_hysteresis',
                                read_function=lambda: self.modbus_pid.read_register(202,number_of_decimals=self.get_decimal(),functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(202,float(data),number_of_decimals=self.get_decimal(),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm1_Relay',
                                size=1,
                                read_function=lambda: self.modbus_pid.read_register(203,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(203,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        new_register.add_preset('Normally Open',0)
        new_register.add_preset('Normally Closed',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm1_on_delay',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(204,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(204,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm1_off_delay',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(205,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(205,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm1_mode',
                                size=4,
                                read_function=lambda: self.modbus_pid.read_register(200,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(200,int(data),functioncode=6))
        new_register.add_preset('Off',0)
        new_register.add_preset('Deviation High Limit',1)
        new_register.add_preset('Deviation Low Limit',2)
        new_register.add_preset('Deviation High/Low Limit',3)
        new_register.add_preset('Deviation High/Low Limit Reverse',4)
        new_register.add_preset('Absolute High Limit',5)
        new_register.add_preset('Absolute Low Limit',6)
        new_register.add_preset('Loop Break',7)
        new_register.add_preset('Sensor Break',8)
        new_register.add_preset('Heater Burnout',9)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = modbus_register(f'{channel_name}_Alarm2_low_limit',
                                read_function=lambda: self.modbus_pid.read_register(55,number_of_decimals=self.get_decimal(),functioncode=3,signed=True),
                                write_function=lambda data: self.modbus_pid.write_register(55,float(data),number_of_decimals=self.get_decimal(),functioncode=6,signed=True))
        new_register.set_category('Alarm_config')
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(500)
        self._add_channel(new_register)
        new_register = modbus_register(f'{channel_name}_Alarm2_high_limit',
                                read_function=lambda: self.modbus_pid.read_register(56,number_of_decimals=self.get_decimal(),functioncode=3,signed=True),
                                write_function=self._write_alarm2_high)
        new_register.set_category('Alarm_config')
        new_register.set_min_write_limit(-199)
        new_register.set_max_write_limit(500)
        self._add_channel(new_register)
        new_register = modbus_register(f'{channel_name}_Alarm2_hysteresis',
                                read_function=lambda: self.modbus_pid.read_register(208,number_of_decimals=self.get_decimal(),functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(208,float(data),number_of_decimals=self.get_decimal(),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm2_Relay',
                                size=1,
                                read_function=lambda: self.modbus_pid.read_register(209,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(209,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        new_register.add_preset('Normally Open',0)
        new_register.add_preset('Normally Closed',1)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm2_on_delay',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(210,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(210,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm2_off_delay',
                                size=16,
                                read_function=lambda: self.modbus_pid.read_register(211,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(211,int(data),functioncode=6))
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)
        new_register = register(f'{channel_name}_Alarm2_mode',
                                size=4,
                                read_function=lambda: self.modbus_pid.read_register(206,functioncode=3),
                                write_function=lambda data: self.modbus_pid.write_register(206,int(data),functioncode=6))
        new_register.add_preset('Off',0)
        new_register.add_preset('Deviation High Limit',1)
        new_register.add_preset('Deviation Low Limit',2)
        new_register.add_preset('Deviation High/Low Limit',3)
        new_register.add_preset('Deviation High/Low Limit Reverse',4)
        new_register.add_preset('Absolute High Limit',5)
        new_register.add_preset('Absolute Low Limit',6)
        new_register.add_preset('Loop Break',7)
        new_register.add_preset('Sensor Break',8)
        new_register.add_preset('Heater Burnout',9)
        new_register.use_presets_read(True)
        new_register.use_presets_write(True)
        new_register.set_category('Alarm_config')
        self._add_channel(new_register)

    def retry(self, cmd, retry_count):
        try:
            return cmd()
        except Exception as e:
            if retry_count > 0:
                print(e)
                print(f'Flushed: {self.flush()}')
                self.retry(cmd, retry_count=retry_count-1)
            else:
                print(f'Flushed: {self.flush()}')
                raise e

    def flush(self):
        return self.modbus_pid.serial.read(self.modbus_pid.serial.inWaiting())
