import pytest

# Legacy interactive test scripts that run module-level code (hardware, GUI).
# These are NOT pytest-compatible and must be excluded from collection.
collect_ignore = [
    "test_agilent_n3301.py",
    "test_caching.py",
    "test_calibrator.py",
    "test_digital_analog_IO.py",
    "test_email.py",
    "test_ena.py",
    "test_expect.py",
    "test_filter.py",
    "test_firmata.py",
    "test_Franken_oven.py",
    "test_gui.py",
    "test_hmp4040.py",
    "test_humanoid.py",
    "test_labcomm_packet_parser.py",
    "test_labcomm_serial_to_DC2038A_ltc4162.py",
    "test_labcomm_serial_to_DC2709A_ltc4021.py",
    "test_logger.py",
    "test_oscilloscope.py",
    "test_parameter_analyzer.py",
    "test_psa.py",
    "test_ramp_to.py",
    "test_remote_server_pinger.py",
    "test_remote_server_threaded_writer.py",
    "test_saleae.py",
    "test_scope_capture.py",
    "test_scpi_inst.py",
    "test_servo.py",
    "test_shift_register.py",
    "test_smu.py",
    "test_sqlite.py",
    "test_thermostream.py",
    "test_threshold_finder.py",
    "test_timer.py",
    "test_twi.py",
    "test_twi_instrument.py",
    "test_vector.py",
]


@pytest.fixture(autouse=True)
def reset_interface_factory_singleton():
    """Reset the interface_factory singleton guard before each test.

    Yields:
        Next value.
    """
    from PyICe.lab_interfaces import interface_factory
    interface_factory._instantiated = False
    yield
    interface_factory._instantiated = False


@pytest.fixture
def master_instance():
    """Create a fresh master instance.

    Yields:
        Next value.
    """
    from PyICe.lab_core import master
    m = master()
    yield m


@pytest.fixture
def master_with_dummies(master_instance):
    """Master with several dummy channels pre-loaded.

    Args:
        master_instance: Master instance.

    Returns:
        Result value.
    """
    m = master_instance
    m.add_channel_dummy('dummy_float')
    m.add_channel_dummy('dummy_int', integer_size=8)
    m.add_channel_dummy('dummy_plain')
    m['dummy_float'].write(3.14)
    m['dummy_int'].write(42)
    return m


@pytest.fixture
def master_with_virtuals(master_instance):
    """Master with virtual read/write channels.

    Args:
        master_instance: Master instance.

    Returns:
        Result value.
    """
    m = master_instance
    m.add_channel_virtual('virt_read', read_function=lambda: 99)
    m.add_channel_virtual('virt_write', write_function=lambda v: None)
    m.add_channel_virtual('virt_int_read', read_function=lambda: 7,
                          integer_size=4)
    return m


@pytest.fixture
def logger_instance(tmp_path, master_with_dummies):
    """Logger with temp SQLite database for isolated testing.

    Args:
        master_with_dummies: Master with dummies.
        tmp_path: Tmp path.

    Yields:
        Next value.
    """
    from PyICe.lab_core import logger
    db_path = str(tmp_path / "test_log.sqlite")
    lg = logger(master_with_dummies, database=db_path, use_threads=False)
    yield lg
    lg.stop()
