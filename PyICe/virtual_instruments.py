"""Virtual instruments module.

Examples:
    >>> from PyICe import virtual_instruments
    >>> d = virtual_instruments.dummy()
    >>> ch = d.add_channel_write('vout')
"""
from .lab_core import *  # noqa: F403
from PyICe.lab_utils.str2num import str2num
from PyICe.lab_instruments.temperature_chamber import temperature_chamber
import PyICe.lab_utils.delay_loop
from PyICe.lab_utils.eng_string import eng_string
from PyICe.lab_utils.threaded_writer import threaded_writer
import random
import types
import math

'''
Virtual Instruments
-------------------
dummy
  Doesn't do anything. Use to replace missing equipment in a testbench, etc.
instrument_humanoid
  Notification helper to put human control of a manual instrument into an otherwise automated measurement.
expect
  Virtual instrument to check that reading is specified tolerance of expected result
delay_loop
  Instrument wrapper for lab_utils delay_loop enables logging of delay diagnostic vairables.
clipboard
  Store and retrieve data to/from windows/linux/osx clipboard.
accumulator
  Accumulator Virtual Instrument
timer
  Timer Virtual Instrument
integrator
  Integrator Virtual Instrument
differencer
  Differencer Virtual Instrument
differentiator
  Differentiator Virtual Instrument
servo
  Servo controller, for kelvins etc
servo_group
  Group Servo Control, servos multiple servos into regulation
ramp_to
  Move forcing channels incrementally to control overshoot
threshold_finder
  Automatically find thresholds and hysteresis
calibrator
  Remap write values through two-point or univariate transform
digital_analog_io
  Digital input/output using analog measure/force channels referenced to a domain supply.
vector_to_scalar_converter
  Reduce vector channel data to scalar data using supplied reduction function. Ex. avg, std-dev, etc.
smart_battery_emulator
  A pair of threaded writers to output smart battery commands to a smart-battery charger
aggregator
  Combines multiple, less capable channels into a single channel of great renown.
dummy_quantum_twin
  Creates dummy channels that opportunistically mirror the state of their live counterparts. Useful for logging DUT state after shutdown, among other things
virtual_oven
  Creates shell of an oven-like instrument. Useful for tests that require oven channels but lack an oven.
'''
class dummy(instrument):
    """Doesn't do anything. Use to replace missing equipment in a testbench, etc.

    >>> d = dummy()
    >>> ch = d.add_channel_write('vout')
    >>> _ = ch.write(3.3)
    >>> d.set_random_read(False)
    >>> rd = d.add_channel_read('vin')
    >>> rd.read() is None
    True
    """
    _add_channel_is_writeable_def = None

    def __init__(self, *args, **kwargs):
        """Match calling convention of other instruments. Accept interface, etc type positional and keyword args.
        Stores configuration in ``_base_name``, ``init_args``, ``init_kwagrs``
        for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import dummy
        >>> obj = dummy()
        >>> isinstance(obj, dummy)
        True

        Args:
            **kwargs: Additional keyword arguments.
            *args: Additional positional arguments.
        """
        # keep init arguments just in case for future reference.
        self.init_args = args
        self.init_kwagrs = kwargs

        self.set_verbose(False)
        self.set_random_read(True)
        self.set_add_channel_is_writeable(self._add_channel_is_writeable_def)

        if self._add_channel_is_writeable is None:
            self._base_name = "Dummy Virtual Instrument"
        elif self._add_channel_is_writeable:
            self._base_name = "Dummy Write Virtual Instrument"
        else:
            self._base_name = "Dummy Read Virtual Instrument"

        instrument.__init__(self, self._base_name)

    def set_verbose(self, verbose=True):
        """Enable or disable debug output for dummy channel reads and writes.

        When enabled, each read and write operation on dummy channels prints
        a diagnostic message to stdout, useful for tracing test-bench behavior.


        >>> from PyICe.virtual_instruments import dummy
        >>> d = dummy()
        >>> d.set_verbose(True)
        >>> d._verbose
        True
        >>> d.set_verbose(False)
        >>> d._verbose
        False

        Args:
            verbose: If True, print debug output on each channel operation.
        """
        self._verbose = verbose

    def set_add_channel_is_writeable(self, add_channel_is_writeable=None):
        """Configure the default writeability of channels created via ``add_channel()``.

        Controls whether the generic ``add_channel()`` method creates read-only
        or writeable channels. Has no effect on ``add_channel_read()`` or
        ``add_channel_write()``, which are always explicit.


        >>> from PyICe.virtual_instruments import dummy
        >>> hasattr(dummy, 'set_add_channel_is_writeable')
        True

        Args:
            add_channel_is_writeable: If True, ``add_channel()`` creates writeable
                channels; if False, read-only; if None, ``add_channel()`` is disabled.
        """
        self._add_channel_is_writeable = add_channel_is_writeable

    def set_random_read(self, channel_read_returns_random=True):
        """Enable or disable random return values from dummy read channels.

        When enabled, reads return random values (uniform for first read,
        Gaussian-correlated with the previous value thereafter). When disabled,
        reads return None.


        >>> from PyICe.virtual_instruments import dummy
        >>> d = dummy()
        >>> d.set_random_read(False)
        >>> d._random_read
        False
        >>> d.set_random_read(True)
        >>> d._random_read
        True

        Args:
            channel_read_returns_random: If True, reads return random numeric
                values; if False, reads return None.
        """
        self._random_read = channel_read_returns_random

    def add_channel_write(self, channel_name, *args, **kwargs):
        """Create a writeable do-nothing channel that silently accepts values.

        Use this to stand in for a real instrument's write channel during
        bench-top development or offline testing. Pass ``integer_size`` in
        *kwargs* to create an ``integer_channel`` with auto-generated presets.


        >>> from PyICe.virtual_instruments import dummy
        >>> d = dummy()
        >>> ch = d.add_channel_write("vout")
        >>> ch.write(3.3)
        3.3
        >>> ch.read()
        3.3

        Args:
            channel_name: Name for the new channel.
            *args: Additional positional arguments stored as channel attributes
                for compatibility with real instrument signatures.
            **kwargs: Additional keyword arguments. ``integer_size`` (int)
                creates an integer channel of the given bit width.

        Returns:
            The newly created and registered dummy write channel.
        """
        if "integer_size" in kwargs:
            new_channel = integer_channel(
                channel_name, write_function=lambda value: self._write(
                    channel_name, value), size=kwargs["integer_size"])

            def _unformat_method_patch(self, string, format, use_presets):
                try:
                    return integer_channel.unformat(
                        self, string, format, use_presets)
                except ValueError:
                    # something not right with dummy setup. Probably missing
                    # preset!
                    enumerated_values = set(self.get_presets_dict().values())
                    possible_values = set(
                        range(
                            self.get_min_write_limit(),
                            self.get_max_write_limit() + 1))
                    available_values = possible_values - enumerated_values
                    try:
                        dummy_preset_val = available_values.pop()
                    except KeyError:
                        # ran out of presets. Improvise...
                        dummy_preset_val = 0  # random.choice?
                    self.add_preset(
                        preset_name=string,
                        preset_value=dummy_preset_val,
                        preset_description='Dummy Channel Automagic Preset (BOGUS!)')
                    print(
                        f'WARNING: Dummy channel creating dummy preset after write exception. {string}={dummy_preset_val}.')
                    return self.unformat(string, format, use_presets)
            new_channel.unformat = types.MethodType(
                _unformat_method_patch, new_channel)
        else:
            new_channel = channel(
                channel_name,
                write_function=lambda value: self._write(
                    channel_name,
                    value))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_write.__doc__)
        new_channel.set_attribute('dummy_args', args)
        new_channel.set_attribute('dummy_kwargs', kwargs)
        if self._verbose:
            print(f"Creating dummy write channel {channel_name}.")
        return self._add_channel(new_channel)

    def _write(self, channel_name, value):
        if self._verbose:
            print(f"Dummy write channel {channel_name} to {value}.")

    def add_channel_read(self, channel_name, *args, **kwargs):
        """Create a read-only dummy channel returning random or None values.

        Use this to stand in for a real instrument's read channel. The returned
        value depends on ``set_random_read()``: either a random number or None.
        Pass ``integer_size`` in *kwargs* for an ``integer_channel``.


        >>> from PyICe.virtual_instruments import dummy
        >>> d = dummy()
        >>> d.set_random_read(False)
        >>> ch = d.add_channel_read("vin")
        >>> ch.read() is None
        True

        Args:
            channel_name: Name for the new channel.
            *args: Additional positional arguments stored as channel attributes
                for compatibility with real instrument signatures.
            **kwargs: Additional keyword arguments. ``integer_size`` (int)
                creates an integer channel of the given bit width.

        Returns:
            The newly created and registered dummy read channel.
        """
        if "integer_size" in kwargs:
            new_channel = integer_channel(
                channel_name, size=kwargs["integer_size"])
            # delay read function to include self reference
            new_channel._read = lambda: self._read(new_channel)
        else:
            new_channel = channel(channel_name)
            # delay read function to include self reference
            new_channel._read = lambda: self._read(new_channel)
        # Undo dummy channel assumed writability
        new_channel.set_write_access(False)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_read.__doc__)
        new_channel.set_attribute('dummy_args', args)
        new_channel.set_attribute('dummy_kwargs', kwargs)
        if self._verbose:
            print(f"Creating dummy read channel {channel_name}.")
        return self._add_channel(new_channel)

    def _read(self, channel):
        if self._random_read:
            if isinstance(channel, integer_channel):
                # Problematic with formats passing real values into range?
                value = random.randint(
                    channel.get_min_write_limit(),
                    channel.get_max_write_limit())
            elif channel._previous_value is None:
                value = random.random()  # [0.0, 1.0)
            else:
                value = random.gauss(
                    mu=channel._previous_value,
                    sigma=0.1)  # auto-correlate samples
        else:
            value = None
        if self._verbose:
            print(f"Dummy read {value} from channel {channel.get_name()}.")
        return value

    def add_channel(self, channel_name, *args, **kwargs):
        """Create a channel whose read/write mode is determined by ``set_add_channel_is_writeable()``.

        Mirrors the generic ``add_channel()`` signature of real instruments so
        a ``dummy`` instance can be used as a drop-in replacement.


        >>> from PyICe.virtual_instruments import dummy
        >>> d = dummy()
        >>> d.set_add_channel_is_writeable(False)
        >>> ch = d.add_channel("vin")
        >>> ch.get_name()
        'vin'

        Args:
            channel_name: Name for the new channel.
            *args: Additional positional arguments forwarded to the underlying
                ``add_channel_read`` or ``add_channel_write`` call.
            **kwargs: Additional keyword arguments forwarded to the underlying
                ``add_channel_read`` or ``add_channel_write`` call.

        Returns:
            The newly created and registered channel (read-only or writeable).
        """
        if self._add_channel_is_writeable:
            new_channel = self.add_channel_write(channel_name, *args, **kwargs)
        else:
            new_channel = self.add_channel_read(channel_name, *args, **kwargs)
        return new_channel


class dummy_read(dummy):
    """Dummy instrument with add_channel method defaulted to read-only.

    >>> from PyICe.virtual_instruments import dummy_read
    >>> dummy_read is not None
    True

    """
    _add_channel_is_writeable_def = False


class dummy_write(dummy):
    """Dummy instrument with add_channel method defaulted to writeable.

    >>> from PyICe.virtual_instruments import dummy_write
    >>> dummy_write is not None
    True

    """
    _add_channel_is_writeable_def = True


