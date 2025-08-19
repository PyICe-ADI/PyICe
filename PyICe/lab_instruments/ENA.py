from ..lab_core import *
import abc

screen_configs = '''
┌───────────┐
│           │D1
│           │
│     1     │
│           │
│           │
└───────────┘
┌─────┬─────┐
│     │     │D12
│     │     │
│  1  │  2  │
│     │     │
│     │     │
└─────┴─────┘
┌───────────┐
│     1     │D1_2
│           │
├───────────┤
│           │
│     2     │
└───────────┘
┌───────┬───┐
│       │   │D112
│       │   │
│    1  │ 2 │
│       │   │
│       │   │
└───────┴───┘
┌───────────┐
│           │D1_1_2
│     1     │
│           │
├───────────┤
│     2     │
└───────────┘
┌───┬───┬───┐
│   │   │   │D123
│   │   │   │
│ 1 │ 2 │ 3 │
│   │   │   │
│   │   │   │
└───┴───┴───┘
┌───────────┐
│     1     │D1_2_3
├───────────┤
│     2     │
├───────────┤
│     3     │
└───────────┘
┌─────┬─────┐
│  1  │  2  │D12_33
│     │     │
├─────┴─────┤
│           │
│     3     │
│           │
└───────────┘
┌───────────┐
│           │D11_23
│     1     │
│           │
├─────┬─────┤
│     │     │
│  2  │  3  │
└─────┴─────┘
┌─────┬─────┐
│  1  │     │D13_23
│     │     │
├─────┤  3  │
│     │     │
│  2  │     │
└─────┴─────┘
┌─────┬─────┐
│     │  2  │D12_13
│     │     │
│  1  ├─────┤
│     │     │
│     │  3  │
└─────┴─────┘
┌──┬──┬──┬──┐
│  │  │  │  │D1234
│  │  │  │  │
│ 1│ 2│ 3│ 4│
│  │  │  │  │
│  │  │  │  │
└──┴──┴──┴──┘
┌───────────┐
│     1     │D1_2_3_4
├───────────┤
│     2     │
├───────────┤
│     3     │
├───────────┤
│     4     │
└───────────┘
┌─────┬─────┐
│  1  │  2  │D12_34
│     │     │
├─────┼─────┤
│     │     │
│  3  │  4  │
└─────┴─────┘'''
class scpi_NA(scpi_instrument, abc.ABC):
    ''''''
    #todo abstract methods?
