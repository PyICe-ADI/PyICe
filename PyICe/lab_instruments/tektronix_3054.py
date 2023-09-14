from ..lab_core import *
import time

class tektronix_3054(scpi_instrument,delegator):
    '''Tek 4-channel DSO'''
    def __init__(self, interface_visa, force_trigger=True):
        '''interface_visa"'''
        self._base_name = 'tektronix_3054'
        delegator.__init__(self)
        scpi_instrument.__init__(self,f"tektronix_3054 @ {interface_visa}")
        self.add_interface_visa(interface_visa,timeout=10)
        self.get_interface().write(('DATA:ENCdg ASCIi'))
        self.get_interface().write(('DATA:WID 2'))
        self.get_interface().write(('HEADER 1')) #data headers help parse results of wfmoutpre? query, since different scopes return different length responses!
        self.force_trigger = force_trigger
    def add_channel_time(self,channel_name):
        time_channel = channel(channel_name, read_function=self._read_scope_time)
        time_channel.set_delegator(self)
        return self._add_channel(time_channel)
    def add_channel(self,channel_name,scope_channel_number):
        '''Add named channel to instrument.  num is 1-4.'''
        assert isinstance(scope_channel_number, int)
        scope_channel = channel(channel_name,read_function=lambda: self._read_scope_channel(scope_channel_number))
        scope_channel.set_delegator(self)
        return self._add_channel(scope_channel)
    def add_channel_dvm(self, channel_name, scope_channel_number, measurement_time=2, mode='DC'):
        assert isinstance(scope_channel_number, int)
        mode = mode.upper()
        assert mode in ['ACRMS', 'ACDCRMS', 'DC', 'FREQ', 'FREQUENCY'] #'OFF'
        dvm_channel = channel(channel_name,read_function=lambda measurement_time=measurement_time: self._read_dvm_channel(scope_channel_number, measurement_time, mode))
        dvm_channel.set_delegator(self)
        dvm_channel.read_without_delegator(measurement_time=0) #set up DMM configuration so that first reading isn't bogus with measurement_time=0 (single channel usage)
        return self._add_channel(dvm_channel)
    def trigger_force(self):
        '''Creates a trigger event. If TRIGger:STATE is set to READy, the acquisition
        will complete. Otherwise, this command will be ignored.'''
        self.get_interface().write(('TRIGger FORCe'))
    def _read_scope_time(self):
        '''
        Data conversion:
        voltage = [(data value - yreference) * yincrement] + yorigin
        time = [(data point number - xreference) * xincrement] + xorigin
        '''
        self.get_interface().write(('WFMPRE?'))
        preamble = self.get_interface().read().split(';')
        preamble[0] = preamble[0].split(':')[-1] #remove junk that doesn't really belong to first field
        preamble_dict = {}
        for field in preamble:
            name, value = field.split(' ', 1)
            preamble_dict[name] = value
        preamble_dict['NR_PT'] = int(preamble_dict['NR_PT'])
        preamble_dict['XINCR'] = float(preamble_dict['XINCR'])
        preamble_dict['PT_OFF'] = float(preamble_dict['PT_OFF'])
        preamble_dict['XZERO'] = float(preamble_dict['XZERO'])
        xpoints = [(x - preamble_dict['PT_OFF'])*preamble_dict['XINCR']+preamble_dict['XZERO'] for x in range(preamble_dict['NR_PT'])]
        return xpoints
    def _read_scope_channel(self,scope_channel_number):
        '''return list of y-axis points for named channel
            list will be datalogged by logger as a string in a single cell in the table
            trigger=False can by used to suppress acquisition of new data by the instrument so that
            data from a single trigger may be retrieved from each of the four channels in turn by read_channels()
        '''
        #trigger / single arm sequence commands need investigation.  Forcing trigger here is not correct
        # if trigger:
            # self.get_interface().write(('TRIGger'))

        # Examples WFMOUTPRE? ? might return the waveform formatting data as:
        #  [0] :WFMOUTPRE:BYT_NR 2;
        #  [1] BIT_NR 16;
        #  [2] ENCDG ASCII;
        #  [3] BN_FMT RI;
        #  [4] BYT_OR MSB;
        #  [5] WFID "Ch1, DC coupling, 100.0mV/div, 4.000us/div, 10000 points, Sample mode";
        #  [6] NR_PT 10000;
        #  [7] PT_FMT Y;
        #  [8] XUNIT "s";
        #  [9] XINCR 4.0000E-9;
        # [10] XZERO - 20.0000E-6;
        # [11] PT_OFF 0;
        # [12] YUNIT "V";
        # [13] YMULT 15.6250E-6;
        # [14] YOFF :"6.4000E+3;
        # [15] YZERO 0.0000

        self.get_interface().write((f'DATA:SOUrce CH{scope_channel_number}'))
        preamble = self.get_interface().ask('WFMPRE?').split(';')
        preamble[0] = preamble[0].split(':')[-1] #remove junk that doesn't really belong to first field
        preamble_dict = {}
        for field in preamble:
            name, value = field.split(' ', 1)
            preamble_dict[name] = value
        preamble_dict['YMULT'] = float(preamble_dict['YMULT']) #scale int to volts
        preamble_dict['YZERO'] = float(preamble_dict['YZERO']) #offset set into scope, subtract from raw_data before scaling if you want data offset
        preamble_dict['YOFF'] = float(preamble_dict['YOFF']) #waveform position
        raw_data = self.get_interface().ask(('CURVe?'))
        raw_data = raw_data.split(',')
        #not sure where y_zero goes in eqn! #offset seems to be display only
        raw_data[0] = raw_data[0].split(' ')[-1]
        data = [(int(x)-preamble_dict['YOFF'])*preamble_dict['YMULT']+preamble_dict['YZERO'] for x in raw_data]
        #TODO - implement binary transfer if speed becomes a problem
        return data
    def _read_dvm_channel(self,scope_channel_number,measurement_time, mode):
        '''return DVM voltage for selected channel'''
        self.get_interface().write((f'DVM:SOUrce CH{scope_channel_number}'))
        self.get_interface().write((f'DVM:MODE {mode}'))
        time.sleep(measurement_time)
        raw_data = self.get_interface().ask(('DVM:MEASUrement:VALue?'))
        raw_data = raw_data.split()
        return float(raw_data[1])
    def read_delegated_channel_list(self,channels):
        if self.force_trigger:
            self.trigger_force()
        results = results_ord_dict()
        for channel in channels:
            results[channel.get_name()] = channel.read_without_delegator()
        return results
