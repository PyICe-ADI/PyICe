"""Channel and Threading Core Framework.

====================================

changes to this file should be minimal!

Examples:
    >>> from PyICe import lab_core
    >>> m = lab_core.master()
    >>> ch = m.add_channel_dummy('test')
    >>> ch.write(42)
    42

"""
import logging
import copy
import os
import numbers
import datetime
import collections
import atexit
import time
import multiprocessing
import multiprocessing.managers
import traceback
import _thread
import re
import queue
import sqlite3
from PyICe.lab_utils.sqlite_data import sqlite_data
from PyICe.lab_utils.clean_sql import clean_sql
from PyICe.lab_utils.eng_string import eng_string
from PyICe.lab_utils.signedToTwosComplement import signedToTwosComplement
from PyICe.lab_utils.twosComplementToSigned import twosComplementToSigned
from PyICe.lab_utils.egg_timer import egg_timer
from PyICe import lab_interfaces
from PyICe import logo
from . import DEFAULT_AUTHKEY
import sys
sys.path.append('..')
logo.display()

try:
    from numpy import ndarray
    numpy_missing = False
except ImportError:
    numpy_missing = True

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
    """Ordered dictionary for channel results reporting with pretty print addition.

    >>> from PyICe.lab_core import results_ord_dict
    >>> d = results_ord_dict([('voltage', 3.3), ('current', 0.01)])
    >>> print(d)
    voltage: 3.3
    current: 0.01
    <BLANKLINE>
    """
    def __str__(self):
        """Return column-aligned key: value listing of all results.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.

        >>> from PyICe.lab_core import results_ord_dict
        >>> d = results_ord_dict([('a', 1), ('b', 2)])
        >>> print(d)
        a: 1
        b: 2
        <BLANKLINE>

        Returns:
            String representation.
        """
        s = ''
        max_channel_name_length = 0
        for k, v in self.items():
            max_channel_name_length = max(max_channel_name_length, len(k))
            s += '{}:\t{}\n'.format(k, v)
        # The '\xFA' messes up in Python 3, maybe because Python 3 treats all strings as Unicode.
        # Removing for now as it seems to be for aesthetics only.
        # s = s.replace(' ', '\xFF') # temporary move
        s = s.expandtabs(max_channel_name_length + 2)
        # s = s.replace(' ', '\xFA') # just the tab spaces
        # s = s.replace('\xFF', ' ') # put back non-tab spaces
        return s

    def __getstate__(self):
        """Return empty state so that pickling ignores internal C-level state.
        Controls what is included when the object is pickled.

        Implements the ``__getstate__`` protocol for this object.

        >>> from PyICe.lab_core import results_ord_dict
        >>> d = results_ord_dict([('voltage', 3.3)])
        >>> d.__getstate__()
        {}

        Returns:
            An empty dictionary.
        """
        return {}


class delegator(object):
    """Mixin that routes channel reads/writes through a delegation chain.

    Every channel belongs to a delegator (typically an ``instrument`` or
    ``channel_master``).  When a channel group or master reads many
    channels at once, it calls ``read_delegated_channel_list`` on the
    root delegator so that the instrument driver can batch I/O into
    fewer bus transactions.  Subclasses override that method to provide
    hardware-optimised batch reads.

    >>> from PyICe.lab_core import delegator
    >>> delegator is not None
    True

    """
    def __init__(self):
        """Initialize with self-delegation, threading enabled, and no interfaces.

        Stores configuration in ``_interfaces``, ``_threadable`` for use by
        other methods.

        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.get_delegator() is d
        True
        >>> d.threadable()
        True

        """
        self.set_delegator(self)
        self._threadable = True
        self._interfaces = []

    def set_delegator(self, delegator):
        """Point this object's reads/writes at *delegator* instead of itself.

        Called automatically when an instrument is added to a master;
        the master becomes the delegator so it can batch reads across
        multiple instruments.


        >>> from PyICe.lab_core import delegator
        >>> d1 = delegator()
        >>> d2 = delegator()
        >>> d1.set_delegator(d2)
        >>> d1.get_delegator() is d2
        True

        Args:
            delegator: The object that will handle batched read/write
                operations on behalf of this one.
        """
        self._delegator = delegator

    def get_delegator(self):
        """Return the immediate delegator (one level up the chain).
        Returns the stored delegator value from the object's internal state.
        Returns the stored delegator from the object's internal state.

        Returns the stored delegator from the object's internal state.


        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.get_delegator() is d
        True

        Returns:
            The delegator object currently handling this object's I/O.
        """
        return self._delegator

    def set_allow_threading(self, state=True):
        """Allow or prevent this delegator's channels from being read in parallel threads.

        Disable threading when the underlying interface is not thread-safe
        (e.g. a shared serial port).


        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.set_allow_threading(False)
        >>> d.threadable()
        False
        >>> d.set_allow_threading()
        >>> d.threadable()
        True

        Args:
            state: True to allow threaded reads (default), False to force
                sequential reads.
        """
        self._threadable = state

    def threadable(self):
        """Check whether threaded (parallel) reads are allowed.

        Supports the ``delegator`` workflow by performing the described operation.


        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.threadable()
        True

        Returns:
            True if threaded reads are permitted, False otherwise.
        """
        return self._threadable

    def resolve_delegator(self):
        """Walk the delegation chain to find the root delegator.

        The root is the delegator that delegates to itself.  In a typical
        setup this is the ``channel_master`` or ``master``.


        >>> from PyICe.lab_core import delegator
        >>> d1 = delegator()
        >>> d1.resolve_delegator() is d1
        True
        >>> d2 = delegator()
        >>> d2.set_delegator(d1)
        >>> d2.resolve_delegator() is d1
        True

        Returns:
            The root delegator at the end of the chain.
        """
        if self._delegator == self:
            return self._delegator
        else:
            return self._delegator.resolve_delegator()

    def add_interface(self, interface):
        """Register a communication interface for lock management.

        Interfaces are locked before batched reads/writes and unlocked
        afterward to prevent concurrent access from multiple threads.


        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d._interfaces
        []
        >>> d.add_interface("iface1")
        >>> d._interfaces
        ['iface1']

        Args:
            interface: A ``lab_interfaces.interface`` instance to manage.
        """
        self._interfaces.append(interface)

    def get_interfaces(self):
        """Collect all interfaces registered on the root delegator.
        Returns the stored interfaces value from the object's internal state.
        Returns the stored interfaces from the object's internal state.

        Returns the stored interfaces from the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel('test')
        >>> ch.get_interfaces()
        set()

        Returns:
            A ``set`` of interface objects from the root of the chain.
        """
        if self.get_delegator() == self:
            return set(self._interfaces)
        else:
            return self.resolve_delegator().get_interfaces()

    def lock_interfaces(self):
        """Acquire exclusive locks on all registered interfaces.

        Records the item so that it participates in future operations.

        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.lock_interfaces()  # No interfaces, no-op

        """
        for interface in self._interfaces:
            interface.lock()

    def unlock_interfaces(self):
        """Release exclusive locks on all registered interfaces.

        Records the item so that it participates in future operations.

        >>> from PyICe.lab_core import delegator
        >>> d = delegator()
        >>> d.unlock_interfaces()  # No interfaces, no-op

        """
        for interface in self._interfaces:
            interface.unlock()

    def write_delegated_channel_list(self, channel_value_list):
        # (NOT IMPLEMENTED YET)
        # OVERLOAD THIS FUNCTION
        # takes a list of (channels, value) tuples
        # writes each channel to its corresponding value
        """Write a batch of channel/value pairs while holding interface locks.

        Subclasses should override this to provide hardware-optimised
        batch writes.  The default implementation writes each channel
        sequentially.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write_delegated_channel_list')
        True

        Args:
            channel_value_list: Iterable of ``(channel, value)`` tuples
                to write.

        Raises:
            Exception: Re-raised from the underlying write after releasing
                interface locks.
        """
        try:
            self.lock_interfaces()
            for (channel, value) in channel_value_list:
                channel.write(value)
            self.unlock_interfaces()
        except Exception as e:
            self.unlock_interfaces()
            raise e

    def _read_delegated_channel_list(self, channel_list):
        try:
            self.lock_interfaces()
            data = self.read_delegated_channel_list(channel_list)
            self.unlock_interfaces()
            return data
        except Exception as e:
            self.unlock_interfaces()
            raise e

    def read_delegated_channel_list(self, channel_list):
        # OVERLOAD THIS FUNCTION
        # takes a list of channels
        # returns a dictionary of read data by channel name
        """Read a batch of channels and return their values as an ordered dict.

        Instrument subclasses override this to combine multiple register
        reads into fewer bus transactions.  The default reads each channel
        individually.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write')
        True

        Args:
            channel_list: Iterable of ``channel`` objects to read.

        Returns:
            A ``results_ord_dict`` mapping channel names to their read values.
        """
        results = results_ord_dict()
        for channel in channel_list:
            results[channel.get_name()] = channel.read_without_delegator()
        return results


def retfirst(t):
    """Return the first element of a tuple (used as a sort key).

    Arranges elements according to the specified ordering criterion.

    >>> from PyICe.lab_core import retfirst
    >>> retfirst([10, 20, 30])
    10

    Args:
        t: Tuple whose first element is the sort key.

    Returns:
        The first element of *t*.
    """
    return (t[0])


