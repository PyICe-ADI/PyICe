"""IP-XACT (IEEE 1685-2014 / SPIRIT 1685-2009) register map parser and converter for PyICe.

Parses IP-XACT component XML into lightweight dataclasses suitable for
consumption by twi_instrument.populate_from_ipxact() and
spiInstrument.from_ipxact().

Getting Started
===============

**Option A: Direct import (skip JSON entirely)**

The simplest path — go straight from IP-XACT XML to live PyICe channels::

    from PyICe.twi_instrument import twi_instrument

    # 'interface' is your TWI/I2C master from lab_interfaces
    inst = twi_instrument(interface)
    inst.populate_from_ipxact("path/to/my_device.xml", addr7=0x50)

    # All register fields are now available as channels:
    inst.write("ENABLE", 1)
    print(inst.read("STATUS"))

**Option B: Convert IP-XACT to PyICe JSON first, then import**

Useful when you want a checked-in JSON artifact that multiple scripts share::

    from PyICe.ipxact_parser import ipxact_to_pyice_json

    # One-time conversion — creates a JSON file compatible with
    # twi_instrument.populate_from_yoda_json_bridge()
    ipxact_to_pyice_json(
        "path/to/my_device.xml",
        output_file="path/to/my_device_regmap.json",
    )

Then in your bench script::

    from PyICe.twi_instrument import twi_instrument

    inst = twi_instrument(interface)
    inst.populate_from_yoda_json_bridge("path/to/my_device_regmap.json",
                                        i2c_addr7=0x50)

**Option C: Command-line conversion (no Python code required)**

Run from a terminal::

    python -m PyICe.ipxact_parser my_device.xml -o my_device_regmap.json

This writes the PyICe JSON file directly. Run with ``--help`` for all options::

    python -m PyICe.ipxact_parser --help

Typical project layout::

    infrastructure/
    └── regmap/
        ├── my_device.xml              # IP-XACT source (from EDA tools)
        └── my_device_regmap.json      # Generated PyICe JSON (checked in)

>>> from PyICe.ipxact_parser import IpxactParser, IpxactField
>>> IpxactParser is not None
True
>>> IpxactField is not None
True

"""
import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field as dataclass_field
from typing import Optional

logger = logging.getLogger(__name__)

KNOWN_NAMESPACES = {
    "http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009": "spirit",
    "http://www.accellera.org/XMLSchema/IPXACT/1685-2014": "ipxact",
}

IPXACT_MODIFIED_WRITE_TO_PYICE = {
    "oneToClear": "W1C",
    "oneToSet": "W1S",
    "zeroToClear": "W0C",
    "zeroToSet": "W0S",
    "clear": None,
    "set": None,
    "modify": None,
}


@dataclass
class IpxactField:
    """A single bitfield within a register.

    >>> f = IpxactField(name="EN", bit_offset=0, bit_width=1,
    ...     access="read-write", reset_value=0, modified_write_value=None,
    ...     description="Enable", enumerated_values=[("off", 0, "disabled")])
    >>> f.name
    'EN'
    >>> f.enumerated_values
    [('off', 0, 'disabled')]
    """
    name: str
    bit_offset: int
    bit_width: int
    access: str
    reset_value: Optional[int]
    modified_write_value: Optional[str]
    description: str
    enumerated_values: list = dataclass_field(default_factory=list)


@dataclass
class IpxactRegister:
    """A single addressable register containing fields.

    >>> r = IpxactRegister(name="CTRL", address_offset=0x10, size=8,
    ...     access="read-write", reset_value=None, description="Control", fields=[])
    >>> r.address_offset
    16
    """
    name: str
    address_offset: int
    size: int
    access: str
    reset_value: Optional[int]
    description: str
    fields: list = dataclass_field(default_factory=list)


@dataclass
class IpxactAddressBlock:
    """An address block grouping registers at a base address."""
    name: str
    base_address: int
    range: int
    width: int
    registers: list = dataclass_field(default_factory=list)


