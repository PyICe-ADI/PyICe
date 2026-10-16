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


def _yoda_json(enums, data_format=None):
    """Return a one-register yoda JSON bridge map with a 2-bit MODE field.

    Args:
        enums: Dict of enum name to value for the MODE bitfield.
        data_format: Optional 'Signed' or 'Unsigned' data_format key.

    Returns:
        List suitable for json.dump.
    """
    regmap = [{
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
    if data_format is not None:
        regmap[0]['bitfields']['MODE']['data_format'] = data_format
    return regmap


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


class TestPopulateSignedPresets:
    """Signed enums are encoded in two's complement during populate_* (issue #247)."""

    def test_yoda_json_signed_negative_enum(self, twi_inst, tmp_path):
        """Encode negative enums on a Signed yoda field.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.json'
        path.write_text(json.dumps(_yoda_json({'M2': -2, 'M1': -1, 'P1': 1}, 'Signed')))
        twi_inst.populate_from_yoda_json_bridge(str(path), 0x70)
        assert twi_inst.get_channel('MODE').get_presets_dict() == {'M2': 2, 'M1': 3, 'P1': 1}

    def test_yoda_json_signed_below_range(self, twi_inst, tmp_path):
        """Reject a signed enum below the field's signed range.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.json'
        path.write_text(json.dumps(_yoda_json({'LOW': -3}, 'Signed')))
        with pytest.raises(ChannelValueException, match='MODE'):
            twi_inst.populate_from_yoda_json_bridge(str(path), 0x70)

    @pytest.mark.parametrize('data_format', [None, 'Unsigned'])
    def test_yoda_json_unsigned_negative_enum(self, twi_inst, tmp_path, data_format):
        """Reject a negative enum on an unsigned or untyped yoda field.

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
            data_format: data_format key value, or None for the old schema.
        """
        path = tmp_path / 'map.json'
        path.write_text(json.dumps(_yoda_json({'M1': -1}, data_format)))
        with pytest.raises(ChannelValueException, match='MODE'):
            twi_inst.populate_from_yoda_json_bridge(str(path), 0x70)

    def test_ipxact_negative_enum(self, twi_inst, tmp_path):
        """Reject a negative IP-XACT enumeratedValue (IP-XACT fields are unsigned).

        Args:
            twi_inst: Twi inst.
            tmp_path: Tmp path.
        """
        path = tmp_path / 'map.xml'
        path.write_text(_IPXACT_TEMPLATE.format(value=-1))
        with pytest.raises(ChannelValueException, match='MODE'):
            twi_inst.populate_from_ipxact(str(path), 0x70)


class TestTwiReplaceValidation:
    """Tests for twi_instrument._replace bitfield bounds validation (issue #246)."""

    def test_bitfield_at_register_boundary(self, twi_inst):
        """Accept a bitfield ending exactly at the register MSB.

        Args:
            twi_inst: Twi inst.
        """
        assert twi_inst._replace(bf_data=0xF, bf_size=4, bf_offset=4,  # pylint: disable=protected-access
                                 reg_data=0x00, reg_size=8) == 0xF0

    @pytest.mark.parametrize('bf_size, bf_offset', [(4, 5), (9, 0)])
    def test_bitfield_exceeding_register_rejected(self, twi_inst, bf_size, bf_offset):
        """Reject a bitfield that extends past the register width.

        Args:
            twi_inst: Twi inst.
            bf_size: Bitfield size.
            bf_offset: Bitfield offset.
        """
        with pytest.raises(ValueError, match='exceeds 8-bit register'):
            twi_inst._replace(bf_data=0, bf_size=bf_size, bf_offset=bf_offset,  # pylint: disable=protected-access
                              reg_data=0, reg_size=8)