class channel(delegator):
    """The base channel object.

    It can be read and/or written. Attributes can also be stored in it.
    For example channel number in a multi channel instrument

    >>> from PyICe.lab_core import channel
    >>> ch = channel(name="vout", write_function=lambda v: v)
    >>> _ = ch.write(3.3)
    >>> ch.read()
    3.3
    >>> _ = ch.set_description("Output voltage")
    >>> ch.get_description()
    'Output voltage'

    """
    def __init__(self, name, read_function=None, write_function=None):
        """Initialize a channel with a name and optional read or write function.

        A channel is the fundamental abstraction in PyICe that
        bridges software and lab hardware.  Each channel wraps
        exactly one I/O direction — either a *read_function* that
        queries the instrument or a *write_function* that programs
        it.  Supplying neither creates a "dummy" channel whose
        value lives only in software (useful for constants, flags,
        or computed quantities).  Write-access, value caching,
        callbacks, limits, and display formatting are all set up
        here so that every subsequent ``read()`` / ``write()``
        call goes through uniform guard-rails.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'get_name')
        True

        Args:
            name: Channel name (must match [_A-Za-z][_a-zA-Z0-9]*).
            read_function: Callable that returns the channel value, or None.
            write_function: Callable that accepts a value to write, or None.

        Raises:
            Exception: If both read_function and write_function are provided.
        """
        delegator.__init__(self)
        self.set_name(name)
        if read_function is not None and write_function is not None:
            raise Exception(
                'There may only be a single read OR write function')
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
        self._write_history = collections.deque([], maxlen=10)
        self._set_type_affinity('NUMERIC')
        if write_function is not None:
            self.set_write_access(True)  # write channel
        elif read_function is not None:
            self.set_write_access(False)  # read channel
        else:
            self.set_write_access(True)  # dummy channels
        self.set_description("No Description")
        self.set_display_format_str()

    def __str__(self):
        """Return string representation.

        Provides a human-friendly identifier when printing or
        logging channel objects so that debug output is immediately
        recognisable without inspecting internal attributes.

        >>> from PyICe.lab_core import channel
        >>> str(channel('vdd'))
        'channel Object: vdd'

        Returns:
            String representation.
        """
        return "channel Object: {}".format(self.get_name())

    def get_name(self):
        """Return channel name.

        The name uniquely identifies a channel within a master and
        is used as the dictionary key in read results, SQLite
        column headers, and GUI labels.  It is validated at
        creation time to be a legal Python / SQL identifier.

        >>> from PyICe.lab_core import channel
        >>> channel('iout').get_name()
        'iout'

        Returns:
            The current name.
        """
        return self.name

    def set_name(self, name):
        """Rename channel.
        Updates the name in the object's internal state.

        Updates the name in the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='my_chan')
        >>> ch.set_name('new_name').get_name()
        'new_name'
        >>> ch.set_name('123bad')
        Traceback (most recent call last):
        ...
        PyICe.lab_core.ChannelNameException: Bad Channel Name "123bad"

        Args:
            name: Name identifier.

        Returns:
            The set name result.

        Raises:
            ChannelNameException: If the channel name is invalid or duplicated.
        """
        name = str(name)
        if not re.match("[_A-Za-z][_a-zA-Z0-9]*$", name):
            raise ChannelNameException('Bad Channel Name "{}"'.format(name))
        self.name = name
        return self

    def _set_type_affinity(self, type):
        self._type_affinity = type

    def get_type_affinity(self):
        """Return the type affinity.

        The type affinity (e.g. ``'NUMERIC'``, ``'TEXT'``,
        ``'INTEGER'``) guides SQLite column typing when data is
        logged by the logger.  It is set automatically by
        subclasses such as ``integer_channel`` and can usually be
        ignored for basic channels.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="v")
        >>> ch.get_type_affinity()
        'NUMERIC'

        Returns:
            The current type affinity.
        """
        return self._type_affinity

    def get_size(self):
        """Return the current size.
        Returns the stored size value from the object's internal state.
        Returns the stored size from the object's internal state.

        Returns the stored size from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='my_chan')
        >>> ch.get_size() is None
        True

        Returns:
            The current size.
        """
        return None

    def set_write_delay(self, delay):
        """Sets the automatic delay in seconds after channel write.

        Many instruments need settling time after being programmed
        (e.g. a power supply ramping to a new voltage or a
        temperature chamber stabilising).  This method inserts a
        fixed pause at the end of every ``write()`` call so that
        subsequent reads return valid, settled data.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'set_write_delay')
        True

        Args:
            delay: Delay time in seconds.

        Returns:
            The set write delay result.
        """
        self._write_delay = delay
        self.set_attribute("write_delay", self._write_delay)
        return self

    def get_write_delay(self):
        """Return automatic delay after channel write.

        Returns the delay in seconds that is applied after every
        ``write()`` call on this channel, as configured by
        ``set_write_delay()``.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='clk')
        >>> ch.set_write_delay(0.1).get_write_delay()
        0.1

        Returns:
            The current write delay.
        """
        return self._write_delay

    def get_description(self):
        """Return channel description string.

        The description is a free-form string that documents what
        the channel represents (e.g. "Output voltage at load").
        It is used by the GUI and data loggers to label columns
        and controls for operators who may not know the channel
        name.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='vout')
        >>> ch.set_description('Output voltage').get_description()
        'Output voltage'

        Returns:
            The current description.
        """
        return self._description

    def set_description(self, description):
        """Sets the channel description. argument is string.
        The description string appears in GUI tooltips and log headers,
        helping users identify what physical quantity or signal the channel
        represents.
        Updates the description in the object's internal state.

        Updates the description in the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='vout')
        >>> ch.set_description('Output voltage').get_description()
        'Output voltage'

        Args:
            description: Description string.

        Returns:
            The set description result.
        """
        self._description = description
        return self

    def read(self):
        # setting delegate to false is reserved for the delegator and should
        # never be used otherwise
        """Read and return the current channel value.

        This is the primary way to retrieve data from a channel.
        It delegates to the channel's ``_read`` function (or
        returns the cached value for write-only channels).  When
        the channel belongs to a delegator — for example an
        instrument that reads many channels in a single bus
        transaction — the delegator's batched read is invoked
        instead, improving bus efficiency.  Interface locks are
        held for the duration to ensure thread safety.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write')
        True

        Returns:
            The value read from the device or channel.

        Raises:
            ChannelAccessException: If the channel cannot be accessed in this mode.
            Exception: If an unexpected error occurs.
        """
        if not self.is_readable():
            raise ChannelAccessException(
                f'Read a non-readable channel:{self.name}')
        try:
            self.lock_interfaces()
            data = self.resolve_delegator()._read_delegated_channel_list([self])[
                self.name]
            debug_logging.debug("Read %s from %s", data, self.name)
            self.unlock_interfaces()
            return data
        except Exception as e:
            self.unlock_interfaces()
            raise e

    def read_without_delegator(self, force_data=False, data=None, **kwargs):
        # do not use this function unless you are the delegator
        """Return read without delegator result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("rwd", write_function=lambda v: v)
        >>> _ = ch.write(7)
        >>> ch.read_without_delegator()
        7
        >>> ch.read_without_delegator(force_data=True, data=99)
        99

        Args:
            **kwargs: Additional keyword arguments.
            data: Data to write.
            force_data: Force data to use.

        Returns:
            The value read from the device or channel.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self.lock_interfaces()
        if force_data:
            result = data
            debug_logging.debug(
                "Channel %s read %s from external source.",
                self.get_name(),
                result)
        elif self._read is None:
            result = self._value
            debug_logging.debug(
                "Channel %s read %s cached from last write.",
                self.get_name(),
                result)
        else:
            try:
                result = self._read(**kwargs)
                debug_logging.debug(
                    "Channel %s read %s from _read method",
                    self.get_name(),
                    result)
            except Exception as e:
                debug_logging.error(
                    "Read error in channel {}".format(
                        self.name))
                debug_logging.error(traceback.format_exc())
                self.unlock_interfaces()
                raise e
        if self._read is not None:
            # cache all but write-only channel results for eg, hysteresis
            # calculation, change_callbacks.
            self._set_value(result)
        for callback in self._read_callbacks:
            debug_logging.debug(
                "Channel %s running read callback %s.",
                self.get_name(),
                callback)
            callback(self, result)
        if self.is_changed():
            for callback in self._change_callbacks:
                debug_logging.debug(
                    "Channel %s running change callback %s from channel read.",
                    self.get_name(),
                    callback)
                callback(self, result)
        self.unlock_interfaces()
        return result

    def write(self, value):
        """Write a value to the channel.
        Validates the value against min/max write limits and the write-access
        flag, then delegates to the instrument's hardware write callback. Any
        registered write callbacks are invoked after the write completes.


        Writes data to the underlying target.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write')
        True

        Args:
            value: Value to set.

        Returns:
            True if the write was acknowledged, False otherwise.

        Raises:
            ChannelAccessException: If the channel cannot be accessed in this mode.
            ChannelValueException: If the value is outside the channel\'s valid range.
            Exception: If an unexpected error occurs.
        """
        if not self.is_writeable():
            raise ChannelAccessException('Wrote a non-writeable channel')
        self.lock_interfaces()
        if value is not None:
            if self._write_min is not None and value < self._write_min:
                self.unlock_interfaces()
                raise ChannelValueException(
                    'Cannot write {} to {}. Minimum is {}.'.format(
                        self.name, value, self._write_min))
            if self._write_max is not None and value > self._write_max:
                self.unlock_interfaces()
                raise ChannelValueException(
                    'Cannot write {} to {}. Maximum is {}.'.format(
                        self.name, value, self._write_max))
            if self._write_min_warning is not None and value < self._write_min_warning:
                print(
                    '\n\n*** Warning, value {} below minimum setting of {}. Minimum is {}.\n\n'.format(
                        self.name, value, self._write_min_warning))
            if self._write_max_warning is not None and value > self._write_max_warning:
                print(
                    '\n\n*** Warning, value {} exceeds maximum setting of {}. Maximum is {}.\n\n'.format(
                        self.name, value, self._write_max_warning))
            if self._write_resolution is not None:
                r_val = round(value, self._write_resolution)
                debug_logging.debug(
                    "Channel %s rounding %f to %f.",
                    self.get_name(),
                    value,
                    r_val)
                value = r_val
        if self._write is not None:
            try:
                self._write(value)
            except Exception as e:
                debug_logging.error(
                    "Write error in channel {}".format(
                        self.name))
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
            debug_logging.debug(
                "Channel %s running write callback %s.",
                self.get_name(),
                callback)
            callback(self, value)
        if self.is_changed():
            for callback in self._change_callbacks:
                debug_logging.debug(
                    "Channel %s running change callback %s from channel write.",
                    self.get_name(),
                    callback)
                callback(self, value)
        self.unlock_interfaces()
        return value

    def write_confirm(self, value):
        """Read back value after writing to make sure it "took".

        This is only useful for register-type channels that model remote memory.
        Basic writable channels pass this check trivially.
        returns value
        raises ChannelValueException


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write_confirm')
        True

        Args:
            value: Value to set.

        Returns:
            True if the write was acknowledged, False otherwise.

        Raises:
            ChannelValueException: If the value is outside the channel\'s valid range.
        """
        v_w = self.write(value)
        v_r = self.read()
        try:
            # Only register channels do special access
            v_w = self.compute_expect_readback_data(value)
        except AttributeError:
            if v_w != v_r:
                raise ChannelValueException(
                    f'Failed to set channel {self.get_name()} to value {v_w}. Read back {v_r}.')
        else:
            if v_w is None and value is not None:
                pass
            elif v_w != v_r:
                raise ChannelValueException(
                    f'Failed to write channel {self.get_name()} value {value}. Read back {v_r}.')
        return v_w

    def add_preset(self, preset_value, preset_description=None):
        """Base channels only have unnamed presets (not enumerations).
        Presets are named stored values that can be applied to writeable
        channels in a single call via ``channel_group.write_preset()``. This
        is useful for quickly switching between known operating conditions.
        Creates and registers a new preset.

        Appends a new preset entry to the object's internal collection.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_preset')
        True

        Args:
            preset_description: Human-readable description of the preset.
            preset_value: Value to associate with the preset.

        Raises:
            ChannelAccessException: If the channel cannot be accessed in this mode.
            ChannelException: If the channel operation is invalid.
        """
        if not self.is_writeable():
            raise ChannelAccessException(
                'Basic channel presets are write-only.')
        if preset_value in list(self._presets.values()):
            raise ChannelException(
                'Duplicated preset: {}.'.format(preset_value))
        self._presets[str(preset_value)] = preset_value
        self._preset_descriptions[str(preset_value)] = preset_description

    def get_presets(self):
        """Returns a list of preset names.
        Returns the stored presets value from the object's internal state.
        Returns the stored presets from the object's internal state.

        Returns the stored presets from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_preset')
        True

        Returns:
            The current presets.
        """
        return sorted(list(self._presets.keys()), key=lambda s: str(s).upper())

    def get_presets_dict(self):
        """Returns a dictionary of preset names and value.
        Returns the stored presets dict value from the object's internal
        state.
        Returns the stored presets dict from the object's internal state.

        Returns the stored presets dict from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_preset')
        True

        Returns:
            The current presets dict.
        """
        return results_ord_dict(self._presets)

    def get_preset_description(self, preset_name):
        """Returns description associated with preset_name.
        Returns the stored preset description value from the object's internal
        state.
        Returns the stored preset description from the object's internal
        state.

        Returns the stored preset description from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_preset')
        True

        Args:
            preset_name: Name of the preset.

        Returns:
            The current preset description.
        """
        return self._preset_descriptions[preset_name]

    def has_preset_descriptions(self):
        """Returns boolean value of whether any presets have a description.
        Returns a boolean reflecting the object's current state.

        Returns a boolean reflecting the object's current state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_preset')
        True

        Returns:
            True if the preset descriptions condition is met, False otherwise.
        """
        return set(self._preset_descriptions.values()) != set([None])

    def get_write_history(self):
        """Return the write history.
        Returns the stored write history value from the object's internal
        state.
        Returns the stored write history from the object's internal state.


        Returns the stored write history from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write')
        True

        Returns:
            The current write history.
        """
        return list(self._write_history)

    def delay(self, dly_time):
        """Delay method. Broken out of write method so that it can be sub-classed if necessary.

        Introduces a timing delay required by the hardware or protocol.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='ch')
        >>> ch.delay(0)  # returns None

        Args:
            dly_time: Dly time to use.
        """
        if dly_time > 5:
            egg_timer(dly_time)
        else:
            time.sleep(dly_time)

    def write_unformatted(self, value):
        """Bypass unformatting stub. Only useful for integer and register channels. intended for use by GUI.

        Writes data to the underlying target.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'write_unformatted')
        True

        Args:
            value: Value to set.
        """
        self.write(value)

    def _set_value(self, value):
        """Private method to set channel cached value without actualy _write call or any checking for writability, limits, etc.
        Internal implementation detail; see the public API for usage.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "_set_value")
        True

        42

        Args:
            value: Value to set.

        Returns:
            The set value result.
        """
        self._previous_value = self._value
        self._value = value
        try:
            changed = (self._value != self._previous_value)
        except ValueError:
            # if the before and after values aren't even sensibly comparable,
            # they're certainly not the same. Ex Numpy Arrays of dissimilar
            # length.
            changed = True
        try:
            if changed:
                self._change_detected = False
        except ValueError:
            # We don't really know what happened but we're assuming it is a
            # numpy.array. Needs revisiting.
            if changed.all():
                self._change_detected = False
        return value

    def is_changed(self):
        """Returns boolean status of whether channel value is different from previously read/written value (once per change).
        Returns a boolean reflecting the object's current state.


        Returns a boolean reflecting the object's current state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="v")
        >>> ch._set_value(1.0)
        1.0
        >>> ch.is_changed()
        True
        >>> ch.is_changed()  # one-shot: second call returns False
        False
        >>> ch._set_value(2.0)
        2.0
        >>> ch.is_changed()
        True

        Returns:
            True if the changed condition is met, False otherwise.
        """
        try:
            changed = (self.cached_value != self.previous_cached_value)
        except ValueError:
            # if the before and after values aren't even sensibly comparable,
            # they're certainly not the same. Ex Numpy Arrays of dissimilar
            # length.
            changed = True
        try:
            if changed:
                if not self._change_detected:
                    self._change_detected = True
                    return True
        except ValueError:
            if changed.all():
                # We don't really know what happened but we're assuming it is a
                # numpy.array. Needs revisiting.
                if not self._change_detected:
                    self._change_detected = True
                    return True
        return False

    def set_attribute(self, attribute_name, value):
        """Set attribute_name to value.

        value can be retrived later with get_attribute(attribute_name)

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='temp')
        >>> ch.set_attribute('units', 'degC').get_attribute('units')
        'degC'

        Args:
            attribute_name: Attribute name to use.
            value: Value to set.

        Returns:
            The set attribute result.
        """
        self._attributes[attribute_name] = value
        return self

    def get_attribute(self, attribute_name):
        """Retrieve value previously set with set_attribute(attribute_name, value).
        Channel attributes are arbitrary key-value metadata attached to a
        channel, used for categorization, filtering, and test-plan
        traceability.
        Returns the stored attribute value from the object's internal state.
        Returns the stored attribute from the object's internal state.


        Returns the stored attribute from the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="v")
        >>> _ = ch.set_attribute("units", "volts")
        >>> ch.get_attribute("units")
        'volts'

        Args:
            attribute_name: Attribute name to use.

        Returns:
            The current attribute.

        Raises:
            ChannelAttributeException: If the operation fails.
        """
        if attribute_name not in list(self._attributes.keys()):
            raise ChannelAttributeException
        return self._attributes[attribute_name]

    def get_attributes(self):
        """Return dictionary of all channel attributes previously set with set_attribute(attribute_name, value).
        Returns the stored attributes value from the object's internal state.
        Returns the stored attributes from the object's internal state.

        Returns the stored attributes from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='vin')
        >>> _ = ch.set_attribute('units', 'V')
        >>> ch.get_attributes()['units']
        'V'

        Returns:
            The current attributes.
        """
        return results_ord_dict(
            sorted(list(self._attributes.items()), key=lambda t: t[0]))

    def set_category(self, category):
        """Each channel may be a member of a single category for sorting purposes. category argument is usually a string.
        Categories group related channels for selective logging, GUI
        filtering, and batch operations on subsets of the channel population.
        Updates the category in the object's internal state.

        Updates the category in the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='vout')
        >>> ch.set_category('power').get_category()
        'power'
        >>> ch.set_category(123)
        Traceback (most recent call last):
        ...
        TypeError: Category must be a string


        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="iout")
        >>> ch.set_category("current").get_category()
        'current'

        Args:
            category: Category label for grouping or classification.

        Returns:
            The set category result.

        Raises:
            TypeError: If an argument has an incompatible type.
        """
        if not isinstance(category, str):
            raise TypeError("Category must be a string")
        self._category = category
        return self

    def get_category(self):
        """Returns category membership.  should be a string.
        Returns the channel's category for use in filtering and grouping
        operations.
        Returns the stored category value from the object's internal state.
        Returns the stored category from the object's internal state.


        Returns the stored category from the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="v")
        >>> _ = ch.set_category("power")
        >>> ch.get_category()
        'power'

        Returns:
            The current category.
        """
        return self._category

    def add_tag(self, tag):
        """Each channel may receive several tags for sorting purposes. The tag is usually a string.

        Appends a new tag entry to the object's internal collection.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("tagged")
        >>> _ = ch.add_tag("my_tag")
        >>> "my_tag" in ch.get_tags()
        True

        Args:
            tag: Tag to use.
        """
        self._tags.append(tag)

    def add_tags(self, tag_list):
        """Each channel may receive several tags for sorting purposes. This function adds a list of tags. The tags are usually strings.

        Appends a new tags entry to the object's internal collection.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("multi_tag")
        >>> _ = ch.add_tags(["t1", "t2"])
        >>> "t1" in ch.get_tags() and "t2" in ch.get_tags()
        True

        Args:
            tag_list: Tag list to use.
        """
        for tag in tag_list:
            self._tags.append(tag)

    def get_tags(self, include_category=True):
        """Returns the list of tags for this channel.  If include_category is True the list will also include the category.
        Returns the stored tags value from the object's internal state.
        Returns the stored tags from the object's internal state.

        Returns the stored tags from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("gt")
        >>> _ = ch.add_tag("voltage")
        >>> "voltage" in ch.get_tags()
        True

        Args:
            include_category: Include category to use.

        Returns:
            The current tags.
        """
        return self._tags + [self._category] if include_category else []

    def is_readable(self):
        """Return register readability boolean.
        Returns a boolean reflecting the object's current state.


        Returns a boolean reflecting the object's current state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="wo", write_function=lambda v: None)
        >>> ch.is_readable()
        True

        Returns:
            True if the readable condition is met, False otherwise.
        """
        return self._readable

    def set_read_access(self, readable=True):
        """Set or unset register read access.
        Updates the read access in the object's internal state.

        Updates the read access in the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("ra")
        >>> ch.is_readable()
        True
        >>> _ = ch.set_read_access(False)
        >>> ch.is_readable()
        False

        Args:
            readable: Readable to use.

        Returns:
            The set read access result.
        """
        self._readable = readable
        self.set_attribute("readable", readable)
        return self

    def is_writeable(self):
        """Return register writability boolean.
        Returns a boolean reflecting the object's current state.


        Returns a boolean reflecting the object's current state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="ro", read_function=lambda: 0)
        >>> ch.is_writeable()
        False
        >>> ch2 = channel(name="rw", write_function=lambda v: None)
        >>> ch2.is_writeable()
        True

        Returns:
            True if the writeable condition is met, False otherwise.
        """
        return self._writeable

    def set_write_access(self, writeable=True):
        """Set or unset register write access.
        Controls whether the channel accepts write operations. Read-only
        channels (the default) raise an exception on write attempts,
        protecting hardware from accidental stimulus changes during
        measurement sweeps.
        Updates the write access in the object's internal state.


        Updates the write access in the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="ch", write_function=lambda v: None)
        >>> ch.is_writeable()
        True
        >>> _ = ch.set_write_access(False)
        >>> ch.is_writeable()
        False

        Args:
            writeable: Writeable to use.

        Returns:
            The set write access result.
        """
        self._writeable = writeable
        self.set_attribute("writeable", writeable)
        return self

    def set_write_resolution(self, decimal_digits=None):
        """Set automatic rounding to fixed number of decimal digits, appropriate to the instrument being controlled.

        for instance, it probably doesn't make much sense to set a power supply to much better than 1mV (3) resolution
        a frequency generator might not have better  than 1ns (9) or 100ps (10) digit resolution.
        One frequent cause of excessive apparent resolution is scaling numbers by multiplication/division, log-stepping, or other operations likely to create unrepresentable numbers.
        There are two known likely problems with excessive resolution:
        1) It's possible to choke the input parsee of test equipment if it has limited input buffer size for the command
        2) Recalling forced values from a SQLite database can be problematic. The answer returned from a get_distict() query can't be fed back into a WHERE clause to return the same data.
        Something gets truncated inconsistently either in the SQLIte C library itself or in the SQLite Python bindings.
        Avoiding getting close to machine epsilon (roughly 15 significant decimal digits for double-precision float) robustly addresses the problem.
        This decimal treatment might not be appropraite for all use cases. The same effect could be achieved with a more generalized function call if necessary (TBD/TODO).


        >>> from PyICe.lab_core import channel
        >>> ch = channel("wr", write_function=lambda v: v)
        >>> _ = ch.set_write_resolution(3)
        >>> ch._write_resolution
        3

        Args:
            decimal_digits: Decimal digits to use.
        """
        assert isinstance(
            decimal_digits, (type(None), int)), f'decimal_digits argument must be None or Int type. Received: {decimal_digits}, {type(decimal_digits)}.'
        self._write_resolution = decimal_digits

    def set_max_write_limit(self, max):
        """Set channel's maximum writable value. None disables limit.
        Enforces an upper bound on values written to the channel. Any write
        attempt exceeding this limit raises a ``ChannelValueException``,
        protecting hardware from over-voltage or over-current damage.
        Updates the max write limit in the object's internal state.


        Updates the max write limit in the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'set_max_write_limit')
        True

        Args:
            max: Maximum value of the range.

        Returns:
            The set max write limit result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if max is None:
            self._write_max = None
        else:
            try:
                self._write_max = float(max)
                self.set_attribute("write_max", self._write_max)
            except BaseException:
                raise Exception(
                    "Value for a channel's maximum write must be a number")
        return self

    def set_min_write_limit(self, min):
        """Set channel's minimum writable value. None disables limit.
        Enforces a lower bound on values written to the channel. Any write
        attempt below this limit raises a ``ChannelValueException``,
        protecting hardware from under-voltage or negative-current conditions.
        Updates the min write limit in the object's internal state.


        Updates the min write limit in the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'set_min_write_limit')
        True

        Args:
            min: Minimum value of the range.

        Returns:
            The set min write limit result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if min is None:
            self._write_min = None
        else:
            try:
                self._write_min = float(min)
                self.set_attribute("write_min", self._write_min)
            except BaseException:
                raise Exception(
                    "Value for a channel's minimum write must be a number")
        return self

    def get_max_write_limit(self):
        """Return max writable channel value.
        Returns the configured upper bound so callers can check the allowed
        range before attempting a write, avoiding exception handling.
        Returns the stored max write limit value from the object's internal
        state.
        Returns the stored max write limit from the object's internal state.

        Returns the stored max write limit from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "get_max_write_limit")
        True

        10

        Returns:
            The current max write limit.
        """
        return self._write_max

    def get_min_write_limit(self, formatted=False):
        """Return min writable channel value.
        Returns the configured lower bound so callers can check the allowed
        range before attempting a write, avoiding exception handling.
        Returns the stored min write limit value from the object's internal
        state.
        Returns the stored min write limit from the object's internal state.

        Returns the stored min write limit from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "get_min_write_limit")
        True

        -5

        Args:
            formatted: Formatted to use.

        Returns:
            The current min write limit.
        """
        return self._write_min

    def set_max_write_warning(self, max):
        """Set channel's maximum writable warning value. None disables limit.
        Updates the max write warning in the object's internal state.

        Updates the max write warning in the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "set_max_write_warning")
        True

        100

        Args:
            max: Maximum value of the range.

        Returns:
            The set max write warning result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if max is None:
            self._write_max_warning = None
        else:
            try:
                self._write_max_warning = float(max)
                self.set_attribute(
                    "_write_max_warning",
                    self._write_max_warning)
            except BaseException:
                raise Exception(
                    "Value for a channel's maximum warning must be a number")
        return self

    def set_min_write_warning(self, min):
        """Set channel's minimum writable value warning. None disables limit.
        Updates the min write warning in the object's internal state.

        Updates the min write warning in the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "set_min_write_warning")
        True

        -100

        Args:
            min: Minimum value of the range.

        Returns:
            The set min write warning result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if min is None:
            self._write_min_warning = None
        else:
            try:
                self._write_min_warning = float(min)
                self.set_attribute(
                    "_write_min_warning",
                    self._write_min_warning)
            except BaseException:
                raise Exception(
                    "Value for a channel's minimum warning must be a number")
        return self

    def get_max_write_warning(self):
        """Return max warning channel value.
        Returns the stored max write warning value from the object's internal
        state.
        Returns the stored max write warning from the object's internal state.

        Returns the stored max write warning from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "get_max_write_warning")
        True

        50

        Returns:
            The current max write warning.
        """
        return self._write_max_warning

    def get_min_write_warning(self, formatted=False):
        """Return min warngin channel value.
        Returns the stored min write warning value from the object's internal
        state.
        Returns the stored min write warning from the object's internal state.

        Returns the stored min write warning from the object's internal state.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "get_min_write_warning")
        True

        -50

        Args:
            formatted: Formatted to use.

        Returns:
            The current min write warning.
        """
        return self._write_min_warning

    def format_display(self, data):  # pylint: disable=method-hidden
        """Converts data to string according to string formatting rule set by self.set_display_format_str().

        Converts between raw numeric values and human-readable representations.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='vout')
        >>> _ = ch.set_display_format_str('3.2f', suffix=' V')
        >>> ch.format_display(3.3)
        '3.30 V'

        Args:
            data: Data to write.

        Returns:
            Formatted string representation.
        """
        return self._display_format_str.format(data)

    def set_display_format_str(self, fmt_str='', prefix='', suffix=''):
        """Format string to alter how data is displayed.

        example '3.2f', '04X', '#06X', '#18b', '.2%'
        prefix will be displayed immediately before the channel data, example '0x'
        suffix will be displayed immediately after the channel data, example ' A' or ' V'

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name='code')
        >>> _ = ch.set_display_format_str('04X', prefix='0x')
        >>> ch.format_display(255)
        '0x00FF'

        Args:
            fmt_str: Fmt str to use.
            prefix: Name prefix string.
            suffix: String suffix to append.

        Returns:
            Formatted string representation.
        """
        self._display_format_str = '{prefix}{{:{fmt_str}}}{suffix}'.format(
            prefix=prefix, fmt_str=fmt_str, suffix=suffix)
        return self

    def set_display_format_function(self, function):
        """Abandon string formatting and pass data through custom user-supplied function.
        The format function transforms raw numeric readings into
        human-readable strings for display in the GUI and logger output.
        Common uses include unit conversions, fixed-point formatting, and
        enumeration decoding.
        Updates the display format function in the object's internal state.


        Updates the display format function in the object's internal state.

        >>> from PyICe.lab_core import channel
        >>> ch = channel(name="temp")
        >>> _ = ch.set_display_format_function(lambda v: f"{v} C")
        >>> ch.format_display(25.0)
        '25.0 C'

        Args:
            function: Callable to execute.

        Returns:
            Formatted string representation.
        """
        self.format_display = function
        return self

    def add_write_callback(self, write_callback):
        """Adds a write callback.

        This is a function that will be called any time the channel is written.
        The callback function takes two arguments (channel_object, data)


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_write_callback')
        True

        Args:
            write_callback: Write callback to use.

        Returns:
            The add write callback result.
        """
        self._write_callbacks.append(write_callback)
        return self

    def add_read_callback(self, read_callback):
        """Adds a read callback.

        This is a function that will be called any time the channel is read.
        The callback function takes two arguments (channel_object, data)


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'add_read_callback')
        True

        Args:
            read_callback: Read callback to use.

        Returns:
            The add read callback result.
        """
        self._read_callbacks.append(read_callback)
        return self

    def add_change_callback(self, change_callback=None):
        """Adds a change callback.

        This is a function that will be called any time the channel value changes due to a read or write.
        The callback function takes two arguments (channel_object, data).
        If change_callback is unspecified, channel name, value and time will be printed to the terminal each time the channel value changes.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "add_change_callback")
        True

        [2]

        Args:
            change_callback: Change callback to use.

        Returns:
            The add change callback result.
        """
        if change_callback is None:
            change_callback = self.default_print_callback
        self._change_callbacks.append(change_callback)
        return self

    def remove_change_callback(self, change_callback=None):
        """Remove a change callback.
        Removes the specified change callback.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import channel
        >>> ch = channel("rcc", write_function=lambda v: v)
        >>> cb = lambda c, v: None
        >>> _ = ch.add_change_callback(cb)
        >>> len(ch._change_callbacks)
        1
        >>> _ = ch.remove_change_callback(cb)
        >>> len(ch._change_callbacks)
        0

        Args:
            change_callback: Change callback to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if change_callback is None:
            change_callback = self.default_print_callback
        try:
            self._change_callbacks.remove(change_callback)
        except ValueError:
            raise Exception(
                "Failed to remove change callback {} because it was not registered.".format(change_callback))

    @staticmethod
    def default_print_callback(channel, value):
        """Perform default print callback operation.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, "default_print_callback")
        True

        test_dpc changed to 42.

        Args:
            channel: Channel object.
            value: Value to set.
        """
        try:
            preset_str = " ({})".format(channel._presets_reverse[value])
        except AttributeError:
            # non register/integer_channel
            preset_str = ""
        except KeyError:
            # register/integer_channel but unmatched with preset
            preset_str = ""
        except Exception as e:
            debug_logging.error(
                "Unknown problem with change callback for channel: {}".format(
                    channel.get_name()))
            debug_logging.error(e, exc_info=True)
            debug_logging.error("Entering debugger!")
            import pdb
            pdb.set_trace()
            preset_str = ""
        debug_logging.info("{}: {} changed from {} to {}{}"
                           ".".format(datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                      channel.get_name(), channel.previous_cached_value, value, preset_str))
    cached_value = property(lambda self: self._value,
                            doc='Retrieve last read or written channel value')
    previous_cached_value = property(
        lambda self: self._previous_value,
        doc='Retrieve second last read or written channel value')


class ChannelException(Exception):
    """Parent of all channel exceptions. Not used directly.

    >>> from PyICe.lab_core import ChannelException
    >>> raise ChannelException("test error")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelException: test error
    """


class ChannelAccessException(ChannelException):
    """Attempt to write non-writable channel or read non-readable channel.

    >>> from PyICe.lab_core import ChannelAccessException
    >>> raise ChannelAccessException("read-only channel")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelAccessException: read-only channel
    """


class ChannelNameException(ChannelException):
    """Attempt to create invalid channel name.

    >>> from PyICe.lab_core import ChannelNameException
    >>> raise ChannelNameException("invalid name")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelNameException: invalid name
    """


class ChannelAttributeException(ChannelException):
    """Attempt to read non-existent channel attribute.

    >>> from PyICe.lab_core import ChannelAttributeException
    >>> raise ChannelAttributeException("missing attribute")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelAttributeException: missing attribute
    """


class ChannelValueException(ChannelException):
    """Attempt to write a channel beyond min or max limits.

    >>> from PyICe.lab_core import ChannelValueException
    >>> raise ChannelValueException("value out of range")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelValueException: value out of range
    """


class IntegerChannelValueException(ChannelException):
    """Attempt to write an integer channel to a non-integer value.

    >>> from PyICe.lab_core import IntegerChannelValueException
    >>> raise IntegerChannelValueException("non-integer value")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.IntegerChannelValueException: non-integer value
    """


class ChannelReadException(ChannelException):
    """Out-of-band return value to signal that channel read failed. Should only be used to indicate partial failures within delegated reads. Not typically raised, just instantiated and returned.

    >>> from PyICe.lab_core import ChannelReadException
    >>> raise ChannelReadException("read failed")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.ChannelReadException: read failed
    """

    def __eq__(self, other):
        """Check equality.
        Enables equality comparison with ``==``.

        Supports equality comparison with the ``==`` operator.


    >>> from PyICe.lab_core import IntegerChannelValueException
    >>> raise IntegerChannelValueException("non-integer value")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.IntegerChannelValueException: non-integer value

        Args:
            other: Second operand for the operation.

        Returns:
            True if the comparison holds, False otherwise.
        """
        if isinstance(other, ChannelReadException):
            return self.args == other.args
        else:
            return False

    def __ne__(self, other):
        """Check inequality.
        Enables inequality comparison with ``!=``.

        Implements the ``__ne__`` protocol for this object.


        >>> from PyICe.lab_core import ChannelReadException
        >>> hasattr(ChannelReadException, "__ne__")
        True

        Args:
            other: Second operand for the operation.

        Returns:
            True if the comparison holds, False otherwise.
        """
        return not self.__eq__(other)


class RemoteChannelGroupException(ChannelException):
    """Connection problem with remote channel group client.

    >>> from PyICe.lab_core import RemoteChannelGroupException
    >>> raise RemoteChannelGroupException("connection lost")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.RemoteChannelGroupException: connection lost
    """


class RegisterFormatException(ChannelException):
    """Attempt to apply non-existent channel format.

    >>> from PyICe.lab_core import RegisterFormatException
    >>> raise RegisterFormatException("unknown format")
    Traceback (most recent call last):
        ...
    PyICe.lab_core.RegisterFormatException: unknown format
    """