class instrument_humanoid(instrument, delegator):
    """Notification helper to put human control of a manual instrument into an otherwise automated measurement.

    >>> from PyICe.virtual_instruments import instrument_humanoid
    >>> instrument_humanoid is not None
    True

    """

    def __init__(self, notification_function=None):
        """Notification will be sent to notification_function when a write occurs to any channel in this instrument.  The function should take a single string argument and deliver it to the user as appropriate (sms, email, etc).

        Hint: Use a lambda function to include a subject line in the email:
        from PyICe.lab_utils.communications import email
        myemail = email(destination='myemail@mycompany.com', smtp_server='smtp.example.com:25', sender='noreply@example.com')
        notification_function=lambda msg: myemail.send(msg,subject="Lab requires attention!")
        If notification_function is None, messages will only be sent to the terminal.
        

        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> obj = instrument_humanoid('test')
        >>> isinstance(obj, instrument_humanoid)
        True

          Args:
            notification_function: Notification function to use.
        """
        self._base_name = 'Humanoid Virtual Instrument'
        delegator.__init__(self)
        instrument.__init__(
            self,
            "manual instrument interface notifying via {}".format(notification_function))
        self._base_name = 'Human Feedback'
        self.notification_functions = []
        if notification_function is not None:
            self.add_notification_function(notification_function)
        self.enable_notifications = True
        self.set_write_block_function()
        self.set_read_input_function()

    def add_notification_function(self, notification_function):
        """Add additional notification function to instrument.  Ex email and SMS.

        Notification will be sent to notification_function when a write occurs to any channel in this instrument.  The function should take a single string argument and deliver it to the user as appropriate (sms, email, etc).
        Hint: Use a lambda function to include a subject line in the email:
        from PyICe.lab_utils.communications import email
        myemail = email(destination='myemail@mycompany.com', smtp_server='smtp.example.com:25', sender='noreply@example.com')
        notification_function=lambda msg: myemail.send(msg,subject="Lab requires attention!")
        

        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'add_notification_function')
        True

        Args:
            notification_function: Notification function to use.
        """
        self.notification_functions.append(notification_function)

    def add_channel_notification_enable(self, channel_name):
        """Hook to temporarily suspend notifications, ex for initial setup.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'add_channel_notification_enable')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              write_function=self.set_notification_enable)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_notification_enable.__doc__)
        return self._add_channel(new_channel)

    def set_notification_enable(self, enabled):
        """Non-channel hook to enable/disable notifications.
        Updates the notification enable in the object's internal state.

        Updates the notification enable in the object's internal state.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'set_notification_enable')
        True

        Args:
            enabled: Enabled to use.
        """
        if enabled:
            self.enable_notifications = True
        else:
            self.enable_notifications = False

    def set_write_block_function(self, fn=None):
        """Replace input() method with alternative way to proceed. IE email or button press.
        Updates the write block function in the object's internal state.

        Updates the write block function in the object's internal state.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'set_write_block_function')
        True

        Args:
            fn: Callable function.
        """
        if fn is None:
            self._write_block = lambda: input(
                'Then press any key to continue.')
        else:
            self._write_block = fn

    def set_read_input_function(self, fn=None):
        """Replace input() prompt with alternative way to supply read values.

        fn should accept a prompt string and return the user's response string.

        >>> h = instrument_humanoid()
        >>> h.set_write_block_function(lambda: None)
        >>> values = iter(['3.3', '25.0'])
        >>> h.set_read_input_function(lambda prompt: next(values))
        >>> ch = h.add_channel_read('temperature')
        >>> ch.read()
        3.3
        >>> ch.read()
        25.0

        Args:
            fn: Callable function.
        """
        if fn is None:
            self._read_input = input
        else:
            self._read_input = fn

    def _ch_block(self, ch):
        print(f'Then toggle {ch.get_name()} to continue.')
        while ch.read():
            # wait for low
            time.sleep(0.01)
        while not ch.read():
            # wait for high
            time.sleep(0.01)
        while ch.read():
            # wait for low
            time.sleep(0.01)
        print(f'Successfully toggled {ch.get_name()}. Moving right along.')

    def set_write_block_channel(self, ch):
        """Wait for channel value to toggle high then low before proceeding.
        Updates the write block channel in the object's internal state.

        Updates the write block channel in the object's internal state.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'set_write_block_channel')
        True

        Args:
            ch: Channel number or channel object.
        """
        self._write_block = lambda ch=ch: self._ch_block(ch)

    def add_channel_write(self, channel_name):
        """Add new channel named channel_name.  Writes to channel_name will send a notification using notification_function and will block until the user acknowledges (in the terminal) that they have intervened as appropriate.

        Useful for including manual forcing instruments in an otherwise automated setup.
        To set delay after changing channel, use set_write_delay() method of returned channel.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'add_channel_write')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            write_function=lambda value: self._write(
                channel_name,
                value))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_write.__doc__)
        return self._add_channel(new_channel)

    def _write(self, channel_name, value):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = 'Please modify channel: {} to value: {} now. ({})'.format(
            channel_name, value, now)
        if self.enable_notifications:
            for notification_function in self.notification_functions:
                notification_function(msg)
        print(msg)
        self._write_block()  # args???

    def add_channel_read(self, channel_name, integer_size=None):
        """Add new channel named channel_name.  Reads from channel_name will send a notification using notification_function and will prompt for input.

        Useful for including manual measurement instruments in an otherwise automated setup.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'add_channel_read')
        True

        Args:
            channel_name: Name for the new channel.
            integer_size: Integer size to use.

        Returns:
            The newly created channel object.
        """
        if integer_size is not None:
            new_channel = integer_channel(channel_name, size=integer_size)
            # delay read function to include self reference
            new_channel._read = lambda: self._read(new_channel)
        else:
            new_channel = channel(channel_name)
            # delay read function to include self reference
            new_channel._read = lambda: self._read(new_channel)
        # Undo dummy channel assumed writability
        new_channel.set_write_access(False)
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_read.__doc__)
        return self._add_channel(new_channel)

    def _read(self, channel):
        value = self._read_input(
            'Please input read value for channel {}:  '.format(
                channel.get_name()))
        if value == '':
            # probably a typo. Try again....
            value = self._read(channel)
        try:
            value = channel.format_write(value)
        except AttributeError:
            # non-integer channel has no formats nor presets
            value = str2num(value, except_on_error=False)
        return value

    def read_delegated_channel_list(self, channels):
        """Private.

        Reads data from the underlying source and returns it.


        >>> from PyICe.virtual_instruments import instrument_humanoid
        >>> hasattr(instrument_humanoid, 'read_delegated_channel_list')
        True

        Args:
            channels: List of channel objects.

        Returns:
            The value read from the device or channel.
        """
        if self.enable_notifications:
            msg = 'Please input read value{s} for channel{s}: {names} now. ({now})'.format(
                s='s' if len(channels) > 1 else '',
                names=', '.join(
                    [
                        ch.get_name() for ch in channels]),
                now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            for notification_function in self.notification_functions:
                notification_function(msg)
        results_dict = results_ord_dict()
        for ch in channels:
            results_dict[ch.get_name()] = ch.read_without_delegator()
        return results_dict


class expect(instrument):
    """Virtual instrument to check that reading is within specified tolerance of expected result.

    >>> expect.compare_abs(measured=10.1, expect=10.0, tolerance=0.2)
    True
    >>> expect.compare_abs(measured=10.5, expect=10.0, tolerance=0.2)
    False
    >>> expect.compare_pct(measured=1.05, expect=1.0, tolerance=0.1)
    True
    >>> expect.compare_pct(measured=1.15, expect=1.0, tolerance=0.1)
    False
    >>> expect.compare_exact(measured=42, expect=42)
    True
    >>> expect.compare_exact(measured=42, expect=43)
    False
    """
    def __init__(self, verbose_pass, err_msg_prefix=None,
                 pass_msg_prefix=None):
        """Expect instrument.

        Monitor slaved channel(s) for unexpected (out-of-spec) measurments.
        Configurable per-channel to emit warning message or raise ExpectException when expectations are not met.
        Configurable per-channel to perform check either on demand, or automatically whenever slaved chanenl is read.
        Configurable per-channel to perform either absolute (additive) check or percentage (multiplicative) check.
        Configurable per-channel to alter expectation and tolerance on the fly.
        Configurable per-instrument to emit custom error message prefix (for regex log search, etc)
        Configurable per-instrument to emit custom pass message prefix (for regex log search, etc)
        Configurable per-instrument to selectively emit verbose_pass message (for regex log search, etc)


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, '__init__')
        True

        Args:
            err_msg_prefix: Err msg prefix to use.
            pass_msg_prefix: Pass msg prefix to use.
            verbose_pass: Verbose pass to use.
        """
        instrument.__init__(self, "Measurement Expect Instrument")
        self._base_name = 'Measurement Expect Instrument'
        self.verbose_pass = True if verbose_pass else False
        if err_msg_prefix is None:
            err_msg_prefix = "FAIL: "
        if pass_msg_prefix is None:
            pass_msg_prefix = "PASS: "
        self.err_msg_prefix = err_msg_prefix
        self.pass_msg_prefix = pass_msg_prefix

        self.channel_msg = '{msg_prefix}{exp_name}: expected {exp_val} from {slave_name}, got {meas_val}.'
        self.naked_msg = '{msg_prefix}{exp_name}{colon}expected {exp_val}, got {meas_val}.'

    @staticmethod
    def compare_exact(measured, expect):
        """Check that measured is equal to expect.


        Evaluates the condition and raises or returns a diagnostic result.

        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_exact(42, 42)
        True
        >>> expect.compare_exact(42, 43)
        False

        Args:
            expect: Expected value.
            measured: Measured value.

        Returns:
            The compare exact result.
        """
        return measured == expect

    @staticmethod
    def compare_pct_not_above(measured, expect, tolerance):
        """Check that measured is below expect * (1 + tolerance).

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_pct_not_above(105, 100, 0.1)
        True
        >>> expect.compare_pct_not_above(115, 100, 0.1)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare pct not above result.
        """
        return measured <= expect * (1 + tolerance)

    @staticmethod
    def compare_pct_not_below(measured, expect, tolerance):
        """Check that measured is above expect * (1 - tolerance).

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_pct_not_below(95, 100, 0.1)
        True
        >>> expect.compare_pct_not_below(85, 100, 0.1)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare pct not below result.
        """
        return measured >= expect * (1 - tolerance)

    @staticmethod
    def compare_abs_not_above(measured, expect, tolerance):
        """Check that measured is below (expect + tolerance).

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_abs_not_above(104, 100, 5)
        True
        >>> expect.compare_abs_not_above(106, 100, 5)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare abs not above result.
        """
        return measured <= expect + tolerance

    @staticmethod
    def compare_abs_not_below(measured, expect, tolerance):
        """Check that measured is above (expect - tolerance).

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_abs_not_below(96, 100, 5)
        True
        >>> expect.compare_abs_not_below(94, 100, 5)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare abs not below result.
        """
        return measured >= expect - tolerance

    @classmethod
    def compare_pct(cls, measured, expect, tolerance):
        """Check that measured is within expect * (1 +/- tolerance).


        Evaluates the condition and raises or returns a diagnostic result.

        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_pct(105, 100, 0.10)
        True
        >>> expect.compare_pct(115, 100, 0.10)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare pct result.
        """
        return cls.compare_pct_not_above(
            measured, expect, tolerance) and cls.compare_pct_not_below(measured, expect, tolerance)

    @classmethod
    def compare_abs(cls, measured, expect, tolerance):
        """Check that measured is within expect +/- tolerance.


        Evaluates the condition and raises or returns a diagnostic result.

        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_abs(104, 100, 5)
        True
        >>> expect.compare_abs(106, 100, 5)
        False

        Args:
            expect: Expected value.
            measured: Measured value.
            tolerance: Tolerance value.

        Returns:
            The compare abs result.
        """
        return cls.compare_abs_not_above(
            measured, expect, tolerance) and cls.compare_abs_not_below(measured, expect, tolerance)

    @classmethod
    def compare_strict(cls, measured, expect, pct_tolerance, abs_tolerance):
        """Check that both absolute tolerance and percentage tolerance is met.

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_strict(105, 100, 0.1, 5)
        True
        >>> expect.compare_strict(106, 100, 0.1, 5)
        False

        Args:
            abs_tolerance: Abs tolerance to use.
            expect: Expected value.
            measured: Measured value.
            pct_tolerance: Pct tolerance to use.

        Returns:
            The compare strict result.
        """
        return cls.compare_pct(measured, expect, pct_tolerance) and cls.compare_abs(
            measured, expect, abs_tolerance)

    @classmethod
    def compare_lenient(cls, measured, expect, pct_tolerance, abs_tolerance):
        """Check that either absolute tolerance or percentage tolerance is met.

        Evaluates the condition and raises or returns a diagnostic result.


        >>> from PyICe.virtual_instruments import expect
        >>> expect.compare_lenient(105, 100, 0.1, 5)
        True
        >>> expect.compare_lenient(120, 100, 0.1, 5)
        False

        Args:
            abs_tolerance: Abs tolerance to use.
            expect: Expected value.
            measured: Measured value.
            pct_tolerance: Pct tolerance to use.

        Returns:
            The compare lenient result.
        """
        return cls.compare_pct(measured, expect, pct_tolerance) or cls.compare_abs(
            measured, expect, abs_tolerance)

    def check_exact(self, measured, expect, en_assertion, name=None):
        """Channel-independent exact-value check method.

        Configurable to either emit warning message or raise ExpectException when expectation is not met.

        >>> from PyICe.virtual_instruments import expect, ExpectUnderException
        >>> e = expect(verbose_pass=False)
        >>> e.check_exact(42, 42, en_assertion=True)
        True
        >>> e.check_exact(42, 43, en_assertion=True)
        Traceback (most recent call last):
            ...
        PyICe.virtual_instruments.ExpectUnderException: FAIL: expected 43, got 42.
        >>> e.check_exact(42, 43, en_assertion=False)
        FAIL: expected 43, got 42.
        False

        Args:
            en_assertion: If True, raise exception on failure.
            expect: Expected value.
            measured: Measured value.
            name: Name identifier.

        Returns:
            The check exact result.
        """
        return self._check(function=self.compare_exact, measured=measured, expect=expect,
                           tolerance=None, en_assertion=en_assertion, exp_name=name, slave_name=None)

    def check_pct(self, measured, expect, tolerance, en_assertion, name=None):
        """Channel-independent percentage/multiplicative check method.

        Configurable to either emit warning message or raise ExpectException when expectation is not met.

        >>> from PyICe.virtual_instruments import expect, ExpectUnderException
        >>> e = expect(verbose_pass=False)
        >>> e.check_pct(105, 100, 0.10, en_assertion=True)
        True
        >>> e.check_pct(90, 100, 0.05, en_assertion=True)
        Traceback (most recent call last):
            ...
        PyICe.virtual_instruments.ExpectUnderException: FAIL: expected 100, got 90.
        >>> e.check_pct(90, 100, 0.05, en_assertion=False)
        FAIL: expected 100, got 90.
        False

        Args:
            en_assertion: If True, raise exception on failure.
            expect: Expected value.
            measured: Measured value.
            name: Name identifier.
            tolerance: Tolerance value.

        Returns:
            The check pct result.
        """
        return self._check(function=self.compare_pct, measured=measured, expect=expect,
                           tolerance=tolerance, en_assertion=en_assertion, exp_name=name, slave_name=None)

    def check_abs(self, measured, expect, tolerance, en_assertion, name=None):
        """Channel-independent absolute/additive check method.

        Configurable to either emit warning message or raise ExpectException when expectation is not met.

        >>> from PyICe.virtual_instruments import expect, ExpectUnderException
        >>> e = expect(verbose_pass=False)
        >>> e.check_abs(104, 100, 5, en_assertion=True)
        True
        >>> e.check_abs(90, 100, 5, en_assertion=True)
        Traceback (most recent call last):
            ...
        PyICe.virtual_instruments.ExpectUnderException: FAIL: expected 100, got 90.
        >>> e.check_abs(90, 100, 5, en_assertion=False)
        FAIL: expected 100, got 90.
        False

        Args:
            en_assertion: If True, raise exception on failure.
            expect: Expected value.
            measured: Measured value.
            name: Name identifier.
            tolerance: Tolerance value.

        Returns:
            The check abs result.
        """
        return self._check(function=self.compare_abs, measured=measured, expect=expect,
                           tolerance=tolerance, en_assertion=en_assertion, exp_name=name, slave_name=None)

    def _ch_check(self, ch, measured=None, expect=None):
        """Unified check and error report wrapper for channel attribute lookup.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, '_ch_check')
        True

        Args:
            ch: Channel number or channel object.
            expect: Expected value.
            measured: Measured value.

        Returns:
            The ch check result.
        """
        if expect is None:
            # as is the case when called from read callbac
            # TODO Does this need some special handling for None actual channel
            # value?
            expect = ch.read()
        if measured is None:
            # as is the case when called from write function (immediate mode)
            # Note that this might not be quite right. If the comparison fails in immediate mode, the Expect exception will cause the channel write to fail.
            # The channel "cached" value will not be updated in this case. The exception can't be caught from the application down inside lab_core.
            # If the write needs to "take", then the exception needs to be "scheduled" for after the write completes, or the write needs to use channel class private methods to store the write value.
            # As is, the expect channel will store the last successful write, which may be the "right" behavior.
            # None of this is an issue in non-immediate (callback) mode.

            # TODO Does this need some special handling for None actual channel
            # value?
            measured = ch.get_attribute('slave_read_channel').read()
        # TODO: Check this comparison for safety against presets, None, True,
        # False, etc.
        if ch.get_attribute('enabled'):
            # comp_result = ch.get_attribute('function')(measured, expect, ch.get_attribute('tolerance'))
            comp_result = self._check(
                ch.get_attribute('function'),
                measured,
                expect,
                ch.get_attribute('tolerance'),
                ch.get_attribute('en_assertion'),
                ch.get_name(),
                ch.get_attribute('slave_read_channel').get_name())
            ch.get_attribute('results_channel').write(comp_result)
            return comp_result
        else:
            ch.get_attribute('results_channel').write(None)
            return None

    def _check(self, function, measured, expect, tolerance,
               en_assertion, exp_name=None, slave_name=None):
        """Unified check and error report.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, '_check')
        True

        Args:
            en_assertion: If True, raise exception on failure.
            exp_name: Exp name to use.
            expect: Expected value.
            function: Callable to execute.
            measured: Measured value.
            slave_name: Slave name to use.
            tolerance: Tolerance value.

        Returns:
            The check result.

        Raises:
            Exception: If an unexpected error occurs.
            ExpectOverException: If the measured value exceeds the upper limit.
            ExpectUnderException: If the measured value is below the lower limit.
        """
        if tolerance is not None:
            comp_result = function(measured, expect, tolerance)
        else:
            comp_result = function(measured, expect)
        if not comp_result:
            # fail
            if exp_name is not None and slave_name is not None:
                msg = self.channel_msg.format(
                    msg_prefix=self.err_msg_prefix,
                    exp_name=exp_name,
                    exp_val=expect,
                    slave_name=slave_name,
                    meas_val=measured)
            else:
                if slave_name is not None:
                    raise Exception('Unimplemented')
                if exp_name is not None:
                    colon = ": "
                else:
                    colon = ""
                    exp_name = ""
                msg = self.naked_msg.format(
                    msg_prefix=self.err_msg_prefix,
                    exp_name=exp_name,
                    colon=colon,
                    exp_val=expect,
                    meas_val=measured)
            if en_assertion:
                if measured > expect:
                    raise ExpectOverException(msg)
                elif measured < expect:
                    raise ExpectUnderException(msg)
                else:
                    # Can this ever happen????
                    # raise ExpectException(msg)
                    raise Exception("Who am I and how did I get here???")
            else:
                print(msg)
                return False
        else:
            # pass
            if self.verbose_pass:
                if exp_name is not None and slave_name is not None:
                    msg = self.channel_msg.format(
                        msg_prefix=self.pass_msg_prefix,
                        exp_name=exp_name,
                        exp_val=expect,
                        slave_name=slave_name,
                        meas_val=measured)
                else:
                    if exp_name is not None:
                        colon = ": "
                    else:
                        colon = ""
                        exp_name = ""
                    msg = self.naked_msg.format(
                        msg_prefix=self.pass_msg_prefix,
                        exp_name=exp_name,
                        colon=colon,
                        exp_val=expect,
                        meas_val=measured)
                print(msg)
            return True
        raise Exception("Who am I and how did I get here???")

    def _add_channel_expect(self, compare_func, channel_name,
                            slave_read_channel, tolerance, en_immediate, en_assertion):
        # write_channel = channel(channel_name,write_function=lambda expect: self.f_assert(lambda: self.compare_pct(slave_read_channel.read(), expect, tolerance)))
        write_channel = channel(channel_name, write_function=None)
        results_channel = channel("{}_pass".format(channel_name))
        results_channel.set_attribute('expect_channel', write_channel)
        # results_channel not returned
        write_channel.set_attribute('function', compare_func)
        write_channel.set_attribute('enabled', True)
        write_channel.set_attribute('slave_read_channel', slave_read_channel)
        write_channel.set_attribute('tolerance', tolerance)
        write_channel.set_attribute('en_immediate', en_immediate)
        write_channel.set_attribute('en_assertion', en_assertion)
        write_channel.set_attribute('results_channel', results_channel)
        if en_immediate:
            write_channel._write = lambda expect: self._ch_check(
                write_channel, expect=expect)
        else:
            # is automatic callback mode exclusive with immediate???
            # slave_read_channel.add_read_callback(lambda read_channel_object,read_value,expect_channel_object=write_channel: self.compare_pct(measured=read_value, expect=expect_channel_object.read(), tolerance=expect_channel_object.get_attribute('tolerance')))
            slave_read_channel.add_read_callback(
                lambda read_channel_object, read_value: self._ch_check(
                    # read_channel object discarded.
                    write_channel, measured=read_value))
        self._add_channel(results_channel)
        return self._add_channel(write_channel)

    def add_channel_expect_pct(
            self, channel_name, slave_read_channel, tolerance, en_immediate, en_assertion):
        """Check that value read from slave_read_channel is within <write_value> * (1 +/- tolerance).

        if en_immediate, a write to this channel triggers a read of slave_read_channel and the compare operation
        otherwise, the compare operation is executed automatically each time slave_read_channel is read.
        if en_assertion, a failed compare operation raises an ExpectException


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, 'add_channel_expect_pct')
        True

        Args:
            channel_name: Name for the new channel.
            en_assertion: If True, raise exception on failure.
            en_immediate: En immediate to use.
            slave_read_channel: Slave read channel to use.
            tolerance: Tolerance value.

        Returns:
            The newly created channel object.
        """
        ch = self._add_channel_expect(
            compare_func=self.compare_pct,
            channel_name=channel_name,
            slave_read_channel=slave_read_channel,
            tolerance=tolerance,
            en_immediate=en_immediate,
            en_assertion=en_assertion)
        ch.set_description(self.get_name() + ': ' +
                           self.add_channel_expect_pct.__doc__)
        return ch

    def add_channel_expect_abs(
            self, channel_name, slave_read_channel, tolerance, en_immediate, en_assertion):
        """Check that value read from slave_read_channel is within <write_value> +/- tolerance.

        if en_immediate, a write to this channel triggers a read of slave_read_channel and the compare operation
        otherwise, the compare operation is executed automatically each time slave_read_channel is read.
        if en_assertion, a failed compare operation raises an ExpectException


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, 'add_channel_expect_abs')
        True

        Args:
            channel_name: Name for the new channel.
            en_assertion: If True, raise exception on failure.
            en_immediate: En immediate to use.
            slave_read_channel: Slave read channel to use.
            tolerance: Tolerance value.

        Returns:
            The newly created channel object.
        """
        ch = self._add_channel_expect(
            compare_func=self.compare_abs,
            channel_name=channel_name,
            slave_read_channel=slave_read_channel,
            tolerance=tolerance,
            en_immediate=en_immediate,
            en_assertion=en_assertion)
        ch.set_description(self.get_name() + ': ' +
                           self.add_channel_expect_abs.__doc__)
        return ch

    def add_channel_expect_exact(
            self, channel_name, slave_read_channel, en_immediate, en_assertion):
        """Check that value read from slave_read_channel is equal to <write_value>.

        slave_read_channel must be an integer channel for an exact comparison to make sense.
        if en_immediate, a write to this channel triggers a read of slave_read_channel and the compare operation
        otherwise, the compare operation is executed automatically each time slave_read_channel is read.
        if en_assertion, a failed compare operation raises an ExpectException


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, 'add_channel_expect_exact')
        True

        Args:
            channel_name: Name for the new channel.
            en_assertion: If True, raise exception on failure.
            en_immediate: En immediate to use.
            slave_read_channel: Slave read channel to use.

        Returns:
            The newly created channel object.
        """
        assert isinstance(slave_read_channel, integer_channel)
        ch = self._add_channel_expect(
            compare_func=self.compare_exact,
            channel_name=channel_name,
            slave_read_channel=slave_read_channel,
            tolerance=None,
            en_immediate=en_immediate,
            en_assertion=en_assertion)
        ch.set_description(self.get_name() + ': ' +
                           self.add_channel_expect_exact.__doc__)
        return ch

    def add_channel_tolerance(self, channel_name, expect_channel):
        """Modify expect tolerance of expect_channel after creation. Also logs tolerance with results (with pct/abs ambiguity).
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, 'add_channel_tolerance')
        True

        Args:
            channel_name: Name for the new channel.
            expect_channel: Expect channel to use.

        Returns:
            The newly created channel object.
        """
        assert 'tolerance' in expect_channel.get_attributes().keys()
        # integer channel / exact comparison
        assert expect_channel.get_attributes()['tolerance'] is not None
        ch = channel(
            channel_name,
            write_function=lambda tolerance: expect_channel.set_attribute(
                'tolerance',
                tolerance))
        ch.write(expect_channel.get_attribute('tolerance'))
        ch.set_description(self.get_name() + ': ' +
                           self.add_channel_tolerance.__doc__)
        return self._add_channel(ch)

    def add_channel_enable(self, channel_name, expect_channel):
        """Enabled/disable expect cheking of expect_channel after creation.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import expect
        >>> hasattr(expect, 'add_channel_enable')
        True

        Args:
            channel_name: Name for the new channel.
            expect_channel: Expect channel to use.

        Returns:
            The newly created channel object.
        """
        ch = channel(
            channel_name,
            write_function=lambda enable: expect_channel.set_attribute(
                'enabled',
                True if enable else False))
        ch.write(expect_channel.get_attribute('enabled'))
        ch.set_description(self.get_name() + ': ' +
                           self.add_channel_enable.__doc__)
        return self._add_channel(ch)


class ExpectException(Exception):
    """Base class for expect instrument comparison failures.

    >>> raise ExpectException("measurement out of range")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ExpectException: measurement out of range
    """


class ExpectOverException(ExpectException):
    """Expect instrument comparison failures for measured > expect.

    >>> raise ExpectOverException("measured 110, expected 100")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ExpectOverException: measured 110, expected 100
    """


class ExpectUnderException(ExpectException):
    """Expect instrument comparison failures for measured < expect.

    >>> raise ExpectUnderException("measured 90, expected 100")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ExpectUnderException: measured 90, expected 100
    """


class delay_loop(PyICe.lab_utils.delay_loop.delay_loop, instrument):
    """Instrument wrapper for lab_utils.delay_loop enables logging of delay diagnostic variables.

    >>> from PyICe.virtual_instruments import delay_loop
    >>> dl = delay_loop(begin=False)
    >>> ch_count = dl.add_channel_count("loop_count")
    >>> ch_time = dl.add_channel_total_time("total_time")
    >>> ch_count.get_name()
    'loop_count'
    >>> ch_time.get_name()
    'total_time'
    """

    def __init__(self, strict=False, begin=True, no_drift=True):
        """Set strict to True to raise an Exception if loop time is longer than requested delay.

        Timer will automatically begin when the object is instantiated if begin=True.
        To start timer only when ready, set begin=False and call begin() method to start timer.
        If no_drift=True, delay loop will manage loop time over-runs by debiting extra time from next cycle.
        This insures long-term time stability at the expense of increased jitter.
        Windows task switching can add multi-mS uncertainty to each delay() call, which can accumulate if not accounted for.
        Set no_drift=False to ignore time over-runs when computing next delay time.

        >>> from PyICe.virtual_instruments import delay_loop
        >>> obj = delay_loop(begin=False)
        >>> isinstance(obj, delay_loop)
        True

        Args:
            begin: Begin to use.
            no_drift: No drift to use.
            strict: Strict to use.
        """
        instrument.__init__(self, "delay_loop instrument wrapper")
        PyICe.lab_utils.delay_loop.delay_loop.__init__(
            self, strict, begin, no_drift)
        self._base_name = 'Precision Delay Loop Virtual Instrument Wrapper'

    def add_channel_count(self, channel_name):
        """Total number of times delay() method called.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import delay_loop
        >>> hasattr(delay_loop, 'add_channel_count')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The count.
        """
        new_channel = channel(channel_name, read_function=self.get_count)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_count.__doc__)
        return self._add_channel(new_channel)

    def add_channel_total_time(self, channel_name):
        """Total number of seconds since delay() method first called.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import delay_loop
        >>> hasattr(delay_loop, 'add_channel_total_time')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=self.get_total_time)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_time.__doc__)
        return self._add_channel(new_channel)

    def add_channel_delay_margin(self, channel_name):
        """Time remaining after user's loop tasks completed to sleep before start of next cycle.

        Negative if user tasks exceed loop time and no time is left to sleep.
        Includes any make-up contribution if previous iterations over-ran allocated loop time with no_drift attribute set.


        >>> from PyICe.virtual_instruments import delay_loop
        >>> hasattr(delay_loop, 'add_channel_delay_margin')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=self.delay_margin)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delay_margin.__doc__)
        return self._add_channel(new_channel)

    def add_channel_achieved_loop_time(self, channel_name):
        """Actual time spent during in last loop iteration.

        possibly longer than requested loop time if user taskes exceeded requested time (overrun).


        >>> from PyICe.virtual_instruments import delay_loop
        >>> hasattr(delay_loop, 'add_channel_achieved_loop_time')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=self.achieved_loop_time)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_achieved_loop_time.__doc__)
        return self._add_channel(new_channel)


class clipboard(instrument):
    """Virtual instrument to exchange data with Windows/Linux clipboard for interactive copy and paste with another application.

    >>> import io, contextlib
    >>> from PyICe.virtual_instruments import clipboard
    >>> with contextlib.redirect_stdout(io.StringIO()):
    ...     try:
    ...         cb = clipboard()
    ...     except Exception:
    ...         cb = None
    >>> name = cb.add_channel_copy("copy").get_name() if cb else "copy"
    >>> name
    'copy'
    """

    def __init__(self):
        """Initialize clipboard.
        Initializes 4 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 7 instance attributes that configure the object's behavior.

        >>> from PyICe.virtual_instruments import clipboard
        >>> clipboard is not None
        True

        """
        instrument.__init__(self, 'Clipboard Exchange Virtual Instrument')
        self._base_name = 'Copy/Past Clipboard Virtual Instrument'
        try:
            import pyperclip  # cross-platform
            # https://pyperclip.readthedocs.org/
            # https://github.com/asweigart/pyperclip
            self._lib = pyperclip
            self._copy = self._pyperclip_copy
            self._paste = self._pyperclip_paste
        except ImportError:
            print('pyperclip dependency not found.  Attempting to use win32clipboard.')
            try:
                import win32clipboard
                # http://docs.activestate.com/activepython/2.4/pywin32/win32clipboard.html
                self._lib = win32clipboard
                self._copy = self._win32_copy
                self._paste = self._win32_paste
            except ImportError:
                raise Exception(
                    'Clipboard virtual instrument requires either pyperclip or pywin32 module win32clipboard.')

    def add_channel_copy(self, channel_name):
        """Place data written to channel_name onto clipboard.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import clipboard
        >>> hasattr(clipboard, 'add_channel_copy')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self._copy)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_copy.__doc__)
        return self._add_channel(new_channel)

    def add_channel_paste(self, channel_name):
        """Place data from clipboard into channel_name.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import clipboard
        >>> hasattr(clipboard, 'add_channel_paste')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=self._paste)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_paste.__doc__)
        return self._add_channel(new_channel)

    def register_copy_channel(self, channel_object, write_copy=True):
        """Automatically places results on clipboard each time channel_object is read and optionally when channel_object is written.

        Supports the ``clipboard`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import clipboard
        >>> hasattr(clipboard, 'register_copy_channel')
        True

        Args:
            channel_object: PyICe channel object to operate on.
            write_copy: Write copy to use.
        """
        channel_object.add_read_callback(
            lambda channel_object,
            read_value: self._copy(read_value))
        if write_copy:
            channel_object.add_write_callback(
                lambda channel_object, write_value: self._copy(write_value))

    def _copy(self, clipboard_data):  # pylint: disable=method-hidden; intentionally overridden in __init__ with library-specific implementation (pyperclip or win32clipboard)
        """Place clipboard_data onto OS clipboard.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import clipboard
        >>> hasattr(clipboard, '_copy')
        True

        Args:
            clipboard_data: Clipboard data to use.

        Raises:
            Exception: If an unexpected error occurs.
        """
        raise Exception('Overloaded implementation is library specific.')

    def _paste(self):  # pylint: disable=method-hidden; intentionally overridden in __init__ with library-specific implementation (pyperclip or win32clipboard)
        """Return OS clipboard contents.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import clipboard
        >>> hasattr(clipboard, '_paste')
        True

        Raises:
            Exception: If an unexpected error occurs.
        """
        raise Exception('Overloaded implementation is library specific.')

    def _pyperclip_copy(self, clipboard_data):
        self._lib.copy(str(clipboard_data))

    def _pyperclip_paste(self):
        return self._lib.paste()

    def _win32_copy(self, clipboard_data):
        self._lib.OpenClipboard()
        self._lib.EmptyClipboard()
        self._lib.SetClipboardText(str(clipboard_data))
        self._lib.CloseClipboard()

    def _win32_paste(self):
        self._lib.OpenClipboard()
        data = self._lib.GetClipboardData()
        self._lib.CloseClipboard()
        return data


class accumulator(instrument):
    """Virtual accumulator instrument.

    Writable channel adds value to stored total.
    Readable channel returns accumulation total.
    Can be used as a counter by writing accumulation value to +/-1

    >>> acc = accumulator(init=0)
    >>> acc.accumulate(5)
    >>> acc.accumulate(3)
    >>> acc.accumulation
    8
    >>> acc.accumulate(-2)
    >>> acc.accumulation
    6
    """
    def __init__(self, init=0):
        """Init sets initial accumulation total.  Defaults to 0.
        Stores configuration in ``_base_name``, ``accumulation`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import accumulator
        >>> obj = accumulator(init=0)
        >>> isinstance(obj, accumulator)
        True

        Args:
            init: Initial value.
        """
        self._base_name = "Accumulator Virtual Instrument"
        instrument.__init__(self, self._base_name)
        self.accumulation = init

    def add_channel_accumulation(self, channel_name):
        """Channel reads return total accumulated quantity.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        >>> from PyICe.virtual_instruments import accumulator
        >>> acc = accumulator(init=10)
        >>> ch = acc.add_channel_accumulation('total')
        >>> ch.read()
        10
        >>> acc.accumulate(5)
        >>> ch.read()
        15

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.accumulation)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_accumulation.__doc__)
        return self._add_channel(new_channel)

    def add_channel_accumulate(self, channel_name):
        """Channel writes accumulate value into total previously accumulated quantity.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.

        >>> from PyICe.virtual_instruments import accumulator
        >>> acc = accumulator(init=0)
        >>> ch = acc.add_channel_accumulate('add')
        >>> _ = ch.write(7)
        >>> acc.accumulation
        7
        >>> _ = ch.write(3)
        >>> acc.accumulation
        10

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self.accumulate)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_accumulate.__doc__)
        return self._add_channel(new_channel)

    def accumulate(self, value):
        """Adds value to accumulation total.  Use with caution outside channel framework.

        Supports the ``accumulator`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import accumulator
        >>> hasattr(accumulator, 'accumulate')
        True

        Args:
            value: Value to set.
        """
        self.accumulation += value


class timer(instrument, delegator):
    """Virtual timer instrument.

    All channels are read only and return time since either last read or first read, scaled to appropriate time units.
    All channels operate from a common timebase.

    >>> from PyICe.virtual_instruments import timer
    >>> t = timer()
    >>> ch = t.add_channel_total_seconds("elapsed_s")
    >>> ch.get_name()
    'elapsed_s'
    >>> ch2 = t.add_channel_total_minutes("elapsed_min")
    >>> ch2.get_name()
    'elapsed_min'

    """
    def __init__(self, category='Timer Virtual Instrument'):
        """Initialize timer.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import timer
        >>> obj = timer()
        >>> isinstance(obj, timer)
        True

        Args:
            category: Category label for grouping or classification.
        """
        self._base_name = category
        delegator.__init__(self)
        instrument.__init__(self, self._base_name)
        self.divs = {'seconds': 1.0,
                     'minutes': 60.0,
                     'hours': 3600.0,
                     'days': 86400.0,
                     # weeks, years?
                     }
        self.last_time = None
        self.elapsed = None
        self._paused = False

    def _dummy_read(self, channel_name):
        return self.results_dict[channel_name]

    def add_channel_total_seconds(self, channel_name):
        """Channel read reports elapsed time since first read with units of seconds.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_total_seconds')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['seconds'])
        new_channel.set_attribute('type', 'total_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_seconds.__doc__)
        new_channel.set_display_format_function(
            function=lambda time: eng_string(
                time, fmt=':3.6g', si=True) + 's')
        return self._add_channel(new_channel)

    def add_channel_total_minutes(self, channel_name):
        """Channel read reports elapsed time since first read with units of minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_total_minutes')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['minutes'])
        new_channel.set_attribute('type', 'total_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_minutes.__doc__)
        return self._add_channel(new_channel)

    def add_channel_total_hours(self, channel_name):
        """Channel read reports elapsed time since first read with units of hours.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_total_hours')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['hours'])
        new_channel.set_attribute('type', 'total_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_hours.__doc__)
        return self._add_channel(new_channel)

    def add_channel_total_days(self, channel_name):
        """Channel read reports elapsed time since first read with units of days.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_total_days')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['days'])
        new_channel.set_attribute('type', 'total_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_days.__doc__)
        return self._add_channel(new_channel)

    def add_channel_total_scale(self, channel_name, time_div):
        """Channel read reports elapsed time since first read with user supplied time units. time_div is seconds per user-unit, eg 60 for minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_total_scale')
        True

        Args:
            channel_name: Name for the new channel.
            time_div: Time-per-division setting on the oscilloscope.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', float(time_div))
        new_channel.set_attribute('type', 'total_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_total_scale.__doc__)
        return self._add_channel(new_channel)

    def add_channel_delta_seconds(self, channel_name):
        """Channel read reports elapsed time since last read with units of seconds.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_delta_seconds')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['seconds'])
        new_channel.set_attribute('type', 'delta_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_seconds.__doc__)
        new_channel.set_display_format_function(
            function=lambda time: eng_string(
                time, fmt=':3.6g', si=True) + 's')
        return self._add_channel(new_channel)

    def add_channel_delta_minutes(self, channel_name):
        """Channel read reports elapsed time since last read with units of minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_delta_minutes')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['minutes'])
        new_channel.set_attribute('type', 'delta_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_minutes.__doc__)
        return self._add_channel(new_channel)

    def add_channel_delta_hours(self, channel_name):
        """Channel read reports elapsed time since last read with units of hours.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_delta_hours')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['hours'])
        new_channel.set_attribute('type', 'delta_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_hours.__doc__)
        return self._add_channel(new_channel)

    def add_channel_delta_days(self, channel_name):
        """Channel read reports elapsed time since last read with units of days.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_delta_days')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['days'])
        new_channel.set_attribute('type', 'delta_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_days.__doc__)
        return self._add_channel(new_channel)

    def add_channel_delta_scale(self, channel_name, time_div):
        """Channel read reports elapsed time since last read with user supplied time units. time_div is seconds per user-unit, eg 60 for minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_delta_scale')
        True

        Args:
            channel_name: Name for the new channel.
            time_div: Time-per-division setting on the oscilloscope.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', float(time_div))
        new_channel.set_attribute('type', 'delta_timer')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_delta_scale.__doc__)
        return self._add_channel(new_channel)

    def add_channel_frequency_hz(self, channel_name):
        """Channel read reports read frequency in Hz.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_frequency_hz')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['seconds'])
        new_channel.set_attribute('type', 'frequency')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_frequency_hz.__doc__)
        new_channel.set_display_format_function(
            function=lambda rate: eng_string(
                rate, fmt=':3.6g', si=True) + 'Hz')
        return self._add_channel(new_channel)

    def add_channel_frequency_scale(self, channel_name, time_div):
        """Channel read reports read frequency with user supplied time units. time_div is seconds per user-unit, eg 60 for RPM.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'add_channel_frequency_scale')
        True

        Args:
            channel_name: Name for the new channel.
            time_div: Time-per-division setting on the oscilloscope.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', float(time_div))
        new_channel.set_attribute('type', 'frequency')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_frequency_scale.__doc__)
        return self._add_channel(new_channel)

    def _compute_delta(self):
        if not self._paused:
            self.this_time = datetime.datetime.now()
            if self.last_time is None:
                self.last_time = self.this_time
                self.total_time = datetime.timedelta(0)
            self.elapsed = self.this_time - self.last_time
            self.total_time += self.elapsed
            self.last_time = self.this_time

    def reset_timer(self):
        """Resets timer to 0. Use with caution outside channel framework.

        Restores the object or hardware to its default state.

        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'reset_timer')
        True

        """
        self.last_time = None
        self._compute_delta()

    def stop_and_reset_timer(self):
        """Halts and resets timer to 0. Timer will begin running after first read,.

        same behavior as after timer object instantiation.
        Use with caution outside channel framework.

        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'stop_and_reset_timer')
        True

        """
        self.last_time = None

    def pause_timer(self):
        """Pause timer . Call resume_timer() to continue counting.

        Introduces a timing delay required by the hardware or protocol.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'pause_timer')
        True

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self._paused:
            raise Exception('Attemped to pause already paused timer.')
        else:  # update internal variables because _compute_delta won't while paused
            self._pause_time = datetime.datetime.now()
            # shouldn't ever pause a timer before it starts...
            self.elapsed = self._pause_time - self.last_time
            self.total_time += self.elapsed
            self._paused = True

    def resume_timer(self):
        """Resume the timer after pausing.

        Call ``pause_timer`` to stop counting again.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'resume_timer')
        True

        Raises:
            Exception: If an unexpected error occurs.
        """
        if self._paused:
            time_paused = datetime.datetime.now() - self._pause_time
            self.total_time -= self.elapsed  # undo temporatry accumulation during pause_timer()
            self.last_time += time_paused  # time warp
            self._paused = False
        elif self.last_time is None:  # allow unpause of never-started timer
            self.reset_timer()
        else:
            raise Exception('Attemped to resume unpaused timer.')

    def read_delegated_channel_list(self, channels):
        """Private.

        Reads data from the underlying source and returns it.


        >>> from PyICe.virtual_instruments import timer
        >>> hasattr(timer, 'read_delegated_channel_list')
        True

        Args:
            channels: List of channel objects.

        Returns:
            The value read from the device or channel.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self._compute_delta()
        self.results_dict = results_ord_dict()
        for channel in channels:
            if channel.get_attribute('type') == 'delta_timer':
                self.results_dict[channel.get_name()] = self.elapsed.total_seconds(
                ) / channel.get_attribute('time_div')
            elif channel.get_attribute('type') == 'total_timer':
                self.results_dict[channel.get_name()] = self.total_time.total_seconds(
                ) / channel.get_attribute('time_div')
            elif channel.get_attribute('type') == 'frequency':
                try:
                    self.results_dict[channel.get_name()] = channel.get_attribute(
                        'time_div') / self.elapsed.total_seconds()
                except ZeroDivisionError:
                    self.results_dict[channel.get_name()] = None
            else:
                raise Exception(
                    'Unknown channel type: {}'.format(
                        channel.get_attribute('type')))
            channel.read_without_delegator()
        return self.results_dict


class integrator(accumulator, timer):
    """Virtual integrator instrument.

    Integrate channel is writable and accumulates value to internally stored total,
    multiplied by elapsed time since last integrate channel write.
    Integration channels are read only and return integration total, scaled to appropriate time units.
    Timer channels are read-only and return elapsed time used to compute time time differential,
    scaled to appropriate time units.
    A readable channel from a different instrument can be registered with this instrument
    so that any read of that channel causes its value to be integrated automatically
    without requiring an explicit call to this instrument's integrate method or channel.
    All channels operate from a common timebase.

    >>> from PyICe.virtual_instruments import integrator
    >>> integrator is not None
    True

    """
    def __init__(self, init=0):
        """Init sets initial accumulation total.  Defaults to 0.
        Stores configuration in ``_base_name``, ``last_value`` for use by
        other methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import integrator
        >>> obj = integrator()
        >>> isinstance(obj, integrator)
        True

        Args:
            init: Initial value.
        """
        accumulator.__init__(self, init)
        timer.__init__(self)
        self._base_name = 'Integrator Virtual Instrument'
        instrument.__init__(self, self._base_name)
        self.last_value = None

    def add_channel_integration_seconds(self, channel_name):
        """Channel read reports integration value with time units of seconds.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integration_seconds')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['seconds'])
        new_channel.set_attribute('type', 'integrator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integration_seconds.__doc__)
        return self._add_channel(new_channel)

    def add_channel_integration_minutes(self, channel_name):
        """Channel read reports integration value with time units of minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integration_minutes')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['minutes'])
        new_channel.set_attribute('type', 'integrator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integration_minutes.__doc__)
        return self._add_channel(new_channel)

    def add_channel_integration_hours(self, channel_name):
        """Channel read reports integration value with time units of hours.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integration_hours')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['hours'])
        new_channel.set_attribute('type', 'integrator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integration_hours.__doc__)
        return self._add_channel(new_channel)

    def add_channel_integration_days(self, channel_name):
        """Channel read reports integration value with time units of days.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integration_days')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['days'])
        new_channel.set_attribute('type', 'integrator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integration_days.__doc__)
        return self._add_channel(new_channel)

    def add_channel_integration_scale(self, channel_name, time_div):
        """Channel read reports integration value with user supplied time units. time_div is seconds per user-unit, eg 60 for minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integration_scale')
        True

        Args:
            channel_name: Name for the new channel.
            time_div: Time-per-division setting on the oscilloscope.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', float(time_div))
        new_channel.set_attribute('type', 'integrator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integration_scale.__doc__)
        return self._add_channel(new_channel)

    def add_channel_integrate(self, channel_name):
        """Writing to this channel causes written value to be added to accumulator scaled by elapsed time since last write.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'add_channel_integrate')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self.integrate)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_integrate.__doc__)
        return self._add_channel(new_channel)

    def register_integrand_channel(self, channel_object):
        """Automatically calls integrate method each time channel_object is read, for example in logger.log().

        Captures data for later analysis or replay.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'register_integrand_channel')
        True

        Args:
            channel_object: PyICe channel object to operate on.
        """
        channel_object.add_read_callback(
            lambda channel_object,
            read_value: self.integrate(read_value))

    def integrate(self, value):
        """Scale value by elapsed time and store to accumulator.  Should typically be used through integrate channel above.

        Persists the current state or data to durable storage.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'integrate')
        True

        Args:
            value: Value to set.
        """
        # results stored internally in value*seconds.  Read channels scale to
        # other time units on the way out.
        self._compute_delta()
        if not self._paused:
            if self.last_value is not None:
                interval_val = (value + self.last_value) * 0.5
                # interval_val = value
                self.accumulate(interval_val * self.elapsed.total_seconds())
            # first order hold to record interval average rather than endpoint
            self.last_value = value

    def read_delegated_channel_list(self, channels):
        """Private.

        Reads data from the underlying source and returns it.


        >>> from PyICe.virtual_instruments import integrator
        >>> hasattr(integrator, 'read_delegated_channel_list')
        True

        Args:
            channels: List of channel objects.

        Returns:
            The value read from the device or channel.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self.results_dict = results_ord_dict()
        for channel in channels:
            if channel.get_attribute('type') == 'integrator':
                self.results_dict[channel.get_name(
                )] = self.accumulation / channel.get_attribute('time_div')
            # actually returns 0 first time
            # elif self.elapsed is None: #first read; can't call total_seconds() method of NoneType
            #        results_dict[channel.get_name()] = None
            elif channel.get_attribute('type') == 'delta_timer':
                try:
                    self.results_dict[channel.get_name()] = self.elapsed.total_seconds(
                    ) / channel.get_attribute('time_div')
                except AttributeError:  # first read before call to integrate()
                    self.results_dict[channel.get_name()] = None
            elif channel.get_attribute('type') == 'total_timer':
                try:
                    self.results_dict[channel.get_name()] = self.total_time.total_seconds(
                    ) / channel.get_attribute('time_div')
                except AttributeError:  # first read before call to integrate()
                    self.results_dict[channel.get_name()] = None
            else:
                raise Exception(
                    'Unknown channel type: {}'.format(
                        channel.get_attribute('type')))
            channel.read_without_delegator()
        return self.results_dict


class differencer(instrument):
    """Virtual differencer instrument.

    Compute_difference channel is writable and causes computation of first difference from last written value.
    Read_difference channel is read-only and returns computed difference.
    A readable channel from a different instrument can be registered with this instrument
    so that any read of that channel causes its value to be differenced automatically
    without requiring an explicit call to this instrument's difference method.

    >>> d = differencer(init=0)
    >>> d.difference(10)
    10
    >>> d.difference(25)
    15
    >>> d.difference(20)
    -5
    """
    def __init__(self, init=None):
        """Init sets initial value of previous value used to compute difference.  Defaults to None.
        Stores configuration in ``_base_name``, ``diff``, ``last_value`` for
        use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 3 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import differencer
        >>> differencer is not None
        True

        Args:
            init: Initial value.
        """
        self.last_value = init
        self.diff = None
        self._base_name = 'Differencer Virtual Instrument'
        instrument.__init__(self, self._base_name)

    def add_channel_read_difference(self, channel_name):
        """Channel read returns difference between previous two values passed to difference method.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differencer
        >>> hasattr(differencer, 'add_channel_read_difference')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self.diff)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_read_difference.__doc__)
        return self._add_channel(new_channel)

    def add_channel_compute_difference(self, channel_name):
        """Channel write computes difference between previous two values passed to difference method.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differencer
        >>> hasattr(differencer, 'add_channel_compute_difference')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self.difference)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_compute_difference.__doc__)
        return self._add_channel(new_channel)

    def difference(self, value):
        """Returns difference between value and value passed in last method call.

        Supports the ``differencer`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import differencer
        >>> hasattr(differencer, 'difference')
        True

        Args:
            value: Value to set.

        Returns:
            The difference result.
        """
        if self.last_value is None:
            self.diff = None
        else:
            self.diff = value - self.last_value
        self.last_value = value
        return self.diff

    def register_difference_channel(self, channel_object):
        """Automatically calls difference method each time channel_object is read, for example in logger.log().

        Captures data for later analysis or replay.


        >>> from PyICe.virtual_instruments import differencer
        >>> hasattr(differencer, 'register_difference_channel')
        True

        Args:
            channel_object: PyICe channel object to operate on.
        """
        channel_object.add_read_callback(
            lambda channel_object,
            read_value: self.difference(read_value))


class differentiator(timer, differencer):
    """Virtual differentiator instrument.

    Differentiate channel is writable and causes computation of first time derivative between value and last written value.
    Differentiation channels are read-only and return previously computed time derivative, scaled to appropriate time units.
    Timer channels are read-only and return elapsed time used to compute derivative, scaled to appropriate time units.
    A readable channel from a different instrument can be registered with this instrument
    so that any read of that channel causes its value to be differentiated automatically
    without requiring an explicit call to this instrument's differentiate method or channel.

    >>> from PyICe.virtual_instruments import differentiator
    >>> d = differentiator()
    >>> d.differentiate(10) is None
    True
    >>> d.derivative is None
    True
    """
    def __init__(self):
        """Initialize differentiator.

        Stores configuration in ``_base_name``, ``derivative`` for use by
        other methods.

        >>> from PyICe.virtual_instruments import differentiator
        >>> obj = differentiator()
        >>> isinstance(obj, differentiator)
        True

        """
        timer.__init__(self)
        differencer.__init__(self)
        self._base_name = 'Differentiator Virtual Instrument'
        instrument.__init__(self, self._base_name)
        self.derivative = None

    def add_channel_differentiation_seconds(self, channel_name):
        """Channel read reports derivative value with time units of seconds.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiation_seconds')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['seconds'])
        new_channel.set_attribute('type', 'differentiator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiation_seconds.__doc__)
        return self._add_channel(new_channel)

    def add_channel_differentiation_minutes(self, channel_name):
        """Channel read reports derivative value with time units of minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiation_minutes')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['minutes'])
        new_channel.set_attribute('type', 'differentiator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiation_minutes.__doc__)
        return self._add_channel(new_channel)

    def add_channel_differentiation_hours(self, channel_name):
        """Channel read reports derivative value with time units of hours.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiation_hours')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['hours'])
        new_channel.set_attribute('type', 'differentiator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiation_hours.__doc__)
        return self._add_channel(new_channel)

    def add_channel_differentiation_days(self, channel_name):
        """Channel read reports derivative value with time units of days.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiation_days')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', self.divs['days'])
        new_channel.set_attribute('type', 'differentiator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiation_days.__doc__)
        return self._add_channel(new_channel)

    def add_channel_differentiation_scale(self, channel_name, time_div):
        """Channel read reports derivative value with user supplied time units. time_div is seconds per user-unit, eg 60 for minutes.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiation_scale')
        True

        Args:
            channel_name: Name for the new channel.
            time_div: Time-per-division setting on the oscilloscope.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._dummy_read(channel_name))
        new_channel.set_attribute('time_div', float(time_div))
        new_channel.set_attribute('type', 'differentiator')
        new_channel.set_delegator(self)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiation_scale.__doc__)
        return self._add_channel(new_channel)

    def differentiate(self, value):
        """Scale value by elapsed time and store to accumulator.  Should typically be used through integrate channel above.

        Persists the current state or data to durable storage.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'differentiate')
        True

        Args:
            value: Value to set.

        Returns:
            The differentiate result.
        """
        # results stored internally in value*seconds.  Read channels scale to
        # other time units on the way out.
        self._compute_delta()
        if not self._paused:
            self.difference(value)
        if self.diff is not None:
            try:
                self.derivative = self.diff / self.elapsed.total_seconds()
            except ZeroDivisionError:
                self.derivative = None
        else:
            self.derivative = None
        return self.derivative

    def add_channel_differentiate(self, channel_name):
        """Channel write causes time derivative between write value and previous write value to be computed and stored.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'add_channel_differentiate')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=self.differentiate)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_differentiate.__doc__)
        return self._add_channel(new_channel)

    def register_derivative_channel(self, channel_object):
        """Automatically calls difference method each time channel_object is read, for example in logger.log().

        Captures data for later analysis or replay.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'register_derivative_channel')
        True

        Args:
            channel_object: PyICe channel object to operate on.
        """
        channel_object.add_read_callback(
            lambda channel_object,
            read_value: self.differentiate(read_value))

    def read_delegated_channel_list(self, channels):
        """Private.

        Reads data from the underlying source and returns it.


        >>> from PyICe.virtual_instruments import differentiator
        >>> hasattr(differentiator, 'read_delegated_channel_list')
        True

        Args:
            channels: List of channel objects.

        Returns:
            The value read from the device or channel.

        Raises:
            Exception: If an unexpected error occurs.
        """
        self.results_dict = results_ord_dict()
        for channel in channels:
            if channel.get_attribute('type') == 'differentiator':
                if self.derivative is not None:
                    self.results_dict[channel.get_name(
                    )] = self.derivative * channel.get_attribute('time_div')
                else:
                    self.results_dict[channel.get_name()] = None
            elif channel.get_attribute('type') == 'delta_timer':
                self.results_dict[channel.get_name()] = self.elapsed.total_seconds(
                ) / channel.get_attribute('time_div')
            elif channel.get_attribute('type') == 'total_timer':
                self.results_dict[channel.get_name()] = self.total_time.total_seconds(
                ) / channel.get_attribute('time_div')
            else:
                raise Exception(
                    'Unknown channel type: {}'.format(
                        channel.get_attribute('type')))
            channel.read_without_delegator()
        return self.results_dict


class ServoException(Exception):
    """Special expcetion for the servo instrument.

    >>> from PyICe.virtual_instruments import ServoException
    >>> raise ServoException("test")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ServoException: test

    """


class servo(instrument):
    """Single channel virtual servo instrument. Modifies a forcing channel until a.

    measurement channel reads within tolerance of a target value.

    >>> from PyICe.lab_core import channel
    >>> setting = [0.0]
    >>> output = channel('force', write_function=lambda v: setting.__setitem__(0, v))
    >>> output.write(0.0)
    0.0
    >>> feedback = channel('measure', read_function=lambda: setting[0] * 2.0)
    >>> s = servo(feedback, output, minimum=0.0, maximum=5.0, abstol=0.01)
    >>> s.servo(target=3.0)  # servo feedback to 3.0 by adjusting output
    3
    >>> abs(setting[0] - 1.5) < 0.01
    True
    """
    def __init__(self, fb_channel, output_channel, minimum, maximum, abstol, reltol=0.001,
                 verbose=False, abort_on_sat=True, max_tries=10, except_on_fail=True):
        """Single channel virtual servo instrument.  Given a forcing channel object and a measurement channel object,.

        modifies the forcing channel value until the measurement channel is within specified tolerance or
        the number of allowed tries is exceeded.  Max number of tries can be varied by modifying the 'tries' property.

        fb_channel is the measurement channel object
        output_channel is the forcing channel object
        minimum is the lowest value that may be forced during the servo attempt
        maximum is the highest value that may be forced during the servo attempt
        abstol is the amount that the measurement may differ from the target value to consider the servo complete. units are the same as the measurement channel (window is +/-abstol)
        reltol is the unitless scale factor that determines when the servo loop is sufficiently settled.  (window is target*(1 +/- reltol))


        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, '__init__')
        True

        Args:
            abort_on_sat: Abort on sat to use.
            abstol: Absolute tolerance.
            except_on_fail: Except on fail to use.
            fb_channel: Fb channel to use.
            max_tries: Max tries to use.
            maximum: Maximum value.
            minimum: Minimum value.
            output_channel: Channel used for stimulus output.
            reltol: Relative tolerance.
            verbose: If True, print debug output.
        """
        self._base_name = 'servo'
        self.fb_channel = fb_channel
        self.output_channel = output_channel
        instrument.__init__(
            self, "Servo Instrument forcing {} via {}".format(
                fb_channel.get_name(), output_channel.get_name()))
        self.tries = max_tries
        self.verbose = verbose
        self.abort_on_sat = abort_on_sat
        self.gain_est = 1
        self.except_on_fail = except_on_fail
        self.target = self.output_channel.read()
        self.reconfigure(minimum, maximum, abstol, reltol)

    def reconfigure(self, minimum=None, maximum=None,
                    abstol=None, reltol=None):
        """Run the reconfigure step.

        Supports the ``servo`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, 'reconfigure')
        True

        Args:
            abstol: Absolute tolerance.
            maximum: Maximum value.
            minimum: Minimum value.
            reltol: Relative tolerance.
        """
        if (minimum is not None):
            self.minimum = minimum
        if (maximum is not None):
            self.maximum = maximum
        if (abstol is not None):
            self.abstol = abstol
        if (reltol is not None):
            self.reltol = reltol

    def add_channel_target(self, channel_name):
        """Channel write causes output_channel to servo to new target value.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, 'add_channel_target')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        servo_channel = channel(channel_name, write_function=self.servo)
        servo_channel.set_description(
            self.get_name() + ': ' + self.add_channel_target.__doc__)
        return self._add_channel(servo_channel)

    def check_enpoints(self):
        """Perform check enpoints operation.

        Sends the ```` SCPI command to the instrument.

        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, 'check_enpoints')
        True

        """
        self.output_channel.write(self.maximum)
        max_readback = float(self.fb_channel.read())
        self.output_channel.write(self.minimum)
        min_readback = float(self.fb_channel.read())
        change = max_readback - min_readback
        self.gain_est = change / (self.maximum - self.minimum)
        if self.verbose:
            print(
                f"{self.get_name()} MAX:{max_readback:3.5e} @ {self.maximum} MIN:{min_readback:3.5e} @ {self.minimum} GAINEST:{self.gain_est:3.5e}")

    def servo(self, target=None):
        """Servo fb_channel to target by varying output_channel.

        If target is omitted, previous target is maintained.


        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, 'servo')
        True

        Args:
            target: Target value.

        Returns:
            The final servo result after convergence.

        Raises:
            ServoException: If the servo fails to converge.
        """
        if target is None:
            target = self.target
        else:
            self.target = target
        if self.verbose:
            print("Servoing {} to {}".format(self.get_name(), self.target))
            print("   reltol:{} abstol:{} min:{} max:{}".format(
                self.reltol, self.abstol, self.minimum, self.maximum))
        cnt = 0
        cnt_break = 0
        readback = float(self.fb_channel.read())
        self.setting = self.output_channel.read()
        while (True):
            cnt += 1
            if (self.servo_check(readback)):
                return cnt
            if cnt > self.tries:
                if self.except_on_fail:
                    raise ServoException(
                        f"Tried to find the answer {cnt - 1} times, couldn't. Got {readback:0.3e} @ {self.setting:0.3e}")
                else:
                    return False
            error = readback - self.target
            change_by = error * -1 / self.gain_est
            new_setting = self.setting + change_by
            if self.setting == self.maximum and new_setting >= self.maximum:
                raise ServoException(
                    f"Stuck against upper limit. Got {readback:0.3e} @ {self.setting:0.3e}")
            elif new_setting > self.maximum:
                new_setting = self.maximum
                print(
                    "      Limit Max: {}".format(
                        self.output_channel.get_name()))
            if self.setting == self.minimum and new_setting <= self.minimum:
                raise ServoException(
                    f"Stuck against lower limit. Got {readback:0.3e} @ {self.setting:0.3e}")
            elif new_setting < self.minimum:
                new_setting = self.minimum
                print(
                    "      Limit Min: {}".format(
                        self.output_channel.get_name()))
            self.output_channel.write(new_setting)
            new_readback = float(self.fb_channel.read())
            change = new_readback - readback
            if new_setting != self.setting:
                gain = f"{change / (new_setting - self.setting):3.5e}"
            else:
                gain = "inf"
            if (change != 0) & (new_setting != self.setting):
                oldgain = self.gain_est
                self.gain_est = change / (new_setting - self.setting)
                if cnt > 1 and oldgain * self.gain_est < 0:
                    raise ServoException(
                        f"Gain flipped phase between cycles, first {oldgain:0.3e} then {self.gain_est:0.3e}")
            readback = new_readback
            if self.verbose:
                print(
                    f"   {cnt}: TGT:{self.target:3.5e} ERR:{error:3.5e} FRC:{new_setting:3.5e} RES:{new_readback:3.5e} GAIN:{gain} GAINEST:{self.gain_est:3.5e}")
            self.setting = new_setting
            # Added following code to quit if two consecutive tries are within
            # reltol even though final target has not been achieved. This will
            # help if available current is lower than the target
            if self.abort_on_sat and abs(change) < self.abstol:
                cnt_break += 1
                if cnt_break > 3:
                    if self.except_on_fail:
                        raise ServoException(
                            f"Change less than abstol of {self.abstol}. {readback} @ {self.setting}")
                    else:
                        return False

    def servo_check(self, readback=None):
        """Returns True if servo is within abstol or reltol tolerances.

        Returns False if servo failed to converge within alotted number of tries.


        >>> from PyICe.virtual_instruments import servo
        >>> hasattr(servo, 'servo_check')
        True

        Args:
            readback: Readback to use.

        Returns:
            The servo check result.
        """
        if readback is None:
            readback = float(self.fb_channel.read())
        if ((readback < (self.target * (1 + self.reltol))) &
                (readback > (self.target * (1 - self.reltol)))):
            return True
        if ((readback < (self.target + self.abstol)) &
                (readback > (self.target - self.abstol))):
            return True
        return False


class servo_group(object):
    """This is a group of servos.

    It will servo each servo in that group until
    all are in regulation or up to servo_group.tries times

    >>> from PyICe.virtual_instruments import servo_group
    >>> servo_group is not None
    True

    """
    def __init__(self, name):
        """Initialize servo_group.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import servo_group
        >>> servo_group is not None
        True

        Args:
            name: Name identifier.
        """
        self.servos = []
        self.verbose = False
        self.max_tries = 5
        self.tries = 0
        self.name = name

    def add_servo(self, servo_inst):
        """Add a servo virtual instrument to the servo_group.
        Adds a new servo to the object's internal collection.

        Appends a new servo entry to the object's internal collection.


        >>> from PyICe.virtual_instruments import servo_group
        >>> hasattr(servo_group, 'add_servo')
        True

        Args:
            servo_inst: Servo inst to use.
        """
        assert isinstance(servo_inst, servo)
        self.servos.append(servo_inst)

    def servo(self):
        """Run each servo in turn until all are in regulation.

        Supports the ``servo_group`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import servo_group
        >>> hasattr(servo_group, 'servo')
        True

        Returns:
            The final servo result after convergence.
        """
        self.tries = 0
        while (True):
            self.tries += 1
            if self.verbose:
                print("Looping all servos ")
            for servo in self.servos:
                servo.servo()
            # must make it through all servos twice
            restart = False
            for servo in self.servos:
                if not servo.servo_check():
                    restart = True
                    if self.verbose:
                        print(
                            "{} failed servo_check, restarting".format(
                                servo.name))
            if not restart:
                return True
            if self.tries > self.max_tries:
                print(("unable to servo in " + str(self.max_tries) + ", failed, END"))
                return False


class ramp_to(instrument):
    """Virtual instrument that changes channel setting incrementally.

    Useful to minimize impact of overshoot when trying to use power supply as a precision voltage source.
    This is a crutch. A better option would be to use an SMU if available.

    >>> from PyICe.lab_core import channel
    >>> supply = channel('vout', write_function=lambda v: v)
    >>> supply.write(0.0)
    0.0
    >>> rt = ramp_to()
    >>> ramp_ch = rt.add_channel_linear('vout_ramp', supply, step_size=1.0)
    >>> _ = ramp_ch.write(3.3)
    >>> supply.read()
    3.3
    """
    def __init__(self, verbose=False):
        """Initialize ramp_to.
        Stores configuration in ``_base_name``, ``verbose`` for use by other
        methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import ramp_to
        >>> ramp_to is not None
        True

        Args:
            verbose: If True, print debug output.
        """
        instrument.__init__(self, "ramp_to virtual instrument")
        self._base_name = "ramp_to"
        self.verbose = verbose

    def add_channel_binary(
            self, channel_name, forcing_channel, abstol=0.001, max_step=None):
        """Writes binarily decreasing magnitude steps to forcing_channel until within abstol of final voltage.

        If specified, max_step will bound the step upper magnitude.
        Use forcing_channel.set_write_delay(seconds) to control ramp rate.


        >>> from PyICe.virtual_instruments import ramp_to
        >>> hasattr(ramp_to, 'add_channel_binary')
        True

        Args:
            abstol: Absolute tolerance.
            channel_name: Name for the new channel.
            forcing_channel: Channel providing the forcing value.
            max_step: Max step to use.

        Returns:
            The newly created channel object.
        """
        assert abstol > 0
        assert max_step is None or max_step > abstol
        new_channel = channel(
            channel_name,
            write_function=lambda final_value: self._ramp_binary(
                forcing_channel,
                final_value,
                abstol,
                max_step))
        new_channel.set_description(
            '{}: binary ramping slave channel: {}. {}'.format(
                self.get_name(),
                forcing_channel.get_name(),
                self.add_channel_linear.__doc__))
        new_channel._set_value(forcing_channel.read())
        forcing_channel.add_write_callback(
            lambda forcing_channel,
            # keep channels sync'd in both directions
            final_value: new_channel._set_value(final_value))
        return self._add_channel(new_channel)

    def add_channel_linear(
            self, channel_name, forcing_channel, step_size=0.01):
        """Writes constant steps of size step_size (linear_ramp) to forcing_channel until within abstol of final voltage.

        Use forcing_channel.set_write_delay(seconds) to control ramp rate.


        >>> from PyICe.virtual_instruments import ramp_to
        >>> hasattr(ramp_to, 'add_channel_linear')
        True

        Args:
            channel_name: Name for the new channel.
            forcing_channel: Channel providing the forcing value.
            step_size: Step size for incremental operations.

        Returns:
            The newly created channel object.
        """
        assert step_size > 0
        new_channel = channel(
            channel_name,
            write_function=lambda final_value: self._ramp_linear(
                forcing_channel,
                final_value,
                step_size))
        new_channel.set_description(
            '{}: linear ramping slave channel: {}. {}'.format(
                self.get_name(),
                forcing_channel.get_name(),
                self.add_channel_linear.__doc__))
        new_channel._set_value(forcing_channel.read())
        forcing_channel.add_write_callback(
            lambda forcing_channel,
            # keep channels sync'd in both directions
            final_value: new_channel._set_value(final_value))
        return self._add_channel(new_channel)

    def add_channel_overshoot(
            self, channel_name, forcing_channel, abstol, estimated_overshoot):
        """Writes steps to forcing channel_such that peak overshoot magnitude never exceeds written value by more than abstol.

        estimated_overshoot is specified as a fraction of setting change (peak = final_value + (final_value - previous_value)*estimated_overshoot).
        For example, to model 10% overshoot (5V to 6V transition hits peak 6.1V), set estimated_overshoot=0.1.


        >>> from PyICe.virtual_instruments import ramp_to
        >>> hasattr(ramp_to, 'add_channel_overshoot')
        True

        Args:
            abstol: Absolute tolerance.
            channel_name: Name for the new channel.
            estimated_overshoot: Estimated overshoot to use.
            forcing_channel: Channel providing the forcing value.

        Returns:
            The newly created channel object.
        """
        assert abstol > 0
        assert estimated_overshoot >= 0
        estimated_overshoot = float(estimated_overshoot)
        new_channel = channel(
            channel_name,
            write_function=lambda final_value: self._ramp_overshoot(
                forcing_channel,
                final_value,
                abstol,
                estimated_overshoot))
        new_channel.set_description(
            '{}: overshoot controlling slave channel: {}. {}'.format(
                self.get_name(),
                forcing_channel.get_name(),
                self.add_channel_overshoot.__doc__))
        new_channel._set_value(forcing_channel.read())
        forcing_channel.add_write_callback(
            lambda forcing_channel,
            # keep channels sync'd in both directions
            final_value: new_channel._set_value(final_value))
        return self._add_channel(new_channel)

    def _direction(self, delta):
        try:
            return delta / abs(delta)
        except ZeroDivisionError:
            # no direction if we're already there
            return 1

    def _ramp_binary(self, forcing_channel, final_value, abstol, max_step):
        present_value = forcing_channel.read()
        if present_value is None:
            raise Exception(
                'You must write a value to underlying channel {} before using {}.'.format(
                    forcing_channel.get_name(), self.get_name()))
        delta = final_value - present_value
        while abs(delta) > abstol:
            if max_step is not None and abs(delta) > max_step:
                forcing_channel.write(
                    present_value +
                    float(max_step) *
                    self._direction(delta))
                if self.verbose:
                    print(
                        "Slewing channel: {} to: {}".format(
                            forcing_channel.get_name(),
                            forcing_channel.read()))
            else:
                forcing_channel.write(present_value + 0.5 * delta)
                if self.verbose:
                    print(
                        "Binary ramping channel: {} to: {}".format(
                            forcing_channel.get_name(),
                            forcing_channel.read()))
            present_value = forcing_channel.read()
            delta = final_value - present_value
        forcing_channel.write(final_value)

    def _ramp_linear(self, forcing_channel, final_value, step_size):
        present_value = forcing_channel.read()
        if present_value is None:
            raise Exception(
                'Error: must write a value to underlying channel {} before using {}.'.format(
                    forcing_channel.get_name(), self.get_name()))
        delta = final_value - present_value
        while abs(delta) > step_size:
            forcing_channel.write(
                present_value +
                float(step_size) *
                self._direction(delta))
            present_value = forcing_channel.read()
            delta = final_value - present_value
            if self.verbose:
                print(
                    "Linear ramping channel: {} to: {}".format(
                        forcing_channel.get_name(),
                        forcing_channel.read()))
        forcing_channel.write(final_value)

    def _ramp_overshoot(self, forcing_channel, final_value,
                        abstol, estimated_overshoot):
        present_value = forcing_channel.read()
        if present_value is None:
            raise Exception(
                'Error: must write a value to underlying channel {} before using {}.'.format(
                    forcing_channel.get_name(), self.get_name()))
        delta = final_value - present_value
        direction = self._direction(delta)
        # calculate next output such that output+overshoot <= final_value +/- abstol
        # x + (x-pv)*estimated_overshoot = final_value + sign*abstol
        next = (final_value + direction * abstol + present_value *
                estimated_overshoot) / (1 + estimated_overshoot)
        while direction == 1 and next < final_value or direction == -1 and next > final_value:
            forcing_channel.write(next)
            if self.verbose:
                peak = next + (next - present_value) * estimated_overshoot
                print(
                    "Controlled overshoot stepping channel: {} to: {} with estimated overshoot to: {}".format(
                        forcing_channel.get_name(),
                        forcing_channel.read(),
                        peak))
            present_value = forcing_channel.read()
            next = (final_value + direction * abstol + present_value *
                    estimated_overshoot) / (1 + estimated_overshoot)
        forcing_channel.write(final_value)


class peak_finder(instrument):
    """Virtual instrument that finds the peak of one channel given a second channel as an input.

    The function is assumed to be unimodal. The channels used with this instrument may want to
    be virtual instruments. For example the output channel could be the computation of efficiency
    from several other channels. The peak is found by recursively performing a ternary search.

    >>> from PyICe.virtual_instruments import peak_finder
    >>> peak_finder is not None
    True

    """
    def __init__(self,
                 input_channel,
                 output_channel,
                 reltol):
        """Input_force_channel - Parameter to be swept.

        output_sense_channel - Parameter presumed to have a peak.
        searchstart - left side of search region (lowest value).
        searchstop - right side of search region (highest value).
        reltol - resolution of search. search stops when center of search region is within this percentage of searchstart and searchstop.


        >>> from PyICe.virtual_instruments import peak_finder
        >>> hasattr(peak_finder, '__init__')
        True

        Args:
            input_channel: Input channel to use.
            output_channel: Channel used for stimulus output.
            reltol: Relative tolerance.
        """
        self._base_name = 'peak_finder_{}_{}'.format(
            input_channel.get_name(), output_channel.get_name())
        instrument.__init__(
            self, "Peak_finder virtual instrument forcing:{} reading:{}".format(
                input_channel.get_name(), output_channel.get_name()))
        self._reltol = float(reltol)
        self._input_channel = input_channel
        self._output_channel = output_channel
        self._peak = None
        self._abscissa = None
        self._successful = None

    def add_channel_peak(self, channel_name):
        """The peak value found if the search was successful.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import peak_finder
        >>> hasattr(peak_finder, 'add_channel_peak')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self._peak)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_peak.__doc__)
        return self._add_channel(new_channel)

    def add_channel_abscissa(self, channel_name, auto_find=False):
        """The value of the input variable at which the peak occurred.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import peak_finder
        >>> hasattr(peak_finder, 'add_channel_abscissa')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self._abscissa)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_abscissa.__doc__)
        return self._add_channel(new_channel)

    def add_channel_successful(self, channel_name, auto_find=False):
        """Indicates whether or not the search was successful or failed due to lost peak before reltol. Try increasing reltol upon return of False.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import peak_finder
        >>> hasattr(peak_finder, 'add_channel_successful')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self._successful)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_successful.__doc__)
        return self._add_channel(new_channel)

    def find(self, searchstart, searchstop):
        """Return the find.

        Searches the collection and returns the matching item or index.


        >>> from PyICe.virtual_instruments import peak_finder
        >>> hasattr(peak_finder, 'find')
        True

        Args:
            searchstart: Searchstart to use.
            searchstop: Searchstop to use.
        """
        self._input_channel.write(searchstart)
        y1 = self._output_channel.read()
        self._input_channel.write(
            searchstart + (searchstop - searchstart) / 3.)
        y2 = self._output_channel.read()
        self._input_channel.write(searchstop - (searchstop - searchstart) / 3.)
        y3 = self._output_channel.read()
        self._input_channel.write(searchstop)
        y4 = self._output_channel.read()
        self._input_channel.write((searchstart + searchstop) / 2.)
        valmid = self._output_channel.read()
        erra = abs((valmid - y1) / valmid)
        errb = abs((valmid - y4) / valmid)
        if erra <= self._reltol and errb <= self._reltol:
            self._peak = valmid
            self._abscissa = (searchstart + searchstop) / 2.
            self._successful = True
            return
        elif y2 - y1 > 0 and y3 - y2 > 0:
            return self.find(searchstart + (searchstop -
                             searchstart) / 3., searchstop)
        elif y3 - y2 < 0 and y4 - y3 < 0:
            return self.find(searchstart, searchstop -
                             (searchstop - searchstart) / 3.)
        else:
            self._successful = False
            return


