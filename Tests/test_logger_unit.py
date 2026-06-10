"""Tests for logger unit."""
import os
import sqlite3
import pytest
from PyICe.lab_core import logger, master, PartialReadException, ChannelReadException


@pytest.fixture
def simple_logger(tmp_path):
    """Logger with a few dummy channels and temp database.

    Args:
        tmp_path: Tmp path.

    Yields:
        Next value.
    """
    m = master()
    m.add_channel_dummy('voltage')
    m.add_channel_dummy('current')
    m['voltage'].write(3.3)
    m['current'].write(0.001)
    db_path = str(tmp_path / "test.sqlite")
    lg = logger(m, database=db_path, use_threads=False)
    yield lg
    lg.stop()
    m.stop_threads()


@pytest.mark.database
class TestLoggerInit:
    """Tests for Logger Init."""

    def test_creates_database_file(self, tmp_path):
        """Perform test creates database file operation.

        Args:
            tmp_path: Tmp path.
        """
        m = master()
        m.add_channel_dummy('ch1')
        db_path = str(tmp_path / "init_test.sqlite")
        lg = logger(m, database=db_path, use_threads=False)
        assert os.path.exists(db_path)
        lg.stop()
        m.stop_threads()

    def test_context_manager(self, tmp_path):
        """Perform test context manager operation.

        Args:
            tmp_path: Tmp path.
        """
        m = master()
        m.add_channel_dummy('ch1')
        db_path = str(tmp_path / "ctx_test.sqlite")
        with logger(m, database=db_path, use_threads=False) as lg:
            assert lg is not None
        assert os.path.exists(db_path)
        m.stop_threads()

    def test_merges_channel_group(self, simple_logger):
        """Perform test merges channel group operation.

        Args:
            simple_logger: Simple logger.
        """
        names = simple_logger.get_all_channel_names()
        assert 'voltage' in names
        assert 'current' in names

    def test_removes_non_readable(self, tmp_path):
        """Perform test removes non readable operation.

        Args:
            tmp_path: Tmp path.
        """
        m = master()
        ch = m.add_channel_virtual('non_readable',
                                   write_function=lambda v: None)
        ch.set_read_access(False)
        m.add_channel_dummy('readable')
        db_path = str(tmp_path / "readable_test.sqlite")
        lg = logger(m, database=db_path, use_threads=False)
        names = lg.get_all_channel_names()
        assert 'readable' in names
        assert 'non_readable' not in names
        lg.stop()
        m.stop_threads()