@dataclass
class IpxactMemoryMap:
    """Top-level memory map containing address blocks."""
    name: str
    address_blocks: list = dataclass_field(default_factory=list)


def ipxact_modified_write_to_pyice(modified_write_value):
    """Convert IP-XACT modifiedWriteValue to PyICe special access string.

    >>> ipxact_modified_write_to_pyice("oneToClear")
    'W1C'
    >>> ipxact_modified_write_to_pyice("oneToSet")
    'W1S'
    >>> ipxact_modified_write_to_pyice("zeroToClear")
    'W0C'
    >>> ipxact_modified_write_to_pyice("zeroToSet")
    'W0S'
    >>> ipxact_modified_write_to_pyice("modify") is None
    True
    """
    if modified_write_value not in IPXACT_MODIFIED_WRITE_TO_PYICE:
        logger.warning("Unrecognized modifiedWriteValue: '%s'; ignoring.",
                       modified_write_value)
        return None
    return IPXACT_MODIFIED_WRITE_TO_PYICE[modified_write_value]


def ipxact_access_to_rw(access_str):
    """Map IP-XACT access string to (is_readable, is_writable).

    >>> ipxact_access_to_rw("read-write")
    (True, True)
    >>> ipxact_access_to_rw("read-only")
    (True, False)
    >>> ipxact_access_to_rw("write-only")
    (False, True)
    >>> ipxact_access_to_rw("read-writeOnce")
    (True, True)
    >>> ipxact_access_to_rw("writeOnce")
    (False, True)
    >>> ipxact_access_to_rw("banana")
    Traceback (most recent call last):
        ...
    ValueError: Unrecognized IP-XACT access type: 'banana'
    """
    _MAP = {
        "read-write": (True, True),
        "read-only": (True, False),
        "write-only": (False, True),
        "read-writeOnce": (True, True),
        "writeOnce": (False, True),
    }
    if access_str not in _MAP:
        raise ValueError(f"Unrecognized IP-XACT access type: '{access_str}'")
    return _MAP[access_str]


