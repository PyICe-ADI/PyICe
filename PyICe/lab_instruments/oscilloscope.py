from ..lab_core import *
import time
import struct
import abc

try:
    from numpy import fromiter, dtype
    numpy_missing = False
except ImportError as e:
    numpy_missing = True

class oscilloscope(scpi_instrument, delegator):
    pass
    # binary unpack
    # scaling
    # trigger status polling / timeout (force trigger)
    
    def fetch_waveform_data(self):
        # assumes :WAVeform:SOURce set correctly before call!
        self.get_interface().write(':WAVeform:DATA?')
        raw_data = self.get_interface().read_raw()
        #Example: "#800027579 4.03266e-002, 1.25647e-004, 1.25647e-004, 1.25647e-004,......."
        # Since bytes objects are sequences of integers (akin to a tuple), for a bytes object b, b[0] will be an integer, while b[0:1] will be a bytes object of length 1. (This contrasts with text strings, where both indexing and slicing will produce a string of length 1)
        assert raw_data[0:1] == b'#'
        raw_data_header_length = int(raw_data[1:2])
        raw_data_length_bytes = int(raw_data[2:raw_data_header_length+2])
        raw_data = raw_data[raw_data_header_length+2:] #remove header
        
        data_format = self.get_interface().ask(':WAVeform:FORMat?')
        if data_format == 'WORD':
            byte_order = self.get_interface().ask(':WAVeform:BYTeorder?')
            byte_type = self.get_interface().ask(':WAVeform:UNSigned?')
            if int(byte_type) == 1:
                fmt_str = 'H'
            elif int(byte_type) == 0:
                fmt_str = 'h'
            else:
                raise Exception("I'm lost. Contact PyICe-developers@analog.com for more information.")
            assert len(raw_data[:-1]) % 2 == 0 #Remove trailing newline; data should be even number of bytes.
            if byte_order == 'LSBF':
                data = struct.unpack(f'<{fmt_str*(len(raw_data[:-1])//2)}', raw_data[:-1])
            elif byte_order == 'MSBF':
                data = struct.unpack(f'>{fmt_str*(len(raw_data[:-1])//2)}', raw_data[:-1])
            else:
                raise Exception('Unknown WORD byte order. Contact PyICe-developers@analog.com for more information.')
            data = self.scale_waveform_data(data)
        elif data_format == 'BYTE':
            byte_type = self.get_interface().ask(':WAVeform:UNSigned?')
            if int(byte_type) == 1:
                fmt_str = 'B'
            elif int(byte_type) == 0:
                fmt_str = 'b'
            else:
                raise Exception("I'm lost. Contact PyICe-developers@analog.com for more information.")
            data = struct.unpack(f'{fmt_str*len(raw_data[:-1])}', raw_data[:-1])
            data = self.scale_waveform_data(data)
        elif data_format == 'ASC':
            raw_data = raw_data.decode(encoding='latin-1').split(',')
            data = [float(x) for x in raw_data]
            print(list(data)[:100])
        else:
            raise Exception(f'Unknown data format: {data_format}. Contact PyICe-developers@analog.com for more information.')
        return data
        
    def scale_waveform_data(self, data):
        # Data Conversion
        # Word or byte data sent from the oscilloscope must be scaled for useful
        # interpretation. The values used to interpret the data are the X and Y references, X
        # and Y origins, and X and Y increments. These values are read from the waveform
        # preamble. Each channel has its own waveform preamble.
        # In converting a data value to a voltage value, the following formula is used:
        # voltage = [(data value - yreference) * yincrement] + yorigin
        # If the :WAVeform:FORMat data format is ASCii (see page 1371), the data values
        # are converted internally and sent as floating point values separated by commas.
        # In converting a data value to time, the time value of a data point can be
        # determined by the position of the data point. For example, the fourth data point
        # sent with :WAVeform:XORigin = 16 ns, :WAVeform:XREFerence = 0, and
        # :WAVeform:XINCrement = 2 ns, can be calculated using the following formula:
        # time = [(data point number - xreference) * xincrement] + xorigin
        # This would result in the following calculation for time bucket 3:
        # time = [(3 - 0) * 2 ns] + 16 ns = 22 ns
        # In :ACQuire:TYPE PEAK mode (see page 307), because data is acquired in
        # max-min pairs, modify the previous time formula to the following:
        # time=[(data pair number - xreference) * xincrement * 2] + xorigin
        # preamble = self.get_interface().ask(':WAVeform:PREamble?')
        # (fmt, typ, points, count, xincrement, xorigin, xreference, yincrement, yorigin, yreference) = preamble.split(',')
        # # fmt = int(fmt)
        # # typ = int(typ)
        # # points = int(points)
        # # count = int(count)
        # # xincrement = float(xincrement)
        # # xorigin = float(xorigin)
        # # xreference = int(xreference)
        # yincrement = float(yincrement)
        # yorigin = float(yorigin)
        # yreference = int(yreference)
        waveform_scaling = self.get_waveform_scaling()
        data = map(lambda pt: ((pt - waveform_scaling['yreference']) * waveform_scaling['yincrement']) + waveform_scaling['yorigin'], data)
        if not numpy_missing:
            return fromiter(data,dtype=dtype('<d'))         ## This will cause trouble if _set_type_affinity('BLOB') isn't on.
        return list(data)
        
    def get_waveform_scaling(self):
        ### Requires Waveform Source to be previously set
        waveform_scaling={}
        preamble = self.get_interface().ask(':WAVeform:PREamble?')
        (waveform_scaling['fmt'], waveform_scaling['typ'], points, count, xincrement, xorigin, xreference, yincrement, yorigin, yreference) = preamble.split(',')
        waveform_scaling['yincrement'] = float(yincrement)
        waveform_scaling['yorigin'] = float(yorigin)
        waveform_scaling['yreference'] = int(yreference)
        
        return waveform_scaling

    @abc.abstractmethod
    def setup_channels(self, scope_channels):
        '''Helper method to set up each specific waveform channel in scope_channels list and call add_all_timebase_trigger_aquisition_channels'''

    @abc.abstractmethod
    def enable_channels(self, channels):
        '''Turn on Y channels in the channels list'''
    
    @abc.abstractmethod
    def disable_all_Ychannels(self):
        '''Turn off all Y channels'''

    @abc.abstractmethod
    def resync_scope():
        '''Reset the scope and reconfigure physical instrument to desired used channels.'''

    @abc.abstractmethod
    def add_Ychannel_waveform(self, name, number):
        '''Add named waveform channel and add Ycontrol and Yreadback channels for that waveform channel'''

    @abc.abstractmethod
    def add_Ycontrol_Yreadback_channels(self, name, number):
        '''Add all control and readback channels for the specified Y waveform channel.'''

    @abc.abstractmethod
    def add_Xcontrol_Xreadback_channels(self, prefix):
        '''Add all X control and readback channels'''

    @abc.abstractmethod
    def add_trigger_channels(self, prefix):
        '''Add all trigger control channels.'''

    @abc.abstractmethod
    def add_aquire_channels(self, prefix):
        '''Add all channels the control the scope aquisition channel'''

    @abc.abstractmethod
    def add_channel_timebase(self,name):
        '''Add time channel that stores the x-axis data points in seconds'''

    @abc.abstractmethod
    def add_all_timebase_trigger_aquisition_channels(self, prefix):
        '''Helper method to easily add time base, X control, X readback, trigger, and aquisition channels'''
    
    # SCPI syntax taken from DSOX3034T programmer manual. May differ from other MSO/DSO Keysight scopes and different manufacturer scopes.
    
    # Command Syntax :WAVeform:BYTeorder <value>
        # <value> ::= {LSBFirst | MSBFirst}
        # The :WAVeform:BYTeorder command sets the output sequence of the WORD data.
            # • MSBFirst — sets the most significant byte to be transmitted first.
            # • LSBFirst — sets the least significant byte to be transmitted first.
        # This command affects the transmitting sequence only when :WAVeform:FORMat
        # WORD is selected.
        # The default setting is MSBFirst.
    # Query Syntax :WAVeform:BYTeorder?
        # The :WAVeform:BYTeorder query returns the current output sequence.
        # Return Format <value><NL>
        # <value> ::= {LSBF | MSBF}

    # :WAVeform:COUNt
        # (see page 1572)
    # Query Syntax :WAVeform:COUNt?
        # The :WAVeform:COUNT? query returns the count used to acquire the current
        # waveform. This may differ from current values if the unit has been stopped and its
        # configuration modified. For all acquisition types except average, this value is 1.
        # Return Format <count_argument><NL>
        # <count_argument> ::= an integer from 1 to 65536 in NR1 format

    # :WAVeform:DATA
        # (see page 1572)
    # Query Syntax :WAVeform:DATA?
        # The :WAVeform:DATA query returns the binary block of sampled data points
        # transmitted using the IEEE 488.2 arbitrary block data format. The binary data is
        # formatted according to the settings of the :WAVeform:UNSigned,
        # :WAVeform:BYTeorder, :WAVeform:FORMat, and :WAVeform:SOURce commands.
        # The number of points returned is controlled by the :WAVeform:POINts command.
        # In BYTE or WORD waveform formats, these data values have special meaning:
            # • 0x00 or 0x0000 — Hole. Holes are locations where data has not yet been
                # acquired.
                # Another situation where there can be zeros in the data, incorrectly, is when
                # programming over telnet port 5024. Port 5024 provides a command prompt
                # and is intended for ASCII transfers. Use telnet port 5025 instead.
            # • 0x01 or 0x0001 — Clipped low. These are locations where the waveform is
                # clipped at the bottom of the oscilloscope display.
            # • 0xFF or 0xFFFF — Clipped high. These are locations where the waveform is
                # clipped at the top of the oscilloscope display.
                # Return Format <binary block data><NL>


    # :WAVeform:FORMat
        # (see page 1572)
    # Command Syntax :WAVeform:FORMat <value>
        # <value> ::= {WORD | BYTE | ASCii}
        # The :WAVeform:FORMat command sets the data transmission mode for waveform
        # data points. This command controls how the data is formatted when sent from the
        # oscilloscope.
        # • ASCii formatted data converts the internal integer data values to real Y-axis
            # values. Values are transferred as ASCii digits in floating point notation,
            # separated by commas.
            # ASCII formatted data is transferred ASCii text.
        # • WORD formatted data transfers 16-bit data as two bytes. The
            # :WAVeform:BYTeorder command can be used to specify whether the upper or
            # lower byte is transmitted first. The default (no command sent) is that the upper
            # byte transmitted first.
        # • BYTE formatted data is transferred as 8-bit bytes.
        # When the :WAVeform:SOURce is the serial decode bus (SBUS1 or SBUS2), ASCii
            # is the only waveform format allowed.
            # When the :WAVeform:SOURce is one of the digital channel buses (BUS1 or BUS2),
            # ASCii and WORD are the only waveform formats allowed.
    # Query Syntax :WAVeform:FORMat?
        # The :WAVeform:FORMat query returns the current output format for the transfer of
        # waveform data.
        # Return Format <value><NL>
        # <value> ::= {WORD | BYTE | ASC}

    # :WAVeform:FORMat
    # (see page 1572)
    # Command Syntax :WAVeform:FORMat <value>
    # <value> ::= {WORD | BYTE | ASCii}
    # The :WAVeform:FORMat command sets the data transmission mode for waveform
    # data points. This command controls how the data is formatted when sent from the
    # oscilloscope.
    # • ASCii formatted data converts the internal integer data values to real Y-axis
    # values. Values are transferred as ASCii digits in floating point notation,
    # separated by commas.
    # ASCII formatted data is transferred ASCii text.
    # • WORD formatted data transfers 16-bit data as two bytes. The
    # :WAVeform:BYTeorder command can be used to specify whether the upper or
    # lower byte is transmitted first. The default (no command sent) is that the upper
    # byte transmitted first.
    # • BYTE formatted data is transferred as 8-bit bytes.
    # When the :WAVeform:SOURce is the serial decode bus (SBUS1 or SBUS2), ASCii
    # is the only waveform format allowed.
    # When the :WAVeform:SOURce is one of the digital channel buses (BUS1 or BUS2),
    # ASCii and WORD are the only waveform formats allowed.
    # Query Syntax :WAVeform:FORMat?
    # The :WAVeform:FORMat query returns the current output format for the transfer of
    # waveform data.
    # Return Format <value><NL>
    # <value> ::= {WORD | BYTE | ASC}
    
    # :WAVeform:POINts:MODE
    # (see page 1572)
    # Command Syntax :WAVeform:POINts:MODE <points_mode>
    # <points_mode> ::= {NORMal | MAXimum | RAW}
    # The :WAVeform:POINts:MODE command sets the data record to be transferred
    # with the :WAVeform:DATA? query.
    # For the analog or digital sources, there are two different records that can be
    # transferred:
    # • The first is the raw acquisition record. The maximum number of points available
    # in this record is returned by the :ACQuire:POINts? query. The raw acquisition
    # record can only be retrieved from the analog or digital sources.
    # • The second is referred to as the measurement record and is a 62,500-point
    # (maximum) representation of the raw acquisition record. The measurement
    # record can be retrieved from any source.
    # If the <points_mode> is NORMal the measurement record is retrieved.
    # If the <points_mode> is RAW, the raw acquisition record is used. Under some
    # conditions, this data record is unavailable.
    # If the <points_mode> is MAXimum, whichever record contains the maximum
    # amount of points is used. Usually, this is the raw acquisition record. But, the
    # measurement record may have more data. If data is being retrieved as the
    # oscilloscope is stopped and as the data displayed is changing, the data being
    # retrieved can switch between the measurement and raw acquisition records.
    # Considerations for
    # MAXimum or RAW
    # data retrieval
    # • The instrument must be stopped (see the :STOP command (see page 285) or
    # the :DIGitize command (see page 258) in the root subsystem) in order to return
    # more than the measurement record.
    # • :TIMebase:MODE must be set to MAIN.
    # • :ACQuire:TYPE must be set to NORMal, AVERage, or HRESolution.
    # • MAXimum or RAW will allow up to 4,000,000 points to be returned. The
    # number of points returned will vary as the instrument's configuration is
    # changed. Use the :WAVeform:POINts? MAXimum query to determine the
    # maximum number of points that can be retrieved at the current settings.
    # Query Syntax :WAVeform:POINts:MODE?
    # NOTE If the :WAVeform:SOURce is not an analog or digital source, the only valid parameters for
    # WAVeform:POINts:MODE is NORMal or MAXimum.
    # :WAVeform Commands 36
    # Keysight InfiniiVision 3000T X-Series Oscilloscopes Programmer's Guide 1375
    # The :WAVeform:POINts:MODE? query returns the current points mode. Setting the
    # points mode will affect what data is transferred. See the discussion above.
    # Return Format <points_mode><NL>
    # <points_mode> ::= {NORMal | MAXimum | RAW}
    
    # :WAVeform:PREamble
    # (see page 1572)
    # Query Syntax :WAVeform:PREamble?
    # The :WAVeform:PREamble query requests the preamble information for the
    # selected waveform source. The preamble data contains information concerning
    # the vertical and horizontal scaling of the data of the corresponding channel.
    # Return Format <preamble_block><NL>
    # <preamble_block> ::= <format 16-bit NR1>,
    # <type 16-bit NR1>,
    # <points 32-bit NR1>,
    # <count 32-bit NR1>,
    # <xincrement 64-bit floating point NR3>,
    # <xorigin 64-bit floating point NR3>,
    # <xreference 32-bit NR1>,
    # <yincrement 32-bit floating point NR3>,
    # <yorigin 32-bit floating point NR3>,
    # <yreference 32-bit NR1>
    # <format> ::= 0 for BYTE format, 1 for WORD format, 4 for ASCii format;
    # an integer in NR1 format (format set by :WAVeform:FORMat).
    # <type> ::= 3 for HRESolution type, 2 for AVERage type, 0 for NORMal
    # type, 1 for PEAK detect type; an integer in NR1 format
    # (type set by :ACQuire:TYPE).
    # <count> ::= Average count or 1 if PEAK or NORMal; an integer in NR1
    # format (count set by :ACQuire:COUNt).
    
    
    # :WAVeform:PREamble
    # (see page 1572)
    # Query Syntax :WAVeform:PREamble?
    # The :WAVeform:PREamble query requests the preamble information for the
    # selected waveform source. The preamble data contains information concerning
    # the vertical and horizontal scaling of the data of the corresponding channel.
    # Return Format <preamble_block><NL>
    # <preamble_block> ::= <format 16-bit NR1>,
    # <type 16-bit NR1>,
    # <points 32-bit NR1>,
    # <count 32-bit NR1>,
    # <xincrement 64-bit floating point NR3>,
    # <xorigin 64-bit floating point NR3>,
    # <xreference 32-bit NR1>,
    # <yincrement 32-bit floating point NR3>,
    # <yorigin 32-bit floating point NR3>,
    # <yreference 32-bit NR1>
    # <format> ::= 0 for BYTE format, 1 for WORD format, 4 for ASCii format;
    # an integer in NR1 format (format set by :WAVeform:FORMat).
    # <type> ::= 3 for HRESolution type, 2 for AVERage type, 0 for NORMal
    # type, 1 for PEAK detect type; an integer in NR1 format
    # (type set by :ACQuire:TYPE).
    # <count> ::= Average count or 1 if PEAK or NORMal; an
    
    # :WAVeform:SEGMented:ALL
    # (see page 1572)
    # Command Syntax :WAVeform:SEGMented:ALL {{0 | OFF} | {1 | ON}}
    # The :WAVeform:SEGMented:ALL command enables or disables the "waveform
    # data for all segments" setting:
    # • ON — The :WAVeform:DATA? query returns data for all segments.
    # ON is available only when the :WAVeform:SOURce is an analog input channel.
    # When ON, the :WAVeform:DATA? query returns data for the number of
    # segments multiplied by the number of points in a segment (which is the points
    # value returned by the :WAVeform:POINts? or :WAVeform:PREamble? queries).
    # • OFF — The :WAVeform:DATA? query returns data for the current segment.
    # The ability to get waveform data for all segments is faster and more convenient
    # than iterating over multiple segments and retrieving each one separately.
    # The performance improvement comes primarily when raw acquisition record data
    # is being retrieved (:WAVeform:POINts:MODE RAW) instead of the measurement
    # record data (:WAVeform:POINts:MODE NORMal).
    # One corner case where you may want to retreive the measurement record data is
    # when the acquired data for a segment is less than the screen resolution and the
    # measurement record is interpolated.
    # Most often though, the acquired data for a segment is enough to fill the screen,
    # and less than the maximum measurement record size, so the segmented raw
    # acquisition data and the measurement record data are the same.
    # If the number of segments is small, the raw acquisition segment size is greater
    # than the measurement record size.
    # Query Syntax :WAVeform:SEGMented:ALL?
    # The :WAVeform:SEGMented:ALL? query returns the "waveform data for all
    # segments" setting.
    # Return Format <setting><NL>
    # <setting> ::= {0 | 1}
    
    # :WAVeform:SEGMented:COUNt
    # (see page 1572)
    # Query Syntax :WAVeform:SEGMented:COUNt?
    # The :WAVeform:SEGMented:COUNt query returns the number of memory
    # segments in the acquired data. You can use the :WAVeform:SEGMented:COUNt?
    # query while segments are being acquired (although :DIGitize blocks subsequent
    # queries until the full segmented acquisition is complete).
    # The segmented memory acquisition mode is enabled with the :ACQuire:MODE
    # command. The number of segments to acquire is set using the
    # :ACQuire:SEGMented:COUNt command, and data is acquired using the :DIGitize,
    # :SINGle, or :RUN commands.
    # Return Format <count> ::= an integer from 2 to 1000 in NR1 format (count set by
    # :ACQuire:SEGMented:COUNt).
    
    # :WAVeform:SEGMented:TTAG
    # (see page 1572)
    # Query Syntax :WAVeform:SEGMented:TTAG?
    # The :WAVeform:SEGMented:TTAG? query returns the time tag of the currently
    # selected segmented memory index. The index is selected using the
    # :ACQuire:SEGMented:INDex command.
    # Return Format <time_tag> ::= in NR3 format
    
    # :WAVeform:SEGMented:XLISt
    # (see page 1572)
    # Query Syntax :WAVeform:SEGMented:XLISt? <xlist_type>
    # <xlist_type> ::= {RELXorigin | ABSXorigin | TTAG}
    # The :WAVeform:SEGMented:XLISt? query returns the X (time) information for all
    # segments at once. The <xlist_type> option specifies the type of information that is
    # returned:
    # • RELXorigin — The relative X-origin for each segment (the value returned by the
    # :WAVeform:XORigin? query) is returned.
    # • TTAG — The time tag for each segment (the value returned by the
    # :WAVeform:SEGMented:TTAG? query) will be returned.
    # • ABSXorigin — The sum of the values of the RELXorigin and TTAG types is
    # returned for each segment.
    # This command is useful when getting the waveform data for all segments at once
    # (see :WAVeform:SEGMented:ALL).
    # Return Format <return_value><NL>
    # <return_value> ::= binary block data in IEEE 488.2 # format, contains
    # comma-separated string with X-info for all segments
    
    # :WAVeform:SOURce
    # (see page 1572)
    # Command Syntax :WAVeform:SOURce <source>
    # <source> ::= {CHANnel<n> | FUNCtion<m> | MATH<m> | FFT | WMEMory<r>
    # | SBUS{1 | 2}} for DSO models
    # <source> ::= {CHANnel<n> | POD{1 | 2} | BUS{1 | 2} | FUNCtion<m>
    # | MATH<m> | FFT | WMEMory<r> | SBUS{1 | 2}}
    # for MSO models
    # <n> ::= 1 to (# analog channels) in NR1 format
    # <m> ::= 1 to (# math functions) in NR1 format
    # <r> ::= 1 to (# ref waveforms) in NR1 format
    # The :WAVeform:SOURce command selects the analog channel, function, digital
    # pod, digital bus, reference waveform, or serial decode bus to be used as the source
    # for the :WAVeform commands.
    # Function capabilities include add, subtract, multiply, integrate, differentiate, and
    # FFT (Fast Fourier Transform) operations.
    # When the :WAVeform:SOURce is the serial decode bus (SBUS1 or SBUS2), ASCii
    # is the only waveform format allowed, and the :WAVeform:DATA? query returns a
    # string with timestamps and associated bus decode information.
    # With MSO oscilloscope models, you can choose a POD or BUS as the waveform
    # source. There are some differences between POD and BUS when formatting and
    # getting data from the oscilloscope:
    # • When POD1 or POD2 is selected as the waveform source, you can choose the
    # BYTE, WORD, or ASCii formats (see ":WAVeform:FORMat" on page 1371).
    # When the WORD format is chosen, every other data byte will be 0. The setting
    # of :WAVeform:BYTeorder controls which byte is 0.
    # When the ASCii format is chosen, the :WAVeform:DATA? query returns a string
    # with unsigned decimal values separated by commas.
    # • When BUS1 or BUS2 is selected as the waveform source, you can choose the
    # WORD or ASCii formats (but not BYTE because bus values are always returned
    # as 16-bit values).
    # When the ASCii format is chosen, the :WAVeform:DATA? query returns a string
    # with hexadecimal bus values, for example: 0x1938,0xff38,...
    # Query Syntax :WAVeform:SOURce?
    # The :WAVeform:SOURce? query returns the currently selected source for the
    # WAVeform commands.
    # 1384 Keysight InfiniiVision 3000T X-Series Oscilloscopes Programmer's Guide
    # 36 :WAVeform Commands
    # Return Format <source><NL>
    # <source> ::= {CHAN<n> | FUNC<m> | WMEM<r> | SBUS{1 | 2}} for DSO models
    # <source> ::= {CHAN<n> | POD{1 | 2} | BUS{1 | 2} | FUNC<m>
    # | WMEM<r> | SBUS{1 | 2}} for MSO models
    # <n> ::= 1 to (# analog channels) in NR1 format
    # <m> ::= 1 to (# math functions) in NR1 format
    # <r> ::= 1 to (# ref waveforms) in NR1 format
    
    # :WAVeform:UNSigned
    # (see page 1572)
    # Command Syntax :WAVeform:UNSigned <unsigned>
    # <unsigned> ::= {{0 | OFF} | {1 | ON}}
    # The :WAVeform:UNSigned command turns unsigned mode on or off for the
    # currently selected waveform. Use the WAVeform:UNSigned command to control
    # whether data values are sent as unsigned or signed integers. This command can
    # be used to match the instrument's internal data type to the data type used by the
    # programming language. This command has no effect if the data format is ASCii.
    # If :WAVeform:SOURce is set to POD1, POD2, BUS1, or BUS2,
    # WAVeform:UNSigned must be set to ON.
    # Query Syntax :WAVeform:UNSigned?
    # The :WAVeform:UNSigned? query returns the status of unsigned mode for the
    # currently selected waveform.
    # Return Format <unsigned><NL>
    # <unsigned> ::= {0 | 1}
    
    # :WAVeform:VIEW
    # (see page 1572)
    # Command Syntax :WAVeform:VIEW <view>
    # <view> ::= {MAIN | ALL}
    # The :WAVeform:VIEW command sets the view setting associated with the currently
    # selected waveform:
    # • MAIN — This view specifies the data you see in the oscilloscope's main
    # waveform display area.
    # • ALL — Available only when Digitizer mode is on (see :ACQuire:DIGitizer), this
    # view specifies all the captured data, which may extend beyound the edges of
    # the oscilloscope's main waveform display area depending on the settings for
    # sample rate, memory depth, and horizontal time/div.
    # Query Syntax :WAVeform:VIEW?
    # The :WAVeform:VIEW? query returns the view setting associated with the currently
    # selected waveform.
    # Return Format <view><NL>
    # <view> ::= {MAIN | ALL}
    
    # :WAVeform:XINCrement
    # (see page 1572)
    # Query Syntax :WAVeform:XINCrement?
    # The :WAVeform:XINCrement? query returns the x-increment value for the currently
    # specified source. This value is the time difference between consecutive data points
    # in seconds.
    # Return Format <value><NL>
    # <value> ::= x-increment in the current preamble in 64-bit
    # floating point NR3 format
    
    # :WAVeform:XORigin
    # (see page 1572)
    # Query Syntax :WAVeform:XORigin?
    # The :WAVeform:XORigin? query returns the x-origin value for the currently
    # specified source. XORigin is the X-axis value of the data point specified by the
    # :WAVeform:XREFerence value. In this product, that is always the X-axis value of
    # the first data point (XREFerence = 0).
    # Return Format <value><NL>
    # <value> ::= x-origin value in the current preamble in 64-bit
    # floating point NR3 format
    # See Also • "Introduction to :WAVeform Commands"
    
    # :WAVeform:XREFerence
    # (see page 1572)
    # Query Syntax :WAVeform:XREFerence?
    # The :WAVeform:XREFerence? query returns the x-reference value for the currently
    # specified source. This value specifies the index of the data point associated with
    # the x-origin data value. In this product, the x-reference point is the first point
    # displayed and XREFerence is always 0.
    # Return Format <value><NL>
    # <value> ::= x-reference value = 0 in 32-bit NR1 format
    
    # :WAVeform:YINCrement
    # (see page 1572)
    # Query Syntax :WAVeform:YINCrement?
    # The :WAVeform:YINCrement? query returns the y-increment value in volts for the
    # currently specified source. This value is the voltage difference between
    # consecutive data values. The y-increment for digital waveforms is always "1".
    # Return Format <value><NL>
    # <value> ::= y-increment value in the current preamble in 32-bit
    # floating point NR3 format
    
    # :WAVeform:YORigin
    # (see page 1572)
    # Query Syntax :WAVeform:YORigin?
    # The :WAVeform:YORigin? query returns the y-origin value for the currently
    # specified source. This value is the Y-axis value of the data value specified by the
    # :WAVeform:YREFerence value. For this product, this is the Y-axis value of the
    # center of the screen.
    # Return Format <value><NL>
    # <value> ::= y-origin in the current preamble in 32-bit
    # floating point NR3 format
    
    # :WAVeform:YREFerence
    # (see page 1572)
    # Query Syntax :WAVeform:YREFerence?
    # The :WAVeform:YREFerence? query returns the y-reference value for the currently
    # specified source. This value specifies the data point value where the y-origin
    # occurs. In this product, this is the data point value of the center of the screen. It is
    # undefined if the format is ASCii.
    # Return Format <value><NL>
    # <value> ::= y-reference value in the current preamble in 32-bit
    # NR1 format
    
    
    # :ACQuire:DIGitizer
    # (see page 1572)
    # Command Syntax :ACQuire:DIGitizer {{0 | OFF} | {1 | ON}}
    # The :ACQuire:DIGitizer command turns Digitizer mode on or off.
    # Normally, when Digitizer mode is disabled (Automatic mode), the oscilloscope's
    # time per division setting determines the sample rate and memory depth so as to
    # fill the waveform display with data while the oscilloscope is running (continuously
    # making acquisitions). For single acquisitions, the time/division setting still
    # determines the sample rate, but the maximum amount of acquisition memory is
    # used.
    # In Digitizer mode, you choose the acquisition sample rate and memory depth, and
    # those settings are used even though the captured data may extend way beyond
    # the edges of, or take up just a small portion of, the waveform display, depending
    # on the oscilloscope's time/div setting.
    # Digitizer mode cannot be used along with these other oscilloscope features: XY
    # and Roll time modes, horizontal Zoom display, time references other than Center,
    # segmented memory, serial decode, digital channels, frequency response analysis,
    # mask test, and the power application. In most cases, enabling one of these
    # features when Digitizer mode is enabled will automatically disable Digitizer mode,
    # and then disabling the feature will automatically reenable Digitizer mode.
    # Digitizer mode primarily aids external software that controls and combines data
    # from multiple instruments.
    # Query Syntax :ACQuire:DIGitizer?
    # The :ACQuire:DIGitizer? query returns whether Digitizer mode is off or on.
    # Return Format <setting><NL>
    # <setting> ::= {0 | 1}






    # '''Agilent 4-channel mixed signal DSO'''
    # def __init__(self, interface_visa, force_trigger=False, reset=False, timeout=2): # 10 seconds recommended in programmer"s manual page 63
        # '''interface_visa'''
        # self._base_name = "agilent_3034a"
        # scpi_instrument.__init__(self,f"agilent_3034a @ {interface_visa}")
        # delegator.__init__(self)  # Clears self._interfaces list, so must happen before add_interface_visa(). --FL 12/21/2016
        # self.add_interface_visa(interface_visa, timeout = timeout)
        # if reset:
            # self.reset() # Get to a known state for full automation if so desired.
        # self.get_interface().write(":WAVeform:FORMat ASCII")
        # self.get_interface().write(":WAVeform:POINts:MODE RAW") #maximum number of points by default (scope must be stopped)
        # self.force_trigger = force_trigger

    # def add_Ychannel(self, name, number):
        # '''Add named channel to instrument. num is 1-4.'''
        # scope_channel = channel(name, read_function=lambda: self._read_scope_channel(number))
        # scope_channel.set_delegator(self)
        # self._add_channel(scope_channel)
        # self.get_interface().write(f":CHANnel{number}:DISPlay ON") # make sure it"s on
        # self.get_interface().write(f":WAVeform:SOURce CHANnel{number}") #make sure one of the selected channels is always active to get time info
        # def get_channel_settings(number):
            # result              = {}
            # result["scale"]     = float(self.get_interface().ask(f":CHANnel{number}:SCALe?"))
            # result["offset"]    = float(self.get_interface().ask(f":CHANnel{number}:OFFSet?"))# This is the value represented by the screen center.
            # result["units"]     = self.get_interface().ask(f":CHANnel{number}:UNITs?")[0]# Pick up just the first letter A for AMP or V for VOLT.
            # result["label"]     = self.get_interface().ask(f":CHANnel{number}:LABel?").decode().strip("'")
            # result["bwlimit"]   = self.get_interface().ask(f":CHANnel{number}:BWLimit?")
            # result["coupling"]  = self.get_interface().ask(f":CHANnel{number}:COUPling?")
            # result["impedance"] = self.get_interface().ask(f":CHANnel{number}:IMPedance?")
            # return result
        # # Extended Channels
        # self.add_channel_probe_gain(name=f"{name}_probe_gain", number=number)
        # self.add_channel_BWLimit(name=f"{name}_BWlimit", number=number)
        # self.add_channel_Yrange(name=f"{name}_Yrange", number=number)
        # self.add_channel_Yoffset(name=f"{name}_Yoffset", number=number)
        # self.add_channel_impedance(name=f"{name}_Impedance", number=number)
        # self.add_channel_units(name=f"{name}_units", number=number)
        # self.add_channel_coupling(name=f"{name}_coupling", number=number)
        # # Extended Channels
        # trace_info = channel(name + "_info", read_function=lambda: get_channel_settings(number))
        # trace_info.set_delegator(self)
        # self._add_channel(trace_info)
        # return scope_channel
        
    # def add_Xchannels(self, prefix):
        # self.add_channel_Xrange(name=f"{prefix}_Xrange")
        # self.add_channel_Xposition(name=f"{prefix}_Xposition")
        # self.add_channel_Xreference(name=f"{prefix}_Xreference")
        # self.add_channel_triggerlevel(name=f"{prefix}_trigger_level")
        # self.add_channel_triggermode(name=f"{prefix}_trigger_mode")
        # self.add_channel_triggerslope(name=f"{prefix}_trigger_slope")
        # self.add_channel_triggersource(name=f"{prefix}_trigger_source")
        # self.add_channel_acquire_type(name=f"{prefix}_acquire_type")
        # self.add_channel_acquire_count(name=f"{prefix}_acquire_count")
        # self.add_channel_pointcount(name=f"{prefix}_points_count")
        # self.add_channel_runmode(name=f"{prefix}_run_mode")
        # self.add_channel_time(name=f"{prefix}_timedata")

    # def add_channel_time(self,name):
        # def compute_x_points(self):
            # '''Data conversion:
            # voltage = [(data value - yreference) * yincrement] + yorigin
            # time = [(data point number - xreference) * xincrement] + xorigin'''
            # xpoints = [(x - self.time_info["reference"]) * self.time_info["increment"] + self.time_info["origin"] for x in range(self.time_info["points"])]
            # return xpoints
        # time_channel = channel(name, read_function=lambda: compute_x_points(self))
        # time_channel.set_delegator(self)
        # self._add_channel(time_channel)
        # def get_time_info(self):
            # return self.time_info
        # time_info = channel(name + "_info", read_function=lambda: get_time_info(self))
        # time_info.set_delegator(self)
        # self._add_channel(time_info)
        # return time_channel

    # def set_points(self, points):
        # '''set the number of points returned by read_channel() or read_channels() points must be in range [100,250,500] or [1000,2000,5000]*10^[0-4] or [8000000]'''
        # allowed_points = [100,250,500]
        # allowed_points.extend(lab_utils.decadeListRange([1000,2000,5000],4))
        # allowed_points.extend(8000000,)
        # if points not in allowed_points:
            # raise ValueError(f"\n\n{self.get_name()}: set_points: points argument muse be in: {allowed_points}")
        # self.get_interface().write(f":WAVeform:POINts {points}")

    # def get_channel_enable_status(self, number):
        # return int(self.get_interface().ask(f":CHANnel{number}:DISPlay?"))

    # def get_time_base(self):
        # return float(self.get_interface().ask(":TIMebase:RANGe?")) / 10 # Always 10 horizontal divisions

    # def trigger_force(self):
        # self.get_interface().write(":RUN;:TRIGger:FORCe")
        # self.operation_complete()

    # def digitize(self):
        # self.get_interface().write(":DIGitize")
        # self.operation_complete()

    # def _read_scope_time_info(self):
        # self.time_info                = {}
        # self.time_info["points"]      = int(self.get_interface().ask(":WAVeform:POINts?"))         # int(preamble[2])
        # self.time_info["increment"]   = float(self.get_interface().ask(":WAVeform:XINCrement?"))   # float(preamble[4])
        # self.time_info["origin"]      = float(self.get_interface().ask(":WAVeform:XORigin?"))      # float(preamble[5])
        # self.time_info["reference"]   = float(self.get_interface().ask(":WAVeform:XREFerence?"))   # float(preamble[6])
        # self.time_info["scale"]       = self.time_info["increment"] * self.time_info["points"] / 10
        # self.time_info["enable_status"] = {}
        # for scope_channel_number in range(1,5):
            # self.time_info["enable_status"][scope_channel_number] = int(self.get_interface().ask(f":CHANnel{scope_channel_number}:DISPlay?"))

    # def _read_scope_channel(self, scope_channel_number):
        # '''return list of y-axis points for named channel
            # list will be datalogged by logger as a string in a single cell in the table
            # trigger=False can by used to suppress acquisition of new data by the instrument so that
            # data from a single trigger may be retrieved from each of the four channels in turn by read_channels()
        # '''
        # self.get_interface().write(f":WAVeform:SOURce CHANnel{scope_channel_number}")
        # raw_data = self.get_interface().ask(":WAVeform:DATA?")
        # #Example: "#800027579 4.03266e-002, 1.25647e-004, 1.25647e-004, 1.25647e-004,......."
        # raw_data = raw_data[10:] #remove header
        # raw_data = raw_data.decode().split(",")
        # data = [float(x) for x in raw_data]
        # #TODO - implement binary transfer if speed becomes a problem
        # return data

    # def read_delegated_channel_list(self, channels):
        # if self.force_trigger:
        # self.trigger_force()
        # # self.digitize()
        # # self.get_interface().write(":STOP")# scope will timeout on :WAVeform:PREamble? if not "STOPped"
        # # print("ACQ Complete: ", self.get_interface().ask(":ACQuire:COMPlete?"))
        # self.operation_complete()
        # time.sleep(0.1) # Why do I need this. How to ask the scope when it's ready to talk? PrimaDonna! DSO-X 3034A
        # self._read_scope_time_info()
        # results = results_ord_dict()
        # for channel in channels:
            # results[channel.get_name()] = channel.read_without_delegator()
        # return results
        
    # def add_channel_probe_gain(self, name, number):
        # new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":CHANnel{number}:PROBe {value}"))
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_BWLimit(self, name, number):
        # def _set_BWLimit(number, value):
            # if value in [True, False]:
                # value = "ON" if value else "OFF"
            # if str(value).upper() in ["TRUE", "FALSE"]:
                # value = "ON" if str(value).upper()== "TRUE" else "OFF"
            # if str(value).upper() not in ["ON", "OFF"]:
                # value = "ON" if value else "OFF" # Best guess but at least no SCPI error.
            # self.get_interface().write(f":CHANnel{number}:BWLimit {value}")
        # new_channel = channel(name, write_function=lambda value : _set_BWLimit(number, value))
        # new_channel.add_preset("ON",    "Enable 25Mhz limit")
        # new_channel.add_preset("OFF",   "Disable 25MHz limit")
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_Yrange(self, name, number):
        # new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":CHANnel{number}:RANGe {value}"))
        # self._add_channel(new_channel)
        # return new_channel
            
    # def add_channel_Yoffset(self, name, number):
        # new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":CHANnel{number}:OFFSet {-value}"))
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_impedance(self, name, number):
        # def _set_impedance(number, value):
            # if value in [50, "50", 1000000, 1e6, "1000000", "1e6", "1M"]:
                # value = "FIFTy" if value in [50, "50"] else "ONEMeg"
            # else:
                # raise ValueError("\n\nScope input impedance must be either 50, 1000000 or 1M")
            # self.get_interface().write(f":CHANnel{number}:IMPedance {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_impedance(number, value))
        # new_channel.add_preset("50",    "50Ω")
        # new_channel.add_preset("1M",    "1MΩ")
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_units(self, name, number):
        # def _set_units(number, value):
            # if value.upper() in ["V", "A", "VOLTS", "AMPS"]:
                # value = "VOLT" if value.upper() in ["V", "VOLTS"] else "AMPere"
            # else:
                # raise ValueError("\n\nUnits must be one of V, A, VOLTS, AMPS")
            # self.get_interface().write(f":CHANnel{number}:UNITs {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_units(number, value))
        # new_channel.add_preset("VOLTS", "Volts")
        # new_channel.add_preset("AMPS",  "Amperes")
        # self._add_channel(new_channel)
        # return new_channel
        
    # def add_channel_coupling(self, name, number):
        # def _set_coupling(number, value):
            # if value.upper() not in ["AC", "DC"]:
                # raise ValueError("\n\nUnits must be either AC or DC")
            # self.get_interface().write(f":CHANnel{number}:COUPling {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_coupling(number, value))
        # new_channel.add_preset("AC", "AC")
        # new_channel.add_preset("DC", "DC")
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_Xrange(self, name):
        # def _set_Xrange(value):
            # self.get_interface().write(f":TIMebase:RANGe {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_Xrange(value))
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_Xposition(self, name):
        # def _set_Xposition(value):
            # self.get_interface().write(f":TIMebase:POSition {-value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_Xposition(value))
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_Xreference(self, name):
        # def _set_xreference(value):
            # if value.upper() not in ["LEFT", "CENTER", "RIGHT"]:
                # raise ValueError("\n\nX reference must be one of must be one of: LEFT, CENTER, RIGHT")
            # self.get_interface().write(f":TIMebase:REFerence {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_xreference(value))
        # new_channel.add_preset("LEFT",      "One Division from the left")
        # new_channel.add_preset("CENTER",    "Screen Center")
        # new_channel.add_preset("RIGHT",     "One Division from the right")
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_runmode(self, name):
        # def _set_runmode(value):
            # if value.upper() not in ["RUN", "STOP", "SINGLE"]:
                # raise ValueError("\n\nRun mode must be one of: RUN, STOP, SINGLE")
            # self.get_interface().write(f":{value}")
            # # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_runmode(value))
        # new_channel.add_preset("RUN",       "Free running mode")
        # new_channel.add_preset("STOP",      "Stopped")
        # new_channel.add_preset("SINGLE",    "Waiting for trigger")
        # self._add_channel(new_channel)
        # return new_channel
            
    # def add_channel_triggerlevel(self, name): # TODO Needs operation complete
        # new_channel = channel(name, write_function=lambda value : self.get_interface().write(f":TRIGger:LEVel {value}"))
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_triggermode(self, name):
        # def _set_triggermode(value):
            # if value.upper() not in ["AUTO", "NORMAL"]:
                # raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL")
            # self.get_interface().write(f":TRIGger:SWEep {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_triggermode(value))
        # new_channel.add_preset("AUTO",       "Find a trigger level")
        # new_channel.add_preset("NORMAL",     "Use defined trigger level")
        # self._add_channel(new_channel)
        # return new_channel
            
    # def add_channel_triggerslope(self, name):
        # def _set_triggerslope(value):
            # if value.upper() not in ["NEGATIVE", "POSITIVE", "EITHER", "ALTERNATE"]:
                # raise ValueError("\n\nTrigger mode must be one of: AUTO, NORMAL, EITHER, ALTERNATE")
            # self.get_interface().write(f":TRIGger:SLOPe {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_triggerslope(value))
        # new_channel.add_preset("POSITIVE",      "Positive edges")
        # new_channel.add_preset("NEGATIVE",      "Negative edges")
        # new_channel.add_preset("EITHER",        "Either edge")
        # new_channel.add_preset("ALTERNATE",     "Alternate between edges")
        # self._add_channel(new_channel)
        # return new_channel
            
    # def add_channel_triggersource(self, name):
        # def _set_triggersource(value):
            # if value.upper() not in ["EXT", "LINE", "WGEN", "CHANNEL1", "CHANNEL2", "CHANNEL3", "CHANNEL4"]:
                # raise ValueError("\n\nTrigger mode must be one of: EXT, LINE, WGEN, CHANx where x=[1..4]]")
            # self.get_interface().write(f":TRIGger:SOURce {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_triggersource(value))
        # new_channel.add_preset("EXT",       "External Trigger")
        # new_channel.add_preset("LINE",      "Line Trigger")
        # new_channel.add_preset("WGEN",      "Waveform Generator")
        # new_channel.add_preset("CHANNEL1",  "Channel 1")
        # new_channel.add_preset("CHANNEL2",  "Channel 2")
        # new_channel.add_preset("CHANNEL3",  "Channel 3")
        # new_channel.add_preset("CHANNEL4",  "Channel 4")
        # self._add_channel(new_channel)
        # return new_channel

    # def add_channel_acquire_type(self, name):
        # def _set_acquiretype(value):
            # if value.upper() not in ["NORMAL", "AVERAGE", "HRESOLUTION", "PEAK"]:
                # raise ValueError("\n\nAcquire type must be one of: NORMAL, AVERAGE, HRESOLUTION, PEAK")
            # self.get_interface().write(f":ACQuire:TYPE {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_acquiretype(value))
        # new_channel.add_preset("NORMAL",        "Sets the oscilloscope in the normal mode")
        # new_channel.add_preset("AVERAGE",       "sets the oscilloscope in the averaging mode. You can set the count by sending the :ACQuire:COUNt command followed by the number of averages. In this mode, the value for averages is an integer from 1 to 65536 (Acquire Count section of manual says 2..65326, setting to 1 results in Data Out of Range (SLM)). The COUNt value determines the number of averages that must be acquired")
        # new_channel.add_preset("HRESOLUTION",   "Sets the oscilloscope in the high-resolution mode (also known as smoothing). This mode is used to reduce noise at slower sweep speeds where the digitizer samples faster than needed to fill memory for the displayed time range. For example, if the digitizer samples at 200 MSa/s, but the effective sample rate is 1 MSa/s (because of a slower sweep speed), only 1 out of every 200 samples needs to be stored. Instead of storing one sample (and throwing others away), the 200 samples are averaged together to provide the value for one display point. The slower the sweep speed, the greater the number of samples that are averaged together for each display point")
        # new_channel.add_preset("PEAK",          "sets the oscilloscope in the peak detect mode. In this mode, :ACQuire:COUNt has no meaning")
        # self._add_channel(new_channel)
        # return new_channel
        
    # def add_channel_acquire_count(self, name):
        # def _set_acquirecount(value):
            # if value not in range(2,65536+1):
                # raise ValueError("\n\nAcquire Count must be in [2..65536]")
            # self.get_interface().write(f":ACQuire:COUNt {value}")
            # self.operation_complete()
        # new_channel = channel(name, write_function=lambda value : _set_acquirecount(value))
        # self._add_channel(new_channel)
        # return new_channel
            
    # def add_channel_pointcount(self, name):
        # new_channel = channel(name, write_function=lambda value : self.set_points(value))
        # self._add_channel(new_channel)
        # return new_channel