class ThresholdFinderError(Exception):
    """Non-specific threshold finder error.

    >>> from PyICe.virtual_instruments import ThresholdFinderError
    >>> raise ThresholdFinderError("test")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ThresholdFinderError: test

    """


class ThresholdUndetectableError(ThresholdFinderError):
    """Threshold finder unable to detect threshold. Perhaps the search range is wrong or perhaps the threshold doesn't exist. Not used for general configuration errors that should almost never be caught.

    >>> from PyICe.virtual_instruments import ThresholdUndetectableError
    >>> raise ThresholdUndetectableError("test")
    Traceback (most recent call last):
        ...
    PyICe.virtual_instruments.ThresholdUndetectableError: test

    """


class threshold_finder(instrument, delegator):
    """Virtual instrument that finds comparator thresholds via binary or linear search.

    Does not automatically find threshold unless auto_find is enabled from add_channel. Otherwise, you must call threshold_finder.find(), or .find_linear()

    >>> from PyICe.virtual_instruments import threshold_finder
    >>> threshold_finder is not None
    True

    The channels used with this instrument may want to be virtual instruments. For example the comparator_input_channel_force
    could be used to clear a latched output before a new value is set, or the comparator_output_sense_channel could interpret complex
    comparator outputs that are not direct measurements.

    Note that these search algorithms are sensitive to absolute repeatability.
    The DUT must not return different output values for the same forced values (within abstol and noise limits).
    If it does, the search will permanently take a wrong turn and fail.

    If the search algorithm is failing, check the properties of the input forcing channel and the DUT. Specifically:
    1) Make sure the forcing channel doesn't overshoot.
    a) If it does, update the forcing_overshoot parameter to a larger number and consider using a less aggressive search algorithm.
    b) Also consider a better forcing instrument with negligible overshoot (SMU, etc)
    2) Make sure the forcing instrument has settled before the DUT output measurement is taken.
    a) Consider [comparator_input_force_channel].set_write_delay(some_time)
    b) Also consider a better forcing instrument with rapid settling (SMU, etc)
    3) Make sure the DUT has settled after the forcing input channel has settled.
    a) This time can be quite long with nearly zero overdrive (forced input very close to true threshold)
    b) This time tents to infinity with zero overdrive, but we are only guaranteeing results to within abstol
    c) Therefore, the DUT should have sufficient time to settle with |abstol| overdrive applied after forcing channel has settled.
    d) Add this worst case DUT settling time to the forcing channel delay above.

    """
    def __init__(self, comparator_input_force_channel,
                 comparator_output_sense_channel,
                 minimum,
                 maximum,
                 abstol,
                 comparator_input_sense_channel=None,
                 forcing_overshoot=0,
                 output_threshold=None,
                 verbose=False):
        """Comparator_input_force_channel - DUT comparator input forcing channel object.

        comparator_output_sense_channel - DUT comparator output measurement channel object.
        minimum - minimum forced input to the DUT comparator via comparator_input_force_channel.
        maximum - maximum forced input to the DUT comparator via comparator_input_force_channel.
        abstol - resolution of search. Relative to comparator_input_channel_force, not comparator_input_sense_channel.
        comparator_input_sense_channel - optionally specify a channel object to read back actual (Kelvin) input to DUT from comparator_input_force_channel.
        forcing_overshoot - optionally specify an expected overshoot of forcing channel as a fraction of setting change. Steps toward threshold will be magnitude-controlled to keep peak value within abstol of target. Over-estimation will slow down search and Under-estimation may corrupt search results.
        output_threshold - optional digitization level threshold for comparator_output_sense_channel. If unspecified, will be calculated from mean of comparator_output_sense_channel reading with comparator_input_channel_force set to minimum and maximum.
        verbose - print extra information about search progress.
        cautious - take extra measurements to make sure search is proceeding correctly and has not been corrupted by overshoot, oscillation, etc.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '__init__')
        True

        Args:
            abstol: Absolute tolerance.
            comparator_input_force_channel: Comparator input force channel to use.
            comparator_input_sense_channel: Comparator input sense channel to use.
            comparator_output_sense_channel: Comparator output sense channel to use.
            forcing_overshoot: Forcing overshoot to use.
            maximum: Maximum value.
            minimum: Minimum value.
            output_threshold: Output threshold to use.
            verbose: If True, print debug output.
        """
        self._base_name = 'threshold_finder_{}_{}'.format(
            comparator_input_force_channel.get_name(),
            comparator_output_sense_channel.get_name())
        instrument.__init__(
            self,
            "Threshold_finder virtual instrument forcing:{} reading:{}".format(
                comparator_input_force_channel.get_name(),
                comparator_output_sense_channel.get_name()))
        delegator.__init__(self)
        self._output_threshold = None
        self._output_threshold_calc = None
        self.verbose = verbose
        self.reconfigure(comparator_input_force_channel,
                         comparator_output_sense_channel,
                         comparator_input_sense_channel,
                         output_threshold,
                         minimum,
                         maximum,
                         abstol,
                         forcing_overshoot)

        self.max_tries = 50
        self.auto_find = False
        # default output before first find()
        self.threshold = None
        self.rising = None
        self.falling = None
        self.tries = None
        self.hysteresis = None
        self.forced_rising = None
        self.forced_falling = None
        self.rising_uncertainty = None
        self.falling_uncertainty = None
        self.rising_relative_uncertainty = None
        self.falling_relative_uncertainty = None
        self.search_algorithm = None
        self.results_dictionary = None

    def reconfigure(self, comparator_input_force_channel,
                    comparator_output_sense_channel,
                    comparator_input_sense_channel,
                    output_threshold=None,
                    minimum=None,
                    maximum=None,
                    abstol=None,
                    forcing_overshoot=None):
        """Reconfigure channel settings to use a single threshold finder instrument with multiplexed DUT channels.

        Required arguments:
        comparator_input_force_channel - DUT comparator input forcing channel object.
        comparator_output_sense_channel - DUT comparator output measurement channel object.
        comparator_input_sense_channel - optionally specify a channel object to read back actual (Kelvin) input to DUT from comparator_input_force_channel. Set to None to disable.

        Optional argument (set to automatic if unspecified):
        output_threshold - optional digitization level threshold for comparator_output_sense_channel. If unspecified, will be calculated from mean of comparator_output_sense_channel reading with comparator_input_channel_force set to minimum and maximum.

        Optional arguments (unchanged if unspecified):
        minimum - minimum forced input to the DUT comparator via comparator_input_force_channel.
        maximum - maximum forced input to the DUT comparator via comparator_input_force_channel.
        abstol - resolution of search. Relative to comparator_input_channel_force, not comparator_input_sense_channel.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'reconfigure')
        True

        Args:
            abstol: Absolute tolerance.
            comparator_input_force_channel: Comparator input force channel to use.
            comparator_input_sense_channel: Comparator input sense channel to use.
            comparator_output_sense_channel: Comparator output sense channel to use.
            forcing_overshoot: Forcing overshoot to use.
            maximum: Maximum value.
            minimum: Minimum value.
            output_threshold: Output threshold to use.

        Raises:
            ThresholdFinderError: If the operation fails.
        """
        self._comparator_input_channel = comparator_input_force_channel
        self._comparator_output_sense_channel = comparator_output_sense_channel
        self._comparator_input_sense_channel = comparator_input_sense_channel

        self._output_threshold = output_threshold

        if minimum is not None:
            self._minimum = float(minimum)
        if maximum is not None:
            self._maximum = float(maximum)
        if abstol is not None:
            self._abstol = float(abstol)
        if forcing_overshoot is not None:
            self._forcing_overshoot = forcing_overshoot

        if self._abstol <= 0:
            raise ThresholdFinderError('abstol must be finite and positive')
        if isinstance(self._comparator_input_channel,
                      integer_channel) and self._abstol < 1:
            raise ThresholdFinderError(
                'integer-forced abstol cannot be less than 1')
        if self._minimum >= self._maximum:
            raise ThresholdFinderError('minimum must be less than maximum')

        self._ramper = ramp_to(self.verbose)
        if self._forcing_overshoot != 0:
            self._comparator_input_ramper = self._ramper.add_channel_overshoot('input_ramper',
                                                                               forcing_channel=self._comparator_input_channel,
                                                                               abstol=self._abstol,
                                                                               estimated_overshoot=self._forcing_overshoot)
        else:
            self._comparator_input_ramper = self._comparator_input_channel

    def add_channel_all(self, channel_name, auto_find=False):
        """Shortcut method adds the following channels:.

        threshold (Average of rising and falling thresholds. Relative to comparator_input_sense_channel.)
        rising threshold (Average of measurements at low and high endpoints of rising threshold uncertainty window. Relative to comparator_input_sense_channel.)
        falling threshold (Average of measurements at low and high endpoints of falling threshold uncertainty window. Relative to comparator_input_sense_channel.)
        tries (Number of binary search steps required to reduce uncertainty window to within abstol, or number of abstol-sized steps required to find threshold with linear search.)
        hysteresis (Difference between rising and falling thresholds. Relative to comparator_input_sense_channel.)
        abstol (Maximum two-sided uncertainty range (window width) for binary search, or step size for linear search. Relative to comparator_input_force_channel.)
        rising uncertainty (Achieved one-sided additive rising threshold uncertainty range for binary or linear search. Relative to comparator_input_sense_channel.)
        falling uncertainty (Achieved one-sided additive falling threshold uncertainty range for binary or linear search. Relative to comparator_input_sense_channel.)
        rising relative uncertainty (Achieved one-sided multiplicative rising threshold uncertainty range for binary or linear search. Relative to comparator_input_sense_channel.)
        falling relative uncertainty (Achieved one-sided multiplicative falling threshold uncertainty range for binary or linear search. Relative to comparator_input_sense_channel.)
        forced rising threshold (Average of low and high forced endpoints of rising threshold uncertainty window. Relative to comparator_input_force_channel.)
        forced falling threshold (Average of low and high forced endpoints of falling threshold uncertainty window. Relative to comparator_input_force_channel.)
        output_threshold (Calculated or specified digitization threshold for comparator_output_sense_channel.)

        if auto_find is 'linear', automatically call find_linear() when channel is read.
        if auto_find is 'geometric', automatically call find_geometric() when channel is read.
        if auto_find is any other true value, automatically call find() when channel is read.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_all')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        # Read channels
        th = self.add_channel_threshold(channel_name + "_average", auto_find)
        self.add_channel_rising(channel_name + "_rising")
        self.add_channel_falling(channel_name + "_falling")
        self.add_channel_tries(channel_name + "_tries")
        self.add_channel_hysteresis(channel_name + "_hysteresis")
        self.add_channel_abstol(channel_name + "_abstol")
        self.add_channel_uncertainty(channel_name + "_uncertainty")
        self.add_channel_relative_uncertainty(
            channel_name + "_relative_uncertainty")
        self.add_channel_forced_rising(channel_name + "_forced_rising")
        self.add_channel_forced_falling(channel_name + "_forced_falling")
        self.add_channel_output_threshold(channel_name + "_output_threshold")
        self.add_channel_algorithm(channel_name + "_search_algorithm")
        # Configuration channels
        self.add_channel_output_threshold_setpoint(
            channel_name + "_output_threshold_setpoint")
        # TODO more needed?
        return th
    # Results channels:

    def add_channel_threshold(self, channel_name, auto_find=False):
        """Average of rising and falling thresholds found by last call to find() method.

        Relative to comparator_input_sense_channel.
        if auto_find is 'linear', automatically call find_linear() when channel is read.
        if auto_find is 'geometric', automatically call find_geometric() when channel is read.
        if auto_find is any other true value, automatically call find() when channel is read.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_threshold')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.threshold)
        self.auto_find = auto_find
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_threshold.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_rising(self, channel_name):
        """Average of measurements at low and high endpoints of rising threshold uncertainty window. Relative to comparator_input_sense_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_rising')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self.rising)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_rising.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_falling(self, channel_name):
        """Average of measurements at low and high endpoints of falling threshold uncertainty window. Relative to comparator_input_sense_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_falling')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self.falling)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_falling.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_tries(self, channel_name):
        """Number of binary search steps required to reduce uncertainty window to within abstol, or number of abstol-sized steps required to find threshold with linear search.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_tries')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self.tries)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_tries.__doc__)
        new_channel.set_delegator(self)
        self._add_channel(new_channel)
        return new_channel

    def add_channel_hysteresis(self, channel_name):
        """Difference between rising and falling thresholds. Relative to comparator_input_sense_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_hysteresis')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.hysteresis)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_hysteresis.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_abstol(self, channel_name):
        """Maximum two-sided uncertainty range (window width) for binary search, or step size for linear search. Relative to comparator_input_force_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_abstol')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, read_function=lambda: self._abstol)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_abstol.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_uncertainty(self, channel_name):
        """Single sided measured threshold uncertainty at termination of search.

        i.e (threshold_rising - uncertainty_rising) < {true rising threshold} < (threshold_rising + uncertainty_rising) and
        (threshold_falling - uncertainty_falling) < {true falling threshold} < (threshold_falling + uncertainty_falling).

        For binary search with comparator_input_sense_channel=None, will be between 0.5*abstol and 0.25*abstol.
        For linear sweep with comparator_input_sense_channel=None, will be 0.5*abstol.

        With comparator_input_sense_channel defined, uncertainty will be relative to measured rather than forced inputs and may be scaled differently than forcing (abstol) units.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_uncertainty')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        rising_threshold_uncertainty_channel = channel(
            channel_name + "_rising", read_function=lambda: self.rising_uncertainty)
        rising_threshold_uncertainty_channel.set_description(
            self.get_name() + ': ' + self.add_channel_uncertainty.__doc__)
        rising_threshold_uncertainty_channel.set_delegator(self)
        self._add_channel(rising_threshold_uncertainty_channel)
        falling_threshold_uncertainty_channel = channel(
            channel_name + "_falling", read_function=lambda: self.falling_uncertainty)
        falling_threshold_uncertainty_channel.set_description(
            self.get_name() + ': ' + self.add_channel_uncertainty.__doc__)
        falling_threshold_uncertainty_channel.set_delegator(self)
        self._add_channel(falling_threshold_uncertainty_channel)
        return rising_threshold_uncertainty_channel

    def add_channel_relative_uncertainty(self, channel_name):
        """Single sided relative measured threshold uncertainty at termination of search.

        i.e threshold_rising * (1 - relative_uncertainty_rising) < {true rising threshold} < threshold_rising * (1 + relative_uncertainty_rising) and
        threshold_falling * (1 - relative_uncertainty_falling) < {true falling threshold} < threshold_falling * (1 + relative_uncertainty_falling)

        With comparator_input_sense_channel defined, uncertainty will be relative to measured rather than forced inputs and may be scaled differently than forcing (abstol) units.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_relative_uncertainty')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        rising_threshold_relative_uncertainty_channel = channel(
            channel_name + "_rising", read_function=lambda: self.rising_relative_uncertainty)
        rising_threshold_relative_uncertainty_channel.set_description(
            self.get_name() + ': ' + self.add_channel_relative_uncertainty.__doc__)
        rising_threshold_relative_uncertainty_channel.set_delegator(self)
        self._add_channel(rising_threshold_relative_uncertainty_channel)
        falling_threshold_relative_uncertainty_channel = channel(
            channel_name + "_falling",
            read_function=lambda: self.falling_relative_uncertainty)
        falling_threshold_relative_uncertainty_channel.set_description(
            self.get_name() + ': ' + self.add_channel_relative_uncertainty.__doc__)
        falling_threshold_relative_uncertainty_channel.set_delegator(self)
        self._add_channel(falling_threshold_relative_uncertainty_channel)
        return rising_threshold_relative_uncertainty_channel

    def add_channel_forced_rising(self, channel_name):
        """Average of low and high forced endpoints of rising threshold uncertainty window. Relative to comparator_input_force_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_forced_rising')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.forced_rising)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_forced_rising.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_forced_falling(self, channel_name):
        """Average of low and high forced endpoints of falling threshold uncertainty window. Relative to comparator_input_force_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_forced_falling')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.forced_falling)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_forced_falling.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_output_threshold(self, channel_name):
        """Computed digitization threshold for comparator_output_sense_channel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_output_threshold')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: self._output_threshold_calc)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_output_threshold.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_algorithm(self, channel_name):
        """Search method used to determine threshold.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_algorithm')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name,
                              read_function=lambda: self.search_algorithm)
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_algorithm.__doc__)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)
    # Configuration channels:

    def add_channel_output_threshold_setpoint(self, channel_name):
        """Digitization threshold setpoint for comparator_output_sense_channel. Caution: a reconfigure() command outsize the channel framework will un-sync this parameter.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Sends the ``:`` SCPI command to the instrument.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'add_channel_output_threshold_setpoint')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name, write_function=lambda val: setattr(
                self, '_output_threshold', val))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_output_threshold_setpoint.__doc__)
        new_channel.write(self._output_threshold)
        new_channel.set_delegator(self)
        return self._add_channel(new_channel)
    # Internal:

    def _write_comparator_input(self, value, controlled):
        """Set forced input to DUT comparator.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_write_comparator_input')
        True

        Args:
            controlled: Controlled to use.
            value: Value to set.
        """
        if controlled:
            self._comparator_input_ramper.write(value)
        else:
            self._comparator_input_channel.write(value)

    def _read_comparator_output(self):
        """Measure analog output of DUT comparator.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_read_comparator_output')
        True

        Returns:
            The measured value.
        """
        return self._comparator_output_sense_channel.read()

    def _read_input_sense(self, input_set):
        """Measure sensed input to DUT comparator.

        Data is stored internally for future use.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_read_input_sense')
        True

        Args:
            input_set: Input set to use.

        Returns:
            The measured value.
        """
        if self._comparator_input_sense_channel is not None:
            sensed_input = self._comparator_input_sense_channel.read()
            self.debug_print(
                msg=f'comparator_input_sense_channel: {sensed_input}')
            self._input_reads[input_set] = sensed_input
            return sensed_input

    def _digitize_output(self, value):
        """Convert analog output to boolean by polarity-aware comparison with threshold.
        Internal helper that computes and returns a derived value.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_digitize_output')
        True

        Args:
            value: Value to set.

        Returns:
            The digitize output result.
        """
        if self.pol > 0:
            return value > self._output_threshold_calc
        else:
            return value < self._output_threshold_calc

    def _test(self, input_force, measure_input, controlled):
        """Private procedure to test each point during sweep.

        1) write new value to comparator_input_force_channel
        2) read comparator_output_sense_channel and digitize
        3) optionally read comparator_input_sense_channel and store for future reference
        4) return results dict


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_test')
        True

        Args:
            controlled: Controlled to use.
            input_force: Input force to use.
            measure_input: Measure input to use.

        Returns:
            The test result.
        """
        self._write_comparator_input(input_force, controlled)
        output_analog = self._read_comparator_output()
        try:
            output_digital = self._digitize_output(output_analog)
        except AttributeError:
            # can't digitize output before threshold and polarity have been
            # determined
            output_digital = None
        if measure_input:
            sensed_input = self._read_input_sense(input_force)
        else:
            sensed_input = None
        self._intermediate_results[input_force] = {'forced_input': input_force,
                                                   'output_analog': output_analog,
                                                   'output_digital': output_digital,
                                                   'sensed_input': sensed_input
                                                   }
        return self._intermediate_results[input_force]

    def _check_polarity(self):
        # fill the variables
        self.begin_time = time.time()
        self._input_reads = {}  # TODO: consider merging with _intermediate_results?
        self._intermediate_results = {}

        self.debug_print("------------------------------")
        self.debug_print(
            "Check polarity and output digitizer threshold.")

        # get the polarity
        low_test = self._test(
            self._integer_round(
                self._minimum),
            measure_input=True,
            controlled=False)
        self.debug_print(
            "Measured low output: {} at input: {}".format(
                low_test['output_analog'],
                self._minimum))
        high_test = self._test(
            self._integer_round(
                self._maximum),
            measure_input=True,
            controlled=False)
        self.debug_print(
            "Measured high output: {} at input: {}".format(
                high_test['output_analog'],
                self._maximum))
        if high_test['output_analog'] == low_test['output_analog']:
            raise ThresholdUndetectableError(
                f'{self.get_name()}: Comparator output unchanged at max and min input forcing levels!')
        if low_test['output_analog'] < high_test['output_analog']:
            self.pol = 1
        else:
            self.pol = -1
        if self._output_threshold is not None:
            self._output_threshold_calc = self._output_threshold
            if self._digitize_output(high_test['output_analog']) == self._digitize_output(
                    low_test['output_analog']):
                raise ThresholdUndetectableError(
                    f'{self.get_name()}: Comparator digital output unchanged at max and min input forcing levels with specified threshold {self._output_threshold}!')
        else:
            self._output_threshold_calc = (
                high_test['output_analog'] + low_test['output_analog']) / 2.0
        self.debug_print("Threshold: {}".format(self._output_threshold_calc))
        self.debug_print("Polarity: {}1".format("+" if self.pol == 1 else "-"))

    def _compute_outputs(self):
        """Shared math for binary and linear search outputs.

        Takes instance variables self.falling_min, self.falling_max, self.rising_min, self.rising_max as input.
        Stores output instance variables self.forced_rising, self.forced_falling, self.rising, self.falling, self.hysteresis, self.threshold, self.rising_uncertainty, self.falling_uncertainty, self.rising_relative_uncertainty, self.falling_relative_uncertainty.
        Passes through self.tries, self._abstol.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_compute_outputs')
        True

        Returns:
            The compute outputs result.
        """
        self.forced_rising = (self.rising_min + self.rising_max) / 2.0
        self.forced_falling = (self.falling_min + self.falling_max) / 2.0
        if self._comparator_input_sense_channel is not None:
            # replace comparator_input_channel_force values with
            # comparator_input_sense_channel values.
            try:
                self.rising = (
                    self._input_reads[self.rising_max] + self._input_reads[self.rising_min]) / 2.0
                self.falling = (
                    self._input_reads[self.falling_max] + self._input_reads[self.falling_min]) / 2.0
                self.rising_uncertainty = max(
                    self._input_reads[self.rising_max] - self.rising, self.rising - self._input_reads[self.rising_min])
                self.falling_uncertainty = max(
                    self._input_reads[self.falling_max] - self.falling, self.falling - self._input_reads[self.falling_min])
                self.rising_relative_uncertainty = max(
                    self._input_reads[self.rising_max] / self.rising - 1, 1 - self._input_reads[self.rising_min] / self.rising)
                self.falling_relative_uncertainty = max(
                    self._input_reads[self.falling_max] / self.falling - 1, 1 - self._input_reads[self.falling_min] / self.falling)
            except (KeyError, Exception) as excp:
                print("Something is wrong with the threshold finder instrument.")
                print(excp)
                import pdb
                pdb.set_trace()
        else:
            self.rising = self.forced_rising
            self.falling = self.forced_falling
            self.rising_uncertainty = (self.rising_max - self.rising_min) / 2.0
            self.falling_uncertainty = (
                self.falling_max - self.falling_min) / 2.0
            self.rising_relative_uncertainty = self.rising_uncertainty / self.rising
            self.falling_relative_uncertainty = self.falling_uncertainty / self.falling
        self.hysteresis = self.rising - self.falling
        self.threshold = (self.rising + self.falling) / 2.0
        self.elapsed_time = time.time() - self.begin_time
        self.results_dictionary = results_ord_dict((
            ("threshold", self.threshold),
            ("rising", self.rising),
            ("falling", self.falling),
            ("hysteresis", self.hysteresis),
            ("forced_rising", self.forced_rising),
            ("forced_falling", self.forced_falling),
            ("rising_uncertainty", self.rising_uncertainty),
            ("falling_uncertainty", self.falling_uncertainty),
            ("rising_relative_uncertainty", self.rising_relative_uncertainty),
            ("falling_relative_uncertainty", self.falling_relative_uncertainty),
            ("polarity", self.pol),
            ("tries", self.tries),
            ("abstol", self._abstol),
            ("elapsed_time", self.elapsed_time),
            ("output_threshold", self._output_threshold_calc),
            ("search_algorithm", self.search_algorithm)
        ))
        self.debug_print("Search results:")
        self.debug_print(self.results_dictionary)
        return self.results_dictionary

    def measure_input(self, input_sense_channel):
        """Measure input sense (Kelvin) channel manually after completion of search algorithm.

        This may be somewhat less accurate than measuring sense channel during search.
        It exposes possibly non-ideal hysteresis or gain/offset drift of the forcing instrument by uncorrelating measurements in time.

        Typically used with comparator_input_sense_channel=None to speed up search at each point.
        Updates and returns internal results dictionary.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'measure_input')
        True

        Args:
            input_sense_channel: Input sense channel to use.

        Returns:
            The measure input result.

        Raises:
            ThresholdFinderError: If the operation fails.
        """
        self.debug_print("Post-measuring input sense....")
        if self.results_dictionary is None:
            raise ThresholdFinderError(
                'ERROR: Must complete a threshold search before calling this method.')
        begin_time = time.time()
        self._write_comparator_input(self._minimum, controlled=False)
        self._write_comparator_input(self.rising_min, controlled=False)
        rising_min_sense = input_sense_channel.read()
        self._write_comparator_input(self.rising_max, controlled=False)
        rising_max_sense = input_sense_channel.read()
        self.rising = (rising_min_sense + rising_max_sense) / 2.0

        self._write_comparator_input(self._maximum, controlled=False)
        self._write_comparator_input(self.falling_max, controlled=False)
        falling_max_sense = input_sense_channel.read()
        self._write_comparator_input(self.falling_min, controlled=False)
        falling_min_sense = input_sense_channel.read()
        self.falling = (falling_min_sense + falling_max_sense) / 2.0

        self.hysteresis = self.rising - self.falling
        self.threshold = (self.rising + self.falling) / 2.0
        self.elapsed_time += time.time() - begin_time

        self.rising_uncertainty = max(
            rising_max_sense - self.rising,
            self.rising - rising_min_sense)
        self.falling_uncertainty = max(
            falling_max_sense - self.falling,
            self.falling - falling_min_sense)
        self.rising_relative_uncertainty = max(
            rising_max_sense / self.rising - 1,
            1 - rising_min_sense / self.rising)
        self.falling_relative_uncertainty = max(
            falling_max_sense / self.falling - 1,
            1 - falling_min_sense / self.falling)

        self.results_dictionary["rising"] = self.rising
        self.results_dictionary["falling"] = self.falling
        self.results_dictionary["threshold"] = self.threshold
        self.results_dictionary["hysteresis"] = self.hysteresis
        self.results_dictionary["elapsed_time"] = self.elapsed_time
        self.results_dictionary["rising_uncertainty"] = self.rising_uncertainty
        self.results_dictionary["falling_uncertainty"] = self.falling_uncertainty
        self.results_dictionary["rising_relative_uncertainty"] = self.rising_relative_uncertainty
        self.results_dictionary["falling_relative_uncertainty"] = self.falling_relative_uncertainty
        self.debug_print("Updated results with input sense:")
        for k, v in self.results_dictionary.items():
            self.debug_print("\t{}: {}".format(k, v))
        return self.results_dictionary

    def debug_print(self, msg):
        """Perform debug print operation.

        Supports the ``threshold_finder`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'debug_print')
        True

        Args:
            msg: Message string to display.
        """
        if self.verbose:
            print(msg)

    def _integer_round(self, value):
        if isinstance(self._comparator_input_channel, integer_channel):
            return int(round(value))
        else:
            return value

    def find(self, cautious=False):
        """Hysteresis-aware double binary search.

        Returns dictionary of results.
        if cautious, perform extra measurement at each step to ensure hysteresis flips and search region has not been corrupted.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find')
        True

        Args:
            cautious: Cautious to use.

        Returns:
            The index of the first match, or -1 if not found.

        Raises:
            ThresholdFinderError: If the operation fails.
        """
        self._check_polarity()
        self.rising_min = self._minimum
        self.rising_max = self._maximum
        self.falling_min = self._minimum
        self.falling_max = self._maximum
        # Binary searching a given interval to within a given abstol always
        # takes the same number of steps.
        abstol_divisions = (self._maximum - self._minimum) / self._abstol
        self.tries = max(int(math.ceil(math.log(abstol_divisions, 2))), 0)
        self.debug_print("------------------------------")
        self.debug_print(
            "Binary searching with {} iterations".format(
                self.tries))
        assert self.tries <= self.max_tries
        for cnt in range(self.tries):
            self.debug_print("-----------------")
            # work on falling threshold
            self.debug_print(
                "Falling Min: {} Max: {}".format(
                    self.falling_min,
                    self.falling_max))
            assert self.falling_max > self.falling_min, "Falling search window closed."
            # cross high threshold to look for low
            reset = self._integer_round(
                min(self.rising_max + self._abstol, self._maximum))
            if cautious and not self._test(reset, measure_input=False, controlled=False)[
                    'output_digital']:
                raise ThresholdFinderError(
                    'Failed to change comparator output high at: {}. Check comparator_input_channel overshoot and adjust forcing_overshoot.'.format(reset))
            elif not cautious:
                self._write_comparator_input(reset, controlled=False)
            new_value = self._integer_round(
                (self.falling_max + self.falling_min) / 2.0)
            self.debug_print("Try {}".format(new_value))
            test_result = self._test(
                new_value, measure_input=True, controlled=True)
            self.debug_print(
                "Output Analog: {}".format(
                    test_result['output_analog']))
            self.debug_print(
                "Output Digital: {}".format(
                    test_result['output_digital']))
            if test_result['output_digital']:
                self.falling_max = new_value
            else:
                self.falling_min = new_value
            self.debug_print("------")
            # work on rising threshold
            self.debug_print(
                "Rising Min: {} Max: {}".format(
                    self.rising_min,
                    self.rising_max))
            assert self.falling_max > self.falling_min, "Rising search window closed."
            # cross low threshold to look for high
            reset = self._integer_round(
                max(self.falling_min - self._abstol, self._minimum))
            if cautious and self._test(reset, measure_input=False, controlled=False)[
                    'output_digital']:
                raise ThresholdFinderError(
                    'Failed to change comparator output low at: {}. Check comparator_input_channel overshoot and adjust forcing_overshoot.'.format(reset))
            elif not cautious:
                self._write_comparator_input(reset, controlled=False)
            new_value = self._integer_round(
                (self.rising_max + self.rising_min) / 2.0)
            self.debug_print("Try: {}".format(new_value))
            test_result = self._test(
                new_value, measure_input=True, controlled=True)
            self.debug_print(
                "Output Analog: {}".format(
                    test_result['output_analog']))
            self.debug_print(
                "Output Digital: {}".format(
                    test_result['output_digital']))
            if test_result['output_digital']:
                self.rising_max = new_value
            else:
                self.rising_min = new_value
        self.debug_print("-----------------")
        self.search_algorithm = "binary search"
        res = self._compute_outputs()
        return res

    def find_no_hysteresis(self, cautious=False):
        """Hysteresis-unaware single binary search.

        Returns dictionary of results.
        If cautious, perform extra measurment at each step to ensure that the threashold is still bounded by the current search interval.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find_no_hysteresis')
        True

        Args:
            cautious: Cautious to use.

        Returns:
            The find no hysteresis result.

        Raises:
            ThresholdFinderError: If the operation fails.
        """
        self._check_polarity()
        th_min = self._minimum
        th_max = self._maximum

        # Binary searching a given interval to within a given abstol always
        # takes the same number of steps.
        abstol_divisions = (self._maximum - self._minimum) / self._abstol
        self.tries = max(int(math.ceil(math.log(abstol_divisions, 2))), 0)
        self.debug_print("------------------------------")
        self.debug_print(
            "Binary searching with {} iterations, ignoring hysteresis.".format(
                self.tries))
        assert self.tries <= self.max_tries
        for cnt in range(self.tries):
            self.debug_print("-----------------")
            self.debug_print("Min: {} Max: {}".format(th_min, th_max))
            new_value = self._integer_round((th_max + th_min) / 2.0)
            self.debug_print("Try {}".format(new_value))
            test_result = self._test(
                new_value, measure_input=True, controlled=True)
            self.debug_print(
                "Output Analog: {}".format(
                    test_result['output_analog']))
            self.debug_print(
                "Output Digital: {}".format(
                    test_result['output_digital']))
            if test_result['output_digital']:
                th_max = new_value
                if cautious and self._test(th_min, measure_input=False, controlled=False)[
                        'output_digital']:
                    raise ThresholdFinderError(
                        f'Failed to change comparator output low between: {th_min} and {th_max}. Check comparator_input_channel overshoot and adjust forcing_overshoot.')
            else:
                th_min = new_value
                if cautious and not self._test(th_max, measure_input=False, controlled=False)[
                        'output_digital']:
                    raise ThresholdFinderError(
                        f'Failed to change comparator output high between: {th_min} and {th_max}. Check comparator_input_channel overshoot and adjust forcing_overshoot.')
        self.debug_print("-----------------")
        self.search_algorithm = "binary search without hysteresis"
        # fill the input variables to _compute_outputs
        self.rising_min = th_min
        self.rising_max = th_max
        self.falling_min = th_min
        self.falling_max = th_max
        res = self._compute_outputs()
        return res

    def find_linear(self):
        """Hysteresis aware linear sweep. Returns dictionary of results.
        Searches for and returns the matching linear.

        Steps through a range of values, collecting data at each point.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find_linear')
        True

        Returns:
            The find linear result.
        """
        # todo integer awareness
        self._check_polarity()
        self.rising_min = self._minimum
        self.rising_max = self._maximum
        self.falling_min = self._minimum
        self.falling_max = self._maximum
        self.tries = 0
        self.debug_print("------------------------------")
        self.debug_print("Searching for rising threshold")
        self._find_linear_threshold(
            self._minimum,
            self._maximum,
            self._abstol)  # find rising threshold
        self.debug_print("-------------------------------")
        self.debug_print("Searching for falling threshold")
        # find falling threshold starting just after rising hysteresis flip.
        self._find_linear_threshold(
            self._minimum, self.rising_max, -1 * self._abstol)
        self.search_algorithm = "linear search"
        res = self._compute_outputs()
        return res

    def find_linear_no_hysteresis(self, rising_direction=True):
        """Hysteresis-unaware linear sweep. Returns dictionary of results. Optionally sweep in downward direction.
        Searches for and returns the matching linear no hysteresis.

        Steps through a range of values, collecting data at each point.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find_linear_no_hysteresis')
        True

        Args:
            rising_direction: Rising direction to use.

        Returns:
            The find linear no hysteresis result.
        """
        # todo integer awareness
        self._check_polarity()
        self.tries = 0
        if rising_direction:
            self.debug_print("------------------------------")
            self.debug_print("Searching for rising threshold")
            self.rising_min = self._minimum
            self.rising_max = self._maximum
            self._find_linear_threshold(
                self._minimum,
                self._maximum,
                self._abstol)  # find rising threshold
            self.falling_min = self.rising_min
            self.falling_max = self.rising_max
            self.search_algorithm = "single linear search - rising"
        else:
            self.debug_print("-------------------------------")
            self.debug_print("Searching for falling threshold")
            self.falling_min = self._minimum
            self.falling_max = self._maximum
            # find falling threshold starting just after rising hysteresis
            # flip.
            self._find_linear_threshold(
                self._minimum, self._maximum, -1 * self._abstol)
            self.rising_min = self.falling_min
            self.rising_max = self.falling_max
            self.search_algorithm = "single linear search - falling"
        res = self._compute_outputs()
        return res

    def find_geometric(self, decades=None):
        # todo integer awareness
        """Perform repeated linear searches for rising and falling thresholds with 10x increase in resolution each iteration.

        Final resolution is abstol
        Optionally specify decades argument to control how many searches are performed. Defaults to as many as possible for given min/max range and abstol.
        No steps are ever made toward the threshold with magnitude larger than current search's resolution in case of overshoot.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find_geometric')
        True

        Args:
            decades: Decades to use.

        Returns:
            The find geometric result.
        """
        self._check_polarity()
        self.rising_min = self._minimum
        self.rising_max = self._maximum
        self.falling_min = self._minimum
        self.falling_max = self._maximum
        self.tries = 0

        max_decades = int(
            math.floor(
                math.log(
                    (self._maximum - self._minimum) / self._abstol,
                    10))) + 1
        if decades is None:
            decades = max_decades
        assert decades >= 1
        assert isinstance(decades, int)
        assert decades <= max_decades
        cisc = self._comparator_input_sense_channel
        self._comparator_input_sense_channel = None
        for e in range(decades - 1, -1, -1):
            step_size = self._abstol * 10**e
            if e == 0:
                # only read back input on last sweep
                self._comparator_input_sense_channel = cisc
            self.debug_print("------------------------------")
            self.debug_print("Ramping to: {}".format(self.rising_min))
            self._write_comparator_input(
                self.rising_min, controlled=True)  # small steps toward threshold
            self.debug_print(
                "Searching for rising threshold with step size: {} between: {} and: {}".format(
                    step_size, self.rising_min, self.rising_max))
            self._find_linear_threshold(
                self.rising_min,
                self.rising_max,
                step_size)  # find rising threshold
            self.debug_print("-------------------------------")
            self.debug_print("Ramping to: {}".format(self.falling_max))
            self._write_comparator_input(
                self.falling_max,
                controlled=True)  # small steps toward threshold
            self.debug_print(
                "Searching for falling threshold with step size: {} between: {} and: {}".format(
                    step_size, self.falling_max, self.falling_min))
            # find falling threshold starting just after rising hysteresis
            # flip.
            self._find_linear_threshold(
                self.falling_min, self.falling_max, -1 * step_size)
            if e != 0:
                # account for possible forcing instrument overshoot in travel
                # direction
                self.rising_max = min(
                    self._maximum, self.rising_max + step_size)
                self.falling_min = max(
                    self._minimum, self.falling_min - step_size)
                # account for possible ambiguity due to delay/noise within
                # abstol.
                self.falling_max = min(
                    self._maximum, self.falling_max + self._abstol)
                self.rising_min = max(
                    self._minimum, self.rising_min - self._abstol)
        self.search_algorithm = "geometric linear search"
        res = self._compute_outputs()
        return res

    def find_hybrid(self, linear_backtrack=None):
        # todo integer awareness
        """Perform course binary search, then approach rising and falling thresholds from correct direction with linear search.

        Both binary and linear searches will be performed to abstol forcing tolerance.
        The linear search will be started linear_backtrack distance away from expected threshold, with default of 5 * reltol.
        Each of the two linear sweeps will take approximately (linear_backtrack / reltol) steps toward threshold.
        Steps toward threshold are of max magnitude max_step.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'find_hybrid')
        True

        Args:
            linear_backtrack: Linear backtrack to use.

        Returns:
            The find hybrid result.

        Raises:
            ThresholdFinderError: If the operation fails.
        """
        if linear_backtrack is None:
            linear_backtrack = 5 * self._abstol
        assert linear_backtrack >= self._abstol
        assert linear_backtrack > 0
        # First run quick binary search to get rough answers
        # Don't need to read back inputs for this phase.
        cisc = self._comparator_input_sense_channel
        self._comparator_input_sense_channel = None
        binary_res = self.find(cautious=True)
        self._comparator_input_sense_channel = cisc

        min_rising = binary_res['forced_rising'] - linear_backtrack
        max_rising = binary_res['forced_rising'] + linear_backtrack
        min_falling = binary_res['forced_falling'] - linear_backtrack
        max_falling = binary_res['forced_falling'] + linear_backtrack
        if min_rising < self._minimum or max_rising > self._maximum or min_falling < self._minimum or max_falling > self._maximum:
            raise ThresholdFinderError(
                'Hybrid sweep abstol: {} and linear_backtrack: {} too large for input range: {} to: {}.'.format(
                    self._abstol, linear_backtrack, self._minimum, self._maximum))

        # Then run one-sided linear search for rising threshold
        self.rising_min = None
        self.rising_max = None
        self.debug_print("------------------------------")
        # set hysteresis up for rising threshold
        reset = max(min_falling - self._abstol, self._minimum)
        self.debug_print(
            "Setting hysteresis state low and ramping from: {} to: {}".format(
                reset, min_rising))
        # start below falling threshold
        self._write_comparator_input(reset, controlled=False)
        self._write_comparator_input(
            min_rising, controlled=True)  # small steps back
        self.debug_print(
            "Linear searching for rising threshold between: {} and: {}".format(
                min_rising, max_rising))
        self._find_linear_threshold(
            min_rising,
            max_rising,
            self._abstol)  # then start looking
        if self.rising_min is None or self.rising_max is None:
            raise ThresholdFinderError(
                'Hybrid threshold finder failed to reset hysteresis before rising threshold linear sweep. Try increasing linear_backtrack.')

        # Then run one-sided linear search for falling threshold
        self.falling_min = None
        self.falling_max = None
        self.debug_print("------------------------------")
        # set hysteresis up for falling threshold
        reset = min(max_rising + self._abstol, self._maximum)
        self.debug_print(
            "Setting hysteresis state high and ramping from: {} to: {}".format(
                reset, max_falling))
        # start above rising threshold
        self._write_comparator_input(reset, controlled=False)
        self._write_comparator_input(
            max_falling, controlled=True)  # take small steps back
        self.debug_print(
            "Linear searching for falling threshold between: {} and: {}".format(
                max_falling, min_falling))
        self._find_linear_threshold(
            min_falling, max_falling, -1 * self._abstol)  # then start looking
        if self.falling_min is None or self.falling_max is None:
            raise ThresholdFinderError(
                'Hybrid threshold finder failed to reset hysteresis before falling threshold linear sweep. Try increasing linear_backtrack.')

        # Lastly, compute outputs
        self.search_algorithm = "binary tuned linear search"
        res = self._compute_outputs()
        return res

    def _find_linear_threshold(self, min, max, step):
        """One sided Linear sweep which sweeps up if step is positive or down if step is negative and finds the threshold.

        Pol is the polarity of the comparator output


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, '_find_linear_threshold')
        True

        Args:
            max: Maximum value of the range.
            min: Minimum value of the range.
            step: Step size.

        Raises:
            ThresholdFinderError: If the operation fails.
            ThresholdUndetectableError: If the operation fails.
        """
        if self._forcing_overshoot >= 1:
            # eventually all linear searches use step size abstol, so might as
            # well detect problems here right away.
            raise ThresholdFinderError(
                "Can't make linear steps of magnitude abstol with over 100% peak overshoot,")
        if step > 0:
            try_threshold = min
            test = False
        else:
            try_threshold = max
            test = True
        test_result = {'output_digital': test}
        tries = 0
        while test_result['output_digital'] == test:
            tries += 1
            self.debug_print("-----------------")
            self.debug_print(
                "Try {}: {}".format(
                    self.tries + tries,
                    try_threshold))
            test_result = self._test(
                try_threshold,
                measure_input=True,
                controlled=False)
            self.debug_print(
                "Output Analog: {}".format(
                    test_result['output_analog']))
            self.debug_print(
                "Output Digital: {}".format(
                    test_result['output_digital']))
            if step > 0:
                if test_result['output_digital']:
                    self.rising_max = try_threshold
                else:
                    self.rising_min = try_threshold
                if try_threshold == max:
                    break
                elif try_threshold + step >= max:
                    try_threshold = max
                else:
                    try_threshold += step
            else:
                if not test_result['output_digital']:
                    self.falling_min = try_threshold
                else:
                    self.falling_max = try_threshold
                if try_threshold == min:
                    break
                elif try_threshold + step <= min:
                    try_threshold = min
                else:
                    try_threshold += step
        if tries < 2:
            raise ThresholdFinderError(
                'Linear sweep too few steps. Step: {} too large for input range: {} or threshold: {} not enclosed by interval {}:{}.'.format(
                    step, max - min, try_threshold, min, max))
        if test_result['output_digital'] == test:
            raise ThresholdUndetectableError(
                'Linear search failed to find transition between: {} and: {}.'.format(
                    min, max))
        self.tries += tries

    def test_repeatability(self, linear_backtrack=None, decades=None):
        """Return test repeatability result.

        Exercises the unit under test and asserts expected behavior.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'test_repeatability')
        True

        Args:
            decades: Decades to use.
            linear_backtrack: Linear backtrack to use.

        Returns:
            The test repeatability result.
        """
        binary_results = self.find(cautious=True)
        hybrid_results = self.find_hybrid(linear_backtrack=linear_backtrack)
        linear_results = self.find_linear()
        geometric_results = self.find_geometric(decades)
        print("\n\n")
        str = ""
        max_key_len = 0
        for key in binary_results:  # same keys in all 3 results
            if key == "search_algorithm":
                continue
            if len(key) > max_key_len:
                max_key_len = len(key)
            str += "{}:\tbinary:{:1.6G}  linear:{:1.6G}  hybrid:{:1.6G}  geometric:{:1.6G}\n".format(key,
                                                                                                     binary_results[key],
                                                                                                     linear_results[key],
                                                                                                     hybrid_results[key],
                                                                                                     geometric_results[key]
                                                                                                     # max(binary_results[key], linear_results[key], hybrid_results[key], geometric_results[key]) - min(binary_results[key], linear_results[key], hybrid_results[key], geometric_results[key])
                                                                                                     )
        print(str.expandtabs(max_key_len + 2))
        return {'binary': binary_results,
                'linear': linear_results,
                'hybrid': hybrid_results
                }

    def read_delegated_channel_list(self, channels):
        """Private.

        Reads data from the underlying source and returns it.


        >>> from PyICe.virtual_instruments import threshold_finder
        >>> hasattr(threshold_finder, 'read_delegated_channel_list')
        True

        Args:
            channels: List of channel objects.

        Returns:
            The value read from the device or channel.
        """
        if self.auto_find:
            if isinstance(self.auto_find,
                          str) and self.auto_find.lower() == 'linear':
                self.find_linear()
            elif isinstance(self.auto_find, str) and self.auto_find.lower() == 'geometric':
                self.find_geometric()
            else:
                self.find()
        results_dict = results_ord_dict()
        for channel in channels:
            results_dict[channel.get_name()] = channel.read_without_delegator()
        return results_dict


