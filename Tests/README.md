# PyICe Unit Tests

## Prerequisites

Install dev dependencies into your virtual environment:

```
pip install -e ".[dev]"
```

Or install test packages directly:

```
pip install pytest pytest-mock pytest-cov
```

## Running Tests

From the project root:

```bash
# Run all tests
pytest

# Run a specific test file
pytest Tests/test_channel_master.py

# Run a specific test class or method
pytest Tests/test_register.py::TestRegisterSpecialAccess::test_W1C_sets_preset_and_attribute

# Run with verbose output
pytest -v

# Run only tests with a specific marker
pytest -m database
pytest -m threading

# Skip slow tests
pytest -m "not slow"

# Run with coverage report
pytest --cov=PyICe.lab_core --cov-report=term-missing
```

## Test Organization

| File | Covers |
|------|--------|
| `test_lab_core.py` | `channel`, `integer_channel`, `channel_group` |
| `test_channel_master.py` | `channel_master`, `master`, `results_ord_dict` |
| `test_register.py` | `register` (cached read, special access, RMW) |
| `test_logger_unit.py` | `logger` (tables, logging, callbacks, data channels) |
| `test_lab_utils_strings.py` | `eng_string`, `str2num`, `ordinalize`, `clean_unicode/ascii/sql` |
| `test_lab_utils_numeric.py` | `float_next/prior/distance`, `safe_divide`, `interpolator`, `ranges` |
| `test_lab_utils_more.py` | `swap_endian`, `twosComplement`, `bounded`, `isclose`, `parse_list`, `ordered_pair` |
| `test_virtual_instruments.py` | `dummy`, `expect`, `servo`, `accumulator`, `differencer` |
| `test_virtual_instruments_more.py` | `timer`, `integrator`, `differentiator`, `ramp_to` |
| `test_twi_spi_interface.py` | `i2c_dummy`, `shift_register`, TWI utilities (PEC, addr, byte ops) |
| `test_transforms.py` | `vector_transform`, `sqlite_data` (query, iteration, slicing, recarray) |
| `test_data_utils.py` | `units_conversions`, `EMI_char_levels`, `signal_generator`, `spectrum_analyzer` |
| `test_detrend_decimate.py` | `detrend_constant`, `detrend_linear`, `decimate` (scipy wrappers) |
| `test_delay_loop.py` | `delay_loop` (timing, count, strict mode, no-drift) |
| `test_threshold_finder_unit.py` | `threshold_finder` (binary, linear, polarity, hysteresis, channels) |
| `test_lab_instruments.py` | `TMP117`, `AD5259` — template for testing I2C drivers with `i2c_dummy` |
| `test_plugin_test_results.py` | `freeze`, `make_hash`, `none_min/max/abs`, `_test_result`, `_test_results_list`, `_evaluate_list` |
| `conftest.py` | Shared fixtures used across all test files |

## Configuration

Pytest is configured in `pyproject.toml` under `[tool.pytest.ini_options]`:

- **testpaths**: `["Tests"]` - pytest discovers tests here
- **markers**: `slow`, `threading`, `database` - use to categorize tests
- **addopts**: `--strict-markers -ra` - enforces declared markers, shows summary of non-passing tests

## Shared Fixtures (conftest.py)

| Fixture | Scope | Description |
|---------|-------|-------------|
| `reset_interface_factory_singleton` | function (autouse) | Resets the `interface_factory` singleton between tests |
| `master_instance` | function | Fresh `master()` with thread pool |
| `master_with_dummies` | function | Master + dummy channels (float, int8, plain) |
| `master_with_virtuals` | function | Master + virtual read/write/integer channels |
| `logger_instance` | function | Logger with temp SQLite database (`use_threads=False`) |

## Writing New Tests

### Adding tests for existing modules

1. Import the classes under test from `PyICe.lab_core` (or other modules).
2. Use fixtures from `conftest.py` where applicable.
3. Apply markers (`@pytest.mark.database`, etc.) for categorization.

### Testing hardware-dependent code without hardware

The key pattern is interface substitution at construction time:

```python
from PyICe.lab_core import master

def test_my_instrument():
    m = master()
    # Use built-in dummy interface instead of real hardware
    dummy_twi = m.get_twi_dummy_interface()

    # Pass dummy interface to instrument driver
    dut = MyInstrumentDriver("dut")
    dut.add_interface_twi(dummy_twi)
    m.add(dut)

    # Test channel logic without touching hardware
    assert dut.get_channel('some_register') is not None
```

Available mock interfaces:

- `m.get_twi_dummy_interface()` - In-memory I2C/SMBus
- `m.get_spi_dummy_interface()` - In-memory SPI
- `add_channel_dummy(name)` - Channel that stores/returns written values
- `add_channel_virtual(name, read_function=...)` - Channel backed by a Python function

For VISA instruments, use `unittest.mock.patch` on the interface's `write()`/`ask()` methods:

```python
from unittest.mock import MagicMock
from PyICe.lab_core import master

def test_scpi_instrument():
    m = master()
    mock_iface = MagicMock()
    mock_iface.ask.return_value = "3.300E+00"

    dut = MyScpiInstrument("dut")
    dut.add_interface_visa(mock_iface)
    m.add(dut)

    result = m.read_channel('voltage')
    mock_iface.ask.assert_called()
```

### Testing pure utility modules

Modules in `PyICe/lab_utils/` and `PyICe/data_utils/` are pure functions with no hardware dependencies. Test them directly:

```python
from PyICe.lab_utils.eng_string import eng_string

def test_eng_string_formatting():
    assert eng_string(0.001, fmt=':3.3g', si=True) == '1m'
```

### Key constraints

- **Singleton**: `interface_factory` allows only one instance. The autouse fixture in `conftest.py` handles this. If you instantiate `master()` or `logger()` in a test, it will work without extra setup.
- **Thread pool**: Each `channel_master` starts 24 daemon threads. They block idle and are cleaned up at process exit. This is acceptable for CI.
- **Logger databases**: Always use pytest's `tmp_path` fixture for SQLite files to avoid conflicts and ensure cleanup.
- **No hardware in CI**: Never import or instantiate real VISA/serial interfaces in unit tests. Use the dummy/mock alternatives above.

## Markers Reference

Declare new markers in `pyproject.toml` under `[tool.pytest.ini_options]` to avoid warnings:

```toml
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "threading: tests involving the thread pool",
    "database: tests creating SQLite databases",
]
```

## CI/CD Integration

A minimal GitHub Actions workflow:

```yaml
- name: Run tests
  run: |
    pip install -e ".[dev]"
    pytest --cov=PyICe --cov-report=xml -q
```

The test suite runs in under 2 seconds with no external dependencies.
