#!/usr/bin/env python3
"""Add doctests to all methods in lab_core.py that have docstrings but no doctests."""

import re
import json

FILEPATH = '/tmp/PyICe-docstrings/PyICe/lab_core.py'

def add_doctest(filepath, method_sig, doctest_lines, nth=1):
    with open(filepath, 'rb') as f:
        content = f.read()
    eol = b'\r\n' if b'\r\n' in content else b'\n'
    lines = content.split(eol)
    sig_bytes = method_sig.encode()
    count = 0
    for i, line in enumerate(lines):
        if sig_bytes in line:
            count += 1
            if count < nth: continue
            for j in range(i+1, min(i+5, len(lines))):
                if b'"""' in lines[j] or b"'''" in lines[j]:
                    ds_start = j; break
            else: continue
            for k in range(ds_start, min(ds_start+60, len(lines))):
                if b'>>>' in lines[k]: return False
                if k > ds_start and lines[k].strip() in (b'"""', b"'''"):break
            indent = b''
            idx = lines[ds_start].find(b'"""')
            if idx < 0: idx = lines[ds_start].find(b"'''")
            if idx >= 0: indent = b' ' * idx
            for k in range(ds_start+1, min(ds_start+60, len(lines))):
                stripped = lines[k].strip()
                if stripped in (b'Args:', b'Returns:', b'Raises:', b'Yields:', b'"""', b"'''"):
                    insert_at = k; break
            else: continue
            dt_lines = [b'']
            for dl in doctest_lines:
                dt_lines.append(indent + dl.encode())
            dt_lines.append(b'')
            for idx_offset, dl in enumerate(dt_lines):
                lines.insert(insert_at + idx_offset, dl)
            with open(filepath, 'wb') as f:
                f.write(eol.join(lines))
            return True
    return False

count = 0

# ============================================================
# delegator class methods
# ============================================================

# delegator.__init__
if add_doctest(FILEPATH, 'def __init__(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.get_delegator() is d',
    'True',
    '>>> d.threadable()',
    'True',
], nth=1):
    count += 1
    print(f"  {count}: delegator.__init__")

# delegator.set_delegator
if add_doctest(FILEPATH, 'def set_delegator(self, delegator):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d1 = delegator()',
    '>>> d2 = delegator()',
    '>>> d1.set_delegator(d2)',
    '>>> d1.get_delegator() is d2',
    'True',
]):
    count += 1
    print(f"  {count}: delegator.set_delegator")

# delegator.get_delegator
if add_doctest(FILEPATH, 'def get_delegator(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.get_delegator() is d',
    'True',
]):
    count += 1
    print(f"  {count}: delegator.get_delegator")

# delegator.set_allow_threading
if add_doctest(FILEPATH, 'def set_allow_threading(self, state=True):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.set_allow_threading(False)',
    '>>> d.threadable()',
    'False',
    '>>> d.set_allow_threading()',
    '>>> d.threadable()',
    'True',
]):
    count += 1
    print(f"  {count}: delegator.set_allow_threading")

# delegator.threadable
if add_doctest(FILEPATH, 'def threadable(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.threadable()',
    'True',
]):
    count += 1
    print(f"  {count}: delegator.threadable")

# delegator.resolve_delegator
if add_doctest(FILEPATH, 'def resolve_delegator(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d1 = delegator()',
    '>>> d1.resolve_delegator() is d1',
    'True',
    '>>> d2 = delegator()',
    '>>> d2.set_delegator(d1)',
    '>>> d2.resolve_delegator() is d1',
    'True',
]):
    count += 1
    print(f"  {count}: delegator.resolve_delegator")

# delegator.add_interface
if add_doctest(FILEPATH, 'def add_interface(self, interface):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d._interfaces',
    '[]',
    '>>> d.add_interface("iface1")',
    '>>> d._interfaces',
    '[\'iface1\']',
]):
    count += 1
    print(f"  {count}: delegator.add_interface")

# delegator.lock_interfaces
if add_doctest(FILEPATH, 'def lock_interfaces(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.lock_interfaces()  # No interfaces, no-op',
]):
    count += 1
    print(f"  {count}: delegator.lock_interfaces")

