"""Tests for filter."""
from PyICe.sqlite_data import sqlite_data
from PyICe.interpolating_spline import interpolating_spline
from PyICe.float_distance import float_distance
from PyICe.column_formatter import column_formatter

db = sqlite_data(table_name='die_temp')
db.query("SELECT temp, die_temp_fmt, board_temp, temp_sense, temp_user_sense FROM die_temp")
arr = db.numpy_recarray(force_float_dtype=True)
splines = interpolating_spline(arr)

print(arr)
print()
report_data = []
report_data.append(
    ["Field Name", "x", "y", "interpolated y", "error distance"])
for row in arr:
    x_data = row[0]
    for col in arr.dtype.names[1:]:
        y_point = row[col]
        interp_point = getattr(splines, col)(x_data).item()
        interp_error = float_distance(y_point, interp_point)
        report_data.append([col, "{:03.1f}".format(x_data), "{:03.4f}".format(
            y_point), "{:03.4f}".format(interp_point), interp_error])
        assert abs(interp_error) <= 7  # allow for minor rounding errors
print(column_formatter(report_data, justification='right'))
