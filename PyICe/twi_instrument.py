"""Channel Wraper for SMBus Compliant Devices.

==========================================

Can automatically populate channels/reisters from XML description

>>> from PyICe.twi_instrument import twi_instrument

"""
import logging
from . import lab_core
from . import twi_interface
import xml.etree.ElementTree as ET
from PyICe.lab_utils.str2num import str2num
from PyICe.lab_utils.interpolator import interpolator
import json
import traceback
from PyICe.ipxact_parser import (IpxactParser, ipxact_access_to_rw,
                                 ipxact_modified_write_to_pyice)
from PyICe.lab_utils.clean_ascii_code import clean_ascii_code

try:
    from scipy.interpolate import UnivariateSpline
except ImportError:
    UnivariateSpline = None  # type: ignore[assignment]
    SCIPY_MISSING = True
    print("SciPy not found. Reverting to Python piecewise linear interpolator/extrapolator for formats.")
SCIPY_MISSING = True  # Force Python interpolator instead of spline

debug_logging = logging.getLogger(__name__)


class twi_instrument(lab_core.instrument, lab_core.delegator):
    """Instrument wrapper that maps I2C/SMBus registers to PyICe channels.

    Provides automatic read-modify-write for sub-register bitfield access,
    XML/JSON register-map import, and configurable error-retry behaviour.
    Each bitfield becomes a readable/writable channel that the lab_core
    delegation framework can batch into efficient bus transactions.

    >>> from PyICe.twi_instrument import twi_instrument
    >>> twi_instrument is not None
    True

    """
    def __init__(self, interface_twi, except_on_i2cInitError=True,
                 except_on_i2cCommError=False, retry_count=5, PEC=False):
        """Create a twi_instrument bound to an I2C/SMBus master interface.

        Call this once per slave device.  After construction, populate
        channels with ``add_register``, ``populate_from_file``, or
        ``populate_from_yoda_json_bridge``.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, '__init__')
        True

        Args:
            interface_twi: TWI/I2C master interface (e.g. from
                ``master.get_twi_interface()``).
            except_on_i2cInitError: If True, raise when the bus cannot be
                re-synchronised after a communication failure.
            except_on_i2cCommError: If True, raise on a failed I2C
                transaction after all retries are exhausted.
            retry_count: Number of additional attempts after the first
                failure before giving up.
            PEC: Enable SMBus Packet Error Checking (CRC-8) on every
                transaction.
        """
        lab_core.instrument.__init__(self, name="twi_instrument")
        lab_core.delegator.__init__(self)
        self.add_interface_twi(interface_twi)
        self._interface = interface_twi
        self._PEC = PEC
        self.except_on_i2cInitError = except_on_i2cInitError
        self.except_on_i2cCommError = except_on_i2cCommError
        self.retry_count = retry_count
        self.formatters = {}
        self._constants = {}
        self._streaming_enabled = False
        # self._previous_command_codes = []
        self._addr7 = None

    def add_register(self, name, addr7, command_code, size, offset,
                     word_size, is_readable, is_writable, overwrite_others=False):
        """Create a new TWI register channel for a single bitfield.

        Builds a ``twi_register`` whose writes are delegated through a
        read-modify-write cycle so that adjacent bitfields sharing the
        same command code are preserved.  The register is returned after
        being added to the instrument's channel list.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'add_register')
        True

        Args:
            name: Human-readable channel name for this bitfield.
            addr7: 7-bit I2C slave address (without R/W bit).
            command_code: SMBus command code (register address byte).
            size: Width of this bitfield in bits.
            offset: LSB position of this bitfield within the register.
            word_size: Total register width in bits (0 for send-byte,
                -1 for quick-command).
            is_readable: Whether the register supports reads.
            is_writable: Whether the register supports writes.
            overwrite_others: If True, skip the read-back during
                read-modify-write and assume other bitfields are zero.

        Returns:
            The newly created ``twi_register`` channel instance.

        Raises:
            Exception: If a different ``addr7`` was already registered
                (only one slave address per instrument is allowed).
        """
        if self._addr7 != addr7:
            if self._addr7 is None:
                self._addr7 = addr7  # first time
            else:
                raise Exception('twi_instrument only supports one chip i2c address.'
                                'Consider making a second twi_instrument instance.')
        new_register = twi_register(name, size,
                                    read_function=self._dummy_read,
                                    write_function=lambda data: self._read_merge_write(data, addr7, command_code, size, offset, word_size, is_readable, overwrite_others))
        new_register.set_delegator(self)
        new_register.set_attribute("chip_address7", addr7)
        new_register.set_read_access(is_readable)
        new_register.set_write_access(is_writable)
        new_register.set_attribute("offset", offset)
        new_register.set_attribute("command_code", command_code)
        new_register.set_attribute("word_size", word_size)
        new_register._command_code_and_rmw_value = (lambda new_value,
                                                    addr7=addr7,
                                                    size=size,
                                                    offset=offset,
                                                    word_size=word_size: self.get_bitfield_writeback_data(addr7=addr7,
                                                                                                          data=new_value,
                                                                                                          command_code=command_code,
                                                                                                          offset=offset,
                                                                                                          size=size,
                                                                                                          word_size=word_size))
        if (word_size == 0 or word_size == -1) and is_writable:
            new_register.add_preset('Send', None)
        return self._add_channel(new_register)

    def add_channel_ARA(self, name):
        """Add an SMBus Alert Response Address (ARA) channel.

        Reading this channel issues an ARA transaction on the bus, which
        causes the alerting slave to respond with its own address.  Use
        this to identify which device asserted SMBALERT#.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'add_channel_ARA')
        True

        Args:
            name: Channel name for the ARA response.

        Returns:
            The newly created ARA channel instance.
        """
        ARA_channel = lab_core.channel(
            name, read_function=self._interface.alert_response)
        return self._add_channel(ARA_channel)

    def _dummy_read(self):
        raise Exception("Shouldn't be here!")

    def get_command_codes(self, register_list):
        """Return the sorted, deduplicated command codes needed to read the given registers.

        Examines each register's readability and caching status to
        determine which command codes must actually be sent on the bus.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'get_command_codes')
        True

        Args:
            register_list: Iterable of ``twi_register`` channel objects
                whose command codes are needed.

        Returns:
            Sorted list of unique integer command codes.

        Raises:
            ChannelAccessException: If a non-readable, non-cached
                register is included in the list.
        """
        command_codes = []
        for register in register_list:
            if register.is_readable() and not register.get_attribute('read_caching'):
                command_codes.append(register.get_attribute('command_code'))
            elif not register.get_attribute('read_caching'):
                raise lab_core.ChannelAccessException(
                    'Read a non-readable channel')
        return sorted(list(set(command_codes)))  # filter unique

    def get_readable_command_codes(self, register_list):
        """Return command codes for all readable registers in the list.

        Not used for normal delegated reads.  Useful when constructing a
        command-code list for external tools such as Linduino streaming.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'get_readable_command_codes')
        True

        Args:
            register_list: Iterable of channel objects to inspect.

        Returns:
            Sorted list of unique integer command codes for the readable
            subset of *register_list*.
        """
        return self.get_command_codes([channel for channel in register_list if channel.is_readable(
        ) and 'command_code' in channel.get_attributes()])

    def read_delegated_channel_list(self, register_list):
        """Batch-read all registers in *register_list* via the I2C bus.

        Groups registers by word size, issues one
        ``read_register_list`` call per group, then extracts each
        bitfield from the raw register data.  Cached registers are
        returned from their local cache instead.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'read_delegated_channel_list')
        True

        Args:
            register_list: Iterable of ``twi_register`` channels to read.

        Returns:
            ``results_ord_dict`` mapping channel name → read value.
        """
        start_streaming = False
        cc_data = {}
        for data_size in set([ch.get_attribute('word_size')
                             for ch in register_list]):
            command_codes = self.get_command_codes(
                [ch for ch in register_list if ch.get_attribute('word_size') == data_size])
            # skip all reading if len(command_codes) == 0
            # if len(command_codes) == 1:
            # function = lambda: {command_codes[0]: self._interface.read_register(self._addr7, command_codes[0], data_size, self._PEC)}
            # debug_logging.debug("TWI instrument reading register %s from %s", command_codes[0], self._addr7)
            # elif len(command_codes) > 1:
            # if command_codes == self._previous_command_codes and not self._PEC and self._streaming_enabled:
            # function = lambda: self._interface.read_streaming_word_list()
            # else:
            # self._previous_command_codes = command_codes
            # function = lambda: self._interface.read_register_list(self._addr7, command_codes, data_size, self._PEC)
            # debug_logging.debug("TWI instrument reading %s registers from %s", len(command_codes), self._addr7)
            # if self._streaming_enabled:
            # start_streaming = True

            def function():
                """Read all command codes for one word-size group.

                Performs the described operation on the object's internal state.

                >>> from PyICe.twi_instrument import twi_instrument
                >>> hasattr(twi_instrument, 'function')
                True

                """
                return self._interface.read_register_list(
                    self._addr7, command_codes, data_size, self._PEC)
            debug_logging.debug(
                "TWI instrument reading %s registers from %s",
                len(command_codes),
                self._addr7)
            raw_data = self._twi_try_function(function)
            if raw_data is None:
                raw_data = lab_core.results_ord_dict(
                    [(cc, None) for cc in command_codes])
            cc_data.update(raw_data)
        if start_streaming:
            self._interface.enable_streaming_word_list()
        results = lab_core.results_ord_dict()
        for register in register_list:
            if register.get_attribute("read_caching"):
                results[register.get_name()] = register.read_without_delegator()
            else:
                register_data = self._extract(data=cc_data[register.get_attribute(
                    'command_code')], size=register.get_attribute('size'), offset=register.get_attribute('offset'))
                results[register.get_name()] = register.read_without_delegator(
                    force_data=True, data=register_data)
        return results

    def _twi_try_function(self, function):
        try_count = self.retry_count + 1
        while True:
            try_count -= 1
            try:
                return function()
            except (twi_interface.i2cError, twi_interface.i2cMasterError) as e:
                print(traceback.format_exc())
                try:
                    self._interface.resync_communication()
                except (twi_interface.i2cError, twi_interface.i2cMasterError) as init_err:
                    if (self.except_on_i2cInitError):
                        raise init_err
                    else:
                        print(traceback.format_exc())
                if try_count <= 0:
                    if (self.except_on_i2cCommError):
                        raise e
                    else:
                        print(
                            "{}:  twi transaction failed: {}".format(
                                self.get_name(),
                                traceback.format_exc()))
                        return None

    def _extract(self, data, size, offset):
        if data is None or isinstance(data, lab_core.ChannelReadException):
            return data
        mask = (2**size - 1) << offset
        return (data & mask) >> offset

    def _replace(self, bf_data, bf_size, bf_offset, reg_data, reg_size):
        # Step 1: Safety checks
        assert reg_size >= bf_offset + bf_size

        # Step 2: Compute mask
        mask = (2**bf_size - 1) << bf_offset
        mask_inv = (2**reg_size - 1) ^ mask

        # Step 3: Clear out space
        reg_data = reg_data & mask_inv

        # Step 4: Align
        if bf_data > 2**bf_size - 1:
            oversize_data = bf_data
            bf_data = 2**bf_size - 1
            print(
                f"Data {oversize_data} doesn't fit into register of size {bf_size}! Clipping at {bf_data}")
        elif bf_data < 0:
            undersize_data = bf_data
            bf_data = 0
            print(
                f"Negative data {undersize_data} not valid for register! Clipping at {bf_data}")
        bf_data = (bf_data << bf_offset) & mask

        # Step 5: Insert
        reg_data = reg_data | bf_data
        reg_data &= 2**reg_size - 1  # necessary with offset/size assert?
        return reg_data

    def get_bitfield_writeback_data(
            self, addr7, data, command_code, size, offset, word_size):
        """Return the bitfield writeback data.

        Returns the stored bitfield writeback data from the object's internal state.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'get_bitfield_writeback_data')
        True

        Args:
            addr7: 7-bit I2C device address.
            command_code: Register command code byte.
            data: Data to write.
            offset: Offset value.
            size: Size in bits.
            word_size: Data word width in bits.

        Raises:
            Exception: If an unexpected error occurs.
        """
        raise Exception(
            'Code cleanup 2024/05/08. Switch to new method name compute_rmw_writeback_data() with new calling and return signature.')

    def compute_rmw_writeback_data(self, data, addr7, command_code, size,
                                   offset, word_size, is_readable=True, overwrite_others=False):
        """Read whole (atmoic) register.

        Replace any slices unrelated to the write slice based on each constituent bitfield's RWM value preference
        Replace slice related to the write with the new data.

        Parameters
        ----------
        data : int
            Bitfield write data, right aligned.
        addr7 : int
            Chip address in 7-bit (no R/W bit) format.
        command_code : int
            Memory address of register/bitfield
        size : int
            Slice width of bitfield within register
        offset : int
            LSB position of bitfield slice within register
        word_size : int
            Register width
        is_readable : bool
            Does register have read access?
        overwrite_others : bool
            Skip readback. Instead assume register content is 0 before replacing slices.

        Returns
        -------
        (int, int)
            Register writeback data and command code tuple.

        Raises
        -------
        Exception
            Various consistency errors. Abnormal.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'compute_rmw_writeback_data')
        True

        Args:
            addr7: 7-bit I2C device address.
            command_code: Register command code byte.
            data: Data to write.
            is_readable: Is readable to use.
            offset: Offset value.
            overwrite_others: Overwrite others to use.
            size: Size in bits.
            word_size: Data word width in bits.

        Returns:
            The result of the operation.

        Raises:
            Exception: If an unexpected error occurs.
        """
        # Step 1: get existing data across whole register width
        if data is None and word_size == 0:
            # send_byte
            pass
        elif data is None and word_size == -1:
            raise Exception('quick_cmd not yet fully implemented.')
        else:
            def function():
                """Return the function.

                Performs a register-level transaction over the communication bus.


                >>> from PyICe.twi_instrument import twi_instrument
                >>> hasattr(twi_instrument, 'function')
                True

                Returns:
                    The function result.
                """
                return self._interface.read_register(
                    addr7, command_code, word_size, self._PEC)
            # read the data
            if size == word_size:
                old_data = 0
            elif not is_readable:
                old_data = 0
            elif overwrite_others:
                old_data = 0
            else:
                old_data = self._twi_try_function(function)
                if old_data is None:
                    # print("i2c_write pre-read failed, not writing")
                    # return
                    # todo specific exception?
                    raise Exception("i2c_write pre-read failed, not writing")

            # Step 2: modify old data according to register special access
            # rules

            bitfields = []
            for each_channel in self.get_all_channels_list():
                try:
                    if each_channel.get_attribute(
                            'command_code') == command_code:
                        bitfields.append(each_channel)
                except lab_core.ChannelAttributeException:
                    # Not a real bitfield
                    pass
            for bf in bitfields:
                rmw_data = bf.compute_rmw_writeback_data(self._extract(data=old_data,
                                                                       size=bf.get_attribute(
                                                                           'size'),
                                                                       offset=bf.get_attribute(
                                                                           'offset')
                                                                       )
                                                         )
                old_data = self._replace(bf_data=rmw_data,
                                         bf_size=bf.get_attribute('size'),
                                         bf_offset=bf.get_attribute('offset'),
                                         reg_data=old_data,
                                         reg_size=word_size
                                         )
            # Step 3: modify old data according to write value
            data = int(data)
            data = self._replace(bf_data=data,
                                 bf_size=size,
                                 bf_offset=offset,
                                 reg_data=old_data,
                                 reg_size=word_size
                                 )

        return (data, command_code)

    def _read_merge_write(self, data, addr7, command_code,
                          size, offset, word_size, is_readable, overwrite_others):
        new_data = self.compute_rmw_writeback_data(data=data,
                                                   addr7=addr7,
                                                   command_code=command_code,
                                                   size=size,
                                                   offset=offset,
                                                   word_size=word_size,
                                                   is_readable=is_readable,
                                                   overwrite_others=overwrite_others
                                                   )
        self._twi_try_function(lambda: self._interface.write_register(addr7=addr7,
                                                                      commandCode=new_data[1],
                                                                      data=new_data[0],
                                                                      data_size=word_size,
                                                                      use_pec=self._PEC))

    def enable_cached_read(self, include_readable_registers=False):
        """Disable remote read of writable register and instead return cached previous write.

        only affects write-only register by default. include_readable_registers argument also includes read-write registers.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'enable_cached_read')
        True

        Args:
            include_readable_registers: Include readable registers to use.
        """
        for register in self:
            if register.is_writeable():
                if not register.is_readable() or include_readable_registers:
                    register.enable_cached_read()

    def populate_from_file(self, xml_file, format_dict=None, access_list=None,
                           use_case=None, channel_prefix="", channel_suffix=""):
        """Parse xml_register file complying with register_map.dtd and populate instrument channels.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'populate_from_file')
        True

        Args:
            xml_file: Path to XML register map file.
            format_dict: Dictionary of format definitions. Default empty dict.
            access_list: List of access modes to include. Default all.
            use_case: Use case name to filter by, or None for all.
            channel_prefix: Prefix string for channel names.
            channel_suffix: Suffix string for channel names.

        Raises:
            Exception: On XML parsing or register configuration errors.
        """
        if format_dict is None:
            format_dict = {}
        if access_list is None:
            access_list = []
        xml_reg_map = ET.parse(xml_file).getroot()
        chip = xml_reg_map.find("./chip")
        addr7 = str2num(chip.find("./address").attrib["address_7bit"])
        chip_name = chip.attrib["name"]
        self.set_name(chip_name)
        word_size = str2num(chip.attrib["word_size"])
        # extract all the xml formats into self._xml_formats
        self._xml_formats = {}
        for fmt_def in xml_reg_map.findall('.//format_definition'):
            name = fmt_def.attrib['name']
            desc = fmt_def.find('./description').text
            units = fmt_def.find('./transformed_units').text
            signed = fmt_def.attrib['signed'] in ["True", "true", "1"]
            points = fmt_def.findall('./piecewise_linear_points/point')
            xlist = []
            ylist = []
            for xpoints in points:
                xlist.append(xpoints.attrib['native'])
            for ypoints in points:
                ylist.append(ypoints.attrib['transformed'])
            points = list(zip(xlist, ylist))
            self._xml_formats[name] = {
                'points': points,
                'description': desc,
                'signed': signed,
                'units': units}
        # extract constant definitions
        for constant in xml_reg_map.findall('.//constant_definition'):
            self._constants[constant.attrib['name']] = constant.attrib['value']
        # generate actual formats using the xml formats
        self._update_xml_formatters()
        # Check which bit fields are allowed to become channels. use_case=None
        # results in no filtering.
        if use_case is None:
            self.categories = None
        else:
            self.categories = []
            for category in xml_reg_map.findall(
                    "./use[@name='{}']/category".format(use_case)):
                self.categories.append(category.text)
        # now extract the bit fields
        for physical_register in chip.findall("./command_code"):
            command_code = str2num(physical_register.attrib['value'])
            is_readable = False
            is_writable = False
            for access in physical_register.findall("./access"):
                if access.attrib['mode'] in access_list or access_list == []:
                    if access.attrib['type'] == 'read':
                        is_readable = True
                    if access.attrib['type'] == 'write':
                        is_writable = True
            if not (is_writable or is_readable):
                continue
            # MAYBE INCLUDE FULL REGISTER ACCESS HERE
            for bit_field in physical_register.findall('./bit_field'):
                # tag attributes
                name = channel_prefix + \
                    bit_field.attrib['name'] + channel_suffix
                category = bit_field.attrib['category']
                size = str2num(bit_field.attrib['size'])
                offset = str2num(bit_field.attrib['offset'])
                default = bit_field.find('./default')
                if default is not None:
                    default = str2num(default.text)
                if self.categories is not None and category not in self.categories:
                    continue  # filter out unauthorized categories for this use_case
                register = self.add_register(
                    name,
                    addr7,
                    command_code,
                    size,
                    offset,
                    word_size,
                    is_readable,
                    is_writable)
                register.set_category(category)
                register.set_attribute("default", default)
                # add presets
                for preset in bit_field.findall('./preset'):
                    if preset.find('./description') is not None:
                        preset_desc = preset.find('./description').text
                    else:
                        preset_desc = None
                    register.add_preset(
                        preset.attrib['name'], str2num(
                            preset.attrib['value']), preset_desc)
                # add additional user formats
                for format in bit_field.findall('./format'):
                    format_name = format.attrib['name']
                    format_definition = [definition for definition in xml_reg_map.findall(
                        ".//format_definition") if definition.attrib['name'] == format_name]
                    if format_name in format_dict and not len(
                            format_definition):
                        register.add_format(
                            format_name,
                            format_dict[format_name]['format'],
                            format_dict[format_name]['unformat'])
                        if len(format_definition):
                            print(
                                "Warning: format dict being used instead of XML for {}".format(format_name))
                    elif len(format_definition):
                        register.add_format(
                            format_name,
                            self.formatters[format_name]['format'],
                            self.formatters[format_name]['unformat'],
                            self.formatters[format_name]['signed'],
                            self.formatters[format_name]['units'],
                            self.formatters[format_name]['xypoints'])
                    else:
                        raise Exception(
                            'Format {} undefined in format_dict and in XML'.format(format_name))
                description = bit_field.find('./description')
                if (description is not None):
                    register.set_description(description.text)

    def populate_from_ipxact(self, ipxact_file, addr7, base_address=0,
                            address_block_name=None, memory_map_name=None,
                            channel_prefix="", channel_suffix="",
                            access_list=None):
        """Populate registers from an IP-XACT (IEEE 1685-2014 or SPIRIT 1685-2009) XML file.

        Parses the IP-XACT component, walks memoryMap → addressBlock → register → field,
        and creates a twi_register channel for each bitfield.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'populate_from_ipxact')
        True

        Args:
            ipxact_file: Path to IP-XACT XML component file.
            addr7: 7-bit I2C slave address.
            base_address: Additional offset added to all register addresses.
            address_block_name: If specified, only import this address block.
            memory_map_name: If specified, only import from this memory map.
            channel_prefix: Prefix string for channel names.
            channel_suffix: Suffix string for channel names.
            access_list: List of IP-XACT access types to include
                (e.g. ["read-write", "read-only"]). None imports all.

        Raises:
            ValueError: If specified memory_map_name or address_block_name not found.
            NotImplementedError: If register arrays (dim > 1) are encountered.
        """
        parser = IpxactParser(ipxact_file)
        memory_maps = parser.parse()
        if memory_map_name is not None:
            memory_maps = [mm for mm in memory_maps if mm.name == memory_map_name]
            if not memory_maps:
                raise ValueError(
                    f"Memory map '{memory_map_name}' not found in {ipxact_file}")
        for mm in memory_maps:
            address_blocks = mm.address_blocks
            if address_block_name is not None:
                address_blocks = [ab for ab in address_blocks
                                  if ab.name == address_block_name]
                if not address_blocks:
                    raise ValueError(
                        f"Address block '{address_block_name}' not found in "
                        f"memory map '{mm.name}'")
            for ab in address_blocks:
                word_size = ab.width
                for reg in ab.registers:
                    command_code = base_address + ab.base_address + reg.address_offset
                    reg_word_size = reg.size if reg.size > 0 else word_size
                    if not reg.fields:
                        is_readable, is_writable = ipxact_access_to_rw(reg.access)
                        if access_list and reg.access not in access_list:
                            continue
                        name = clean_ascii_code(channel_prefix + reg.name + channel_suffix)
                        register = self.add_register(
                            name, addr7, command_code, reg.size, 0,
                            reg_word_size, is_readable, is_writable)
                        register.set_category(ab.name)
                        if reg.description:
                            register.set_description(reg.description)
                        if reg.reset_value is not None:
                            register.set_attribute("default", reg.reset_value)
                        continue
                    for fld in reg.fields:
                        if access_list and fld.access not in access_list:
                            continue
                        is_readable, is_writable = ipxact_access_to_rw(fld.access)
                        name = clean_ascii_code(channel_prefix + fld.name + channel_suffix)
                        register = self.add_register(
                            name, addr7, command_code, fld.bit_width,
                            fld.bit_offset, reg_word_size,
                            is_readable, is_writable)
                        register.set_category(ab.name)
                        if fld.description:
                            register.set_description(fld.description)
                        if fld.reset_value is not None:
                            register.set_attribute("default", fld.reset_value)
                        if fld.modified_write_value:
                            pyice_access = ipxact_modified_write_to_pyice(
                                fld.modified_write_value)
                            if pyice_access is not None:
                                register.set_special_access(pyice_access)
                        for ev_name, ev_value, ev_desc in fld.enumerated_values:
                            register.add_preset(ev_name, ev_value, ev_desc or None)

    def populate_from_yoda_json_bridge(
            self, filename, i2c_addr7, extended_addressing=False):
        """Perform populate from yoda json bridge operation.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'populate_from_yoda_json_bridge')
        True

        Args:
            extended_addressing: Extended addressing to use.
            filename: File path.
            i2c_addr7: I2c addr7 to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
        with open(filename, 'r') as fp:
            registers = json.load(fp)
        for reg in registers:
            if len(reg['bitfields']) > 1:
                overwrite_others = False
            else:
                overwrite_others = True
            for name, bf in list(reg['bitfields'].items()):
                if extended_addressing:
                    command_code = reg["address"] % 2**reg['width']
                    slave_addr = i2c_addr7 + \
                        int(reg["address"] / 2**reg['width'])
                else:
                    command_code = reg["address"]
                    slave_addr = i2c_addr7
                size = bf['slicewidth']
                offset = bf['regoffset']
                word_size = reg['width']
                is_readable = "R" in bf['access']
                is_writable = "W" in bf['access']
                register = self.add_register(
                    name,
                    slave_addr,
                    command_code,
                    size,
                    offset,
                    word_size,
                    is_readable,
                    is_writable,
                    overwrite_others)
                try:
                    bf['write_side_effect']
                except KeyError:
                    # Old schema
                    pass
                else:
                    if bf['write_side_effect'] == 'None':
                        pass
                    elif bf['write_side_effect'] == 'OneToClear':
                        assert is_readable, f'Unexpected W1C register without read access: {name}. Contact PyICe developers.'
                        assert is_writable, f'Unexpected W1C register without write access: {name}. Contact PyICe developers.'
                        register.set_special_access('W1C')
                    elif bf['write_side_effect'] == 'OneToSet':
                        assert is_readable, f'Unexpected W1S register without read access: {name}. Contact PyICe developers.'
                        assert is_writable, f'Unexpected W1S register without write access: {name}. Contact PyICe developers.'
                        register.set_special_access('W1S')
                    elif bf['write_side_effect'] == 'ZeroToClear':
                        assert is_readable, f'Unexpected W0C register without read access: {name}. Contact PyICe developers.'
                        assert is_writable, f'Unexpected W0C register without write access: {name}. Contact PyICe developers.'
                        register.set_special_access('W0C')
                    elif bf['write_side_effect'] == 'ZeroToSet':
                        assert is_readable, f'Unexpected W0S register without read access: {name}. Contact PyICe developers.'
                        assert is_writable, f'Unexpected W0S register without write access: {name}. Contact PyICe developers.'
                        register.set_special_access('W0S')
                    elif bf['write_side_effect'] in ('OneToToggle', 'ZeroToToggle', 'Clear', 'Set'):
                        raise Exception(
                            f'Register side effect {bf["write_side_effect"]} not implemented. Contact PyICe developers.')
                    else:
                        raise Exception(
                            f'Register side effect {bf["write_side_effect"]} unknown. Contact PyICe developers.')
                try:
                    bf['data_format']
                except KeyError:
                    # 'data_format' key absent: old register-map schema without type info.
                    # Treat as unsigned; no scaled format is added.
                    pass
                else:
                    # New schema: 'data_format' declares whether the raw field is
                    # 'Unsigned' or 'Signed' two's complement.
                    if bf['data_format'] == 'Unsigned':
                        signed = False
                    elif bf['data_format'] == 'Signed':
                        signed = True
                    else:
                        raise Exception(
                            f'Unknown format {bf["data_format"]}. Contact PyICe developers.')
                    if signed and size > 1:
                        # Register a human-readable signed-decimal display format and
                        # tag the channel so that GUI / format helpers know the
                        # signedness.
                        register.set_format('signed dec')
                        register.set_attribute('signed', True)
                    elif signed:
                        # A 1-bit field declared Signed is technically a sign bit with no
                        # magnitude bits, which is nonsensical for most
                        # use-cases.
                        print(
                            f'WARNING: bit field {name} nonsensically declared signed with size {size}.')
                    try:
                        bf['format']
                    except KeyError:
                        # No linear scaling defined — the raw (or signed-decimal) format is
                        # the only display format for this field.
                        pass
                    else:
                        # 'format' subkey provides a linear y = scale*x + offset transform
                        # ('yoda' is the internal name for this schema family).
                        # The 'yoda_scaled' format converts between raw integer and physical
                        # units (e.g. raw LSBs → millivolts).
                        # TODO: pass xypoints derived from the scale/offset so that SQL
                        # reproduction of the transform works without
                        # re-parsing the schema.
                        register.add_format('yoda_scaled',
                                            format_function=lambda i, m=bf['format'][
                                                'scale'], b=bf['format']['offset']: i * m + b,
                                            unformat_function=lambda f, m=bf['format']['scale'], b=bf['format']['offset']: int(
                                                round((f - b) / m)),
                                            signed=signed,
                                            units=bf['format']['units'] if bf['format']['units'] is not None else '',
                                            xypoints=[])
                if len(reg["functionalgroups"]) != 0:
                    if str(reg["functionalgroups"][0]) == '':
                        register.set_category("BlankFunctionalGroup")
                    else:
                        register.set_category(str(reg["functionalgroups"][0]))
                else:
                    register.set_category("NoFunctionalGroup")
                if len(reg["functionalgroups"]) > 1:
                    register.add_tags(reg["functionalgroups"][1:])
                register.set_description(bf['documentation'])
                if len(bf["enums"]):
                    for name, value in list(bf["enums"].items()):
                        register.add_preset(name, value)

    def create_format(self, format_name, format_function, unformat_function,
                      signed=False, description=None, units='', xypoints=None):
        """Create a new format definition or modify an existing definition.

        format_function should take a single argument of integer raw data from the register and return a version of the data scaled to appropriate units.
        unformat_function should take a single argument of data in real units and return an integer version of the data scaled to the register LSB weight.
        If the data is signed in two's-complement format, set signed=True.
        After creating format, use set_active_format method to make the new format active.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'create_format')
        True

        Args:
            description: Description string.
            format_function: Format function to use.
            format_name: Name of the format.
            signed: If True, interpret as signed value.
            unformat_function: Unformat function to use.
            units: Unit string.
            xypoints: Xypoints to use.
        """
        if xypoints is None:
            xypoints = []
        self.formatters[format_name] = {
            'format': format_function,
            'unformat': unformat_function,
            'description': description,
            'signed': signed,
            'units': units,
            'xypoints': xypoints}

    def set_constant(self, constant, value):
        """Sets the constants found in the datasheet used by the formatters to convert from real world values to digital value and back.

        Updates the constant in the object's internal state.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'set_constant')
        True

        Args:
            constant: Constant to use.
            value: Value to set.
        """
        self._constants[constant] = value
        self._update_xml_formatters()

    def get_constant(self, constant):
        """Sets the constants found in the datasheet used by the formatters to convert from real world values to digital value and back.
        Returns the stored constant value from the object's internal state.
        Returns the stored constant from the object's internal state.

        Returns the stored constant from the object's internal state.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'get_constant')
        True

        Args:
            constant: Constant to use.

        Returns:
            The current constant.
        """
        return self._constants[constant]

    def list_constants(self):
        """Returns the list of constants found in the datasheet used by the formatters to convert from real world values to digital value and back.

        Transforms the input data into the required output form.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, 'list_constants')
        True

        Returns:
            List of matching items.
        """
        return self._constants

    def _update_xml_formatters(self):
        self.create_format(format_name='None',
                           format_function=lambda x: x,
                           unformat_function=lambda x: x,
                           signed=False,
                           description='''No formatting applied to data.''',
                           units='')
        for fmt_name in self._xml_formats:
            xyevalpoints = self._evaluated_points(
                self._xml_formats[fmt_name]["points"])
            self.create_format(format_name=fmt_name,
                               format_function=self._transform_from_points(
                                   xyevalpoints, "format"),
                               unformat_function=self._transform_from_points(
                                   xyevalpoints, "unformat"),
                               signed=self._xml_formats[fmt_name]["signed"],
                               description=self._xml_formats[fmt_name]["description"],
                               units=self._xml_formats[fmt_name]["units"],
                               xypoints=xyevalpoints)

    def _transform_from_points(self, xyevalpoints, direction):
        """Used internally to convert from register values to real world values and back again.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.twi_instrument import twi_instrument
        >>> hasattr(twi_instrument, '_transform_from_points')
        True

        Args:
            direction: Direction of operation (e.g. ``"up"``/``"down"``).
            xyevalpoints: Xyevalpoints to use.

        Returns:
            The transform from points result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if not SCIPY_MISSING:
            x_evaled, y_evaled = list(zip(*xyevalpoints))
            if direction == "format":
                z = sorted(zip(x_evaled, y_evaled), key=lambda x: x[0])
                z_unzipped = list(zip(*z))
                z_x, z_y = z_unzipped[0], z_unzipped[1]
                return lambda x: None if x is None else float(
                    UnivariateSpline(x=z_x, y=z_y, k=1, s=0)(x))
            elif direction == "unformat":
                z = sorted(zip(x_evaled, y_evaled), key=lambda x: x[1])
                z_unzipped = list(zip(*z))
                z_y, z_x = z_unzipped[1], z_unzipped[0]
                return lambda x: int(round(UnivariateSpline(
                    x=z_y, y=z_x, k=1, s=0)(float(x))))
            else:
                raise Exception(
                    "'transform_from_points()' requires one of either: 'format' or 'unformat'")
        else:
            # revert to PyICe.lab_utils.interpolator
            if direction == "format":
                return lambda x: None if x is None else float(
                    interpolator(xyevalpoints)(x))
            elif direction == "unformat":
                return lambda y: int(
                    round(interpolator(xyevalpoints).get_x_val(float(y))))
            else:
                raise Exception(
                    "'transform_from_points()' requires one of either: 'format' or 'unformat'")

    def _evaluated_points(self, xypoints):
        eval_constants = {}
        eval_constants.update(self._constants)
        # eval allows expressions within XML constants
        eval_constants = {key: float(eval(value))
                          for key, value in self._constants.items()}
        return [(eval(point[0], eval_constants), eval(
            point[1], eval_constants)) for point in xypoints]