# delegator.unlock_interfaces
if add_doctest(FILEPATH, 'def unlock_interfaces(self):', [
    '>>> from PyICe.lab_core import delegator',
    '>>> d = delegator()',
    '>>> d.unlock_interfaces()  # No interfaces, no-op',
]):
    count += 1
    print(f"  {count}: delegator.unlock_interfaces")

# delegator.write_delegated_channel_list
if add_doctest(FILEPATH, 'def write_delegated_channel_list(self, channel_value_list):', [
    '>>> from PyICe.lab_core import master',
    '>>> m = master()',
    '>>> ch = m.add_channel_dummy("wdcl")',
    '>>> m.write_delegated_channel_list([(ch, 42)])',
    '>>> ch.read()',
    '42',
]):
    count += 1
    print(f"  {count}: delegator.write_delegated_channel_list")

# delegator.read_delegated_channel_list (first occurrence in delegator class)
if add_doctest(FILEPATH, 'def read_delegated_channel_list(self, channel_list):', [
    '>>> from PyICe.lab_core import master',
    '>>> m = master()',
    '>>> ch = m.add_channel_dummy("rdcl")',
    '>>> _ = ch.write(99)',
    '>>> result = m.read_delegated_channel_list([ch])',
    '>>> result["rdcl"]',
    '99',
], nth=1):
    count += 1
    print(f"  {count}: delegator.read_delegated_channel_list")

# ============================================================
# channel class methods
# ============================================================

# channel.read_without_delegator
if add_doctest(FILEPATH, 'def read_without_delegator(self, force_data=False, data=None, **kwargs):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("rwd", write_function=lambda v: v)',
    '>>> _ = ch.write(7)',
    '>>> ch.read_without_delegator()',
    '7',
    '>>> ch.read_without_delegator(force_data=True, data=99)',
    '99',
], nth=1):
    count += 1
    print(f"  {count}: channel.read_without_delegator")

# channel.add_preset
if add_doctest(FILEPATH, 'def add_preset(self, preset_value, preset_description=None):', [
    '>>> from PyICe.lab_core import master',
    '>>> m = master()',
    '>>> ch = m.add_channel_dummy("vdd")',
    '>>> ch.add_preset(3.3)',
    '>>> ch.add_preset(1.8, preset_description="low power")',
    '>>> sorted(ch.get_presets())',
    "['1.8', '3.3']",
]):
    count += 1
    print(f"  {count}: channel.add_preset")

# channel.get_preset_description
if add_doctest(FILEPATH, 'def get_preset_description(self, preset_name):', [
    '>>> from PyICe.lab_core import master',
    '>>> m = master()',
    '>>> ch = m.add_channel_dummy("vdd")',
    '>>> ch.add_preset(3.3, preset_description="nominal")',
    '>>> ch.get_preset_description("3.3")',
    "'nominal'",
]):
    count += 1
    print(f"  {count}: channel.get_preset_description")

# channel._set_value
if add_doctest(FILEPATH, 'def _set_value(self, value):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("sv")',
    '>>> ch._set_value(42)',
    '>>> ch._value',
    '42',
]):
    count += 1
    print(f"  {count}: channel._set_value")

# channel.add_tag
if add_doctest(FILEPATH, 'def add_tag(self, tag):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("tagged")',
    '>>> _ = ch.add_tag("my_tag")',
    '>>> "my_tag" in ch.get_tags()',
    'True',
]):
    count += 1
    print(f"  {count}: channel.add_tag")

# channel.add_tags
if add_doctest(FILEPATH, 'def add_tags(self, tag_list):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("multi_tag")',
    '>>> _ = ch.add_tags(["t1", "t2"])',
    '>>> "t1" in ch.get_tags() and "t2" in ch.get_tags()',
    'True',
]):
    count += 1
    print(f"  {count}: channel.add_tags")

# channel.get_tags
if add_doctest(FILEPATH, 'def get_tags(self, include_category=True):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("gt")',
    '>>> _ = ch.add_tag("voltage")',
    '>>> "voltage" in ch.get_tags()',
    'True',
]):
    count += 1
    print(f"  {count}: channel.get_tags")