class integer_channel(channel):
    """Channel with integer value limitation.

    Adds presets and formats but retains channel class's read/write restrictions.

    >>> from PyICe.lab_core import integer_channel
    >>> ic = integer_channel(name='dac_code', size=8, write_function=lambda v: v)
    >>> ic.get_size()
    8
    >>> ic.get_min_write_limit()
    0
    >>> ic.get_max_write_limit()
    255
    >>> ic.format(0xAB, 'hex', use_presets=False)
    '0xAB'
    >>> ic.format(0b1100, 'bin', use_presets=False)
    '0b00001100'
    >>> ic.unformat('0xFF', 'hex', use_presets=False)
    255
    """
    def __init__(self, name, size, read_function=None, write_function=None):
        """Initialize an integer channel with a fixed bit width.
        Initializes 7 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 7 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("reg", size=8)
        >>> ic.get_size()
        8
        >>> ic.get_name()
        'reg'

        Args:
            name: Channel name.
            size: Bit width of the integer value.
            read_function: Callable that returns the channel value, or None.
            write_function: Callable that accepts a value to write, or None.
        """
        channel.__init__(
            self,
            name,
            read_function=read_function,
            write_function=write_function)
        assert isinstance(size, numbers.Integral)
        self._size = size
        self.set_attribute("size", size)
        self._formats = results_ord_dict()
        self._presets_reverse = results_ord_dict()
        self._preset_descriptions = results_ord_dict()
        self._format = None
        self._use_presets_read = False
        self._use_presets_write = True
        self._add_default_formats()
        assert self._size >= 1
        self.set_min_write_limit(0)
        self.set_max_write_limit(2**size - 1)
        self.set_attribute("min", 0)
        self.set_attribute("max", 2**size - 1)

    def __str__(self):
        """Return string representation.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, '__str__')
        True

        Returns:
            String representation.
        """
        return "integer_channel Object: {}".format(self.get_name())

    def _add_default_formats(self):
        def check_sign(data):
            """Return check sign result.
            Validates the sign and raises an exception if invalid.

            Evaluates the condition and raises or returns a diagnostic result.


            >>> from PyICe.lab_core import integer_channel
            >>> integer_channel.check_sign(5)
            False
            >>> integer_channel.check_sign(-3)
            True
            >>> integer_channel.check_sign(0)
            False

            Args:
                data: Data to write.

            Returns:
                The check sign result.

            Raises:
                ValueError: If the provided value is out of range or invalid.
            """
            assert isinstance(data, numbers.Number)
            if data < 0:
                raise ValueError('Negative binary/hex values not allowed.')
            return data
        if self._size == 1:
            # single bit default presets
            self._add_preset('True', True, None)
            self._add_preset('False', False, None)
        elif self._size > 1:
            self.add_format('dec', str, int)
            self.add_format(
                'hex',
                lambda data: '0x{{:0{}X}}'.format(
                    (self._size -
                     1) //
                    4 +
                    1).format(
                    check_sign(data)),
                lambda data: int(
                    str(data),
                    16))
            self.add_format(
                'bin', lambda data: '0b{{:0{}b}}'.format(
                    self._size).format(
                    check_sign(data)), lambda data: int(
                    str(data), 2))
            self.add_format('signed dec', str, int, signed=True)
            # self.add_preset('Minimum', self.get_attribute("min")) #this is wrong for two's-comp channels. Not sure how to deal with signed data here since that's handled by formatting...
            # self.add_preset('Maximum', self.get_attribute("max")) #this is
            # wrong for two's-comp channels. Not sure how to deal with signed
            # data here since that's handled by formatting...
        else:
            raise Exception('Bad size: {}'.format(self._size))

    def get_size(self):
        """Return the current size.
        Returns the stored size value from the object's internal state.
        Returns the stored size from the object's internal state.

        Returns the stored size from the object's internal state.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, 'get_size')
        True

        Returns:
            The current size.
        """
        return self._size

    def get_max_write_limit(self, formatted=False):
        """Return max writable channel value. If formatted, return max writeable value in transformed units accorting to set_format(format) active format.
        Returns the stored max write limit value from the object's internal
        state.
        Returns the stored max write limit from the object's internal state.

        Returns the stored max write limit from the object's internal state.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("mxwl", size=8, write_function=lambda v: v)
        >>> ic.get_max_write_limit()
        255

        Args:
            formatted: Formatted to use.

        Returns:
            The current max write limit.
        """
        if formatted:
            return self.format(self._write_max, self._format, use_presets=False)
        else:
            return int(self._write_max)

    def get_min_write_limit(self, formatted=False):
        """Return min writable channel value. If formatted, return min writeable value in transformed units accorting to set_format(format) active format.
        Returns the stored min write limit value from the object's internal
        state.
        Returns the stored min write limit from the object's internal state.

        Returns the stored min write limit from the object's internal state.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("mnwl", size=8, write_function=lambda v: v)
        >>> ic.get_min_write_limit()
        0

        Args:
            formatted: Formatted to use.

        Returns:
            The current min write limit.
        """
        if formatted:
            return self.format(self._write_min, self._format, use_presets=False)
        else:
            return int(self._write_min)

    def add_preset(self, preset_name, preset_value, preset_description=None):
        """Adds a preset named preset_name with value preset_value.
        Adds a new preset to the object's internal collection.

        Appends a new preset entry to the object's internal collection.

        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel(name='mux', size=4, write_function=lambda v: v)
        >>> _ = ic.add_preset('CH_A', 0)
        >>> _ = ic.add_preset('CH_B', 1)
        >>> ic.format(0, 'dec', use_presets=True)
        'CH_A'
        >>> ic.unformat('CH_B', 'dec', use_presets=True)
        1

        Args:
            preset_description: Human-readable description of the preset.
            preset_name: Name of the preset.
            preset_value: Value to associate with the preset.

        Returns:
            The add preset result.
        """
        if self._size == 1 and len(list(self._presets.keys(
        ))) == 2 and 'True' in self._presets and 'False' in self._presets:
            # remove True/False presets if custom presets are added
            self._presets = results_ord_dict()
            self._presets_reverse = results_ord_dict()
        self._add_preset(preset_name, preset_value, preset_description)
        return self

    def _add_preset(self, preset_name, preset_value, preset_description):
        if not isinstance(preset_value, (numbers.Integral, bool, type(None))):
            raise Exception(
                'Preset value {} neither numeric nor boolean'.format(preset_value))
        if preset_name in self._presets:
            raise Exception('Preset name duplicated: {}.'.format(preset_name))
        if preset_value in self._presets_reverse:
            debug_logging.warning('WARNING: Preset value: {} of register: {} ambiguous name lookup:[{}, {}]'
                                  '.'.format(preset_value, self.get_name(), preset_name,
                                             self._presets_reverse[preset_value]))
        self._presets[preset_name] = preset_value
        self._presets_reverse[preset_value] = preset_name
        self._preset_descriptions[preset_name] = preset_description

    def set_format(self, format):
        """Set active transformation format. reads and writes happen in transformed (real) units instead of native integer.

        Set to None to disable formatting.

        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel(name='reg', size=8, write_function=lambda v: v)
        >>> ic.set_format('hex').get_format()
        'hex'
        >>> ic.set_format(None).get_format() is None
        True

        Args:
            format: Format name string.

        Returns:
            Formatted string representation.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if format is not None and format not in self.get_formats():
            raise Exception(
                'Invalid format "{}" for {}'.format(
                    format, self.get_name()))
        self._format = format
        return self

    def get_format(self):
        """Return active format as set by set_format(format).
        Returns the stored format value from the object's internal state.
        Returns the stored format from the object's internal state.

        Returns the stored format from the object's internal state.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("gf", size=8)
        >>> ic.get_format()

        Returns:
            The current format.
        """
        return self._format

    def use_presets_read(self, bool):  # pragma: no cover
        """Enable replacement of integer value with named enum when reading channel.

        Supports the ``integer_channel`` workflow by performing the described operation.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "use_presets_read")
        True

        Args:
            bool: Boolean flag.

        Returns:
            The use presets read result.
        """
        self._use_presets_read = bool
        return self

    def use_presets_write(self, bool):  # pragma: no cover
        """Enable replacement of named enum with integer value when writing channel.

        Supports the ``integer_channel`` workflow by performing the described operation.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "use_presets_write")
        True

        Args:
            bool: Boolean flag.

        Returns:
            The use presets write result.
        """
        self._use_presets_write = bool
        return self

    def using_presets_read(self):  # pragma: no cover
        """Return boolean denoting last setting of use_presets_read().

        Restores the object or hardware to its default state.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("rpr", size=8)
        >>> ic.using_presets_read()
        False

        Returns:
            The using presets read result.
        """
        return self._use_presets_read

    def using_presets_write(self):  # pragma: no cover
        """Return boolean denoting last setting of use_presets_write().

        Restores the object or hardware to its default state.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "using_presets_write")
        True

        Returns:
            The using presets write result.
        """
        return self._use_presets_write

    def add_format(self, format_name, format_function=None, unformat_function=None, signed=False, units='', xypoints=None):  # pragma: no cover
        """Add a format to this register.  Formats convert a raw number into a more meaningful string and vice-versa.

        Formats can be generic hex, bin, etc, or can be more complicated.

        format_name       - string key used to select this format in format() / unformat() calls.
        format_function   - callable(raw_int) -> physical_value, or None to auto-derive from xypoints.
        unformat_function - callable(physical_value) -> raw_int, or None to auto-derive from xypoints.
        signed            - if True, raw integer is interpreted as two's complement before formatting.
        units             - optional unit string appended to formatted values in the GUI.
        xypoints          - list of (raw, physical) calibration pairs.

        Auto piecewise-linear (PWL) mode:
        When format_function and unformat_function are both None and xypoints contains
        two or more calibration points, format/unformat are automatically derived as a
        piecewise-linear function through those points.
        - For N=2 this is a simple slope-intercept (y = m*x + b).
        - For N>2 each consecutive pair of points defines one linear segment.
        - Values outside the calibrated range are extrapolated using the nearest
        endpoint segment.
        Constraints enforced by assertion:
        - x-coordinates (register values) must be strictly unique.
        - y-coordinates (physical values) must be strictly unique and monotonically
        ordered so that the inverse mapping is uniquely defined.

        Note on signed channels: when signed=True the raw integer is converted from two's
        complement before being passed to format_function, so auto-PWL calibration points
        should use the signed integer domain (e.g. -128..127 for an 8-bit signed channel).


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "add_format")
        True

        Args:
            format_function: Format function to use.
            format_name: Name of the format.
            signed: If True, interpret as signed value.
            unformat_function: Unformat function to use.
            units: Unit string.
            xypoints: Xypoints to use.

        Returns:
            The add format result.
        """
        if xypoints is None:
            xypoints = []
        self._formats[format_name] = {}
        if format_function is None and unformat_function is None and len(
                xypoints) >= 2:
            # Auto piecewise-linear (PWL) formatter.
            # Sort calibration points by x (register / raw) value ascending so that
            # segment lookup uses a consistent direction for the forward
            # transform.
            sorted_pts = sorted(xypoints, key=lambda p: p[0])
            x_pts = [p[0] for p in sorted_pts]
            y_pts = [p[1] for p in sorted_pts]
            assert len(x_pts) == len(set(x_pts)), \
                f'ERROR: {self.get_name()} format {format_name}: duplicate x-values — mapping is not invertible.'
            assert len(y_pts) == len(set(y_pts)), \
                f'ERROR: {self.get_name()} format {format_name}: duplicate y-values — physical transform is not unique.'
            y_diffs = [y_pts[i + 1] - y_pts[i] for i in range(len(y_pts) - 1)]
            assert all(d > 0 for d in y_diffs) or all(d < 0 for d in y_diffs), \
                f'ERROR: {self.get_name()} format {format_name}: y-values are not monotonic — inverse would be ambiguous.'

            def _pwl_interp(val, in_pts, out_pts):
                """Piecewise-linear interpolation / extrapolation along N-point sequences.

                Handles both ascending and descending in_pts. Values outside the range
                are extrapolated from the nearest endpoint segment.


                >>> from PyICe.lab_core import integer_channel
                >>> integer_channel._pwl_interp(5, [0, 10], [0, 100])
                50.0

                Args:
                    in_pts: In pts to use.
                    out_pts: Out pts to use.
                    val: Val to use.

                Returns:
                    The pwl interp result.
                """
                n = len(in_pts)
                for i in range(n - 1):
                    lo = min(in_pts[i], in_pts[i + 1])
                    hi = max(in_pts[i], in_pts[i + 1])
                    if lo <= val <= hi:
                        break
                else:
                    # val is outside the calibrated range — extrapolate from the
                    # nearest endpoint segment based on proximity to
                    # end-points.
                    i = 0 if abs(
                        val - in_pts[0]) < abs(val - in_pts[-1]) else n - 2
                dx = in_pts[i + 1] - in_pts[i]
                dy = out_pts[i + 1] - out_pts[i]
                return out_pts[i] + dy * (val - in_pts[i]) / dx

            def format_function(x, xp=x_pts, yp=y_pts):  # pylint: disable=function-redefined
                return _pwl_interp(x, xp, yp)

            def unformat_function(y, xp=x_pts, yp=y_pts):  # pylint: disable=function-redefined
                """Return unformat function result.

                Converts between raw numeric values and human-readable representations.


                >>> from PyICe.lab_core import integer_channel
                >>> hasattr(integer_channel, 'unformat_function')
                True

                Args:
                    xp: X-axis data points array.
                    y: Y-axis value.
                    yp: Y-axis data points array.

                Returns:
                    Formatted string representation.
                """
                return int(round(_pwl_interp(y, yp, xp)))
        if signed:
            self._formats[format_name]['format_function'] = lambda x: format_function(
                self.twosComplementToSigned(x))
            self._formats[format_name]['unformat_function'] = lambda x: self.signedToTwosComplement(
                unformat_function(x))
        else:
            self._formats[format_name]['format_function'] = format_function
            self._formats[format_name]['unformat_function'] = unformat_function
        self._formats[format_name]['units'] = units
        self._formats[format_name]['xypoints'] = xypoints
        self._formats[format_name]['signed'] = signed
        return self

    def remove_format(self, format_name):  # pragma: no cover
        """Remove format_name from dictionary of available formats.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "remove_format")
        True

        Args:
            format_name: Name of the format.
        """
        del self._formats[format_name]

    def get_formats(self):
        """Return a list of format_names associate with this register.

        The format_string elements of the returned list may be passed to the format or unformat methods


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "get_formats")
        True

        []

        Returns:
            The current formats.
        """
        return list(self._formats.keys())

    def format(self, data, format, use_presets):
        """Take in integer data, pass through specified formatting function, and return string/real representation.

        Converts between raw numeric values and human-readable representations.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "format")
        True

        20

        Args:
            data: Data to write.
            format: Format name string.
            use_presets: If True, apply saved preset configurations.

        Returns:
            Formatted string representation.

        Raises:
            RegisterFormatException: If the register format definition is invalid.
        """
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
                raise RegisterFormatException(
                    'Register {} has no format {}'.format(
                        self.name, format))
            return self._formats[format]['format_function'](data)
        return data

    def sql_format(self, format, use_presets):
        """Return SQL legal column selection text for insertion into a query/view.

        Supports the ``integer_channel`` workflow by performing the described operation.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "sql_format")
        True

        Args:
            format: Format name string.
            use_presets: If True, apply saved preset configurations.

        Returns:
            Formatted string representation.
        """
        def _slope_int_str(p1, p2):
            """Return line-defining slope and intercept for a particular piecewise segment between p1 and p2 points.
            Internal implementation detail; see the public API for usage.

            Internal implementation detail; see the public API for usage.


            >>> from PyICe.lab_core import integer_channel
            >>> integer_channel._slope_int_str((0, 0), (10, 100))
            '10.0 * code + 0.0'

            Args:
                p1: First point as an ``(x, y)`` tuple.
                p2: Second point as an ``(x, y)`` tuple.

            Returns:
                The slope int str result.
            """
            x1, y1 = p1
            x2, y2 = p2
            slope = 1.0 * (y2 - y1) / (x2 - x1)
            intercept = y1 - slope * x1
            if intercept == 0:
                intercept_str = ''
            else:
                intercept_str = '{:+3.6E}'.format(intercept)
            return '"{}"*{:3.6E}{}'.format(self.get_name(),
                                           slope, intercept_str)
        if format is not None:
            xypoints = sorted(
                self._formats[format]['xypoints'],
                key=lambda point: point[0])  # ascending in x
            if len(xypoints) < 2:
                return None  # only return presets once in case of default dec/hex/bin formats
            elif len(xypoints) == 2:
                # straight line
                fmt_str = _slope_int_str(xypoints[0], xypoints[1])
            else:
                # multi-segment interpolator. extrapolation from first and last
                # segments
                fmt_str = 'CASE\n'
                for pidx in range(1, len(xypoints) - 1):
                    fmt_str += '    WHEN "{}" < {} THEN {}\n'.format(self.get_name(
                    ), xypoints[pidx][0], _slope_int_str(xypoints[pidx - 1], xypoints[pidx]))
                fmt_str += '    ELSE {}\n'.format(
                    _slope_int_str(xypoints[-2], xypoints[-1]))
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
                sql_txt += "    WHEN {} THEN '{}'\n".format(
                    preset_value_escaped, self._presets_reverse[preset_value])
            if format is not None:
                sql_txt += '    ELSE {}\n'.format(fmt_str)
            else:
                # return raw channel value to prevent NULL result if no
                # presets/formats match
                sql_txt += '    ELSE "{}"\n'.format(self.get_name())
            sql_txt += '  END'
        elif format is not None:
            sql_txt = '  {}'.format(fmt_str)
        else:
            return None
        sql_txt += ' AS {}'.format(self.get_name())  # _fmt\n
        return sql_txt

    def unformat(self, string, format, use_presets):
        """Take in formatted string / real, pass through specified unformatting function, and return integer representation.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "unformat")
        True

        10

        Args:
            format: Format name string.
            string: String data.
            use_presets: If True, apply saved preset configurations.

        Returns:
            Formatted string representation.

        Raises:
            Exception: If an unexpected error occurs.
            IntegerChannelValueException: If the value is not a valid integer for this channel.
            RegisterFormatException: If the register format definition is invalid.
            TypeError: If an argument has an incompatible type.
            e: Re-raised after cleanup.
            e1: Re-raised after cleanup.
        """
        if string is None:
            debug_logging.debug(
                "Channel %s unformat returning None.",
                self.get_name())
            return None
        if use_presets:
            try:
                debug_logging.debug(
                    "Channel %s unformat attempting preset match to %s.",
                    self.get_name(),
                    string)
                return self._presets[string]
            except KeyError:
                pass
        if format is not None:
            if format not in self._formats:
                raise RegisterFormatException(
                    'Register {} has no format {}.'.format(
                        self.name, format))
            try:
                debug_logging.debug(
                    "Channel %s unformat attempting unformat using %s.",
                    self.get_name(),
                    format)
                return self._formats[format]['unformat_function'](string)
            except Exception as e:
                # formats intended for real data will get switched to strings
                # in the GUI. Make an attempt here to fix.
                if isinstance(string, int) or isinstance(
                        string, float) or string is None:
                    raise e
                try:
                    debug_logging.debug(
                        "Channel %s unformat attempting string to int conversion.",
                        self.get_name())
                    formatted_data = int(
                        string, 0)  # automatically select base
                except ValueError:
                    try:
                        debug_logging.debug(
                            "Channel %s unformat attempting string to float conversion.",
                            self.get_name())
                        formatted_data = float(string)
                    except ValueError as e2:
                        print(e2)
                        raise e
                debug_logging.debug(
                    "Channel %s unformat retrying unformat using %s after string to numeric conversion.",
                    self.get_name(),
                    format)
                int_data = self._formats[format]['unformat_function'](
                    formatted_data)
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
            debug_logging.debug(
                "Channel %s attempting string to numeric conversion without assigned format.",
                self.get_name())
            return int(string, 0)
        except ValueError as e1:  # String-type inputs, probably from GUI.
            try:
                # last chance. If data is type float but is a round integer,
                # then let it through.
                if float(string) == int(float(string)):
                    return int(float(string))
            except Exception as e2:
                debug_logging.error(e2, exc_info=True)
                debug_logging.error(
                    "Unknown conversion error. Channel {} data {}".format(
                        self.get_name(), string))
                raise e1
            raise IntegerChannelValueException(
                'Floating point data {} passed to integer channel {} without unformat or preset match. Automatic rounding not allowed outside formats.'.format(
                    string, self.get_name()))
        except TypeError:  # Probably float-type input.
            if isinstance(string, float):
                raise IntegerChannelValueException(
                    'Floating point data {} passed to integer channel {} without unformat or preset match. Automatic rounding not allowed outside formats.'.format(
                        string, self.get_name()))
            else:
                raise  # no idea what happened
        except Exception as e:
            debug_logging.debug(
                "Channel %s unknown conversion error.",
                self.get_name())
            debug_logging.warning("WARNING: Channel: {} write data: {} unknown conversion error of type "
                                  "{}.".format(self.get_name(), string, type(e)))
            raise IntegerChannelValueException(
                "Channel: {} write data: {} (type {}) unknown conversion error of type {}.".format(
                    self.get_name(), string, type(string), type(e)))

    def get_units(self, format):  # pragma: no cover
        """Return real units string for specified format. ex 'A' or 'V'.
        Returns the stored units value from the object's internal state.
        Returns the stored units from the object's internal state.

        Returns the stored units from the object's internal state.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, "get_units")
        True

        Args:
            format: Format name string.

        Returns:
            The current units.
        """
        return self._formats[format]['units']

    def format_read(self, raw_data):
        """Transform from integer to real units according to using_presets_read() and active format.
        Formats the read for display or transmission.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("fr", size=8)
        >>> ic.format_read(42)
        42

        Args:
            raw_data: Raw data to use.

        Returns:
            Formatted string representation.
        """
        if isinstance(raw_data, int):
            if raw_data > self.get_max_write_limit():
                print(
                    "WARNING: Channel {} read data {} exceeds channel size {}.".format(
                        self.get_name(), raw_data, self._size))
            if raw_data < self.get_min_write_limit():
                print(
                    "WARNING: Channel {} read data {} exceeds channel size {}.".format(
                        self.get_name(), raw_data, self._size))
        if self._format or self._use_presets_read:
            fmt_data = self.format(
                raw_data, self._format, self._use_presets_read)
            debug_logging.debug(
                "Channel %s formatted %s to %s",
                self.get_name(),
                raw_data,
                fmt_data)
            return fmt_data
        else:
            debug_logging.debug(
                "Channel %s didn't format %s.",
                self.get_name(),
                raw_data,
            )
            return raw_data

    def format_write(self, value):
        """Transform from real units to integer according to using_presets_write() and active format.

        Converts between raw numeric values and human-readable representations.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("fw", size=8, write_function=lambda v: v)
        >>> ic.format_write(100)
        100

        Args:
            value: Value to set.

        Returns:
            Formatted string representation.
        """
        return self.unformat(value, self._format, self._use_presets_write)  # pylint: disable=not-callable; unformat is defined in this class at line ~1767

    def twosComplementToSigned(self, binary):
        """Transform two's complement formatted binary number to signed integer.  Requires register's size attribute to be set in __init__.

        Transforms the input data into the required output form.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("tcs", size=8)
        >>> ic.twosComplementToSigned(255)
        -1
        >>> ic.twosComplementToSigned(127)
        127

        Args:
            binary: Binary/integer data.

        Returns:
            The twosComplementToSigned result.
        """
        return twosComplementToSigned(binary, self._size)

    def signedToTwosComplement(self, signed):
        """Transform signed integer to two's complement formatted binary number.  Requires register's size attribute to be set in __init__.

        Transforms the input data into the required output form.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("stc", size=8)
        >>> ic.signedToTwosComplement(-1)
        255
        >>> ic.signedToTwosComplement(127)
        127

        Args:
            signed: If True, interpret as signed value.

        Returns:
            The signedToTwosComplement result.
        """
        return signedToTwosComplement(signed, self._size)

    def write(self, value):
        """Write intercept to apply formats/presets before channel write. Coerce to integer and warn about rounding error. Also accepts None.
        Validates the value is within the integer channel's bit range, then
        writes the integer value to the instrument hardware.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("iw", size=8, write_function=lambda v: v)
        >>> ic.write(100)
        100

        Args:
            value: Value to set.

        Returns:
            True if the write was acknowledged, False otherwise.
        """
        if self._size == 1:
            # allow True,False values
            if value is True:
                channel.write(self, True)
                return True
            elif value is False:
                channel.write(self, False)
                return False
        if value is not None:
            raw_data = self.format_write(value)
            int_data = int(round(raw_data))
            if int_data != raw_data:
                debug_logging.warning(
                    "WARNING: Channel: {} write: {} unformatted to: {} and rounded to: {}.".format(
                        self.get_name(), value, raw_data, int_data))
        else:
            int_data = value
        channel.write(self, int_data)
        return int_data

    def write_unformatted(self, value):
        """Bypass unformatting. intended for use by GUI.
        Formats and sends the command to the instrument.
        Sends the ``WARNING:`` SCPI command to the instrument.
        Formats and sends the command to the instrument.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import integer_channel
        >>> hasattr(integer_channel, 'write_unformatted')
        True

        Args:
            value: Value to set.

        Returns:
            Formatted string representation.
        """
        if self._size == 1:
            # allow True,False values
            if value is True:
                channel.write(self, True)
                return True
            elif value is False:
                channel.write(self, False)
                return False
        if value is not None:
            int_data = int(round(value))
            if int_data != value:
                debug_logging.warning("WARNING: Channel: {} write_unformatted: "
                                      "{} rounded to: {}.".format(self.get_name(), value, int_data))
            value = int_data
        channel.write(self, value)
        return value

    def read_without_delegator(self, force_data=False, data=None, **kwargs):  # pragma: no cover
        """Read intercept to apply formats/presets to channel (raw) read.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import integer_channel
        >>> ic = integer_channel("irwd", size=8, write_function=lambda v: v)
        >>> ic.write(42)
        42

        Args:
            **kwargs: Additional keyword arguments.
            data: Data to write.
            force_data: Force data to use.

        Returns:
            The value read from the device or channel.
        """
        return self.format_read(channel.read_without_delegator(
            self, force_data, data, **kwargs))


class register(integer_channel):
    """Integer channel with read/write restriction removed.

    Models remote (volatile) memory. IE, reads must check remote copy rather than use cache like ordinary integer channels.
    This behavior can be modified on a channel-by-channel basis to speed up communication with the enable_cached_read method.

    >>> from PyICe.lab_core import register
    >>> reg = register(name='STATUS', size=8, read_function=lambda: 0)
    >>> reg.get_size()
    8
    >>> reg.is_readable()
    True
    """
    def __init__(self, name, size, read_function=None, write_function=None):
        """If subclass overloads __init__, it should also call this one.
        Stores configuration in ``_write`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_core import register
        >>> register is not None
        True

        Args:
            name: Name identifier.
            read_function: Callable for reading the channel.
            size: Size in bits.
            write_function: Callable for writing the channel.
        """
        # channel doesn't allow both read and write so just do one, then force
        # in the other
        integer_channel.__init__(
            self,
            name=name,
            size=size,
            read_function=read_function)
        self.set_attribute('read_caching', False)
        self.set_attribute('special_access', None)
        if write_function:
            self._write = write_function
            self.set_write_access()

    def __str__(self):
        """Return string representation.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.


        >>> from PyICe.lab_core import register
        >>> hasattr(register, '__str__')
        True

        Returns:
            String representation.
        """
        return "Register Object: {}".format(self.get_name())

    def enable_cached_read(self):
        """Return last written value rather than read remote memory contents. Essentially reverts from register to writable integer_channel.
        Enables the cached read function.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_core import register
        >>> hasattr(register, 'enable_cached_read')
        True

        Raises:
            Exception: If an unexpected error occurs.
        """
        if not self.is_writeable():
            raise Exception(
                "ERROR: Can't set non-writable register to cache reads: {}.".format(self.get_name()))
        self._read = None
        self.set_read_access(True)
        self.set_attribute('read_caching', True)

    def set_special_access(self, access):
        """Following uvm_reg_field convention.

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


        >>> from PyICe.lab_core import register
        >>> hasattr(register, 'set_special_access')
        True

        Args:
            access: Access to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
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
            raise Exception(
                f'Read side effect {access.upper()} special register access unimplemented. Please contact PyICe developers.')

        # special write behavior
        elif access.upper() in ("WC", "WS", "W1T", "W0T", "WOC", "WOS", "W1", "WO1"):
            raise Exception(
                f'Limited write side effect special register access implemented. {access.upper()} not yet implemented. Please contact PyICe developers.')
        elif access.upper() == "W1C":
            self.set_attribute('special_access', 'W1C')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset(
                "clear",
                2**self.get_size() - 1,
                "Write 1 to clear")
        elif access.upper() == "W0C":
            self.set_attribute('special_access', 'W0C')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("clear", 0, "Write 0 to clear")
        elif access.upper() == "W1S":
            self.set_attribute('special_access', 'W1S')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("set", 2**self.get_size() - 1, "Write 1 to set")
        elif access.upper() == "W0S":
            self.set_attribute('special_access', 'W0S')
            self.set_read_access(True)
            self.set_write_access(True)
            self.add_preset("set", 0, "Write 0 to set")

        # special read and write behavior
        elif access.upper in ("WSRC", "WCRS", "W1SRC", "W1CRS", "W0SRC", "W0CRS"):
            raise Exception(
                'Read/write side effect special register access unimplemented. Please contact PyICe developers.')
        # likely typo
        else:
            raise Exception(
                'Unknown register side effect special access.. Please contact PyICe developers.')

    def compute_rmw_writeback_data(self, data):
        """Bitfield level callback to modify writeback data for read-modify-write sub-atomic register access.

        This is useful primarily for bitfields with write side effects implemented.

        Args:
            data: Bitfield readback data, masked and shifted to LSB position.

        Returns:
            Bitfield writeback data. Usually the same as readback data.

        Raises:
            Exception: Unknown value contained in "special_access" channel attribute.

        >>> from PyICe.lab_core import register
        >>> reg = register(name='FLAGS', size=8, read_function=lambda: 0)
        >>> reg.compute_rmw_writeback_data(0xAB)
        171
        >>> w1c = register(name='IRQ', size=8, read_function=lambda: 0)
        >>> w1c.set_special_access('W1C')
        >>> w1c.compute_rmw_writeback_data(0xAB)
        0
        >>> w0c = register(name='STAT', size=8, read_function=lambda: 0)
        >>> w0c.set_special_access('W0C')
        >>> w0c.compute_rmw_writeback_data(0xAB)
        255

        Args:
            data: Data to write.

        Returns:
            The computed result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self.get_attribute('special_access') is None:
            return data
        elif self.get_attribute('special_access') in ('W1C', 'W1S'):
            return 0
        elif self.get_attribute('special_access') in ('W0C', 'W0S'):
            return 2**self.get_size() - 1
        else:
            raise Exception(
                f'Register special access {self.get_attribute("special_access")} improperly implemented. Contact PyICe developers.')

    def compute_expect_readback_data(self, data):
        """Return compute expect readback data result.

        Supports the ``register`` workflow by performing the described operation.


        >>> from PyICe.lab_core import register
        >>> hasattr(register, 'compute_expect_readback_data')
        True

        Args:
            data: Data to write.

        Returns:
            The computed result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self.get_attribute('special_access') is None:
            return self.format_write(data)
        elif self.get_attribute('special_access') in ('W1C',):
            return 0 if data == 1 else None  # unknown
        elif self.get_attribute('special_access') in ('W1S',):
            return 1 if data == 1 else None
        elif self.get_attribute('special_access') in ('W0C',):
            return 0 if data == 0 else None
        elif self.get_attribute('special_access') in ('W0S',):
            return 1 if data == 1 else None
        elif self.get_attribute('special_access').upper() in ("WSRC", "WCRS", "W1SRC", "W1CRS", "W0SRC", "W0CRS"):
            raise Exception(
                'Read/write side effect special register access unimplemented. Please contact PyICe developers.')
        else:
            raise Exception(
                'Unknown register side effect special access.. Please contact PyICe developers.')


class channel_group(object):
    """Collection of channels, optionally organized into sub-groups.

    >>> from PyICe.lab_core import channel_group, channel
    >>> g = channel_group('my_instrument')
    >>> g.get_name()
    'my_instrument'
    >>> ch = channel(name='voltage', read_function=lambda: 3.3)
    >>> g.add(ch).get_name()
    'voltage'
    >>> g.get_all_channel_names()
    ['voltage']
    """
    def __init__(self, name='Unnamed Channel Group'):
        """Initialize a channel group with a name and empty channel/group collections.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import channel_group
        >>> obj = channel_group('grp')
        >>> isinstance(obj, channel_group)
        True

        Args:
            name: Display name for this channel group.
        """
        self.set_name(name)
        # a dictionary of channel objects, keyed by name, contained by this
        # channel_group
        self._channel_dict = results_ord_dict()
        # a list of other groups contained by this object
        self._sub_channel_groups = []
        self._threaded = False
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = []
        debug_logging.debug("Created new channel group: %s", self.get_name())

    def __str__(self):
        """Return a human-readable string identifying this channel group by name.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, '__str__')
        True

        Returns:
            str: String of the form ``"channel_group Object: <name>"``.
        """
        return "channel_group Object: {}".format(self.get_name())

    def __iter__(self):
        """Iterate over all channels in this group, including sub-groups.
        Enables iteration over the object's elements.

        Supports iteration with ``for ... in`` loops.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, '__iter__')
        True

        Yields:
            channel: The next channel object in the group.
        """
        for channel in self.get_all_channels_list():
            yield channel  # this is inconsistent with dictionaries, which yield their keys when iterated!

    def __contains__(self, key):
        """Check whether a channel object exists in this group.
        Enables ``in`` membership testing.

        Supports the ``in`` operator for membership testing.

        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, '__contains__')
        True

        Args:
            key: A channel object to look for among all channels.

        Returns:
            bool: True if the channel is found in this group or its sub-groups.
        """
        return key in self.get_all_channels_list()

    def __getitem__(self, channel_name):
        """Retrieve a channel by name using bracket notation.
        Enables bracket-style indexing (``obj[key]``).


        Supports bracket-style indexing (``obj[key]``) for this container.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, '__getitem__')
        True

        Args:
            channel_name: The registered name of the channel to retrieve.

        Returns:
            channel: The resolved channel object.
        """
        return self.get_channel(channel_name)

    def copy(self):
        """Create a shallow copy of this channel group with a duplicated channel dictionary.

        The copy shares the same channel objects but has an independent
        dictionary, so adding or removing channels from the copy does not
        affect the original.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'copy')
        True

        Returns:
            channel_group: A new channel_group with the same channels.
        """
        copy_self = copy.copy(self)  # Make copy of the channel group object
        # Replace the channel dictionary with an empty one
        copy_self._channel_dict = results_ord_dict()
        # Populate the copy of the dictionary with copies of original channels
        copy_self._channel_dict.update(self._channel_dict)
        # How should _partial_delegation_results, _self_delegation_channels,
        # _sub_channel_groups be handled by this copy routine?
        if isinstance(self, delegator):
            if self.get_delegator() is self:
                copy_self.set_delegator(copy_self)
        return copy_self

    def get_name(self):
        """Return the display name of this channel group.
        Returns the stored name value from the object's internal state.
        Returns the stored name from the object's internal state.

        Returns the stored name from the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> g = channel_group('my_group')
        >>> g.get_name()
        'my_group'

        Returns:
            str: The name string assigned to this group.
        """
        return self._name

    def set_name(self, name):
        """Set the display name of this channel group.
        Updates the name in the object's internal state.

        Updates the name in the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'set_name')
        True

        Args:
            name: The new display name (converted to string).
        """
        self._name = str(name)

    def get_categories(self):
        """Collect all unique category labels from every channel in this group.
        Returns the stored categories value from the object's internal state.
        Returns the stored categories from the object's internal state.

        Returns the stored categories from the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_categories')
        True

        Returns:
            set: A set of category strings across all channels.
        """
        return set([ch.get_category() for ch in self.get_all_channels_list(
            categories=None)])  # TODO return list instead of set?

    def sort(self, deep=True, **kwargs):
        """Sort channels in-place by name (default) or a custom key function.

        When *deep* is True, sub-groups are sorted recursively.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'sort')
        True

        Args:
            deep: If True, recursively sort sub-channel groups as well.
            **kwargs: Keyword arguments forwarded to :func:`sorted`, e.g.
                ``key`` or ``reverse``.  If *key* is not provided, channels
                are sorted alphabetically by name.
        """
        if 'key' not in kwargs:
            # sort by channel name by default
            kwargs['key'] = lambda kv_tuple: kv_tuple[0]
        self._channel_dict = results_ord_dict(
            sorted(list(self._channel_dict.items()), **kwargs))
        if deep:  # should this go deep and sort sub channel groups too?
            for scg in self._sub_channel_groups:
                scg.sort(**kwargs)

    def add(self, channel_or_group):
        """Add a channel or channel group to this group.

        If *channel_or_group* is a :class:`channel`, it is added directly
        to this group.  If it is a :class:`channel_group`, it is added as
        a sub-group whose channels are resolved through the parent but are
        not considered direct members.  An iterable of channels/groups is
        also accepted.


        >>> from PyICe.lab_core import channel_group, channel
        >>> g = channel_group("test")
        >>> ch = channel(name="x", read_function=lambda: 42)
        >>> g.add(ch).get_name()
        'x'
        >>> len(g.get_all_channel_names())
        1

        Args:
            channel_or_group: A channel object, channel_group object, or an
                iterable of such objects to add.

        Returns:
            channel or channel_group or list: The added object(s).

        Raises:
            TypeError: If the argument is not a channel, channel_group, or
                iterable thereof.
        """
        if isinstance(channel_or_group, channel):
            return self._add_channel(channel_or_group)
        elif isinstance(channel_or_group, channel_group):
            return self._add_sub_channel_group(channel_or_group)
        else:
            try:
                iterator = iter(channel_or_group)
            except TypeError as e:
                raise TypeError(
                    '\nAttempted to add something other than a channel or channel_group to a channel_group') from e
            else:
                return [self.add(ch) for ch in iterator]

    def _add_channel(self, channel_object):
        if not isinstance(channel_object, channel):
            err_str = 'Attempted to add a non-channel to a channel_group'
            debug_logging.error(err_str)
            raise Exception(err_str)
        if channel_object.get_name() in list(self._channel_dict.keys()):
            debug_logging.warning(
                "WARNING: Re-defined channel %s",
                channel_object.get_name())
            print(("WARNING: Re-defined channel {}".format(channel_object.get_name())))
        elif channel_object.get_name() in list(self.get_all_channels_dict().keys()):
            err_str = '\nName Conflict: Attempted to create an already named channel {} existing in another subgroup'.format(
                channel_object.get_name())
            debug_logging.error(err_str)
            raise Exception(err_str)
        debug_logging.debug(
            "Added %s to %s",
            channel_object.get_name(),
            self.get_name())
        self._channel_dict[channel_object.get_name()] = channel_object
        return channel_object

    def merge_in_channel_group(self, channel_group_object):
        """Merge all channels from another channel group into this group's top level.

        Unlike :meth:`add`, which nests a sub-group, this method copies each
        channel from *channel_group_object* directly into this group.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'merge_in_channel_group')
        True

        Args:
            channel_group_object: The source channel_group whose channels
                will be individually added to this group.

        Raises:
            Exception: If *channel_group_object* is not a channel_group instance.
        """
        if not isinstance(channel_group_object, channel_group):
            raise Exception(
                '\nAttempted to merge a non-channel_group to a channel_group')
        for channel_object in channel_group_object:
            self._add_channel(channel_object)

    def _add_sub_channel_group(self, channel_group_object):
        """Register a channel group as a sub-group of this group.

        Sub-group channels are resolved when the parent is queried but are
        not direct members of the parent's channel dictionary.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, '_add_sub_channel_group')
        True

        Args:
            channel_group_object: The channel_group to nest as a sub-group.

        Returns:
            channel_group: The added sub-group object.

        Raises:
            Exception: If *channel_group_object* is not a channel_group, or
                if any channel names conflict with existing channels.
        """
        if not isinstance(channel_group_object, channel_group):
            raise Exception('\nAttempted to add a "{}" to a channel_group as a sub group'.format(
                channel_group_object))
        channel_name_conflicts = set(
            self.get_all_channels_dict().keys()) & set(
            channel_group_object.get_all_channels_dict().keys())
        for channel_name_conflict in channel_name_conflicts:
            raise Exception(
                '\nChannel name conflict for "{}"'.format(channel_name_conflict))
        self._sub_channel_groups.append(channel_group_object)
        return channel_group_object

    def get_channel_groups(self):
        """Return a list of sub-channel groups registered under this group.
        Returns the stored channel groups value from the object's internal
        state.
        Returns the stored channel groups from the object's internal state.

        Returns the stored channel groups from the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_channel_groups')
        True

        Returns:
            list: A list of channel_group objects that are direct sub-groups.
        """
        return list(self._sub_channel_groups)

    def read(self, channel_name):
        """Read a single channel by name and return its current value.

        Convenience wrapper around :meth:`read_channel`.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, '__getitem__')
        True

        Args:
            channel_name: The registered name of the channel to read.

        Returns:
            The current value of the named channel.
        """
        return self.read_channel(channel_name)

    def write(self, channel_name, value, confirm=False):
        """Write a value to a named channel.

        Convenience wrapper around :meth:`write_channel`.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'write')
        True

        Args:
            channel_name: The registered name of the channel to write.
            value: The value to write to the channel.
            confirm: If True, perform a write-then-read-back confirmation.

        Returns:
            The result of the write (or write-confirm) operation.
        """
        return self.write_channel(channel_name, value, confirm)

    def read_channel(self, channel_name):
        """Read a single channel by name, resolving through sub-groups if needed.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'read_channel')
        True

        Args:
            channel_name: The registered name of the channel to read.

        Returns:
            The current value of the named channel.

        Raises:
            ChannelAccessException: If the channel name cannot be resolved
                in this group or any of its sub-groups.
        """
        channel = self._resolve_channel(channel_name)
        if channel is None:
            raise ChannelAccessException(
                '\nUnable to read channel "{}", did you create it or is it a typo?'.format(channel_name))
        return self.read_channel_list([channel])[channel_name]

    def read_channels(self, item_list):
        """Read multiple channels specified as objects, names, or groups.

        The *item_list* is first resolved to a flat list of channel objects
        before reading.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'read_channels')
        True

        Args:
            item_list: A list of channel objects, channel name strings, or
                channel_group objects to read.

        Returns:
            results_ord_dict: Ordered dictionary mapping channel names to values.
        """
        channel_list = self.resolve_channel_list(item_list)
        return self.read_channel_list(channel_list)

    def write_channel(self, channel_name, value, confirm=False):
        """Write a value to a channel, optionally confirming via read-back.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'write_channel')
        True

        Args:
            channel_name: The registered name of the channel to write.
            value: The value to write to the channel.
            confirm: If True, write then read back to verify the value.

        Returns:
            The result of the write (or write-confirm) operation.
        """
        if confirm:
            return self.get_channel(channel_name).write_confirm(value)
        else:
            return self.get_channel(channel_name).write(value)

    def write_channels(self, item_list):
        """Write values to multiple channels from a list of (name, value) pairs.

        Writes data to the underlying target.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'write_channels')
        True

        Args:
            item_list: An iterable of ``(channel_name, value)`` tuples to write.

        Returns:
            list: A list of results from each individual write_channel call.
        """
        return [self.write_channel(ch_name, ch_value)
                for (ch_name, ch_value) in item_list]

    def get_channel(self, channel_name):
        """Retrieve a channel object by name, resolving through sub-groups.
        Looks up a channel by name within this group. Raises ``KeyError`` if
        the channel is not found.
        Returns the stored channel from the object's internal state.


        Returns the stored channel from the object's internal state.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, 'get_channel')
        True

        Args:
            channel_name: The registered name of the channel to look up.

        Returns:
            channel: The resolved channel object.

        Raises:
            ChannelAccessException: If the channel name cannot be resolved
                in this group or any of its sub-groups.
        """
        channel = self._resolve_channel(channel_name)
        if channel is None:
            raise ChannelAccessException(
                '\nUnable to get channel "{}", did you create it or is it a typo?'.format(channel_name))
        return channel

    def get_flat_channel_group(self, name=None):
        """Create a new single-level channel group containing all resolvable channels.

        Flattens the hierarchy by merging all channels (including those in
        sub-groups) into one top-level group.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_flat_channel_group')
        True

        Args:
            name: Display name for the new flattened group.  Defaults to
                ``"<original_name>_flattened"``.

        Returns:
            channel_group: A new channel_group containing all channels at one level.
        """
        if name is None:
            name = '{}_flattened'.format(self.get_name())
        new_group = channel_group(name)
        new_group.merge_in_channel_group(self)
        return new_group

    def _resolve_channel(self, channel_name):
        if channel_name in self._channel_dict:
            debug_logging.debug(
                "%s resolved %s to self.",
                self.get_name(),
                channel_name)
            return self._channel_dict[channel_name]
        for sub_channel_group in self._sub_channel_groups:
            channel = sub_channel_group._resolve_channel(channel_name)
            if channel is not None:
                debug_logging.debug(
                    "%s resolved %s to %s.",
                    self.get_name(),
                    channel_name,
                    sub_channel_group.get_name())
                return channel
        return None

    def get_all_channels_dict(self, categories=None):
        # returns a dictionary of all channels by name
        """Return an ordered dictionary of all channels keyed by name.

        Includes channels from sub-groups.  Optionally filters by category.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_all_channels_dict')
        True

        Args:
            categories: An iterable of category strings to include.  If None,
                all channels are returned regardless of category.

        Returns:
            results_ord_dict: Ordered dict mapping channel names to channel objects.
        """
        all_channels = results_ord_dict(self._channel_dict)
        for sub_channel_group in self._sub_channel_groups:
            all_channels.update(sub_channel_group.get_all_channels_dict())
        if categories is not None:
            for k, v in list(all_channels.items()):
                if v.get_category() not in categories:
                    del all_channels[k]
        return all_channels

    def get_all_channel_names(self, categories=None):
        """Return a list of all channel names in this group and its sub-groups.
        Returns the stored all channel names value from the object's internal
        state.
        Returns the stored all channel names from the object's internal state.


        Returns the stored all channel names from the object's internal state.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, 'get_all_channel_names')
        True

        Args:
            categories: An iterable of category strings to filter by.  If None,
                all channel names are returned.

        Returns:
            list: A list of channel name strings.
        """
        return list(self.get_all_channels_dict(categories).keys())

    def get_all_channels_list(self, categories=None):
        """Return a list of all channel objects in this group and its sub-groups.
        Returns the stored all channels list value from the object's internal
        state.
        Returns the stored all channels list from the object's internal state.

        Returns the stored all channels list from the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_all_channels_list')
        True

        Args:
            categories: An iterable of category strings to filter by.  If None,
                all channels are returned.

        Returns:
            list: A list of channel objects.
        """
        return list(self.get_all_channels_dict(categories).values())

    def get_all_channels_set(self, categories=None):
        """Return a set of all channel objects in this group and its sub-groups.
        Returns the stored all channels set value from the object's internal
        state.
        Returns the stored all channels set from the object's internal state.

        Returns the stored all channels set from the object's internal state.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_all_channels_set')
        True

        Args:
            categories: An iterable of category strings to filter by.  If None,
                all channels are returned.

        Returns:
            set: A set of unique channel objects.
        """
        return set(self.get_all_channels_dict(categories).values())

    def read_channel_list(self, channel_list):
        # reads a list of channel objects
        # create lists of threadable and non-threadable channels
        """Read a list of channel objects, dispatching to delegators and optional threading.

        Channels are partitioned by their delegator and read in bulk.
        If threading is enabled via :meth:`start_threads`, eligible channels
        are read concurrently.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'read_channel_list')
        True

        Args:
            channel_list: An iterable of channel objects to read.

        Returns:
            results_ord_dict: Ordered dict mapping channel names to their read values.
        """
        threadable_channels = []
        non_threadable_channels = []
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = []
        for channel in channel_list:
            if channel.resolve_delegator() is self:
                # if the user asked the delegator directly to read do not thread
                # this is also useful for the masters caching mode to do it
                # last
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
        results.update(
            self._read_channels_non_threaded(non_threadable_channels))
        if len(self._self_delegation_channels):
            self._partial_delegation_results.update(results)
            results.update(
                self._read_delegated_channel_list(  # pylint: disable=no-member; inherited from delegator via multiple inheritance
                    self._self_delegation_channels))
        self._partial_delegation_results = results_ord_dict()
        self._self_delegation_channels = results_ord_dict()
        return results

    def _read_channels_non_threaded(self, channel_list):
        # get a dictionary of delegators for list of channel objects
        delegator_list = []
        for channel in channel_list:
            delegator_list.append(channel.resolve_delegator())
        # remove all duplicates
        delegator_list = list(set(delegator_list))
        # have each delegator read its channels
        results = results_ord_dict()
        for delegator in delegator_list:
            # for each delegator get the list of channels it is responsible for
            channel_delegation_list = []
            for channel in channel_list:
                if delegator == channel.resolve_delegator():
                    channel_delegation_list.append(channel)
            results.update(
                delegator._read_delegated_channel_list(channel_delegation_list))
        return results

    def _read_channels_threaded(self, channel_list):
        # dont read threaded unless i know how to group interfaces for theads (only interface_factory's
        #    know this, ie a master
        if not hasattr(self, 'group_com_nodes_for_threads_filter'):
            return self._read_channels_non_threaded(channel_list)
        # get a dictionary of delegator's by channel name
        delegator_list = [channel.resolve_delegator()
                          for channel in channel_list]
        # remove all duplicates
        delegator_list = list(set(delegator_list))
        # build a list of interfaces that will be used in this read
        interfaces = []
        for delegator in delegator_list:
            for interface in delegator.get_interfaces():
                interfaces.append(interface)

        remaining_delegators = []
        interface_thread_groups = self.group_com_nodes_for_threads_filter(  # pylint: disable=no-member; defined in master subclass, guarded by hasattr check above
            interfaces)
        work_units = 0
        if len(interface_thread_groups):
            for interface_group in interface_thread_groups:
                # build a group of delegators for each potential thread
                delegator_group = []
                remaining_delegators = []
                for delegator in delegator_list:
                    interfaces = delegator.get_interfaces()
                    # a delegator without interfaces cannot be threaded since I
                    # dont know how it works
                    if len(interfaces) and interfaces.issubset(
                            interface_group):
                        delegator_group.append(delegator)
                    else:
                        remaining_delegators.append(delegator)

                # build a list of channels for that group of delegators to read
                delegator_groups_channel_list = []
                # this is where the channel reads become unordered...
                for delegator in delegator_group:
                    for channel in channel_list:
                        if channel.resolve_delegator() == delegator:
                            delegator_groups_channel_list.append(channel)
                # start the threaded read here
                # not threaded yet
                work_units += 1
                # send channels to thread pool
                self._read_queue.put(delegator_groups_channel_list)
                delegator_list = remaining_delegators
        else:
            remaining_delegators = delegator_list
        results = self.get_threaded_results(work_units)
        # group all the thread results here
        # find the channels for any decelerators that couldn't be threaded
        delegator_groups_channel_list = []
        for delegator in remaining_delegators:
            for channel in channel_list:
                if channel.resolve_delegator() == delegator:
                    delegator_groups_channel_list.append(channel)
        results.update(self._read_channels_non_threaded(
            delegator_groups_channel_list))
        # check results to make sure every channel in channel_list is present,
        # otherwise it is a read error
        for channel in channel_list:
            if channel.get_name() in results:
                pass
            else:
                results[channel.get_name()] = ChannelReadException(
                    'READ_ERROR')
        return results

    def start_threads(self, number):
        """Start worker threads for concurrent channel reads.

        Creates the specified number of background threads that pull channel
        lists from a shared queue and read them in parallel.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'start_threads')
        True

        Args:
            number: The number of worker threads to start.

        Raises:
            Exception: If threads have already been started.
        """
        if self._threaded is False:
            self._threaded = True
            self._threads = number
            self._read_queue = queue.Queue()
            self._read_results_queue = queue.Queue()
            for i in range(number):
                _thread.start_new_thread(self.threaded_read_function, ())
        else:
            raise Exception('Threads already started, do not start again')

    def stop_threads(self):
        """Stop worker threads started by start_threads.

        Supports the ``channel_group`` workflow by performing the described operation.

        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'stop_threads')
        True

        """
        if self._threaded:
            self._threaded = False
            for _ in range(self._threads):
                self._read_queue.put(None)

    def threaded_read_function(self):
        """Run the worker-thread loop that consumes channel-read requests from the queue.

        Supports the ``channel_group`` workflow by performing the described operation.

        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'threaded_read_function')
        True

        """
        while self._threaded:
            try:
                channel_list = self._read_queue.get(block=True)
            except queue.Empty:
                # shouldn't get here
                pass
            else:
                if channel_list is None:
                    break
                try:
                    results = self._read_channels_non_threaded(channel_list)
                except Exception as e:
                    print((traceback.format_exc()))
                    self._read_results_queue.put(e)
                else:
                    self._read_results_queue.put(results)

    def get_threaded_results(self, work_units):
        """Collect results from threaded channel reads.

        Blocks until all *work_units* results have been received from the
        result queue.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'get_threaded_results')
        True

        Args:
            work_units: The number of completed work-unit results to wait for.

        Returns:
            results_ord_dict: Aggregated results from all worker threads.

        Raises:
            Exception: If all work units failed and no results were collected.
        """
        results = results_ord_dict()
        for i in range(work_units):
            thread_results = self._read_results_queue.get(block=True)
            if isinstance(thread_results, Exception):
                _error = thread_results  # noqa: F841
                # raise thread_results
            else:
                results.update(thread_results)
        if len(results) == 0 and work_units > 0:
            # if we get here every work unit failed, raise exception
            debug_logging.error("error out {}".format(len(results)))
            raise Exception
        return results

    def read_all_channels(self, categories=None, exclusions=None):
        """Read all readable channels and return results sorted by channel name.

        Optionally filters channels by category and excludes specific channels.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, 'read_all_channels')
        True

        Args:
            categories: An iterable of category strings to include.  If None,
                all readable channels are read.
            exclusions: A list of channel objects, names, or groups to skip.

        Returns:
            results_ord_dict: Alphabetically sorted dict of channel names to values.
        """
        if exclusions is None:
            exclusions = []
        channels = [
            channel for channel in self.get_all_channels_list() if channel.is_readable() and (
                categories is None or channel.get_category() in categories)]
        for channel in self.resolve_channel_list(exclusions):
            channels.remove(channel)
        return results_ord_dict(sorted(list(self.read_channel_list(
            # sort results by channel name
            channels).items()), key=lambda t: t[0]))

    def remove_channel(self, channel):
        # note this delete will only remove from this channel_group, not from
        # children
        """Remove a channel from this group's direct channel dictionary.

        Does not remove from sub-groups.  Use :meth:`remove_channel_by_name`
        when you have a name string instead of a channel object.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_channel')
        True

        Args:
            channel: The channel object to remove.

        Raises:
            Exception: If the channel is not a direct member of this group.
        """
        channel_name = channel.get_name()
        if channel_name not in list(self._channel_dict.keys()):
            raise Exception(
                'Channel "{}" is not a member of {}'.format(
                    channel_name, self.get_name()))
        del self._channel_dict[channel_name]

    def remove_channel_group(self, channel_group_to_remove):
        """Remove all channels belonging to a channel group from this group.
        Removes the specified channel group.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_channel_group')
        True

        Args:
            channel_group_to_remove: The channel_group whose channels should
                be removed from this group.
        """
        removed_channels = channel_group_to_remove.get_all_channels_list()
        for removed_channel in removed_channels:
            self.remove_channel(removed_channel)

    def remove_channel_by_name(self, channel_name):
        """Remove a channel from this group by its registered name.
        Removes the specified channel by name.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_channel_by_name')
        True

        Args:
            channel_name: The name of the channel to remove.
        """
        channel = self.get_channel(channel_name)
        self.remove_channel(channel)

    def remove_all_channels_and_sub_groups(self):
        """Remove all channels and sub-groups, resetting this group to empty.

        Removes the specified all channels and sub groups.

        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_all_channels_and_sub_groups')
        True

        """
        self._channel_dict = results_ord_dict()
        self._sub_channel_groups = []

    def remove_sub_channel_group(self, sub_channel_group):
        """Remove a sub-channel group from this group's sub-group list.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_sub_channel_group')
        True

        Args:
            sub_channel_group: The sub-group object to detach.
        """
        self._sub_channel_groups.remove(sub_channel_group)

    def remove_category(self, category):
        # note this delete will only remove from this channel_group, not from
        # children
        """Remove all channels matching a given category from this group.

        Only removes from the direct channel dictionary, not from sub-groups.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_category')
        True

        Args:
            category: The category string to match for removal.
        """
        for channel in self.get_all_channels_list():
            if channel.get_category() == category:
                self.remove_channel(channel)

    def remove_categories(self, *categories):
        """Remove all channels matching any of the given categories.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_categories')
        True

        Args:
            *categories: One or more category strings whose channels should
                be removed.
        """
        for category in categories:
            self.remove_category(category)

    def debug_print(self, indent=" "):
        """Print the channel hierarchy to stdout for debugging.

        Recursively prints each channel and its delegation info, indented
        by sub-group depth.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'debug_print')
        True

        Args:
            indent: The prefix string used for indentation at this level.
        """
        for ch in list(self._channel_dict.values()):
            d = ""
            if ch.get_delegator() is not ch:
                d = "(delegated by {})".format(ch.resolve_delegator())
            print(("{} {} {}".format(indent, ch, d)))
        for sub_channel_group in self._sub_channel_groups:
            print(("{} {}".format(indent, sub_channel_group)))
            sub_channel_group.debug_print("{}   ".format(indent))
            # remove the excluded items from the scan list

    def remove_channel_list(self, item_list):
        """Remove multiple channels specified as objects, names, or groups.
        Removes the specified channel list.

        Removes the specified item from the object's internal collection.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'remove_channel_list')
        True

        Args:
            item_list: A list of channel objects, name strings, or
                channel_group objects to remove.
        """
        channel_list = self.resolve_channel_list(item_list)
        for channel in channel_list:
            self.remove_channel(channel)

    def resolve_channel_list(self, item_list):
        """Resolve a mixed list of channels, names, and groups into a flat channel_group.

        Accepts channel objects, name strings, and channel_group objects in
        any combination, and returns a single channel_group containing all
        resolved channel objects.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'resolve_channel_list')
        True

        Args:
            item_list: A list containing channel objects, channel name strings,
                or channel_group objects.

        Returns:
            channel_group: A new flat channel_group with all resolved channels.

        Raises:
            Exception: If an element of *item_list* is not a recognized type.
        """
        ch_group = channel_group()
        for item in item_list:
            if isinstance(item, str):
                ch_group._add_channel(self.get_channel(item))
            elif isinstance(item, channel):
                ch_group._add_channel(item)
            elif isinstance(item, channel_group):
                ch_group.merge_in_channel_group(item)
            else:
                raise Exception('Unknown input {}'.format(item_list))
        return ch_group

    def clone(self, name=None, categories=None):
        """Build a flattened clone, reconnecting remote channels to fresh clients.

        Creates a new channel_group containing copies of all channels.  For
        remote channels, new client connections are established so that the
        clone is independent of the original server bindings.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'clone')
        True

        Args:
            name: Display name for the cloned group.  Defaults to
                ``"<original_name>_cloned"``.
            categories: An iterable of category strings to include.  If None,
                all channels are cloned.

        Returns:
            channel_group: A new independent channel_group with the same channels.
        """
        channels = self.get_all_channels_list()
        if categories is not None:
            channels = [
                channel for channel in channels if channel.get_category() in categories]
        new_channels = []
        remote_channel_group_clients = set()
        for ch in channels:
            if isinstance(ch, remote_channel):
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
        """Generate an HTML document describing all channels and optionally write it to a file.

        The HTML includes a table of channel names, categories, and
        descriptions. When *verbose* is True, preset and attribute
        dropdowns are included for each channel.


        >>> from PyICe.lab_core import channel_group
        >>> hasattr(channel_group, 'write_html')
        True

        Args:
            file_name: Path to write the HTML file.  If None, no file is written.
            verbose: If True, include preset and attribute tables per channel.
            sort_categories: If True, group channels by category before
                alphabetical name sort.

        Returns:
            str: The complete HTML document as a string.
        """
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
        channels = sorted(
            self.get_all_channels_list(),
            key=lambda ch: ch.get_name())
        if sort_categories:
            # stable sort preserves name sort above when tied
            channels = sorted(channels, key=lambda ch: str(ch.get_category()))
        for channel in channels:
            txt += '<TR>\n'
            txt += '''<TD><p style='font-family:"Helvetica"'>{}</p></TD>\n'''.format(
                channel.get_name())
            txt += '''<TD><p style='font-family:"Helvetica"'>{}</p></TD>\n'''.format(
                channel.get_category())
            txt += '<TD>\n'
            txt += '''<p style='font-family:"Helvetica"'>\n'''
            txt += '{}\n'.format(
                "No Description Available" if channel.get_description() in [
                    '', None, '\n\n'] else channel.get_description())
            txt += '</p>\n'
            if verbose:  # add presets and attributes
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
                except Exception:
                    print((traceback.format_exc()))
                    pass  # Only integer_channels and registers can have presets
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
    """Superclass for all lab instruments.

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

    >>> from PyICe.virtual_instruments import dummy
    >>> inst = dummy()
    >>> ch = inst.add_channel_write("dac_out")
    >>> _ = ch.write(1.25)
    >>> ch.read()
    1.25
    >>> inst.get_name()
    'Dummy Virtual Instrument'

    """
    def __init__(self, name):
        """Initialize instrument base class with a name and empty interface list.

        Subclasses should call ``instrument.__init__(self, name)`` and
        use ``add_interface_*`` methods to attach communication interfaces.


        >>> from PyICe.lab_core import instrument
        >>> instrument is not None
        True

        Args:
            name: A descriptive name for this instrument instance.
        """
        channel_group.__init__(self, name)
        self._interfaces = []
        if not hasattr(self, '_base_name'):
            self._base_name = "unnamed instrument"

    def add_channel(self, channel_name):
        """Register a named channel on this instrument.

        Subclasses must override this method to create a :class:`channel`
        object (with a read or write function) and call
        ``self._add_channel(channel)`` to register it.  For multi-channel
        instruments, additional arguments (e.g. physical channel number)
        are typically accepted.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'add_channel')
        True

        Args:
            channel_name: The user-visible name for the new channel.

        Raises:
            Exception: Always, because this base implementation must be
                overridden by each instrument driver.
        """
        raise Exception(
            'Add channel method not implemented for instrument {}'.format(
                self.get_name()))

    def get_error(self):
        """Return the first error from the instrument.

        Override in a subclass (e.g. :class:`scpi_instrument`) to query the
        actual hardware error queue.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'get_error')
        True

        Returns:
            str: A message indicating error checking is not implemented.
        """
        return 'Error checking not implemented for this instrument'

    def get_errors(self):
        """Return a list of all errors from the instrument.

        Override in a subclass to query the actual hardware error queue.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'get_errors')
        True

        Returns:
            list: A single-element list with a not-implemented message.
        """
        return ['Error checking not implemented for this instrument']

    def _add_interface(self, interface):
        self._interfaces.append(interface)

    def get_interface(self, num=0):
        """Return an attached communication interface by index.
        Returns the stored interface value from the object's internal state.
        Returns the stored interface from the object's internal state.

        Returns the stored interface from the object's internal state.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'get_interface')
        True

        Args:
            num: Zero-based index of the interface to retrieve.

        Returns:
            The interface object at the given index.
        """
        return self._interfaces[num]

    def set_category(self, category_name, update_existing_channels=False):
        """Set the default category for new channels added to this instrument.
        Updates the category in the object's internal state.

        Updates the category in the object's internal state.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'set_category')
        True

        Args:
            category_name: The category string to assign.
            update_existing_channels: If True, retroactively update the
                category of all channels already in this instrument.
        """
        self._base_name = category_name
        if update_existing_channels:
            for channel in self:
                channel.set_category(category_name)

    def add_interface_visa(self, interface_visa, timeout=None):
        """Attach a VISA interface to this instrument.

        If a *timeout* is given and exceeds the interface's current timeout,
        the interface timeout is increased (but never decreased, since the
        interface may be shared).


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'add_interface_visa')
        True

        Args:
            interface_visa: A :class:`lab_interfaces.interface_visa` instance.
            timeout: Optional timeout in seconds.  Only applied if it is
                greater than the interface's current timeout.

        Raises:
            Exception: If *interface_visa* is not an interface_visa instance.
        """
        if not isinstance(interface_visa, lab_interfaces.interface_visa):
            raise Exception(
                'Interface must be a visa interface,, interface is {}'.format(interface_visa))
        if timeout and timeout > interface_visa.timeout:
            # only increase a timeout if it is shared it may be to fast for the
            # others
            interface_visa.timeout = timeout
        self._add_interface(interface_visa)

    def add_interface_raw_serial(
            self, interface_raw_serial, timeout=None, baudrate=None):
        """Attach a raw serial interface to this instrument.

        Optionally overrides timeout and baudrate on the interface.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'add_interface_raw_serial')
        True

        Args:
            interface_raw_serial: A :class:`lab_interfaces.interface_raw_serial`
                instance.
            timeout: Optional timeout in seconds.  Only applied if it exceeds
                the interface's current timeout.
            baudrate: Optional baud rate to set on the serial interface.

        Raises:
            Exception: If *interface_raw_serial* is not an
                interface_raw_serial instance.
        """
        if not isinstance(interface_raw_serial,
                          lab_interfaces.interface_raw_serial):
            raise Exception('Interface must be a raw serial interface, interface is {}'.format(
                interface_raw_serial))
        if timeout and timeout > interface_raw_serial.timeout:
            # only increase a timeout if it is shared it may be to fast for the
            # others
            interface_raw_serial.timeout = timeout
        if baudrate:
            interface_raw_serial.baudrate = baudrate
        self._add_interface(interface_raw_serial)

    def add_interface_twi(self, interface_twi, timeout=None):
        """Attach a TWI (I2C) interface to this instrument.
        Creates and registers a new interface twi.

        Appends a new interface twi entry to the object's internal collection.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'add_interface_twi')
        True

        Args:
            interface_twi: A :class:`lab_interfaces.interface_twi` instance.
            timeout: Optional timeout in seconds.  Only applied if it exceeds
                the interface's current timeout.

        Raises:
            Exception: If *interface_twi* is not an interface_twi instance.
        """
        if not isinstance(interface_twi, lab_interfaces.interface_twi):
            raise Exception(
                'Interface must be a twi interface, interface is {}'.format(interface_twi))
        if timeout and timeout > interface_twi.timeout:
            # only increase a timeout if it is shared it may be to fast for the
            # others
            interface_twi.timeout = timeout
        self._add_interface(interface_twi)

    def add_interface_spi(self, interface_spi, timeout=None, baudrate=None):
        """Attach an SPI interface to this instrument.
        Creates and registers a new interface spi.

        Appends a new interface spi entry to the object's internal collection.


        >>> from PyICe.lab_core import instrument
        >>> hasattr(instrument, 'add_interface_spi')
        True

        Args:
            interface_spi: A :class:`lab_interfaces.interface_spi` instance.
            timeout: Optional timeout in seconds.  Only applied if it exceeds
                the interface's current timeout.
            baudrate: Optional baud rate (currently accepted but not applied
                to the interface).

        Raises:
            Exception: If *interface_spi* is not an interface_spi instance.
        """
        if not isinstance(interface_spi, lab_interfaces.interface_spi):
            raise Exception(
                'Interface must be an spi interface, interface is {}'.format(interface_spi))
        if timeout and timeout > interface_spi.timeout:
            # only increase a timeout if it is shared it may be to fast for the
            # others
            interface_spi.timeout = timeout
        self._add_interface(interface_spi)

    def _add_channel(self, channel):
        # overload _add_channel to do some automatic repetive tasks before
        #  letting channel_group do the rest
        for interface in self._interfaces:
            channel.add_interface(interface)
        if channel.get_category() is None:
            channel.set_category(self._base_name)
        channel_group._add_channel(self, channel)
        return channel


class scpi_instrument(instrument):
    """SCPI Instrument Base Class. Implements methods common to all SCPI instruments.

    Instruments which adhere to the SCPI specification should inherit from the
    scpi_instrument class rather than the instrument class.

    >>> from PyICe.lab_core import scpi_instrument
    >>> scpi_instrument is not None
    True

    """
    def __init__(self, name):
        """Initialize a SCPI instrument with debug-communications mode disabled.
        Calls the parent class constructor and initializes instance-specific
        attributes for scpi_instrument.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_core import scpi_instrument
        >>> scpi_instrument is not None
        True

        Args:
            name: A descriptive name for this SCPI instrument.
        """
        super(scpi_instrument, self).__init__(name)
        self._debug_comms = False

    def get_interface(self, num=0):
        """Return the communication interface, optionally wrapped with error checking.

        When ``_debug_comms`` is True, wraps the real interface so every
        read, write, and ask call automatically checks ``SYST:ERROR?``
        and raises on SCPI errors.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'get_interface')
        True

        Args:
            num: Zero-based index of the interface to retrieve.

        Returns:
            The (possibly error-checking wrapped) interface object.
        """
        if not self._debug_comms:
            return super(scpi_instrument, self).get_interface(num=num)
        else:
            try:
                return self._debug_if
            except AttributeError:
                # first time
                import types
                print(
                    f'Creating SCPI SYS:ERR checking interface for {self.get_name()}')
                self._debug_if = super(
                    scpi_instrument,
                    self).get_interface(
                    num=num)
                self._debug_if._naked_read = self._debug_if.read
                self._debug_if._naked_write = self._debug_if.write
                self._debug_if._naked_ask = self._debug_if.ask
                _raw_if = copy.copy(self._debug_if)

                def read_check(s):
                    """Read from the interface and check for SCPI errors.

                    Reads data from the underlying source and returns it.


                    >>> from PyICe.lab_core import scpi_instrument
                    >>> hasattr(scpi_instrument, 'read_check')
                    True

                    Args:
                        s: The interface instance (bound as self by MethodType).

                    Returns:
                        str: The response string from the instrument.

                    Raises:
                        Exception: If the SCPI error queue contains errors.
                    """
                    resp = s._naked_read()
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(err_lst)
                    return resp

                def write_check(s, m):
                    """Write a command to the interface and check for SCPI errors.
                    Formats and sends the command to the instrument.

                    Writes data to the underlying target.


                    >>> from PyICe.lab_core import scpi_instrument
                    >>> hasattr(scpi_instrument, 'write_check')
                    True

                    Args:
                        s: The interface instance (bound as self by MethodType).
                        m: The SCPI command string to send.

                    Raises:
                        Exception: If the SCPI error queue contains errors
                            after the write.
                    """
                    s._naked_write(m)
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(m, err_lst)

                def ask_check(s, m):
                    """Send a query to the interface and check for SCPI errors.

                    Transmits data to the remote endpoint.


                    >>> from PyICe.lab_core import scpi_instrument
                    >>> hasattr(scpi_instrument, 'ask_check')
                    True

                    Args:
                        s: The interface instance (bound as self by MethodType).
                        m: The SCPI query string to send.

                    Returns:
                        str: The response string from the instrument.

                    Raises:
                        Exception: If the SCPI error queue contains errors
                            after the query.
                    """
                    resp = s._naked_ask(m)
                    err_lst = self.get_errors(interface=_raw_if)
                    if len(err_lst) > 1:
                        raise Exception(m, err_lst)
                    return resp
                self._debug_if.read = types.MethodType(
                    read_check, self._debug_if)
                self._debug_if.write = types.MethodType(
                    write_check, self._debug_if)
                self._debug_if.ask = types.MethodType(
                    ask_check, self._debug_if)
                return self.get_interface(num=num)

    def get_error(self, interface=None):
        """Query the SCPI error queue and return the first error string.

        An error code of ``+0`` or ``0`` indicates no error.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'get_error')
        True

        Args:
            interface: Optional interface to query.  If None, uses the
                default interface from :meth:`get_interface`.

        Returns:
            str: The error string returned by ``SYST:ERROR?``.
        """
        return self.error(interface=interface)

    def get_errors(self, interface=None):
        """Drain the SCPI error queue and return all accumulated error strings.

        Repeatedly queries ``SYST:ERROR?`` until the instrument returns
        error code ``+0`` (no error).  The final no-error entry is included.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'get_errors')
        True

        Args:
            interface: Optional interface to query.  If None, uses the
                default interface.

        Returns:
            list: A list of error strings, ending with the no-error response.
        """
        errors = []
        while (True):
            response = self.get_error(interface=interface)  # .decode('utf-8')
            errors.append(response)
            if (response.split(",")[0] == '+0'):
                return errors
            elif (response.split(",")[0] == '0'):
                return errors

    def beep(self):
        """Send a beep command.

        Sends the corresponding SCPI command string to the instrument over the bus.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'beep')
        True

        """
        self.get_interface().write('SYST:BEEP')

    def clear_status(self):
        """Send the *CLS command.

        Transmits data to the remote endpoint.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'clear_status')
        True

        """
        self.get_interface().write('*CLS')

    def display_clear(self):
        """Clear the instrument display.

        Sends the corresponding SCPI command string to the instrument over the bus.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'display_clear')
        True

        """
        self.get_interface().write('DISP:TEXT:CLE')

    def display_off(self):
        """Turn the instrument display off.

        Supports the ``scpi_instrument`` workflow by performing the described operation.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'display_off')
        True

        """
        self.get_interface().write('DISP OFF')

    def display_on(self):
        """Turn the instrument display on.

        Supports the ``scpi_instrument`` workflow by performing the described operation.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'display_on')
        True

        """
        self.get_interface().write('DISP ON')

    def display_text(self, text=""):
        """Display a text message on the instrument front panel.
        Sends the ``DISP:TEXT`` SCPI command to the instrument.
        Outputs the text to the console or display.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'display_text')
        True

        Args:
            text: The message string to display.  Defaults to empty (clears text).
        """
        # command=b"DISP:TEXT '"+text.encode('utf-8')+b"'"
        command = f"DISP:TEXT '{text}'"
        self.get_interface().write(command)

    def enable_serial_polling(self):
        """Enable the instrument to report operation complete via serial polling.

        Enables the serial polling function on the instrument via SCPI.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'enable_serial_polling')
        True

        """
        self.clear_status()  # clear the stauts register
        # enable the operation complete bit in the event register
        self.get_interface().write('*ESE 1')
        # enable the event register to update the status register
        self.get_interface().write('*SRE 32')

    def error(self, interface=None):
        """Query the SCPI ``SYST:ERROR?`` register and return the response.
        Sends the ``SYST:ERROR`` SCPI command to the instrument.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'error')
        True

        Args:
            interface: Optional interface to use for the query.  If None,
                uses the default interface.

        Returns:
            str: The raw error response string from the instrument.
        """
        if interface is None:
            interface = self.get_interface()
        return interface.ask('SYST:ERROR?')

    def operation_complete(self):
        """Block until the current operation completes by sending ``*OPC?``.

        The query blocks I/O until the instrument signals completion or
        the interface times out.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'operation_complete')
        True

        Returns:
            str: The instrument response to ``*OPC?`` (typically ``"1"``).
        """
        return self.get_interface().ask('*OPC?')

    def fetch(self):
        """Retrieve the latest measurement result via the ``FETCH?`` query.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'fetch')
        True

        Returns:
            str: The measurement data string from the instrument.
        """
        return self.get_interface().ask('FETCH?')

    def init(self):
        """Send INIT command.

        Transmits data to the remote endpoint.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'init')
        True

        """
        self.get_interface().write('INIT')

    def initiate_measurement(self, enable_polling=False):
        """Initiate a new measurement, optionally with serial-poll completion signaling.

        When *enable_polling* is True, configures the status register for
        serial-poll-based operation-complete notification before triggering.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'initiate_measurement')
        True

        Args:
            enable_polling: If True, enable serial polling and OPC
                signaling before initiating.
        """
        if enable_polling:
            self.enable_serial_polling()  # enable serial polling
            self.clear_status()  # clear the status register
            self.operation_complete()
            self.init()
            # enable operation complete update to the status register
            self.get_interface().write('*OPC')
        else:
            self.operation_complete()
            self.init()

    def read_measurement(self):
        """Retrieve the latest measurement result via ``FETCH?``.
        Sends the appropriate query to the instrument and parses the response.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'read_measurement')
        True

        Returns:
            str: The measurement data string from the instrument.
        """
        return self.get_interface().ask('FETCH?')

    def reset(self):
        """Send the *RST command.

        Transmits data to the remote endpoint.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'reset')
        True

        """
        self.get_interface().write('*RST')

    def trigger(self):
        """Send the *TRG command.

        Transmits data to the remote endpoint.

        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'trigger')
        True

        """
        self.get_interface().write('*TRG')

    def identify(self):
        """Query the instrument identification string via ``*IDN?``.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'identify')
        True

        Returns:
            str: The identification string (manufacturer, model, serial, firmware).
        """
        return self.get_interface().ask('*IDN?')

    def flush(self, buffer):
        """Flush the communication interface buffer.

        Supports the ``scpi_instrument`` workflow by performing the described operation.


        >>> from PyICe.lab_core import scpi_instrument
        >>> hasattr(scpi_instrument, 'flush')
        True

        Args:
            buffer: The buffer identifier to flush (interface-specific constant).
        """
        self.get_interface().flush(buffer)


class remote_channel_group_server(object):
    """Server that exposes a channel group for remote access over a network connection.

    >>> from PyICe.lab_core import remote_channel_group_server
    >>> remote_channel_group_server is not None
    True

    """

    def __init__(self, channel_group_object, address='localhost',
                 port=5001, authkey=DEFAULT_AUTHKEY):
        """Initialize the remote channel group server.
        Stores configuration in ``cgm``, ``channel_group`` for use by other
        methods.

        Initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import remote_channel_group_server
        >>> hasattr(remote_channel_group_server, '__init__')
        True

        Args:
            channel_group_object: The channel group to expose remotely.
            address: Network address to bind to.
            port: TCP port number.
            authkey: Authentication key for the connection.
        """
        self.channel_group = channel_group_object

        class channel_group_manager(multiprocessing.managers.BaseManager):
            pass
        channel_group_manager.register('channel')
        channel_group_manager.register(
            'get_channel_server',
            callable=lambda: self.channel_group,
            method_to_typeid={
                'get_channel': 'channel'})
        self.cgm = channel_group_manager(
            address=(address, port), authkey=authkey)

    def serve_forever(self):
        """Start the manager server and listen for incoming connections indefinitely.

        This blocks the calling thread and serves remote channel group
        requests until the process is terminated.

        >>> from PyICe.lab_core import remote_channel_group_server
        >>> hasattr(remote_channel_group_server, 'serve_forever')
        True

        """
        print(("Launching remote server listening at address {}:{}".format(
            self.cgm.address[0], self.cgm.address[1])))
        server = self.cgm.get_server()
        server.serve_forever()


class remote_channel(channel):
    """Proxy channel that forwards method calls to a remote channel over a network connection.

    >>> from PyICe.lab_core import remote_channel
    >>> remote_channel is not None
    True

    """

    methods_to_proxy = ['__str__',
                        # integer_channel methods:
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
                        # 'read_without_delegator',
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

                        # channel methods:
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

                        # delegator methods omitted
                        ]

    def __init__(self, proxy_channel, parent_delegator):
        """Initialize a remote channel proxy by copying methods from the remote channel.
        Stores configuration in ``_proxy_delegator`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_core import remote_channel
        >>> remote_channel is not None
        True

        Args:
            proxy_channel: The remote proxy channel object to wrap.
            parent_delegator: The delegator that owns this channel.
        """
        # this intentially does not call the init of channel,just delegator
        delegator.__init__(self)
        self.set_delegator(parent_delegator)
        self._proxy_delegator = delegator
        for method_name in self.methods_to_proxy:
            if hasattr(proxy_channel, method_name):
                setattr(self, method_name, getattr(proxy_channel, method_name))


class remote_channel_group_client(channel_group, delegator):
    """Client that connects to a remote channel group server and proxies its channels locally.

    >>> from PyICe.lab_core import remote_channel_group_client
    >>> remote_channel_group_client is not None
    True

    """

    def __init__(self, address='localhost', port=5001,
                 authkey=DEFAULT_AUTHKEY):
        """Initialize the remote channel group client.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import remote_channel_group_client
        >>> hasattr(remote_channel_group_client, '__init__')
        True

        Args:
            address: Network address of the remote server.
            port: TCP port number.
            authkey: Authentication key for the connection.

        Raises:
            RemoteChannelGroupException: If the remote server port is not open or
                the connection cannot be established.
        """
        self._address = address
        self._port = port
        self._authkey = authkey
        channel_group.__init__(
            self, 'remote_channel @ {}:{}'.format(address, port))
        delegator.__init__(self)

        class channel_group_manager(multiprocessing.managers.BaseManager):
            pass
        channel_group_manager.register('channel')
        channel_group_manager.register('get_channel_server')
        # check if the port is open, there doesn't seem to be a way to time out
        # so check first
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((address, port))
        if result:
            # the port is not open
            raise RemoteChannelGroupException(
                'Unable to connect: {}'.format(result))
        self.cgm = channel_group_manager(
            address=(address, port), authkey=authkey)
        self.cgm.connect()
        self.server = self.cgm.get_channel_server()  # pylint: disable=no-member; method added dynamically by BaseManager.register()
        names = self.server.get_all_channel_names()
        for i in names:
            ch = self.server.get_channel(i)
            self._add_channel(remote_channel(ch, self))

    def read_delegated_channel_list(self, channel_list):
        """Return read delegated channel list result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import remote_channel_group_client
        >>> hasattr(remote_channel_group_client, 'read_delegated_channel_list')
        True

        Args:
            channel_list: List of channel objects.

        Returns:
            The value read from the device or channel.
        """
        channel_names = [ch.get_name() for ch in channel_list]
        return self.server.read_channels(channel_names)

    def clone(self):
        """Return the clone.

        Supports the ``remote_channel_group_client`` workflow by performing the described operation.


        >>> from PyICe.lab_core import remote_channel_group_client
        >>> hasattr(remote_channel_group_client, 'clone')
        True

        Returns:
            The clone result.
        """
        return remote_channel_group_client(
            self._address, self._port, self._authkey)


class channel_master(channel_group, delegator):
    """Master channel collection. There is typically only one. It replaces the old lab_bench.

    as the main point of interaction with channels.  Channels and channel_groups (instruments) may
    be added to it.  It also creates dummy and virtual channels and adds them to its collection.  It also
    supports virtual_caching channels; these can use cached data if available during logging or other multiple channel read.


    >>> from PyICe.lab_core import channel
    >>> hasattr(channel, 'write')
    True

    """

    def __init__(self, name=None):
        """Initialize the channel master.
        Stores configuration in ``_caching_mode``, ``_read_callbacks``,
        ``_write_callbacks`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import channel_master
        >>> channel_master is not None
        True

        Args:
            name: Optional name; defaults to the object's repr string.
        """
        if name is None:
            # remove Python <> because Qt interpret's them as HTML tags
            name = object.__str__(self)[1:-1]
        channel_group.__init__(self, name)
        delegator.__init__(self)
        self._caching_mode = 0
        self._read_callbacks = []
        self._write_callbacks = []
        self.start_threads(24)

    def add(self, channel_or_group):
        """Return the add.
        Registers channels with the master so they participate in
        ``read_all_channels()`` sweeps and are visible to the logger.

        Captures data for later analysis or replay.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add')
        True

        Args:
            channel_or_group: Channel or group to use.

        Returns:
            The add result.
        """
        return channel_group.add(self, channel_or_group)

    def add_channel_virtual(
            self, channel_name, read_function=None, write_function=None, integer_size=None):
        """Adds a channel named channel_name. Channel may have a read_function or a write_function but not both.

        If write_function is supplied, the write function is called with the value when written, and the last written value is returned when read.
        If read_function is supplied, this channel returns the return of read_function when read.
        If integer_size is not None, creates in integer_channel instead of a channel. integer_size should specify the number of data bits.
        Integer channels can add presets, formats.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_channel_virtual')
        True

        Args:
            channel_name: Name for the new channel.
            integer_size: Integer size to use.
            read_function: Callable for reading the channel.
            write_function: Callable for writing the channel.

        Returns:
            The newly created channel object.
        """
        if integer_size is not None:
            new_channel = integer_channel(
                channel_name,
                size=integer_size,
                read_function=read_function,
                write_function=write_function)
        else:
            new_channel = channel(
                channel_name,
                read_function=read_function,
                write_function=write_function)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_virtual.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)

    def add_channel_virtual_caching(
            self, channel_name, read_function=None, write_function=None, integer_size=None):
        """Adds a channel named channel_name. Channel may have a read_function or a write_function but not both.

        If write_function is supplied, the write function is called with the value when written, and the last written value is returned when read.
        If read_function is supplied, this channel returns the return of read_function when read.
        If the read_function calls the creating channel_master's read_channel on another channel,
        a cached value may be used if part of a multi-channel channel read. This can improve logging speed in some cases.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_channel_virtual_caching')
        True

        Args:
            channel_name: Name for the new channel.
            integer_size: Integer size to use.
            read_function: Callable for reading the channel.
            write_function: Callable for writing the channel.

        Returns:
            The newly created channel object.
        """
        if integer_size is not None:
            new_channel = integer_channel(
                channel_name,
                size=integer_size,
                read_function=read_function,
                write_function=write_function)
        else:
            new_channel = channel(
                channel_name,
                read_function=read_function,
                write_function=write_function)
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_virtual_caching.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)

    def add_channel_dummy(self, channel_name, integer_size=None):
        """Add a named dummy channel. This can be used if a single physical instrument channel is externally multiplexed to.

        multiple measurement nodes. The user can store the multiple measurement results from a single instrument into
        multiple dummy channels. Also it is useful for logging test conditions.


        >>> from PyICe.lab_core import channel
        >>> hasattr(channel, 'get_name')
        True

        Args:
            channel_name: Name for the new channel.
            integer_size: Integer size to use.

        Returns:
            The newly created channel object.
        """
        if integer_size is not None:
            new_channel = integer_channel(channel_name, size=integer_size)
        else:
            new_channel = channel(channel_name)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_dummy.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)

    def add_channel_delta_timer(self, channel_name, reciprocal=False):
        """Add a named timer channel. Returns the time elapsed since the prior channel read.

        Optionally, compute 1/time to return frequency instead.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_channel_delta_timer')
        True

        Args:
            channel_name: Name for the new channel.
            reciprocal: Reciprocal to use.

        Returns:
            The newly created channel object.
        """
        class timer(object):
            def __init__(self, reciprocal):
                self.reciprocal = reciprocal
                self.last_time = datetime.datetime.now(datetime.timezone.utc)

            def __call__(self):
                """Call the instance.
                Enables calling the object as a function.

                Makes the object callable like a function.


                >>> from PyICe.lab_core import channel_master
                >>> hasattr(channel_master, '__call__')
                True

                Returns:
                    The computed result.
                """
                self.this_time = datetime.datetime.now(datetime.timezone.utc)
                elapsed = self.this_time - self.last_time
                self.last_time = self.this_time
                if not reciprocal:
                    return elapsed.total_seconds()  # return native dimedelta instead?
                else:
                    try:
                        return 1 / elapsed.total_seconds()
                    except ZeroDivisionError:  # too fast?
                        return None
        new_channel = channel(channel_name, read_function=timer(reciprocal))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_timer.__doc__)
        new_channel.set_category('Virtual')
        new_channel.set_display_format_function(
            function=lambda time: eng_string(
                time, fmt=':3.6g', si=True) + 's')
        return self._add_channel(new_channel)

    def add_channel_total_timer(self, channel_name):
        """Add a named timer channel. Returns the time elapsed since first channel read.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_channel_total_timer')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        class timer(object):
            def __init__(self):
                self.beginning = None

            def __call__(self):
                """Call the instance.
                Enables calling the object as a function.

                Makes the object callable like a function.


                >>> from PyICe.lab_core import channel_master
                >>> hasattr(channel_master, '__call__')
                True

                Returns:
                    The computed result.
                """
                if self.beginning is None:
                    self.beginning = datetime.datetime.now(datetime.timezone.utc)
                # return native dimedelta instead?
                return (datetime.datetime.now(datetime.timezone.utc) -
                        self.beginning).total_seconds()
        new_channel = channel(channel_name, read_function=timer())
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_timer.__doc__)
        new_channel.set_category('Virtual')
        new_channel.set_display_format_function(
            function=lambda time: eng_string(
                time, fmt=':3.6g', si=True) + 's')
        return self._add_channel(new_channel)

    def add_channel_counter(self, channel_name, **kwargs):
        """Add a named counter channel. Returns zero the first time channel is read and increments by one each time thereafter.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_channel_counter')
        True

        Args:
            **kwargs: Additional keyword arguments.
            channel_name: Name for the new channel.

        Returns:
            The count.
        """
        class counter(object):
            def __init__(self, init=0, inc=1):
                self.inc = inc
                self.count = init - self.inc

            def __call__(self):
                """Call the instance.
                Enables calling the object as a function.

                Makes the object callable like a function.


                >>> from PyICe.lab_core import channel_master
                >>> hasattr(channel_master, '__call__')
                True

                Returns:
                    The computed result.
                """
                self.count += self.inc
                return self.count

            def write(self, value):
                """Write a value to the channel.

                Writes data to the underlying target.


                >>> from PyICe.lab_core import channel_master
                >>> hasattr(channel_master, 'write')
                True

                Args:
                    value: Value to set.
                """
                self.count = value
        cnt_obj = counter(**kwargs)
        new_channel = channel(channel_name, read_function=cnt_obj)
        new_channel._write = cnt_obj.write
        new_channel.set_write_access()
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_counter.__doc__)
        new_channel.set_category('Virtual')
        return self._add_channel(new_channel)

    def read_channel(self, channel_name):
        """Return read channel result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'read_channel')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The value read from the device or channel.
        """
        debug_logging.debug(
            "Reading Channel (via channel_master.read_channel): %s",
            channel_name)
        channel = self.get_channel(channel_name)
        if self._caching_mode:
            if channel_name in self._partial_delegation_results:
                result = self._partial_delegation_results[channel_name]
                debug_logging.debug(
                    "Reading Channel: %s from previous results: %s",
                    channel_name,
                    result)
            else:
                result = self.get_channel(channel_name).read()
                debug_logging.debug(
                    "Cache miss %s read: %s", channel_name, result)
                if channel in self._self_delegation_channels:
                    self._partial_delegation_results[channel_name] = result
                return result
        else:
            result = self.get_channel(channel_name).read()
        debug_logging.debug("%s read: %s", channel_name, result)
        # calling the observer is done here so its in the secondary thread, if
        # threading
        if not self._caching_mode:
            for function in self._read_callbacks:
                function({channel_name: result})
        return result

    def read_channel_list(self, channel_list):
        """Return read channel list result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'read_channel_list')
        True

        Args:
            channel_list: List of channel objects.

        Returns:
            The value read from the device or channel.
        """
        results = channel_group.read_channel_list(self, channel_list)
        if not self._caching_mode:
            for function in self._read_callbacks:
                debug_logging.debug(
                    "Channel master running read callback %s.", function)
                function(results)
        return results

    def write_channel(self, channel_name, value, confirm=False):
        """Delegates channel write to the appropriate registered instrument.
        Formats and sends the command to the instrument.

        Writes data to the underlying target.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'write_channel')
        True

        Args:
            channel_name: Name for the new channel.
            confirm: Confirm to use.
            value: Value to set.

        Returns:
            True if the write was acknowledged, False otherwise.
        """
        debug_logging.debug("Writing Channel %s to %s", channel_name, value)
        data = channel_group.write_channel(self, channel_name, value, confirm)
        debug_logging.debug(
            "Channel %s write data unformatted to %s",
            channel_name,
            data)
        for function in self._write_callbacks:
            debug_logging.debug(
                "Channel master running write callback %s.", function)
            function({channel_name: data})
        return data

    def read_delegated_channel_list(self, channel_list):
        """Return read delegated channel list result.

        Reads data from the underlying source and returns it.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'read_delegated_channel_list')
        True

        Args:
            channel_list: List of channel objects.

        Returns:
            The value read from the device or channel.
        """
        results = results_ord_dict()
        if self._caching_mode:
            for channel in channel_list:
                if channel.get_name() not in self._partial_delegation_results:
                    results[channel.get_name()] = channel.read_without_delegator()
                    self._partial_delegation_results[channel.get_name(
                    )] = results[channel.get_name()]
                else:
                    results[channel.get_name(
                    )] = self._partial_delegation_results[channel.get_name()]
        else:
            self._caching_mode += 1
            for channel in channel_list:
                if channel.get_name() not in self._partial_delegation_results:
                    results[channel.get_name()] = channel.read()
                    self._partial_delegation_results[channel.get_name(
                    )] = results[channel.get_name()]
                else:
                    results[channel.get_name(
                    )] = self._partial_delegation_results[channel.get_name()]
            self._caching_mode -= 1
        if self._caching_mode == 0:
            self._partial_delegation_results = results_ord_dict()
        return results

    def serve(self, address='localhost', port=5001, authkey=DEFAULT_AUTHKEY):
        """Run the serve step.

        Supports the ``channel_master`` workflow by performing the described operation.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'serve')
        True

        Args:
            address: Network hostname or IP address string.
            authkey: Authentication key bytes for remote connections.
            port: TCP/IP port number.
        """
        rcgs = remote_channel_group_server(self, address, port, authkey)
        rcgs.serve_forever()

    def attach(self, address='localhost', port=5001, authkey=DEFAULT_AUTHKEY):
        """Return the attach.

        Supports the ``channel_master`` workflow by performing the described operation.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'attach')
        True

        Args:
            address: Network hostname or IP address string.
            authkey: Authentication key bytes for remote connections.
            port: TCP/IP port number.

        Returns:
            The attach result.
        """
        try:
            rcgc = remote_channel_group_client(address, port, authkey)
        except RemoteChannelGroupException as e:
            print(e)
            return False
        self.add(rcgc)
        return True

    def background_gui(self, cfg_file='default.guicfg'):
        """Perform background gui operation.

        Supports the ``channel_master`` workflow by performing the described operation.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'background_gui')
        True

        Args:
            cfg_file: Cfg file to use.
        """
        _thread.start_new_thread(self._gui_launcher_passive, (cfg_file,))

    def gui(self, cfg_file='default.guicfg', log_history=False):
        """Log_history - bool. Default False. If set to True, channel read and write commands will be logged in gui_cmd_history.log.

        Captures data for later analysis or replay.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'gui')
        True

        Args:
            cfg_file: Cfg file to use.
            log_history: Log history to use.
        """
        self._gui_launcher(cfg_file, log_history=log_history)

    def add_read_callback(self, read_callback):
        """Adds a read callback. This is a function that will be called any time a channel(s) is read. the callback function should accept one argument: the dictionary of results.

        If it is not important to group results by each batch read, consider adding a callback to an individual channel instead.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_read_callback')
        True

        Args:
            read_callback: Read callback to use.
        """
        self._read_callbacks.append(read_callback)

    def remove_read_callback(self, read_callback):
        """Remove a read callback.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'remove_read_callback')
        True

        Args:
            read_callback: Read callback to use.
        """
        self._read_callbacks.remove(read_callback)

    def add_write_callback(self, write_callback):
        """Adds a write callback. This is a function that will be called any time a channel is written. the callback function should accept one argument: the dictionary of results.

        In this case, the dictionary will only contain a key,value pair for the single channel that was written. For more flexibility, considering adding a callback to an individual channel instead.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'add_write_callback')
        True

        Args:
            write_callback: Write callback to use.
        """
        self._write_callbacks.append(write_callback)

    def remove_write_callback(self, write_callback):
        """Remove a write callback.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'remove_write_callback')
        True

        Args:
            write_callback: Write callback to use.
        """
        self._write_callbacks.remove(write_callback)

    def _gui_launcher_passive(self, cfg_file):
        from . import lab_gui  # this cannot be imported in the main thread
        gui = lab_gui.ltc_lab_gui_app(self, passive=True, cfg_file=cfg_file)
        self.add_read_callback(gui.passive_data)
        self.add_write_callback(gui.passive_data)
        gui.exec_()

    def _gui_launcher(self, cfg_file, log_history):
        from . import lab_gui  # this cannot be imported in the main thread
        gui = lab_gui.ltc_lab_gui_app(
            self,
            passive=False,
            cfg_file=cfg_file,
            log_history=log_history)
        gui.exec_()

    def get_dummy_clone(self):
        """Return the dummy clone.
        Queries the instrument for its current dummy clone and returns the
        parsed response.
        Queries the instrument for its current dummy clone and returns the
        parsed response.

        Returns the stored dummy clone from the object's internal state.


        >>> from PyICe.lab_core import channel_master
        >>> hasattr(channel_master, 'get_dummy_clone')
        True

        Returns:
            The current dummy clone.
        """
        clone = channel_master()
        for channel in self:
            clone.add_channel_dummy(channel.get_name())
            clone[channel.get_name()].set_category(channel.get_category())
            if channel._read:
                clone[channel.get_name()].write(0)
        return clone


class master(channel_master, lab_interfaces.interface_factory):
    """Top-level instrument master combining channel management with interface creation.


    >>> from PyICe.lab_core import channel
    >>> hasattr(channel, 'write')
    True

    """

    def __init__(self, name=None):
        """Initialize the master with channel management and interface factory.

        Calls the parent constructor to inherit base behavior.


        >>> from PyICe.lab_core import master
        >>> obj = master()
        >>> isinstance(obj, master)
        True

        Args:
            name: Optional name; defaults to the object's repr string.
        """
        channel_master.__init__(self, name)
        lab_interfaces.interface_factory.__init__(self)


class channel_access_wrapper(object):
    """Syntatic sugar object to access channels in a channel_group (or master).

    a channel_group (or master) returns the channel object in response to indexing by channel name
    this gives an object that wraps a channel_group the the channels themselves are access by index names.
    master_instance['channel_name'] returns the channel object
    channel_access_wrapper_instance['channel_name'] returns the channel value
    channel_access_wrapper_instance['channel_name']= value writes the value of channel to value

    >>> from PyICe.lab_core import channel_access_wrapper
    >>> channel_access_wrapper is not None
    True

    """
    def __init__(self, channel_group):
        """Initialize the wrapper around a channel group.
        Stores configuration in ``channels`` for use by other methods.

        Initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.lab_core import channel, channel_access_wrapper
        >>> obj = channel_access_wrapper(channel('test'))
        >>> isinstance(obj, channel_access_wrapper)
        True

        Args:
            channel_group: The channel group to wrap.
        """
        self.channels = channel_group

    def __getitem__(self, channel_name):
        """Get item by key or index.
        Enables bracket-style indexing (``obj[key]``).

        Supports bracket-style indexing (``obj[key]``) for this container.


        >>> from PyICe.lab_core import channel_access_wrapper
        >>> hasattr(channel_access_wrapper, "__getitem__")
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The item at the requested position or key.
        """
        return self.channels[channel_name].read()

    def __setitem__(self, channel_name, value):
        """Set item by key or index.
        Enables bracket-style assignment (``obj[key] = value``).

        Supports bracket-style assignment (``obj[key] = value``) for this container.


        >>> from PyICe.lab_core import channel_access_wrapper
        >>> hasattr(channel_access_wrapper, "__setitem__")
        True

        Args:
            channel_name: Name for the new channel.
            value: Value to set.

        Returns:
            The setitem   result.
        """
        return self.channels[channel_name].write(value)


class logger(master):
    """SQLite-backed data logger for channel measurements.


    >>> from PyICe.lab_core import master
    >>> hasattr(master, 'stop_threads')
    True


    """
    def __init__(self, channel_master_or_group=None,
                 database="data_log.sqlite", use_threads=True):
        """Channel_group is a lab_bench object containing all instruments of interest for logging.

        database is the filename in which the sqlite database will be stored.
        Channels or channel groups added to the channel master after the master is added to the logger will not be registered for logging.
        Notice, however, that the logger inherits from the 'master' class, which means that channels can now be added to the LOGGER after the master has been added as if the logger is a master.
        Suppose a master object is created and channel A is added to it. A logger is then created and the master is added to the logger. Another channel, B, is added to the master, and a third channel, C, is added to the logger.
        In this scenario, both the master and the logger can see and interact with channel A. The master can interact with B but not C, and the logger can interact with C but not B.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, '__init__')
        True

        Args:
            channel_master_or_group: Channel master or group to use.
            database: Database to use.
            use_threads: Use threads to use.
        """
        master.__init__(self, name='logger')
        if channel_master_or_group is not None:
            self.merge_in_channel_group(channel_master_or_group)
        for channel in self:
            if not channel.is_readable():
                self.remove_channel(channel)
        # if the object given
        if isinstance(channel_master_or_group, channel_master):
            self.master = channel_master_or_group
        else:
            self.master = self
        self._backend = logger_backend(
            database=database, use_threads=use_threads)
        self._database = database
        atexit.register(self.stop)
        self._table_name = None
        self._log_callbacks = []
        self._previously_logged_data = None

    def __enter__(self):
        """Enter the context manager.
        Sets up the context manager for ``with`` statement usage.

        Sets up the context manager for use in a ``with`` statement.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, '__enter__')
        True

        Returns:
            Self, for use as a context manager.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager.
        Tears down the context manager and handles exceptions.

        Cleans up resources when leaving a ``with`` block.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, '__exit__')
        True

        Args:
            exc_type: Exception type (from context manager protocol).
            exc_value: Exception value (from context manager protocol).
            traceback: Exception traceback (from context manager protocol).

        Returns:
            None (exceptions are not suppressed).
        """
        self.stop()
        return None

    def stop(self):
        """Close sqlite database connection.

        Releases resources and restores the system to a safe state.

        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'stop')
        True

        """
        self._backend.stop()

    def add_channel(self, channel_object):
        """Add a channel.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'add_channel')
        True

        Args:
            channel_object: PyICe channel object to operate on.
        """
        self._add_channel(channel_object)

    def append_table(self, table_name):
        """Perform append table operation.

        Supports the ``logger`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'append_table')
        True

        Args:
            table_name: Database table name.
        """
        self._table_name = table_name
        columns = {ch.get_name(): ch.get_type_affinity() for ch in self}
        self._backend.append_table(table_name, columns)
        self.create_format_view()

    def new_table(self, table_name, replace_table=False, warn=False):
        """Create a new table with columns matching channels known to logger instance.

        if replace_table == 'copy', previously collected data to a new table with the date and time appended to the table name before overwriting
        if replace_table, allow previously collected data to be overwritten
        if not replace_table, raise an exception (or print to screen instead if warn) rather than overwrite existing data

        >>> import tempfile, os
        >>> from PyICe.lab_core import logger
        >>> db = tempfile.mktemp(suffix='.sqlite')
        >>> lg = logger(database=db, use_threads=False)
        >>> _ = lg.add_channel_dummy('x')
        >>> lg.new_table('test_data')
        >>> lg.get_table_name()
        'test_data'
        >>> lg.new_table('test_data', replace_table=True)
        >>> lg.stop()
        >>> os.unlink(db)


        >>> import tempfile, os
        >>> from PyICe.lab_core import logger
        >>> db = tempfile.mktemp(suffix=".sqlite")
        >>> lg = logger(database=db, use_threads=False)
        >>> _ = lg.add_channel_dummy("x")
        >>> lg.new_table("test_data")
        >>> lg.get_table_name()
        'test_data'
        >>> lg.stop()
        >>> os.unlink(db)

        Args:
            replace_table: Replace table to use.
            table_name: Database table name.
            warn: Warn to use.
        """
        self._table_name = table_name
        columns = {ch.get_name(): ch.get_type_affinity() for ch in self}
        self._backend.new_table(table_name, columns, replace_table, warn)
        self.create_format_view()

    def switch_table(self, table_name):
        """Return switch table result.

        Supports the ``logger`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'switch_table')
        True

        Args:
            table_name: Database table name.

        Returns:
            The switch table result.
        """
        self._table_name = table_name
        return self._backend.switch_table(table_name)

    def copy_table(self, old_table, new_table):
        """Return copy table result.

        Supports the ``logger`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'copy_table')
        True

        Args:
            new_table: New table to use.
            old_table: Old table to use.

        Returns:
            The copy table result.
        """
        return self._backend.copy_table(old_table, new_table)

    def check_format_name(self, format_name):
        """Perform check format name operation.

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'check_format_name')
        True

        Args:
            format_name: Name of the format.

        Raises:
            ChannelNameException: If the channel name is invalid or duplicated.
        """
        if format_name in self.get_all_channel_names():
            raise ChannelNameException(
                'Formatted channel view name:{} conflicts with table column'.format(format_name))

    def create_format_view(self, use_presets=True):
        """Return create format view result.
        Creates and returns a new format view.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'create_format_view')
        True

        Args:
            use_presets: If True, apply saved preset configurations.

        Returns:
            Formatted string representation.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self.get_table_name() is None:
            raise Exception(
                'Table name unspecified!\nCall new_table() or append_table() before log_formats()')
        view_name = '{}_formatted'.format(self.get_table_name())
        self.execute('DROP VIEW IF EXISTS {}'.format(view_name))
        self.execute(
            'DROP VIEW IF EXISTS {}_all'.format(
                self.get_table_name()))
        sql_txt = ''
        for channel in sorted(self.get_all_channels_list(),
                              key=lambda channel: channel.get_name()):
            try:
                # alphabetize? name, units? sorted(channel.get_formats())
                channel_formats = channel.get_formats()
                # Formatting already formatted data or preset strings can cause problems.
                # This check isn't perfect, since somebody can always turn
                # channel formats/presets on after logger creation.
                if channel.get_format() is not None:
                    debug_logging.warning(
                        "Warning: Channel {} SQL format omitted because channel already has an active format ({}).".format(
                            channel.get_name(), channel.get_format()))
                    continue
                if channel.using_presets_read():
                    debug_logging.warning(
                        "Warning: Channel {} SQL format omitted because channel has read presets enabled.".format(
                            channel.get_name()))
                    continue
            except AttributeError:
                # not an integer_channel with formats...
                continue
            except Exception as e:
                debug_logging.warning("{} {}".format(type(e), e))
            # stuffed with (sql_format, units, channel_format) (sql str, units
            # str, format_name str)
            sql_formats = []
            for channel_format in channel_formats:
                sql_format = channel.sql_format(channel_format, use_presets)
                if sql_format is not None:
                    sql_formats.append(
                        (sql_format,
                         clean_sql(
                             channel.get_units(channel_format)),
                            channel_format))
            if len(sql_formats) == 0:
                # make one more attempt to get presets if all formats were
                # non-XML
                sql_format = channel.sql_format(None, use_presets)
                if sql_format is not None:
                    self.check_format_name(
                        '{}_PRESET'.format(
                            channel.get_name()))
                    sql_txt += '{}_PRESET,\n'.format(sql_format)
            elif len(sql_formats) == 1:
                # append _units
                self.check_format_name(
                    '{}_{}'.format(
                        channel.get_name(),
                        sql_formats[0][1]))
                sql_txt += '{}_{},\n'.format(
                    sql_formats[0][0], sql_formats[0][1])
            else:
                if len(set([fmt_tuple[1] for fmt_tuple in sql_formats])) == len(
                        sql_formats):
                    # units make unique names
                    for sql_format in sql_formats:
                        self.check_format_name('{}_{}'.format(
                            channel.get_name(), sql_format[1]))
                        sql_txt += '{}_{},\n'.format(
                            sql_format[0], sql_format[1])
                else:
                    # units are duplicated too; append format name
                    for sql_format in sql_formats:
                        self.check_format_name(
                            '{}_{}_{}'.format(
                                channel.get_name(),
                                sql_format[1],
                                sql_format[2]))
                        sql_txt += '{}_{}_{},\n'.format(
                            sql_format[0], sql_format[1], sql_format[2])
        elapsed_time = "  (strftime('%s',datetime)\n   + strftime('%f',datetime)\n   - strftime('%S',datetime)\n  )\n  - (strftime('%s',(SELECT min(datetime) FROM {table_name}))\n     + strftime('%f',(SELECT min(datetime) FROM {table_name}))\n     - strftime('%S',(SELECT min(datetime) FROM {table_name}))\n    )\n  AS datetime_sec".format(
            # not very efficient and doesn't get added if no presets/formats
            # exist!
            table_name=self.get_table_name())
        if len(sql_txt):
            sql_txt = 'CREATE VIEW {} AS SELECT\n  rowid,\n{},\n{}\nFROM {}'.format(
                view_name, elapsed_time, sql_txt[:-2], self.get_table_name())
            self.execute(sql_txt)
            self.execute(
                'CREATE VIEW {}_all AS SELECT * FROM {} JOIN {}_formatted USING (rowid)'.format(
                    self.get_table_name(),
                    self.get_table_name(),
                    self.get_table_name()))
            return sql_txt

        # constants some day?
        # self.execute('CREATE TABLE IF NOT EXISTS {TABLE_NAME}_CONSTANTS (name TEXT PRIMARY KEY, value REAL')
    def get_database(self):
        """Return the current database.
        Returns the stored database value from the object's internal state.
        Returns the stored database from the object's internal state.

        Returns the stored database from the object's internal state.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'get_database')
        True

        Returns:
            The current database.
        """
        return self._database

    def get_table_name(self):
        """Return the table name.
        Returns the stored table name value from the object's internal state.
        Returns the stored table name from the object's internal state.

        Returns the stored table name from the object's internal state.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'get_table_name')
        True

        Returns:
            The current table name.
        """
        return self._table_name

    def _fetch_channel_data(self, exclusions):
        scan_list = self.get_flat_channel_group('scan_list')
        # only log channels that are readable
        for channel in scan_list.get_all_channels_list():
            if not channel.is_readable():
                scan_list.remove_channel(channel)
        # remove the excluded items from the scan list
        scan_list.remove_channel_list(exclusions)
        channel_data = self.master.read_channel_list(scan_list)
        # add additional database columns
        channel_data['rowid'] = None
        if 'datetime' not in channel_data:
            channel_data['datetime'] = datetime.datetime.now(
                datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        return channel_data

    def log(self, exclusions=None):
        """Measure all non-excluded channels. Channels may be excluded by name, channel_group(instrument), or directly.  Returns a dictionary of what it logged.
        Reads all registered channels, stores results in the database, and
        invokes any registered callbacks.
        Reads all registered channels via the master, inserts the results as a
        new row in the SQLite database, and invokes any registered log
        callbacks. This is the primary data-acquisition entry point.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import master
        >>> hasattr(master, 'stop_threads')
        True

        Args:
            exclusions: List of items to exclude.

        Returns:
            The logged results dictionary.
        """
        if exclusions is None:
            exclusions = []
        self._backend.check_exception()
        data = self._fetch_channel_data(exclusions)
        self._backend.store(data)
        self._previously_logged_data = data
        for (key, value) in data.items():
            if isinstance(value, channel):
                # avoid deep copying channels(pickle error)
                data[key] = value.get_name()
        # Avoid thread contention if callbacks or user script modify dictionary
        # before logger thread gets it processed.
        data = copy.deepcopy(data)
        for callback in self._log_callbacks:
            debug_logging.debug("Logger running log callback %s.", callback)
            callback(data)
        return data

    def check_data_changed(self, data, compare_exclusions=None):
        """Return True if data is different than self._previously_logged_data.

        Shared test between several log_if_changed methods.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'check_data_changed')
        True

        Args:
            compare_exclusions: Compare exclusions to use.
            data: Data to write.

        Returns:
            The check data changed result.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if compare_exclusions is None:
            compare_exclusions = []
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
                if isinstance(item, str):
                    del old_data[item]
                    del new_data[item]
                elif isinstance(item, channel):
                    del old_data[item.get_name()]
                    del new_data[item.get_name()]
                else:
                    raise Exception(
                        'Unknown compare exclusion type: {} {}'.format(
                            type(item), item))
            return old_data != new_data

    def log_if_changed(self, log_exclusions=None, compare_exclusions=None):
        """Like log(), but only stores data to database if data in at least on channel/column has changed.

        log_exclusions is a list of logger channels which will not be read nor stored in the database.
        compare_exclusions is a list of logger channels which will not be used to decide if data has changed but which will be read and stored in the databased if something else changed.
        rowid and datetime are automatically excluded from change comparison.
        returns channel data if logged, else None


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'log_if_changed')
        True

        Args:
            compare_exclusions: Compare exclusions to use.
            log_exclusions: Log exclusions to use.

        Returns:
            The log if changed result.
        """
        if log_exclusions is None:
            log_exclusions = []
        if compare_exclusions is None:
            compare_exclusions = []
        self._backend.check_exception()
        data = self._fetch_channel_data(log_exclusions)
        if self.check_data_changed(data, compare_exclusions):
            self._backend.store(data)
            self._previously_logged_data = data
            # skip callbacks if data unchanged?
            for callback in self._log_callbacks:
                debug_logging.debug(
                    "Logger running log callback %s form log_if_changed.", callback)
                callback(data)
            return data
        else:
            return None

    def log_data(self, data_dictionary, only_if_changed=False):
        """Log previously collected data.

        data_dictionary should have channel name keys.
        set up logger and table using logger.add_data_channels()
        alternately, data_dictionary can be an iterable containing dictionaries, each representing a single row.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'log_data')
        True

        Args:
            data_dictionary: Data dictionary to use.
            only_if_changed: Only if changed to use.

        Returns:
            The log data result.
        """
        self._backend.check_exception()
        try:
            if not only_if_changed or self.check_data_changed(
                    data_dictionary, compare_exclusions=[]):
                # compare_exclusions not currently supported
                data_dictionary['rowid'] = None
                if data_dictionary.get('datetime', None) is None:
                    data_dictionary['datetime'] = datetime.datetime.now(
                        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
                self._backend.store(data_dictionary)
                self._previously_logged_data = data_dictionary
                return data_dictionary
            return None  # skipped duplicate data
        except TypeError:
            # not a mapping type, assume iterable of mapping
            # TODO print or debugg logging?
            print('Interable of mapping type is better logged with log_many() method')
            for row in data_dictionary:
                # try to prevent infinite recursion with malformed data
                assert len(list(row.keys()))
                self.log_data(row)

    def log_kwdata(self, **kwargs):
        """Log previously collected data, but provided as keyword key,value pairs instead of dictionary.

        Captures data for later analysis or replay.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'log_kwdata')
        True

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            The log kwdata result.
        """
        return self.log_data(kwargs, only_if_changed=False)

    def log_many(self, data_iter_of_dictionaries):
        """Perform log many operation.
        Records the many to the log or database.

        Captures data for later analysis or replay.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'log_many')
        True

        Args:
            data_iter_of_dictionaries: Data iter of dictionaries to use.
        """
        self._backend.check_exception()
        # walrus comprehension not yet available in Python 3.7
        logtime = datetime.datetime.now(
            datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        for row in data_iter_of_dictionaries:
            row['rowid'] = None
            if row.get('datetime', None) is None:
                row['datetime'] = logtime
            self._previously_logged_data = row
        self._backend.storemany(data_iter_of_dictionaries)

    def add_data_channels(self, data_dictionary):
        """Prepare logger channel group with fake channels matching data_dictionary keys.

        call before logger.new_table().
        use to log previously collected data in conjunction with logger.log_data()


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'add_data_channels')
        True

        Args:
            data_dictionary: Data dictionary to use.
        """
        assert len(self.get_all_channel_names()) == 0

        def read_disable():
            """Perform read disable operation.

            Reads data from the underlying source and returns it.


            >>> from PyICe.lab_core import logger
            >>> hasattr(logger, 'read_disable')
            True

            Raises:
                Exception: If an unexpected error occurs.
            """
            raise Exception(
                'Attempted to read fake channel designed to be used with logger.log_data()')
        for key in data_dictionary:
            fake_channel = channel(key, read_function=read_disable)
            self.add_channel(fake_channel)

    def add_log_callback(self, log_callback):
        """Adds a read callback. This is a function that will be called any time a channel(s) is read. the callback function should accept one argument: the dictionary of results.

        If it is not important to group results by each batch read, consider adding a callback to an individual channel instead.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'add_log_callback')
        True

        Args:
            log_callback: Log callback to use.
        """
        self._log_callbacks.append(log_callback)

    def remove_log_callback(self, log_callback):
        """Remove a log callback.

        Hooks into the event system so that custom logic runs at the appropriate time.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'remove_log_callback')
        True

        Args:
            log_callback: Log callback to use.
        """
        self._log_callbacks.remove(log_callback)

    def get_master(self):
        """Return the current master.
        Returns the stored master value from the object's internal state.
        Returns the stored master from the object's internal state.

        Returns the stored master from the object's internal state.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'get_master')
        True

        Returns:
            The current master.
        """
        return self.master

    def get_data(self):
        """Return the current data.
        Returns the stored data value from the object's internal state.
        Returns the stored data from the object's internal state.

        Returns the stored data from the object's internal state.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'get_data')
        True

        Returns:
            The current data.
        """
        return sqlite_data(table_name=self.get_table_name(),
                           database_file=self.get_database())

    def query(self, sql_query, *params):
        """Return the query.

        Supports the ``logger`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'query')
        True

        Args:
            *params: Additional positional arguments.
            sql_query: Sql query to use.

        Returns:
            Cursor with query results.
        """
        return self.get_data().query(sql_query, *params)

    def flush(self):
        """Commit pending transactions and block until database thread queue is empty.

        Supports the ``logger`` workflow by performing the described operation.

        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'flush')
        True

        """
        self._backend.sync_threads()

    def set_journal_mode(self, journal_mode='WAL',
                         synchronous='NORMAL', timeout_ms=10000):
        """Configure database connection for more reliable concurrent read/write operations with high data throughput or large data sets.

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


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'set_journal_mode')
        True

        Args:
            journal_mode: Journal mode to use.
            synchronous: Synchronous to use.
            timeout_ms: Timeout ms to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self._backend.execute("PRAGMA locking_mode = NORMAL")
        self._backend.execute("PRAGMA busy_timeout = {}".format(timeout_ms))
        journal_mode = journal_mode.upper()
        if journal_mode not in ["DELETE", "TRUNCATE",
                                "PERSIST", "MEMORY", "WAL", "OFF"]:
            raise Exception(
                'Valid arguments to journal_mode are "DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", and "OFF". See https://www.sqlite.org/pragma.html#pragma_journal_mode')
        self._backend.execute("PRAGMA journal_mode = {}".format(journal_mode))
        if journal_mode == "WAL":
            self._backend.execute("PRAGMA wal_autocheckpoint=100")
        synchronous = synchronous.upper()
        if synchronous not in ["OFF", "NORMAL", "FULL", "EXTRA"]:
            raise Exception(
                'Valid arguments to synchronous are "OFF", "NORMAL", "FULL", and "EXTRA". See https://www.sqlite.org/pragma.html#pragma_synchronous')
        self._backend.execute("PRAGMA synchronous = {}".format(synchronous))

    def optimize(self):
        """Defragment database file, reducing file size and speeding future queries.

        Also re-runs query plan optimizer to speed future queries.
        WARNING: May take a lot time to complete when operating on a large database.
        WARNING: May re-order rowid's

        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'optimize')
        True

        """
        self.execute("VACUUM")
        self.execute("ANALYZE")

    def execute(self, sql_query, *params):
        """Execute arbitrary SQL statements on database.

        Not capable of returning results across thread boundary.
        Useful to set up views, indices, etc


        >>> from PyICe.lab_core import logger
        >>> hasattr(logger, 'execute')
        True

        Args:
            *params: Additional positional arguments.
            sql_query: Sql query to use.
        """
        self._backend.execute(sql_query, *params)


class logger_backend(object):
    """SQLite logging backend that records channel data to a database.

    >>> from PyICe.lab_core import logger_backend
    >>> logger_backend is not None
    True

    """

    def __init__(self, database="data_log.sqlite", use_threads=True):
        """Initialize the logger backend.
        Initializes 8 instance attributes that configure the object's
        behavior.

        Initializes 8 instance attributes that configure the object's behavior.


        >>> from PyICe.lab_core import logger_backend
        >>> logger_backend is not None
        True

        Args:
            database: Path to the SQLite database file.
            use_threads: If True, use a background thread for writes.
        """
        self.table_name = None
        self._use_thread = use_threads
        self._max_lock_time = datetime.timedelta(seconds=10)
        self._thread_exception = None
        self._run = True
        self._stopped = False
        database = os.path.expanduser(
            os.path.expandvars(database))  # resolve env vars + ~
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
            # no effect if DB not in write-ahead log journal mode
            checkpoint_command = "PRAGMA wal_checkpoint(RESTART);"
            try:
                self.conn.execute(checkpoint_command)
            except sqlite3.OperationalError as e:
                debug_logging.warning("Checkpoint failed.")
                debug_logging.warning(
                    "  Specifically, '{}' raised exception '{}'".format(
                        checkpoint_command, e))
            try:
                self.conn.execute("PRAGMA journal_mode=DELETE;")
            except sqlite3.OperationalError as e:
                debug_logging.warning(
                    "Journal mode change failed. Is another app connected to the database file?")
                debug_logging.warning(
                    "  Specific exception raised was: {}".format(e))
            self.conn.close()
        except sqlite3.ProgrammingError as e:
            # can't execute if connection previously closed
            print(e)
        except Exception as e:
            debug_logging.error("Unhandled exception in _close!")
            debug_logging.error("{} {}".format(e, type(e)))

    def sync_threads(self):
        """Perform sync threads operation.

        Brings the cached state into agreement with the authoritative source.

        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'sync_threads')
        True

        """
        if self._use_thread:
            self.storage_queue.put(self._commit)
            self.storage_queue.join()
            self.check_exception()
        else:
            self._commit()

    def check_exception(self):
        """Perform check exception operation.

        Evaluates the condition and raises or returns a diagnostic result.

        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'check_exception')
        True

        """
        self._check_exception()

    def _check_exception(self):
        if self._thread_exception:
            raise self._thread_exception

    def execute(self, sql_query, *params):
        """Not currently capable of returning the query result through the thread queue.

        useful for setting up the database with PRAGMA commands.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'execute')
        True

        Args:
            *params: Additional positional arguments.
            sql_query: Sql query to use.
        """
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

    def _connect_db(self, database):
        self.db = database
        # isolation_level of None means turn off Python sqlite3 module's
        # automatic BEGIN and COMMIT: we'll handle transactions ourselves.
        self.conn = sqlite3.connect(self.db, isolation_level=None)
        # self.cur = self.conn.cursor()

    def _db_thread(self):
        self.lock_time = None
        self._stopped = False  # redundant but defensive
        while self._run:
            _dbconn = getattr(self, "conn", None)  # noqa: F841
            if self.lock_time is not None and (datetime.datetime.now(
                    datetime.timezone.utc) - self.lock_time) > self._max_lock_time:
                self._commit()
                self.lock_time = None
                # print 'max lock timed out'
            try:
                function = self.storage_queue.get(block=False)
            except queue.Empty:
                if self.lock_time is not None:
                    try:
                        self.conn.commit()  # not self._commit to avoid infinite retry
                        # no effect if DB not in write-ahead log journal mode
                        checkpoint_command = "PRAGMA wal_checkpoint(PASSIVE);"
                        try:
                            self.conn.execute(checkpoint_command)
                        except sqlite3.OperationalError as e:
                            debug_logging.warning(
                                "{} raised exception {}".format(
                                    checkpoint_command, e))
                    except sqlite3.OperationalError:
                        debug_logging.warning(
                            "Opportunistic commit failed. Not retrying.")
                    else:
                        self.lock_time = None
                function = self.storage_queue.get(block=True)
            finally:
                try:
                    if self.lock_time is None:
                        self.lock_time = datetime.datetime.now(datetime.timezone.utc)
                    function()
                except Exception as e:
                    print((traceback.format_exc()))
                    self._thread_exception = e
                    raise e
                finally:
                    self.storage_queue.task_done()
        self._stopped = True

    def store(self, data):
        """Run the store step.

        Persists the current state or data to durable storage.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'store')
        True

        Args:
            data: Data to write.
        """
        if self._use_thread:
            self.storage_queue.put(lambda: self._store(data))
        else:
            self._store(data)
            self.conn.commit()

    def storemany(self, data):
        """Run the storemany step.

        Persists the current state or data to durable storage.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'storemany')
        True

        Args:
            data: Data to write.
        """
        if self._use_thread:
            self.storage_queue.put(lambda: self._storemany(data))
        else:
            self._storemany(data)
            self.conn.commit()

    def _new_table(self, table_name, columns, replace_table=False, warn=False):
        """Create new table in the sqlite database with a column for each channel.

        replace any existing table with the same name (delete data!).


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, '_new_table')
        True

        Args:
            columns: Columns to use.
            replace_table: Replace table to use.
            table_name: Database table name.
            warn: Warn to use.

        Raises:
            e: Re-raised after cleanup.
        """
        table_name = str(table_name).replace(" ", "_")

        try:
            self._create_table(table_name, columns)
            self._commit()
        except sqlite3.OperationalError as e:
            if isinstance(replace_table,
                          str) and replace_table.lower() == 'copy':
                try:
                    # try to name copied table for when it was created, not
                    # time now.
                    try:
                        table_date = self.conn.execute(
                            'SELECT DATETIME from {} ORDER BY DATETIME ASC LIMIT 1'.format(table_name)).fetchone()[0]
                        table_date = datetime.datetime.strptime(
                            table_date, '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y_%m_%dT%H_%M_%SZ')
                    except TypeError:
                        debug_logging.warning(
                            "WARNING: Failed to extract datetime information from table {}. Reverting to current time".format(
                                self.table_name))
                        table_date = datetime.datetime.now(
                            datetime.timezone.utc).strftime('%Y_%m_%dT%H_%M_%SZ')
                    self._copy_table(
                        self.table_name, '{}_{}'.format(
                            table_name, table_date))
                    self.conn.execute("DROP TABLE {}".format(self.table_name))
                    self._commit()
                except sqlite3.OperationalError as e:
                    debug_logging.error(e)
                    debug_logging.error(
                        "Table not copied (may not exist): {}".format(
                            self.table_name))
                self._create_table(table_name, columns)
                self._commit()
            elif replace_table:
                try:
                    self.conn.execute("DROP TABLE {}".format(self.table_name))
                    self._commit()
                except sqlite3.OperationalError as e:
                    debug_logging.error(e)
                    debug_logging.error(
                        "Table not dropped (may not exist): {}".format(
                            self.table_name))
                self._create_table(table_name, columns)
                self._commit()
            else:
                if warn:
                    debug_logging.warning(
                        'Table name {} creation failed.  Table probably exists. Rename table, change table name argument, or call with replace_table argument=True'.format(
                            self.table_name))
                else:
                    raise e

    def _create_table(self, table_name, columns):
        """Create the actual sql table and commit to database.  Called by new_sweep_replace() (and new_sweep()?).
        Internal implementation detail; see the public API for usage.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, '_create_table')
        True

        Args:
            columns: Columns to use.
            table_name: Database table name.
        """
        self.table_name = table_name
        self.columns = list(columns)
        self.columns.sort()
        txt = "CREATE TABLE " + self.table_name + \
            " ( rowid INTEGER PRIMARY KEY, datetime DATETIME, "
        for column in self.columns:
            if column == 'datetime':
                continue
            try:
                txt += f'"{column}" {columns[column]}, '
            except TypeError as e:
                # It's the legacy list. But. . .why?
                txt += f'"{column}" NUMERIC, '
                print(e)  # The world needs to know.
                print(
                    "Contact pyice-developers@analog.com. Or file a bug report at jira.analog.com/projects/PYICE")
        txt = txt[:-2]
        txt += " )"
        self.conn.execute(txt)
        self._commit()

    @classmethod
    def db_clean(cls, column_data):
        """Help database to store lists, dictionaries and any other future datatype that doesn't fit natively.

        Persists the current state or data to durable storage.


        >>> from PyICe.lab_core import logger_backend
        >>> callable(getattr(logger_backend, 'db_clean', None))
        True

        Args:
            column_data: The data to clean for database storage.

        Returns:
            Cleaned data suitable for SQLite storage.
        """
        # perhaps better implemented using sqlite.register_adapter?
        # https://docs.python.org/2/library/sqlite3.html#registering-an-adapter-callable
        # https://docs.python.org/2/library/sqlite3.html#sqlite3.register_adapter
        if isinstance(column_data, list):
            return str(column_data)
        elif isinstance(column_data, dict):
            return str(column_data)
        elif isinstance(column_data, tuple):
            return str(column_data)
        elif not numpy_missing and isinstance(column_data, ndarray):
            dtype_header = bytearray(
                column_data.dtype.str,
                encoding='latin1')  # ex '<d' or '<i4'
            dtype_header.insert(
                0, len(
                    column_data.dtype.str))  # ex \x02 or \x03
            bytes_coldata = column_data.tobytes()
            return dtype_header + bytes_coldata
        elif isinstance(column_data, ChannelReadException):
            return None
        elif isinstance(column_data, channel):
            return str(column_data)
        return column_data

    def _store(self, data, num=0):
        """Match data dictionary keys to table column names and commit new row to table.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, '_store')
        True

        Args:
            data: Data to write.
            num: Count or number.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self.table_name is None:
            raise Exception("Need to create a table before logging")
        if len(data) <= 999:
            # SQLITE_MAX_VARIABLE_NUMBER defaults to 999
            q = ("?," * len(data))[:-1]
            values = tuple([self.db_clean(column)
                           for column in list(data.values())])
            cursor = self.conn.cursor()
            sql = "INSERT INTO {} {} VALUES ({})".format(
                self.table_name, tuple(data.keys()), q)
            try:
                cursor.execute(sql, values)
                data['rowid'] = cursor.execute(
                    'SELECT last_insert_rowid() FROM {}'.format(
                        self.table_name)).fetchone()[0]
            except sqlite3.OperationalError as e:
                if num > 2:
                    debug_logging.warning(data)
                    debug_logging.warning(e)
                    debug_logging.warning(
                        "Try {} failed. Trying again...".format(num))
                time.sleep(0.01)
                self._store(data, num=num + 1)  # keep trying forever
        else:
            # SQLITE_MAX_COLUMN defaults to 2000
            data_cp = data.copy()  # don't delete rowid from original dict
            try:
                del data_cp['rowid']
            except KeyError:
                pass
            q = ("?," * 999)[:-1]
            values = tuple([self.db_clean(column)
                           for column in list(data_cp.values())[:999]])
            sql = "INSERT INTO {} {} VALUES ({})".format(
                self.table_name, tuple(list(data_cp.keys())[:999]), q)
            try:
                self.conn.execute(sql, values)
            except sqlite3.OperationalError as e:
                if num > 2:
                    debug_logging.warning(data_cp)
                    debug_logging.warning(e)
                    debug_logging.warning(
                        "Try {} failed. Trying again...".format(num))
                time.sleep(0.01)
                self._store(data, num=num + 1)  # keep trying forever
            cursor = self.conn.execute(
                'SELECT last_insert_rowid() FROM {}'.format(
                    self.table_name))
            data['rowid'] = cursor.fetchone()[0]
            # data['rowid'] = self.cur.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name)).fetchone()[0]
            assignments = ', '.join(["'{}' = ?".format(k)
                                    for k in list(data_cp.keys())[999:]])
            values = tuple([self.db_clean(column)
                           for column in list(data_cp.values())[999:]])
            sql = "UPDATE {} SET {} WHERE rowid == {}".format(
                self.table_name, assignments, data['rowid'])
            while True:
                try:
                    self.conn.execute(sql, values)
                    break
                except sqlite3.OperationalError as e:
                    if num > 2:
                        debug_logging.warning(data_cp)
                        debug_logging.warning(e)
                        debug_logging.warning(
                            "Try {} failed. Trying again...".format(num))
                    time.sleep(0.01)
                    num += 1

    def _storemany(self, data_iter, num=0):
        """Match data dictionary keys of each iter element to table column names and commit multiple new rows to table.

        all elements of iterable must have same dimention and type
        column count above 999 not currently supported


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, '_storemany')
        True

        Args:
            data_iter: Data iter to use.
            num: Count or number.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self.table_name is None:
            raise Exception("Need to create a table before logging")
        set_of_data_lengths = {len(row) for row in data_iter}
        assert len(
            set_of_data_lengths) == 1, f'storemany iterable element has items of disparate dimension {set_of_data_lengths}'
        example_row = (next(iter(data_iter)))
        q = ("?," * len(example_row))[:-1]
        values = tuple(tuple(self.db_clean(column)
                       for column in row.values()) for row in data_iter)
        cursor = self.conn.cursor()
        sql = "INSERT INTO {} {} VALUES ({})".format(
            self.table_name, tuple(example_row.keys()), q)
        try:
            cursor.executemany(sql, values)
            # data['rowid'] = cursor.execute('SELECT last_insert_rowid() FROM {}'.format(self.table_name)).fetchone()[0]
            cursor.close()  # rapid garbage collection might speed things up
        except sqlite3.OperationalError as e:
            if num > 2:
                debug_logging.warning(data_iter)
                debug_logging.warning(e)
                debug_logging.warning(
                    "Try {} failed. Trying again...".format(num))
            time.sleep(0.01)
            self._storemany(data_iter, num=num + 1)  # keep trying forever

    def copy_table(self, old_table, new_table):
        """Perform copy table operation.

        Supports the ``logger_backend`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'copy_table')
        True

        Args:
            new_table: New table to use.
            old_table: Old table to use.
        """
        self._check_name(new_table)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(
                lambda: self._copy_table(
                    old_table, new_table))
        else:
            self._copy_table(old_table, new_table)
        self.sync_threads()

    def _copy_table(self, old_table, new_table):
        # inspecting sql create statements allows type preservation. Otherwise,
        # it gets clobbered. DATETIME specifically doesn't get copied
        # correctly.
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE tbl_name=='{}'".format(old_table))
        sql_create = cursor.fetchone()[0]
        new_sql, count = re.subn(
            r"^CREATE TABLE {old_table} \( rowid INTEGER PRIMARY KEY, datetime DATETIME, ".format(
                old_table=old_table), "CREATE TABLE {new_table} ( rowid INTEGER PRIMARY KEY, datetime DATETIME, ".format(
                new_table=new_table), sql_create, flags=re.DOTALL)
        assert count == 1
        self._execute(new_sql)
        self._execute(
            "INSERT INTO {} SELECT * FROM {}".format(new_table, old_table))

        # look for format view to copy also
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type=='view' AND tbl_name=='{}_formatted'".format(old_table))
        sql_format = cursor.fetchone()
        if sql_format is not None:
            sql_txt, count = re.subn(
                "^CREATE VIEW (.*?) AS SELECT\n  (.*)\nFROM (.*?)$", "CREATE VIEW {new_table}_formatted AS SELECT\n  \\2\nFROM {new_table}".format(
                    new_table=new_table), sql_format[0], flags=re.DOTALL)
            assert count == 1
            # now rewrite datetime_sec view to point to new view name
            sql_txt, count = re.subn(
                r"\(SELECT min\(datetime\) FROM (.*?)\)", "(SELECT min(datetime) FROM {new_table})".format(
                    new_table=new_table), sql_txt, flags=re.DOTALL)
            assert count == 3
            self._execute(sql_txt)
        # now look for the joined view to copy
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type=='view' AND tbl_name=='{}_all'".format(old_table))
        sql_format = cursor.fetchone()
        if sql_format is not None:
            sql_txt, count = re.subn(r"^CREATE VIEW (.*?) AS SELECT \* FROM (.*?) JOIN (.*?) USING \(rowid\)$",
                                     "CREATE VIEW {new_table}_all AS SELECT * FROM {new_table} JOIN {new_table}_formatted USING (rowid)".format(new_table=new_table), sql_format[0], flags=re.DOTALL)
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

    def switch_table(self, table_name):
        """Perform switch table operation.

        Supports the ``logger_backend`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'switch_table')
        True

        Args:
            table_name: Database table name.
        """
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(lambda: self._switch_table(table_name))
        else:
            self._switch_table(table_name)
        self.sync_threads()

    def _switch_table(self, table_name):
        self.table_name = table_name

    def append_table(self, table_name, columns):
        """Perform append table operation.

        Supports the ``logger_backend`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'append_table')
        True

        Args:
            columns: Columns to use.
            table_name: Database table name.
        """
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(
                lambda: self._append_table(
                    table_name, columns))
        else:
            self._append_table(table_name, columns)
        self.sync_threads()

    def _append_table(self, table_name, columns):
        try:
            self._new_table(
                table_name,
                columns,
                replace_table=False,
                warn=False)
            self._commit()
        except sqlite3.OperationalError:
            pass
        self._switch_table(table_name)
        for column in columns:
            try:
                self.conn.execute(
                    "ALTER TABLE {} ADD {} NUMERIC".format(
                        self.table_name, column))
                self._commit()
            except sqlite3.OperationalError:
                pass
            else:
                debug_logging.info(
                    "Added column: {} to table: {}".format(
                        column, self.table_name))

    def _check_name(self, name):
        if not re.match("[_A-Za-z][_a-zA-Z0-9]*$", name):
            raise Exception('Bad Table Name "{}"'.format(name))

    def new_table(self, table_name, columns, replace_table=False, warn=False):
        """Perform new table operation.

        Supports the ``logger_backend`` workflow by performing the described operation.


        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'new_table')
        True

        Args:
            columns: Columns to use.
            replace_table: Replace table to use.
            table_name: Database table name.
            warn: Warn to use.
        """
        self._check_name(table_name)
        self._check_exception()
        if self._use_thread:
            self.storage_queue.put(
                lambda: self._new_table(
                    table_name,
                    columns,
                    replace_table,
                    warn))
        else:
            self._new_table(table_name, columns, replace_table, warn)
        self.sync_threads()

    def stop(self):
        """Run the stop step.

        Supports the ``logger_backend`` workflow by performing the described operation.

        >>> from PyICe.lab_core import logger_backend
        >>> hasattr(logger_backend, 'stop')
        True

        """
        if self._use_thread:
            if not self._stopped:
                self.storage_queue.put(self._stop)
                self.storage_queue.join()
        else:
            # non-threaded case
            if not self._stopped:
                self._stop()

    def _stop(self):
        try:
            self._commit()
        except sqlite3.ProgrammingError as e:
            # can't commit if connection previously closed
            debug_logging.error(e)
        except Exception as e:
            debug_logging.error("Unhandled exception in _stop!")
            debug_logging.error("{} {}".format(type(e), e))
        finally:
            self._close()
            self._run = False
            self._stopped = True


if __name__ == "__main__":  # pragma: no cover
    def print_it(x):
        """Perform print it operation.

        Performs the described operation on the object's internal state.


        >>> from PyICe.lab_core import print_it
        >>> callable(print_it)
        True

        Args:
            x: X-axis value.
        """
        print(x)
    # test of threaded delegation
    lb = master()
    if not lb.attach(address='localhost'):
        print("creating fake channels")
        # make 4 communication nodes, a-d, a and b are root level interfaces, b
        # is not thread safe, c and d are downstream of b
        ia = lb.get_dummy_interface(name='a')
        ia.set_com_node_thread_safe(True)
        ib = lb.get_dummy_interface(name='b')
        ib.set_com_node_thread_safe(True)
        ic = lb.get_dummy_interface(parent=ib, name='c')
        id = lb.get_dummy_interface(parent=ib, name='d')

        # create some dummy channels using these interfaces
        ch1_ia = channel('ch1_ia', read_function=lambda: time.sleep(0.3))
        ch1_ia.add_interface(ia)
        ch2_ic = channel('ch2_ic', read_function=lambda: time.sleep(0.1))
        ch2_ic.add_interface(ic)
        ch3_id = channel('ch3_id', read_function=lambda: time.sleep(0.1))
        ch3_id.add_interface(id)
        ch4_id = channel('ch4_id', read_function=lambda: time.sleep(0.1))
        # ch4_id.set_delegator(ch3_id)
        ch4_id.add_interface(id)

        lb._add_channel(ch1_ia)
        lb._add_channel(ch2_ic)
        lb._add_channel(ch3_id)
        lb._add_channel(ch4_id)
        lb.add_channel_dummy('dummy')
        lb.write('dummy', "dummydata")
        lb.add_channel_virtual(
            'virtual_print',
            write_function=lambda x: print_it(x))
        print("new_logger")
        lb.gui()
        logger = logger(lb)
        logger.new_table("test_table", replace_table=True)
        logger.set_journal_mode()
        logger.log()
        logger.log()
        # lb.background_gui()
        # lb.serve(address='localhost')
        print("done")
    else:
        print("did not create any channels")
        tstart = time.time()
        data = lb.read_all_channels()
        print(("read took {}".format(time.time() - tstart)))
        print(data)

        lgr = logger(lb)
        lgr.new_table('test', replace_table=True)
        lgr.log()
        lgr.log()

        # lgr.gui()

        # lb.gui() # pra