@pytest.mark.database
class TestLoggerTableManagement:
    """Tests for Logger Table Management."""

    def test_new_table(self, simple_logger):
        """Perform test new table operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('test_table')
        assert simple_logger.get_table_name() == 'test_table'

    def test_new_table_duplicate_raises(self, simple_logger):
        """Perform test new table duplicate raises operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('dup_table')
        with pytest.raises(Exception):
            simple_logger.new_table('dup_table', replace_table=False)

    def test_new_table_replace(self, simple_logger):
        """Perform test new table replace operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('rep_table')
        simple_logger.log()
        simple_logger.new_table('rep_table', replace_table=True)

    def test_append_table(self, simple_logger):
        """Perform test append table operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('append_test')
        simple_logger.log()
        simple_logger.append_table('append_test')
        simple_logger.log()

    def test_switch_table(self, simple_logger):
        """Perform test switch table operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('table_a')
        simple_logger.new_table('table_b')
        simple_logger.switch_table('table_a')
        assert simple_logger.get_table_name() == 'table_a'


@pytest.mark.database
class TestLoggerLogging:
    """Tests for Logger Logging."""

    def test_log_returns_dict(self, simple_logger):
        """Perform test log returns dict operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('log_test')
        data = simple_logger.log()
        assert isinstance(data, dict)
        assert 'voltage' in data
        assert 'current' in data

    def test_log_values_correct(self, simple_logger):
        """Perform test log values correct operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('val_test')
        data = simple_logger.log()
        assert data['voltage'] == 3.3
        assert data['current'] == 0.001

    def test_log_adds_datetime(self, simple_logger):
        """Perform test log adds datetime operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('dt_test')
        data = simple_logger.log()
        assert 'datetime' in data

    def test_log_stores_to_database(self, simple_logger):
        """Perform test log stores to database operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('store_test')
        simple_logger.log()
        simple_logger.flush()
        conn = sqlite3.connect(simple_logger.get_database())
        cur = conn.execute("SELECT voltage, current FROM store_test")
        row = cur.fetchone()
        conn.close()
        assert row[0] == 3.3
        assert row[1] == 0.001

    def test_log_exclusions(self, simple_logger):
        """Perform test log exclusions operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('excl_test')
        data = simple_logger.log(exclusions=['voltage'])
        assert 'voltage' not in data
        assert 'current' in data

    def test_log_if_changed_skips_duplicate(self, simple_logger):
        """Perform test log if changed skips duplicate operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('change_test')
        first = simple_logger.log()
        assert first is not None
        second = simple_logger.log_if_changed()
        assert second is None

    def test_log_if_changed_logs_different(self, simple_logger):
        """Perform test log if changed logs different operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('diff_test')
        simple_logger.log()
        simple_logger.master['voltage'].write(5.0)
        result = simple_logger.log_if_changed()
        assert result is not None
        assert result['voltage'] == 5.0

    def test_log_callback(self, simple_logger):
        """Perform test log callback operation.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('cb_test')
        received = []
        simple_logger.add_log_callback(lambda data: received.append(data))
        simple_logger.log()
        assert len(received) == 1
        assert 'voltage' in received[0]

    def test_remove_log_callback(self, simple_logger):
        """Return test remove log callback result.

        Args:
            simple_logger: Simple logger.
        """
        simple_logger.new_table('rmcb_test')
        received = []

        def cb(data):
            """Return cb result.

            Args:
                data: Data to write.

            Returns:
                Result value.
            """
            return received.append(data)

        simple_logger.add_log_callback(cb)
        simple_logger.log()
        simple_logger.remove_log_callback(cb)
        simple_logger.log()
        assert len(received) == 1


@pytest.mark.database
class TestLoggerDataChannels:
    """Tests for Logger Data Channels."""

    def test_add_data_channels_and_log_data(self, tmp_path):
        """Perform test add data channels and log data operation.

        Args:
            tmp_path: Tmp path.
        """
        lg = logger(database=str(tmp_path / "data_ch.sqlite"),
                    use_threads=False)
        sample = {'temp': 25.0, 'pressure': 101.3}
        lg.add_data_channels(sample)
        lg.new_table('manual_data')
        result = lg.log_data({'temp': 25.0, 'pressure': 101.3})
        assert result is not None
        assert result['temp'] == 25.0
        lg.stop()

    def test_log_many(self, tmp_path):
        """Perform test log many operation.

        Args:
            tmp_path: Tmp path.
        """
        lg = logger(database=str(tmp_path / "many.sqlite"),
                    use_threads=False)
        sample = {'x': 0, 'y': 0}
        lg.add_data_channels(sample)
        lg.new_table('batch')
        rows = [{'x': i, 'y': i * 2} for i in range(10)]
        lg.log_many(rows)
        lg.flush()
        conn = sqlite3.connect(str(tmp_path / "many.sqlite"))
        cur = conn.execute("SELECT count(*) FROM batch")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 10
        lg.stop()

@pytest.mark.database
class TestLoggerPartialRead:
    """Tests that logger stores partial results before re-raising PartialReadException."""

    @pytest.fixture
    def partial_logger(self, tmp_path):
        """Logger with one good and one failing channel.

        Args:
            tmp_path: Tmp path.

        Yields:
            Next value.
        """
        m = master()
        m.add_channel_dummy('good_ch').write(42.0)
        m.add_channel_virtual('bad_ch',
                              read_function=lambda: (_ for _ in ()).throw(
                                  RuntimeError("comm failure")))
        db_path = str(tmp_path / "partial.sqlite")
        lg = logger(m, database=db_path, use_threads=False)
        lg.new_table('test_partial', replace_table=True)
        yield lg, db_path, m
        lg.stop()
        m.stop_threads()

    def test_log_stores_partial_row_before_raising(self, partial_logger):
        """logger.log() commits partial results to DB then raises PartialReadException."""
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException):
            lg.log()
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT good_ch, bad_ch FROM test_partial").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 42.0
        assert row[1].startswith('READ_ERROR:RuntimeError:comm failure')

    def test_log_partial_row_has_datetime(self, partial_logger):
        """Partial row includes datetime metadata column."""
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException):
            lg.log()
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT datetime FROM test_partial").fetchone()
        conn.close()
        assert row[0] is not None
        assert 'T' in row[0]

    def test_log_updates_previously_logged_data(self, partial_logger):
        """_previously_logged_data is set even on partial failure."""
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException):
            lg.log()
        assert lg._previously_logged_data is not None
        assert lg._previously_logged_data['good_ch'] == 42.0
        assert isinstance(lg._previously_logged_data['bad_ch'], ChannelReadException)

    def test_log_if_changed_stores_partial_row(self, partial_logger):
        """log_if_changed() also commits partial results before raising."""
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException):
            lg.log_if_changed()
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT good_ch, bad_ch FROM test_partial").fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 42.0

    def test_exception_carries_enriched_results(self, partial_logger):
        """PartialReadException.results includes rowid and datetime."""
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException) as exc_info:
            lg.log()
        results = exc_info.value.results
        assert 'rowid' in results
        assert 'datetime' in results
        assert results['good_ch'] == 42.0

    def test_all_good_channels_no_exception(self, tmp_path):
        """No PartialReadException when all channels succeed."""
        m = master()
        m.add_channel_dummy('a').write(1.0)
        m.add_channel_dummy('b').write(2.0)
        db_path = str(tmp_path / "allgood.sqlite")
        lg = logger(m, database=db_path, use_threads=False)
        lg.new_table('t', replace_table=True)
        data = lg.log()
        assert data['a'] == 1.0
        assert data['b'] == 2.0
        lg.stop()
        m.stop_threads()

    def test_sqlite_data_deserializes_channel_failure(self, partial_logger):
        """sqlite_data returns ChannelFailure namedtuple for failed channels."""
        from PyICe.lab_utils.sqlite_data import sqlite_data, ChannelFailure
        lg, db_path, m = partial_logger
        with pytest.raises(PartialReadException):
            lg.log()
        lg.stop()
        sd = sqlite_data(table_name='test_partial', database_file=db_path)
        row = sd[0]
        assert row['good_ch'] == 42.0
        failure = row['bad_ch']
        assert isinstance(failure, ChannelFailure)
        assert failure.exception_type == 'RuntimeError'
        assert failure.message == 'comm failure'