# channel.set_read_access
if add_doctest(FILEPATH, 'def set_read_access(self, readable=True):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("ra")',
    '>>> ch.is_readable()',
    'True',
    '>>> _ = ch.set_read_access(False)',
    '>>> ch.is_readable()',
    'False',
]):
    count += 1
    print(f"  {count}: channel.set_read_access")

# channel.set_write_resolution
if add_doctest(FILEPATH, 'def set_write_resolution(self, decimal_digits=None):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("wr", write_function=lambda v: v)',
    '>>> _ = ch.set_write_resolution(3)',
    '>>> ch._write_resolution',
    '3',
]):
    count += 1
    print(f"  {count}: channel.set_write_resolution")

# channel.get_max_write_limit
if add_doctest(FILEPATH, 'def get_max_write_limit(self):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("maxwl", write_function=lambda v: v)',
    '>>> _ = ch.set_max_write_limit(10)',
    '>>> ch.get_max_write_limit()',
    '10',
], nth=1):
    count += 1
    print(f"  {count}: channel.get_max_write_limit")

# channel.get_min_write_limit (first one - base channel)
if add_doctest(FILEPATH, 'def get_min_write_limit(self, formatted=False):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("minwl", write_function=lambda v: v)',
    '>>> _ = ch.set_min_write_limit(-5)',
    '>>> ch.get_min_write_limit()',
    '-5',
], nth=1):
    count += 1
    print(f"  {count}: channel.get_min_write_limit")

# channel.set_max_write_warning
if add_doctest(FILEPATH, 'def set_max_write_warning(self, max):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("mww", write_function=lambda v: v)',
    '>>> _ = ch.set_max_write_warning(100)',
    '>>> ch.get_max_write_warning()',
    '100',
]):
    count += 1
    print(f"  {count}: channel.set_max_write_warning")

# channel.set_min_write_warning
if add_doctest(FILEPATH, 'def set_min_write_warning(self, min):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("mnww", write_function=lambda v: v)',
    '>>> _ = ch.set_min_write_warning(-100)',
    '>>> ch.get_min_write_warning()',
    '-100',
]):
    count += 1
    print(f"  {count}: channel.set_min_write_warning")

# channel.get_max_write_warning
if add_doctest(FILEPATH, 'def get_max_write_warning(self):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("gmww", write_function=lambda v: v)',
    '>>> _ = ch.set_max_write_warning(50)',
    '>>> ch.get_max_write_warning()',
    '50',
]):
    count += 1
    print(f"  {count}: channel.get_max_write_warning")

# channel.get_min_write_warning
if add_doctest(FILEPATH, 'def get_min_write_warning(self, formatted=False):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("gmnww", write_function=lambda v: v)',
    '>>> _ = ch.set_min_write_warning(-50)',
    '>>> ch.get_min_write_warning()',
    '-50',
]):
    count += 1
    print(f"  {count}: channel.get_min_write_warning")

# channel.add_change_callback
if add_doctest(FILEPATH, 'def add_change_callback(self, change_callback=None):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("acc", write_function=lambda v: v)',
    '>>> calls = []',
    '>>> _ = ch.add_change_callback(lambda c, v: calls.append(v))',
    '>>> _ = ch.write(1)',
    '>>> _ = ch.write(2)',
    '>>> calls',
    '[2]',
]):
    count += 1
    print(f"  {count}: channel.add_change_callback")

# channel.remove_change_callback
if add_doctest(FILEPATH, 'def remove_change_callback(self, change_callback=None):', [
    '>>> from PyICe.lab_core import channel',
    '>>> ch = channel("rcc", write_function=lambda v: v)',
    '>>> cb = lambda c, v: None',
    '>>> _ = ch.add_change_callback(cb)',
    '>>> len(ch._change_callbacks)',
    '1',
    '>>> _ = ch.remove_change_callback(cb)',
    '>>> len(ch._change_callbacks)',
    '0',
]):
    count += 1
    print(f"  {count}: channel.remove_change_callback")

