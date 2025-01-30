'''
Channel and Threading Core Framework
====================================

changes to this file should be minimal!

'''

from . import DEFAULT_AUTHKEY
import sys
sys.path.append('..')
from PyICe import logo
logo.display()
from PyICe import lab_interfaces
from PyICe.lab_utils.egg_timer import egg_timer
from PyICe.lab_utils.twosComplementToSigned import twosComplementToSigned
from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
from PyICe.lab_utils.eng_string import eng_string
from PyICe.lab_utils.clean_sql import clean_sql
from PyICe.lab_utils.sqlite_data import sqlite_data
import sqlite3
import queue
import re
import _thread
import traceback
import multiprocessing.managers
import multiprocessing
import time
import atexit
import collections
import datetime
import numbers
import os
import copy
import functools

try:
    from numpy import ndarray, insert
    numpy_missing = False
except ImportError as e:
    numpy_missing = True

import logging
debug_logging = logging.getLogger(__name__)

root_logging = logging.getLogger()
print_logging_level = logging.INFO  # Consider setting this to WARNING - 1.

if debug_logging.getEffectiveLevel() > print_logging_level:
    # We get here if our print logs aren't going to be printed
    # because perhaps the root logging object doesn't yet
    # have a handler installed.
    # So configure root logging to print out messages to stdout
    # using a StreamHandler which writes to stdout.
    # It is also possible that there could be intermediate loggers in
    # the logger hierarchy with stricter levels blocking our
    # prints. We will take that to be a deliberate choice by the
    # PyICe library user which we won't try to override.
    root_logging.setLevel(print_logging_level)
    root_logging.addHandler(logging.StreamHandler())

class results_ord_dict(collections.OrderedDict):
    '''Ordered dictionary for channel results reporting with pretty print addition.'''
    def __str__(self):
        s = ''
        max_channel_name_length = 0
        for k,v in self.items():
            max_channel_name_length = max(max_channel_name_length, len(k))
            s += '{}:\t{}\n'.format(k,v)
        # The '\xFA' messes up in Python 3, maybe because Python 3 treats all strings as Unicode.
        # Removing for now as it seems to be for aesthetics only.
        # s = s.replace(' ', '\xFF') # temporary move
        s = s.expandtabs(max_channel_name_length+2)
        # s = s.replace(' ', '\xFA') # just the tab spaces
        # s = s.replace('\xFF', ' ') # put back non-tab spaces
        return s
    def __getstate__(self):
        return {}

class delegator(object):
    '''base class for a read delegator, this is the lowest level class in the library.
    You will probably never use it directly.'''
    def __init__(self):
        self.set_delegator(self)
        self._threadable = True
        self._interfaces = []
    def set_delegator(self,delegator):
        self._delegator = delegator
    def get_delegator(self):
        return self._delegator
    def set_allow_threading(self,state=True):
        self._threadable = state
    def threadable(self):
        return self._threadable
    def resolve_delegator(self):
        if self._delegator == self:
            return self._delegator
        else:
            return self._delegator.resolve_delegator()
    def add_interface(self,interface):
        self._interfaces.append(interface)
    def get_interfaces(self):
        if self.get_delegator() == self:
            return set(self._interfaces)
        else:
            return self.resolve_delegator().get_interfaces()
    def lock_interfaces(self):
        for interface in self._interfaces:
            interface.lock()
    def unlock_interfaces(self):
        for interface in self._interfaces:
            interface.unlock()
    def write_delegated_channel_list(self,channel_value_list):
        # (NOT IMPLEMENTED YET)
        #OVERLOAD THIS FUNCTION
        # takes a list of (channels, value) tuples
        # writes each channel to its corresponding value
        try:
            self.lock_interfaces()
            for (channel,value) in channel_value_list:
                channel.write(value)
            self.unlock_interfaces()
        except Exception as e:
            self.unlock_interfaces()
            raise e
    def _read_delegated_channel_list(self,channel_list):
        try:
            self.lock_interfaces()
            data = self.read_delegated_channel_list(channel_list)
            self.unlock_interfaces()
            return data
        except Exception as e:
            self.unlock_interfaces()
            raise e
    def read_delegated_channel_list(self,channel_list):
        #OVERLOAD THIS FUNCTION
        # takes a list of channels
        # returns a dictionary of read data by channel name
        results = results_ord_dict()
        for channel in channel_list:
            results[channel.get_name()] = channel.read_without_delegator()
        return results

def retfirst (t):
    return (t[0])

class channel(delegator):
    '''The base channel object.

        It can be read and/or written. Attributes can also be stored in it.
        For example channel number in a multi channel instrument'''
    def __init__(self,name,read_function=None,write_function=None):
        delegator.__init__(self)
        self.set_name(name)
        if read_function is not None and write_function is not None:
            raise Exception('There may only be a single read OR write function')
        self._read = read_function
        self._write = write_function
        self._value = None
        self._previous_value = None
        self._change_detected = False
        self._attributes = results_ord_dict()
        self.set_read_access(True)
        self._category = None
        self._tags = []
        self.set_write_delay(0)
        self._write_resolution = None
        self._write_min = None
        self._write_min_warning = None
        self._write_max = None
        self._write_max_warning = None
        self._write_callbacks = []
        self._read_callbacks = []
        self._change_callbacks = []
        self._presets = results_ord_dict()
        self._preset_descriptions = results_ord_dict()
        self._write_history = collections.deque([],maxlen=10)
        self._set_type_affinity('NUMERIC')
        if write_function is not None:
            self.set_write_access(True) # write channel
        elif read_function is not None:
            self.set_write_access(False) #read channel
        else:
            self.set_write_access(True) #dummy channels
        self.set_description("No Description")
        self.set_display_format_str()
    def __str__(self):
        return "channel Object: {}".format(self.get_name())
    def get_name(self):
        '''return channel name'''
        return self.name
    def set_name(self,name):
        '''rename channel'''
        name = str(name)
        if not re.match("[_A-Za-z][_a-zA-Z0-9]*$",name):
            raise ChannelNameException('Bad Channel Name "{}"'.format(name))
        self.name = name
        return self
    def _set_type_affinity(self, type):
        self._type_affinity = type
    def get_type_affinity(self):
        return self._type_affinity
    def get_size(self):
        return None
    def set_write_delay(self,delay):
        '''sets the automatic delay in seconds after channel write'''
        self._write_delay = delay
        self.set_attribute("write_delay",self._write_delay)
        return self
    def get_write_delay(self):
        '''return automatic delay after channel write'''
        return self._write_delay
    def get_description(self):
        '''return channel description string.'''
        return self._description
    def set_description(self,description):
        '''sets the channel description. argument is string'''
        self._description = description
        return self
    def read(self):
        #setting delegate to false is reserved for the delegator and should never be used otherwise
        if not self.is_readable():
            raise ChannelAccessException(f'Read a non-readable channel:{self.name}')
        try:
            self.lock_interfaces()
            data = self.resolve_delegator()._read_delegated_channel_list([self])[self.name]
            debug_logging.debug("Read %s from %s", data, self.name)
            self.unlock_interfaces()
            return data
        except Exception as e:
            self.unlock_interfaces()
            raise e
    def read_without_delegator(self, force_data=False, data=None, **kwargs):
        # do not use this function unless you are the delegator
        self.lock_interfaces()
        if force_data:
            result = data
            debug_logging.debug("Channel %s read %s from external source.", self.get_name(), result)
        elif self._read is None:
            result = self._value
            debug_logging.debug("Channel %s read %s cached from last write.", self.get_name(), result)
        else:
            try:
                result = self._read(**kwargs)
                debug_logging.debug("Channel %s read %s from _read method", self.get_name(), result)
            except Exception as e:
                debug_logging.error("Read error in channel {}".format(self.name))
                debug_logging.error(traceback.format_exc())
                self.unlock_interfaces()
                raise e
        if self._read is not None:
            self._set_value(result) #cache all but write-only channel results for eg, hysteresis calculation, change_callbacks.
        for callback in self._read_callbacks:
            debug_logging.debug("Channel %s running read callback %s.", self.get_name(), callback)
            callback(self,result)
        if self.is_changed():
            for callback in self._change_callbacks:
                debug_logging.debug("Channel %s running change callback %s from channel read.", self.get_name(), callback)
                callback(self,result)
        self.unlock_interfaces()
        return result
    def write(self,value):
        if not self.is_writeable():
            raise ChannelAccessException('Wrote a non-writeable channel')
        self.lock_interfaces()
        if value is not None:
            if self._write_min is not None and value < self._write_min:
                self.unlock_interfaces()
                raise ChannelValueException('Cannot write {} to {}. Minimum is {}.'.format(self.name,value,self._write_min))
            if self._write_max is not None and value > self._write_max:
                self.unlock_interfaces()
                raise ChannelValueException('Cannot write {} to {}. Maximum is {}.'.format(self.name,value,self._write_max))
            if self._write_min_warning is not None and value < self._write_min_warning:
                print('\n\n*** Warning, value {} below minimum setting of {}. Minimum is {}.\n\n'.format(self.name,value,self._write_min_warning))
            if self._write_max_warning is not None and value > self._write_max_warning:
                print('\n\n*** Warning, value {} exceeds maximum setting of {}. Maximum is {}.\n\n'.format(self.name,value,self._write_max_warning))
            if self._write_resolution is not None:
                r_val = round(value, self._write_resolution)
                debug_logging.debug("Channel %s rounding %f to %f.", self.get_name(), value, r_val)
                value = r_val
        if self._write is not None:
            try:
                self._write(value)
            except Exception as e:
                debug_logging.error("Write error in channel {}".format(self.name))
                debug_logging.error(traceback.format_exc())
                self.unlock_interfaces()
                raise e
        if self._write_delay:
            self.delay(self._write_delay)
        self._set_value(value)
        if self._write_history.count(value):
            self._write_history.remove(value)
        self._write_history.append(value)
        for callback in self._write_callbacks:
            debug_logging.debug("Channel %s running write callback %s.", self.get_name(), callback)
            callback(self,value)
        if self.is_changed():
            for callback in self._change_callbacks:
                debug_logging.debug("Channel %s running change callback %s from channel write.", self.get_name(), callback)
                callback(self,value)
        self.unlock_interfaces()
        return value
    def add_preset(self, preset_value, preset_description=None):
        '''base channels only have unnamed presets (not enumerations)'''
        if not self.is_writeable():
            raise ChannelAccessException('Basic channel presets are write-only.')
        if preset_value in list(self._presets.values()):
            raise ChannelException('Duplicated preset: {}.'.format(preset_value))
        self._presets[str(preset_value)] = preset_value
        self._preset_descriptions[str(preset_value)] = preset_description
    def get_presets(self):
        '''Returns a list of preset names'''
        return sorted(list(self._presets.keys()), key=lambda s: str(s).upper())
    def get_presets_dict(self):
        '''Returns a dictionary of preset names and value'''
        return results_ord_dict(self._presets)
    def get_preset_description(self, preset_name):
        '''Returns description associated with preset_name'''
        return self._preset_descriptions[preset_name]
    def has_preset_descriptions(self):
        '''returns boolean value of whether any presets have a description'''
        return set(self._preset_descriptions.values()) != set([None])
    def get_write_history(self):
        return list(self._write_history)
    def delay(self, dly_time):
        '''delay method. Broken out of write method so that it can be sub-classed if necessary.'''
        if dly_time > 5:
            egg_timer(dly_time)
        else:
            time.sleep(dly_time)
    def write_unformatted(self, value):
        '''bypass unformatting stub. Only useful for integer and register channels. intended for use by GUI.'''
        self.write(value)
    def _set_value(self,value):
        '''private method to set channel cached value without actualy _write call or any checking for writability, limits, etc.'''
        self._previous_value = self._value
        self._value = value
        try:
            changed = (self._value != self._previous_value)
        except ValueError as e:
            #if the before and after values aren't even sensibly comparable, they're certainly not the same. Ex Numpy Arrays of dissimilar length.
            changed = True
        try:
            if changed:
                self._change_detected = False
        except ValueError as e:
            ## We don't really know what happened but we're assuming it is a numpy.array. Needs revisiting.
            if changed.all():
                self._change_detected = False
        return value
    def is_changed(self):
        '''returns boolean status of whether channel value is different from previously read/written value (once per change)'''
        try:
            changed = (self.cached_value != self.previous_cached_value)
        except ValueError as e:
            #if the before and after values aren't even sensibly comparable, they're certainly not the same. Ex Numpy Arrays of dissimilar length.
            changed = True
        try:
            if changed:
                if not self._change_detected:
                    self._change_detected = True
                    return True
        except ValueError as e:
            if changed.all():
                ## We don't really know what happened but we're assuming it is a numpy.array. Needs revisiting.
                if not self._change_detected:
                    self._change_detected = True
                    return True
        return False
    def set_attribute(self,attribute_name,value):
        '''set attribute_name to value
        value can be retrived later with get_attribute(attribute_name)'''
        self._attributes[attribute_name] = value
        return self
    def get_attribute(self,attribute_name):
        '''retrieve value previously set with set_attribute(attribute_name, value)'''
        if attribute_name not in list(self._attributes.keys()):
            raise ChannelAttributeException
        return self._attributes[attribute_name]
    def get_attributes(self):
        '''return dictionary of all channel attributes previously set with set_attribute(attribute_name, value)'''
        return results_ord_dict(sorted(list(self._attributes.items()), key=lambda t: t[0]))
    def set_category(self, category):
        '''each channel may be a member of a single category for sorting purposes. category argument is usually a string'''
        if not isinstance(category,str):
            raise TypeError("Category must be a string")
        self._category = category
        return self
    def get_category(self):
        '''returns category membership.  should be a string.'''
        return self._category
    def add_tag(self,tag):
        '''each channel may receive several tags for sorting purposes. The tag is usually a string.'''
        self._tags.append(tag)
    def add_tags(self,tag_list):
        '''each channel may receive several tags for sorting purposes. This function adds a list of tags. The tags are usually strings.'''
        for tag in tag_list:
            self._tags.append(tag)
    def get_tags(self,include_category=True):
        '''returns the list of tags for this channel.  If include_category is True the list will also include the category'''
        return self._tags + [self._category] if include_category else []
    def is_readable(self):
        '''return register readability boolean'''
        return self._readable
    def set_read_access(self, readable=True):
        '''set or unset register read access'''
        self._readable = readable
        self.set_attribute("readable",readable)
        return self
    def is_writeable(self):
        '''return register writability boolean'''
        return self._writeable
    def set_write_access(self, writeable=True):
        '''set or unset register write access'''
        self._writeable = writeable
        self.set_attribute("writeable",writeable)
        return self
    def set_write_resolution(self, decimal_digits=None):
        '''set automatic rounding to fixed number of decimal digits, appropriate to the instrument being controlled.
        for instance, it probably doesn't make much sense to set a power supply to much better than 1mV (3) resolution
        a frequency generator might not have better  than 1ns (9) or 100ps (10) digit resolution.
        One frequent cause of excessive apparent resolution is scaling numbers by multiplication/division, log-stepping, or other operations likely to create unrepresentable numbers.
        There are two known likely problems with excessive resolution:
            1) It's possible to choke the input parsee of test equipment if it has limited input buffer size for the command
            2) Recalling forced values from a SQLite database can be problematic. The answer returned from a get_distict() query can't be fed back into a WHERE clause to return the same data.
                Something gets truncated inconsistently either in the SQLIte C library itself or in the SQLite Python bindings.
                Avoiding getting close to machine epsilon (roughly 15 significant decimal digits for double-precision float) robustly addresses the problem.
        This decimal treatment might not be appropraite for all use cases. The same effect could be achieved with a more generalized function call if necessary (TBD/TODO).
        '''
        assert isinstance(decimal_digits, (type(None), int)), f'decimal_digits argument must be None or Int type. Received: {decimal_digits}, {type(decimal_digits)}.'
        self._write_resolution = decimal_digits
    def set_max_write_limit(self,max):
        '''set channel's maximum writable value. None disables limit'''
        if max is None:
            self._write_max = None
        else:
            try:
                self._write_max = float(max)
                self.set_attribute("write_max",self._write_max)
            except:
                raise Exception("Value for a channel's maximum write must be a number")
        return self
    def set_min_write_limit(self,min):
        '''set channel's minimum writable value. None disables limit'''
        if min is None:
            self._write_min = None
        else:
            try:
                self._write_min = float(min)
                self.set_attribute("write_min",self._write_min)
            except:
                raise Exception("Value for a channel's minimum write must be a number")
        return self
    def get_max_write_limit(self):
        '''return max writable channel value.'''
        return self._write_max
    def get_min_write_limit(self, formatted=False):
        '''return min writable channel value.'''
        return self._write_min
    def set_max_write_warning(self,max):
        '''set channel's maximum writable warning value. None disables limit'''
        if max is None:
            self._write_max_warning = None
        else:
            try:
                self._write_max_warning = float(max)
                self.set_attribute("_write_max_warning",self._write_max_warning)
            except:
                raise Exception("Value for a channel's maximum warning must be a number")
        return self
    def set_min_write_warning(self,min):
        '''set channel's minimum writable value warning. None disables limit'''
        if min is None:
            self._write_min_warning = None
        else:
            try:
                self._write_min_warning = float(min)
                self.set_attribute("_write_min_warning",self._write_min_warning)
            except:
                raise Exception("Value for a channel's minimum warning must be a number")
        return self
    def get_max_write_warning(self):
        '''return max warning channel value.'''
        return self._write_max_warning
    def get_min_write_warning(self, formatted=False):
        '''return min warngin channel value.'''
        return self._write_min_warning
    def format_display(self,data):
        '''converts data to string according to string formatting rule set by self.set_display_format_str()'''
        return self._display_format_str.format(data)
    def set_display_format_str(self,fmt_str='',prefix='',suffix=''):
        '''format string to alter how data is displayed.

        example '3.2f', '04X', '#06X', '#18b', '.2%'
        prefix will be displayed immediately before the channel data, example '0x'
        suffix will be displayed immediately after the channel data, example ' A' or ' V'
        '''
        self._display_format_str = '{prefix}{{:{fmt_str}}}{suffix}'.format(prefix=prefix,fmt_str=fmt_str,suffix=suffix)
        return self
    def set_display_format_function(self,function):
        '''abandon string formatting and pass data through custom user-supplied function'''
        self.format_display = function
        return self
    def add_write_callback(self,write_callback):
        '''Adds a write callback.

        This is a function that will be called any time the channel is written.
        The callback function takes two arguments (channel_object, data)'''
        self._write_callbacks.append(write_callback)
        return self
    def add_read_callback(self,read_callback):
        '''Adds a read callback.

        This is a function that will be called any time the channel is read.
        The callback function takes two arguments (channel_object, data)'''
        self._read_callbacks.append(read_callback)
        return self
    def add_change_callback(self,change_callback=None):
        '''Adds a change callback.

        This is a function that will be called any time the channel value changes due to a read or write.
        The callback function takes two arguments (channel_object, data).
        If change_callback is unspecified, channel name, value and time will be printed to the terminal each time the channel value changes.'''

        if change_callback is None:
            change_callback = self.default_print_callback
        self._change_callbacks.append(change_callback)
        return self
    def remove_change_callback(self,change_callback=None):
        if change_callback is None:
            change_callback = self.default_print_callback
        try:
            self._change_callbacks.remove(change_callback)
        except ValueError as e:
            raise Exception("Failed to remove change callback {} because it was not registered.".format(change_callback))
    @staticmethod
    def default_print_callback(channel, value):
        try:
            preset_str = " ({})".format(channel._presets_reverse[value])
        except AttributeError:
            #non register/integer_channel
            preset_str = ""
        except KeyError:
            #register/integer_channel but unmatched with preset
            preset_str = ""
        except Exception as e:
            debug_logging.error("Unknown problem with change callback for channel: {}".format(channel.get_name()))
            debug_logging.error(e, exc_info=True)
            debug_logging.error("Entering debugger!")
            import pdb; pdb.set_trace()
            preset_str = ""
        debug_logging.info("{}: {} changed from {} to {}{}"
                           ".".format(datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                           channel.get_name(), channel.previous_cached_value, value, preset_str))
    cached_value = property(lambda self: self._value, doc='Retrieve last read or written channel value')
    previous_cached_value = property(lambda self: self._previous_value, doc='Retrieve second last read or written channel value')

