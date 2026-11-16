"""Tests for PyICe.data_utils.instrument_recorder."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from PyICe.data_utils.instrument_recorder import instrument_recorder
from PyICe.lab_core import ChannelReadException, PartialReadException, master
from PyICe.visa_wrappers import visaWrapperException


def _make_mock_instrument(name='inst1', channel_names=None):
    """Create a mock instrument with the interface instrument_recorder expects.

    Uses a dynamic subclass so type(inst).__module__ and __qualname__ resolve
    to known values for the metadata table test.
    """
    iface = MagicMock()
    cls = type('MockInstrument', (), {
        '__module__': 'test_module',
        '_iface': iface,
        'get_name': lambda self: name,
        'get_all_channel_names': lambda self: channel_names or ['ch1'],
        'get_interface': lambda self: iface,
    })
    return cls()


def _make_mock_channel(name, attrs=None):
    """Create a mock channel object as yielded by iterating the logger."""
    ch = MagicMock()
    ch.get_name.return_value = name
    ch.get_attributes.return_value = attrs or {}
    return ch


class TestInstrumentRecorder:

    def test_raises_on_no_instruments(self):
        with pytest.raises(ValueError, match="at least one instrument"):
            instrument_recorder(table_name='t')

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_init_creates_logger_and_table(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst1 = _make_mock_instrument('a', ['ch_a'])
        inst2 = _make_mock_instrument('b', ['ch_b'])
        db = str(tmp_path / 'test.sqlite')

        recorder = instrument_recorder(inst1, inst2, db_filename=db, table_name='run1')

        mock_logger_cls.assert_called_once_with(database=db, use_threads=False)
        assert mock_logger.add.call_count == 2
        mock_logger.new_table.assert_called_once_with('run1')
        assert recorder.table_name == 'run1'

    @pytest.mark.database
    def test_metadata_table_written(self, tmp_path):
        db = str(tmp_path / 'meta.sqlite')
        inst = _make_mock_instrument('ena', ['freq', 'mag'])

        ch_freq = _make_mock_channel('freq', {
            'channel_type': 'x_data',
            'measurement': 'frequency',
            'channel_number': 1,
        })
        ch_mag = _make_mock_channel('mag', {
            'channel_type': 'y_data',
            'measurement': 'S21',
            'channel_number': 1,
        })

        with patch('PyICe.data_utils.instrument_recorder.lab_core.logger') as mock_logger_cls:
            mock_logger = MagicMock()
            mock_logger.__iter__ = MagicMock(return_value=iter([ch_freq, ch_mag]))
            mock_logger_cls.return_value = mock_logger

            instrument_recorder(inst, db_filename=db, table_name='bode')

        conn = sqlite3.connect(db)
        rows = conn.execute(
            'SELECT channel_name, channel_type, measurement, channel_number, instrument_class '
            'FROM [bode_channel_meta] ORDER BY channel_name'
        ).fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0] == ('freq', 'x_data', 'frequency', 1, 'test_module.MockInstrument')
        assert rows[1] == ('mag', 'y_data', 'S21', 1, 'test_module.MockInstrument')

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_log_delegates_to_logger(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.log()

        mock_logger.log.assert_called_once()

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_log_handles_partial_read_exception(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        cre = ChannelReadException("timeout", original_exception=IOError("timeout"))
        failures = {'ch_bad': cre}
        mock_logger.log.side_effect = PartialReadException({'ch_bad': cre}, failures)

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.log()

        captured = capsys.readouterr()
        assert "ch_bad" in captured.out
        assert "timeout" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_init_creates_comment_channel(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        instrument_recorder(inst, db_filename=db, table_name='t')

        mock_logger.master.add_channel_dummy.assert_called_once_with('comment')

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_log_writes_comment(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger
        comment_ch = mock_logger.master.add_channel_dummy.return_value

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.log(comment='sweep 1 done')

        comment_ch.write.assert_called_with('sweep 1 done')

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_log_default_comment_is_empty(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger
        comment_ch = mock_logger.master.add_channel_dummy.return_value

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        comment_ch.write.reset_mock()
        rec.log()

        comment_ch.write.assert_called_once_with('')

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_stop_closes_interfaces(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst1 = _make_mock_instrument('a')
        inst2 = _make_mock_instrument('b')
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst1, inst2, db_filename=db, table_name='t')

        rec.stop()

        mock_logger.stop.assert_called_once()
        inst1.get_interface().close.assert_called()
        inst2.get_interface().close.assert_called()

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_stop_handles_close_failure(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument('broken')
        inst._iface.close.side_effect = visaWrapperException("comm error")
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.stop()

        captured = capsys.readouterr()
        assert "broken" in captured.out
        assert "visaWrapperException" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_context_manager_calls_stop(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')

        with instrument_recorder(inst, db_filename=db, table_name='t') as rec:
            rec.log()

        mock_logger.stop.assert_called_once()

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_properties(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='my_table')

        assert rec.db_filename == db
        assert rec.table_name == 'my_table'

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_default_db_filename(self, mock_logger_cls, tmp_path, monkeypatch):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger
        monkeypatch.chdir(tmp_path)

        inst = _make_mock_instrument()
        rec = instrument_recorder(inst, table_name='t')

        assert rec.db_filename == 'data_record.sqlite'
        mock_logger_cls.assert_called_once_with(database='data_record.sqlite', use_threads=False)

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_table_name_prompts_when_none(self, mock_logger_cls, tmp_path, monkeypatch):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        responses = iter(['', '', 'my_run'])
        monkeypatch.setattr('builtins.input', lambda prompt: next(responses))

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name=None)

        assert rec.table_name == 'my_run'
        mock_logger.new_table.assert_called_once_with('my_run')

    @pytest.mark.database
    def test_metadata_multiple_instruments(self, tmp_path):
        """Channels from different instruments get their respective class paths."""
        db = str(tmp_path / 'multi.sqlite')
        inst_a = _make_mock_instrument('ena', ['freq', 'mag'])
        inst_b = _make_mock_instrument('scope', ['time', 'wfm'])
        # Give inst_b a different class identity
        type(inst_b).__module__ = 'scope_module'
        type(inst_b).__qualname__ = 'ScopeInstrument'

        ch_freq = _make_mock_channel('freq', {'channel_type': 'x_data'})
        ch_mag = _make_mock_channel('mag', {'channel_type': 'y_data'})
        ch_time = _make_mock_channel('time', {'channel_type': 'x_data'})
        ch_wfm = _make_mock_channel('wfm', {'channel_type': 'y_data'})

        with patch('PyICe.data_utils.instrument_recorder.lab_core.logger') as mock_logger_cls:
            mock_logger = MagicMock()
            mock_logger.__iter__ = MagicMock(
                return_value=iter([ch_freq, ch_mag, ch_time, ch_wfm]))
            mock_logger_cls.return_value = mock_logger

            instrument_recorder(inst_a, inst_b, db_filename=db, table_name='multi')

        conn = sqlite3.connect(db)
        rows = conn.execute(
            'SELECT channel_name, instrument_class FROM [multi_channel_meta] ORDER BY channel_name'
        ).fetchall()
        conn.close()

        assert ('freq', 'test_module.MockInstrument') in rows
        assert ('mag', 'test_module.MockInstrument') in rows
        assert ('time', 'scope_module.ScopeInstrument') in rows
        assert ('wfm', 'scope_module.ScopeInstrument') in rows

    @pytest.mark.database
    def test_metadata_missing_attributes(self, tmp_path):
        """Channels with no attributes get None values in metadata."""
        db = str(tmp_path / 'sparse.sqlite')
        inst = _make_mock_instrument('dev', ['bare_ch'])

        ch = _make_mock_channel('bare_ch', {})

        with patch('PyICe.data_utils.instrument_recorder.lab_core.logger') as mock_logger_cls:
            mock_logger = MagicMock()
            mock_logger.__iter__ = MagicMock(return_value=iter([ch]))
            mock_logger_cls.return_value = mock_logger

            instrument_recorder(inst, db_filename=db, table_name='sparse')

        conn = sqlite3.connect(db)
        row = conn.execute(
            'SELECT channel_type, measurement, channel_number FROM [sparse_channel_meta]'
        ).fetchone()
        conn.close()

        assert row == (None, None, None)

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_multiple_log_calls(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.log()
        rec.log()
        rec.log()

        assert mock_logger.log.call_count == 3

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_log_multiple_failures_reported(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        cre1 = ChannelReadException("timeout", original_exception=IOError("timeout"))
        cre2 = ChannelReadException("overload", original_exception=RuntimeError("overload"))
        failures = {'ch_a': cre1, 'ch_b': cre2}
        mock_logger.log.side_effect = PartialReadException(
            {'ch_a': cre1, 'ch_b': cre2}, failures)

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.log()

        captured = capsys.readouterr()
        assert "ch_a" in captured.out
        assert "ch_b" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_stop_handles_oserror(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument('flaky')
        inst._iface.close.side_effect = OSError("device disconnected")
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.stop()

        captured = capsys.readouterr()
        assert "flaky" in captured.out
        assert "OSError" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_stop_handles_attribute_error(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument('noif')
        inst._iface.close.side_effect = AttributeError("no interface")
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='t')

        rec.stop()

        captured = capsys.readouterr()
        assert "noif" in captured.out
        assert "AttributeError" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_stop_prints_summary(self, mock_logger_cls, tmp_path, capsys):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(inst, db_filename=db, table_name='results')

        rec.stop()

        captured = capsys.readouterr()
        assert db in captured.out
        assert "results" in captured.out

    @patch('PyICe.data_utils.instrument_recorder.lab_core.logger')
    def test_context_manager_does_not_suppress_exceptions(self, mock_logger_cls, tmp_path):
        mock_logger = MagicMock()
        mock_logger.__iter__ = MagicMock(return_value=iter([]))
        mock_logger_cls.return_value = mock_logger

        inst = _make_mock_instrument()
        db = str(tmp_path / 'test.sqlite')

        with pytest.raises(RuntimeError, match="user error"):
            with instrument_recorder(inst, db_filename=db, table_name='t'):
                raise RuntimeError("user error")

        mock_logger.stop.assert_called_once()


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


@pytest.mark.database
class TestIntegration:
    """Integration tests using real master/logger/SQLite (no mocks)."""

    def test_creates_database_table(self, tmp_path, dummy_instrument):
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(dummy_instrument, db_filename=db, table_name='run1')
        conn = sqlite3.connect(db)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        rec.stop()
        assert 'run1' in tables
        assert 'run1_channel_meta' in tables

    def test_logs_channel_values(self, tmp_path, dummy_instrument):
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(dummy_instrument, db_filename=db, table_name='data')
        rec.log()
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT voltage, current FROM [data]").fetchone()
        conn.close()
        rec.stop()
        assert float(row[0]) == pytest.approx(3.3)
        assert float(row[1]) == pytest.approx(0.1)

    def test_values_change_between_logs(self, tmp_path):
        m = master()
        m.add_channel_dummy('voltage')
        m['voltage'].write(1.0)
        db = str(tmp_path / 'change.sqlite')
        rec = instrument_recorder(m, db_filename=db, table_name='data')
        rec.log(comment='1V')
        m['voltage'].write(2.0)
        rec.log(comment='2V')
        m['voltage'].write(3.3)
        rec.log(comment='3.3V')
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT voltage, comment FROM [data] ORDER BY rowid").fetchall()
        conn.close()
        rec.stop()
        m.stop_threads()
        assert float(rows[0][0]) == pytest.approx(1.0)
        assert rows[0][1] == '1V'
        assert float(rows[1][0]) == pytest.approx(2.0)
        assert rows[1][1] == '2V'
        assert float(rows[2][0]) == pytest.approx(3.3)
        assert rows[2][1] == '3.3V'

    def test_comment_per_row(self, tmp_path, dummy_instrument):
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(dummy_instrument, db_filename=db, table_name='data')
        rec.log(comment='first')
        rec.log(comment='second')
        rec.log()
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT comment FROM [data] ORDER BY rowid").fetchall()
        conn.close()
        rec.stop()
        assert rows[0][0] == 'first'
        assert rows[1][0] == 'second'
        assert rows[2][0] == ''

    def test_multiple_instruments(self, tmp_path):
        m1 = master()
        m1.add_channel_dummy('voltage')
        m1['voltage'].write(5.0)
        m2 = master()
        m2.add_channel_dummy('temperature')
        m2['temperature'].write(25.0)
        db = str(tmp_path / 'multi.sqlite')
        rec = instrument_recorder(m1, m2, db_filename=db, table_name='data')
        rec.log()
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT voltage, temperature FROM [data]").fetchone()
        conn.close()
        rec.stop()
        m1.stop_threads()
        m2.stop_threads()
        assert float(row[0]) == pytest.approx(5.0)
        assert float(row[1]) == pytest.approx(25.0)

    def test_multiple_instruments_metadata(self, tmp_path):
        m1 = master()
        m1.add_channel_dummy('v_in')
        m2 = master()
        m2.add_channel_dummy('i_out')
        db = str(tmp_path / 'multi.sqlite')
        rec = instrument_recorder(m1, m2, db_filename=db, table_name='data')
        conn = sqlite3.connect(db)
        rows = conn.execute("SELECT channel_name FROM [data_channel_meta]").fetchall()
        names = [r[0] for r in rows]
        conn.close()
        rec.stop()
        m1.stop_threads()
        m2.stop_threads()
        assert 'v_in' in names
        assert 'i_out' in names

    def test_metadata_channel_attributes(self, tmp_path):
        m = master()
        ch = m.add_channel_dummy('trace_y')
        ch.set_attribute('channel_type', 'y_data')
        ch.set_attribute('measurement', 'S21 Log Magnitude')
        ch.set_attribute('channel_number', 2)
        db = str(tmp_path / 'attrs.sqlite')
        rec = instrument_recorder(m, db_filename=db, table_name='data')
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT channel_type, measurement, channel_number "
            "FROM [data_channel_meta] WHERE channel_name='trace_y'"
        ).fetchone()
        conn.close()
        rec.stop()
        m.stop_threads()
        assert row == ('y_data', 'S21 Log Magnitude', 2)

    def test_metadata_instrument_class_path(self, tmp_path):
        m = master()
        m.add_channel_dummy('ch1')
        db = str(tmp_path / 'cls.sqlite')
        rec = instrument_recorder(m, db_filename=db, table_name='data')
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT instrument_class FROM [data_channel_meta] WHERE channel_name='ch1'"
        ).fetchone()
        conn.close()
        rec.stop()
        m.stop_threads()
        assert row[0] is not None
        assert 'master' in row[0]

    def test_partial_read_does_not_crash(self, tmp_path):
        m = master()
        m.add_channel_dummy('good_ch')
        m['good_ch'].write(42)
        m.add_channel_virtual('bad_ch', read_function=lambda: 1/0)
        db = str(tmp_path / 'partial.sqlite')
        rec = instrument_recorder(m, db_filename=db, table_name='test')
        rec.log()
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM [test]").fetchone()[0]
        conn.close()
        rec.stop()
        m.stop_threads()
        assert count == 1

    def test_database_readable_after_stop(self, tmp_path, dummy_instrument):
        db = str(tmp_path / 'test.sqlite')
        rec = instrument_recorder(dummy_instrument, db_filename=db, table_name='run1')
        rec.log()
        rec.stop()
        conn = sqlite3.connect(db)
        count = conn.execute("SELECT COUNT(*) FROM [run1]").fetchone()[0]
        conn.close()
        assert count == 1