# channel.default_print_callback
if add_doctest(FILEPATH, 'def default_print_callback(channel, value):', [
    '>>> from PyICe.lab_core import channel',
    '>>> channel.default_print_callback(channel("test_dpc"), 42)',
    'test_dpc changed to 42.',
]):
    count += 1
    print(f"  {count}: channel.default_print_callback")

# ============================================================
# ChannelReadException
# ============================================================

# ChannelReadException.__ne__
if add_doctest(FILEPATH, 'def __ne__(self, other):', [
    '>>> from PyICe.lab_core import ChannelReadException',
    '>>> e = ChannelReadException("fail")',
    '>>> e != 42',
    'True',
    '>>> e != e',
    'True',
]):
    count += 1
    print(f"  {count}: ChannelReadException.__ne__")

# ============================================================
# integer_channel class methods
# ============================================================

# integer_channel.__init__
if add_doctest(FILEPATH, "def __init__(self, name, size, read_function=None, write_function=None):", [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("reg", size=8)',
    '>>> ic.get_size()',
    '8',
    '>>> ic.get_name()',
    "'reg'",
]):
    count += 1
    print(f"  {count}: integer_channel.__init__")

# integer_channel.__str__
if add_doctest(FILEPATH, 'def __str__(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("myreg", size=8, write_function=lambda v: v)',
    '>>> "myreg" in str(ic)',
    'True',
], nth=2):
    count += 1
    print(f"  {count}: integer_channel.__str__")

# integer_channel.check_sign (static method)
if add_doctest(FILEPATH, 'def check_sign(data):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> integer_channel.check_sign(5)',
    'False',
    '>>> integer_channel.check_sign(-3)',
    'True',
    '>>> integer_channel.check_sign(0)',
    'False',
]):
    count += 1
    print(f"  {count}: integer_channel.check_sign")

# integer_channel.get_size
if add_doctest(FILEPATH, 'def get_size(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("sz", size=16)',
    '>>> ic.get_size()',
    '16',
]):
    count += 1
    print(f"  {count}: integer_channel.get_size")

# integer_channel.get_max_write_limit (2nd occurrence)
if add_doctest(FILEPATH, 'def get_max_write_limit(self, formatted=False):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("mxwl", size=8, write_function=lambda v: v)',
    '>>> ic.get_max_write_limit()',
    '255',
], nth=1):
    count += 1
    print(f"  {count}: integer_channel.get_max_write_limit")

# integer_channel.get_min_write_limit (2nd occurrence)
if add_doctest(FILEPATH, 'def get_min_write_limit(self, formatted=False):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("mnwl", size=8, write_function=lambda v: v)',
    '>>> ic.get_min_write_limit()',
    '0',
], nth=2):
    count += 1
    print(f"  {count}: integer_channel.get_min_write_limit")

# integer_channel.get_format
if add_doctest(FILEPATH, 'def get_format(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("gf", size=8)',
    '>>> ic.get_format()',
]):
    count += 1
    print(f"  {count}: integer_channel.get_format")

# integer_channel.use_presets_read
if add_doctest(FILEPATH, 'def use_presets_read(self, bool):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("upr", size=8)',
    '>>> ic.use_presets_read(True)',
    '>>> ic._use_presets_read',
    'True',
]):
    count += 1
    print(f"  {count}: integer_channel.use_presets_read")

# integer_channel.use_presets_write
if add_doctest(FILEPATH, 'def use_presets_write(self, bool):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("upw", size=8)',
    '>>> ic.use_presets_write(True)',
    '>>> ic._use_presets_write',
    'True',
]):
    count += 1
    print(f"  {count}: integer_channel.use_presets_write")

# integer_channel.using_presets_read
if add_doctest(FILEPATH, 'def using_presets_read(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("rpr", size=8)',
    '>>> ic.using_presets_read()',
    'False',
]):
    count += 1
    print(f"  {count}: integer_channel.using_presets_read")

# integer_channel.using_presets_write
if add_doctest(FILEPATH, 'def using_presets_write(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("rpw", size=8)',
    '>>> ic.using_presets_write()',
    'False',
]):
    count += 1
    print(f"  {count}: integer_channel.using_presets_write")

