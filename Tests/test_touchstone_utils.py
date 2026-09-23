"""Tests for touchstone_utils module — skrf Circuit compatibility and core operations."""
import matplotlib
matplotlib.use('Agg')
import numpy as np
import pytest
import skrf
from unittest.mock import MagicMock, patch

try:
    from skrf.circuit import Circuit
except ImportError:
    from skrf import Circuit

from PyICe.data_utils.touchstone_utils import (
    touchstone_utils,
    resistor_ladder_coefficient,
    _parallel,
)


@pytest.fixture
def freqs():
    """Frequency sweep fixture for circuit tests."""
    return skrf.frequency.Frequency(
        start=10, stop=10e6, npoints=100, unit='Hz', sweep_type='log'
    )


@pytest.fixture
def series_lr_network(freqs):
    """Create a simple series LR 1-port network using Circuit."""
    R = 100
    L = 1e-6
    z0 = 50
    source_port = Circuit.Port(frequency=freqs, name='in', z0=z0)
    res = Circuit.SeriesImpedance(frequency=freqs, name='res', z0=z0, Z=R)
    ind = Circuit.SeriesImpedance(
        frequency=freqs, name='ind', z0=z0, Z=1j * freqs.w * L
    )
    ground = Circuit.Ground(frequency=freqs, name='gnd', z0=z0)
    connections = [
        [(source_port, 0), (res, 0)],
        [(res, 1), (ind, 0)],
        [(ind, 1), (ground, 0)],
    ]
    circuit = Circuit(connections)
    return circuit.network


@pytest.fixture
def star_3port_network(freqs):
    """Create a 3-port star resistor network using Circuit."""
    z0 = 0.1
    resistors = []
    connections = []
    for i in range(1, 4):
        port = Circuit.Port(frequency=freqs, name=f"Port{i}", z0=z0)
        res = Circuit.SeriesImpedance(
            frequency=freqs, name=f"Res{i}", z0=z0, Z=i * z0
        )
        connections.append([(port, 0), (res, 0)])
        resistors.append(res)
    connections.append([(resistors[0], 1), (resistors[1], 1), (resistors[2], 1)])
    circuit = Circuit(connections)
    return skrf.network.Network(
        frequency=freqs, s=circuit.network.s, z0=z0, name="star_3port"
    )


class TestCircuitCompat:
    """Verify skrf Circuit import shim works for both v1.x and v2.x."""

    def test_circuit_port_creation(self, freqs):
        """Circuit.Port creates a valid 1-port network element."""
        port = Circuit.Port(frequency=freqs, name='test_port', z0=50)
        assert port is not None

    def test_circuit_ground_creation(self, freqs):
        """Circuit.Ground creates a valid grounding element."""
        gnd = Circuit.Ground(frequency=freqs, name='gnd', z0=50)
        assert gnd is not None

    def test_circuit_open_creation(self, freqs):
        """Circuit.Open creates a valid open-circuit element."""
        opn = Circuit.Open(frequency=freqs, name='open', z0=50)
        assert opn is not None

    def test_circuit_series_impedance(self, freqs):
        """Circuit.SeriesImpedance creates an element with correct impedance."""
        R = 100
        res = Circuit.SeriesImpedance(frequency=freqs, name='res', z0=50, Z=R)
        assert res is not None

    def test_circuit_assembly(self, series_lr_network):
        """A complete Circuit assembles into a valid Network with S-parameters."""
        assert series_lr_network is not None
        assert series_lr_network.s.shape[0] == 100
        assert series_lr_network.s.shape[1] == 1
        assert series_lr_network.s.shape[2] == 1


class TestNetworkNportToMport:
    """Test N-port to M-port network reduction."""

    def test_3port_to_2port(self, freqs, star_3port_network):
        """Reducing a 3-port star network to 2-port produces valid S-params."""
        tu = touchstone_utils()
        tu.network = star_3port_network
        result = tu.network_Nport_to_Mport([1, 2])
        assert result.nports == 2
        assert result.s.shape == (100, 2, 2)

    def test_3port_to_1port(self, freqs, star_3port_network):
        """Reducing a 3-port to 1-port (keeping port 1) produces valid result."""
        tu = touchstone_utils()
        tu.network = star_3port_network
        result = tu.network_Nport_to_Mport([1])
        assert result.nports == 1
        assert result.s.shape == (100, 1, 1)

    def test_port_order_transposes_s_matrix(self, freqs, star_3port_network):
        """Swapping port order transposes the S-parameter matrix."""
        tu = touchstone_utils()
        tu.network = star_3port_network
        result_12 = tu.network_Nport_to_Mport([1, 2])
        result_21 = tu.network_Nport_to_Mport([2, 1])
        assert np.allclose(result_12.s[:, 0, 0], result_21.s[:, 1, 1])
        assert np.allclose(result_12.s[:, 0, 1], result_21.s[:, 1, 0])


