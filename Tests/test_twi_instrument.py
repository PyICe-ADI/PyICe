"""Tests for twi instrument."""
import json
import pytest
from PyICe.twi_instrument import twi_instrument
from PyICe.lab_interfaces import interface_factory
from PyICe.lab_core import ChannelValueException


fact = interface_factory()


@pytest.fixture()
def twi_inter():
    """Return twi inter result.

    Returns:
        Result value.
    """
    interface = fact.get_twi_dummy_interface()
    return interface


@pytest.fixture()
def twi_inst(twi_inter):
    """Return twi inst result.

    Args:
        twi_inter: Twi inter.

    Returns:
        Result value.
    """
    inst = twi_instrument(twi_inter)
    return inst


class TestTwiInstrument:
    """Tests for Twi Instrument."""

    def test_add_register(self, twi_inst):
        """Perform test add register operation.

        Args:
            twi_inst: Twi inst.
        """
        print('test)')
        twi_inst.add_register(name='ex_register',
                              addr7='0x70',
                              command_code=12,
                              size=8,
                              offset=16,
                              word_size=16,
                              is_readable=True,
                              is_writable=False)
        chan = twi_inst.get_channel('ex_register')
        assert chan.read() == 0
        with pytest.raises(Exception):
            twi_inst.add_register(name='new_reg',
                                  addr7='0x90',
                                  command_code=12,
                                  size=8,
                                  offset=16,
                                  word_size=16,
                                  is_readable=True,
                                  is_writable=False)
        twi_inst.add_register(name='single_bit',
                              addr7='0x70',
                              command_code=12,
                              size=1,
                              offset=16,
                              word_size=0,
                              is_readable=False,
                              is_writable=True)
        chan = twi_inst.get_channel('single_bit')
        # chan.write('Send') This should have worked? non in "Send"?

    def test_add_channel_ARA(self, twi_inst):
        """Perform test add channel ARA operation.

        Args:
            twi_inst: Twi inst.
        """
        twi_inst.add_channel_ARA('alert')
        chan = twi_inst.get_channel('alert')
        result = chan.read()
        assert type(result) is int  # bad practice to return random numbers


def _yoda_json(enums):
    """Return a one-register yoda JSON bridge map with a 2-bit MODE field.

    Args:
        enums: Dict of enum name to value for the MODE bitfield.

    Returns:
        List suitable for json.dump.
    """
    return [{
        'address': 0x10,
        'width': 8,
        'functionalgroups': ['ctrl'],
        'bitfields': {
            'MODE': {
                'slicewidth': 2,
                'regoffset': 0,
                'access': 'RW',
                'documentation': 'Operating mode',
                'enums': enums,
            },
        },
    }]


_IPXACT_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<ipxact:component xmlns:ipxact="http://www.accellera.org/XMLSchema/IPXACT/1685-2014">
  <ipxact:name>dev</ipxact:name>
  <ipxact:memoryMaps>
    <ipxact:memoryMap>
      <ipxact:name>map</ipxact:name>
      <ipxact:addressBlock>
        <ipxact:name>blk</ipxact:name>
        <ipxact:baseAddress>0x00</ipxact:baseAddress>
        <ipxact:range>256</ipxact:range>
        <ipxact:width>8</ipxact:width>
        <ipxact:register>
          <ipxact:name>CTRL</ipxact:name>
          <ipxact:addressOffset>0x00</ipxact:addressOffset>
          <ipxact:size>8</ipxact:size>
          <ipxact:access>read-write</ipxact:access>
          <ipxact:field>
            <ipxact:name>MODE</ipxact:name>
            <ipxact:bitOffset>0</ipxact:bitOffset>
            <ipxact:bitWidth>2</ipxact:bitWidth>
            <ipxact:access>read-write</ipxact:access>
            <ipxact:enumeratedValues>
              <ipxact:enumeratedValue><ipxact:name>A</ipxact:name><ipxact:value>0</ipxact:value></ipxact:enumeratedValue>
              <ipxact:enumeratedValue><ipxact:name>B</ipxact:name><ipxact:value>{value}</ipxact:value></ipxact:enumeratedValue>
            </ipxact:enumeratedValues>
          </ipxact:field>
        </ipxact:register>
      </ipxact:addressBlock>
    </ipxact:memoryMap>
  </ipxact:memoryMaps>
</ipxact:component>
"""


class TestPopulatePresetRange:
    """Out-of-range enums fail during populate_*, not on first write (issue #245)."""

    def test_yoda_json_in_range(self, twi_inst, tmp_path):
        """Accept an in-range enum from a yoda JSON map.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.json'
        path.write_text(json.dumps(_yoda_json({'A': 0, 'B': 3})))
        twi_inst.populate_from_yoda_json_bridge(str(path), 0x70)
        assert twi_inst.get_channel('MODE').get_presets_dict()['B'] == 3

    def test_yoda_json_out_of_range(self, twi_inst, tmp_path):
        """Reject an out-of-range enum from a yoda JSON map.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.json'
        path.write_text(json.dumps(_yoda_json({'A': 0, 'B': 4})))
        with pytest.raises(ChannelValueException, match='MODE'):
            twi_inst.populate_from_yoda_json_bridge(str(path), 0x70)

    def test_ipxact_in_range(self, twi_inst, tmp_path):
        """Accept an in-range enumeratedValue from an IP-XACT map.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.xml'
        path.write_text(_IPXACT_TEMPLATE.format(value=3))
        twi_inst.populate_from_ipxact(str(path), 0x70)
        assert twi_inst.get_channel('MODE').get_presets_dict()['B'] == 3

    def test_ipxact_out_of_range(self, twi_inst, tmp_path):
        """Reject an out-of-range enumeratedValue from an IP-XACT map.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.xml'
        path.write_text(_IPXACT_TEMPLATE.format(value=4))
        with pytest.raises(ChannelValueException, match='MODE'):
            twi_inst.populate_from_ipxact(str(path), 0x70)