# integer_channel.add_format
if add_doctest(FILEPATH, 'def add_format(self, format_name, format_function=None, unformat_function=None, signed=False, units=', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("af", size=8, write_function=lambda v: v)',
    '>>> ic.add_format("volts", format_function=lambda x: x * 0.1, unformat_function=lambda x: int(x / 0.1), units="V")',
    '>>> "volts" in ic.get_formats()',
    'True',
]):
    count += 1
    print(f"  {count}: integer_channel.add_format")

# integer_channel._pwl_interp (static method)
if add_doctest(FILEPATH, 'def _pwl_interp(val, in_pts, out_pts):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> integer_channel._pwl_interp(5, [0, 10], [0, 100])',
    '50.0',
]):
    count += 1
    print(f"  {count}: integer_channel._pwl_interp")

# integer_channel.unformat_function (lambda inside add_format)
# This is a nested def, skip - it's inside add_format
# Actually let's check the sig more carefully

# integer_channel.remove_format
if add_doctest(FILEPATH, 'def remove_format(self, format_name):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("rf", size=8, write_function=lambda v: v)',
    '>>> ic.add_format("volts", format_function=lambda x: x * 0.1, unformat_function=lambda x: int(x / 0.1))',
    '>>> ic.remove_format("volts")',
    '>>> "volts" in ic.get_formats()',
    'False',
]):
    count += 1
    print(f"  {count}: integer_channel.remove_format")

# integer_channel.get_formats
if add_doctest(FILEPATH, 'def get_formats(self):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("gfs", size=8)',
    '>>> ic.get_formats()',
    '[]',
]):
    count += 1
    print(f"  {count}: integer_channel.get_formats")

# integer_channel.format
if add_doctest(FILEPATH, 'def format(self, data, format, use_presets):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("fmt", size=8, write_function=lambda v: v)',
    '>>> ic.add_format("dbl", format_function=lambda x: x * 2, unformat_function=lambda x: x // 2)',
    '>>> ic.format(10, "dbl", False)',
    '20',
]):
    count += 1
    print(f"  {count}: integer_channel.format")

# integer_channel.sql_format
if add_doctest(FILEPATH, 'def sql_format(self, format, use_presets):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("sqf", size=8)',
    '>>> result = ic.sql_format(None, False)',
    '>>> isinstance(result, str)',
    'True',
]):
    count += 1
    print(f"  {count}: integer_channel.sql_format")

# integer_channel._slope_int_str (static method)
if add_doctest(FILEPATH, 'def _slope_int_str(p1, p2):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> integer_channel._slope_int_str((0, 0), (10, 100))',
    "'10.0 * code + 0.0'",
]):
    count += 1
    print(f"  {count}: integer_channel._slope_int_str")

# integer_channel.unformat
if add_doctest(FILEPATH, 'def unformat(self, string, format, use_presets):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("uf", size=8, write_function=lambda v: v)',
    '>>> ic.add_format("dbl", format_function=lambda x: x * 2, unformat_function=lambda x: x // 2)',
    '>>> ic.unformat(20, "dbl", False)',
    '10',
]):
    count += 1
    print(f"  {count}: integer_channel.unformat")

# integer_channel.get_units
if add_doctest(FILEPATH, 'def get_units(self, format):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("gu", size=8)',
    '>>> ic.add_format("volts", format_function=lambda x: x, unformat_function=lambda x: x, units="V")',
    '>>> ic.get_units("volts")',
    "'V'",
]):
    count += 1
    print(f"  {count}: integer_channel.get_units")

# integer_channel.format_read
if add_doctest(FILEPATH, 'def format_read(self, raw_data):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("fr", size=8)',
    '>>> ic.format_read(42)',
    '42',
]):
    count += 1
    print(f"  {count}: integer_channel.format_read")

# integer_channel.format_write
if add_doctest(FILEPATH, 'def format_write(self, value):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("fw", size=8, write_function=lambda v: v)',
    '>>> ic.format_write(100)',
    '100',
]):
    count += 1
    print(f"  {count}: integer_channel.format_write")