class twi_register(lab_core.register):
    """Twi_register.

    >>> from PyICe.twi_instrument import twi_register
    >>> twi_register is not None
    True

    """
    pass
    # 2024/05/07 DJS: This code appears unused. Prove me wrong.
    # def calculate_cc_merge_bf(self, bf_data):
    #     addr = self.get_attribute('chip_address7')
    #     cc = self.get_attribute('command_code')
    #     offset = self.get_attribute('offset')
    #     size = self.get_attribute('size')
    #     word_size = self.get_attribute('word_size')
    #     iface = next(iter(self.get_interfaces()))
    #     old_data = iface.read_register(addr7=addr, commandCode=cc, data_size=word_size, use_pec=self.get_delegator()._PEC)
    #     if bf_data > 2**size-1:
    #         raise Exception(f"Bitfield data too large for bitfield of size = {size}")
    #     new_data = old_data & ~((2**size-1)<<offset)
    #     new_data = new_data | (bf_data<<offset)
    #     return (new_data, cc)


class pmbus_instrument(twi_instrument):
    """Pmbus_instrument (twi_instrument subclass).

    >>> from PyICe.twi_instrument import pmbus_instrument
    >>> pmbus_instrument is not None
    True

    """
    def __init__(self, interface_twi, except_on_i2cInitError=True,
                 except_on_i2cCommError=False, retry_count=5, PEC=False):
        """Initialize pmbus_instrument.
        Stores configuration in ``pmbus_commands`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.twi_instrument import pmbus_instrument
        >>> hasattr(pmbus_instrument, '__init__')
        True

        Args:
            PEC: Pec to use.
            except_on_i2cCommError: Except on i2ccommerror to use.
            except_on_i2cInitError: Except on i2ciniterror to use.
            interface_twi: TWI/I2C interface instance.
            retry_count: Retry count to use.
        """
        twi_instrument.__init__(
            self,
            interface_twi,
            except_on_i2cInitError,
            except_on_i2cCommError,
            retry_count,
            PEC)
        self.pmbus_commands = {
            'PAGE': 0x00,
            'PHASE': 0x04,
        }

    def add_register(self, name, addr7, page, command_code,
                     size, offset, word_size, is_readable, is_writable):
        """Add a register.
        Creates and registers a new register.

        Appends a new register entry to the object's internal collection.


        >>> from PyICe.twi_instrument import pmbus_instrument
        >>> hasattr(pmbus_instrument, 'add_register')
        True

        Args:
            addr7: 7-bit I2C device address.
            command_code: Register command code byte.
            is_readable: Is readable to use.
            is_writable: Is writable to use.
            name: Name identifier.
            offset: Offset value.
            page: PMBus page number for multi-output devices.
            size: Size in bits.
            word_size: Data word width in bits.

        Returns:
            The add register result.
        """
        def paged_write(data, channel):
            """Return paged write result.

            Performs the described operation on the object's internal state.


            >>> from PyICe.twi_instrument import pmbus_instrument
            >>> hasattr(pmbus_instrument, 'paged_write')
            True

            Args:
                channel: Channel object.
                data: Data to write.

            Returns:
                The paged write result.
            """
            self.set_page(channel.get_attribute('page'))
            return channel.pmbus_unpaged_write(data)
        new_register = twi_instrument.add_register(
            self,
            name,
            addr7,
            command_code,
            size,
            offset,
            word_size,
            is_readable,
            is_writable
        )
        new_register.set_attribute('page', page)
        new_register.pmbus_unpaged_write = new_register._write
        new_register._write = lambda data: paged_write(data, new_register)
        return new_register

    def set_page(self, page):
        """Set the page.

        Performs a register-level transaction over the communication bus.


        >>> from PyICe.twi_instrument import pmbus_instrument
        >>> hasattr(pmbus_instrument, 'set_page')
        True

        Args:
            page: PMBus page number for multi-output devices.
        """
        if page is not None:
            self._interface.write_register(
                addr7=self._addr7,
                commandCode=self.pmbus_commands['PAGE'],
                data=page,
                data_size=8,
                use_pec=self._PEC)
            debug_logging.debug(
                "PMBus instrument at %s setting page register to %s",
                self._addr7,
                page)

    def read_delegated_channel_list(self, register_list):
        """Return read delegated channel list result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.twi_instrument import pmbus_instrument
        >>> hasattr(pmbus_instrument, 'read_delegated_channel_list')
        True

        Args:
            register_list: Register list to use.

        Returns:
            The value read from the device or channel.
        """
        results = lab_core.results_ord_dict()
        pages = set([ch.get_attribute('page') for ch in register_list])
        merge_none = False
        if len(pages) > 1 and None in pages:
            pages -= set([None])
            merge_none = True
        for idx, page in enumerate(pages):
            if page is not None:
                self.set_page(page)
            # speed up slightly by merging None pages with the first non-None
            # page, if None and non-None pages are both in the register_list
            results.update(twi_instrument.read_delegated_channel_list(self, [ch for ch in register_list if ch.get_attribute(
                'page') == page or merge_none and not idx and ch.get_attribute('page') is None]))
        return results


class twi_instrument_dummy(twi_instrument):
    """Use for formatters, etc without having to set up a master and physical hardware.

    >>> from PyICe.twi_instrument import twi_instrument_dummy
    >>> twi_instrument_dummy is not None
    True

    """

    def __init__(self):
        """Initialize twi_instrument_dummy.

        Stores configuration in ``_addr7``, ``_constants``, ``formatters`` for
        use by other methods.

        >>> from PyICe.twi_instrument import twi_instrument_dummy
        >>> twi_instrument_dummy is not None
        True

        """
        lab_core.instrument.__init__(self, name="twi_instrument_dummy")
        self._addr7 = None
        self.formatters = {}
        self._constants = {}


if __name__ == "__main__":
    from . import lab_core  # noqa: F811
    m = lab_core.master()
    twi_ifc = m.get_twi_dummy_interface()
    twi = twi_instrument(twi_ifc)
    twi.populate_from_file(
        "./xml_registers/EXAMPLE/LTC3350.xml",
        format_dict={},
        access_list=['user'],
        use_case="demo")