class servo_binary_search(instrument):  # todo delegator?!?!?
    """Servo virtual insturment based on thinly wrapped threshold finder.

    Servo forces channel to specified value within abstol/reltol tolerance by manipulating other channel.

    >>> from PyICe.virtual_instruments import servo_binary_search
    >>> servo_binary_search is not None
    True

    """
    def __init__(self, fb_channel, output_channel, minimum_output,
                 maximum_output, abstol, output_readback_channel=None, verbose=False):
        """Initialize servo_binary_search.
        Initializes 12 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 12 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import servo_binary_search
        >>> hasattr(servo_binary_search, '__init__')
        True

        Args:
            abstol: Absolute tolerance.
            fb_channel: Fb channel to use.
            maximum_output: Maximum output to use.
            minimum_output: Minimum output to use.
            output_channel: Channel used for stimulus output.
            output_readback_channel: Output readback channel to use.
            verbose: If True, print debug output.
        """
        # reltol=0.001
        # abort_on_sat=True
        # except_on_fail=True
        self._base_name = 'servo_binary_search'
        instrument.__init__(self, "servo_binary_search virtual instrument")
        self.minimum_output = minimum_output
        self.maximum_output = maximum_output
        self.abstol = abstol
        self.verbose = verbose

        self.fb_channel = fb_channel
        self.output_channel = output_channel
        self.output_readback_channel = output_readback_channel
        self.compare_channel = channel(
            name='servo_comparator',
            read_function=self._compare)

        self.results_dictionary = None
        self._fb_val = None

        self._tf = threshold_finder(comparator_input_force_channel=self.output_channel,
                                    comparator_output_sense_channel=self.compare_channel,
                                    minimum=self.minimum_output,
                                    maximum=self.maximum_output,
                                    abstol=self.abstol,
                                    # no reltol!!!
                                    comparator_input_sense_channel=self.output_readback_channel,
                                    forcing_overshoot=0,
                                    output_threshold=None,  # automatic
                                    verbose=self.verbose,
                                    )

    def add_channel_target(self, channel_name, auto_find=True):  # why not auto find???
        """Servo target value (setpoint).
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import servo_binary_search
        >>> hasattr(servo_binary_search, 'add_channel_target')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=None,
            write_function=lambda val: self._target_write(
                val,
                auto_find))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_target.__doc__)
        # new_channel.set_delegator(self)
        return self._add_channel(new_channel)

    def add_channel_results(self, channel_name):
        """Add result reporting channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import servo_binary_search
        >>> hasattr(servo_binary_search, 'add_channel_results')
        True

        Args:
            channel_name: Name for the new channel.
        """
        abstol_channel = channel(
            f'{channel_name}_abstol',
            read_function=lambda: self.results_dictionary['abstol'])
        forced_channel = channel(
            f'{channel_name}_forced',
            read_function=lambda: self.results_dictionary['forced'])
        output_readback_channel = channel(
            f'{channel_name}_output_readback',
            read_function=lambda: self.results_dictionary['output_readback'])
        feedback_value_channel = channel(
            f'{channel_name}_feedback_value',
            read_function=lambda: self.results_dictionary['feedback_value'])
        target_error_channel = channel(
            f'{channel_name}_target_error',
            read_function=lambda: self.results_dictionary['target_error'])
        # target_channel.set_description(self.get_name() + ': ' + self.add_channel_target.__doc__)
        # Todo
        self._add_channel(abstol_channel)
        self._add_channel(forced_channel)
        self._add_channel(output_readback_channel)
        self._add_channel(feedback_value_channel)
        self._add_channel(target_error_channel)

    def add_channels(self, channel_name, auto_find=True):
        """Add a channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import servo_binary_search
        >>> hasattr(servo_binary_search, 'add_channels')
        True

        Args:
            auto_find: If True, automatically detect the device or setting.
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        self.add_channel_results(channel_name)
        return self.add_channel_target(
            f'{channel_name}_target', auto_find=auto_find)

    def _target_write(self, value, auto_find):
        self._target_value = value
        if auto_find:  # why not????
            return self.find(value)

    def find(self, value):
        """Return the find.

        Searches the collection and returns the matching item or index.


        >>> from PyICe.virtual_instruments import servo_binary_search
        >>> hasattr(servo_binary_search, 'find')
        True

        Args:
            value: Value to set.

        Returns:
            The index of the first match, or -1 if not found.
        """
        self._target_value = value
        tf_results = self._tf.find_no_hysteresis()
        # Some non-specific exceptions leak out of threshold finder. Ex
        # polarity check.

        self.results_dictionary = results_ord_dict((
            ("target", self._target_value),
            ("abstol", self.abstol),
            ("forced", self.output_channel.read()),
            ("output_readback", tf_results['threshold']
             if self.output_readback_channel is not None else None),
            ("feedback_value", self._fb_val),
            ("target_error", self._fb_val - self._target_value),
        ))
        return self.results_dictionary

    def _compare(self):
        try:
            self._fb_val = self.fb_channel.read()
            return self._fb_val > self._target_value
        except TypeError:
            raise  # ServoException from e #todo
        except Exception:
            raise  # ThresholdFinderError?