# integer_channel.twosComplementToSigned
if add_doctest(FILEPATH, 'def twosComplementToSigned(self, binary):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("tcs", size=8)',
    '>>> ic.twosComplementToSigned(255)',
    '-1',
    '>>> ic.twosComplementToSigned(127)',
    '127',
]):
    count += 1
    print(f"  {count}: integer_channel.twosComplementToSigned")

# integer_channel.signedToTwosComplement
if add_doctest(FILEPATH, 'def signedToTwosComplement(self, signed):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("stc", size=8)',
    '>>> ic.signedToTwosComplement(-1)',
    '255',
    '>>> ic.signedToTwosComplement(127)',
    '127',
]):
    count += 1
    print(f"  {count}: integer_channel.signedToTwosComplement")

# integer_channel.write
if add_doctest(FILEPATH, 'def write(self, value):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("iw", size=8, write_function=lambda v: v)',
    '>>> ic.write(100)',
    '100',
], nth=2):
    count += 1
    print(f"  {count}: integer_channel.write")

# integer_channel.write_unformatted
if add_doctest(FILEPATH, 'def write_unformatted(self, value):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("iwu", size=8, write_function=lambda v: v)',
    '>>> ic.write_unformatted(200)',
    '200',
]):
    count += 1
    print(f"  {count}: integer_channel.write_unformatted")

# integer_channel.read_without_delegator (2nd occurrence)
if add_doctest(FILEPATH, 'def read_without_delegator(self, force_data=False, data=None, **kwargs):', [
    '>>> from PyICe.lab_core import integer_channel',
    '>>> ic = integer_channel("irwd", size=8, write_function=lambda v: v)',
    '>>> ic.write(42)',
    '42',
], nth=2):
    count += 1
    print(f"  {count}: integer_channel.read_without_delegator")

# ============================================================
# register class
# ============================================================

# register.__init__
if add_doctest(FILEPATH, 'def __init__(self, name, size, read_function=None, write_function=None, is_register=True):', [
    '>>> from PyICe.lab_core import register',
    '>>> r = register("config", size=8)',
    '>>> r.get_name()',
    "'config'",
    '>>> r.get_size()',
    '8',
]):
    count += 1
    print(f"  {count}: register.__init__")

# register.add_channel
if add_doctest(FILEPATH, 'def add_channel(self, channel_name, bit_offset, bit_size):', [
    '>>> from PyICe.lab_core import register',
    '>>> r = register("cfg", size=8, write_function=lambda v: v)',
    '>>> sub_ch = r.add_channel("bit0", 0, 1)',
    '>>> sub_ch.get_name()',
    "'bit0'",
]):
    count += 1
    print(f"  {count}: register.add_channel")

# register.merge_write_channels
if add_doctest(FILEPATH, 'def merge_write_channels(self):', [
    '>>> from PyICe.lab_core import register',
    '>>> r = register("mrg", size=8, write_function=lambda v: v)',
    '>>> _ = r.add_channel("lo", 0, 4)',
    '>>> _ = r.add_channel("hi", 4, 4)',
    '>>> isinstance(r.merge_write_channels(), int)',
    'True',
]):
    count += 1
    print(f"  {count}: register.merge_write_channels")

# register.get_channels
if add_doctest(FILEPATH, 'def get_channels(self):', [
    '>>> from PyICe.lab_core import register',
    '>>> r = register("gc", size=8)',
    '>>> _ = r.add_channel("bit0", 0, 1)',
    '>>> len(r.get_channels())',
    '1',
]):
    count += 1
    print(f"  {count}: register.get_channels")

# register.get_all_channels
if add_doctest(FILEPATH, 'def get_all_channels(self):', [
    '>>> from PyICe.lab_core import register',
    '>>> r = register("gac", size=8)',
    '>>> _ = r.add_channel("b0", 0, 1)',
    '>>> chs = r.get_all_channels()',
    '>>> len(chs) >= 1',
    'True',
]):
    count += 1
    print(f"  {count}: register.get_all_channels")

# ============================================================
# channel_group class methods
# ============================================================

# Now read channel_group to understand its methods
print(f"\nProcessed up to count={count}, continuing with channel_group...")
