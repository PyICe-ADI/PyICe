from ..lab_core import *
import tempfile, struct

class saleae(instrument, delegator):
    '''analog DAQ intrument using Saleae Logic Pro hardware.
    Requires https://pypi.python.org/pypi/saleae
    Also requires Saleae Logic software GUI to be running to listen on TCP remote control port.
    Digital channels not supported (yet). (Mixed analog/digital capture file binary unsupported.)'''
    def __init__(self,host='localhost', port=10429):
        import saleae as saleae_lib
        instrument.__init__(self,f"Saleae Logic @ {host}:{port}")
        delegator.__init__(self)
        self._saleae = saleae_lib.Saleae(host,port)
        self._channels = []
        self.set_num_samples(100)
        self.set_sample_rates() #max rate
    def set_num_samples(self, num_samples_per_channel):
        '''set number of samples to average and sample rate
        because valid sample rates change with ???number of configured channels???, may need to call after adding all channels.'''
        self._saleae.set_num_samples(num_samples_per_channel)
    def get_sample_rates(self):
        return [i[1] for i in self._saleae.get_all_sample_rates()] # why throw out analog rates Dave?
    def set_sample_rates(self, sample_rates=None):
        available_rates = self._saleae.get_all_sample_rates()
        if sample_rates is None:
            self._saleae.set_sample_rate(available_rates[0])
        else:
            if sample_rates in available_rates:
                self._saleae.set_sample_rate(sample_rates)
            else:
                raise(f"\n\nSaleae: Sorry I can't support the sample rates {sample_rates}.\n\n")
        return self.get_sample_rates()
    def _set_active_channels(self):
        self._saleae.set_active_channels(digital=[],analog=self._channels)
    def add_channel_scalar(self,channel_name, channel_number, scaling=1.0):
        '''Add analog scalar (DMM) DAQ channel to instrument.
        channel_number is 0-7 or 0-15 for Logic Pro 8 and Logic Pro 16 respectively.'''
        assert isinstance(channel_number,int)
        assert channel_number < 16
        assert channel_number not in self._channels
        new_channel = channel(channel_name,read_function=lambda: self._dummy_read(channel_number))
        new_channel.set_attribute('channel',channel_number)
        new_channel.set_attribute('type','scalar')
        new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        self._channels.append(channel_number)
        self._set_active_channels()
        return self._add_channel(new_channel)
    def add_channel_trace(self,channel_name, channel_number, scaling=1.0):
        '''Add analog vector trace (scope) DAQ channel to instrument.
        channel_number is 0-7 or 0-15 for Logic Pro 8 and Logic Pro 16 respectively.'''
        assert isinstance(channel_number,int)
        assert channel_number < 16
        assert channel_number not in self._channels
        new_channel = channel(channel_name,read_function=lambda: self._dummy_read(channel_number))
        new_channel.set_attribute('channel',channel_number)
        new_channel.set_attribute('type','vector')
        new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel.__doc__)
        self._channels.append(channel_number)
        self._set_active_channels()
        return self._add_channel(new_channel)
    def _dummy_read(self, index):
        raise Exception("Shouldn't be here...")
    def _read_from_file(self, file, bytes, timeout=10):
        '''intermittently, data is slow to flush to disk...'''
        start_time = time.time()
        str = file.read(bytes)
        while len(str) < bytes:
            if (time.time() - start_time) > timeout:
                raise Exception('Saleae communication failure')
            str += file.read(bytes-len(str))
        return str
    def read_delegated_channel_list(self,channels):
        '''private'''
        results_dict = results_ord_dict()
        temp_dir = tempfile.mkdtemp(prefix='saleae_tmp')
        temp_file = temp_dir + '\\capture.logicdata'
        print(temp_file)
        self._saleae.capture_start()
        while not self._saleae.is_processing_complete():
            pass
        ch_list = [ch.get_attribute('channel') for ch in channels]
        self._saleae.export_data2(temp_file, digital_channels=[], analog_channels=ch_list, format='binary') #
        while not self._saleae.is_processing_complete():
            pass
        with open(temp_file + '.bin', mode='rb', buffering=0) as logicdata:
            num_samples_per_channel = struct.unpack('<Q', self._read_from_file(logicdata, 8))[0]
            num_channels = struct.unpack('<L',self._read_from_file(logicdata, 4))[0]
            sample_period = struct.unpack('<d',self._read_from_file(logicdata, 8))[0]
            assert len(channels) == num_channels
            for channel in channels:
                if channel.get_attribute('type') == 'scalar':
                    channel_avg = 0
                    for sample in range(num_samples_per_channel):
                        channel_avg += struct.unpack('<f',self._read_from_file(logicdata, 4))[0]
                    channel_avg /= num_samples_per_channel
                    results_dict[channel.get_name()] = channel_avg
                elif channel.get_attribute('type') == 'vector':
                    channel_data = []
                    for sample in range(num_samples_per_channel):
                        channel_data.append(struct.unpack('<f',logicdata.read(4))[0])
                    results_dict[channel.get_name()] = channel_data
                else:
                    raise Exception('Bad "type" channel attribute.')
            logicdata.close()
        os.remove(temp_file + '.bin')
        os.rmdir(temp_dir)
        return results_dict