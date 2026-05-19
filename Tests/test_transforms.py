import sqlite3
import numpy as np
import pytest
from PyICe.lab_utils.scalar_transform import scalar_transform
from PyICe.lab_utils.vector_transform import vector_transform
from PyICe.lab_utils.sqlite_data import sqlite_data


def make_recarray():
    """Create a simple numpy recarray for testing."""
    return np.rec.fromarrays(
        [[1.0, 2.0, 3.0, 4.0, 5.0],
         [10.0, 20.0, 30.0, 40.0, 50.0],
         [100.0, 200.0, 300.0, 400.0, 500.0]],
        names=['x', 'y', 'z']
    )


class TestScalarTransform:

    def test_identity(self):
        arr = make_recarray()
        result = scalar_transform(arr, [None, None, None])
        np.testing.assert_array_equal(result.x, arr.x)
        np.testing.assert_array_equal(result.y, arr.y)

    def test_scale_single_column(self):
        arr = make_recarray()
        result = scalar_transform(arr, [None, lambda v: v * 2, None])
        np.testing.assert_array_equal(result.y, [20, 40, 60, 80, 100])
        np.testing.assert_array_equal(result.x, arr.x)

    def test_multiple_transforms(self):
        arr = make_recarray()
        result = scalar_transform(arr,
                                  [lambda v: v + 10,
                                   lambda v: v * 0.1,
                                   lambda v: v - 100])
        np.testing.assert_array_almost_equal(result.x, [11, 12, 13, 14, 15])
        np.testing.assert_array_almost_equal(result.y, [1, 2, 3, 4, 5])
        np.testing.assert_array_almost_equal(result.z, [0, 100, 200, 300, 400])

    def test_rename_columns(self):
        arr = make_recarray()
        result = scalar_transform(arr, [None, None, None],
                                  column_names=['time', 'voltage', 'current'])
        assert 'time' in result.dtype.names
        assert 'voltage' in result.dtype.names
        assert 'current' in result.dtype.names

    def test_partial_rename(self):
        arr = make_recarray()
        result = scalar_transform(arr, [None, None, None],
                                  column_names=['time', None, None])
        assert 'time' in result.dtype.names
        assert 'y' in result.dtype.names

    def test_preserves_length(self):
        arr = make_recarray()
        result = scalar_transform(arr, [None, lambda v: v ** 2, None])
        assert len(result) == len(arr)


class TestVectorTransform:

    def test_identity(self):
        arr = make_recarray()
        result = vector_transform(arr, [None, None, None])
        np.testing.assert_array_equal(result.x, arr.x)
        np.testing.assert_array_equal(result.y, arr.y)

    def test_scale_column(self):
        arr = make_recarray()
        result = vector_transform(arr, [None, lambda col: col * 3, None])
        np.testing.assert_array_equal(result.y, [30, 60, 90, 120, 150])

    def test_cumulative_sum(self):
        arr = make_recarray()
        result = vector_transform(arr,
                                  [None, np.cumsum, None])
        np.testing.assert_array_equal(result.y, [10, 30, 60, 100, 150])

    def test_rename_columns(self):
        arr = make_recarray()
        result = vector_transform(arr, [None, None, None],
                                  column_names=['a', 'b', 'c'])
        assert result.dtype.names == ('a', 'b', 'c')

    def test_mismatched_function_count_raises(self):
        arr = make_recarray()
        with pytest.raises(AssertionError):
            vector_transform(arr, [None, None])

    def test_diff_operation(self):
        arr = np.rec.fromarrays(
            [[0, 1, 2, 3], [0, 1, 4, 9]],
            names=['x', 'y']
        )
        result = vector_transform(arr,
                                  [lambda c: c[:-1], np.diff])
        np.testing.assert_array_equal(result.y, [1, 3, 5])
        assert len(result) == 3


@pytest.mark.database
class TestSqliteData:

    @pytest.fixture
    def populated_db(self, tmp_path):
        """Create a SQLite database with test data."""
        db_path = str(tmp_path / "test.sqlite")
        conn = sqlite3.connect(db_path)
        conn.execute("""CREATE TABLE measurements (
            rowid INTEGER PRIMARY KEY,
            datetime TEXT,
            voltage REAL,
            current REAL,
            status TEXT
        )""")
        conn.executemany(
            "INSERT INTO measurements (datetime, voltage, current, status) "
            "VALUES (?, ?, ?, ?)",
            [
                ('2024-01-01T00:00:00Z', 3.3, 0.001, 'ok'),
                ('2024-01-01T00:00:01Z', 3.2, 0.002, 'ok'),
                ('2024-01-01T00:00:02Z', 3.1, 0.003, 'warn'),
                ('2024-01-01T00:00:03Z', 3.0, 0.004, 'ok'),
                ('2024-01-01T00:00:04Z', 2.9, 0.005, 'fail'),
            ]
        )
        conn.commit()
        conn.close()
        return db_path

    def test_basic_query(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        rows = list(db)
        assert len(rows) == 5

    def test_row_access_by_name(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        row = db[0]
        assert row['voltage'] == 3.3
        assert row['current'] == 0.001

    def test_row_access_by_index(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        row = db[0]
        assert row['voltage'] == 3.3

    def test_length(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        assert len(db) == 5

    def test_slicing(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        rows = db[1:3]
        assert len(rows) == 2

    def test_custom_query(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        db.query("SELECT voltage FROM measurements WHERE current > ?", 0.003)
        rows = list(db)
        assert len(rows) == 2
        assert all(row['voltage'] <= 3.0 for row in rows)

    def test_get_column_names(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        names = db.get_column_names()
        assert 'voltage' in names
        assert 'current' in names
        assert 'status' in names

    def test_get_table_names(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        tables = db.get_table_names()
        assert 'measurements' in tables

    def test_get_distinct(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        statuses = db.get_distinct('status')
        assert 'ok' in statuses
        assert 'warn' in statuses
        assert 'fail' in statuses

    def test_context_manager(self, populated_db):
        with sqlite_data(table_name='measurements',
                         database_file=populated_db) as db:
            rows = list(db)
            assert len(rows) == 5

    def test_iteration(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        voltages = [row['voltage'] for row in db]
        assert voltages == [3.3, 3.2, 3.1, 3.0, 2.9]

    def test_numpy_recarray(self, populated_db):
        db = sqlite_data(table_name='measurements',
                         database_file=populated_db)
        db.query("SELECT voltage, current FROM measurements")
        arr = db.numpy_recarray(force_float_dtype=True)
        assert len(arr) == 5
        assert arr.voltage[0] == pytest.approx(3.3)
