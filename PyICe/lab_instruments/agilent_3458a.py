from ..lab_core import instrument, channel

class hp_3458a(instrument):
    '''HP 3458A MULTIMETER'''
    def __init__(self,interface_visa):
        '''interface_visa"'''
        self._base_name = 'hp_3458a'
        instrument.__init__(self,f"hp_3458a @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self.get_interface().write(('RESET'))
        self.get_interface().write(('END 1')) # EOI line set true with last byte of last reading
        self.meter_channel = None
    def add_channel(self,channel_name):
        '''Deprecated! Use add_channel_[a,d]c_voltage, current, etc instead.
        Channel configuration was changed to bring meter NPLC/range configuration
        within channel framework and allow access from channel master.'''
        # raise Exception('Use add_channel_dc_voltage, add_channel_dc_current, etc to configure instrument.')
        print(f"WARNING: Channel {channel_name} add_channel method deprecated!")
        print('Use add_channel_dc_voltage, add_channel_dc_current, etc to configure instrument instead.')
        print('Defaulting to DC Voltage, NPLC=50, range="AUTO"')
        return self.add_channel_dc_voltage(channel_name)
    def add_channel_dc_voltage(self,channel_name,NPLC=50,range='AUTO'):
        '''Add named DC voltage measurement channel.
        Optionally set number of powerline cycles for integration to [0-1000]
        and set range to ['AUTO' or 0.12, 1.2, 12, 120, 1000]'''
        if self.meter_channel is not None:
            print("WARNING: Re-defining 3458 DMM channel configuration")
        self.meter_channel = channel(channel_name,read_function=self._read_meter)
        self.meter_channel.set_attribute('type', 'DCV')
        self._configure_meter(NPLC=NPLC, range=range)
        return self._add_channel(self.meter_channel)
    def add_channel_ac_voltage(self,channel_name,NPLC=50,range='AUTO'):
        '''Add named AC voltage measurement channel.
        Optionally set number of powerline cycles for integration to [0-1000]
        and set range to ['AUTO' or 0.012, 0.12, 1.2, 12, 120, 1000]'''
        if self.meter_channel is not None:
            print("WARNING: Re-defining 3458 DMM channel configuration")
        self.meter_channel = channel(channel_name,read_function=self._read_meter)
        self.meter_channel.set_attribute('type', 'ACV')
        self._configure_meter(NPLC=NPLC, range=range)
        return self._add_channel(self.meter_channel)
    def add_channel_dc_current(self,channel_name,NPLC=50,range='AUTO'):
        '''Add named DC current measurement channel.
        Optionally set number of powerline cycles for integration to [0-1000]
        and set range to ['AUTO' or 0.12E-6, 1.2E-6, 12E-6, 120E-6, 1.2E-3, 12E-3, 120E-3, 1.2]'''
        if self.meter_channel is not None:
            print("WARNING: Re-defining 3458 DMM channel configuration")
        self.meter_channel = channel(channel_name,read_function=self._read_meter)
        self.meter_channel.set_attribute('type', 'DCI')
        self._configure_meter(NPLC=NPLC, range=range)
        return self._add_channel(self.meter_channel)
    def add_channel_ac_current(self,channel_name,NPLC=50,range='AUTO'):
        '''Add named AC current measurement channel.
        Optionally set number of powerline cycles for integration to [0-1000]
        and set range to ['AUTO' or 0.12E-6, 1.2E-6, 12E-6, 120E-6, 1.2E-3, 12E-3, 120E-3, 1.2]'''
        if self.meter_channel is not None:
            print("WARNING: Re-defining 3458 DMM channel configuration")
        self.meter_channel = channel(channel_name,read_function=self._read_meter)
        self.meter_channel.set_attribute('type', 'ACI')
        self._configure_meter(NPLC=NPLC, range=range)
        return self._add_channel(self.meter_channel)
    def add_channel_ohm_fourwire(self,channel_name,NPLC=50,range='AUTO'):
        '''Add named 4-wire resistance measurement channel.
        Optionally set number of powerline cycles for integration to [0-1000]
        and set range to ['AUTO' or 12, 120 1.2e3, 1.2e4, 1.2e5, 1.2e6, 1.2e7, 1.2e8, 1.2e9]'''
        if self.meter_channel is not None:
            print("WARNING: Re-defining 3458 DMM channel configuration")
        self.meter_channel = channel(channel_name,read_function=self._read_meter)
        self.meter_channel.set_attribute('type', 'OHMF')
        self._configure_meter(NPLC=NPLC, range=range)
        return self._add_channel(self.meter_channel)
    def add_channel_NPLC(self,channel_name):
        '''add named channel to re-configure meter powerline cycle integration time.
        Valid values are [0-1000]'''
        if self.meter_channel is None:
            raise Exception(f'ERROR: Please create 3458 DMM NPLC re-configuration channel: {channel_name} after creating measurement channel.')
        meter_config_channel = channel(channel_name,write_function=lambda nplc: self._configure_meter(NPLC=nplc))
        return self._add_channel(meter_config_channel)
    def add_channel_range(self,channel_name):
        '''add named channel to re-configure meter range.
        Valid values depend on meter mode configuration.'''
        if self.meter_channel is None:
            raise Exception(f'ERROR: Please create 3458 DMM range re-configuration channel: {channel_name} after creating measurement channel.')
        meter_config_channel = channel(channel_name,write_function=lambda rng: self._configure_meter(range=rng))
        return self._add_channel(meter_config_channel)
    def _configure_meter(self,NPLC=None,range=None):
        if NPLC is not None:
            self.meter_channel.set_attribute('NPLC', NPLC)
        if range is not None:
            self.meter_channel.set_attribute('range', range)
        self.get_interface().write((f"FUNC {self.meter_channel.get_attribute('type')}, {self.meter_channel.get_attribute('range')}"))
        self.get_interface().write((f"NPLC {self.meter_channel.get_attribute('NPLC')}"))
        self.get_interface().write(('TARM HOLD'))
        self.get_interface().write(('TRIG AUTO'))
    def _read_meter(self):
        '''return float representing meter measurement.'''
        #why does float conversion raise exception? - TODO: Debug!
        self.get_interface().write(('TARM SGL, 1'))
        return float(self.get_interface().read())
    def display(self,message):
        '''Write message to instrument front panel display.'''
        self.get_interface().write(('DISP MSG,"' + message + '"'))