class ChannelException(Exception):
    '''Parent of all channel exceptions. Not used directly.'''
class ChannelAccessException(ChannelException):
    '''Attempt to write non-writable channel or read non-readable channel.'''
class ChannelNameException(ChannelException):
    '''Attempt to create invalid channel name.'''
class ChannelAttributeException(ChannelException):
    '''Attempt to read non-existent channel attribute.'''
class ChannelValueException(ChannelException):
    '''Attempt to write a channel beyond min or max limits.'''
class IntegerChannelValueException(ChannelException):
    '''Attempt to write an integer channel to a non-integer value.'''
class ChannelReadException(ChannelException):
    '''Out-of-band return value to signal that channel read failed. Should only be used to indicate partial failures within delegated reads. Not typically raised, just instantiated and returned.'''
    def __eq__(self, other):
        if isinstance(other, ChannelReadException):
            return self.args == other.args
        else:
            return False
    def __ne__(self, other):
        return not self.__eq__(other)
class RemoteChannelGroupException(ChannelException):
    '''Connection problem with remote channel group client.'''
class RegisterFormatException(ChannelException):
    '''Attempt to apply non-existent channel format.'''

class integer_channel(channel):
    '''Channel with integer value limitation.

    Adds presets and formats but retains channel class's read/write restrictions.'''
    def __init__(self, name, size, read_function=None, write_function=None):
        channel.__init__(self,name,read_function=read_function,write_function=write_function)
        assert isinstance(size, numbers.Integral)
        self._size = size
        self.set_attribute("size",size)
        self._formats = results_ord_dict()
        self._presets_reverse = results_ord_dict()
        self._preset_descriptions = results_ord_dict()
        self._format = None
        self._use_presets_read = False
        self._use_presets_write = True
        self._add_default_formats()
        assert self._size >= 1
        self.set_min_write_limit(0)
        self.set_max_write_limit(2**size-1)
        self.set_attribute("min",0)
        self.set_attribute("max",2**size-1)
    def __str__(self):
        return "integer_channel Object: {}".format(self.get_name())
    def _add_default_formats(self):
        def check_sign(data):
            assert isinstance(data, numbers.Number)
            if data < 0:
                raise ValueError('Negative binary/hex values not allowed.')
            return data
        if self._size == 1:
            #single bit default presets
            self._add_preset('True', True, None)
            self._add_preset('False', False, None)
        elif self._size > 1:
            self.add_format('dec', str, int)
            self.add_format('hex', lambda data : '0x{{:0{}X}}'.format((self._size-1)//4+1).format(check_sign(data)), lambda data : int(str(data),16))
            self.add_format('bin', lambda data : '0b{{:0{}b}}'.format(self._size).format(check_sign(data)), lambda data : int(str(data),2))
            self.add_format('signed dec', str, int, signed=True)
            #self.add_preset('Minimum', self.get_attribute("min")) #this is wrong for two's-comp channels. Not sure how to deal with signed data here since that's handled by formatting...
            #self.add_preset('Maximum', self.get_attribute("max")) #this is wrong for two's-comp channels. Not sure how to deal with signed data here since that's handled by formatting...
        else:
            raise Exception('Bad size: {}'.format(self._size))
    def get_size(self):
        return self._size
    def get_max_write_limit(self, formatted=False):
        '''return max writable channel value. If formatted, return max writeable value in transformed units accorting to set_format(format) active format.'''
        if formatted:
            return self.format(self._write_max, self._format)
        else:
            return int(self._write_max)
    def get_min_write_limit(self, formatted=False):
        '''return min writable channel value. If formatted, return min writeable value in transformed units accorting to set_format(format) active format.'''
        if formatted:
            return self.format(self._write_min, self._format)
        else:
            return int(self._write_min)
    def add_preset(self, preset_name, preset_value, preset_description=None):
        '''Adds a preset named preset_name with value preset_value'''
        if self._size == 1 and len(list(self._presets.keys())) == 2 and 'True' in self._presets and 'False' in self._presets:
            #remove True/False presets if custom presets are added
            self._presets = results_ord_dict()
            self._presets_reverse = results_ord_dict()
        self._add_preset(preset_name, preset_value, preset_description)
        return self
    def _add_preset(self, preset_name, preset_value, preset_description):
        if not isinstance(preset_value, (numbers.Integral, bool, type(None))):
            raise Exception('Preset value {} neither numeric nor boolean'.format(preset_value))
        if preset_name in self._presets:
            raise Exception('Preset name duplicated: {}.'.format(preset_name))
        if preset_value in self._presets_reverse:
            debug_logging.warning('WARNING: Preset value: {} of register: {} ambiguous name lookup:[{}, {}]'
                                  '.'.format(preset_value, self.get_name(), preset_name,
                                              self._presets_reverse[preset_value]))
        self._presets[preset_name] = preset_value
        self._presets_reverse[preset_value] = preset_name
        self._preset_descriptions[preset_name] = preset_description
    def set_format(self,format):
        '''set active transformation format. reads and writes happen in transformed (real) units instead of native integer.
        Set to None to disable formatting.'''
        if format is not None and format not in self.get_formats():
            raise Exception('Invalid format "{}" for {}'.format(format,self.get_name()))
        self._format = format
        return self
    def get_format(self):
        '''return active format as set by set_format(format)'''
        return self._format
    def use_presets_read(self,bool): # pragma: no cover
        '''enable replacement of integer value with named enum when reading channel'''
        self._use_presets_read = bool
        return self
    def use_presets_write(self,bool): # pragma: no cover
        '''enable replacement of named enum with integer value when writing channel'''
        self._use_presets_write = bool
        return self
    def using_presets_read(self): # pragma: no cover
        '''return boolean denoting last setting of use_presets_read()'''
        return self._use_presets_read
    def using_presets_write(self): # pragma: no cover
        '''return boolean denoting last setting of use_presets_write()'''
        return self._use_presets_write
    def add_format(self, format_name, format_function, unformat_function, signed=False, units='', xypoints=[]): # pragma: no cover
        '''Add a format to this register.  Formats convert a raw number into a more meaningful string and vice-versa
            Formats can be generic hex, bin, etc, or can be more complicated.
            format_name is the name of the format
            format_function transforms from integer data to real
            unformat_function transforms from real data to integer
            format_function and unformat_function should be reversible
            signed treats integer data as two's complement with self.size bit width
            units optionally appended to formatted (real) data when displayed by GUI
            xypoints optionally allows duplicates information from format/unformat function to allow reproduction of transform in SQL, etc'''
        self._formats[format_name] = {}
        if signed:
            self._formats[format_name]['format_function'] = lambda x: format_function(self.twosComplementToSigned(x))
            self._formats[format_name]['unformat_function'] = lambda x: self.signedToTwosComplement(unformat_function(x))
        else:
            self._formats[format_name]['format_function'] = format_function
            self._formats[format_name]['unformat_function'] = unformat_function
        self._formats[format_name]['units'] = units
        self._formats[format_name]['xypoints'] = xypoints
        self._formats[format_name]['signed'] = signed
        return self
    def remove_format(self, format_name): # pragma: no cover
        '''remove format_name from dictionary of available formats'''
        del self._formats[format_name]
    def get_formats(self):
        '''Return a list of format_names associate with this register.
            The format_string elements of the returned list may be passed to the format or unformat methods'''
        return list(self._formats.keys())
    def format(self, data, format, use_presets):
        '''take in integer data, pass through specified formatting function, and return string/real representation.'''
        if data is None:
            return None
        if data is True:
            return True
        if data is False:
            return False
        if use_presets:
            try:
                return self._presets_reverse[data]
            except KeyError:
                pass
        if format is not None:
            if format not in self._formats:
                raise RegisterFormatException('Register {} has no format {}'.format(self.name,format))
            return self._formats[format]['format_function'](data)
        return data
    def sql_format(self, format, use_presets):
        '''return SQL legal column selection text for insertion into a query/view'''
        def _slope_int_str(p1, p2):
            '''return line-defining slope and intercept for a particular piecewise segment between p1 and p2 points'''
            x1,y1 = p1
            x2,y2 = p2
            slope = 1.0*(y2-y1)/(x2-x1)
            intercept = y1 - slope*x1
            if intercept == 0:
                intercept_str = ''
            else:
                intercept_str = '{:+3.6E}'.format(intercept)
            return '"{}"*{:3.6E}{}'.format(self.get_name(),slope,intercept_str)
        if format is not None:
            xypoints = sorted(self._formats[format]['xypoints'], key=lambda point: point[0]) #ascending in x
            if len(xypoints) < 2:
                return None #only return presets once in case of default dec/hex/bin formats
            elif len(xypoints) == 2:
                #straight line
                fmt_str = _slope_int_str(xypoints[0], xypoints[1])
            else:
                #multi-segment interpolator. extrapolation from first and last segments
                fmt_str = 'CASE\n'
                for pidx in range(1,len(xypoints)-1):
                    fmt_str += '    WHEN "{}" < {} THEN {}\n'.format(self.get_name(), xypoints[pidx][0], _slope_int_str(xypoints[pidx-1], xypoints[pidx]))
                fmt_str += '    ELSE {}\n'.format(_slope_int_str(xypoints[-2], xypoints[-1]))
                fmt_str += '  END'
        if (use_presets
           and len(self._presets)
           and not (self._size == 1
                    and len(list(self._presets.keys())) == 2
                    and 'True' in self._presets
                    and 'False' in self._presets)):
            sql_txt = '  CASE "{}"\n'.format(self.get_name())
            for preset_value in self._presets_reverse:
                if preset_value is True:
                    preset_value_escaped = "'True'"
                elif preset_value is False:
                    preset_value_escaped = "'False'"
                elif preset_value is None:
                    preset_value_escaped = "'None'"
                else:
                    preset_value_escaped = preset_value
                sql_txt += "    WHEN {} THEN '{}'\n".format(preset_value_escaped, self._presets_reverse[preset_value])
            if format is not None:
                sql_txt += '    ELSE {}\n'.format(fmt_str)
            else:
                #return raw channel value to prevent NULL result if no presets/formats match
                sql_txt += '    ELSE "{}"\n'.format(self.get_name())
            sql_txt += '  END'
        elif format is not None:
            sql_txt = '  {}'.format(fmt_str)
        else:
            return None
        sql_txt += ' AS {}'.format(self.get_name()) #_fmt\n
        return sql_txt
    def unformat(self, string, format, use_presets):
        '''take in formatted string / real, pass through specified unformatting function, and return integer representation.'''
        if string is None:
            debug_logging.debug("Channel %s unformat returning None.", self.get_name())
            return None
        if use_presets:
            try:
                debug_logging.debug("Channel %s unformat attempting preset match to %s.", self.get_name(), string)
                return self._presets[string]
            except KeyError:
                pass
        if format is not None:
            if format not in self._formats:
                raise RegisterFormatException('Register {} has no format {}.'.format(self.name,format))
            try:
                debug_logging.debug("Channel %s unformat attempting unformat using %s.", self.get_name(), format)
                return self._formats[format]['unformat_function'](string)
            except Exception as e:
                #formats intended for real data will get switched to strings in the GUI. Make an attempt here to fix.
                if isinstance(string,int) or isinstance(string,float) or string is None:
                    raise e
                try:
                    debug_logging.debug("Channel %s unformat attempting string to int conversion.", self.get_name())
                    formatted_data =  int(string,0) #automatically select base
                except ValueError:
                    try:
                        debug_logging.debug("Channel %s unformat attempting string to float conversion.", self.get_name())
                        formatted_data =  float(string)
                    except ValueError as e2:
                        print(e2)
                        raise e
                debug_logging.debug("Channel %s unformat retrying unformat using %s after string to numeric conversion.", self.get_name(), format)
                int_data = self._formats[format]['unformat_function'](formatted_data)
                assert isinstance(int_data, numbers.Integral)
                return int_data
        if string is True or string == 'True':
            debug_logging.debug("Channel %s returning True.", self.get_name())
            return True
        if string is False or string == 'False':
            debug_logging.debug("Channel %s returning False.", self.get_name())
            return False
        if isinstance(string, numbers.Integral):
            return string
        try:
            debug_logging.debug("Channel %s attempting string to numeric conversion without assigned format.", self.get_name())
            return int(string,0)
        except ValueError as e1: #String-type inputs, probably from GUI.
            try:
                if float(string) == int(float(string)): #last chance. If data is type float but is a round integer, then let it through.
                    return int(float(string))
            except Exception as e2:
                debug_logging.error(e2, exc_info=True)
                debug_logging.error("Unknown conversion error. Channel {} data {}".format(self.get_name(), string))
                raise e1
            raise IntegerChannelValueException('Floating point data {} passed to integer channel {} without unformat or preset match. Automatic rounding not allowed outside formats.'.format(string, self.get_name()))
        except TypeError as e: #Probably float-type input.
            if isinstance(string, float):
                raise IntegerChannelValueException('Floating point data {} passed to integer channel {} without unformat or preset match. Automatic rounding not allowed outside formats.'.format(string, self.get_name()))
            else:
                raise #no idea what happened
        except Exception as e:
            debug_logging.debug("Channel %s unknown conversion error.", self.get_name())
            debug_logging.warning("WARNING: Channel: {} write data: {} unknown conversion error of type "
                                  "{}.".format(self.get_name(), string, type(e)))
            raise IntegerChannelValueException("Channel: {} write data: {} (type {}) unknown conversion error of type {}.".format(self.get_name(), string, type(string), type(e)))
    def get_units(self, format): # pragma: no cover
        """return real units string for specified format. ex 'A' or 'V'"""
        return self._formats[format]['units']
    def format_read(self,raw_data):
        '''transform from integer to real units according to using_presets_read() and active format'''
        if isinstance(raw_data, int):
            if raw_data > self.get_max_write_limit():
                print("WARNING: Channel {} read data {} exceeds channel size {}.".format(self.get_name(), raw_data, self._size))
            if raw_data < self.get_min_write_limit():
                print("WARNING: Channel {} read data {} exceeds channel size {}.".format(self.get_name(), raw_data, self._size))
        if self._format or self._use_presets_read:
            fmt_data = self.format(raw_data,self._format,self._use_presets_read)
            debug_logging.debug("Channel %s formatted %s to %s", self.get_name(), raw_data, fmt_data)
            return fmt_data
        else:
            debug_logging.debug("Channel %s didn't format %s.", self.get_name(), raw_data,)
            return raw_data
    def format_write(self,value):
        '''transform from real units to integer according to using_presets_write() and active format'''
        return self.unformat(value,self._format,self._use_presets_write)
    def twosComplementToSigned(self,binary):
        '''transform two's complement formatted binary number to signed integer.  Requires register's size attribute to be set in __init__'''
        return twosComplementToSigned(binary,self._size)
    def signedToTwosComplement(self,signed):
        '''transform signed integer to two's complement formatted binary number.  Requires register's size attribute to be set in __init__'''
        return signedToTwosComplement(signed,self._size)
    def write(self,value):
        '''write intercept to apply formats/presets before channel write. Coerce to integer and warn about rounding error. Also accepts None'''
        if self._size == 1:
            #allow True,False values
            if value is True:
                channel.write(self,True)
                return True
            elif value is False:
                channel.write(self,False)
                return False
        if value is not None:
            raw_data = self.format_write(value)
            int_data = int(round(raw_data))
            if int_data != raw_data:
                debug_logging.warning("WARNING: Channel: {} write: {} unformatted to: {} and rounded to: {}.".format(self.get_name(), value, raw_data, int_data))
        else:
            int_data = value
        channel.write(self,int_data)
        return int_data
    def write_unformatted(self, value):
        '''bypass unformatting. intended for use by GUI.'''
        if self._size == 1:
            #allow True,False values
            if value is True:
                channel.write(self,True)
                return True
            elif value is False:
                channel.write(self,False)
                return False
        if value is not None:
            int_data = int(round(value))
            if int_data != value:
                debug_logging.warning("WARNING: Channel: {} write_unformatted: "
                                      "{} rounded to: {}.".format(self.get_name(), value, int_data))
            value = int_data
        channel.write(self,value)
        return value
    def read_without_delegator(self, force_data=False, data=None, **kwargs): # pragma: no cover
        '''read intercept to apply formats/presets to channel (raw) read'''
        return self.format_read(channel.read_without_delegator(self, force_data, data, **kwargs))

class register(integer_channel):
    '''Integer channel with read/write restriction removed.

    Models remote (volatile) memory. IE, reads must check remote copy rather than use cache like ordinary integer channels.
    This behavior can be modified on a channel-by-channel basis to speed up communication with the enable_cached_read method.
    '''
    def __init__(self, name, size, read_function=None,write_function=None):
        '''if subclass overloads __init__, it should also call this one'''
        #channel doesn't allow both read and write so just do one, then force in the other
        integer_channel.__init__(self, name=name, size=size, read_function=read_function)
        self.set_attribute('read_caching', False)
        self.set_attribute('special_access', None)
        if write_function:
            self._write = write_function
            self.set_write_access()
    def __str__(self):
        return "Register Object: {}".format(self.get_name())
    def enable_cached_read(self):
        '''return last written value rather than read remote memory contents. Essentially reverts from register to writable integer_channel.'''
        if not self.is_writeable():
            raise Exception("ERROR: Can't set non-writable register to cache reads: {}.".format(self.get_name()))
        self._read = None
        self.set_read_access(True)
        self.set_attribute('read_caching', True)
    def set_special_access(self, access):
        '''
        following uvm_reg_field convention
        https://verificationacademy.com/verification-methodology-reference/uvm/docs_1.1a/html/files/reg/uvm_reg_field-svh.html
        access:
	”RO”	W: no effect	R: no effect
	”RW”	W: as-is	R: no effect
	”RC”	W: no effect	R: clears all bits
	”RS”	W: no effect	R: sets all bits
	”WRC”	W: as-is	R: clears all bits
	”WRS”	W: as-is	R: sets all bits
	”WC”	W: clears all bits	R: no effect
	”WS”	W: sets all bits	R: no effect
	”WSRC”	W: sets all bits	R: clears all bits
	”WCRS”	W: clears all bits	R: sets all bits
	”W1C”	W: 1/0 clears/no effect on matching bit	R: no effect
	”W1S”	W: 1/0 sets/no effect on matching bit	R: no effect
	”W1T”	W: 1/0 toggles/no effect on matching bit	R: no effect
	”W0C”	W: 1/0 no effect on/clears matching bit	R: no effect
	”W0S”	W: 1/0 no effect on/sets matching bit	R: no effect
	”W0T”	W: 1/0 no effect on/toggles matching bit	R: no effect
	”W1SRC”	W: 1/0 sets/no effect on matching bit	R: clears all bits
	”W1CRS”	W: 1/0 clears/no effect on matching bit	R: sets all bits
	”W0SRC”	W: 1/0 no effect on/sets matching bit	R: clears all bits
	”W0CRS”	W: 1/0 no effect on/clears matching bit	R: sets all bits
	”WO”	W: as-is	R: error
	”WOC”	W: clears all bits	R: error
	”WOS”	W: sets all bits	R: error
	”W1”	W: first one after HARD reset is as-is, other W have no effects	R: no effect
	”WO1”	W: first one after HARD reset is as-is, other W have no effects	R: error
        '''
        # no side effect
        if access.upper() == "RO":
            self.set_attribute('special_access', None)
            self.set_read_access(True)
            self.set_write_access(False)
        elif access.upper() == "RW":
            self.set_attribute('special_access', None)
            self.set_read_access(True)
            self.set_write_access(True)
        elif access.upper() == "WO":
            self.set_attribute('special_access', None)
            self.set_read_access(False)
            self.set_write_access(True)

        # special read behavior    
        elif access.upper() in ("RC", "RS", "WRC", "WRS"):
            raise Exception(f'Read side effect {access.upper()} special register access unimplemented. Please contact PyICe developers.')
        
        # special write behavior
        elif access.upper() in ("WC", "WS", "W1T", "W0T", "WOC", "WOS", "W1", "WO1"):
            raise Exception(f'Limited write side effect special register access implemented. {access.upper()} not yet implemented. Please contact PyICe developers.')
        elif access.upper() == "W1C":
            self.set_attribute('special_access', 'W1C')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("clear", 2**self.get_size()-1, "Write 1 to clear")
        elif access.upper() == "W0C":
            self.set_attribute('special_access', 'W0C')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("clear", 0, "Write 0 to clear")
        elif access.upper() == "W1S":
            self.set_attribute('special_access', 'W1S')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("set", 2**self.get_size()-1, "Write 1 to set")
        elif access.upper() == "W0S":
            self.set_attribute('special_access', 'W0S')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("set", 0, "Write 0 to set")

        # special read and write behavior
        elif access.upper in ("WSRC", "WCRS", "W1SRC", "W1CRS", "W0SRC", "W0CRS"):
            raise Exception('Read/write side effect special register access unimplemented. Please contact PyICe developers.')
        # likely typo
        else:
            raise Exception('Unknown register side effect special access.. Please contact PyICe developers.')
    def compute_rmw_writeback_data(self, data):
        '''Bitfield level callback to modify writeback data for read-modify-write sub-atomic register access. This is useful primarily for bitfields with write side effects implemented.
           
        Parameters
        ----------
        data : int
            Bitfield readback data, masked and shifted to LSB position.
        
        Returns
        -------
        int
            Bitfield writeback data. Usually the same as readback data.

        Raises
        -------
        Exception
            Unknown value contained in "special_access" channel attribute.
        '''
        if self.get_attribute('special_access') is None:
            return data
        elif self.get_attribute('special_access') in ('W1C','W1S'):
            return 0
        elif self.get_attribute('special_access') in ('W0C','W0S'):
            return 2**self.get_size()-1
        else:
            raise Exception(f'Register special access {self.get_attribute("special_access")} improperly implemented. Contact PyICe developers.')

class channel_group(object):
    def __init__(self, name='Unnamed Channel Group'):
        self.set_name(name)
        self._channel_dict = results_ord_dict()  # a dictionary of channel objects, keyed by name, contained by this channel_group
        self._sub_channel_groups = []                   # a list of other groups contained by this object
        self._threaded = False
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = []
        debug_logging.debug("Created new channel group: %s", self.get_name())
    def __str__(self):
        return "channel_group Object: {}".format(self.get_name())
    def __iter__(self):
        for channel in self.get_all_channels_list():
            yield channel #this is inconsistent with dictionaries, which yield their keys when iterated!
    def __contains__(self, key):
        return key in self.get_all_channels_list()
    def __getitem__(self,channel_name):
        return self.get_channel(channel_name)
    def copy(self):
        copy_self = copy.copy(self)                                 #Make copy of the channel group object
        copy_self._channel_dict = results_ord_dict()                #Replace the channel dictionary with an empty one
        copy_self._channel_dict.update(self._channel_dict)          #Populate the copy of the dictionary with copies of original channels
        ### How should _partial_delegation_results, _self_delegation_channels, _sub_channel_groups be handled by this copy routine?
        return copy_self
    def get_name(self):
        return self._name
    def set_name(self,name):
        self._name = str(name)
    def get_categories(self):
        return set([ch.get_category() for ch in self.get_all_channels_list(categories=None)]) #TODO return list instead of set?
    def sort(self, deep=True, **kwargs):
        if 'key' not in kwargs:
            kwargs['key'] = lambda kv_tuple: kv_tuple[0] #sort by channel name by default
        self._channel_dict = results_ord_dict(sorted(list(self._channel_dict.items()), **kwargs))
        if deep: #should this go deep and sort sub channel groups too?
            for scg in self._sub_channel_groups:
                scg.sort(**kwargs)
    def add(self,channel_or_group):
        '''If a channel object is given, the channel is added to the topmost level of the channel group.
           If a channel group object is given, a subgroup is added to the channel group. When a parent group, but the channels are not considered to be part of the parent group.'''
        if isinstance(channel_or_group,channel):
            return self._add_channel(channel_or_group)
        elif isinstance(channel_or_group,channel_group):
            return self._add_sub_channel_group(channel_or_group)
        else:
            try:
                iterator = iter(channel_or_group)
            except TypeError as e:
                raise TypeError('\nAttempted to add something other than a channel or channel_group to a channel_group') from e
            else:
                return [self.add(ch) for ch in iterator]
    def _add_channel(self,channel_object):
        if not isinstance(channel_object,channel):
            err_str = 'Attempted to add a non-channel to a channel_group'
            debug_logging.error(err_str)
            raise Exception(err_str)
        if channel_object.get_name() in list(self._channel_dict.keys()):
            debug_logging.warning("WARNING: Re-defined channel %s", channel_object.get_name())
            print(("WARNING: Re-defined channel {}".format(channel_object.get_name())))
        elif channel_object.get_name() in list(self.get_all_channels_dict().keys()):
            err_str = '\nName Conflict: Attempted to create an already named channel {} existing in another subgroup'.format(channel_object.get_name())
            debug_logging.error(err_str)
            raise Exception(err_str)
        debug_logging.debug("Added %s to %s", channel_object.get_name(), self.get_name())
        self._channel_dict[channel_object.get_name()] = channel_object
        return channel_object
    def merge_in_channel_group(self,channel_group_object):
        '''adds to the topmost level of this channel group all the channels of the given channel group.'''
        if not isinstance(channel_group_object,channel_group):
            raise Exception('\nAttempted to merge a non-channel_group to a channel_group')
        for channel_object in channel_group_object:
            self._add_channel(channel_object)
    def _add_sub_channel_group(self,channel_group_object):
        '''adds a subgroup to this channel group. Subgroups are also resolved when the parents group is, but the channels of the subgroup are not considered to be part of the parent group.'''
        if not isinstance(channel_group_object,channel_group):
            raise Exception('\nAttempted to add a "{}" to a channel_group as a sub group'.format(channel_group_object))
        channel_name_conflicts = set(self.get_all_channels_dict().keys()) & set(channel_group_object.get_all_channels_dict().keys())
        for channel_name_conflict in channel_name_conflicts:
            raise Exception('\nChannel name conflict for "{}"'.format(channel_name_conflict))
        self._sub_channel_groups.append(channel_group_object)
        return channel_group_object
    def get_channel_groups(self):
        return list(self._sub_channel_groups)
    def read(self,channel_name):
        return self.read_channel(channel_name)
    def write(self,channel_name,value):
        return self.write_channel(channel_name,value)
    def read_channel(self,channel_name):
        channel = self._resolve_channel(channel_name)
        if channel is None:
            raise ChannelAccessException('\nUnable to read channel "{}", did you create it or is it a typo?'.format(channel_name))
        return self.read_channel_list([channel])[channel_name]
    def read_channels(self,item_list):
        '''item list is a list of channel objects, names or channel_groups'''
        channel_list = self.resolve_channel_list(item_list)
        return self.read_channel_list(channel_list)
    def write_channel(self,channel_name,value):
        return self.get_channel(channel_name).write(value)
    def write_channels(self, item_list):
        return [self.write_channel(ch_name, ch_value) for (ch_name, ch_value) in item_list]
    def get_channel(self,channel_name):
        channel = self._resolve_channel(channel_name)
        if channel is None:
            raise ChannelAccessException('\nUnable to get channel "{}", did you create it or is it a typo?'.format(channel_name))
        return channel
    def get_flat_channel_group(self,name=None):
        '''returns a channel_group directly containing all channels this one can resolve'''
        if name is None:
            name = '{}_flattened'.format(self.get_name())
        new_group = channel_group(name)
        new_group.merge_in_channel_group(self)
        return new_group
    def _resolve_channel(self,channel_name):
        if channel_name in self._channel_dict:
            debug_logging.debug("%s resolved %s to self.", self.get_name(), channel_name)
            return self._channel_dict[channel_name]
        for sub_channel_group in self._sub_channel_groups:
            channel = sub_channel_group._resolve_channel(channel_name)
            if channel is not None:
                debug_logging.debug("%s resolved %s to %s.", self.get_name(), channel_name, sub_channel_group.get_name())
                return channel
        return None
    def get_all_channels_dict(self, categories=None):
        #returns a dictionary of all channels by name
        all_channels = results_ord_dict(self._channel_dict)
        for sub_channel_group in self._sub_channel_groups:
            all_channels.update(sub_channel_group.get_all_channels_dict())
        if categories is not None:
            for k,v in list(all_channels.items()):
                if v.get_category() not in categories:
                    del all_channels[k]
        return all_channels
    def get_all_channel_names(self, categories=None):
        return list(self.get_all_channels_dict(categories).keys())
    def get_all_channels_list(self, categories=None):
        return list(self.get_all_channels_dict(categories).values())
    def get_all_channels_set(self, categories=None):
        return set(self.get_all_channels_dict(categories).values())
    def read_channel_list(self,channel_list):
        #reads a list of channel objects
        # create lists of threadable and non-threadable channels
        threadable_channels = []
        non_threadable_channels = []
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = []
        for channel in channel_list:
            if channel.resolve_delegator() is self:
                # if the user asked the delegator directly to read do not thread
                # this is also useful for the masters caching mode to do it last
                self._self_delegation_channels.append(channel)
            elif not channel.threadable():
                non_threadable_channels.append(channel)
            elif not channel.resolve_delegator().threadable():
                non_threadable_channels.append(channel)
            else:
                threadable_channels.append(channel)
        if self._threaded:
            debug_logging.debug("*** threaded read_channel_list() called")
            results = self._read_channels_threaded(threadable_channels)
        else:
            debug_logging.debug("Nonthreaded read_channel_list() called")
            results = self._read_channels_non_threaded(threadable_channels)
        results.update(self._read_channels_non_threaded(non_threadable_channels))
        if len(self._self_delegation_channels):
            self._partial_delegation_results.update(results)
            results.update( self._read_delegated_channel_list(self._self_delegation_channels) )
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = results_ord_dict()
        return results
    def _read_channels_non_threaded(self,channel_list):
        #get a dictionary of delegators for list of channel objects
        delegator_list = []
        for channel in channel_list:
            delegator_list.append( channel.resolve_delegator() )
        # remove all duplicates
        delegator_list = list(set(delegator_list))
        #have each delegator read its channels
        results = results_ord_dict()
        for delegator in delegator_list:
            # for each delegator get the list of channels it is responsible for
            channel_delegation_list = []
            for channel in channel_list:
                if delegator == channel.resolve_delegator():
                    channel_delegation_list.append(channel)
            results.update( delegator._read_delegated_channel_list(channel_delegation_list) )
        return results
    def _read_channels_threaded(self,channel_list):
        # dont read threaded unless i know how to group interfaces for theads (only interface_factory's
        #    know this, ie a master
        if not hasattr(self,'group_com_nodes_for_threads_filter'):
            return self._read_channels_non_threaded(channel_list)
        #get a dictionary of delegator's by channel name
        delegator_list = [ channel.resolve_delegator() for channel in channel_list]
        # remove all duplicates
        delegator_list = list(set(delegator_list))
        # build a list of interfaces that will be used in this read
        interfaces = []
        for delegator in delegator_list:
            for interface in delegator.get_interfaces():
                interfaces.append(interface)

        remaining_delegators = []
        interface_thread_groups = self.group_com_nodes_for_threads_filter(interfaces)
        work_units = 0
        if len(interface_thread_groups):
            for interface_group in interface_thread_groups:
                #build a group of delegators for each potential thread
                delegator_group = []
                remaining_delegators = []
                for delegator in delegator_list:
                    interfaces = delegator.get_interfaces()
                    # a delegator without interfaces cannot be threaded since I dont know how it works
                    if len(interfaces) and interfaces.issubset(interface_group):
                        delegator_group.append(delegator)
                    else:
                        remaining_delegators.append(delegator)

                #build a list of channels for that group of delegators to read
                delegator_groups_channel_list = []
                for delegator in delegator_group: #this is where the channel reads become unordered...
                    for channel in channel_list:
                        if channel.resolve_delegator() == delegator:
                            delegator_groups_channel_list.append(channel)
                #start the threaded read here
                #not threaded yet
                work_units += 1
                #send channels to thread pool
                self._read_queue.put(delegator_groups_channel_list)
                delegator_list = remaining_delegators
        else:
            remaining_delegators = delegator_list
        results = self.get_threaded_results(work_units)
        #group all the thread results here
        # find the channels for any decelerators that couldn't be threaded
        delegator_groups_channel_list = []
        for delegator in remaining_delegators:
            for channel in channel_list:
                if channel.resolve_delegator() == delegator:
                    delegator_groups_channel_list.append(channel)
        results.update( self._read_channels_non_threaded(delegator_groups_channel_list) )
        # check results to make sure every channel in channel_list is present, otherwise it is a read error
        for channel in channel_list:
            if channel.get_name() in results:
                pass
            else:
                results[channel.get_name()] = ChannelReadException('READ_ERROR')
        return results
    def start_threads(self,number):
        if self._threaded == False:
            self._threaded = True
            self._threads = number
            self._read_queue = queue.Queue()
            self._read_results_queue = queue.Queue()
            for i in range(number):
                _thread.start_new_thread(self.threaded_read_function, ())
        else:
            raise Exception('Threads already started, do not start again')
    def threaded_read_function(self):
        while self._threaded:
            try:
                channel_list = self._read_queue.get(block=True)
            except queue.Empty:
                #shouldn't get here
                pass
            else:
                try:
                    results = self._read_channels_non_threaded(channel_list)
                except Exception as e:
                    print((traceback.format_exc()))
                    self._read_results_queue.put(e)
                else:
                    self._read_results_queue.put(results)
    def get_threaded_results(self,work_units):
        results = results_ord_dict()
        for i in range(work_units):
            thread_results = self._read_results_queue.get(block=True)
            if isinstance(thread_results,Exception):
                error = thread_results
                #raise thread_results
            else:
                results.update(thread_results)
        if len(results) == 0 and work_units > 0:
            #if we get here every work unit failed, raise exception
            debug_logging.error("error out {}".format(len(results)))
            raise Exception
        return results
    def read_all_channels(self, categories=None, exclusions=[]):
        '''read all readable channels in channel group and return orderd dictionary of results. Optionally filter by list of categories.'''
        channels = [ channel for channel in self.get_all_channels_list() if channel.is_readable() and (categories is None or channel.get_category() in categories)]
        for channel in self.resolve_channel_list(exclusions):
            channels.remove(channel)
        return results_ord_dict(sorted(list(self.read_channel_list(channels).items()), key=lambda t: t[0])) #sort results by channel name
    def remove_channel(self,channel):
        #note this delete will only remove from this channel_group, not from children
        channel_name = channel.get_name()
        if channel_name not in list(self._channel_dict.keys()):
            raise Exception('Channel "{}" is not a member of {}'.format(channel_name,self.get_name()))
        del self._channel_dict[channel_name]
    def remove_channel_group(self,channel_group_to_remove):
        removed_channels = channel_group_to_remove.get_all_channels_list()
        for removed_channel in removed_channels:
            self.remove_channel(removed_channel)
    def remove_channel_by_name(self,channel_name):
        channel = self.get_channel(channel_name)
        self.remove_channel(channel)
    def remove_all_channels_and_sub_groups(self):
        self._channel_dict = results_ord_dict()
        self._sub_channel_groups = []
    def remove_sub_channel_group(self,sub_channel_group):
        self._sub_channel_groups.remove(sub_channel_group)
    def remove_category(self, category):
        #note this delete will only remove from this channel_group, not from children
        for channel in self.get_all_channels_list():
            if channel.get_category() == category:
                self.remove_channel(channel)
    def remove_categories(self, *categories):
        [self.remove_category(category) for category in categories]
    def debug_print(self,indent=" "):
        for ch in list(self._channel_dict.values()):
            d = ""
            if ch.get_delegator() is not ch:
                d = "(delegated by {})".format(ch.resolve_delegator())
            print(("{} {} {}".format(indent,ch,d)))
        for sub_channel_group in self._sub_channel_groups:
            print(("{} {}".format(indent,sub_channel_group)))
            sub_channel_group.debug_print("{}   ".format(indent) )
            #remove the excluded items from the scan list
    def remove_channel_list(self,item_list):
        channel_list = self.resolve_channel_list(item_list)
        for channel in channel_list:
            self.remove_channel(channel)
    def resolve_channel_list(self,item_list):
        '''takes a list of channels, channel_names, or channel_groups and produces a single channel group'''
        ch_group = channel_group()
        for item in item_list:
            if isinstance(item,str):
                ch_group._add_channel(self.get_channel(item))
            elif isinstance(item,channel):
                ch_group._add_channel(item)
            elif isinstance(item,channel_group):
                ch_group.merge_in_channel_group(item)
            else:
                raise Exception('Unknown input {}'.format(item_list))
        return ch_group
    def clone(self, name=None, categories=None):
        '''Builds a flattened group and tries to reconnect to the remote_channels

        If not None, categories list argument acts as a filter - including only channels matching elements of categories.
        '''
        channels = self.get_all_channels_list()
        if categories is not None:
            channels = [channel for channel in channels if channel.get_category() in categories]
        new_channels = []
        remote_channel_group_clients = set()
        for ch in channels:
            if isinstance(ch,remote_channel):
                remote_channel_group_clients.add(ch.get_delegator())
            else:
                new_channels.append(ch)
        for rcgc in remote_channel_group_clients:
            clone_rcgc = rcgc.clone()
            for ch in channels:
                if ch.get_delegator() == rcgc:
                    new_channels.append(clone_rcgc[ch.get_name()])
        if name is None:
            new_group = channel_group(self.get_name() + '_cloned')
        else:
            new_group = channel_group(name)
        for ch in new_channels:
            new_group._add_channel(ch)
        return new_group
    def write_html(self, file_name=None, verbose=True, sort_categories=False):  # pragma: no cover
        '''return html document string and optionally write to file_name
        if verbose, include tables of presets and attributes for each channel
        if sort_categories, group channel names first by category before alphabetical sort of channel name'''
        txt = '<!DOCTYPE html/>'
        txt += '<HTML>\n'
        txt += '<HEAD>\n'
        txt += '<META charset="UTF-8"/>\n'
        txt += '<TITLE>\n'
        txt += 'Secret Channel Decoder Ring\n'
        txt += '</TITLE>\n'
        txt += '<STYLE>\n'
        txt += '    table, th, td {\n'
        txt += '        border: 1px solid black;\n'
        txt += '        border-collapse: collapse;\n'
        txt += '    }\n'
        txt += '</STYLE>\n'
        txt += '</HEAD>\n'
        txt += '<BODY>\n'
        txt += '<TABLE>\n'
        txt += '<TR>\n'
        txt += '<TH>Channel Name</TH>\n'
        txt += '<TH>Category</TH>\n'
        txt += '<TH>Description</TH>\n'
        txt += '</TR>\n'
        channels = sorted(self.get_all_channels_list(), key=lambda ch: ch.get_name())
        if sort_categories:
            channels = sorted(channels, key=lambda ch: str(ch.get_category())) #stable sort preserves name sort above when tied
        for channel in channels:
            txt += '<TR>\n'
            txt += '''<TD><p style='font-family:"Helvetica"'>{}</p></TD>\n'''.format(channel.get_name())
            txt += '''<TD><p style='font-family:"Helvetica"'>{}</p></TD>\n'''.format(channel.get_category())
            txt += '<TD>\n'
            txt += '''<p style='font-family:"Helvetica"'>\n'''
            txt += '{}\n'.format("No Description Available" if channel.get_description() in ['', None,'\n\n'] else channel.get_description())
            txt += '</p>\n'
            if verbose: # add presets and attributes
                try:
                    if len(channel.get_presets()):
                        ps_dict = channel.get_presets_dict()
                        txt += '<form action="/action_page.php">\n'
                        txt += '''<p style='font-family:"Helvetica"'>'''
                        txt += '''<label for="presets">PRESETS: </label>\n'''
                        txt += '<select name="presets" id="presets">\n'
                        for ps in channel.get_presets():
                            txt += f'''<option value="{ps}">{ps}: {ps_dict[ps]}</option>\n'''
                        txt += '</select>\n'
                        txt += '</p>\n'
                        txt += '</form>\n'
                except Exception as e:
                    print((traceback.format_exc())) 
                    pass # Only integer_channels and registers can have presets
                if len(channel.get_attributes()):
                    txt += '<form action="/action_page.php">\n'
                    txt += '''<p style='font-family:"Helvetica"'>'''
                    txt += '''<label for="attributes">ATTRIBUTES:</label>\n'''
                    txt += '<select name="attributes" id="attributes">\n'
                    for attrib in sorted(channel.get_attributes()):
                        txt += f'''<option value="{attrib}">{attrib}: {channel.get_attribute(attrib)}</option>\n'''
                    txt += '</select>\n'
                    txt += '</p>\n'
                    txt += '</form>\n'
            txt += '</TD>\n'
            txt += '</TR>\n'
        txt += '</TABLE>\n'
        txt += '</BODY>\n'
        txt += '</HTML>\n'
        if file_name is not None:
            with open(file_name, 'wb') as f:
                f.write(txt.encode('utf-8'))
                f.close()
        return txt

class instrument(channel_group):
    '''Superclass for all lab instruments
       To add an instrument to a lab_bench object, it must inherit from instrument or one of its specialized subclasses
        Rules for adding instruments:
          1) extend instrument class
          2) call the instrument classes __init__ from its __init__
          3) contain an add_channel (and/or add_channel_XXXXX) methods that:
                a) create a channel object with a:
                    1) name
                    2) EITHER a read_function or write_function
                b) call the _add_channel method with that channel as an argument
          4) has a name attribute which is a meaningful string about the instrument
          '''
    def __init__(self,name):
        '''Overload method in instrument specific class, the __init__ method should call instrument.__init__(self,name).
        if an instrument uses an interface, it must call an add_interface_ function from this class of the appropriate type'''
        channel_group.__init__(self,name)
        self._interfaces = []
        if not hasattr(self,'_base_name'):
            self._base_name = "unnamed instrument"
    def add_channel(self,channel_name):
        '''Usage: Add channel name to instrument.  For multi-channel instruments,
            typically also takes a second argument representing the physical
            channel of the instrument. May also take channel configuration arguments specific to the instrument.

           Operation:  This method should create the channel object then call self._add_channel(channel) to add it to the internal channel group

            Method must be overloaded by each instrument driver.
        '''
        raise Exception('Add channel method not implemented for instrument {}'.format(self.get_name()))
    def get_error(self):
        '''Return the first error from the instrument.  Overload in scpi_instrument or the actual instrument class'''
        return 'Error checking not implemented for this instrument'
    def get_errors(self):
        '''Return a list of all errors from the instrument.  Overload in scpi_instrument or the actual instrument class'''
        return ['Error checking not implemented for this instrument']
    def _add_interface(self,interface):
        self._interfaces.append(interface)
    def get_interface(self, num=0):
        return self._interfaces[num]
    def set_category(self, category_name, update_existing_channels=False):
        self._base_name = category_name
        if update_existing_channels:
            for channel in self:
                channel.set_category(category_name)
    def add_interface_visa(self,interface_visa,timeout=None):
        if not isinstance(interface_visa,lab_interfaces.interface_visa):
            raise Exception('Interface must be a visa interface,, interface is {}'.format(interface_visa))
        if timeout and timeout > interface_visa.timeout:
            # only increase a timeout if it is shared it may be to fast for the others
            interface_visa.timeout = timeout
        self._add_interface(interface_visa)
    def add_interface_raw_serial(self,interface_raw_serial,timeout=None,baudrate=None):
        if not isinstance(interface_raw_serial,lab_interfaces.interface_raw_serial):
            raise Exception('Interface must be a raw serial interface, interface is {}'.format(interface_raw_serial))
        if timeout and timeout > interface_raw_serial.timeout:
            # only increase a timeout if it is shared it may be to fast for the others
            interface_raw_serial.timeout = timeout
        if baudrate:
            interface_raw_serial.baudrate = baudrate
        self._add_interface(interface_raw_serial)
    def add_interface_twi(self,interface_twi,timeout=None):
        if not isinstance(interface_twi,lab_interfaces.interface_twi):
            raise Exception('Interface must be a twi interface, interface is {}'.format(interface_twi))
        if timeout and timeout > interface_twi.timeout:
            # only increase a timeout if it is shared it may be to fast for the others
            interface_twi.timeout = timeout
        self._add_interface(interface_twi)
    def add_interface_spi(self,interface_spi,timeout=None,baudrate=None):
        if not isinstance(interface_spi,lab_interfaces.interface_spi):
            raise Exception('Interface must be an spi interface, interface is {}'.format(interface_spi))
        if timeout and timeout > interface_spi.timeout:
            # only increase a timeout if it is shared it may be to fast for the others
            interface_spi.timeout = timeout
        self._add_interface(interface_spi)
    def _add_channel(self,channel):
        #overload _add_channel to do some automatic repetive tasks before
        #  letting channel_group do the rest
        for interface in self._interfaces:
            channel.add_interface(interface)
        if channel.get_category() is None:
            channel.set_category(self._base_name)
        channel_group._add_channel(self,channel)
        return channel

class scpi_instrument(instrument):
    """SCPI Instrument Base Class. Implements methods common to all SCPI instruments
        Instruments which adhere to the SCPI specification should inherit from the
        scpi_instrument class rather than the instrument class.
    """
    def __init__(self, name):
        super(scpi_instrument, self).__init__(name)
        self._debug_comms = False
    def get_interface(self, num=0):
        if not self._debug_comms:
            return super(scpi_instrument, self).get_interface(num=num)
        else:
            try:
                return self._debug_if
            except AttributeError:
                #first time
                import types
                print(f'Creating SCPI SYS:ERR checking interface for {self.get_name()}')
                self._debug_if = super(scpi_instrument, self).get_interface(num=num)
                self._debug_if._naked_read = self._debug_if.read
                self._debug_if._naked_write = self._debug_if.write
                self._debug_if._naked_ask = self._debug_if.ask
                _raw_if = copy.copy(self._debug_if)
                def read_check(s):
                    resp = s._naked_read()
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(err_lst)
                    return resp
                def write_check(s, m):
                    s._naked_write(m)
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(m, err_lst)
                def ask_check(s, m):
                    resp = s._naked_ask(m)
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(m, err_lst)
                    return resp
                self._debug_if.read = types.MethodType(read_check, self._debug_if)
                self._debug_if.write = types.MethodType(write_check, self._debug_if)
                self._debug_if.ask = types.MethodType(ask_check, self._debug_if)
                return self.get_interface(num=num)
    def get_error(self, interface=None):
        '''Return the first error from the SCPI instrument.  +0 is the errorcode for no error'''
        return self.error(interface=interface)
    def get_errors(self, interface=None):
        '''Return a list of all accumulated SCPI instrument errors.'''
        errors = []
        while(True):
            response = self.get_error(interface=interface)#.decode('utf-8')
            errors.append(response)
            if (response.split(",")[0] == '+0'):
                return errors
            elif (response.split(",")[0] == '0'):
                return errors
    def beep(self):
        '''Send a beep command.'''
        self.get_interface().write('SYST:BEEP')
    def clear_status(self):
        '''Send the *CLS command.'''
        self.get_interface().write('*CLS')
    def display_clear(self):
        """Clear the instrument display"""
        self.get_interface().write('DISP:TEXT:CLE')
    def display_off(self):
        '''Turn the instrument display off'''
        self.get_interface().write('DISP OFF')
    def display_on(self):
        '''Turn the instrument display on'''
        self.get_interface().write('DISP ON')
    def display_text(self,text=""):
        '''Display text on instrument front panel'''
        # command=b"DISP:TEXT '"+text.encode('utf-8')+b"'"
        command=f"DISP:TEXT '{text}'"
        self.get_interface().write(command)
    def enable_serial_polling(self):
        '''Enable the instrument to report operation complete via serial polling'''
        self.clear_status()     #clear the stauts register
        self.get_interface().write('*ESE 1')    #enable the operation complete bit in the event register
        self.get_interface().write('*SRE 32')   #enable the event register to update the status register
    def error(self, interface=None):
        '''Get error message.'''
        if interface is None:
            interface = self.get_interface()
        return interface.ask('SYST:ERROR?')
    def operation_complete(self):
        '''query if current operation is done
            blocks i/o until operation is complete or timeout
            this method retries query until a character is returned in cas of premature timeout
            EDIT - delet retry for now
            '''
        return self.get_interface().ask('*OPC?')
    def fetch(self):
        '''Send FETCH? query.'''
        return self.get_interface().ask('FETCH?')
    def init(self):
        '''Send INIT command.'''
        self.get_interface().write('INIT')
    def initiate_measurement(self,enable_polling=False):
        '''Initiate a measurement'''
        if enable_polling:
            self.enable_serial_polling()         #enable serial polling
            self.clear_status()                  #clear the status register
            self.operation_complete()
            self.init()
            self.get_interface().write('*OPC')         #enable operation complete update to the status register
        else:
            self.operation_complete()
            self.init()
    def read_measurement(self):
        '''Send FETCH? query.'''
        return self.get_interface().ask('FETCH?')
    def reset(self):
        '''Send the *RST command.'''
        self.get_interface().write('*RST')
    def trigger(self):
        '''Send the *TRG command.'''
        self.get_interface().write('*TRG')
    def identify(self):
        '''Send the *IDN? command.'''
        return self.get_interface().ask('*IDN?')
    def flush(self, buffer):
        self.get_interface().flush(buffer)

class remote_channel_group_server(object):
    # this class takes a channel groups and makes it remotely accessible
    # it currently does not support changing channels after creation
    def __init__(self,channel_group_object,address='localhost',port=5001,authkey=DEFAULT_AUTHKEY):
        self.channel_group = channel_group_object
        class channel_group_manager(multiprocessing.managers.BaseManager): pass
        channel_group_manager.register('channel')
        channel_group_manager.register('get_channel_server', callable=lambda: self.channel_group, method_to_typeid={'get_channel':'channel'})
        self.cgm = channel_group_manager(address=(address,port),authkey=authkey)
    def serve_forever(self):
        print(("Launching remote server listening at address {}:{}".format(self.cgm.address[0],self.cgm.address[1])))
        server = self.cgm.get_server()
        server.serve_forever()

class remote_channel(channel):
    # this handles both registers and channels
    methods_to_proxy = ['__str__',
                #integer_channel methods:
                'add_format',
                'add_preset',
                'format',
                'format_read',
                'format_write',
                'get_format',
                'get_formats',
                'get_max_write_limit',
                'get_min_write_limit',
                'get_presets',
                'get_presets_dict',
                'get_units',
                #'read_without_delegator',
                'remove_format',
                'set_format',
                'signedToTwosComplement',
                'twosComplementToSigned',
                'unformat',
                'use_presets_read',
                'use_presets_write',
                'using_presets_read',
                'using_presets_write',
                'write',
                'write_unformatted',

                #channel methods:
                'add_tag',
                'add_tags',
                'add_read_callback',
                'add_write_callback',
                'format_display',
                'get_attribute',
                'get_attributes',
                'get_category',
                'get_description',
                'get_name',
                'get_tags',
                'get_type_affinity',
                'get_write_delay',
                'get_write_history',
                'is_readable',
                'is_writeable',
                'read',
                'set_attribute',
                'set_category',
                'set_description',
                'set_display_format_function',
                'set_display_format_str',
                'set_max_write_limit',
                'set_min_write_limit',
                'set_name',
                'set_read_access',
                'set_write_access',
                'set_write_delay',
                'sql_format',

                #delegator methods omitted
                ]
    def __init__(self,proxy_channel,parent_delegator):
        #this intentially does not call the init of channel,just delegator
        delegator.__init__(self)
        self.set_delegator(parent_delegator)
        self._proxy_delegator = delegator
        for method_name in self.methods_to_proxy:
            if hasattr( proxy_channel, method_name):
                setattr(self, method_name, getattr(proxy_channel, method_name))

class remote_channel_group_client(channel_group,delegator):
    def __init__(self, address='localhost',port=5001,authkey=DEFAULT_AUTHKEY):
        self._address = address
        self._port = port
        self._authkey=authkey
        channel_group.__init__(self,'remote_channel @ {}:{}'.format(address,port))
        delegator.__init__(self)
        class channel_group_manager(multiprocessing.managers.BaseManager): pass
        channel_group_manager.register('channel')
        channel_group_manager.register('get_channel_server')
        #check if the port is open, there doesn't seem to be a way to time out so check first
        import socket;
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((address,port))
        if result:
            #the port is not open
            raise RemoteChannelGroupException('Unable to connect: {}'.format(result))
        self.cgm = channel_group_manager(address=(address,port),authkey=authkey)
        self.cgm.connect()
        self.server = self.cgm.get_channel_server()
        names = self.server.get_all_channel_names()
        for i in names:
            ch = self.server.get_channel(i)
            self._add_channel(remote_channel(ch,self))
    def read_delegated_channel_list(self,channel_list):
        channel_names = [ch.get_name() for ch in channel_list]
        return self.server.read_channels(channel_names)
    def clone(self):
        return remote_channel_group_client(self._address,self._port,self._authkey)

class channel_master(channel_group,delegator):
    '''Master channel collection. There is typically only one. It replaces the old lab_bench
    as the main point of interaction with channels.  Channels and channel_groups (instruments) may
    be added to it.  It also creates dummy and virtual channels and adds them to its collection.  It also
    supports virtual_caching channels; these can use cached data if available during logging or other multiple channel read.'''
    def __init__(self,name=None):
        if name is None:
            name = object.__str__(self)[1:-1] #remove Python <> because Qt interpret's them as HTML tags
        channel_group.__init__(self, name)
        delegator.__init__(self)
        self._caching_mode = 0
        self._read_callbacks = []
        self._write_callbacks = []
        self.start_threads(24)
    def add(self,channel_or_group):
        return channel_group.add(self,channel_or_group)
    def add_channel_virtual(self,channel_name,read_function=None,write_function=None,integer_size=None):
        '''Adds a channel named channel_name. Channel may have a read_function or a write_function but not both.
        If write_function is supplied, the write function is called with the value when written, and the last written value is returned when read.
        If read_function is supplied, this channel returns the return of read_function when read.
        If integer_size is not None, creates in integer_channel instead of a channel. integer_size should specify the number of data bits.
        Integer channels can add presets, formats.'''
        if integer_size is not None:
            new_channel = integer_channel(channel_name,size=integer_size,read_function=read_function,write_function=write_function)
        else:
            new_channel = channel(channel_name,read_function=read_function,write_function=write_function)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_virtual.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)
    def add_channel_virtual_caching(self,channel_name,read_function=None,write_function=None,integer_size=None):
        '''Adds a channel named channel_name. Channel may have a read_function or a write_function but not both.
        If write_function is supplied, the write function is called with the value when written, and the last written value is returned when read.
        If read_function is supplied, this channel returns the return of read_function when read.
        If the read_function calls the creating channel_master's read_channel on another channel,
        a cached value may be used if part of a multi-channel channel read. This can improve logging speed in some cases.'''
        if integer_size is not None:
            new_channel = integer_channel(channel_name,size=integer_size,read_function=read_function,write_function=write_function)
        else:
            new_channel = channel(channel_name,read_function=read_function,write_function=write_function)
        new_channel.set_delegator(self)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_virtual_caching.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)
    def add_channel_dummy(self,channel_name,integer_size=None):
        '''Add a named dummy channel. This can be used if a single physical instrument channel is externally multiplexed to
        multiple measurement nodes. The user can store the multiple measurement results from a single instrument into
        multiple dummy channels. Also it is useful for logging test conditions.'''
        if integer_size is not None:
            new_channel = integer_channel(channel_name,size=integer_size)
        else:
            new_channel = channel(channel_name)
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_dummy.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)
    def add_channel_delta_timer(self,channel_name,reciprocal=False):
        '''Add a named timer channel. Returns the time elapsed since the prior channel read.
        Optionally, compute 1/time to return frequency instead.'''
        class timer(object):
            def __init__(self, reciprocal):
                self.reciprocal = reciprocal
                self.last_time = datetime.datetime.utcnow()
            def __call__(self):
                self.this_time = datetime.datetime.utcnow()
                elapsed = self.this_time - self.last_time
                self.last_time = self.this_time
                if not reciprocal:
                    return elapsed.total_seconds() #return native dimedelta instead?
                else:
                    try:
                        return 1/elapsed.total_seconds()
                    except ZeroDivisionError: #too fast?
                        return None
        new_channel = channel(channel_name, read_function=timer(reciprocal))
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_delta_timer.__doc__)
        new_channel.set_category('Virtual')
        new_channel.set_display_format_function(function = lambda time: eng_string(time, fmt=':3.6g',si=True) + 's')
        return self._add_channel(new_channel)
    def add_channel_total_timer(self,channel_name):
        '''Add a named timer channel. Returns the time elapsed since first channel read.'''
        class timer(object):
            def __init__(self):
                self.beginning = None
            def __call__(self):
                if self.beginning is None:
                    self.beginning = datetime.datetime.utcnow()
                return (datetime.datetime.utcnow() - self.beginning).total_seconds() #return native dimedelta instead?
        new_channel = channel(channel_name, read_function=timer())
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_total_timer.__doc__)
        new_channel.set_category('Virtual')
        new_channel.set_display_format_function(function = lambda time: eng_string(time, fmt=':3.6g',si=True) + 's')
        return self._add_channel(new_channel)
    def add_channel_counter(self,channel_name, **kwargs):
        '''Add a named counter channel. Returns zero the first time channel is read and increments by one each time thereafter.'''
        class counter(object):
            def __init__(self, init=0, inc=1):
                self.inc = inc
                self.count = init - self.inc
            def __call__(self):
                self.count += self.inc
                return self.count
            def write(self, value):
                self.count = value
        cnt_obj = counter(**kwargs)
        new_channel = channel(channel_name, read_function=cnt_obj)
        new_channel._write = cnt_obj.write
        new_channel.set_write_access()
        new_channel.set_description(self.get_name() + ': ' + self.add_channel_counter.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)
    def read_channel(self,channel_name):
        debug_logging.debug("Reading Channel (via channel_master.read_channel): %s", channel_name)
        channel = self.get_channel(channel_name)
        if self._caching_mode:
            if channel_name in self._partial_delegation_results:
                result = self._partial_delegation_results[channel_name]
                debug_logging.debug("Reading Channel: %s from previous results: %s", channel_name, result)
            else:
                result = self.get_channel(channel_name).read()
                debug_logging.debug("Cache miss %s read: %s", channel_name, result)
                if channel in self._self_delegation_channels:
                    self._partial_delegation_results[channel_name] = result
                return result
        else:
            result = self.get_channel(channel_name).read()
        debug_logging.debug("%s read: %s", channel_name, result)
        #calling the observer is done here so its in the secondary thread, if threading
        if not self._caching_mode:
            for function in self._read_callbacks:
                function({channel_name: result})
        return result
    def read_channel_list(self,channel_list):
        read_str = "Reading channel list" #: \n"
        # for c in channel_list:
            # read_str += "\t{}\n".format(c)
        #debug_logging.debug(read_str)
        results = channel_group.read_channel_list(self,channel_list)
        if not self._caching_mode:
            for function in self._read_callbacks:
                debug_logging.debug("Channel master running read callback %s.", function)
                function(results)
        return results
    def write_channel(self,channel_name,value):
        '''Delegates channel write to the appropriate registered instrument.'''
        debug_logging.debug("Writing Channel %s to %s", channel_name, value)
        data =  channel_group.write_channel(self,channel_name,value)
        debug_logging.debug("Channel %s write data unformatted to %s", channel_name, data)
        for function in self._write_callbacks:
            debug_logging.debug("Channel master running write callback %s.", function)
            function({channel_name: data})
        return data
    def read_delegated_channel_list(self,channel_list):
        results = results_ord_dict()
        if self._caching_mode:
            for channel in channel_list:
                if channel.get_name() not in self._partial_delegation_results:
                    results[channel.get_name()] = channel.read_without_delegator()
                    self._partial_delegation_results[channel.get_name()] = results[channel.get_name()]
                else:
                    results[channel.get_name()] = self._partial_delegation_results[channel.get_name()]
        else:
            self._caching_mode += 1
            for channel in channel_list:
                if channel.get_name() not in self._partial_delegation_results:
                    results[channel.get_name()] = channel.read()
                    self._partial_delegation_results[channel.get_name()] = results[channel.get_name()]
                else:
                    results[channel.get_name()] = self._partial_delegation_results[channel.get_name()]
            self._caching_mode -= 1
        if self._caching_mode == 0:
            self._partial_delegation_results = results_ord_dict()
        return results
    def serve(self,address='localhost',port=5001,authkey=DEFAULT_AUTHKEY):
        rcgs = remote_channel_group_server(self,address,port,authkey)
        rcgs.serve_forever()
    def attach(self, address='localhost',port=5001,authkey=DEFAULT_AUTHKEY):
        try:
            rcgc = remote_channel_group_client(address,port,authkey)
        except RemoteChannelGroupException as e:
            print(e)
            return False
        self.add(rcgc)
        return True
    def background_gui(self,cfg_file='default.guicfg'):
        _thread.start_new_thread( self._gui_launcher_passive, (cfg_file,) )
    def gui(self,cfg_file='default.guicfg'):
        self._gui_launcher(cfg_file)
    def add_read_callback(self,read_callback):
        '''Adds a read callback. This is a function that will be called any time a channel(s) is read. the callback function should accept one argument: the dictionary of results.
        If it is not important to group results by each batch read, consider adding a callback to an individual channel instead.'''
        self._read_callbacks.append(read_callback)
    def remove_read_callback(self, read_callback):
        self._read_callbacks.remove(read_callback)
    def add_write_callback(self,write_callback):
        '''Adds a write callback. This is a function that will be called any time a channel is written. the callback function should accept one argument: the dictionary of results.
        In this case, the dictionary will only contain a key,value pair for the single channel that was written. For more flexibility, considering adding a callback to an individual channel instead.'''
        self._write_callbacks.append(write_callback)
    def remove_write_callback(self, write_callback):
        self._write_callbacks.remove(write_callback)
    def _gui_launcher_passive(self,cfg_file):
        from . import lab_gui #this cannot be imported in the main thread
        gui = lab_gui.ltc_lab_gui_app(self,passive=True,cfg_file=cfg_file)
        self.add_read_callback(gui.passive_data)
        self.add_write_callback(gui.passive_data)
        gui.exec_()
    def _gui_launcher(self,cfg_file):
        from . import lab_gui #this cannot be imported in the main thread
        gui = lab_gui.ltc_lab_gui_app(self,passive=False,cfg_file=cfg_file)
        gui.exec_()
    def get_dummy_clone(self):
        clone = channel_master()
        for channel in self:
            clone.add_channel_dummy(channel.get_name())
            clone[channel.get_name()].set_category(channel.get_category())
            if channel._read:
                clone[channel.get_name()].write(0)
        return clone

