"""Tests for PyICe.data_utils.instrument_recorder."""
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from PyICe.data_utils.instrument_recorder import instrument_recorder
from PyICe.lab_core import ChannelReadException, PartialReadException
from PyICe.visa_wrappers import visaWrapperException


def _make_mock_instrument(name='inst1', channel_names=None):
    """Create a mock instrument with the interface instrument_recorder expects.

    Uses a dynamic subclass so type(inst).__module__ and __qualname__ resolve
    to known values for the metadata table test.
    """
    iface = MagicMock()
    cls = type('MockInstrument', (), {
        '__module__': 'test_module',
        'get_name': lambda self: name,
        'get_all_channel_names': lambda self: channel_names or ['ch1'],
        'get_interface': lambda self: iface,
    })
    inst = cls()
    inst._iface = iface
    return inst


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