class leakage_nuller(instrument):
    """TODO: Add docstring.

    >>> from PyICe.virtual_instruments import leakage_nuller
    >>> leakage_nuller is not None
    True

    """

    def __init__(self, leakage_measurement_channel, leakage_forcing_channel, voltage_measurement_channel,
                 minimum_output, maximum_output, voltage_abstol, current_abstol, verbose=False):
        """Initialize leakage_nuller.
        Initializes 10 instance attributes that configure the object's
        behavior.

        Initializes 10 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import leakage_nuller
        >>> hasattr(leakage_nuller, '__init__')
        True

        Args:
            current_abstol: Current abstol to use.
            leakage_forcing_channel: Leakage forcing channel to use.
            leakage_measurement_channel: Leakage measurement channel to use.
            maximum_output: Maximum output to use.
            minimum_output: Minimum output to use.
            verbose: If True, print debug output.
            voltage_abstol: Voltage abstol to use.
            voltage_measurement_channel: Voltage measurement channel to use.
        """
        self.verbose = verbose
        self.voltage_abstol = voltage_abstol
        self.current_abstol = current_abstol
        self.minimum_output = minimum_output
        self.maximum_output = maximum_output
        self.voltage_measurement_channel = voltage_measurement_channel
        self.leakage_forcing_channel = leakage_forcing_channel
        self.leakage_measurement_channel = leakage_measurement_channel
        self._common_mode_servo = servo_binary_search()  # pylint: disable=no-value-for-parameter; known incomplete stub - leakage_nuller class is a TODO prototype awaiting full implementation
        self._leakage_servo = servo_binary_search()  # pylint: disable=no-value-for-parameter; known incomplete stub - leakage_nuller class is a TODO prototype awaiting full implementation

    def measure(self, estimated_voltage):
        """Run the measure step.

        Supports the ``leakage_nuller`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import leakage_nuller
        >>> hasattr(leakage_nuller, 'measure')
        True

        Args:
            estimated_voltage: Estimated voltage to use.
        """
        self._common_mode_servo.find(estimated_voltage)
        self.ileak = self.leakage_measurement_channel.read()
        return  # something

    def null(self):
        """Return the null.

        Supports the ``leakage_nuller`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import leakage_nuller
        >>> hasattr(leakage_nuller, 'null')
        True

        Returns:
            The null result.
        """
        leak_servo_results = self._leakage_servo.find(self.ileak)
        return leak_servo_results

    def add_channel_null(self, channel_name, auto_null=False):
        """Add a channel null.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import leakage_nuller
        >>> hasattr(leakage_nuller, 'add_channel_null')
        True

        Args:
            auto_null: Auto null to use.
            channel_name: Name for the new channel.
        """
        pass


