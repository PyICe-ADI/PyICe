'''
Channel Wrapper for SPI Devices
===============================
'''
from PyICe.lab_core import instrument, delegator, integer_channel
from PyICe import spi_interface

class spiInstrument(instrument, delegator):
    '''Instrument wrapper for basic linear shift register SPI port.
    Not appropriate for context-sensitive (sub addressed) memory directly.
    Instead, use multiple spiInstrument copies with appropriate preamble_clk_cnt and preamble_data settings.'''
    def __init__(self, name, spiInterface, write_shift_register=None, read_shift_register=None, preamble_clk_cnt=0, preamble_data=0):
        '''Specify at lease one of (write_shift_register, read_shift_register arguments).
        If read data has the same meaning as write data (memory read-back), send same shift register object to write_shift_register and read_shift_register arguments.
        If both (write_shift_register, read_shift_register) arguments are specified, they must be of the same length.'''
        delegator.__init__(self)
        instrument.__init__(self, '{} SPI instrument wrapper'.format(name))
        self._base_name = name
        assert isinstance(spiInterface, spi_interface.spiInterface)
        self.spi_interface = spiInterface
        self.write_shift_register = write_shift_register
        self.read_shift_register = read_shift_register
        self.preamble_clk_cnt = preamble_clk_cnt
        self.preamble_data = preamble_data
        assert self.spi_interface._check_size(self.preamble_data, self.preamble_clk_cnt)
        self.dummy_write_value = 0 #data to shift in if SPI is read-only
        self._transceive_enabled = True
        if self.write_shift_register is None and self.read_shift_register is None:
            raise Exception('spiInstrument must specify at least one of write_shift_register, read_shift_register')
        if self.write_shift_register is self.read_shift_register:
            #channel name conflict
            self.read_shift_register = spi_interface.shift_register()
            for bf in read_shift_register:
                new_name = '{}_readback'.format(bf)
                print("WARNING: {} bit field: {} readback renamed to: {} to avoid duplicated channel name.".format(name, bf, new_name))
                self.read_shift_register.add_bit_field(new_name, read_shift_register[bf], 'readback: {}'.format(read_shift_register.get_description(bf)))
        elif self.write_shift_register is not None and self.read_shift_register is not None:
            if len(self.write_shift_register) != len(self.read_shift_register):
                raise Exception('spiInstrument write_shift_register, read_shift_register must be of equal length')
        if self.write_shift_register is not None:
            assert isinstance(self.write_shift_register, spi_interface.shift_register)
            for bf in self.write_shift_register:
                write_ch = integer_channel(name = bf, size = self.write_shift_register[bf], 
                                           write_function = lambda write_data, channel_name=bf: self._transceive(write_channel_name=channel_name, data=write_data))
                write_ch.set_delegator(self)
                write_ch.set_description(self.write_shift_register.get_description(bf))
                self._add_channel(write_ch)
        if self.read_shift_register is not None:
            assert isinstance(self.read_shift_register, spi_interface.shift_register)
            for bf in self.read_shift_register:
                read_ch = integer_channel(name = bf, size = self.read_shift_register[bf], read_function = self._dummy_read)
                read_ch.set_delegator(self)
                read_ch.set_description(self.read_shift_register.get_description(bf))
                self._add_channel(read_ch)
    def add_channel_transceive_enable(self, channel_name):
        '''Add channel to enable/disable SPI port communication.
        This can be used to serially change multiple bit fields before sending the data to the SPI slave with a single transaction.
        Note that communication is disabled independent of this setting if not all writable bit fields have been initialized.
        Also note that after communication is enabled, a SPI transceive will not take place until a bit field is read or written.'''
        trans_en_ch = integer_channel(name=channel_name, size=1, write_function=lambda enable: setattr(self, '_transceive_enabled', enable))
        trans_en_ch.set_description(self.get_name() + ': ' + self.add_channel_transceive_enable.__doc__)
        trans_en_ch.write(self._transceive_enabled)
        return self._add_channel(trans_en_ch)
    def _transceive(self, write_channel_name=None, data=None, no_transceive=False):
        write_data = {}
        for channel in self:
            if channel.is_writeable():
                write_data[channel.get_name()] = channel.read_without_delegator()
        if write_channel_name is not None:
            write_data[write_channel_name] = data
        if no_transceive or not self._transceive_enabled:
            #skip SPI transaction
            if self.read_shift_register is not None:
                read_data = {bf: None for bf in self.read_shift_register}
            else:
                read_data = {}
        elif None in list(write_data.values()):
            #skip SPI transaction
            print("Deferring {} SPI write until all writable channels are assigned values.".format(write_channel_name))
            for ch in write_data:
                print('\t{}:{}'.format(ch,write_data[ch]))
            if self.read_shift_register is not None:
                read_data = {bf: None for bf in self.read_shift_register}
            else:
                read_data = {}
        else:
            #doing SPI transaction
            if self.write_shift_register is None:
                miso = self.spi_interface.transceive((self.preamble_data << len(self.read_shift_register)) + self.dummy_write_value, self.preamble_clk_cnt+len(self.read_shift_register))
            else:
                data, clkcnt = self.write_shift_register.pack(write_data)
                data += self.preamble_data << clkcnt
                clkcnt += self.preamble_clk_cnt
                miso = self.spi_interface.transceive(data,clkcnt)
            if self.read_shift_register is not None:
                read_data = self.read_shift_register.unpack(miso)
            else:
                read_data = {}
        merged_data = {}
        merged_data.update(write_data)
        merged_data.update(read_data)
        return merged_data
    def _dummy_read(self):
        raise Exception("Shouldn't ever get here...")
    def read_delegated_channel_list(self,channels):
        '''private'''
        results_dict = {}
        spi_data = None
        for channel in channels:
            if not channel.is_writeable(): #read channel in list; need to do spi transaction
                spi_data = self._transceive()
                break
        if spi_data is None: #only writable channels; skip spi transaction
            spi_data = self._transceive(no_transceive=True)
        for channel in channels:
            results_dict[channel.get_name()] = channel.read_without_delegator(force_data = True, data = spi_data[channel.get_name()])
        return results_dict