class master(channel_master,lab_interfaces.interface_factory):
    def __init__(self,name=None):
        channel_master.__init__(self,name)
        lab_interfaces.interface_factory.__init__(self)

class channel_access_wrapper(object):
    '''syntatic sugar object to access channels in a channel_group (or master)
    a channel_group (or master) returns the channel object in response to indexing by channel name
    this gives an object that wraps a channel_group the the channels themselves are access by index names.
    master_instance['channel_name'] returns the channel object
    channel_access_wrapper_instance['channel_name'] returns the channel value
    channel_access_wrapper_instance['channel_name']= value writes the value of channel to value'''
    def __init__(self,channel_group):
        self.channels = channel_group
    def __getitem__(self,channel_name):
        return self.channels[channel_name].read()
    def __setitem__(self,channel_name,value):
        return self.channels[channel_name].write(value)

class logger(master):
    def __init__(self, channel_master_or_group=None, database="data_log.sqlite", use_threads=True):
        '''channel_group is a lab_bench object containing all instruments of interest for logging.
        database is the filename in which the sqlite database will be stored.
        Channels or channel groups added to the channel master after the master is added to the logger will not be registered for logging.
        Notice, however, that the logger inherits from the 'master' class, which means that channels can now be added to the LOGGER after the master has been added as if the logger is a master.
        Suppose a master object is created and channel A is added to it. A logger is then created and the master is added to the logger. Another channel, B, is added to the master, and a third channel, C, is added to the logger.
        In this scenario, both the master and the logger can see and interact with channel A. The master can interact with B but not C, and the logger can interact with C but not B.'''
        master.__init__(self, name='logger')
        if channel_master_or_group is not None:
            self.merge_in_channel_group(channel_master_or_group)
        for channel in self:
            if not channel.is_readable():
                self.remove_channel(channel)
        # if the object given
        if isinstance(channel_master_or_group,channel_master):
            self.master = channel_master_or_group
        else:
            self.master = self
        self._backend = logger_backend(database=database, use_threads=use_threads)
        self._database = database
        atexit.register(self.stop)
        self._table_name = None
        self._log_callbacks = []
        self._previously_logged_data = None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        return None
    def stop(self):
        '''close sqlite database connection.'''
        self._backend.stop()
    def add_channel(self,channel_object):
        self._add_channel(channel_object)
    def append_table(self,table_name):
        self._table_name = table_name
        columns = {ch.get_name():ch.get_type_affinity() for ch in self}
        self._backend.append_table(table_name,columns)
        self.create_format_view()
    def new_table(self,table_name,replace_table=False,warn=False):
        '''create a new table with columns matching channels known to logger instance
        if replace_table == 'copy', previously collected data to a new table with the date and time appended to the table name before overwriting
        if replace_table, allow previously collected data to be overwritten
        if not replace_table, raise an exception (or print to screen instead if warn) rather than overwrite existing data'''
        self._table_name = table_name
        columns = {ch.get_name():ch.get_type_affinity() for ch in self}
        self._backend.new_table(table_name,columns,replace_table,warn)
        self.create_format_view()
    def switch_table(self,table_name):
        self._table_name = table_name
        return self._backend.switch_table(table_name)
    def copy_table(self,old_table, new_table):
        return self._backend.copy_table(old_table,new_table)
    def check_format_name(self, format_name):
        if format_name in self.get_all_channel_names():
            raise ChannelNameException('Formatted channel view name:{} conflicts with table column'.format(format_name))
    def create_format_view(self, use_presets=True):
        if self.get_table_name() is None:
            raise Exception('Table name unspecified!\nCall new_table() or append_table() before log_formats()')
        view_name = '{}_formatted'.format(self.get_table_name())
        self.execute('DROP VIEW IF EXISTS {}'.format(view_name))
        self.execute('DROP VIEW IF EXISTS {}_all'.format(self.get_table_name()))
        sql_txt = ''
        for channel in sorted(self.get_all_channels_list(), key = lambda channel: channel.get_name()):
            try:
                channel_formats = channel.get_formats() #alphabetize? name, units? sorted(channel.get_formats())
                # Formatting already formatted data or preset strings can cause problems.
                # This check isn't perfect, since somebody can always turn channel formats/presets on after logger creation.
                if channel.get_format() is not None:
                    debug_logging.warning("Warning: Channel {} SQL format omitted because channel already has an active format ({}).".format(channel.get_name(), channel.get_format()))
                    continue
                if channel.using_presets_read():
                    debug_logging.warning("Warning: Channel {} SQL format omitted because channel has read presets enabled.".format(channel.get_name()))
                    continue
            except AttributeError:
                #not an integer_channel with formats...
                continue
            except Exception as e:
                debug_logging.warning("{} {}".format(type(e), e))
            sql_formats = [] #stuffed with (sql_format, units, channel_format) (sql str, units str, format_name str)
            for channel_format in channel_formats:
                sql_format = channel.sql_format(channel_format, use_presets)
                if sql_format is not None:
                    sql_formats.append((sql_format, clean_sql(channel.get_units(channel_format)),channel_format))
            if len(sql_formats) == 0:
                #make one more attempt to get presets if all formats were non-XML
                sql_format = channel.sql_format(None, use_presets)
                if sql_format is not None:
                    self.check_format_name('{}_PRESET'.format(channel.get_name()))
                    sql_txt += '{}_PRESET,\n'.format(sql_format)
            elif len(sql_formats) == 1:
                #append _units
                self.check_format_name('{}_{}'.format(channel.get_name(), sql_formats[0][1]))
                sql_txt += '{}_{},\n'.format(sql_formats[0][0], sql_formats[0][1])
            else:
                if len(set([fmt_tuple[1] for fmt_tuple in sql_formats])) == len(sql_formats):
                    #units make unique names
                    for sql_format in sql_formats:
                        self.check_format_name('{}_{}'.format(channel.get_name(), sql_format[1]))
                        sql_txt += '{}_{},\n'.format(sql_format[0], sql_format[1])
                else:
                    #units are duplicated too; append format name
                    for sql_format in sql_formats:
                        self.check_format_name('{}_{}_{}'.format(channel.get_name(), sql_format[1], sql_format[2]))
                        sql_txt += '{}_{}_{},\n'.format(sql_format[0], sql_format[1], sql_format[2])
        elapsed_time = "  (strftime('%s',datetime)\n   + strftime('%f',datetime)\n   - strftime('%S',datetime)\n  )\n  - (strftime('%s',(SELECT min(datetime) FROM {table_name}))\n     + strftime('%f',(SELECT min(datetime) FROM {table_name}))\n     - strftime('%S',(SELECT min(datetime) FROM {table_name}))\n    )\n  AS datetime_sec".format(table_name=self.get_table_name()) #not very efficient and doesn't get added if no presets/formats exist!
        if len(sql_txt):
            sql_txt = 'CREATE VIEW {} AS SELECT\n  rowid,\n{},\n{}\nFROM {}'.format(view_name, elapsed_time, sql_txt[:-2], self.get_table_name())
            self.execute(sql_txt)
            self.execute('CREATE VIEW {}_all AS SELECT * FROM {} JOIN {}_formatted USING (rowid)'.format(self.get_table_name(), self.get_table_name(), self.get_table_name()))
            return sql_txt

        #constants some day?
        #self.execute('CREATE TABLE IF NOT EXISTS {TABLE_NAME}_CONSTANTS (name TEXT PRIMARY KEY, value REAL')
    def get_database(self):
        return self._database
    def get_table_name(self):
        return self._table_name
    def _fetch_channel_data(self,exclusions):
        scan_list = self.get_flat_channel_group('scan_list')
        #only log channels that are readable
        for channel in scan_list.get_all_channels_list():
            if not channel.is_readable():
                scan_list.remove_channel(channel)
        #remove the excluded items from the scan list
        scan_list.remove_channel_list(exclusions)
        channel_data = self.master.read_channel_list(scan_list)
        #add additional database columns
        channel_data['rowid'] = None
        if 'datetime' not in channel_data:
            channel_data['datetime'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return channel_data
    def log(self,exclusions=[]):
        '''measure all non-excluded channels. Channels may be excluded by name, channel_group(instrument), or directly.  Returns a dictionary of what it logged.'''
        self._backend.check_exception()
        data = self._fetch_channel_data(exclusions)
        self._backend.store(data)
        self._previously_logged_data = data
        for (key,value) in data.items():
            if isinstance(value, channel):      
                #avoid deep copying channels(pickle error)
                data[key]=value.get_name()
        data = copy.deepcopy(data)              # Avoid thread contention if callbacks or user script modify dictionary before logger thread gets it processed.
        for callback in self._log_callbacks:
            debug_logging.debug("Logger running log callback %s.", callback)
            callback(data)
        return data
    def check_data_changed(self, data, compare_exclusions=[]):
        '''return True if data is different than self._previously_logged_data.
        Shared test between several log_if_changed methods.'''
        if self._previously_logged_data is None:
            return True
        else:
            old_data = dict(self._previously_logged_data)
            new_data = dict(data)
            del old_data['rowid']
            del old_data['datetime']
            if 'rowid' in new_data:
                del new_data['rowid']
            if 'datetime' in new_data:
                del new_data['datetime']
            for item in compare_exclusions:
                if isinstance(item,str):
                    del old_data[item]
                    del new_data[item]
                elif isinstance(item,channel):
                    del old_data[item.get_name()]
                    del new_data[item.get_name()]
                else:
                    raise Exception('Unknown compare exclusion type: {} {}'.format(type(item),item))
            return old_data != new_data
    def log_if_changed(self, log_exclusions=[], compare_exclusions=[]):
        '''like log(), but only stores data to database if data in at least on channel/column has changed.
        log_exclusions is a list of logger channels which will not be read nor stored in the database.
        compare_exclusions is a list of logger channels which will not be used to decide if data has changed but which will be read and stored in the databased if something else changed.
        rowid and datetime are automatically excluded from change comparison.
        returns channel data if logged, else None'''
        self._backend.check_exception()
        data = self._fetch_channel_data(log_exclusions)
        if self.check_data_changed(data, compare_exclusions):
            self._backend.store(data)
            self._previously_logged_data = data
            #skip callbacks if data unchanged?
            for callback in self._log_callbacks:
                debug_logging.debug("Logger running log callback %s form log_if_changed.", callback)
                callback(data)
            return data
        else:
            return None
    def log_data(self, data_dictionary, only_if_changed=False):
        '''log previously collected data.
        data_dictionary should have channel name keys.
        set up logger and table using logger.add_data_channels()
        alternately, data_dictionary can be an iterable containing dictionaries, each representing a single row.'''
        self._backend.check_exception()
        try:
            if not only_if_changed or self.check_data_changed(data_dictionary, compare_exclusions=[]):
                #compare_exclusions not currently supported
                data_dictionary['rowid'] = None
                if data_dictionary.get('datetime', None) is None:
                    data_dictionary['datetime'] = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                self._backend.store(data_dictionary)
                self._previously_logged_data = data_dictionary
                return data_dictionary
            return None #skipped duplicate data
        except TypeError:
            #not a mapping type, assume iterable of mapping
            print('Interable of mapping type is better logged with log_many() method') # TODO print or debugg logging?
            for row in data_dictionary:
                assert len(list(row.keys())) #try to prevent infinite recursion with malformed data
                self.log_data(row)
    def log_kwdata(self, **kwargs):
        '''log previously collected data, but provided as keyword key,value pairs instead of dictionary.'''
        return self.log_data(kwargs, only_if_changed=False)
    def log_many(self, data_iter_of_dictionaries):
        self._backend.check_exception()
        #walrus comprehension not yet available in Python 3.7
        logtime=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        for row in data_iter_of_dictionaries:
            row['rowid'] = None 
            if row.get('datetime', None) is None:
                row['datetime'] = logtime
            self._previously_logged_data = row
        self._backend.storemany(data_iter_of_dictionaries)
    def add_data_channels(self, data_dictionary):
        '''prepare logger channel group with fake channels matching data_dictionary keys.
        call before logger.new_table().
        use to log previously collected data in conjunction with logger.log_data()
        '''
        assert len(self.get_all_channel_names()) == 0
        def read_disable():
            raise Exception('Attempted to read fake channel designed to be used with logger.log_data()')
        for key in data_dictionary:
            fake_channel = channel(key, read_function=read_disable)
            self.add_channel(fake_channel)
    def add_log_callback(self,log_callback):
        '''Adds a read callback. This is a function that will be called any time a channel(s) is read. the callback function should accept one argument: the dictionary of results.
        If it is not important to group results by each batch read, consider adding a callback to an individual channel instead.'''
        self._log_callbacks.append(log_callback)
    def remove_log_callback(self, log_callback):
        self._log_callbacks.remove(log_callback)
    def get_master(self):
        return self.master
    def get_data(self):
        return sqlite_data(table_name=self.get_table_name(), database_file=self.get_database())
    def query(self, sql_query, *params):
        return self.get_data().query(sql_query, *params)
    def flush(self):
        '''commit pending transactions and block until database thread queue is empty.'''
        self._backend.sync_threads()
    def set_journal_mode(self, journal_mode='WAL', synchronous='NORMAL', timeout_ms=10000):
        '''configure database connection for more reliable concurrent read/write operations with high data throughput or large data sets.
        Three options are individually configurable:

        journal_mode changes the default rollback journal to other methods which read-lock the database less often and for less time.
        WAL (write-ahead log) is usually the best choice. Reading and writing are independet and will never block each other.
        https://www.sqlite.org/pragma.html#pragma_journal_mode
        https://www.sqlite.org/wal.html

        synchronouns changes how SQLite waits to confirm that data has been safely written to the disk platter surface.
        Relaxing this from FULL to NORMAL to OFF will increase commit speed with an increasing risk of data corruption if power is lost or the compute crashes at an inopportune time.
        Use with caution. Usually WAL alone will correct most access problems.
        https://www.sqlite.org/pragma.html#pragma_synchronous

        timeout_ms changes the amount of time SQLite will wait for access to a locked database before giving up and failing.
        Timeouts are much less likely in WAL mode compated to normal rollback journal mode.
        https://www.sqlite.org/pragma.html#pragma_busy_timeout
        '''
        self._backend.execute("PRAGMA locking_mode = NORMAL")
        self._backend.execute("PRAGMA busy_timeout = {}".format(timeout_ms))
        journal_mode = journal_mode.upper()
        if journal_mode not in ["DELETE","TRUNCATE","PERSIST","MEMORY","WAL","OFF"]:
            raise Exception('Valid arguments to journal_mode are "DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", and "OFF". See https://www.sqlite.org/pragma.html#pragma_journal_mode')
        self._backend.execute("PRAGMA journal_mode = {}".format(journal_mode))
        if journal_mode == "WAL":
            self._backend.execute("PRAGMA wal_autocheckpoint=100")
        synchronous = synchronous.upper()
        if synchronous not in ["OFF","NORMAL","FULL","EXTRA"]:
            raise Exception('Valid arguments to synchronous are "OFF", "NORMAL", "FULL", and "EXTRA". See https://www.sqlite.org/pragma.html#pragma_synchronous')
        self._backend.execute("PRAGMA synchronous = {}".format(synchronous))
    def optimize(self):
        '''Defragment database file, reducing file size and speeding future queries.
        Also re-runs query plan optimizer to speed future queries.
        WARNING: May take a lot time to complete when operating on a large database.
        WARNING: May re-order rowid's
        '''
        self.execute("VACUUM")
        self.execute("ANALYZE")
    def execute(self, sql_query, *params):
        '''Execute arbitrary SQL statements on database.
        Not capable of returning results across thread boundary.
        Useful to set up views, indices, etc
        '''
        self._backend.execute(sql_query, *params)

class logger_backend(object):
    def __init__(self,database="data_log.sqlite", use_threads=True):
        self.table_name = None
        self._use_thread = use_threads
        self._max_lock_time = datetime.timedelta(seconds=10)
        self._thread_exception = None
        self._run = True
        self._stopped = False
        database = os.path.expanduser( os.path.expandvars(database) ) #resolve env vars + ~
        if self._use_thread:
            self.storage_queue = queue.Queue()
            self._thread = _thread.start_new_thread(self._db_thread, ())
            self.storage_queue.put(lambda: self._connect_db(database))
        else:
            self._connect_db(database)
        atexit.register(self.stop)
    def _close(self):
        debug_logging.info("Closing database connection.")
        try:
            checkpoint_command = "PRAGMA wal_checkpoint(RESTART);" #no effect if DB not in write-ahead log journal mode
            try:
                self.conn.execute(checkpoint_command)
            except sqlite3.OperationalError as e:
                debug_logging.warning("Checkpoint failed.")
                debug_logging.warning("  Specifically, '{}' raised exception '{}'".format(checkpoint_command, e))
            try:
                self.conn.execute("PRAGMA journal_mode=DELETE;")
            except sqlite3.OperationalError as e:
                debug_logging.warning("Journal mode change failed. Is another app connected to the database file?")
                debug_logging.warning("  Specific exception raised was: {}".format(e))
            self.conn.close()
        except sqlite3.ProgrammingError as e:
            #can't execute if connection previously closed
            print(e)
        except Exception as e:
            debug_logging.error("Unhandled exception in _close!")
            debug_logging.error("{} {}".format(e, type(e)))
    def sync_threads(self):
        if self._use_thread:
            self.storage_queue.put(self._commit)
            self.storage_queue.join()
            self.check_exception()
        else:
            self._commit()
    def check_exception(self):
        self._check_exception()
    def _check_exception(self):
        if self._thread_exception:
            raise self._thread_exception
    def execute(self, sql_query, *params):
        '''not currently capable of returning the query result through the thread queue
        useful for setting up the database with PRAGMA commands.'''
        if self._use_thread:
            self.storage_queue.put(lambda: self._execute(sql_query, *params))
        else:
            self._execute(sql_query, *params)
        self.sync_threads()
    def _execute(self, sql_query, *params):
        cursor = self.conn.cursor()
        if len(params):
            return cursor.execute(sql_query, params)
        else:
            return cursor.executescript(sql_query)
    def _connect_db(self,database):
        self.db = database
        self.conn = sqlite3.connect(self.db, isolation_level=None) # isolation_level of None means turn off Python sqlite3 module's automatic BEGIN and COMMIT: we'll handle transactions ourselves.
        # self.cur = self.conn.cursor()
    def _db_thread(self):
        self.lock_time = None
        self._stopped = False # redundant but defensive
        while self._run:
            dbconn = getattr(self, "conn", None)
            if self.lock_time is not None and (datetime.datetime.utcnow()-self.lock_time) > self._max_lock_time:
                self._commit()
                self.lock_time = None
                #print 'max lock timed out'
            try:
                function = self.storage_queue.get(block=False)
            except queue.Empty:
                if self.lock_time is not None:
                    try:
                        self.conn.commit() #not self._commit to avoid infinite retry
                        checkpoint_command = "PRAGMA wal_checkpoint(PASSIVE);" #no effect if DB not in write-ahead log journal mode
                        try:
                            self.conn.execute(checkpoint_command)
                        except sqlite3.OperationalError as e:
                            debug_logging.warning("{} raised exception {}".format(checkpoint_command, e))
                    except sqlite3.OperationalError as e:
                        debug_logging.warning("Opportunistic commit failed. Not retrying.")
                    else:
                        self.lock_time = None
                function = self.storage_queue.get(block=True)
            finally:
                try:
                    if self.lock_time is None:
                        self.lock_time = datetime.datetime.utcnow()
                    function()
                except Exception as e:
                    print((traceback.format_exc()))
                    raise e
                    self._thread_exception = e
                finally:
                    self.storage_queue.task_done()
        self._stopped = True
    def store(self,data):
        if self._use_thread:
            self.storage_queue.put(lambda: self._store(data))
        else:
            self._store(data)
            self.conn.commit()
    def storemany(self,data):
        if self._use_thread:
            self.storage_queue.put(lambda: self._storemany(data))
        else:
            self._storemany(data)
            self.conn.commit()
    def _new_table(self,table_name,columns,replace_table=False,warn=False):
        '''create new table in the sqlite database with a column for each channel.
            replace any existing table with the same name (delete data!).'''
        table_name = str(table_name).replace(" ","_")

        try:
            self._create_table(table_name,columns)
            self._commit()
        except sqlite3.OperationalError as e:
            if isinstance(replace_table, str) and replace_table.lower() == 'copy':
                try:
                    #try to name copied table for when it was created, not time now.
                    try:
                        table_date = self.conn.execute('SELECT DATETIME from {} ORDER BY DATETIME ASC LIMIT 1'.format(table_name)).fetchone()[0]
                        table_date = datetime.datetime.strptime(table_date, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y_%m_%dT%H_%M_%SZ')
                    except TypeError as e:
                        debug_logging.warning("WARNING: Failed to extract datetime information from table {}. Reverting to current time".format(self.table_name))
                        table_date = datetime.datetime.utcnow().strftime('%Y_%m_%dT%H_%M_%SZ')
                    self._copy_table(self.table_name, '{}_{}'.format(table_name, table_date))
                    self.conn.execute("DROP TABLE {}".format(self.table_name))
                    self._commit()
                except sqlite3.OperationalError as e:
                    debug_logging.error(e)
                    debug_logging.error("Table not copied (may not exist): {}".format(self.table_name))
                self._create_table(table_name,columns)
                self._commit()
            elif replace_table:
                try:
                    self.conn.execute("DROP TABLE {}".format(self.table_name))
                    self._commit()
                except sqlite3.OperationalError as e:
                    debug_logging.error(e)
                    debug_logging.error("Table not dropped (may not exist): {}".format(self.table_name))
                self._create_table(table_name,columns)
                self._commit()
            else:
                if warn:
                    debug_logging.warning('Table name {} creation failed.  Table probably exists. Rename table, change table name argument, or call with replace_table argument=True'.format(self.table_name))
                else:
                    raise e
    def _create_table(self,table_name,columns):
        '''create the actual sql table and commit to database.  Called by new_sweep_replace() (and new_sweep()?)'''
        self.table_name = table_name
        self.columns = list(columns)
        self.columns.sort()
        txt = "CREATE TABLE " + self.table_name + " ( rowid INTEGER PRIMARY KEY, datetime DATETIME, "
        for column in self.columns:
            if column == 'datetime':
                continue
            try:
                txt += f'"{column}" {columns[column]}, '
            except TypeError as e:
                ## It's the legacy list. But. . .why?
                txt += f'"{column}" NUMERIC, '
                print(e) ## The world needs to know.
                print("Contact pyice-developers@analog.com. Or file a bug report at jira.analog.com/projects/PYICE")
        txt = txt[:-2]
        txt += " )"
        self.conn.execute(txt)
        self._commit()
    @classmethod
    def db_clean(cls, column_data):
        '''help database to store lists, dictionaries and any other future datatype that doesn't fit natively'''
        # perhaps better implemented using sqlite.register_adapter?
        # https://docs.python.org/2/library/sqlite3.html#registering-an-adapter-callable
        # https://docs.python.org/2/library/sqlite3.html#sqlite3.register_adapter
        if isinstance(column_data,list):
            return str(column_data)
        elif isinstance(column_data,dict):
            return str(column_data)
        elif isinstance(column_data,tuple):
            return str(column_data)
        elif not numpy_missing and isinstance(column_data,ndarray):
            dtype_header = bytearray(column_data.dtype.str, encoding='latin1') # ex '<d' or '<i4'
            dtype_header.insert(0, len(column_data.dtype.str)) # ex \x02 or \x03
            bytes_coldata = column_data.tobytes()
            return dtype_header+bytes_coldata
        elif isinstance(column_data,ChannelReadException):
            return None
        elif isinstance(column_data,channel):
            return str(column_data)
        return column_data
    def _store(self,data,num=0):
        '''match data dictionary keys to table column names and commit new row to table.'''
        if self.table_name is None:
            raise Exception("Need to create a table before logging")
        if len(data) <= 999:
            # SQLITE_MAX_VARIABLE_NUMBER defaults to 999
            q = ("?," * len(data))[:-1]
            values = tuple([self.db_clean(column) for column in list(data.values())])
            cursor = self.conn.cursor()
            sql = "INSERT INTO {} {} VALUES ({})".format(self.table_name, tuple(data.keys()), q)
            try:
                cursor.execute(sql,values)
                data['rowid'] = cursor.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name)).fetchone()[0]
            except sqlite3.OperationalError as e:
                if num > 2:
                    debug_logging.warning(data)
                    debug_logging.warning(e)
                    debug_logging.warning("Try {} failed. Trying again...".format(num))
                time.sleep(0.01)
                self._store(data,num=num+1) #keep trying forever
        else:
            # SQLITE_MAX_COLUMN defaults to 2000
            data_cp = data.copy() #don't delete rowid from original dict
            try:
                del data_cp['rowid']
            except KeyError:
                pass
            q = ("?," * 999)[:-1]
            values = tuple([self.db_clean(column) for column in list(data_cp.values())[:999]])
            sql = "INSERT INTO {} {} VALUES ({})".format(self.table_name, tuple(list(data_cp.keys())[:999]), q)
            try:
                self.conn.execute(sql,values)
            except sqlite3.OperationalError as e:
                if num > 2:
                    debug_logging.warning(data_cp)
                    debug_logging.warning(e)
                    debug_logging.warning("Try {} failed. Trying again...".format(num))
                time.sleep(0.01)
                self._store(data,num=num+1) #keep trying forever
            cursor = self.conn.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name))
            data['rowid'] = cursor.fetchone()[0]
            # data['rowid'] = self.cur.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name)).fetchone()[0]
            assignments = ', '.join(["'{}' = ?".format(k) for k in list(data_cp.keys())[999:]])
            values = tuple([self.db_clean(column) for column in list(data_cp.values())[999:]])
            sql = "UPDATE {} SET {} WHERE rowid == {}".format(self.table_name, assignments, data['rowid'])
            while True:
                try:
                    self.conn.execute(sql,values)
                    break
                except sqlite3.OperationalError as e:
                    if num > 2:
                        debug_logging.warning(data_cp)
                        debug_logging.warning(e)
                        debug_logging.warning("Try {} failed. Trying again...".format(num))
                    time.sleep(0.01)
                    num += 1
    def _storemany(self,data_iter,num=0):
        '''match data dictionary keys of each iter element to table column names and commit multiple new rows to table.
        all elements of iterable must have same dimention and type
        column count above 999 not currently supported'''
        if self.table_name is None:
            raise Exception("Need to create a table before logging")
        set_of_data_lengths={len(row) for row in data_iter}
        assert len(set_of_data_lengths)==1, f'storemany iterable element has items of disparate dimension {set_of_data_lengths}'
        example_row = (next(iter(data_iter)))
        q = ("?," * len(example_row))[:-1]
        values = tuple(tuple(self.db_clean(column) for column in row.values()) for row in data_iter)
        cursor = self.conn.cursor()
        sql = "INSERT INTO {} {} VALUES ({})".format(self.table_name, tuple(example_row.keys()), q)
        try:
            cursor.executemany(sql,values)
            # data['rowid'] = cursor.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name)).fetchone()[0]
            cursor.close() #rapid garbage collection might speed things up 
        except sqlite3.OperationalError as e:
            if num > 2:
                debug_logging.warning(data)
                debug_logging.warning(e)
                debug_logging.warning("Try {} failed. Trying again...".format(num))
            time.sleep(0.01)
            self._storemany(data_iter,num=num+1) #keep trying forever
    def copy_table(self,old_table,new_table):
        self._check_name(new_table)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(lambda: self._copy_table(old_table,new_table))
        else:
            self._copy_table(old_table,new_table)
        self.sync_threads()
    def _copy_table(self, old_table, new_table):
        #inspecting sql create statements allows type preservation. Otherwise, it gets clobbered. DATETIME specifically doesn't get copied correctly.
        cursor = self.conn.cursor()
        cursor.execute("SELECT sql FROM sqlite_master WHERE tbl_name=='{}'".format(old_table))
        sql_create = cursor.fetchone()[0]
        new_sql, count = re.subn("^CREATE TABLE {old_table} \( rowid INTEGER PRIMARY KEY, datetime DATETIME, ".format(old_table=old_table), "CREATE TABLE {new_table} ( rowid INTEGER PRIMARY KEY, datetime DATETIME, ".format(new_table=new_table), sql_create, flags=re.DOTALL)
        assert count == 1
        self._execute(new_sql)
        self._execute("INSERT INTO {} SELECT * FROM {}".format(new_table, old_table))

        #look for format view to copy also
        cursor.execute("SELECT sql FROM sqlite_master WHERE type=='view' AND tbl_name=='{}_formatted'".format(old_table))
        sql_format = cursor.fetchone()
        if sql_format is not None:
            sql_txt, count = re.subn("^CREATE VIEW (.*?) AS SELECT\n  (.*)\nFROM (.*?)$", "CREATE VIEW {new_table}_formatted AS SELECT\n  \\2\nFROM {new_table}".format(new_table=new_table), sql_format[0], flags=re.DOTALL)
            assert count == 1
            #now rewrite datetime_sec view to point to new view name
            sql_txt, count = re.subn("\(SELECT min\(datetime\) FROM (.*?)\)", "(SELECT min(datetime) FROM {new_table})".format(new_table=new_table), sql_txt, flags=re.DOTALL)
            assert count == 3
            self._execute(sql_txt)
        #now look for the joined view to copy
        cursor.execute("SELECT sql FROM sqlite_master WHERE type=='view' AND tbl_name=='{}_all'".format(old_table))
        sql_format = cursor.fetchone()
        if sql_format is not None:
            sql_txt, count = re.subn("^CREATE VIEW (.*?) AS SELECT \* FROM (.*?) JOIN (.*?) USING \(rowid\)$", "CREATE VIEW {new_table}_all AS SELECT * FROM {new_table} JOIN {new_table}_formatted USING (rowid)".format(new_table=new_table), sql_format[0], flags=re.DOTALL)
            assert count == 1
            self._execute(sql_txt)
    def _commit(self, retries=10):
        for try_count in range(retries):
            try:
                self.conn.commit()
            except sqlite3.OperationalError as e:
                debug_logging.warning(e)
                debug_logging.warning("Trying commit again...")
            else:
                break
    def switch_table(self,table_name):
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(lambda: self._switch_table(table_name))
        else:
            self._switch_table(table_name)
        self.sync_threads()
    def _switch_table(self,table_name):
        self.table_name = table_name
    def append_table(self,table_name,columns):
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(lambda: self._append_table(table_name,columns))
        else:
            self._append_table(table_name,columns)
        self.sync_threads()
    def _append_table(self,table_name,columns):
        try:
            self._new_table(table_name,columns,replace_table=False,warn=False)
            self._commit()
        except sqlite3.OperationalError:
            pass
        self._switch_table(table_name)
        for column in columns:
            try:
                self.conn.execute("ALTER TABLE {} ADD {} NUMERIC".format(self.table_name, column))
                self._commit()
            except sqlite3.OperationalError as e:
                pass
            else:
                debug_logging.info("Added column: {} to table: {}".format(column, self.table_name))
    def _check_name(self,name):
        if not re.match("[_A-Za-z][_a-zA-Z0-9]*$",name):
            raise Exception('Bad Table Name "{}"'.format(name))
    def new_table(self,table_name,columns,replace_table=False,warn=False):
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(lambda: self._new_table(table_name,columns,replace_table,warn))
        else:
            self._new_table(table_name,columns,replace_table,warn)
        self.sync_threads()
    def stop(self):
        if self._use_thread:
            if not self._stopped:
                self.storage_queue.put(self._stop)
                self.storage_queue.join()
        else:
            # non-threaded case
            self._stop()
    def _stop(self):
        try:
            self._commit()
        except sqlite3.ProgrammingError as e:
            #can't commit if connection previously closed
            debug_logging.error(e)
        except Exception as e:
            debug_logging.error("Unhandled exception in _stop!")
            debug_logging.error("{} {}".format(type(e), e))
        finally:
            self._close()
            self._run = False


