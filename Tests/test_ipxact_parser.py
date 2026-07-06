"""Tests for IP-XACT parser and instrument integration."""
import os
import pytest
from PyICe.ipxact_parser import (
    IpxactParser, ipxact_access_to_rw, ipxact_modified_write_to_pyice,
    ipxact_to_pyice_json,
)
from PyICe.twi_instrument import twi_instrument
from PyICe.spi_instrument import spiInstrument
from PyICe.lab_interfaces import interface_factory
from PyICe import spi_interface

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
IPXACT_2014 = os.path.join(FIXTURE_DIR, "test_ipxact_2014.xml")


class TestIpxactParser:
    def test_parse_memory_maps(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        assert len(maps) == 1
        assert maps[0].name == "default_map"

    def test_parse_address_block(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        ab = maps[0].address_blocks[0]
        assert ab.name == "ctrl_regs"
        assert ab.base_address == 0
        assert ab.width == 8
        assert len(ab.registers) == 3

    def test_parse_register_fields(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        status_reg = maps[0].address_blocks[0].registers[0]
        assert status_reg.name == "STATUS"
        assert status_reg.address_offset == 0
        assert status_reg.size == 8
        assert status_reg.access == "read-only"
        assert len(status_reg.fields) == 3

    def test_parse_field_details(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        busy = maps[0].address_blocks[0].registers[0].fields[0]
        assert busy.name == "BUSY"
        assert busy.bit_offset == 0
        assert busy.bit_width == 1
        assert busy.reset_value == 0
        assert busy.access == "read-only"

    def test_parse_modified_write_value(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        error_fld = maps[0].address_blocks[0].registers[0].fields[1]
        assert error_fld.modified_write_value == "oneToClear"

    def test_parse_enumerated_values(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        mode_fld = maps[0].address_blocks[0].registers[0].fields[2]
        assert len(mode_fld.enumerated_values) == 3
        assert mode_fld.enumerated_values[0] == ("IDLE", 0, "Idle mode")
        assert mode_fld.enumerated_values[1] == ("RUN", 1, "Running")

    def test_register_without_fields(self):
        parser = IpxactParser(IPXACT_2014)
        maps = parser.parse()
        data_reg = maps[0].address_blocks[0].registers[2]
        assert data_reg.name == "DATA"
        assert data_reg.size == 16
        assert data_reg.fields == []

    def test_resolve_expression_hex(self):
        assert IpxactParser.resolve_expression("0xFF") == 255

    def test_resolve_expression_verilog_hex(self):
        assert IpxactParser.resolve_expression("'hFF") == 255

    def test_resolve_expression_decimal(self):
        assert IpxactParser.resolve_expression("42") == 42

    def test_resolve_expression_parameterized(self):
        with pytest.raises(NotImplementedError):
            IpxactParser.resolve_expression("id('some_param')")

    def test_resolve_expression_none(self):
        assert IpxactParser.resolve_expression(None) is None

    def test_detect_namespace_invalid(self):
        import xml.etree.ElementTree as ET
        root = ET.fromstring('<component/>')
        with pytest.raises(ValueError):
            IpxactParser._detect_namespace(root)


class TestIpxactAccessMapping:
    def test_read_write(self):
        assert ipxact_access_to_rw("read-write") == (True, True)

    def test_read_only(self):
        assert ipxact_access_to_rw("read-only") == (True, False)

    def test_write_only(self):
        assert ipxact_access_to_rw("write-only") == (False, True)

    def test_invalid(self):
        with pytest.raises(ValueError):
            ipxact_access_to_rw("invalid")

    def test_modified_write_w1c(self):
        assert ipxact_modified_write_to_pyice("oneToClear") == "W1C"

    def test_modified_write_unknown(self):
        assert ipxact_modified_write_to_pyice("unknownThing") is None


class TestTwiInstrumentIpxact:
    @pytest.fixture()
    def twi_inst(self):
        fact = interface_factory()
        interface = fact.get_twi_dummy_interface()
        return twi_instrument(interface)

    def test_populate_basic(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50)
        channel_names = [ch.get_name() for ch in twi_inst]
        assert "BUSY" in channel_names
        assert "ERROR" in channel_names
        assert "MODE" in channel_names
        assert "ENABLE" in channel_names
        assert "GAIN" in channel_names
        assert "DATA" in channel_names

    def test_populate_field_attributes(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50)
        channels = {ch.get_name(): ch for ch in twi_inst}
        busy = channels["BUSY"]
        assert busy.get_attribute("command_code") == 0
        assert busy.get_attribute("offset") == 0
        assert busy.get_attribute("default") == 0
        gain = channels["GAIN"]
        assert gain.get_attribute("command_code") == 1
        assert gain.get_attribute("offset") == 1
        assert gain.get_attribute("default") == 4

    def test_populate_data_register_no_fields(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50)
        channels = {ch.get_name(): ch for ch in twi_inst}
        data = channels["DATA"]
        assert data.get_attribute("command_code") == 0x10
        assert data.get_attribute("word_size") == 16

    def test_populate_presets(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50)
        channels = {ch.get_name(): ch for ch in twi_inst}
        mode = channels["MODE"]
        presets = mode.get_presets()
        assert "IDLE" in presets
        assert "RUN" in presets
        assert "SLEEP" in presets

    def test_populate_base_address(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50, base_address=0x80)
        channels = {ch.get_name(): ch for ch in twi_inst}
        assert channels["BUSY"].get_attribute("command_code") == 0x80

    def test_populate_channel_prefix_suffix(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50,
                                      channel_prefix="DEV_", channel_suffix="_ch")
        channel_names = [ch.get_name() for ch in twi_inst]
        assert "DEV_BUSY_ch" in channel_names

    def test_populate_memory_map_not_found(self, twi_inst):
        with pytest.raises(ValueError, match="Memory map"):
            twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50,
                                          memory_map_name="nonexistent")

    def test_populate_address_block_not_found(self, twi_inst):
        with pytest.raises(ValueError, match="Address block"):
            twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50,
                                          address_block_name="nonexistent")

    def test_populate_access_list_filter(self, twi_inst):
        twi_inst.populate_from_ipxact(IPXACT_2014, addr7=0x50,
                                      access_list=["read-write"])
        channel_names = [ch.get_name() for ch in twi_inst]
        assert "ENABLE" in channel_names
        assert "GAIN" in channel_names
        assert "BUSY" not in channel_names


class TestIpxactToPyiceJson:
    def test_basic_conversion(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        assert isinstance(result, list)
        assert len(result) == 3

    def test_register_structure(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        status = result[0]
        assert status["address"] == 0
        assert status["width"] == 8
        assert "BUSY" in status["bitfields"]
        assert "ERROR" in status["bitfields"]
        assert "MODE" in status["bitfields"]
        assert status["functionalgroups"] == ["ctrl_regs"]

    def test_bitfield_details(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        busy = result[0]["bitfields"]["BUSY"]
        assert busy["slicewidth"] == 1
        assert busy["regoffset"] == 0
        assert busy["access"] == "R"
        assert busy["write_side_effect"] == "None"
        assert busy["data_format"] == "Unsigned"
        assert busy["documentation"] == "Device busy flag"

    def test_write_side_effect_readonly_suppressed(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        error = result[0]["bitfields"]["ERROR"]
        assert error["write_side_effect"] == "None"

    def test_write_side_effect_rw(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        ctrl = result[1]
        enable = ctrl["bitfields"]["ENABLE"]
        assert enable["write_side_effect"] == "None"

    def test_enums(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        mode = result[0]["bitfields"]["MODE"]
        assert mode["enums"] == {"IDLE": 0, "RUN": 1, "SLEEP": 2}

    def test_rw_register(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        ctrl = result[1]
        assert ctrl["address"] == 1
        enable = ctrl["bitfields"]["ENABLE"]
        assert enable["access"] == "RW"

    def test_no_field_register(self):
        result = ipxact_to_pyice_json(IPXACT_2014)
        data = result[2]
        assert data["address"] == 0x10
        assert data["width"] == 16
        assert "DATA" in data["bitfields"]
        assert data["bitfields"]["DATA"]["slicewidth"] == 16

    def test_base_address(self):
        result = ipxact_to_pyice_json(IPXACT_2014, base_address=0x80)
        assert result[0]["address"] == 0x80

    def test_write_to_file(self, tmp_path):
        out = tmp_path / "output.json"
        result = ipxact_to_pyice_json(IPXACT_2014, output_file=str(out))
        import json
        with open(out) as f:
            loaded = json.load(f)
        assert loaded == result

    def test_round_trip_populate(self, tmp_path):
        out = tmp_path / "round_trip.json"
        ipxact_to_pyice_json(IPXACT_2014, output_file=str(out))
        fact = interface_factory()
        iface = fact.get_twi_dummy_interface()
        inst = twi_instrument(iface)
        inst.populate_from_yoda_json_bridge(str(out), i2c_addr7=0x50)
        channel_names = [ch.get_name() for ch in inst]
        assert "BUSY" in channel_names
        assert "ENABLE" in channel_names
        assert "MODE" in channel_names


class TestSpiInstrumentIpxact:
    @pytest.fixture()
    def spi_iface(self):
        class DummySpi(spi_interface.spiInterface):
            def __init__(self):
                spi_interface.spiInterface.__init__(self, CPOL=0, CPHA=0,
                                                   ss_ctrl=None, word_size=8)
            def _shift_data(self, data, clk_count):
                return 0
        return DummySpi()

    def test_from_ipxact_single_register(self, spi_iface):
        inst = spiInstrument.from_ipxact("test_spi", spi_iface, IPXACT_2014,
                                         register_name="CTRL")
        channel_names = [ch.get_name() for ch in inst]
        assert "ENABLE" in channel_names or "ENABLE_readback" in channel_names
        assert "GAIN" in channel_names or "GAIN_readback" in channel_names

    def test_from_ipxact_register_not_found(self, spi_iface):
        with pytest.raises(ValueError, match="Register"):
            spiInstrument.from_ipxact("test_spi", spi_iface, IPXACT_2014,
                                      register_name="NONEXISTENT")

    def test_from_ipxact_all_registers(self, spi_iface):
        inst = spiInstrument.from_ipxact("test_spi", spi_iface, IPXACT_2014)
        channel_names = [ch.get_name() for ch in inst]
        assert len(channel_names) > 0
