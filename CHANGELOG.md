# Changelog 

All notable changes to this project will be recorded in this file.  No
releases will be made unless a summary is documented here.  Please use 
[KeepAChangelog](https://keepachangelog.com/en) as a reference


## Unreleased - 2023-10-04

### Added
- `lab_utils.preset_to_raw(value, bitCount, signed=False)` converts a preset or
enumerated value to the raw bit pattern an `integer_channel` writes: negative
values are encoded in two's complement when `signed` is true, and the result
must fit in `0..2**bitCount - 1` or `ValueError` is raised. Register-map
importers can use it instead of calling `signedToTwosComplement` and
`twi_interface.check_size` themselves. (#247)
- `integer_channel.add_preset()` takes an optional `signed` argument. With
`signed=True` a negative preset is stored in two's complement; the default
(`None`) uses the signed flag of the active format. Out-of-range signed presets
raise `ChannelValueException`. `populate_from_yoda_json_bridge` passes the
field's `data_format` so negative enums on `Signed` fields are encoded;
`populate_from_ipxact` passes `signed=False`. (#247)
### Changed
- `integer_channel.add_preset()` now raises `ChannelValueException` when a
numeric preset is outside the channel's write limits, instead of failing on
the first write. This also applies to `twi_instrument.populate_from_file`,
`populate_from_ipxact` and `populate_from_yoda_json_bridge`. Presets are raw
bit patterns; negative values on signed channels must be supplied in two's
complement. (#245)
- Input validation no longer relies on `assert`, so it is not bypassed under
`python -O`. `lab_utils.signedToTwosComplement()` (and the signed-format
unformat path of `integer_channel`) raises `ValueError` for out-of-range
values, matching `twosComplementToSigned()`. Both helpers raise `TypeError`
for a non-integer `bitCount` and `ValueError` for `bitCount < 1`.
`integer_channel()` raises
`TypeError` for a non-integer `size` and `ValueError` for `size < 1`.
`twi_instrument` raises `ValueError` when a bitfield's offset + size exceeds
the register width. Callers catching `AssertionError` must update. (#246)
### Fixed
- Exception handling in the hameg_4040 driver.
- `lab_gui` now raises `ImportError` with the PySide2 and PySide6 failure
reasons when no Qt binding can be imported. Previously the error was reduced
to a warning and the import then failed with
`AttributeError: 'NoneType' object has no attribute 'QLabel'`, hiding the
cause (e.g. a conflicting Qt library on `LD_LIBRARY_PATH`).
### Changed 
- Large import infrastructure change. lab_utils and data_utils are now 
separated from their large files into smaller files within folders.  This will
break any legacy PyICe code. 

## [0.0.4] - N/A
This was the first release of PyICe.