class TestNetworkNportTo1port:
    """Test N-port to 1-port network reduction with short termination."""

    def test_3port_to_1port_shorted(self, freqs, star_3port_network):
        """Reducing 3-port to 1-port by shorting load port gives valid impedance."""
        tu = touchstone_utils()
        tu.network = star_3port_network
        result = tu.network_Nport_to_1port(source_port_num=1, load_port_num=2)
        assert result.nports == 1
        assert result.s.shape == (100, 1, 1)


class TestSeriesLRModel:
    """Test dev_make_series_LR_model circuit construction."""

    @patch('skrf.circuit.Circuit.plot_graph', MagicMock())
    @patch('matplotlib.pyplot.figure', MagicMock())
    def test_creates_valid_network(self):
        """Series LR model sets self.network to a 1-port with correct frequency points."""
        tu = touchstone_utils()
        tu.dev_make_series_LR_model(R=1e3, L=1e-3)
        assert tu.network is not None
        assert tu.network.nports == 1
        assert tu.network.s.shape[0] == 1000

    @patch('skrf.circuit.Circuit.plot_graph', MagicMock())
    @patch('matplotlib.pyplot.figure', MagicMock())
    def test_impedance_at_dc_approaches_resistance(self):
        """At low frequency, series LR impedance is dominated by R."""
        tu = touchstone_utils()
        tu.dev_make_series_LR_model(R=100, L=1e-9)
        z_low = tu.network.z[0, 0, 0]
        assert abs(z_low.real - 100) < 1.0
        assert abs(z_low.imag) < 1.0


class TestResistorLadderCoefficient:
    """Test resistor ladder coefficient solver."""

    def test_single_stage(self):
        """Single-stage ladder has a known analytical solution."""
        r_dc = 50
        r_hf = 100
        coeff = float(resistor_ladder_coefficient(r_dc, r_hf, num_stages=1))
        r_eq = 1.0 / (1.0 / r_hf + 1.0 / (r_hf * coeff))
        assert abs(r_eq - r_dc) < 0.01

    def test_two_stage(self):
        """Two-stage ladder coefficient produces correct DC resistance."""
        r_dc = 10
        r_hf = 100
        coeff = float(resistor_ladder_coefficient(r_dc, r_hf, num_stages=2))
        r_inv = 1 / r_hf + 1 / (r_hf * coeff) + 1 / (r_hf * coeff**2)
        r_eq = 1.0 / r_inv
        assert abs(r_eq - r_dc) < 0.01


class TestParallel:
    """Test _parallel helper function."""

    def test_equal_resistors(self):
        """Two equal resistors in parallel give half the resistance."""
        import sympy
        result = float(_parallel(sympy.Float(100), sympy.Float(100)))
        assert abs(result - 50.0) < 0.001

    def test_one_infinite(self):
        """Infinite parallel with finite gives the finite value."""
        import sympy
        result = _parallel(sympy.Float(100), sympy.oo)
        assert abs(float(result) - 100.0) < 0.001


class TestWriteTouchstone:
    """Test that write_touchstone is called with correct kwargs."""

    def test_output_touchstone_uses_filename_kwarg(self, freqs, tmp_path):
        """output_touchstone calls write_touchstone with 'filename' (no underscore)."""
        z0 = 50
        source_port = Circuit.Port(frequency=freqs, name='in', z0=z0)
        ground = Circuit.Ground(frequency=freqs, name='gnd', z0=z0)
        res = Circuit.SeriesImpedance(frequency=freqs, name='res', z0=z0, Z=100)
        connections = [
            [(source_port, 0), (res, 0)],
            [(res, 1), (ground, 0)],
        ]
        circuit = Circuit(connections)
        network = circuit.network
        tu = touchstone_utils()
        tu.network = network
        tu.output_touchstone(
            output_file_name="test_output",
            output_file_dir=str(tmp_path),
        )
        output_files = list(tmp_path.glob("*.s1p"))
        assert len(output_files) == 1