if __name__ == "__main__": # pragma: no cover
    def print_it(x):
        print(x)
    #test of threaded delegation
    lb = master()
    if not lb.attach(address='localhost'):
        print("creating fake channels")
        # make 4 communication nodes, a-d, a and b are root level interfaces, b is not thread safe, c and d are downstream of b
        ia = lb.get_dummy_interface(name='a')
        ia.set_com_node_thread_safe(True)
        ib = lb.get_dummy_interface(name='b')
        ib.set_com_node_thread_safe(True)
        ic = lb.get_dummy_interface(parent=ib,name='c')
        id = lb.get_dummy_interface(parent=ib,name='d')

        #create some dummy channels using these interfaces
        ch1_ia = channel('ch1_ia', read_function = lambda: time.sleep(0.3)  )
        ch1_ia.add_interface(ia)
        ch2_ic = channel('ch2_ic', read_function = lambda: time.sleep(0.1) )
        ch2_ic.add_interface(ic)
        ch3_id = channel('ch3_id', read_function = lambda: time.sleep(0.1) )
        ch3_id.add_interface(id)
        ch4_id = channel('ch4_id', read_function = lambda: time.sleep(0.1) )
        #ch4_id.set_delegator(ch3_id)
        ch4_id.add_interface(id)

        lb._add_channel(ch1_ia)
        lb._add_channel(ch2_ic)
        lb._add_channel(ch3_id)
        lb._add_channel(ch4_id)
        lb.add_channel_dummy('dummy')
        lb.write('dummy',"dummydata")
        lb.add_channel_virtual('virtual_print',write_function= lambda x: print_it(x))
        print("new_logger")
        lb.gui()
        logger = logger(lb)
        logger.new_table("test_table",replace_table=True)
        logger.set_journal_mode()
        logger.log()
        logger.log()
        #lb.background_gui()
        #lb.serve(address='localhost')
        print("done")
    else:
        print("did not create any channels")
        tstart = time.time()
        data =  lb.read_all_channels()
        print(("read took {}".format(time.time()-tstart)))
        print(data)

        lgr = logger(lb)
        lgr.new_table('test',replace_table=True)
        lgr.log()
        lgr.log()

        #lgr.gui()

        #lb.gui() # pra