class calibrator(instrument):
    """Calibrator virtual instrument. Corrects channel's read/write values based on.

    either two-point gain/offset correction or full lookup table.

    >>> from PyICe.lab_core import channel
    >>> raw = channel('dac', write_function=lambda v: v)
    >>> cal = calibrator()
    >>> cal_ch = cal.add_channel_calibrated_2point('dac_cal', raw, gain=1.02, offset=0.01)
    >>> _ = cal_ch.write(1.0)
    >>> raw.read()
    1.03
    """
    def __init__(self, verbose=False):
        """Initialize calibrator.
        Stores configuration in ``_base_name``, ``verbose`` for use by other
        methods.

        Calls the parent constructor to inherit base behavior, and initializes 2 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import calibrator
        >>> calibrator is not None
        True

        Args:
            verbose: If True, print debug output.
        """
        self._base_name = 'calibrator'
        instrument.__init__(self, "calibrator virtual instrument")
        self.verbose = verbose

    def calibrate(self, forcing_channel, readback_channel,
                  forcing_values, results_filename=None):
        """Produce calibration table and gain/offset calculation for later use by 2point and spline calibrators.
        Applies correction factors derived from known reference values to
        improve measurement accuracy.

        Adjusts internal parameters to compensate for hardware offsets or gain errors.


        >>> from PyICe.virtual_instruments import calibrator
        >>> hasattr(calibrator, 'calibrate')
        True

        Args:
            forcing_channel: Channel providing the forcing value.
            forcing_values: Forcing values to use.
            readback_channel: Readback channel to use.
            results_filename: Results filename to use.

        Returns:
            The calibrate result.
        """
        import numpy  # pylint: disable=import-error; numpy is an optional dependency imported at point of use
        points = {}
        for force_v in forcing_values:
            forcing_channel.write(force_v)
            points[force_v] = readback_channel.read()
        force_values = [x for x in sorted(points)]
        readback_values = [points[x] for x in force_values]
        x_arr = numpy.vstack(
            [readback_values, numpy.ones(len(force_values))]).T
        results = results_ord_dict()
        results['force_values'] = force_values
        results['readback_values'] = readback_values
        results['gain'], results['offset'] = numpy.linalg.lstsq(x_arr, force_values)[
            0]
        if results_filename is not None:
            import pickle
            with open(results_filename, 'wb') as f:
                pickle.dump(results, f)
        return results

    def add_channel_calibrated_2point(
            self, channel_name, forcing_channel, gain=None, offset=None, calibration_filename=None, **kwargs):
        """Correct channel writes by previously determined 2-point gain/offset trim. Can pass in **calibrate() to get gain/offset measurements.

        offset and gain are specified in the direction of readback channel to forcing channel. ie forcing channel error.


        >>> from PyICe.virtual_instruments import calibrator
        >>> hasattr(calibrator, 'add_channel_calibrated_2point')
        True

        Args:
            **kwargs: Additional keyword arguments.
            calibration_filename: Calibration filename to use.
            channel_name: Name for the new channel.
            forcing_channel: Channel providing the forcing value.
            gain: Gain value.
            offset: Offset value.

        Returns:
            The newly created channel object.

        Raises:
            Exception: If an unexpected error occurs.
        """
        if calibration_filename is None and gain is not None and offset is not None:
            gain = float(gain)
            offset = float(offset)
        elif calibration_filename is not None and gain is None and offset is None:
            import pickle
            with open(calibration_filename, 'rb') as f:
                cal_dict = pickle.load(f)
            gain = cal_dict['gain']
            offset = cal_dict['offset']
        else:
            raise Exception(
                'Specify either calibration_filename or gain and offset arguments, but not both.')
        new_channel = channel(
            channel_name,
            write_function=lambda value: self._correct_2point(
                value,
                forcing_channel,
                gain,
                offset))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_calibrated_2point.__doc__)
        forcing_channel.add_write_callback(
            lambda forcing_channel, raw_value: new_channel._set_value(
                # keep channels sync'd in both directions
                (raw_value - offset) / gain))
        return self._add_channel(new_channel)

    def _correct_2point(self, value, forcing_channel, gain, offset):
        raw_value = value * gain + offset
        if self.verbose:
            print(
                "Correcting {} to {} to get {}".format(
                    forcing_channel.get_name(),
                    raw_value,
                    value))
        forcing_channel.write(raw_value)

    def add_channel_calibrated_spline(
            self, channel_name, forcing_channel, calibration_filename=None, **kwargs):
        """Correct channel writes by previously determined mapping (from calibrate()).

        Can pass in **calibrate() to get cal map, store results dict locally, or use pickle file.
        Requires scipy.interpolate.UnivariateSpline


        >>> from PyICe.virtual_instruments import calibrator
        >>> hasattr(calibrator, 'add_channel_calibrated_spline')
        True

        Args:
            **kwargs: Additional keyword arguments.
            calibration_filename: Calibration filename to use.
            channel_name: Name for the new channel.
            forcing_channel: Channel providing the forcing value.

        Returns:
            The newly created channel object.

        Raises:
            Exception: If an unexpected error occurs.
        """
        from scipy.interpolate import UnivariateSpline  # pylint: disable=import-error; scipy is an optional dependency imported at point of use
        if kwargs.get('force_values', None) is not None and kwargs.get(
                'readback_values', None) is not None and calibration_filename is None:
            force_values = kwargs['force_values']
            readback_values = kwargs['readback_values']
        elif kwargs.get('force_values', None) is None and kwargs.get('readback_values', None) is None and calibration_filename is not None:
            import pickle
            with open(calibration_filename, 'rb') as f:
                cal_dict = pickle.load(f)
            force_values = cal_dict['force_values']
            readback_values = cal_dict['readback_values']
        else:
            raise Exception(
                'Specify either calibration_filename or **dictionary from calibrate(), but not both.')
        # change raw output to desired output for callback
        spl_rev = UnivariateSpline(force_values, readback_values, s=0)
        readback_values_sort, force_values_sort = list(zip(
            # SORT by readback
            *sorted(zip(readback_values, force_values), key=lambda tup: tup[0])))
        spl = UnivariateSpline(
            readback_values_sort,
            force_values_sort,
            s=0)  # change desired output to raw output
        new_channel = channel(
            channel_name,
            write_function=lambda value: self._correct_spline(
                value,
                forcing_channel,
                spl))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_calibrated_spline.__doc__)
        forcing_channel.add_write_callback(
            lambda forcing_channel, raw_value: new_channel._set_value(
                spl_rev(raw_value)))  # keep channels sync'd in both directions
        return self._add_channel(new_channel)

    def _correct_spline(self, value, forcing_channel, spl):
        corrected_value = spl(value)
        if self.verbose:
            print(
                "Correcting {} to {} to get {}".format(
                    forcing_channel.get_name(),
                    corrected_value,
                    value))
        forcing_channel.write(corrected_value)