class IpxactParser:
    """Parse an IP-XACT component XML file into dataclass structures.

    Supports both SPIRIT 1685-2009 and IEEE 1685-2014 namespaces.

    >>> from PyICe.ipxact_parser import IpxactParser
    >>> hasattr(IpxactParser, 'parse')
    True
    """

    def __init__(self, filename):
        self._filename = filename
        self._tree = ET.parse(filename)
        self._root = self._tree.getroot()
        self._ns = self._detect_namespace(self._root)
        self._prefix = KNOWN_NAMESPACES[self._ns]

    def parse(self):
        """Return list of IpxactMemoryMap found in the component.

        Raises:
            NotImplementedError: For register arrays with <dim>.
        """
        memory_maps = []
        for mm_elem in self._findall(self._root, "memoryMaps/memoryMap"):
            memory_maps.append(self._parse_memory_map(mm_elem))
        if not memory_maps:
            for mm_elem in self._findall(self._root, "memoryMap"):
                memory_maps.append(self._parse_memory_map(mm_elem))
        return memory_maps

    @staticmethod
    def _detect_namespace(root):
        """Detect IP-XACT namespace from root element tag.

        >>> from xml.etree.ElementTree import fromstring
        >>> IpxactParser._detect_namespace(fromstring(
        ...     '<spirit:component xmlns:spirit="http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009"/>'))
        'http://www.spiritconsortium.org/XMLSchema/SPIRIT/1685-2009'
        >>> IpxactParser._detect_namespace(fromstring(
        ...     '<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014"/>'))
        'http://www.accellera.org/XMLSchema/IPXACT/1685-2014'
        >>> IpxactParser._detect_namespace(fromstring('<component/>'))
        Traceback (most recent call last):
            ...
        ValueError: Unrecognized IP-XACT namespace in root tag: component
        """
        tag = root.tag
        if tag.startswith("{"):
            ns = tag[1:tag.index("}")]
            if ns in KNOWN_NAMESPACES:
                return ns
        raise ValueError(f"Unrecognized IP-XACT namespace in root tag: {tag}")

    @staticmethod
    def resolve_expression(text):
        """Resolve IP-XACT address/value expression to int.

        >>> IpxactParser.resolve_expression("0x10")
        16
        >>> IpxactParser.resolve_expression("32")
        32
        >>> IpxactParser.resolve_expression("'h2A")
        42
        >>> IpxactParser.resolve_expression("id('param')")
        Traceback (most recent call last):
            ...
        NotImplementedError: Parameterized expressions not supported: id('param')
        """
        if text is None:
            return None
        text = text.strip()
        if not text:
            return None
        if "id(" in text or "(" in text:
            raise NotImplementedError(
                f"Parameterized expressions not supported: {text}")
        if text.startswith("'h") or text.startswith("'H"):
            return int(text[2:], 16)
        if text.startswith("0x") or text.startswith("0X"):
            return int(text, 16)
        if text.startswith("0b") or text.startswith("0B"):
            return int(text, 2)
        return int(text)

    def _tag(self, local_name):
        return f"{{{self._ns}}}{local_name}"

    def _find(self, elem, path):
        parts = path.split("/")
        qualified = "/".join(self._tag(p) for p in parts)
        return elem.find(qualified)

    def _findall(self, elem, path):
        parts = path.split("/")
        qualified = "/".join(self._tag(p) for p in parts)
        return elem.findall(qualified)

    def _text(self, elem, path, default=None):
        child = self._find(elem, path)
        if child is not None and child.text:
            return child.text.strip()
        return default

    def _parse_memory_map(self, mm_elem):
        name = self._text(mm_elem, "name") or "unnamed"
        address_blocks = []
        for ab_elem in self._findall(mm_elem, "addressBlock"):
            address_blocks.append(self._parse_address_block(ab_elem))
        return IpxactMemoryMap(name=name, address_blocks=address_blocks)

    def _parse_address_block(self, ab_elem):
        name = self._text(ab_elem, "name") or "unnamed"
        base_address = self.resolve_expression(self._text(ab_elem, "baseAddress")) or 0
        range_val = self.resolve_expression(self._text(ab_elem, "range")) or 0
        width = self.resolve_expression(self._text(ab_elem, "width")) or 8
        registers = []
        for reg_file in self._findall(ab_elem, "registerFile"):
            logger.warning("registerFile '%s' encountered; flattening into parent addressBlock.",
                           self._text(reg_file, "name"))
            for reg_elem in self._findall(reg_file, "register"):
                registers.append(self._parse_register(reg_elem))
        for reg_elem in self._findall(ab_elem, "register"):
            registers.append(self._parse_register(reg_elem))
        return IpxactAddressBlock(name=name, base_address=base_address,
                                  range=range_val, width=width, registers=registers)

    def _parse_register(self, reg_elem):
        name = self._text(reg_elem, "name") or "unnamed"
        dim_elem = self._find(reg_elem, "dim")
        if dim_elem is not None and dim_elem.text:
            dim_val = self.resolve_expression(dim_elem.text)
            if dim_val is not None and dim_val > 1:
                raise NotImplementedError(
                    f"Register array (dim={dim_val}) not supported: '{name}'")
        address_offset = self.resolve_expression(self._text(reg_elem, "addressOffset")) or 0
        size = self.resolve_expression(self._text(reg_elem, "size")) or 8
        access = self._text(reg_elem, "access") or "read-write"
        description = self._text(reg_elem, "description") or ""
        reset_value = None
        reset_elem = self._find(reg_elem, "reset")
        if reset_elem is not None:
            reset_value = self.resolve_expression(self._text(reset_elem, "value"))
        fields = []
        for field_elem in self._findall(reg_elem, "field"):
            fields.append(self._parse_field(field_elem, fallback_access=access))
        return IpxactRegister(name=name, address_offset=address_offset, size=size,
                              access=access, reset_value=reset_value,
                              description=description, fields=fields)

    def _parse_field(self, field_elem, fallback_access="read-write"):
        name = self._text(field_elem, "name") or "unnamed"
        bit_offset = self.resolve_expression(self._text(field_elem, "bitOffset")) or 0
        bit_width = self.resolve_expression(self._text(field_elem, "bitWidth")) or 1
        access = self._text(field_elem, "access") or fallback_access
        description = self._text(field_elem, "description") or ""
        modified_write_value = self._text(field_elem, "modifiedWriteValue")
        reset_value = None
        reset_elem = self._find(field_elem, "resets/reset")
        if reset_elem is not None:
            reset_value = self.resolve_expression(self._text(reset_elem, "value"))
        else:
            reset_elem = self._find(field_elem, "reset")
            if reset_elem is not None:
                reset_value = self.resolve_expression(self._text(reset_elem, "value"))
        vendor_ext = self._find(field_elem, "vendorExtensions")
        if vendor_ext is not None:
            logger.info("vendorExtensions on field '%s' ignored.", name)
        enumerated_values = self._parse_enumerated_values(field_elem)
        return IpxactField(name=name, bit_offset=bit_offset, bit_width=bit_width,
                           access=access, reset_value=reset_value,
                           modified_write_value=modified_write_value,
                           description=description,
                           enumerated_values=enumerated_values)

    def _parse_enumerated_values(self, field_elem):
        result = []
        ev_container = self._find(field_elem, "enumeratedValues")
        if ev_container is None:
            return result
        for ev in self._findall(ev_container, "enumeratedValue"):
            ev_name = self._text(ev, "name") or "unnamed"
            ev_value = self.resolve_expression(self._text(ev, "value"))
            ev_desc = self._text(ev, "description") or ""
            result.append((ev_name, ev_value, ev_desc))
        return result


