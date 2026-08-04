"""Tests for PyICe.data_utils.instrument_data_dump module."""
import sqlite3
import pytest
from PyICe.lab_core import master
from PyICe.data_utils.instrument_data_dump import instrument_data_dump


@pytest.fixture
def dummy_instrument():
    """Create a master with dummy channels simulating an instrument."""
    m = master()
    m.add_channel_dummy('voltage')
    m.add_channel_dummy('current')
    m['voltage'].write(3.3)
    m['current'].write(0.1)
    yield m
    m.stop_threads()


@pytest.fixture
def dump(tmp_path, dummy_instrument):
    """Create an instrument_data_dump with a temp database."""
    db_file = str(tmp_path / 'test.sqlite')
    d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='measurements')
    yield d
    d._logger.stop()


class TestInit:
    """Tests for instrument_data_dump initialization."""

    def test_creates_database(self, tmp_path, dummy_instrument):
        """Verify database file is created."""
        db_file = str(tmp_path / 'init_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='test')
        conn = sqlite3.connect(db_file)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        d._logger.stop()
        assert 'test' in tables

    def test_creates_metadata_table(self, tmp_path, dummy_instrument):
        """Verify metadata companion table is created."""
        db_file = str(tmp_path / 'meta_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='run1')
        conn = sqlite3.connect(db_file)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        d._logger.stop()
        assert 'run1_channel_meta' in tables

    def test_metadata_contains_channels(self, tmp_path, dummy_instrument):
        """Verify metadata table lists instrument channels."""
        db_file = str(tmp_path / 'channels_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        rows = conn.execute("SELECT channel_name FROM [data_channel_meta]").fetchall()
        channel_names = [r[0] for r in rows]
        conn.close()
        d._logger.stop()
        assert 'voltage' in channel_names
        assert 'current' in channel_names

    def test_comment_channel_in_metadata(self, tmp_path, dummy_instrument):
        """Verify comment channel appears in metadata."""
        db_file = str(tmp_path / 'comment_meta_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        rows = conn.execute("SELECT channel_name FROM [data_channel_meta]").fetchall()
        channel_names = [r[0] for r in rows]
        conn.close()
        d._logger.stop()
        assert 'comment' in channel_names

    def test_raises_on_no_instruments(self, tmp_path):
        """Verify assertion error with no instruments."""
        db_file = str(tmp_path / 'empty.sqlite')
        with pytest.raises(AssertionError):
            instrument_data_dump(db_filename=db_file, table_name='test')


class TestLog:
    """Tests for instrument_data_dump.log method."""

    def test_logs_one_row(self, dump, tmp_path):
        """Verify a single log call writes one row."""
        dump.log()
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        count = conn.execute("SELECT COUNT(*) FROM [measurements]").fetchone()[0]
        conn.close()
        assert count == 1

    def test_logs_multiple_rows(self, dump, tmp_path):
        """Verify multiple log calls write multiple rows."""
        dump.log()
        dump.log()
        dump.log()
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        count = conn.execute("SELECT COUNT(*) FROM [measurements]").fetchone()[0]
        conn.close()
        assert count == 3

    def test_logs_channel_values(self, dump, tmp_path):
        """Verify channel values are stored correctly."""
        dump.log()
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        row = conn.execute("SELECT voltage, current FROM [measurements]").fetchone()
        conn.close()
        assert float(row[0]) == pytest.approx(3.3)
        assert float(row[1]) == pytest.approx(0.1)

    def test_comment_default_empty(self, dump, tmp_path):
        """Verify default comment is empty string."""
        dump.log()
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        row = conn.execute("SELECT comment FROM [measurements]").fetchone()
        conn.close()
        assert row[0] == ''

    def test_comment_stored(self, dump, tmp_path):
        """Verify comment parameter is stored in the row."""
        dump.log(comment='bias changed to 5V')
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        row = conn.execute("SELECT comment FROM [measurements]").fetchone()
        conn.close()
        assert row[0] == 'bias changed to 5V'

    def test_comment_per_row(self, dump, tmp_path):
        """Verify each row gets its own comment."""
        dump.log(comment='first')
        dump.log(comment='second')
        dump.log()
        conn = sqlite3.connect(str(tmp_path / 'test.sqlite'))
        rows = conn.execute("SELECT comment FROM [measurements]").fetchall()
        conn.close()
        assert rows[0][0] == 'first'
        assert rows[1][0] == 'second'
        assert rows[2][0] == ''

    def test_partial_read_does_not_crash(self, tmp_path):
        """Verify a failing channel doesn't crash log()."""
        m = master()
        m.add_channel_dummy('good_ch')
        m['good_ch'].write(42)
        m.add_channel_virtual('bad_ch', read_function=lambda: 1/0)
        db_file = str(tmp_path / 'partial.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='test')
        d.log()
        conn = sqlite3.connect(db_file)
        count = conn.execute("SELECT COUNT(*) FROM [test]").fetchone()[0]
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert count == 1


class TestMetadata:
    """Tests for channel metadata table content."""

    def test_channel_type_stored(self, tmp_path):
        """Verify channel_type attribute is written to metadata."""
        m = master()
        ch = m.add_channel_dummy('trace_y')
        ch.set_attribute('channel_type', 'y_data')
        db_file = str(tmp_path / 'type_test.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT channel_type FROM [data_channel_meta] WHERE channel_name='trace_y'"
        ).fetchone()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert row[0] == 'y_data'

    def test_measurement_stored(self, tmp_path):
        """Verify measurement attribute is written to metadata."""
        m = master()
        ch = m.add_channel_dummy('s21')
        ch.set_attribute('measurement', 'S21 Log Magnitude')
        db_file = str(tmp_path / 'meas_test.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT measurement FROM [data_channel_meta] WHERE channel_name='s21'"
        ).fetchone()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert row[0] == 'S21 Log Magnitude'

    def test_channel_number_stored(self, tmp_path):
        """Verify channel_number attribute is written to metadata."""
        m = master()
        ch = m.add_channel_dummy('freq')
        ch.set_attribute('channel_number', 2)
        db_file = str(tmp_path / 'chnum_test.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT channel_number FROM [data_channel_meta] WHERE channel_name='freq'"
        ).fetchone()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert row[0] == 2

    def test_missing_attributes_are_null(self, tmp_path):
        """Verify channels without attributes get NULL in metadata."""
        m = master()
        m.add_channel_dummy('plain')
        db_file = str(tmp_path / 'null_test.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT channel_type, measurement, channel_number "
            "FROM [data_channel_meta] WHERE channel_name='plain'"
        ).fetchone()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert row[0] is None
        assert row[1] is None
        assert row[2] is None

    def test_instrument_class_stored(self, tmp_path):
        """Verify instrument_class is written to metadata."""
        m = master()
        m.add_channel_dummy('ch1')
        db_file = str(tmp_path / 'class_test.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        row = conn.execute(
            "SELECT instrument_class FROM [data_channel_meta] WHERE channel_name='ch1'"
        ).fetchone()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert row[0] is not None
        assert 'master' in row[0]


class TestStop:
    """Tests for instrument_data_dump.stop method."""

    def test_stop_prints_summary(self, tmp_path, dummy_instrument, capsys):
        """Verify stop prints the database filename and table name."""
        db_file = str(tmp_path / 'stop_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='run1')
        d.log()
        d.stop()
        captured = capsys.readouterr()
        assert 'stop_test.sqlite' in captured.out
        assert 'run1' in captured.out

    def test_stop_closes_database(self, tmp_path, dummy_instrument):
        """Verify stop closes the database without error."""
        db_file = str(tmp_path / 'close_test.sqlite')
        d = instrument_data_dump(dummy_instrument, db_filename=db_file, table_name='run1')
        d.log()
        d.stop()
        conn = sqlite3.connect(db_file)
        count = conn.execute("SELECT COUNT(*) FROM [run1]").fetchone()[0]
        conn.close()
        assert count == 1


class TestMultipleInstruments:
    """Tests for logging multiple instruments in one dump."""

    def test_two_instruments(self, tmp_path):
        """Verify channels from multiple instruments are logged together."""
        m1 = master()
        m1.add_channel_dummy('voltage')
        m1['voltage'].write(5.0)

        m2 = master()
        m2.add_channel_dummy('temperature')
        m2['temperature'].write(25.0)

        db_file = str(tmp_path / 'multi.sqlite')
        d = instrument_data_dump(m1, m2, db_filename=db_file, table_name='data')
        d.log()
        conn = sqlite3.connect(db_file)
        row = conn.execute("SELECT voltage, temperature FROM [data]").fetchone()
        conn.close()
        d._logger.stop()
        m1.stop_threads()
        m2.stop_threads()
        assert float(row[0]) == pytest.approx(5.0)
        assert float(row[1]) == pytest.approx(25.0)

    def test_two_instruments_metadata(self, tmp_path):
        """Verify metadata table contains channels from both instruments."""
        m1 = master()
        m1.add_channel_dummy('v_in')

        m2 = master()
        m2.add_channel_dummy('i_out')

        db_file = str(tmp_path / 'multi_meta.sqlite')
        d = instrument_data_dump(m1, m2, db_filename=db_file, table_name='data')
        conn = sqlite3.connect(db_file)
        rows = conn.execute("SELECT channel_name FROM [data_channel_meta]").fetchall()
        names = [r[0] for r in rows]
        conn.close()
        d._logger.stop()
        m1.stop_threads()
        m2.stop_threads()
        assert 'v_in' in names
        assert 'i_out' in names


class TestChangingValues:
    """Tests for logging changing channel values across rows."""

    def test_values_change_between_logs(self, tmp_path):
        """Verify each row captures the channel state at log time."""
        m = master()
        m.add_channel_dummy('voltage')
        m['voltage'].write(1.0)
        db_file = str(tmp_path / 'change.sqlite')
        d = instrument_data_dump(m, db_filename=db_file, table_name='data')
        d.log(comment='1V')
        m['voltage'].write(2.0)
        d.log(comment='2V')
        m['voltage'].write(3.3)
        d.log(comment='3.3V')
        conn = sqlite3.connect(db_file)
        rows = conn.execute("SELECT voltage, comment FROM [data] ORDER BY rowid").fetchall()
        conn.close()
        d._logger.stop()
        m.stop_threads()
        assert float(rows[0][0]) == pytest.approx(1.0)
        assert rows[0][1] == '1V'
        assert float(rows[1][0]) == pytest.approx(2.0)
        assert rows[1][1] == '2V'
        assert float(rows[2][0]) == pytest.approx(3.3)
        assert rows[2][1] == '3.3V'