class digital_analog_io(instrument):
    """Wraps an analog output PyICe channel with a digital interface.

    domain_channel is the PyICe channel for the logic supply of the digital input
    we're talking to, e.g. master['vin_supply'] or master['dvcc_supply'].

    >>> from PyICe.lab_core import channel
    >>> from PyICe.virtual_instruments import digital_analog_io, dummy
    >>> d = dummy()
    >>> analog_out = d.add_channel_write("vpin")
    >>> _ = analog_out.set_min_write_limit(0)
    >>> _ = analog_out.set_max_write_limit(5)
    >>> dio = digital_analog_io()
    >>> dig_ch = dio.add_channel_digital_output("gpio0", analog_out)
    >>> dig_ch.get_name()
    'gpio0'

    """
    def __init__(self, domain_channel=None, verbose=False):
        """Initialize digital_analog_io.
        Initializes 5 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 5 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> obj = digital_analog_io()
        >>> isinstance(obj, digital_analog_io)
        True

        Args:
            domain_channel: Domain channel to use.
            verbose: If True, print debug output.
        """
        self._base_name = 'digital_analog_io'
        instrument.__init__(self, "digital_analog_io virtual instrument")
        if domain_channel is None:
            domain_channel = channel('dummy_domain')
            domain_channel.write(0)
        else:
            assert isinstance(domain_channel, channel)
        self._domain_channel = domain_channel
        # domain supply voltage doesn't need to be cached for output type
        # channels, but is necessary for input type domain channels (DMM, etc)
        self._domain_supply = None
        self._verbose = verbose
        self.mapping_data_t = collections.namedtuple(
            'state_map', ['scale', 'offset'])

    def _dummy_write(self, dummy_value):
        raise Exception('Not supposed to get this far...')

    def _dummy_read(self):
        raise Exception('Not supposed to get this far...')

    def _compute_outputs(self, digital_value, digital_channel):
        if digital_value is None:
            return digital_value
        try:
            output_v = self._domain_supply * digital_channel.get_attribute('logic_map')[
                digital_value].scale + digital_channel.get_attribute('logic_map')[digital_value].offset
        except KeyError:
            raise NotImplementedError(
                "Don't know how to digital_write{} to {} !".format(
                    digital_channel.get_name(), digital_value))
        return output_v

    def _digital_write(self, digital_value, digital_channel):
        self._domain_supply = self._domain_channel.read()
        # short-circuit callback path for the originating channel. otherwise,
        # output callback will be run before digital_channel value gets stored
        digital_channel._set_value(digital_value)
        output_v = self._compute_outputs(digital_value, digital_channel)
        digital_channel.get_attribute('output_channel').write(output_v)
        return output_v

    def _output_channel_callback(self, digital_channel, output_channel, value):
        """Change digital channels back to None if overwritten by another digital channel or output channel.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, '_output_channel_callback')
        True

        Args:
            digital_channel: Digital channel to use.
            output_channel: Channel used for stimulus output.
            value: Value to set.
        """
        expected_output = self._compute_outputs(
            digital_channel.read(),
            # use cached domain supply to avoid domain supply noise corrupting
            # comparison below
            digital_channel)
        if expected_output is None:
            return
        if value != expected_output:
            if self._verbose:
                print("Digital channel: {} relinquishing control of output channel: {}".format(
                    digital_channel.get_name(), output_channel.get_name()))
            digital_channel._set_value(None)  # avoid recursive callbacks

    def _domain_channel_callback(self, digital_channel):
        """Update outputs when reference level changes.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, '_domain_channel_callback')
        True

        Args:
            digital_channel: Digital channel to use.
        """
        if digital_channel.read() is not None:
            output_v = self._digital_write(
                digital_channel.read(), digital_channel)
            if self._verbose:
                print(
                    "Domain change: {}:{}:{}".format(
                        digital_channel.get_name(),
                        digital_channel.get_attribute(
                            'output_channel').get_name(),
                        output_v))

    def _domain_read_callback(
            self, digital_output_channel, domain_channel_value):
        raise NotImplementedError(
            "Read callbacks are hard to avoid recursion and maybe not necessary?")

    def _digital_read(self, digital_channel):
        vin = digital_channel.get_attribute('input_channel').read()
        if vin is None:
            return None
        _vdomain = self._domain_channel.read()  # noqa: F841 - side-effect read
        vin_ratio_rising = 1.0 * \
            (vin - digital_channel.get_attribute('hys_absolute')) / \
            self._domain_channel.read()
        if vin_ratio_rising > digital_channel.get_attribute('vih'):
            return True
        vin_ratio_falling = 1.0 * \
            (vin + digital_channel.get_attribute('hys_absolute')) / \
            self._domain_channel.read()
        if vin_ratio_falling < digital_channel.get_attribute('vil'):
            return False
        if digital_channel.get_attribute('hys_enable'):
            return digital_channel._value  # undefined = old state
        return None  # undefined = 'X' state

    def add_channel_digital_output(
            self, channel_name, output_channel, voh_scale=1, voh_offset=0, vol_scale=0, vol_offset=0):
        """Add a mapping from logic states to analog supply.

        optionally track instrument's domain supply (through callbacks) with non-zero _scale arguments
        optionally offset from domain supply by absolute amount with _offset arguments
        absolute min and max write limits can be achieved using output_channel.set_min_write_limit() and output_channel.set_max_write_limit()
        after channel creation, additional logic states can be accommodated either by add_logic_state() to this channel, or create another digital channel mapping through the same output_channel
        use a ramp_to domain channel to interleave output channel writes with each step and prevent logic state changes when domain supply changes


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, 'add_channel_digital_output')
        True

        Args:
            channel_name: Name for the new channel.
            output_channel: Channel used for stimulus output.
            voh_offset: Voh offset to use.
            voh_scale: Voh scale to use.
            vol_offset: Vol offset to use.
            vol_scale: Vol scale to use.

        Returns:
            The newly created channel object.
        """
        digital_channel = integer_channel(
            channel_name,
            size=16,
            write_function=self._dummy_write)  # negative values permissible???
        digital_channel._write = lambda digital_value: self._digital_write(
            digital_value,
            digital_channel)  # need to wait for assignment to get reference back to new channel
        digital_channel.set_description(
            '{}: digital control of slave channel: {}. {}'.format(
                self.get_name(),
                output_channel.get_name(),
                self.add_channel_digital_output.__doc__))
        assert isinstance(vol_scale, numbers.Real)
        assert isinstance(vol_offset, numbers.Real)
        assert isinstance(voh_scale, numbers.Real)
        assert isinstance(voh_offset, numbers.Real)
        digital_channel.set_attribute('logic_map', {0: self.mapping_data_t(vol_scale, vol_offset),
                                                    1: self.mapping_data_t(voh_scale, voh_offset)})
        digital_channel.set_attribute('output_channel', output_channel)
        digital_channel.add_preset("0", 0)
        digital_channel.add_preset("1", 1)
        output_channel.add_write_callback(
            lambda output_channel, value: self._output_channel_callback(
                digital_channel, output_channel, value))
        self._domain_channel.add_write_callback(
            lambda domain_channel,
            value: self._domain_channel_callback(digital_channel))
        return self._add_channel(digital_channel)

    def add_digital_output_logic_state(
            self, digital_output_channel, digital_state, vo_scale, vo_offset):
        """Add an additional logic state to an existing digital output channel, eg 2 for testhook overdrive.

        vo_scale is a percentage of the domain channel
        vo_offset is absolute


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, 'add_digital_output_logic_state')
        True

        Args:
            digital_output_channel: Digital output channel to use.
            digital_state: Digital state to use.
            vo_offset: Vo offset to use.
            vo_scale: Vo scale to use.
        """
        assert isinstance(digital_output_channel, channel)
        assert isinstance(digital_state, int)
        assert isinstance(vo_scale, numbers.Real)
        assert isinstance(vo_offset, numbers.Real)
        digital_output_channel.get_attribute('logic_map').update(
            [(digital_state, self.mapping_data_t(vo_scale, vo_offset))])
        digital_output_channel.add_preset(str(digital_state), digital_state)

    def enable_digital_output_domain_read_callback(
            self, digital_output_channel):
        """This doesn't work yet. Is it worth implementing?

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, 'enable_digital_output_domain_read_callback')
        True

        Args:
            digital_output_channel: Digital output channel to use.
        """
        self._domain_channel.add_read_callback(
            lambda domain_channel,
            domain_channel_value: self._domain_read_callback(
                digital_output_channel,
                domain_channel_value))

    def add_channel_digital_input(self, channel_name, analog_input_channel,
                                  vil_ratio=0.3, vih_ratio=0.7, hys_enable=0, hys_absolute=0):
        """Add a mapping from analog channel to boolean, scaled to variable domain supply.

        absolute voltage thresholds are achievable by using a dummy domain supply channel


        >>> from PyICe.virtual_instruments import digital_analog_io
        >>> hasattr(digital_analog_io, 'add_channel_digital_input')
        True

        Args:
            analog_input_channel: Analog input channel to use.
            channel_name: Name for the new channel.
            hys_absolute: Hys absolute to use.
            hys_enable: Hys enable to use.
            vih_ratio: Vih ratio to use.
            vil_ratio: Vil ratio to use.

        Returns:
            The newly created channel object.
        """
        digital_channel = integer_channel(
            channel_name, size=1, read_function=self._dummy_read)
        # need to wait for assignment to get reference back to new channel
        digital_channel._read = lambda: self._digital_read(digital_channel)
        digital_channel.set_description(
            '{}: digital read of analog channel: {}. {}'.format(
                self.get_name(),
                analog_input_channel.get_name(),
                self.add_channel_digital_input.__doc__))
        assert isinstance(analog_input_channel, channel)
        assert isinstance(vil_ratio, numbers.Real)
        assert isinstance(vih_ratio, numbers.Real)
        assert isinstance(hys_absolute, numbers.Real)
        assert vih_ratio >= vil_ratio
        assert hys_absolute >= 0
        digital_channel.set_attribute('input_channel', analog_input_channel)
        digital_channel.set_attribute('vil', vil_ratio)
        digital_channel.set_attribute('vih', vih_ratio)
        digital_channel.set_attribute('hys_enable', hys_enable)
        digital_channel.set_attribute('hys_absolute', hys_absolute)
        # domain channel callback useful?
        return self._add_channel(digital_channel)