_PYICE_MODIFIED_WRITE_FROM_IPXACT = {
    "oneToClear": "OneToClear",
    "oneToSet": "OneToSet",
    "zeroToClear": "ZeroToClear",
    "zeroToSet": "ZeroToSet",
    "oneToToggle": "OneToToggle",
    "zeroToToggle": "ZeroToToggle",
    "clear": "Clear",
    "set": "Set",
}


def _ipxact_access_to_pyice_str(access_str):
    """Convert IP-XACT access to PyICe JSON 'access' field value.

    >>> _ipxact_access_to_pyice_str("read-write")
    'RW'
    >>> _ipxact_access_to_pyice_str("read-only")
    'R'
    >>> _ipxact_access_to_pyice_str("write-only")
    'W'
    >>> _ipxact_access_to_pyice_str("read-writeOnce")
    'RW'
    >>> _ipxact_access_to_pyice_str("writeOnce")
    'W'
    """
    _MAP = {
        "read-write": "RW",
        "read-only": "R",
        "write-only": "W",
        "read-writeOnce": "RW",
        "writeOnce": "W",
    }
    return _MAP.get(access_str, "RW")


def ipxact_to_pyice_json(ipxact_file, output_file=None,
                         address_block_name=None, memory_map_name=None,
                         base_address=0, indent=2):
    """Convert an IP-XACT XML file to PyICe Yoda JSON register map format.

    The output JSON is a list of register objects compatible with
    ``twi_instrument.populate_from_yoda_json_bridge()``.

    >>> import os, tempfile
    >>> # Verify function exists and is callable
    >>> callable(ipxact_to_pyice_json)
    True

    Args:
        ipxact_file: Path to IP-XACT XML component file.
        output_file: Path to write JSON output. If None, returns the
            JSON data structure (list of dicts) without writing to disk.
        address_block_name: If specified, only convert this address block.
        memory_map_name: If specified, only convert from this memory map.
        base_address: Additional offset added to all register addresses.
        indent: JSON indentation level (default 2). Set to None for compact.

    Returns:
        List of register dicts in PyICe JSON schema format. Also writes
        to output_file if specified.

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
    registers_out = []
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
            for reg in ab.registers:
                address = base_address + ab.base_address + reg.address_offset
                width = reg.size
                functional_groups = [ab.name]
                bitfields = {}
                if not reg.fields:
                    bitfields[reg.name] = {
                        "slicewidth": reg.size,
                        "regoffset": 0,
                        "access": _ipxact_access_to_pyice_str(reg.access),
                        "write_side_effect": "None",
                        "data_format": "Unsigned",
                        "documentation": reg.description,
                        "enums": {},
                    }
                else:
                    for fld in reg.fields:
                        mwv = "None"
                        is_writable = "W" in _ipxact_access_to_pyice_str(fld.access)
                        if fld.modified_write_value and is_writable:
                            mwv = _PYICE_MODIFIED_WRITE_FROM_IPXACT.get(
                                fld.modified_write_value, "None")
                        enums = {}
                        for ev_name, ev_value, _ev_desc in fld.enumerated_values:
                            enums[ev_name] = ev_value
                        bitfields[fld.name] = {
                            "slicewidth": fld.bit_width,
                            "regoffset": fld.bit_offset,
                            "access": _ipxact_access_to_pyice_str(fld.access),
                            "write_side_effect": mwv,
                            "data_format": "Unsigned",
                            "documentation": fld.description,
                            "enums": enums,
                        }
                registers_out.append({
                    "address": address,
                    "width": width,
                    "bitfields": bitfields,
                    "functionalgroups": functional_groups,
                })
    if output_file is not None:
        with open(output_file, 'w') as fp:
            json.dump(registers_out, fp, indent=indent)
        logger.info("Wrote PyICe JSON register map to '%s'.", output_file)
    return registers_out


def _cli_main():
    """Entry point for ``python -m PyICe.ipxact_parser``."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m PyICe.ipxact_parser",
        description=(
            "Convert an IP-XACT XML register map to PyICe JSON format.\n\n"
            "The output JSON is directly consumable by\n"
            "twi_instrument.populate_from_yoda_json_bridge()."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python -m PyICe.ipxact_parser my_device.xml -o my_device_regmap.json\n"
            "  python -m PyICe.ipxact_parser my_device.xml --base-address 0x100\n"
            "  python -m PyICe.ipxact_parser my_device.xml --memory-map default_map\n"
        ),
    )
    parser.add_argument(
        "ipxact_file",
        help="Path to IP-XACT XML component file.")
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON file path. If omitted, prints to stdout.")
    parser.add_argument(
        "--base-address",
        type=lambda x: int(x, 0),
        default=0,
        help="Base address offset added to all registers (default: 0). "
             "Accepts hex (0x...) or decimal.")
    parser.add_argument(
        "--memory-map",
        default=None,
        help="Only convert registers from this named memory map.")
    parser.add_argument(
        "--address-block",
        default=None,
        help="Only convert registers from this named address block.")
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation (default: 2). Use 0 for compact output.")

    args = parser.parse_args()

    indent = args.indent if args.indent > 0 else None

    try:
        result = ipxact_to_pyice_json(
            ipxact_file=args.ipxact_file,
            output_file=args.output,
            memory_map_name=args.memory_map,
            address_block_name=args.address_block,
            base_address=args.base_address,
            indent=indent,
        )
    except (ValueError, NotImplementedError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output is None:
        json.dump(result, sys.stdout, indent=indent)
        print()
    else:
        print(f"Wrote {len(result)} registers to {args.output}")


if __name__ == "__main__":
    _cli_main()