# class keysight_e5061b_base(scpi_NA, abc.ABC):
class keysight_e5061b_base(scpi_NA, metaclass=abc.ABCMeta):
# class keysight_e5061b_base(abc.ABC):
    ''''''
    def __init__(self,interface_visa):
        '''interface_visa'''
        self._base_name = 'Keysight E5061B ENA network analyzer'
        super(keysight_e5061b_base, self).__init__(f"Keysight E5061B @ {interface_visa}")
        self.add_interface_visa(interface_visa)
        self._configured_traces = {ch:[] for ch in range(1,5)} #todo trace dict to track down channel_name?
        # turn off unpoulated channels to avoid confusing status condition register monitoring sweep/trigger status?
        for i in range(1,5):
            self.get_interface().write(f':INITiate{i}:CONTinuous OFF')

    def _check_trace_unconfigured(self, trace_number, channel_number):
        # what about more than 4 measurements from the same sweep (logged but not displayed)
        assert trace_number in range(1,5), f'trace_number argument {trace_number} must be between 1 and 4 inclusive.'
        assert channel_number in range(1,5), f'trace_number argument {trace_number} must be between 1 and 4 inclusive.'
        if trace_number in self._configured_traces[channel_number]:
            raise Exception(f'Trace {trace_number} already configured in channel {channel_number}.')
        else:
            self._configured_traces[channel_number].append(trace_number)
        if max(self._configured_traces[channel_number]) == 1:
            layout = 'D1'
        elif max(self._configured_traces[channel_number]) == 2:
            layout = 'D1_2'
        elif max(self._configured_traces[channel_number]) == 3:
            layout = 'D1_2_3'
        elif max(self._configured_traces[channel_number]) == 4:
            layout = 'D1_2_3_4'
        else:
            raise Exception("ENA network Analyzer: I'm lost - '_check_trace_unconfigured'")
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:SPLit {layout}') #{D1|D12|D1_2|D112|D1_1_2|D123|D1_2_3|D12_33|D11_23|D13_23|D12_13| D1234|D1_2_3_4|D12_34}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter:COUNt {max(self._configured_traces[channel_number])}')
        # TODO What about setting channel count and layout???

    def add_channels(self, channel_name, channel_number=1):
        '''shortcut method to add chx/trace1 channels'''
        channels = []
        channels.extend(self.add_xchannels(channel_name, channel_number=channel_number))
        channels.append(self.add_channel_trigger(channel_name)) #what about multiple channels? Just one trigger??
        # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))
        channels.append(self.add_channel_error(f'{channel_name}_errors'))
        return channels

    def add_channel_display_split(self, channel_name, channel_number):
        f'''Configures the screen splitting of the display.
{screen_configs}
'''
        new_channel = channel(channel_name, write_function=lambda layout: self.get_interface().write(f':DISPlay:WINDow{channel_number}:SPLit {layout}'))
        new_channel._read = lambda: self.get_interface().ask(':DISPlay:WINDow{channel_number}:SPLit?')
        new_channel.add_preset("D1")
        new_channel.add_preset("D12")
        new_channel.add_preset("D1_2")
        new_channel.add_preset("D112")
        new_channel.add_preset("D1_1_2")
        new_channel.add_preset("D123")
        new_channel.add_preset("D1_2_3")
        new_channel.add_preset("D12_33")
        new_channel.add_preset("D11_23")
        new_channel.add_preset("D13_23")
        new_channel.add_preset("D12_13")
        new_channel.add_preset("D1234")
        new_channel.add_preset("D1_2_3_4")
        new_channel.add_preset("D12_34")
        new_channel.set_attribute('channel_type', 'screen_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_display_split.__doc__)
        return self._add_channel(new_channel)

    def add_xchannels(self, channel_name, channel_number=1):
        '''shortcut method to add chx x-axis channels'''
        channels = []
        channels.append(self.add_channel_xdata(f'{channel_name}_fpoints', channel_number=channel_number))
        channels.append(self.add_channel_start_freq(f'{channel_name}_fstart', channel_number=channel_number))
        channels.append(self.add_channel_stop_freq(f'{channel_name}_fstop', channel_number=channel_number))
        channels.append(self.add_channel_points(f'{channel_name}_point_count', channel_number=channel_number))
        channels.append(self.add_channel_sweep_type(f'{channel_name}_sweep_type', channel_number=channel_number))
        channels.append(self.add_channel_IFBW(f'{channel_name}_RBW', channel_number=channel_number))
        # channels.append(self.add_channel_IFBW_readback(f'{channel_name}_RBW_readback', channel_number=channel_number))
        channels.append(self.add_channel_sweep_time(f'{channel_name}_sweep_time', channel_number=channel_name))
        return channels

    def add_channel_error(self, channel_name):
        ''''''
        new_channel = channel(channel_name,read_function=lambda: '\n'.join(self.get_errors()))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_error.__doc__)
        return self._add_channel(new_channel)

    def _read_trace_data(self, trace_number, channel_number, complex=False):
        #ascii. TODO binary?
        # Indicates the array data (formatted data array) of NOP 
        # (number of measurement points)×2. Where n is an 
        # integer between 1 and NOP. 
        #  Data(n×2-2) :Data (primary value) at the nth measurement point. 
        #  Data(n×2-1) :Data (secondary value) at the 
        # n-th measurement point. Always 0 when the data 
        # format is not the Smith chart format or the polar 
        # format. 
        # The index of the array starts from 0.
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        resp = self.get_interface().ask(f':CALCulate{channel_number}:SELected:DATA:FDATa?').split(',')
        if not complex:
            return [float(y) for i,y in enumerate(resp) if not i%2]
        else:
            raise Exception('ENA: _read_trace_data: Implement me!')

    def _read_x_data(self, channel_number):
        resp = self.get_interface().ask(f':SENSe{channel_number}:FREQuency:DATA?').split(',')
        return [float(x) for x in resp]

    def add_channel_ydata(self, channel_name, trace_number=1, channel_number=1):
        '''trace data vector'''
        new_channel = channel(channel_name,read_function=lambda trace_number=trace_number, channel_number=channel_number: self._read_trace_data(trace_number, channel_number))
        new_channel.set_attribute('trace_number', trace_number)
        new_channel.set_attribute('channel_type', 'y_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_ydata.__doc__)
        return self._add_channel(new_channel)

    def add_channel_xdata(self, channel_name, channel_number=1):
        '''frequency sweep data vector'''
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._read_x_data(channel_number))
        new_channel.set_attribute('channel_type', 'x_data')
        # new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_xdata.__doc__)
        return self._add_channel(new_channel)

    def add_channel_start_freq(self, channel_name, channel_number=1):
        '''sweep start (low)frequency control'''
        new_channel = channel(channel_name,write_function=lambda freq, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:FREQuency:STARt {freq}'))
        new_channel.add_preset(3)
        new_channel.add_preset(10)
        new_channel.add_preset(100)
        new_channel.add_preset(300)
        new_channel.add_preset(1e3)
        new_channel.add_preset(1e4)
        new_channel.add_preset(1e5)
        new_channel._set_value(float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STARt?')))
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_start_freq.__doc__)
        return self._add_channel(new_channel)

    def add_channel_stop_freq(self, channel_name, channel_number=1):
        '''sweep stop (high) frequency control'''
        new_channel = channel(channel_name,write_function=lambda freq, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:FREQuency:STOP {freq}'))
        new_channel._read = lambda: float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        new_channel.add_preset(1e6)
        new_channel.add_preset(3e6)
        new_channel.add_preset(10e6)
        new_channel.add_preset(30e6)
        new_channel.add_preset(100e6)
        new_channel.add_preset(300e6)
        # new_channel._set_value(float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?')))
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_stop_freq.__doc__)
        return self._add_channel(new_channel)

    def add_channel_points(self, channel_name, channel_number=1):
        '''number of trace data points'''
        new_channel = channel(channel_name,write_function=lambda points, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:SWEep:POINts {points}'))
        new_channel._read = lambda: int(self.get_interface().ask(f':SENSe{channel_number}:SWEep:POINts?'))
        # new_channel._set_value(int(self.get_interface().ask(f':SENSe{channel_number}:SWEep:POINts?')))
        new_channel.add_preset(201)
        new_channel.add_preset(1601)
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_points.__doc__)
        return self._add_channel(new_channel)

    def add_channel_sweep_type(self, channel_name, channel_number=1):
        '''sweept variable control'''
        new_channel = channel(channel_name,write_function=lambda stype, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:SWEep:TYPE {stype}'))
        new_channel._set_value(self.get_interface().ask(f':SENSe{channel_number}:SWEep:TYPE?'))
        new_channel.add_preset('LINear')
        new_channel.add_preset('LOGarithmic')
        new_channel.add_preset('SEGMent')
        new_channel.add_preset('POWer')
        new_channel.add_preset('BIAS')
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_type.__doc__)
        return self._add_channel(new_channel)

    def add_channel_IFBW(self, channel_name, channel_number=1):
        '''IF/resolution bandwidth. TODO: Disrespected when IFBW set to AUTO.'''
        new_channel = channel(channel_name,write_function=lambda rbw, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:BANDwidth:RESolution {rbw}'))
        new_channel._read = lambda: float(self.get_interface().ask(f':SENSe{channel_number}:BANDwidth:RESolution?'))
        # new_channel._set_value(float(self.get_interface().ask(f':SENSe{channel_number}:BANDwidth:RESolution?')))
        new_channel.add_preset(1)
        new_channel.add_preset(5)
        new_channel.add_preset(10)
        new_channel.add_preset(50)
        new_channel.add_preset(100)
        new_channel.add_preset(500)
        new_channel.add_preset(1000)
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_IFBW.__doc__)
        return self._add_channel(new_channel)
    # def add_channel_IFBW_readback(self, channel_name, channel_number=1):
        # '''redback of RBW. May differ from setting because of discretized steps.'''
        # new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: float(self.get_interface().ask(f':SENSe{channel_number}:BANDwidth:RESolution?')))
        # new_channel.set_attribute('channel_type', 'x_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_IFBW_readback.__doc__)
        # return self._add_channel(new_channel)
    # TODO IFBW Auto and Auto Limit control channels.

    def add_channel_sweep_time(self, channel_name ,channel_number=1):
        ''''''
        channel_number = 1 # TODO
        def _set_sweep_time(time, channel_number=channel_number):
            if time == 'AUTO': #TODO seperate auto channel?
                self.get_interface().write(f':SENSe{channel_number}:SWEep:TIME:AUTO ON')
            else:
                self.get_interface().write(f':SENSe{channel_number}:SWEep:TIME:AUTO OFF')
                self.get_interface().write(f':SENSe{channel_number}:SWEep:TIME:DATA {time}')
        new_channel = channel(channel_name,write_function=_set_sweep_time)
        new_channel._read = lambda: float(self.get_interface().ask(f':SENSe{channel_number}:SWEep:TIME:DATA?')) #Auto setting suppressed
        new_channel.add_preset('AUTO')
        new_channel.set_attribute('channel_type', 'x_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_sweep_time.__doc__)
        return self._add_channel(new_channel)

    def add_channel_display(self, channel_name):
        ''''''
        # axis linlog-y, reference level, scale/div, autoscale, division_count, etc
        # trace allocation

    def add_channels_gp_control(self ,channel_name): #todo channl number???
        ''''''
        channels = []
        r_z = channel(f'{channel_name}_R_Z',write_function=lambda z: self.get_interface().write(f':INPut:IMPedance:GPPort:R {z}'))
        r_z._read = lambda: int(float(self.get_interface().ask(f':INPut:IMPedance:GPPort:R?')))
        r_z.set_description(self.get_name() + ': ' + self.add_channels_gp_control.__doc__)
        r_z.add_preset(50)
        r_z.add_preset(1e6)
        channels.append(self._add_channel(r_z))
        
        t_z = channel(f'{channel_name}_T_Z',write_function=lambda z: self.get_interface().write(f':INPut:IMPedance:GPPort:T {z}'))
        t_z._read = lambda: int(float(self.get_interface().ask(f':INPut:IMPedance:GPPort:T?')))
        t_z.set_description(self.get_name() + ': ' + self.add_channels_gp_control.__doc__)
        t_z.add_preset(50)
        t_z.add_preset(1e6)
        channels.append(self._add_channel(t_z))
        
        r_a = channel(f'{channel_name}_R_Atten',write_function=lambda a: self.get_interface().write(f':INPut:ATTenuation:GPPort:R {a}'))
        r_a._read = lambda: int(float(self.get_interface().ask(f':INPut:ATTenuation:GPPort:R?')))
        r_a.set_description(self.get_name() + ': ' + self.add_channels_gp_control.__doc__)
        r_a.add_preset(0)
        r_a.add_preset(20)
        channels.append(self._add_channel(r_a))
        
        t_a = channel(f'{channel_name}_T_Atten',write_function=lambda a: self.get_interface().write(f':INPut:ATTenuation:GPPort:T {a}'))
        t_a._read = lambda: int(float(self.get_interface().ask(f':INPut:ATTenuation:GPPort:T?')))
        t_a.set_description(self.get_name() + ': ' + self.add_channels_gp_control.__doc__)
        t_a.add_preset(0)
        t_a.add_preset(20)
        channels.append(self._add_channel(t_a))

        return channels
    
    def add_channels_bias_control(self, channel_name): #TODO channel number!
        '''bias sweep currently unsupported TODO'''
        channels = []
        def _write_bias_enable_port(p):
            if p == 'Off':
                self.get_interface().write(':SOURce:BIAS:ENABle OFF')
            elif p in ('LFOut', 'P1'):
                self.get_interface().write(f':SOURce:BIAS:PORT {p}')
                self.get_interface().write(':SOURce:BIAS:ENABle ON') #should this really be here and mixed??
            else:
                raise Exception(f'Unexpected channel write value {p}')
        def _read_bias_enable_port():
            en = int(self.get_interface().ask(':SOURce:BIAS:ENABle?'))
            if en:
                port = self.get_interface().ask(':SOURce:BIAS:PORT?')
                if port == 'LFO':
                    port = 'LFOut'
                return port
            else:
                return 'Off' 
        bias_port_en_ch = channel(f'{channel_name}_port', write_function=_write_bias_enable_port)
        bias_port_en_ch._read = _read_bias_enable_port
        bias_port_en_ch.set_description(self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
        bias_port_en_ch.add_preset('Off')
        bias_port_en_ch.add_preset('LFOut', 'G/P source port')
        bias_port_en_ch.add_preset('P1', 'S-param port 1')
        channels.append(self._add_channel(bias_port_en_ch))
        
        bias_voltage_ch = channel(f'{channel_name}_voltage',write_function=lambda v: self.get_interface().write(f':SOURce:BIAS:VOLTage {v}'))
        bias_voltage_ch._read = lambda: float(self.get_interface().ask(':SOURce:BIAS:VOLTage?'))
        bias_voltage_ch.set_description(self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
        bias_voltage_ch.add_preset(0)
        channels.append(self._add_channel(bias_voltage_ch))

        return channels
        
    def add_channels_source_power(self, channel_name, port='GP'): #TODO channel number!
        '''dBm'''
        # NB 460 Continuous switching may damage source. This error occurs when different power ranges are selected in multiple channel measurement settings to avoid source attenuator damage.
        # TODO sync channel powers...
        assert port in ('GP', 1, 2, 3, 4)
        if port == 'GP':
            power_ch = channel(f'{channel_name}',write_function=lambda p: self.get_interface().write(f':SOURce{1}:POWer:GPPort:LEVel:IMMediate:AMPLitude {p}'))
            power_ch._read = lambda: float(self.get_interface().ask(f':SOURce{1}:POWer:GPPort:LEVel:IMMediate:AMPLitude?'))
            power_ch.set_description(self.get_name() + ': ' + self.add_channels_bias_control.__doc__)
            power_ch.add_preset(0)
            power_ch.set_min_write_limit(-45)
            power_ch.set_max_write_limit(10)
            self._add_channel(power_ch)
            return (power_ch,)
        else:
            raise Exception('ENA add_channels_power_source: Implement me')
            # :SOURce{[1]-4}:POWer:PORT{[1]|2}[:LEVel][:IMMediate][:AMPLitude] <numeric>
            # :SOURce{[1]-4}:POWer:PORT{[1]|2}[:LEVel][:IMMediate][:AMPLitude]?
            # :SOURce{[1]-4}:POWer[:LEVel]:SLOPe[:DATA] <numeric>
            # :SOURce{[1]-4}:POWer[:LEVel]:SLOPe[:DATA]?
            # :SOURce{[1]-4}:POWer[:LEVel][:IMMediate][:AMPLitude] <numeric>
            # :SOURce{[1]-4}:POWer[:LEVel][:IMMediate][:AMPLitude]?

    def add_marker(self, channel_name, marker_number, trace_number, channel_number=1):
        ''''''
        channels = []
        assert marker_number in range(1,11)
        m_x = channel(f'{channel_name}_x',write_function=lambda x: self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:X {x}'))
        m_x._read = lambda: float(self.get_interface().ask(f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:X?'))
        m_x.set_description(self.get_name() + ': ' + self.add_marker.__doc__)
        m_x.set_attribute('trace_number', trace_number)
        m_x.set_attribute('marker_number', marker_number)
        channels.append(self._add_channel(m_x))

        m_y = channel(f'{channel_name}_y',read_function=lambda: float(self.get_interface().ask(f':CALCulate{channel_number}:PARameter{trace_number}:SELect;:CALCulate{channel_number}:SELected:MARKer{marker_number}:Y?').split(',')[0]))
        m_y.set_description(self.get_name() + ': ' + self.add_marker.__doc__)
        m_y.set_attribute('trace_number', trace_number)
        m_y.set_attribute('marker_number', marker_number)
        channels.append(self._add_channel(m_y))

        return channels

        # SCPI.CALCulate(1).PARameter(1).SELect
        # SCPI.CALCulate(1).SELected.MARKer(1).ACTivate
        # SCPI.CALCulate(1).SELected.MARKer(1).X = 1E9
        # MkrX = SCPI.CALCulate(1).SELected.MARKer(1).X
        # MkrY = SCPI.CALCulate(1).SELected.MARKer(1).Y
        # SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TYPE = "targ"
        # SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TRACking = True
        # SrchTrac = SCPI.CALCulate(1).SELected.MARKer(1).FUNCtion.TRACking

    def add_channel_trigger(self, channel_name):
        #TODO channel number!
        #todo all-channel controls?
        ''''''
        channel_number = 1
        def _single_abort_trigger_wait(run_mode):
            '''
            channel.write function for the {ENA}_trigger_mode channel.
            
            Configures the ENA to run a continuous measurement sweep or
            triggers a single measurement sweep.
            
            When triggering a single sweep, this function will wait and
            poll a bitfield in the ENA that indicates if a measurement
            is active or not until the measurement is no longer active.
            
            When setting the ENA to continuous sweep, the ENA will be
            set to continuous sweep mode, and this function will return
            control of the program.
            
            Args:
                run_mode (string): Sets the sweep mode of the ENA, must 
                    be "Single" or "Continuous".
                
            Raises:
                Exception: If run_mode is not "Single" or "Continuous"
            '''
            if run_mode not in ['Single', 'Continuous']:
                exception_str = f'ENA: Unknown trigger/run mode {run_mode}. Expected "Single"'
                exception_str += 'or "Continuous"'
                raise Exception(exception_str)
            if run_mode == 'Single':
                self.get_interface().write(':ABORt')
            self.get_interface().write(f':INITiate{channel_number}:CONTinuous ON')
            if run_mode == 'Single':
                expected_time = float(self.get_interface().ask(':SENSe:SWEep:TIME?'))
                self.get_interface().write(f':TRIGger:SOURce BUS')
                self.get_interface().write(f':TRIGger:SINGle')
                datetime_now_str = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                print(f'{datetime_now_str} trigger time. Expected sweep time {expected_time}s.')
            else:
                self.get_interface().write(f':TRIGger:SOURce INTernal')
                print('ENA Continuous sweep activated.')
                return
            status_register = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
            status = (status_register & int('00010000')) >> 4
            # print(f'BEFORE LOOP: Waiting for status 0 (idle). Got {status} ({type(status)})')
            while status:
                time.sleep(0.1) #?!?
                status_register = int(self.get_interface().ask(':STATus:OPERation:CONDition?'))
                status = (status_register & int('00010000')) >> 4
                # print(f'Waiting for status 0 (idle). Got {status} ({type(status)})')
        def _single_write_cb(ch, v):
            # print(f'{ch.get_name()} writtent to {v}')
            if v == 'Single':
                ch._set_value('Stop')
        mode_channel = channel(f'{channel_name}_trigger_mode',write_function=_single_abort_trigger_wait)
        # mode_channel._read = lambda: None #Don't cache value that only has side-effect value
        mode_channel.add_preset('Single')
        mode_channel.add_preset('Continuous')
        mode_channel.add_write_callback(_single_write_cb)
        inital_mode = int(self.get_interface().ask(f':INITiate{channel_number}:CONTinuous?'))
        if inital_mode:
            mode_channel._set_value('Continuous')
        else:
            mode_channel._set_value('Stop') #sort of... It might be finishing the last sweep!
        mode_channel.set_attribute('channel_type', 'trig_control')
        mode_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(mode_channel)
        
        #
        source_channel = channel(f'{channel_name}_trigger_source',write_function=lambda s: self.get_interface().write(f':TRIGger:SEQuence:SOURce {s}'))
        source_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:SOURce?')
        source_channel.add_preset('INTernal')
        source_channel.add_preset('EXTernal')
        source_channel.add_preset('MANual}')
        source_channel.add_preset('BUS}')
        
        source_channel.set_attribute('channel_type', 'trig_control')
        source_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(source_channel)

        slope_channel = channel(f'{channel_name}_trigger_slope',write_function=lambda s: self.get_interface().write(f':TRIGger:SEQuence:EXTernal:SLOPe {s}'))
        slope_channel._read = lambda: self.get_interface().ask(':TRIGger:SEQuence:EXTernal:SLOPe?')
        slope_channel.add_preset('POSitive')
        slope_channel.add_preset('NEGative')
        slope_channel.set_attribute('channel_type', 'trig_control')
        slope_channel.set_description(self.get_name() + ': ' + self.add_channel_trigger.__doc__)
        self._add_channel(slope_channel)

        #todo event, scope, delay
        
        return (mode_channel, source_channel, slope_channel)
        #todo read_delegated blocking / autotrigger??

class keysight_e5061b(keysight_e5061b_base):
    # def __init__(self, interface_visa):
        # super(keysight_e5061b, self).__init__(interface_visa)
    def add_channels(self, channel_name, channel_number=1):
        channels = []
        channels.append(super(keysight_e5061b, self).add_channels(channel_name=channel_name, channel_number=channel_number))
        return channels

    def add_channel_limit(self, channel_name):
        ''''''
        # SCPI.CALCulate(Ch).SELected.LIMit.DATA = Data
        # Data = SCPI.CALCulate(Ch).SELected.LIMit.DATA

    def add_channel_TR_mag(self, channel_name, trace_number, channel_number=1):
        ''''''
        self._check_trace_unconfigured(trace_number=trace_number, channel_number=channel_number)
        channels = []
        channels.append(self.add_channel_ydata(f'{channel_name}', trace_number=trace_number, channel_number=channel_number)) # _ypoints
        channels[-1].set_attribute('measurement', 'T/R Log Magnitude')
        
        stop_f = float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(f':SENSe{channel_number}:FREQuency:STOP 30E+6') #max for G/P port
        float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        self.get_interface().write(f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic') # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine TR') # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN') # {LIN|LOG}
        # return channels
        return channels[0]

    def add_channel_T_mag(self, channel_name, trace_number, channel_number=1):
        ''''''
        self._check_trace_unconfigured(trace_number=trace_number, channel_number=channel_number)
        channels = []
        channels.append(self.add_channel_ydata(f'{channel_name}', trace_number=trace_number, channel_number=channel_number)) # _ypoints
        channels[-1].set_attribute('measurement', 'T Log Magnitude')
        
        stop_f = float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(f':SENSe{channel_number}:FREQuency:STOP 30E+6') #max for G/P port
        float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        self.get_interface().write(f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic') # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine T') # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN') # {LIN|LOG}
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))

    def add_channel_R_mag(self, channel_name, trace_number, channel_number=1):
        ''''''
        self._check_trace_unconfigured(trace_number=trace_number, channel_number=channel_number)
        channels = []
        channels.append(self.add_channel_ydata(f'{channel_name}', trace_number=trace_number, channel_number=channel_number)) # _ypoints
        channels[-1].set_attribute('measurement', 'R Log Magnitude')
        
        stop_f = float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 30e6:
            self.get_interface().write(f':SENSe{channel_number}:FREQuency:STOP 30E+6') #max for G/P port
        float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        self.get_interface().write(f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic') # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine R') # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN') # {LIN|LOG}
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))

    def add_channel_TR_phase(self, channel_name, trace_number, channel_number=1):
        ''''''
        # "3"	"E5061B"	":CALCulate:SELected:FORMat PHASe"	""
        self._check_trace_unconfigured(trace_number=trace_number, channel_number=channel_number)
        channels = []
        channels.append(self.add_channel_ydata(f'{channel_name}', trace_number=trace_number, channel_number=channel_number)) #_ypoints
        channels[-1].set_attribute('measurement', 'T/R Expanded Phase')
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        self.get_interface().write(f':CALCulate{channel_number}:SELected:FORMat UPHase') # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine TR') # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN') # {LIN|LOG}
        # return channels
        return channels[0]
    # channels.append(self.add_channel_ydata(f'{channel_name}_ypoints', trace_number=1, channel_number=channel_number))
    
    def add_channel_rlevel(self, channel_name, channel_number, trace_number):
        ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:RLEVel value
        This command sets/gets the value of the reference division line, for the selected trace (Tr) of the selected channel (Ch).'''
        new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RLEVel {value}'))
        new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RLEVel?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_rlevel.__doc__)
        return self._add_channel(new_channel)

    ##### Seems to just track RLEVEL?.... ####
    # def add_channel_rposition(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:RPOSition value
        # This command specifies the position of a reference division line with its number
        # (an integer assigned starting from 0 from the lowest division),
        # for the selected trace (Tr) of selected channel (Ch).'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RPOSition {int(value)}'))
        # new_channel._read = lambda: int(self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:RPOSition?'))
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_rposition.__doc__)
        # return self._add_channel(new_channel)

    # Doesn't seem to do anything? ....
    # def add_channel_top(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:TOP value
        # This command sets or gets the maximum scale value for the Log-Y Axis.'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:TOP {value}'))
        # new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:TOP?')
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_top.__doc__)
        # return self._add_channel(new_channel)

    # def add_channel_bottom(self, channel_name, channel_number, trace_number):
        # ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:BOTTom value
        # This command sets or gets the minimum scale value for the Log-Y Axis.'''
        # new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:BOTTom {value}'))
        # new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:BOTTom?')
        # new_channel.set_attribute('channel_type', 'Y_control')
        # new_channel.set_description(self.get_name() + ': ' + self.add_channel_bottom.__doc__)
        # return self._add_channel(new_channel)
        
    def add_channel_divisions(self, channel_name, channel_number):
        ''':DISPlay:WINDow{}:Y:SCALe:DIVisions value
        This command sets/gets the number of divisions in all the graphs, for the selected channel (Ch)..'''
        new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:Y:SCALe:DIVisions {value}'))
        new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:Y:SCALe:DIVisions?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_divisions.__doc__)
        return self._add_channel(new_channel)

    def add_channel_pdiv(self, channel_name, channel_number, trace_number):
        ''':DISPlay:WINDow{}:TRACe{}:Y:SCALe:PDIVision value
        For the selected trace (Tr) of selected channel (Ch), when the data format is not the Smith chart format or the polar format, sets the scale per division.
        When the data format is the Smith chart format or the polar format, sets the full scale value (the value of the outermost circumference).'''
        new_channel = channel(channel_name, write_function=lambda value, channel_number=channel_number, trace_number=trace_number: self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:PDIVision {value}'))
        new_channel._read = lambda: self.get_interface().ask(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SCALe:PDIVision?')
        new_channel.set_attribute('channel_type', 'Y_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_pdiv.__doc__)
        return self._add_channel(new_channel)

    def add_channel_sparam(self, channel_name, trace_number, x, y, channel_number=1):
        ''''''
        assert x in range(1,3) # What about 4-port machines?
        assert y in range(1,3) # What about 4-port machines?
        self._check_trace_unconfigured(trace_number=trace_number, channel_number=channel_number)
        channels = []
        channels.append(self.add_channel_ydata(f'{channel_name}', trace_number=trace_number, channel_number=channel_number)) # _ypoints
        channels[-1].set_attribute('measurement', f'S{x}{y} Log Magnitude')
        stop_f = float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        if stop_f > 3e9:
            self.get_interface().write(f':SENSe{channel_number}:FREQuency:STOP 3E+9')
        float(self.get_interface().ask(f':SENSe{channel_number}:FREQuency:STOP?'))
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        self.get_interface().write(f':CALCulate{channel_number}:SELected:FORMat MLOGarithmic') # {MLOGarithmic|PHASe|GDELay| SLINear|SLOGarithmic|SCOMplex|SMITh|SADMittance|PLINear|PLOGarithmic|POLar|MLINear|SWR|REAL| IMAGinary|UPHase|PPHase}
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:DEFine S{x}{y}') # {S11|S21|S12|S22|A|B|R1|R2|TR|T|R}
        self.get_interface().write(f':DISPlay:WINDow{channel_number}:TRACe{trace_number}:Y:SPACing LIN') # {LIN|LOG}
        # return channels
        return channels[0]

    # def add_channel_s_absolute(self, channel_name, trace_number, x, y, channel_number=1):

    def add_channels_calibration(self, channel_name):
        ''''''
        # G/P vs sparam
        # fixture
        # correction status
        # cal type
        # coefficient array
        # port extension
        # edly time
        # ...
        
        
        # To turn ON/OFF error correction, use the following command:
        # :SENS{1-4}:CORR:STAT
        # E5061B
        # 600
        # Also, once you have calculated the calibration coefficient using the :SENS{1-
        # 4}:CORR:COLL:SAVE command, error correction is automatically turned on.
        # When you turn on the error correction, you can check the calibration type
        # actually applied to each trace. To check the calibration type, use the
        # following command:
        # :SENS{1-4}:CORR:TYPE{1-4}?
        # You must follow the steps below to write the calibration coefficient.
        # 1. Declare the calibration type to write.
        # Execute :SENS{1-4}:CORR:COEF:METH:xxxx command
        # 2. Write any calibration coefficient.
        # Execute :SENS{1-4}:CORR:COEF command as needed for the written
        # calibration coefficients
        # 3. Validate the calibration coefficients.
        # Execute :SENS{1-4}:CORR:COEF:SAVE command
        # Do not execute any other command while writing the
        # calibration coefficients. This may cause the system to function
        # incorrectly.
        # To calculate the calibration coefficients using partial overwrite, use the
        # following command:
        # :SENS{1-4}:CORR:COLL:PART:SAVE
        # Before you can calculate the calibration coefficients
        # with the partial overwrite, you must select the appropriate
        # calibration type in the same way used for normal calibration. If
        # calculation of the calibration coefficients is attempted without
        # selecting the calibration type, an error message (28: Invalid
        # Calibration Method) is displayed.

class keysight_e5061b_impedance(keysight_e5061b_base):
    # def __init__(self, interface_visa):
        # super(keysight_e5061b, self).__init__(interface_visa)


    # :SENSe{[1]-4}:Z:METHod <string> 
    # :SENSe{[1]-4}:Z:METHod? 
        # Select one of the following options:
        # P1Reflection:S-Parameter Port 1 reflection measurement
        # (for simple impedance measurement)
        # P2Reflection:S-Parameter Port 2 reflection measurement
        # (for simple impedance measurement)
        # TSERies:S-Parameter series-through measurement (for
        # simple impedance measurement)
        # TSHunt:S-Parameter shunt-through measurement (for
        # PDN component characterization)
        # GSERies:Gain-Phase series-through measurement (for
        # simple impedance measurement)
        # GSHunt:Gain-Phase shunt-through measurement (for
        # PDN component characterization)

    # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine <string>
    # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine?
    # Z|Y|Cp|Cs|Lp|Ls|Rp|Rs|D|Q



    # :SENSe{[1]-4}:Z:COMPensation:COEFficient[:DATA] 
    # {OPEN|SHORt|LOAD}, <numeric 1>, ... ,<numeric NOP×2> 
    # :SENSe{[1]-4}:Z:COMPensation:COEFficient[:DATA]? 
    # {OPEN|SHORt|LOAD} 
    # Query Response 
     # <numeric 1>, ... ,<numeric NOP×2><newline><^END> 
     # Description 
    # <numeric n×2-
    # 1> 
    # Real part of data (complex number) at the n-th 
    # measurement point. 
    # <numeric 
    # n×2> 
    # Imaginary part of data (complex number) at the n-th 
    # measurement point. 
    # :SENSe{[1]-4}:Z:COMPensation:COEFficient:POINts? {OPEN|SHORt|LOAD}
    # Query Response 
    # <numeric><newline><^END>
    # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA] 
    # {OPEN|SHORt|LOAD|LOAD2},<numeric 1>, ... ,<numeric NOP×2> 
    # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA]? 
    # Query Response 
     # <numeric 1>, ... ,<numeric NOP×2><newline><^END> 
     # Description 
    # <numeric n×2-
    # 1> 
    # Real part of data (complex number) at the n-th 
    # measurement point. 
    # <numeric 
    # n×2> 
    # Imaginary part of data (complex number) at the n-th 
    # measurement point. 
    # Because the calibration coefficient array is expressed by a complex 
    # number, the real part and the imaginary part of one measurement point 
    # are returned and obtained as a value. Here, NOP is the number of 
    # measurement points and n is an integer between 1 and NOP. 
    # :SENSe{[1]-4}:Z:METHod <string> 
    # :SENSe{[1]-4}:Z:METHod? 
    # Query Response 
    # <string><newline><^END>
    # :SENSe{[1]-4}:DC:PARameter {DCV|DCI|R|T} 
    # :SENSe{[1]-4}:DC:PARameter? 
    # Query Response 
    # {DCV|DCI|R|T} <newline><^END> 

    def add_channels(self, channel_name, channel_number=1):
        channels = []
        channels.append(super(keysight_e5061b_impedance, self).add_channels(channel_name=channel_name, channel_number=channel_number))
        # TODO more channels
        return channels

    def add_channel_zmethod(self, channel_name, channel_number=1):
        ''''''
        # :SENSe{[1]-4}:Z:METHod <string> 
        # :SENSe{[1]-4}:Z:METHod? 
            # Select one of the following options:
            # P1Reflection:S-Parameter Port 1 reflection measurement
            # (for simple impedance measurement)
            # P2Reflection:S-Parameter Port 2 reflection measurement
            # (for simple impedance measurement)
            # TSERies:S-Parameter series-through measurement (for
            # simple impedance measurement)
            # TSHunt:S-Parameter shunt-through measurement (for
            # PDN component characterization)
            # GSERies:Gain-Phase series-through measurement (for
            # simple impedance measurement)
            # GSHunt:Gain-Phase shunt-through measurement (for
            # PDN component characterization)
        new_channel = channel(channel_name,write_function=lambda zmeth, channel_number=channel_number: self.get_interface().write(f':SENSe{channel_number}:Z:METHod {zmeth}'))
        new_channel._set_value(self.get_interface().ask(f':SENSe{channel_number}:Z:METHod?'))
        new_channel.add_preset('P1Reflection', 'S-Parameter Port 1 reflection measurement (for simple impedance measurement)')
        new_channel.add_preset('P2Reflection', 'S-Parameter Port 2 reflection measurement (for simple impedance measurement)')
        new_channel.add_preset('TSERies', 'S-Parameter series-through measurement (for simple impedance measurement)')
        new_channel.add_preset('TSHunt', 'S-Parameter shunt-through measurement (for PDN component characterization)')
        new_channel.add_preset('GSERies', 'Gain-Phase series-through measurement (for simple impedance measurement)')
        new_channel.add_preset('GSHunt', 'Gain-Phase shunt-through measurement (for PDN component characterization)')
        new_channel.set_attribute('channel_type', 'z_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zmethod.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zparameter(self, channel_name, trace_number=1, channel_number=1):
        ''''''
        # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine <string>
        # :CALCulate{[1]-4}[:SELected]:ZPARameter:DEFine?
        # Z|Y|Cp|Cs|Lp|Ls|Rp|Rs|D|Q
        new_channel = channel(channel_name,write_function=lambda zparam, trace_number=trace_number, channel_number=channel_number: self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect; :CALCulate{channel_number}:SELected:ZPARameter:DEFine {zparam}'))
        self.get_interface().write(f':CALCulate{channel_number}:PARameter{trace_number}:SELect')
        new_channel._set_value(self.get_interface().ask(f':CALCulate{channel_number}:SELected:ZPARameter:DEFine?'))
        new_channel.add_preset('Z', 'Impedance Magnitude')
        new_channel.add_preset('Y', 'Admittance Magnitude')
        new_channel.add_preset('Cp', 'Parallel Capacitance')
        new_channel.add_preset('Cs', 'Series Capacitance')
        new_channel.add_preset('Lp', 'Parallel Inductance')
        new_channel.add_preset('Ls', 'Series Inductance')
        new_channel.add_preset('Rp', 'Parallel Resistance')
        new_channel.add_preset('Rs', 'Series Resistance')
        new_channel.add_preset('D', 'Dissipation Factor')
        new_channel.add_preset('Q', 'Quality Factor')
        # R Resistance
        # X Reactance
        # G Conductance
        # B Susceptance
        # page 342-3
        new_channel.set_attribute('channel_type', 'z_control')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zparameter.__doc__)
        return self._add_channel(new_channel)

    def _parse_complex(self, interleaved_array):
        return [complex(interleaved_array[i], interleaved_array[i+1]) for i in range(0, len(interleaved_array), 2)]

    def add_channel_zcorrection_open(self, channel_name, channel_number=1):
        '''open load complex correction vector'''
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._parse_complex([float(z) for z in self.get_interface().ask(f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? OPEN').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zcorrection_open.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_short(self, channel_name, channel_number=1):
        '''shorted load complex correction vector'''
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._parse_complex([float(z) for z in self.get_interface().ask(f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? SHORt').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zcorrection_short.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_load(self, channel_name, channel_number=1):
        '''50 Ogm load complex correction vector'''
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number: self._parse_complex([float(z) for z in self.get_interface().ask(f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA? LOAD').split(',')]))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zcorrection_load.__doc__)
        return self._add_channel(new_channel)

    def add_channels_impedance_setup(self, channel_name, channel_number=1):
        '''shortcut to add impedance measurment control channels'''
        channels = []
        channels.append(self.add_channel_zmethod(f'{channel_name}_method', channel_number=channel_number))
        channels.append(self.add_channel_zparameter(f'{channel_name}_parameter', trace_number=1, channel_number=channel_number))
        channels.extend(self.add_channels_zcorrection(f'{channel_name}_zcorr', channel_number=channel_number))
        return channels

    def add_channels_zcorrection(self, channel_name, channel_number=1):
        ''''''
        channels = []
        channels.append(self.add_channel_zcorrection_open(f'{channel_name}_open', channel_number=channel_number))
        channels.append(self.add_channel_zcorrection_short(f'{channel_name}_short', channel_number=channel_number))
        channels.append(self.add_channel_zcorrection_load(f'{channel_name}_load', channel_number=channel_number))
        #todo load two low loss C?
        return channels

    def add_channel_zcorrection_collect(self, channel_name, channel_number=1):
        ''''''
        def col_and_wait(cal_type, channel_number):
            old_timeout = self.get_interface().timeout
            self.get_interface().write(f':SENSe{channel_number}:Z:CORRection:COLLect:ACQuire {cal_type}')
            self.get_interface().timeout = 1000
            self.get_interface().ask('*OPC?')
            self.get_interface().timeout = old_timeout
            self.get_interface().write(f':SENSe{channel_number}:Z:CORRection:COLLect:SAVE') #This step seems to be necessary in order to read back the calibration components.
        new_channel = channel(channel_name,write_function=lambda cal_type, channel_number=channel_number: col_and_wait(cal_type,channel_number))
        new_channel.add_preset('OPEN')
        new_channel.add_preset('SHORt')
        new_channel.add_preset('LOAD')
        new_channel.add_preset('LOAD2')
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zcorrection_collect.__doc__)
        return self._add_channel(new_channel)

    def add_channel_zcorrection_write(self, channel_name, channel_number=1):
        '''single channel expects dictionary of OPEN/SHORt/LOAD complex correction vectors. Intended usage to 3-d cal across applied bias, etc'''
        def _write_cal_data(data_dict, channel_number):
            for cal_type in ('OPEN', 'SHORt', 'LOAD'): #LOAD2
                vector_str = ','.join([f'{c.real},{c.imag}' for c in data_dict[cal_type]])
                # :SENSe{[1]-4}:Z:CORRection:COEFficient[:DATA] {OPEN|SHORt|LOAD|LOAD2},<numeric 1>, ... ,<numeric NOP×2>
                self.get_interface().write(f':SENSe{channel_number}:Z:CORRection:COEFficient:DATA {cal_type},{vector_str}')
            self.get_interface().write(f':SENSe{channel_number}:Z:CORRection:COLLect:SAVE')
        new_channel = channel(channel_name,write_function=lambda cal_data, channel_number=channel_number: _write_cal_data(cal_data, channel_number))
        new_channel.set_attribute('channel_type', 'z_cal')
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_zcorrection_write.__doc__)
        return self._add_channel(new_channel)

    def add_channels_impedance_equiv_A(self, channel_name, channel_number=1):
        '''Parallel RLC. Model A - Generally suited to analyze inductors with high core loss.'''
        return self._add_channels_impedance_equiv(channel_name=channel_name, channel_number=channel_number, circuit_topology='A')

    def add_channels_impedance_equiv_B(self, channel_name, channel_number=1):
        '''C parallel R+L. Model B - Generally suited to analyze general inductors and resistors.'''
        return self._add_channels_impedance_equiv(channel_name=channel_name, channel_number=channel_number, circuit_topology='B')
        
    def add_channels_impedance_equiv_C(self, channel_name, channel_number=1):
        '''L series C//R. Model C - Generally suited to analyze resistors with high resistance.'''
        return self._add_channels_impedance_equiv(channel_name=channel_name, channel_number=channel_number, circuit_topology='C')
        
    def add_channels_impedance_equiv_D(self, channel_name, channel_number=1):
        '''Series RLC. Model D - Generally suited to analyze capacitors.'''
        return self._add_channels_impedance_equiv(channel_name=channel_name, channel_number=channel_number, circuit_topology='D')
        
    def add_channels_impedance_equiv_E(self, channel_name, channel_number=1):
        '''C0 parallel Series RLC. Model E - Generally suited to analyze resonators and oscillators.'''
        channels = self._add_channels_impedance_equiv(channel_name=channel_name, channel_number=channel_number, circuit_topology='E')
        channels.append(self._add_channel_impedance_equiv(f'{channel_name}_C0', channel_number=channel_number, circuit_topology='E', component_desig='C0'))
        return channels
        
    def _add_channels_impedance_equiv(self, channel_name, channel_number, circuit_topology):
            self.get_interface().write(f':CALCulate{channel_number}:EPARameters:CIRCuit:TYPE {circuit_topology}')
            self.get_interface().write(f':CALCulate{channel_number}:EPARameters:DISPlay:STATe ON')
            self.get_interface().write(f':CALCulate{channel_number}:EPARameters:SIMulate:AUTO ON')
            # :CALCulate{[1]-4}:EPARameters:SIMulate[:IMMediate]
            channels = []
            channels.append(self._add_channel_impedance_equiv(f'{channel_name}_R1', channel_number=channel_number, circuit_topology=circuit_topology, component_desig='R1'))
            channels.append(self._add_channel_impedance_equiv(f'{channel_name}_C1', channel_number=channel_number, circuit_topology=circuit_topology, component_desig='C1'))
            channels.append(self._add_channel_impedance_equiv(f'{channel_name}_L1', channel_number=channel_number, circuit_topology=circuit_topology, component_desig='L1'))
            return channels
            
    def _add_channel_impedance_equiv(self, channel_name, channel_number, circuit_topology, component_desig):
        ''''''
        # :CALCulate{[1]-4}:EPARameters:CIRCuit:B:C1?
        calc_cmd = f':CALCulate{channel_number}:EPARameters:EXECute; '
        new_channel = channel(channel_name,read_function=lambda channel_number=channel_number, circuit_topology=circuit_topology, component_desig=component_desig: float(self.get_interface().ask(f'{calc_cmd}:CALCulate{channel_number}:EPARameters:CIRCuit:{circuit_topology}:{component_desig}?')))
        new_channel.set_attribute('channel_type', 'z_equiv')
        new_channel.set_attribute('topology', 'circuit_topology')
        new_channel.set_description(self.get_name() + ': ' + self._add_channel_impedance_equiv.__doc__)
        return self._add_channel(new_channel)

# :SENSe1:Z:COMPensation:COEFficient:DATA? OPEN
# :SENSe1:Z:COMPensation:COEFficient:DATA? SHORt
# :SENSe1:Z:COMPensation:COEFficient:DATA? LOAD

# :SENSe1:Z:COMPensation:COEFficient:POINts? OPEN
# :SENSe1:Z:COMPensation:COEFficient:POINts? SHORt
# :SENSe1:Z:COMPensation:COEFficient:POINts? LOAD

# :SENSe1:Z:CORRection:COEFficient:DATA? 
# :SENSe1:Z:CORRection:COEFficient:DATA? {OPEN|SHORt|LOAD|LOAD2}
# :SENSe1:Z:CORRection:COEFficient:DATA? LOAD
# :SENSe1:Z:CORRection:COEFficient:DATA? 
# :SENSe1:CORRection:COEFficient:DATA?
# :SENSe1:CORRection:COEFficient:GPData?
    
    # TODO!
    # log-y control
    # attenuator control
    # GP/Sparam switch
    # GP impedance/atten switch
    # transmit power control
    # S param (not Z) calibration vectors
    
    #swept bias controls
    #dc bias controls
    
    #Marker controls page 1077
    
    #update sync to sweep rate
    
    #sore and load bias-dependent cal vectors to synthesize 2d sweep
    
    # :SENSe{[1]-4}:Z:CORRection:COLLect[:ACQuire]
    # {OPEN|SHORt|LOAD|LOAD2}
    
    
    
    
    # :SENSe{[1]-4}:FREQuency:DATA? 
# Query response 
# {numeric 1},… ,{numeric NOP}<newline><^END> 
# :SENSe{[1]-4}:FREQuency[:CW|FIXed] <numeric> 
# :SENSe{[1]-4}:FREQuency[:CW|FIXed]? 
# Query response 
# {numeric}<newline><^END>

# :SENSe{[1]-4}:DC:MEASure:DATA? 
# Query Response 
# {numeric} <newline><^END>
# :SENSe{[1]-4}:DC:MEASure:ENABle {ON|OFF|1|0} 
# :SENSe{[1]-4}:DC:MEASure:ENABle?


#read manual page 627

#page 906
#  SCPI.CALCulate(Ch).SELected.DATA.FDATa 
# :CALCulate{[1]-4}[:SELected]:DATA:FDATa <numeric1>,… ,<numeric 
# NOP×2> 
# :CALCulate{[1]-4}[:SELected]:DATA:FDATa?

#  SCPI.CALCulate(Ch).SELected.DATA.FMEMory 
# :CALCulate{[1]-4}[:SELected]:DATA:FMEMory <numeric 1>,… ,<numeric 
# NOP×2> 
# :CALCulate{[1]-4}[:SELected]:DATA:FMEMory? 
# Query response 
# {numeric 1},… ,{numeric NOP×2}<newline><^END> 

#  SCPI.CALCulate(Ch).SELected.DATA.SDATa 
# :CALCulate{[1]-4}[:SELected]:DATA:SDATa <numeric 1>,… ,<numeric 
# NOP×2> 
# :CALCulate{[1]-4}[:SELected]:DATA:SDATa?

#  SCPI.CALCulate(Ch).SELected.DATA.SMEMory 
# :CALCulate{[1]-4}[:SELected]:DATA:SMEMory <numeric 1>,… ,<numeric 
# NOP×2> 
# :CALCulate{[1]-4}[:SELected]:DATA:SMEMory? 

# :CALCulate{[1]-4}[:SELected]:DATA:XAXis?

