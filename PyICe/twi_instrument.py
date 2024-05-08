'''
Channel Wraper for SMBus Compliant Devices
==========================================

Can automatically populate channels/reisters from XML description
'''
from . import lab_core
from . import twi_interface
import xml.etree.ElementTree as ET
from PyICe.lab_utils.str2num import str2num
from PyICe.lab_utils.interpolator import interpolator
import json

try:
    from scipy.interpolate import UnivariateSpline
except ImportError:
    SCIPY_MISSING = True
    print("SciPy not found. Reverting to Python piecewise linear interpolator/extrapolator for formats.")
SCIPY_MISSING = True #Force Python interpolator instead of spline

import logging
debug_logging = logging.getLogger(__name__)

class twi_instrument(lab_core.instrument,lab_core.delegator):
    def __init__(self,interface_twi,except_on_i2cInitError=True,except_on_i2cCommError=False,retry_count=5,PEC=False):
        lab_core.instrument.__init__(self,name=None)
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
    def add_register(self,name,addr7,command_code,size,offset,word_size,is_readable,is_writable,overwrite_others=False):
        if self._addr7 != addr7:
            if self._addr7 is None:
              self._addr7 = addr7 #first time
            else:
              raise Exception('twi_instrument only supports one chip i2c address.'
                              'Consider making a second twi_instrument instance.')
        new_register = twi_register(name, size,
                                    read_function = self._dummy_read,
                                    write_function = lambda data : self._read_merge_write(data,addr7,command_code,size,offset,word_size,is_readable,overwrite_others))
        new_register.set_delegator(self)
        new_register.set_attribute("chip_address7",addr7)
        new_register.set_read_access(is_readable)
        new_register.set_write_access(is_writable)
        new_register.set_attribute("offset",offset)
        new_register.set_attribute("command_code",command_code)
        new_register.set_attribute("word_size",word_size)
        new_register.set_attribute("command_code_and_rmw_value", lambda new_value,
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
        ARA_channel = lab_core.channel(name, read_function=self._interface.alert_response)
        return self._add_channel(ARA_channel)
    def _dummy_read(self):
        raise Exception("Shouldn't be here!")
    def get_command_codes(self, register_list):
        command_codes = []
        for register in register_list:
            if register.is_readable() and not register.get_attribute('read_caching'):
                command_codes.append(register.get_attribute('command_code'))
            elif not register.get_attribute('read_caching'):
                raise lab_core.ChannelAccessException('Read a non-readable channel')
        return sorted(list(set(command_codes))) #filter unique
    def get_readable_command_codes(self, register_list):
        '''returns list of command codes required to read all readable registers within register_list
        not used for normal delegated reads. helpful to construct command code list for use with other tools (Linduino streaming for example)'''
        return self.get_command_codes([channel for channel in register_list if channel.is_readable() and 'command_code' in channel.get_attributes()])
    def read_delegated_channel_list(self,register_list):
        start_streaming = False
        cc_data = {}
        for data_size in set([ch.get_attribute('word_size') for ch in register_list]):
            command_codes = self.get_command_codes([ch for ch in register_list if ch.get_attribute('word_size') == data_size])
            #skip all reading if len(command_codes) == 0
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
            function = lambda: self._interface.read_register_list(self._addr7, command_codes, data_size, self._PEC)
            debug_logging.debug("TWI instrument reading %s registers from %s", len(command_codes), self._addr7)
            raw_data = self._twi_try_function(function)
            if raw_data is None:
                raw_data = lab_core.results_ord_dict([(cc, None) for cc in command_codes])
            cc_data.update(raw_data)
        if start_streaming:
            self._interface.enable_streaming_word_list()
        results = lab_core.results_ord_dict()
        for register in register_list:
            if register.get_attribute("read_caching"):
                results[register.get_name()] = register.read_without_delegator()
            else:                
                register_data = self._extract(data=cc_data[register.get_attribute('command_code')],size=register.get_attribute('size'),offset=register.get_attribute('offset'))
                results[register.get_name()] = register.read_without_delegator(force_data = True, data = register_data)
        return results
    def _twi_try_function(self,function):
        try_count = self.retry_count + 1
        while True:
            try_count -= 1
            try:
                return function()
            except (twi_interface.i2cError,twi_interface.i2cMasterError) as e:
                print(e)
                try:
                    self._interface.resync_communication()
                except (twi_interface.i2cError,twi_interface.i2cMasterError) as init_err:
                    if (self.except_on_i2cInitError):
                        raise init_err
                    else:
                        print(init_err)
                if try_count <= 0:
                    if (self.except_on_i2cCommError):
                        raise e
                    else:
                        print("{}:  twi transaction failed: {}".format(self.get_name(), e))
                        return None
    def _extract(self,data,size,offset):
        if data is None or isinstance(data, lab_core.ChannelReadException):
            return data
        mask = (2**size-1) << offset
        return (data & mask)>> offset
    def _replace(self, bf_data, bf_size, bf_offset, reg_data, reg_size):
        # Step 1: Safety checks
        assert reg_size >= bf_offset + bf_size

        # Step 2: Compute mask        
        mask = (2**bf_size-1) << bf_offset
        mask_inv = (2**reg_size-1) ^ mask

        # Step 3: Clear out space
        reg_data = reg_data & mask_inv

        # Step 4: Align
        if bf_data > 2**bf_size-1:
            oversize_data = bf_data
            bf_data = 2**bf_size-1
            print(f"Data {oversize_data} doesn't fit into register of size {bf_size}! Clipping at {bf_data}")
        elif bf_data < 0:
            undersize_data = bf_data
            bf_data = 0
            print(f"Negative data {undersize_data} not valid for register! Clipping at {bf_data}")
        bf_data = (bf_data << bf_offset) & mask

        # Step 5: Insert
        reg_data = reg_data | bf_data
        reg_data &= 2**reg_size-1 #necessary with offset/size assert?
        return reg_data    

    def get_bitfield_writeback_data(self, addr7, data, command_code, size, offset, word_size):
        raise Exception('Code cleanup 2024/05/08. Switch to new method name compute_rmw_writeback_data() with new calling and return signature.')
    def compute_rmw_writeback_data(self, data, addr7, command_code, size, offset, word_size, is_readable=True, overwrite_others=False):
        # Step 1: get existing data across whole register width
        if data is None and word_size == 0:
            #send_byte
            pass
        elif data is None and word_size == -1:
            raise Exception('quick_cmd not yet fully implemented.')
        else:
            function = lambda: self._interface.read_register(addr7, command_code, word_size, self._PEC)
            #read the data
            if size == word_size:
                old_data = 0
            elif not is_readable:
                old_data = 0
            elif overwrite_others:
                old_data = 0
            else:
                old_data = self._twi_try_function(function)
                if old_data == None:
                    # print("i2c_write pre-read failed, not writing")
                    # return
                    raise Exception("i2c_write pre-read failed, not writing") #todo specific exception?


            # Step 2: modify old data according to register special access rules
            bitfields = [bf for bf in self.get_all_channels_list() if bf.get_attribute('command_code') == command_code]
            for bf in bitfields:
                rmw_data = bf.compute_rmw_writeback_data(self._extract(data   = old_data,
                                                                       size   = bf.get_attribute('size'),
                                                                       offset = bf.get_attribute('offset')
                                                                      )
                                                        )
                old_data = self._replace(bf_data   = rmw_data,
                                         bf_size   = bf.get_attribute('size'),
                                         bf_offset = bf.get_attribute('offset'),
                                         reg_data  = old_data,
                                         reg_size  = word_size
                                         )
            # Step 3: modify old data according to write value
            data = int(data)
            data =  self._replace(bf_data   = data,
                                      bf_size   = size,
                                      bf_offset = offset,
                                      reg_data  = old_data,
                                      reg_size  = word_size
                                      )

        return (data, command_code)
    def _read_merge_write(self,data,addr7,command_code,size,offset,word_size,is_readable,overwrite_others):
        new_data = self.compute_rmw_writeback_data(data = data,
                                                  addr7 = addr7,
                                                  command_code = command_code,
                                                  size = size,
                                                  offset = offset,
                                                  word_size = word_size,
                                                  is_readable=is_readable,
                                                  overwrite_others=overwrite_others
                                                 )
        self._twi_try_function(lambda: self._interface.write_register(addr7 = addr7,
                                                                      commandCode = new_data[1],
                                                                      data = new_data[0],
                                                                      data_size = word_size,
                                                                      use_pec = self._PEC))
    def enable_cached_read(self, include_readable_registers=False):
        '''disable remote read of writable register and instead return cached previous write.
        only affects write-only register by default. include_readable_registers argument also includes read-write registers.'''
        for register in self:
            if register.is_writeable():
                if not register.is_readable() or include_readable_registers:
                    register.enable_cached_read()
    def populate_from_file(self ,xml_file, format_dict={}, access_list=[], use_case=None, channel_prefix="", channel_suffix=""):
        '''
        xml_register parsing accepts xml input complying with the following DTD (register_map.dtd):

    <!-- Visit http://en.wikipedia.org/wiki/Document_Type_Definition for an excellent explanation of DTD syntax -->
    <!ELEMENT register_map (chip+, use*, format_definitions?)>
    <!ELEMENT chip (description, address+, command_code*)>
    <!ELEMENT address EMPTY>
    <!ELEMENT command_code (description?, access+, bit_field+)>
    <!ELEMENT access EMPTY>
    <!ELEMENT bit_field (description, default?, preset*, format*)>
    <!ELEMENT description (#PCDATA)>
    <!ELEMENT default (#PCDATA)>
    <!ELEMENT preset (description?)>
    <!ELEMENT format EMPTY>
    <!ELEMENT use (category+)>
    <!ELEMENT category (#PCDATA)>
    <!ELEMENT format_definitions (format_definition+)>
    <!ELEMENT format_definition (description, transformed_units?, piecewise_linear_points?)>
    <!ELEMENT transformed_units (#PCDATA)>
    <!ELEMENT piecewise_linear_points (point,point+)>
    <!ELEMENT point EMPTY>
    <!ATTLIST chip name CDATA #REQUIRED word_size CDATA #REQUIRED>
    <!ATTLIST address address_7bit CDATA #REQUIRED>
    <!ATTLIST command_code name ID #REQUIRED value CDATA #REQUIRED>
    <!ATTLIST bit_field name ID #REQUIRED size CDATA #REQUIRED offset CDATA #REQUIRED category CDATA #REQUIRED>
    <!ATTLIST access mode CDATA #REQUIRED type (read | write) #REQUIRED>
    <!ATTLIST preset name CDATA #REQUIRED value CDATA #REQUIRED>
    <!ATTLIST format name IDREF #REQUIRED>
    <!ATTLIST use name CDATA #REQUIRED>
    <!ATTLIST format_definition name ID #REQUIRED signed (True | False | 1 | 0) #REQUIRED>
    <!ATTLIST point native CDATA #REQUIRED transformed CDATA #REQUIRED>
    '''
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
            signed = fmt_def.attrib['signed'] in ["True","true","1"]
            points = fmt_def.findall('./piecewise_linear_points/point')
            xlist = []
            ylist = []
            for xpoints in points:
                xlist.append(xpoints.attrib['native'])
            for ypoints in points:
                ylist.append(ypoints.attrib['transformed'])
            points = list(zip(xlist, ylist))
            self._xml_formats[name] = {'points': points, 'description': desc, 'signed': signed, 'units': units}
        #extract constant definitions
        for constant in xml_reg_map.findall('.//constant_definition'):
            self._constants[constant.attrib['name']] = constant.attrib['value']
        # generate actual formats using the xml formats
        self._update_xml_formatters()
        #Check which bit fields are allowed to become channels. use_case=None results in no filtering.
        if use_case is None:
            self.categories = None
        else:
            self.categories = []
            for category in xml_reg_map.findall("./use[@name='{}']/category".format(use_case)):
                self.categories.append(category.text)
        #now extract the bit fields
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
                #tag attributes
                name = channel_prefix + bit_field.attrib['name'] + channel_suffix
                category = bit_field.attrib['category']
                size = str2num(bit_field.attrib['size'])
                offset = str2num(bit_field.attrib['offset'])
                default = bit_field.find('./default')
                if default is not None:
                    default = str2num(default.text)
                if self.categories is not None and category not in self.categories:
                    continue #filter out unauthorized categories for this use_case
                register = self.add_register(name,addr7,command_code,size,offset,word_size,is_readable, is_writable)
                register.set_category(category)
                register.set_attribute("default",default)
                #add presets
                for preset in bit_field.findall('./preset'):
                    if preset.find('./description') is not None:
                        preset_desc = preset.find('./description').text
                    else:
                        preset_desc = None
                    register.add_preset(preset.attrib['name'], str2num(preset.attrib['value']), preset_desc)
                #add additional user formats
                for format in bit_field.findall('./format'):
                    format_name = format.attrib['name']
                    format_definition = [definition for definition in xml_reg_map.findall(".//format_definition") if definition.attrib['name'] == format_name]
                    if format_name in format_dict and not len(format_definition):
                        register.add_format(format_name, format_dict[format_name]['format'], format_dict[format_name]['unformat'])
                        if len(format_definition):
                            print("Warning: format dict being used instead of XML for {}".format(format_name))
                    elif len(format_definition):
                        register.add_format(format_name,self.formatters[format_name]['format'],self.formatters[format_name]['unformat'],self.formatters[format_name]['signed'],self.formatters[format_name]['units'],self.formatters[format_name]['xypoints'])
                    else:
                        raise Exception('Format {} undefined in format_dict and in XML'.format(format_name))
                description = bit_field.find('./description')
                if (description is not None):
                    register.set_description(description.text)
    
    def populate_from_yoda_json_bridge(self,filename,i2c_addr7,extended_addressing=False):
        # print("Experimental Feature for Kirkwood, json bridge file format is in development")
	# extended_addressing causes 
        with open(filename, 'r') as fp:
            registers = json.load(fp)
        for reg in registers:
            if len(reg['bitfields']) > 1:
                overwrite_others = False
            else:
                overwrite_others = True
            for name,bf in list(reg['bitfields'].items()):
                if extended_addressing:
                    command_code = reg["address"] % 2**reg['width']
                    slave_addr = i2c_addr7 + int(reg["address"] / 2**reg['width'])
                else:
                    command_code = reg["address"]
                    slave_addr = i2c_addr7
                size = bf['slicewidth']
                offset = bf['regoffset']
                word_size = reg['width']
                is_readable = "R" in bf['access']
                is_writable = "W" in bf['access']
                register = self.add_register(name,slave_addr,command_code,size,offset,word_size,is_readable,is_writable,overwrite_others)
                try:
                    register.add_write_callback(self._interface.ivy_session._textwave)
                except AttributeError as e:
                    #print("WARNING: textwave callback not implemented for this interface")
                    pass #print once??
                if len(reg["functionalgroups"]) != 0:
                    register.set_category(str(reg["functionalgroups"][0]))
                else:
                    register.set_category("NoFunctionalGroup")
                if len(reg["functionalgroups"]) > 1:
                    register.add_tags(reg["functionalgroups"][1:])
                register.set_description(bf['documentation'])
                if len(bf["enums"]):
                    for name,value in list(bf["enums"].items()):
                        register.add_preset( name,value )
    def create_format(self, format_name, format_function, unformat_function, signed=False, description=None, units='', xypoints=[]):
        '''Create a new format definition or modify an existing definition.

        format_function should take a single argument of integer raw data from the register and return a version of the data scaled to appropriate units.
        unformat_function should take a single argument of data in real units and return an integer version of the data scaled to the register LSB weight.
        If the data is signed in two's-complement format, set signed=True.
        After creating format, use set_active_format method to make the new format active.
        '''
        self.formatters[format_name] = {'format': format_function, 'unformat': unformat_function, 'description': description, 'signed': signed, 'units': units, 'xypoints': xypoints}
    def set_constant(self, constant, value):
        '''Sets the constants found in the datasheet used by the formatters to convert from real world values to digital value and back.'''
        self._constants[constant] = value
        self._update_xml_formatters()
    def get_constant(self,constant):
        '''Sets the constants found in the datasheet used by the formatters to convert from real world values to digital value and back.'''
        return self._constants[constant]
    def list_constants(self):
        '''Returns the list of constants found in the datasheet used by the formatters to convert from real world values to digital value and back.'''
        return self._constants
    def _update_xml_formatters(self):
        self.create_format( format_name = 'None',
                            format_function = lambda x:x,
                            unformat_function = lambda x:x,
                            signed = False,
                            description = '''No formatting applied to data.''',
                            units = '')
        for fmt_name in self._xml_formats:
            xyevalpoints = self._evaluated_points(self._xml_formats[fmt_name]["points"])
            self.create_format( format_name = fmt_name,
                                format_function = self._transform_from_points(xyevalpoints, "format"),
                                unformat_function = self._transform_from_points(xyevalpoints, "unformat"),
                                signed = self._xml_formats[fmt_name]["signed"],
                                description = self._xml_formats[fmt_name]["description"],
                                units = self._xml_formats[fmt_name]["units"],
                                xypoints = xyevalpoints)
    def _transform_from_points(self, xyevalpoints, direction):
        '''Used internally to convert from register values to real world values and back again.'''
        if not SCIPY_MISSING:
            x_evaled, y_evaled = list(zip(*xyevalpoints))
            if direction == "format":
                z = sorted(zip(x_evaled, y_evaled), key = lambda x: x[0])
                return lambda x: None if x is None else float(UnivariateSpline(x = zip(*z)[0], y = zip(*z)[1], k=1, s = 0)(x))
            elif direction == "unformat":
                z = sorted(zip(x_evaled, y_evaled), key = lambda x: x[1])
                return lambda x: int(round(UnivariateSpline(x = zip(*z)[1], y = zip(*z)[0], k=1, s = 0)(float(x))))
            else:
                raise Exception("'transform_from_points()' requires one of either: 'format' or 'unformat'")
        else:
            # revert to PyICe.lab_utils.interpolator
            if direction == "format":
                return lambda x: None if x is None else float(interpolator(xyevalpoints)(x))
            elif direction == "unformat":
                return lambda y: int(round(interpolator(xyevalpoints).get_x_val(float(y))))
            else:
                raise Exception("'transform_from_points()' requires one of either: 'format' or 'unformat'")
    def _evaluated_points(self, xypoints):
        eval_constants = {}
        eval_constants.update(self._constants)
        eval_constants = {key:float(eval(value)) for key, value in self._constants.items()} #eval allows expressions within XML constants
        return [(eval(point[0], eval_constants),eval(point[1], eval_constants)) for point in xypoints]

class twi_register(lab_core.register):
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
    def __init__(self,interface_twi,except_on_i2cInitError=True,except_on_i2cCommError=False,retry_count=5,PEC=False):
        twi_instrument.__init__(self,interface_twi,except_on_i2cInitError,except_on_i2cCommError,retry_count,PEC)
        self.pmbus_commands = {
        'PAGE' : 0x00,
        'PHASE': 0x04,
        }
    def add_register(self,name,addr7,page,command_code,size,offset,word_size,is_readable,is_writable):
        def paged_write(data, channel):
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
        new_register.set_attribute('page',page)
        new_register.pmbus_unpaged_write = new_register._write
        new_register._write = lambda data: paged_write(data, new_register)
        return new_register
    def set_page(self, page):
        if page != None:
            self._interface.write_register(addr7=self._addr7, commandCode=self.pmbus_commands['PAGE'], data=page, data_size=8, use_pec=self._PEC)
            debug_logging.debug("PMBus instrument at {} setting page register to %s", self._addr7, page)
    def read_delegated_channel_list(self,register_list):
        results = lab_core.results_ord_dict()
        pages = set([ch.get_attribute('page') for ch in register_list])
        if len(pages) > 1 and None in pages:
            pages -= set([None])
            merge_none = True
        for idx, page in enumerate(pages):
            if page is not None:
                self.set_page(page)
            #speed up slightly by merging None pages with the first non-None page, if None and non-None pages are both in the register_list
            results.update(twi_instrument.read_delegated_channel_list(self, [ch for ch in register_list if ch.get_attribute('page') == page or merge_none and not idx and ch.get_attribute('page') is None]))
        return results

class twi_instrument_dummy(twi_instrument):
    '''use for formatters, etc without having to set up a master and physical hardware.'''
    def __init__(self):
        lab_core.instrument.__init__(self,name=None)
        self._addr7 = None
        self.formatters = {}
        self._constants = {}

if __name__ == "__main__":
    from . import lab_core
    m = lab_core.master()
    twi_interface = m.get_twi_dummy_interface()
    twi = twi_instrument(twi_interface)
    twi.populate_from_file("./xml_registers/EXAMPLE/LTC3350.xml", format_dict={}, access_list=['user'], use_case="demo")