class vector_to_scalar_converter(instrument):
    """Reduce rank of channel data from iterable vector data to scalar data using arbitrary reduction function (average, sum, std. dev, etc).

    >>> vector_to_scalar_converter.sum([1, 2, 3, 4])
    10.0
    >>> vector_to_scalar_converter.mean([2, 4, 6, 8])
    5.0
    >>> vector_to_scalar_converter.stdev([2, 4, 4, 4, 5, 5, 7, 9])  # doctest: +ELLIPSIS
    2.138...
    >>> vector_to_scalar_converter.sum(None) is None
    True
    """
    def __init__(self):
        """Initialize vector_to_scalar_converter.

        Stores configuration in ``_base_name`` for use by other methods.

        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> vector_to_scalar_converter is not None
        True

        """
        self._base_name = 'vector_scalar_converter'
        instrument.__init__(self, self._base_name)
        # NB Python 3.4 adds useful statistics module:
        # https://docs.python.org/3/library/statistics.html

    @staticmethod
    def sum(sequence):
        """Arithmetic sum.

        Supports the ``vector_to_scalar_converter`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> callable(getattr(vector_to_scalar_converter, 'sum', None))
        True

        Args:
            sequence: Ordered sequence of values or steps.

        Returns:
            The sum result.
        """
        return math.fsum(sequence) if sequence is not None else None

    @classmethod
    def mean(cls, sequence):
        """Arithmetic mean of sequence.

        Supports the ``vector_to_scalar_converter`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> callable(getattr(vector_to_scalar_converter, 'mean', None))
        True

        Args:
            sequence: Ordered sequence of values or steps.

        Returns:
            The mean result.
        """
        return cls.sum(sequence) / \
            len(sequence) if sequence is not None else None

    @classmethod
    def stdev(cls, sequence):
        """Sample std deviation.

        Supports the ``vector_to_scalar_converter`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> callable(getattr(vector_to_scalar_converter, 'stdev', None))
        True

        Args:
            sequence: Ordered sequence of values or steps.

        Returns:
            The stdev result.
        """
        if sequence is None:
            return None
        mean = cls.mean(sequence)
        return (
            cls.sum([(sample - mean)**2 for sample in sequence]) / (len(sequence) - 1))**0.5

    @classmethod
    def pstdev(cls, sequence):
        """Population std deviation.

        Supports the ``vector_to_scalar_converter`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> callable(getattr(vector_to_scalar_converter, 'pstdev', None))
        True

        Args:
            sequence: Ordered sequence of values or steps.

        Returns:
            The pstdev result.
        """
        if sequence is None:
            return None
        return cls.stdev(sequence) * ((len(sequence) - 1) / len(sequence))**0.5

    @classmethod
    def rms(cls, sequence):
        """RMS (root mean square). To instead subtract sample mean, use pstdev.

        Supports the ``vector_to_scalar_converter`` workflow by performing the described operation.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> callable(getattr(vector_to_scalar_converter, 'rms', None))
        True

        Args:
            sequence: Ordered sequence of values or steps.

        Returns:
            The rms result.
        """
        if sequence is None:
            return None
        mean = cls.mean([x**2 for x in sequence])**0.5
        return (
            cls.sum([(sample - mean)**2 for sample in sequence]) / (len(sequence) - 1))**0.5

    def add_channel_callback(
            self, channel_name, vector_data_channel, reduction_function):
        """Vector reduction channel that operates by a callback whenever vector_data_channel is read. Reading this channel won't cause vector_data_channel.

        to be read, nor will this channel's value be updated.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> hasattr(vector_to_scalar_converter, 'add_channel_callback')
        True

        Args:
            channel_name: Name for the new channel.
            reduction_function: Reduction function to use.
            vector_data_channel: Vector data channel to use.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name)  # dummy channel
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel_callback.__doc__)
        vector_data_channel.add_change_callback(
            lambda vector_data_channel,
            vector_data: new_channel.write(
                reduction_function(vector_data)))
        return self._add_channel(new_channel)

    def add_channel(self, channel_name, vector_data_channel,
                    reduction_function):
        """Vector reduction channel that operates by directly reading vector_data_channel. Reading this channel will cause vector_data_channel.

        to be read, and will cause vector_data_channel to be read twice if both vector_data_channel and this virtual channel are in the read list.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> hasattr(vector_to_scalar_converter, 'add_channel')
        True

        Args:
            channel_name: Name for the new channel.
            reduction_function: Reduction function to use.
            vector_data_channel: Vector data channel to use.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            read_function=lambda: reduction_function(
                vector_data_channel.read()))
        new_channel.set_description(
            self.get_name() + ': ' + self.add_channel.__doc__)
        return self._add_channel(new_channel)

    def _add_channel_dummy_random(
            self, channel_name, vector_length, max=1, min=0):
        """Return random vector channel data to test virtual instrument.

        Internal implementation detail; see the public API for usage.


        >>> from PyICe.virtual_instruments import vector_to_scalar_converter
        >>> hasattr(vector_to_scalar_converter, '_add_channel_dummy_random')
        True

        Args:
            channel_name: Name for the new channel.
            max: Maximum value of the range.
            min: Minimum value of the range.
            vector_length: Vector length to use.

        Returns:
            The add channel dummy random result.
        """
        new_channel = channel(
            channel_name, read_function=lambda: [
                random.uniform(
                    min, max) for x in range(vector_length)])
        new_channel.set_description(
            self.get_name() + ': ' + self._add_channel_dummy_random.__doc__)
        return self._add_channel(new_channel)


class smart_battery_emulator(instrument):
    """Smart_battery_emulator (instrument subclass).

    >>> from PyICe.virtual_instruments import smart_battery_emulator
    >>> smart_battery_emulator is not None
    True

    """
    def __init__(self, voltage_channel_name, current_channel_name,
                 voltage_interval, current_interval, verbose=False):
        """Smart Battery emulator to kick out voltage and current requests to keep a smart-battery charger alive.
        Initializes 7 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 7 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import smart_battery_emulator
        >>> hasattr(smart_battery_emulator, '__init__')
        True

        Args:
            current_channel_name: Current channel name to use.
            current_interval: Current interval to use.
            verbose: If True, print debug output.
            voltage_channel_name: Voltage channel name to use.
            voltage_interval: Voltage interval to use.
        """
        self._base_name = 'SB_emulator'
        instrument.__init__(self, "Smart Battery Emulator")
        self.verbose = verbose
        self.writer = threaded_writer(verbose=self.verbose)
        self.voltage_thread = self.writer.connect_channel(
            channel_name=voltage_channel_name, time_interval=voltage_interval)
        self.current_thread = self.writer.connect_channel(
            channel_name=current_channel_name, time_interval=current_interval)
        self.initial_voltage_interval = voltage_interval
        self.initial_current_interval = current_interval

    def stop_all(self):
        """Kills all threaded channels, can't be restarted.

        Supports the ``smart_battery_emulator`` workflow by performing the described operation.

        >>> from PyICe.virtual_instruments import smart_battery_emulator
        >>> hasattr(smart_battery_emulator, 'stop_all')
        True

        """
        self.writer.stop_all()

    def add_channel_voltage_interval(self, channel_name):
        """Adds a channel that can change the update interval of the smart battery voltage.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import smart_battery_emulator
        >>> hasattr(smart_battery_emulator, 'add_channel_voltage_interval')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            write_function=self.voltage_thread.set_time_interval)
        new_channel.set_description(self.add_channel_voltage_interval.__doc__)
        new_channel.write(self.initial_voltage_interval)
        return self._add_channel(new_channel)

    def add_channel_current_interval(self, channel_name):
        """Adds a channel that can change the update interval of the smart battery current.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import smart_battery_emulator
        >>> hasattr(smart_battery_emulator, 'add_channel_current_interval')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(
            channel_name,
            write_function=self.current_thread.set_time_interval)
        new_channel.set_description(self.add_channel_current_interval.__doc__)
        new_channel.write(self.initial_current_interval)
        return self._add_channel(new_channel)


class aggregator(instrument):
    """Combines multiple, less capable channels into a single channel of great renown.

    >>> from PyICe.virtual_instruments import aggregator, dummy
    >>> d = dummy()
    >>> ch_a = d.add_channel_write("rail_a")
    >>> _ = ch_a.set_min_write_limit(0)
    >>> _ = ch_a.set_max_write_limit(3.3)
    >>> ch_b = d.add_channel_write("rail_b")
    >>> _ = ch_b.set_min_write_limit(0)
    >>> _ = ch_b.set_max_write_limit(3.3)
    >>> agg = aggregator()
    >>> agg_ch = agg.add_channel_sequential("combined", [ch_a, ch_b])
    >>> agg_ch.get_name()
    'combined'
    """

    def __init__(self):
        """TODO: Add docstring.

        Stores configuration in ``_base_name`` for use by other methods.

        >>> from PyICe.virtual_instruments import aggregator
        >>> obj = aggregator()
        >>> isinstance(obj, aggregator)
        True

        """
        self._base_name = 'aggreg'
        instrument.__init__(self, 'AGGREGATOR')

    def add_channel_sequential(self, channel_name, slave_channels):
        """Add a channel sequential.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import aggregator
        >>> hasattr(aggregator, 'add_channel_sequential')
        True

        Args:
            channel_name: Name for the new channel.
            slave_channels: Slave channels to use.

        Returns:
            The newly created channel object.
        """
        return self.add_channel(channel_name=channel_name,
                                slave_channels=slave_channels, sequential=True)

    def add_channel_parallel(self, channel_name, slave_channels):
        """Add a channel parallel.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import aggregator
        >>> hasattr(aggregator, 'add_channel_parallel')
        True

        Args:
            channel_name: Name for the new channel.
            slave_channels: Slave channels to use.

        Returns:
            The newly created channel object.
        """
        return self.add_channel(channel_name=channel_name,
                                slave_channels=slave_channels, sequential=False)

    def add_channel(self, channel_name, slave_channels, sequential=True):
        """Adds the main channels that will make use of the lesser channels.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import aggregator
        >>> hasattr(aggregator, 'add_channel')
        True

        Args:
            channel_name: Name for the new channel.
            sequential: Sequential to use.
            slave_channels: Slave channels to use.

        Returns:
            The newly created channel object.
        """
        new_channel = channel(channel_name, write_function=None)
        new_channel._write = lambda value, channel = new_channel: self._write_channel(
            value, channel)
        new_channel.set_write_access(True)
        new_channel.set_attribute("slave_channels", slave_channels)
        new_channel.set_attribute("sequential_mode", sequential)
        new_channel.set_description(self.add_channel.__doc__)
        for ch in slave_channels:
            for iface in ch.resolve_delegator().get_interfaces():
                new_channel.add_interface(iface)
        self._check_limits(channel_name, slave_channels)
        return self._add_channel(new_channel)

    def _check_limits(self, channel_name, slave_channels):
        # Not sure why this wasn't done originally. Might be too draconian, but also don't see why the missing limits can't just be fixed within the individual instrument drivers.
        # TODO remove all the print warnings below in _write_sequential after
        # these limit checks are fully enforced.
        for ch in slave_channels:
            assert ch.get_max_write_limit() is not None, f"ERROR: Aggregator channel {ch.get_name()} from {channel_name} aggregated by {self.get_name()} has no max write limit."
            assert ch.get_min_write_limit() is not None, f"ERROR: Aggregator channel {ch.get_name()} from {channel_name} aggregated by {self.get_name()} has no min write limit."

    def _write_channel(self, value, channel):
        if channel.get_attribute("sequential_mode"):
            self._write_sequential(
                value, channel.get_attribute("slave_channels"))
        else:
            self._write_parallel(
                value, channel.get_attribute("slave_channels"))

    def _write_sequential(self, value, servant_channels):
        """Distributes value through the lesser channels.
        Internal helper that sends the ``WARNING:`` SCPI command.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.virtual_instruments import aggregator
        >>> hasattr(aggregator, '_write_sequential')
        True

        Args:
            servant_channels: Servant channels to use.
            value: Value to set.

        Raises:
            ChannelValueException: If the value is outside the channel\'s valid range.
        """
        if len(servant_channels) == 1:
            if value != 0:
                if servant_channels[0].get_max_write_limit() is None:
                    print(
                        f"WARNING: Aggregator channel {servant_channels[0].get_name()} has no max write limit.")
                if servant_channels[0].get_min_write_limit() is None:
                    print(
                        f"WARNING: Aggregator channel {servant_channels[0].get_name()} has no min write limit.")
            try:
                servant_channels[0].write(value)
            except ChannelValueException as e:
                print("Aggregator failed to reach the target value.")
                raise e
        elif servant_channels[0].get_max_write_limit() is not None and value > servant_channels[0].get_max_write_limit():
            servant_channels[0].write(
                servant_channels[0].get_max_write_limit())
            self._write_sequential(
                value - servant_channels[0].get_max_write_limit(), servant_channels[1:])
        elif servant_channels[0].get_min_write_limit() is not None and value < servant_channels[0].get_min_write_limit():
            servant_channels[0].write(
                servant_channels[0].get_min_write_limit())
            self._write_sequential(
                value - servant_channels[0].get_min_write_limit(), servant_channels[1:])
        else:
            if value != 0:
                if servant_channels[0].get_max_write_limit() is None:
                    print(
                        f"WARNING: Aggregator channel {servant_channels[0].get_name()} has no max write limit.")
                if servant_channels[0].get_min_write_limit() is None:
                    print(
                        f"WARNING: Aggregator channel {servant_channels[0].get_name()} has no min write limit.")
            servant_channels[0].write(value)
            self._write_sequential(0, servant_channels[1:])

    def _write_parallel(self, value, servant_channels):
        contrib_val = value / float(len(servant_channels))
        for ch in servant_channels:
            ch.write(contrib_val)
        # Todo: check quantization error?


class simple_servo(instrument):
    """Alternae servo instrument, which makes no assumptions about gain or linearity.

    Binary and geometric have monotonicity constraints. Linear searches should fine an answer eventually, without a monotonicity constraint

    >>> from PyICe.virtual_instruments import simple_servo
    >>> simple_servo is not None
    True

    """
    def __init__(self, fb_channel, output_channel, minimum, maximum, reltol=0.001,
                 abstol=None, verbose=False, max_tries=10, step_method="BINARY"):
        """Initialize simple_servo.
        Initializes 11 instance attributes that configure the object's
        behavior.

        Calls the parent constructor to inherit base behavior, and initializes 11 instance attributes that configure the object's behavior.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, '__init__')
        True

        Args:
            abstol: Absolute tolerance.
            fb_channel: Fb channel to use.
            max_tries: Max tries to use.
            maximum: Maximum value.
            minimum: Minimum value.
            output_channel: Channel used for stimulus output.
            reltol: Relative tolerance.
            step_method: Step method to use.
            verbose: If True, print debug output.
        """
        self._base_name = 'servo'
        self.fb_channel = fb_channel
        self.output_channel = output_channel
        self.max_tries = max_tries
        self.minimum = minimum
        self.maximum = maximum
        self.step_method = step_method
        self.reltol = reltol
        self.abstol = abstol
        self._history = []
        assert self.abstol is None or self.abstol > 0
        assert self.reltol is None or self.reltol > 0
        assert reltol is not None or abstol is not None
        self.verbose = verbose
        instrument.__init__(
            self, "Servo Instrument forcing {} via {}".format(
                fb_channel.get_name(), output_channel.get_name()))
        assert self.maximum > self.minimum
        if step_method == "BINARY":
            if abstol is not None:
                bin_steps = math.log((maximum - minimum) / abstol, 2)
                assert max_tries >= bin_steps, "Servo max tries tighter than search window / abstol ratio."
        self.set_search_direction_override_fn(self.search_direction_override)
        # if self.step_method == "BINARY":
        # starting_range = self.maximum - self.minimum
        # range_attenuation = 0.5 ** self.max_tries
        # final_range = starting_range * range_attenuation

    def set_search_direction_override_fn(self, fn):
        """Set the search direction override fn.
        Updates the search direction override fn in the object's internal
        state.

        Updates the search direction override fn in the object's internal state.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'set_search_direction_override_fn')
        True

        Args:
            fn: Callable function.
        """
        self._search_direction_override_fn = fn

    def search_direction_override(self, **kwargs):
        """Use extra (multivariate or more complex) logic to control servo direction in the face of non-monotonic behavior.

        For example, current measurement too low because too much current caused compliance/dropout problem with servo'd load, measurable though compliance voltage waveform, current limit status bit, etc.
        return None to allow loop decision to stand
        return True to force an upward search
        return False to foece a downward search

        This dummy method doesn't alter behavior, but can be replaced with inheritance or the set_search_direction_override_fn method to point to something with more smarts.
        Should accept **kwargs dict argument containing servo state information


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'search_direction_override')
        True

        Args:
            **kwargs: Additional keyword arguments.

        Returns:
            The search direction override result.
        """
        return None

    def set_minimum(self, value):
        """Set the minimum.
        Updates the minimum in the object's internal state.

        Updates the minimum in the object's internal state.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'set_minimum')
        True

        Args:
            value: Value to set.
        """
        self.minimum = value

    def set_maximum(self, value):
        """Set the maximum.
        Updates the maximum in the object's internal state.

        Updates the maximum in the object's internal state.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'set_maximum')
        True

        Args:
            value: Value to set.
        """
        self.maximum = value

    def add_channel_target(self, channel_name):
        """Channel write causes output_channel to servo to new target value.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.
        Registers the channel with the parent instrument so that it appears in
        read-all sweeps and logger output.

        Registers the channel with the parent instrument so that it appears in read-all sweeps and logger output.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'add_channel_target')
        True

        Args:
            channel_name: Name for the new channel.

        Returns:
            The newly created channel object.
        """
        servo_channel = channel(channel_name, write_function=self.servo)
        servo_channel.set_description(
            self.get_name() + ': ' + self.add_channel_target.__doc__)
        return self._add_channel(servo_channel)

    def servo(self, target):
        """Return the servo.
        Sends the ``Max`` SCPI command to the instrument.
        Sends the ``Incorrect`` SCPI command to the instrument.

        Transmits data to the remote endpoint.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'servo')
        True

        Args:
            target: Target value.

        Returns:
            The final servo result after convergence.

        Raises:
            ServoException: If the servo fails to converge.
        """
        assert target != 0 or self.reltol is not None
        self.lower_bound = self.minimum
        self.upper_bound = self.maximum
        self.previous_error = None
        self.error = None
        self._history = []
        count = 0
        while (self.max_tries is None or count < self.max_tries + 1):
            count += 1
            if self.step_method == "BINARY":
                setting = (self.lower_bound + self.upper_bound) / 2.
            elif self.step_method == "GEOMETRIC":
                # only works for positive settings
                setting = (self.lower_bound * self.upper_bound) ** 0.5
            # The logic is not correct. If it steps over the desired point, it
            # may not stop.
            elif self.step_method == "LINEAR INCREASING" or self.step_method == "LINEAR":
                setting = ((count - 1) / self.max_tries) * \
                    (self.maximum - self.minimum) + self.minimum
            elif self.step_method == "LINEAR DECREASING":
                setting = self.maximum - \
                    ((count - 1) / self.max_tries) * \
                    (self.maximum - self.minimum)
            else:
                raise ServoException(
                    f"Don't know the step method: {self.step_method}")
            self.output_channel.write(setting)
            if self.is_in_spec(target, setting):
                print("\n".join([f"{pt[0]}\t{pt[1]}" for pt in self._history]))
                return count
            else:
                forced_direction = self._search_direction_override_fn(count=count,
                                                                      step_method=self.step_method,
                                                                      setting=setting,
                                                                      max_tries=self.max_tries,
                                                                      lower_bound=self.lower_bound,
                                                                      upper_bound=self.upper_bound,
                                                                      target=target,
                                                                      error=self.error,
                                                                      previous_error=self.previous_error,
                                                                      fb_read_val=self.fb_read_val
                                                                      )
                if forced_direction is None:
                    if self.previous_error is not None \
                        and self.error is not None \
                        and math.copysign(1, self.error) == math.copysign(1, self.previous_error) \
                            and math.fabs(self.error) >= math.fabs(self.previous_error) + (self.abstol if self.abstol is not None else 0):
                        if self.verbose:
                            print(
                                "\n".join([f"{pt[0]}\t{pt[1]}" for pt in self._history]))
                        raise ServoException(
                            "Error is growing. Gain sign error or broken feedback loop?")
                    elif self.error > 0:
                        self.upper_bound = setting
                    else:
                        self.lower_bound = setting
                elif forced_direction is True:
                    self.lower_bound = setting
                    if self.verbose:
                        print('Search Direction Forced Upward by Override.')
                elif forced_direction is False:
                    self.upper_bound = setting
                    if self.verbose:
                        print('Search Direction Forced Downward by Override.')
                else:
                    raise ServoException(
                        f"Incorrect value: {forced_direction} returned from search direction override function.  Expected None, True, or False")
        if self.verbose:
            print("\n".join([f"{pt[0]}\t{pt[1]}" for pt in self._history]))
        raise ServoException(f"Max servo tries exceeded: {self.max_tries}")

    def is_in_spec(self, target, setting):
        """Return whether the channel is in spec.
        Returns a boolean reflecting the object's current state.

        Issues a SCPI query to the instrument and parses the response.


        >>> from PyICe.virtual_instruments import simple_servo
        >>> hasattr(simple_servo, 'is_in_spec')
        True

        Args:
            setting: Setting to use.
            target: Target value.

        Returns:
            True if the in spec condition is met, False otherwise.
        """
        self.previous_error = self.error
        self.fb_read_val = float(self.fb_channel.read())
        self.error = self.fb_read_val - target
        if self.verbose:
            try:
                spe = f'{self.previous_error: 0.4e}'
            except TypeError:
                spe = ' None' + ' ' * (10 - 4)
            print(
                f'Target:{target:.4e}, Readback:{self.fb_read_val:.4e}, set:{setting:.4e}, prev err:{spe}, err:{self.error: 0.4e}, up_bound:{self.upper_bound:.4e}, lo_bound:{self.lower_bound:.4e}')
        self._history.append((setting, self.fb_read_val))
        if self.abstol is not None and abs(self.error) < self.abstol:
            return True
        elif self.reltol is not None and abs(self.error / target) < self.reltol:
            return True
        else:
            return False


class dummy_quantum_twin(instrument):
    """Dummy_quantum_twin (instrument subclass).

    >>> from PyICe.virtual_instruments import dummy_quantum_twin
    >>> dummy_quantum_twin is not None
    True

    """
    def __init__(self, name=None):
        """Creates dummy channels that opportunistically mirror the state of the live originals.

        Can be used to replace channels in a logger than might not always still be readable at time of logging.
        Can speed up multiple logging iterations if resisters are known to be static.
        Etc...


        >>> from PyICe.virtual_instruments import dummy_quantum_twin
        >>> dummy_quantum_twin is not None
        True

        Args:
            name: Name identifier.
        """
        self._base_name = 'Dummy Quantum Twin Instrument' if name is None else f'{name}'
        instrument.__init__(self, self._base_name)
    # TODO - prests, formats, int channel size???
    # TODO - Allow writeback through dummy to orignal channel??? Too
    # confusing???

    def add_channel(self, live_channel, skip_read=False, cached_value=None):
        """Make a new dummy chanel, entangle it with the live one, and add it to this instrument.

        Original live channel unchanged except for added callbacks.


        >>> from PyICe.virtual_instruments import dummy_quantum_twin
        >>> hasattr(dummy_quantum_twin, 'add_channel')
        True

        Args:
            cached_value: Cached value to use.
            live_channel: Live channel to use.
            skip_read: Skip read to use.

        Returns:
            The newly created channel object.
        """
        dummy_channel = channel(
            name=live_channel.get_name(),
            read_function=None,
            write_function=None)
        if skip_read:
            dummy_channel.write(cached_value)
        else:
            assert cached_value is None, f'dummy_quantum_twin {live_channel.get_name()}: Do not specify cached_value if not skip_read.'
            dummy_channel.write(live_channel.read())
        dummy_channel.set_write_access(False)
        dummy_channel.set_description(
            f'Quantum twin of: {live_channel.get_description()}')
        dummy_channel.set_attribute('live_channel', live_channel)
        live_channel.set_attribute('dummy_twin', dummy_channel)
        live_channel.add_read_callback(
            lambda live_ch,
            value,
            dummy_ch=dummy_channel: self._callback_update(
                live_ch,
                value,
                dummy_ch))
        live_channel.add_write_callback(
            lambda live_ch,
            value,
            dummy_ch=dummy_channel: self._callback_update(
                live_ch,
                value,
                dummy_ch))
        return self._add_channel(dummy_channel)

    def _callback_update(self, live_channel, value, dummy_channel):
        dummy_channel.set_write_access(True)
        dummy_channel.write(value)
        dummy_channel.set_write_access(False)


class Virtual_Oven(temperature_chamber):
    """Virtual_ oven (temperature_chamber subclass).

    >>> from PyICe.virtual_instruments import Virtual_Oven
    >>> Virtual_Oven is not None
    True

    """
    def __init__(self):
        """Initialize virtual_ oven.

        Stores configuration in ``_base_name`` for use by other methods.

        >>> from PyICe.virtual_instruments import Virtual_Oven
        >>> Virtual_Oven is not None
        True

        """
        self._base_name = 'Virtual_Oven'
        temperature_chamber.__init__(self)

    def _write_temperature(self, value):
        self.setpoint = value
        self._wait_settle()

    def _read_temperature_sense(self):
        return self.setpoint

    def _enable(self, enable):
        pass
