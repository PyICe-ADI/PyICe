# Changelog 

All notable changes to this project will be recorded in this file.  No
releases will be made unless a summary is documented here.  Please use 
[KeepAChangelog](https://keepachangelog.com/en) as a reference


## Unreleased - 2023-10-04

### Changed
- `integer_channel.add_preset()` now raises `ChannelValueException` when a
numeric preset is outside the channel's write limits, instead of failing on
the first write. This also applies to `twi_instrument.populate_from_file`,
`populate_from_ipxact` and `populate_from_yoda_json_bridge`. Presets are raw
bit patterns; negative values on signed channels must be supplied in two's
complement. (#245)
- `LTC_plot` SVG output now converts text to vector paths
(`svg.fonttype = "path"`), eliminating font-availability issues on Linux
renderers. SVG text is no longer searchable/selectable but renders identically
across all environments. Font family falls back through Arial, Liberation Sans,
DejaVu Sans.
### Fixed
- Exception handling in the hameg_4040 driver.
### Changed 
- Large import infrastructure change. lab_utils and data_utils are now 
separated from their large files into smaller files within folders.  This will
break any legacy PyICe code. 

## [0.0.4] - N/A
This was the first release of PyICe.