"""Comprehensive tests for PyICe.LTC_plot module."""
import csv
import re
import numpy as np
import pytest
from PyICe.LTC_plot import (
    plot,
    scope_plot,
    Page,
    Multipage_pdf,
    color_gen,
    CMYK_to_fracRGB,
    fracRGB_to_CMYK,
    webRGB_to_fracRGB,
    webRGB_to_RGB,
    RGB_to_webRGB,
    fracRGB_to_RGB,
    RGB_to_fracRGB,
    data_from_file,
    MARCOM_COLORS,
    MARCOM_COLORSfracRGB,
    LT_RED_1,
    LT_BLUE_1,
    LT_BLACK,
    DELTA,
    DEGC,
    DEG,
)


@pytest.fixture
def basic_plot():
    """Create a minimal plot with fixed numeric limits."""
    return plot(
        plot_title="Test Plot",
        plot_name="TP01",
        xaxis_label="VOLTAGE (V)",
        yaxis_label="CURRENT (mA)",
        xlims=(-10, 10),
        ylims=(0, 100),
        xminor=2,
        xdivs=5,
        yminor=2,
        ydivs=10,
        logx=False,
        logy=False,
    )


@pytest.fixture
def autoscale_plot():
    """Create a plot with autoscaling on both axes."""
    return plot(
        plot_title="Autoscale Plot",
        plot_name="AP01",
        xaxis_label="TIME (s)",
        yaxis_label="AMPLITUDE (V)",
        xlims=None,
        ylims="auto",
        xminor=0,
        xdivs=10,
        yminor=0,
        ydivs=8,
        logx=False,
        logy=False,
    )


@pytest.fixture
def scope():
    """Create a scope_plot with fixed limits."""
    return scope_plot(
        plot_title="Scope Capture",
        plot_name="SC01",
        xaxis_label="500ns/DIV",
        xlims=(0, 5e-6),
        ylims=(0, 5),
    )


@pytest.fixture
def populated_plot(basic_plot):
    """Create a plot with traces, note, and legend already added."""
    basic_plot.add_trace(
        axis=1,
        data=[(x, x * 10) for x in range(-10, 11)],
        color=LT_RED_1,
        legend="Trace 1",
    )
    basic_plot.add_trace(
        axis=1,
        data=[(x, x * 5 + 50) for x in range(-10, 11)],
        color=LT_BLUE_1,
        legend="Trace 2",
    )
    basic_plot.add_note(note="Test note", location=[0.5, 0.5])
    basic_plot.add_legend(axis=1, location=(0.1, 0.9))
    return basic_plot


class TestPlotInit:
    """Tests for plot constructor initialization."""

    def test_stores_plot_title(self, basic_plot):
        """Verify plot_title is stored correctly."""
        assert basic_plot.plot_title == "Test Plot"

    def test_stores_plot_name(self, basic_plot):
        """Verify plot_name is stored correctly."""
        assert basic_plot.plot_name == "TP01"

    def test_stores_xaxis_label(self, basic_plot):
        """Verify xaxis_label is stored correctly."""
        assert basic_plot.xaxis_label == "VOLTAGE (V)"

    def test_stores_xlims(self, basic_plot):
        """Verify xlims tuple is stored correctly."""
        assert basic_plot.xlims == (-10, 10)

    def test_stores_ylims_in_y1_params(self, basic_plot):
        """Verify ylims is stored in y1_axis_params."""
        assert basic_plot.y1_axis_params["ylims"] == (0, 100)

    def test_stores_xdivs(self, basic_plot):
        """Verify xdivs is stored correctly."""
        assert basic_plot.xdivs == 5

    def test_stores_xminor(self, basic_plot):
        """Verify xminor is stored correctly."""
        assert basic_plot.xminor == 2

    def test_stores_logx(self, basic_plot):
        """Verify logx is stored correctly."""
        assert basic_plot.logx is False

    def test_y1_axis_params_keys(self, basic_plot):
        """Verify y1_axis_params has all expected keys."""
        expected_keys = {
            "yaxis_label", "ylims", "yminor", "ydivs", "logy",
            "autoscaley", "place_legend", "legend_loc",
            "trace_data", "histo_data", "axis_is_used",
        }
        assert expected_keys.issubset(set(basic_plot.y1_axis_params.keys()))

    def test_y1_axis_is_used(self, basic_plot):
        """Verify y1 axis is marked as used."""
        assert basic_plot.y1_axis_params["axis_is_used"] is True

    def test_y2_axis_not_used(self, basic_plot):
        """Verify y2 axis is not used by default."""
        assert basic_plot.y2_axis_params["axis_is_used"] is False

    def test_styles_populated(self, basic_plot):
        """Verify styles list contains 4 linestyles x 5 colors = 20 entries."""
        assert len(basic_plot.styles) == 20

    def test_plot_type_regular(self, basic_plot):
        """Verify plot_type is 'regular'."""
        assert basic_plot.plot_type == "regular"

    def test_notes_initially_empty(self, basic_plot):
        """Verify notes list starts empty."""
        assert basic_plot.notes == []

    def test_arrows_initially_empty(self, basic_plot):
        """Verify arrows list starts empty."""
        assert basic_plot.arrows == []

    def test_trace_data_initially_empty(self, basic_plot):
        """Verify trace data lists start empty."""
        assert basic_plot.y1_axis_params["trace_data"] == []
        assert basic_plot.y2_axis_params["trace_data"] == []


class TestAddTrace:
    """Tests for plot.add_trace method."""

    def test_appends_to_y1_axis(self, basic_plot):
        """Verify trace is appended to y1 when axis=1."""
        basic_plot.add_trace(
            axis=1, data=[(0, 0), (1, 1)], color=LT_RED_1, legend="test"
        )
        assert len(basic_plot.y1_axis_params["trace_data"]) == 1

    def test_appends_to_y2_axis(self, basic_plot):
        """Verify trace is appended to y2 when axis=2."""
        basic_plot.add_trace(
            axis=2, data=[(0, 0), (1, 1)], color=LT_BLUE_1, legend="test"
        )
        assert len(basic_plot.y2_axis_params["trace_data"]) == 1

    def test_trace_dict_keys(self, basic_plot):
        """Verify trace dict contains all expected keys."""
        basic_plot.add_trace(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend="test"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        expected_keys = {
            "axis", "data", "color", "marker", "markersize",
            "linestyle", "linewidth", "legend", "stepped_style",
            "vxline", "hxline",
        }
        assert set(trace.keys()) == expected_keys

    def test_rejects_empty_data(self, basic_plot, capsys):
        """Verify empty data is rejected with a warning."""
        basic_plot.add_trace(
            axis=1, data=[], color=LT_RED_1, legend="empty"
        )
        assert len(basic_plot.y1_axis_params["trace_data"]) == 0
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_converts_zip_to_list(self, basic_plot):
        """Verify zip input is converted to list."""
        data = zip([1, 2, 3], [4, 5, 6])
        basic_plot.add_trace(axis=1, data=data, color=LT_RED_1, legend="zip")
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert isinstance(trace["data"], list)
        assert trace["data"] == [(1, 4), (2, 5), (3, 6)]

    def test_handles_numpy_array(self, basic_plot):
        """Verify numpy array data is accepted."""
        data = np.array([(0.0, 1.0), (2.0, 3.0)])
        basic_plot.add_trace(axis=1, data=data, color=LT_RED_1, legend="np")
        assert len(basic_plot.y1_axis_params["trace_data"]) == 1

    def test_legend_hyphen_replaced(self, basic_plot):
        """Verify hyphen in legend is replaced with unicode minus."""
        basic_plot.add_trace(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend="V-OUT"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert "-" not in trace["legend"]
        assert "−" in trace["legend"]

    def test_legend_none_is_preserved(self, basic_plot):
        """Verify None legend is kept as None."""
        basic_plot.add_trace(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend=None
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["legend"] is None

    def test_default_parameters(self, basic_plot):
        """Verify default values for optional parameters."""
        basic_plot.add_trace(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend="test"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["marker"] is None
        assert trace["markersize"] == 0
        assert trace["linestyle"] == "-"
        assert trace["linewidth"] is None
        assert trace["stepped_style"] is False
        assert trace["vxline"] is False
        assert trace["hxline"] is False


class TestAddScatter:
    """Tests for plot.add_scatter method."""

    def test_adds_trace_with_no_linestyle(self, basic_plot):
        """Verify scatter uses linestyle='None'."""
        basic_plot.add_scatter(
            axis=1, data=[(0, 0), (1, 1)], color=LT_RED_1, legend="scatter"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["linestyle"] == "None"

    def test_default_marker(self, basic_plot):
        """Verify default marker is '*'."""
        basic_plot.add_scatter(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend="scatter"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["marker"] == "*"

    def test_default_markersize(self, basic_plot):
        """Verify default markersize is 4."""
        basic_plot.add_scatter(
            axis=1, data=[(0, 0)], color=LT_RED_1, legend="scatter"
        )
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["markersize"] == 4


class TestHorizontalLine:
    """Tests for plot.add_horizontal_line method."""

    def test_creates_trace(self, basic_plot):
        """Verify horizontal line creates a trace in y1."""
        basic_plot.add_horizontal_line(value=50)
        assert len(basic_plot.y1_axis_params["trace_data"]) == 1

    def test_trace_data_spans_xlims(self, basic_plot):
        """Verify trace data spans the full x range."""
        basic_plot.add_horizontal_line(value=50)
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["data"] == [(-10, 50), (10, 50)]

    def test_adds_note_when_specified(self, basic_plot):
        """Verify note is added when note parameter is provided."""
        basic_plot.add_horizontal_line(value=50, note="limit")
        assert len(basic_plot.notes) == 1
        assert basic_plot.notes[0]["note"] == "limit"

    def test_discards_note_on_autoscale(self, autoscale_plot, capsys):
        """Verify note is discarded when xlims is auto."""
        autoscale_plot.add_horizontal_line(value=50, note="limit")
        assert len(autoscale_plot.notes) == 0
        captured = capsys.readouterr()
        assert "Discarding" in captured.out

    def test_hxline_flag_on_autoscale(self, autoscale_plot):
        """Verify hxline flag is True when xlims are auto and no xrange."""
        autoscale_plot.add_horizontal_line(value=50)
        trace = autoscale_plot.y1_axis_params["trace_data"][0]
        assert trace["hxline"] is True

    def test_custom_xrange(self, basic_plot):
        """Verify custom xrange overrides xlims."""
        basic_plot.add_horizontal_line(value=50, xrange=(-5, 5))
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["data"] == [(-5, 50), (5, 50)]

    def test_default_color_is_red(self, basic_plot):
        """Verify default color is red [1, 0, 0]."""
        basic_plot.add_horizontal_line(value=50)
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["color"] == [1, 0, 0]

    def test_axis2(self, basic_plot):
        """Verify horizontal line can target axis 2."""
        basic_plot.make_second_y_axis("Y2", (0, 50), 0, 5, False)
        basic_plot.add_horizontal_line(value=25, axis=2)
        assert len(basic_plot.y2_axis_params["trace_data"]) == 1


class TestVerticalLine:
    """Tests for plot.add_vertical_line method."""

    def test_creates_trace(self, basic_plot):
        """Verify vertical line creates a trace."""
        basic_plot.add_vertical_line(value=0)
        assert len(basic_plot.y1_axis_params["trace_data"]) == 1

    def test_trace_data_spans_ylims(self, basic_plot):
        """Verify trace data spans the full y range."""
        basic_plot.add_vertical_line(value=0)
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["data"] == [(0, 0), (0, 100)]

    def test_adds_note_when_specified(self, basic_plot):
        """Verify note is added when note parameter is provided."""
        basic_plot.add_vertical_line(value=0, note="trigger")
        assert len(basic_plot.notes) == 1

    def test_raises_on_invalid_axis(self, basic_plot):
        """Verify Exception is raised for invalid axis value."""
        with pytest.raises(Exception, match="AXIS MUST BE 1 or 2"):
            basic_plot.add_vertical_line(value=0, axis=3)

    def test_vxline_flag_on_autoscale(self, autoscale_plot):
        """Verify vxline flag is True when ylims are auto and no yrange."""
        autoscale_plot.add_vertical_line(value=0)
        trace = autoscale_plot.y1_axis_params["trace_data"][0]
        assert trace["vxline"] is True

    def test_custom_yrange(self, basic_plot):
        """Verify custom yrange overrides ylims."""
        basic_plot.add_vertical_line(value=5, yrange=(10, 90))
        trace = basic_plot.y1_axis_params["trace_data"][0]
        assert trace["data"] == [(5, 10), (5, 90)]


class TestHistogram:
    """Tests for plot.add_histogram method."""

    def test_appends_to_y1(self, basic_plot):
        """Verify histogram is appended to y1 histo_data."""
        basic_plot.add_histogram(
            axis=1, xdata=[1, 2, 3, 4, 5], num_bins=5, color=LT_RED_1
        )
        assert len(basic_plot.y1_axis_params["histo_data"]) == 1

    def test_appends_to_y2(self, basic_plot):
        """Verify histogram is appended to y2 histo_data."""
        basic_plot.add_histogram(
            axis=2, xdata=[1, 2, 3], num_bins=3, color=LT_BLUE_1
        )
        assert len(basic_plot.y2_axis_params["histo_data"]) == 1

    def test_histo_dict_keys(self, basic_plot):
        """Verify histogram dict contains expected keys."""
        basic_plot.add_histogram(
            axis=1, xdata=[1, 2], num_bins=2, color=LT_RED_1, legend="hist"
        )
        histo = basic_plot.y1_axis_params["histo_data"][0]
        expected_keys = {"axis", "xdata", "num_bins", "color", "legend", "linewidth", "alpha"}
        assert set(histo.keys()) == expected_keys

    def test_default_linewidth_and_alpha(self, basic_plot):
        """Verify default linewidth is 0.5 and alpha is 1."""
        basic_plot.add_histogram(
            axis=1, xdata=[1], num_bins=1, color=LT_RED_1
        )
        histo = basic_plot.y1_axis_params["histo_data"][0]
        assert histo["linewidth"] == 0.5
        assert histo["alpha"] == 1


class TestSecondYAxis:
    """Tests for plot.make_second_y_axis method."""

    def test_enables_y2(self, basic_plot):
        """Verify y2 axis is marked as used."""
        basic_plot.make_second_y_axis("Current (A)", (0, 1), 2, 5, False)
        assert basic_plot.y2_axis_params["axis_is_used"] is True

    def test_stores_label(self, basic_plot):
        """Verify y2 axis label is stored."""
        basic_plot.make_second_y_axis("Current (A)", (0, 1), 2, 5, False)
        assert basic_plot.y2_axis_params["yaxis_label"] == "Current (A)"

    def test_stores_ylims(self, basic_plot):
        """Verify y2 axis limits are stored."""
        basic_plot.make_second_y_axis("Y2", (0, 50), 0, 10, False)
        assert basic_plot.y2_axis_params["ylims"] == (0, 50)

    def test_stores_logy(self, basic_plot):
        """Verify y2 axis log setting is stored."""
        basic_plot.make_second_y_axis("Y2", (1, 1000), 0, 3, True)
        assert basic_plot.y2_axis_params["logy"] is True


class TestAddLegend:
    """Tests for plot.add_legend method."""

    def test_enables_legend_y1(self, basic_plot):
        """Verify legend is enabled for y1 axis."""
        basic_plot.add_legend(axis=1, location=(0.1, 0.9))
        assert basic_plot.y1_axis_params["place_legend"] is True

    def test_stores_location(self, basic_plot):
        """Verify legend location is stored."""
        basic_plot.add_legend(axis=1, location=(0.2, 0.8))
        assert basic_plot.y1_axis_params["legend_loc"] == (0.2, 0.8)

    def test_stores_justification(self, basic_plot):
        """Verify legend justification is stored."""
        basic_plot.add_legend(axis=1, justification='upper right')
        assert basic_plot.y1_axis_params["legend_justification"] == 'upper right'

    def test_stores_fontsize(self, basic_plot):
        """Verify legend fontsize is stored."""
        basic_plot.add_legend(axis=1, fontsize=10)
        assert basic_plot.y1_axis_params["legend_fontsize"] == 10

    def test_y2_axis_legend(self, basic_plot):
        """Verify legend can be placed on y2 axis."""
        basic_plot.add_legend(axis=2, location=(0.9, 0.9))
        assert basic_plot.y2_axis_params["place_legend"] is True
        assert basic_plot.y2_axis_params["legend_loc"] == (0.9, 0.9)


class TestAddNote:
    """Tests for plot.add_note method."""

    def test_appends_note(self, basic_plot):
        """Verify note is appended to notes list."""
        basic_plot.add_note(note="Hello", location=[0.5, 0.5])
        assert len(basic_plot.notes) == 1

    def test_note_dict_keys(self, basic_plot):
        """Verify note dict contains all expected keys."""
        basic_plot.add_note(note="Test", location=[0.1, 0.2])
        note = basic_plot.notes[0]
        expected_keys = {
            "note", "location", "axis", "use_axes_scale",
            "fontsize", "horizontalalignment", "verticalalignment",
        }
        assert set(note.keys()) == expected_keys

    def test_default_location(self, basic_plot):
        """Verify default location is [0.05, 0.5]."""
        basic_plot.add_note(note="default loc")
        assert basic_plot.notes[0]["location"] == [0.05, 0.5]

    def test_default_fontsize(self, basic_plot):
        """Verify default fontsize is 7."""
        basic_plot.add_note(note="small")
        assert basic_plot.notes[0]["fontsize"] == 7

    def test_custom_fontsize(self, basic_plot):
        """Verify custom fontsize is stored."""
        basic_plot.add_note(note="big", fontsize=14)
        assert basic_plot.notes[0]["fontsize"] == 14

    def test_default_alignment(self, basic_plot):
        """Verify default alignment values."""
        basic_plot.add_note(note="aligned")
        note = basic_plot.notes[0]
        assert note["horizontalalignment"] == "left"
        assert note["verticalalignment"] == "bottom"

    def test_multiple_notes(self, basic_plot):
        """Verify multiple notes can be added."""
        basic_plot.add_note(note="First", location=[0.1, 0.1])
        basic_plot.add_note(note="Second", location=[0.5, 0.5])
        basic_plot.add_note(note="Third", location=[0.9, 0.9])
        assert len(basic_plot.notes) == 3


class TestAddArrow:
    """Tests for plot.add_arrow method."""

    def test_appends_arrow(self, basic_plot):
        """Verify arrow is appended to arrows list."""
        basic_plot.add_arrow(
            text="Peak", text_location=[0.2, 0.8], arrow_tip=[0.5, 0.5]
        )
        assert len(basic_plot.arrows) == 1

    def test_arrow_dict_keys(self, basic_plot):
        """Verify arrow dict contains all expected keys."""
        basic_plot.add_arrow(
            text="Point", text_location=[0.1, 0.9], arrow_tip=[0.3, 0.3]
        )
        arrow = basic_plot.arrows[0]
        expected_keys = {"text", "text_location", "arrow_tip", "use_axes_scale", "fontsize"}
        assert set(arrow.keys()) == expected_keys

    def test_default_fontsize(self, basic_plot):
        """Verify default arrow fontsize is 7."""
        basic_plot.add_arrow(
            text="A", text_location=[0, 0], arrow_tip=[1, 1]
        )
        assert basic_plot.arrows[0]["fontsize"] == 7

    def test_custom_fontsize(self, basic_plot):
        """Verify custom arrow fontsize is stored."""
        basic_plot.add_arrow(
            text="B", text_location=[0, 0], arrow_tip=[1, 1], fontsize=12
        )
        assert basic_plot.arrows[0]["fontsize"] == 12


class TestScopePlot:
    """Tests for scope_plot class."""

    def test_plot_type(self, scope):
        """Verify plot_type is 'scope_plot'."""
        assert scope.plot_type == "scope_plot"

    def test_xdivs_fixed(self, scope):
        """Verify xdivs is fixed at 10."""
        assert scope.xdivs == 10

    def test_ydivs_fixed(self, scope):
        """Verify ydivs is fixed at 8."""
        assert scope.y1_axis_params["ydivs"] == 8

    def test_logx_false(self, scope):
        """Verify logx is always False for scope plots."""
        assert scope.logx is False

    def test_logy_false(self, scope):
        """Verify logy is always False for scope plots."""
        assert scope.y1_axis_params["logy"] is False

    def test_add_trace_no_axis_param(self, scope):
        """Verify scope_plot add_trace works without axis parameter."""
        scope.add_trace(data=[(0, 0), (1, 1)], color=LT_RED_1)
        assert len(scope.y1_axis_params["trace_data"]) == 1

    def test_make_second_y_axis_raises(self, scope):
        """Verify make_second_y_axis raises Exception."""
        with pytest.raises(Exception):
            scope.make_second_y_axis("Y2", (0, 10), 0, 5, False)

    def test_add_ref_marker(self, scope):
        """Verify add_ref_marker stores data."""
        scope.add_ref_marker(ylocation=2.5, marker_color=LT_RED_1, use_axes_scale=True)
        assert len(scope.ref_markers) == 1
        assert scope.ref_markers[0]["ylocation"] == 2.5

    def test_add_trace_label(self, scope):
        """Verify add_trace_label stores data."""
        scope.add_trace_label(trace_label="VIN", ylocation=3.0, use_axes_scale=True)
        assert len(scope.trace_labels) == 1
        assert scope.trace_labels[0]["trace_label"] == "VIN"

    def test_add_time_refmarker_open(self, scope):
        """Verify add_time_refmarker_open stores xlocation."""
        scope.add_time_refmarker_open(xlocation=1e-6)
        assert scope.include_time_refmarker_open is True
        assert scope.time_refmarker_open_xlocation == 1e-6

    def test_add_time_refmarker_closed(self, scope):
        """Verify add_time_refmarker_closed stores xlocation."""
        scope.add_time_refmarker_closed(xlocation=3e-6)
        assert scope.include_time_refmarker_closed is True
        assert scope.time_refmarker_closed_xlocation == 3e-6

    def test_add_all_time_refmarkers(self, scope):
        """Verify add_all_time_refmarkers sets both markers."""
        scope.add_all_time_refmarkers(xlocation_open=1e-6, xlocation_closed=4e-6)
        assert scope.include_time_refmarker_open is True
        assert scope.include_time_refmarker_closed is True

    def test_add_horizontal_line(self, scope):
        """Verify scope add_horizontal_line creates a trace."""
        scope.add_horizontal_line(value=2.5)
        assert len(scope.y1_axis_params["trace_data"]) == 1

    def test_add_vertical_line(self, scope):
        """Verify scope add_vertical_line creates a trace."""
        scope.add_vertical_line(value=2.5e-6)
        assert len(scope.y1_axis_params["trace_data"]) == 1

    def test_horizontal_line_with_note(self, scope):
        """Verify scope horizontal line with note adds both trace and note."""
        scope.add_horizontal_line(value=3.0, note="LIMIT")
        assert len(scope.y1_axis_params["trace_data"]) == 1
        assert len(scope.notes) == 1


class TestPageInit:
    """Tests for Page constructor."""

    def test_rows_x_cols(self):
        """Verify rows_x_cols is stored correctly."""
        page = Page(rows_x_cols=(2, 3))
        assert page.rows_x_cols == (2, 3)

    def test_plot_count_1(self):
        """Verify plot_count=1 maps to (1, 1) grid."""
        page = Page(plot_count=1)
        assert page.rows_x_cols == (1, 1)

    def test_plot_count_2(self):
        """Verify plot_count=2 maps to (1, 2) grid."""
        page = Page(plot_count=2)
        assert page.rows_x_cols == (1, 2)

    def test_plot_count_3(self):
        """Verify plot_count=3 maps to (1, 3) grid."""
        page = Page(plot_count=3)
        assert page.rows_x_cols == (1, 3)

    def test_plot_count_4(self):
        """Verify plot_count=4 maps to (2, 3) grid."""
        page = Page(plot_count=4)
        assert page.rows_x_cols == (2, 3)

    def test_plot_count_7(self):
        """Verify plot_count=7 maps to (3, 3) grid."""
        page = Page(plot_count=7)
        assert page.rows_x_cols == (3, 3)

    def test_raises_when_both_specified(self):
        """Verify Exception when both rows_x_cols and plot_count given."""
        with pytest.raises(Exception):
            Page(rows_x_cols=(2, 2), plot_count=4)

    def test_raises_when_neither_specified(self):
        """Verify Exception when neither rows_x_cols nor plot_count given."""
        with pytest.raises(Exception):
            Page()

    def test_page_size_stored(self):
        """Verify page_size is stored."""
        page = Page(rows_x_cols=(1, 1), page_size=(8.5, 11))
        assert page.page_size == (8.5, 11)


class TestPageAddPlot:
    """Tests for Page.add_plot method."""

    def test_adds_to_plot_list(self, basic_plot):
        """Verify plot is added to page's plot_list."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        assert len(page.plot_list) == 1
        assert page.plot_list[0] is basic_plot

    def test_raises_on_mixed_types(self, basic_plot, scope):
        """Verify Exception when mixing regular and scope plots."""
        page = Page(plot_count=2)
        page.add_plot(basic_plot)
        with pytest.raises(Exception, match="different types"):
            page.add_plot(scope)


class TestPageRendering:
    """Tests for Page SVG and PDF rendering."""

    def test_create_svg_returns_bytes(self, basic_plot):
        """Verify create_svg returns bytes without writing file."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)
        assert b"<svg" in result

    def test_create_svg_contains_title(self, basic_plot):
        """Verify SVG output contains the plot title."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        result = page.create_svg(file_basename=None)
        assert b"Test Plot" in result

    def test_create_svg_writes_file(self, basic_plot, tmp_path):
        """Verify create_svg writes file when basename specified."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        page.create_svg(file_basename="test_output", filepath=str(tmp_path))
        svg_path = tmp_path / "plots" / "test_output.svg"
        assert svg_path.exists()
        assert svg_path.stat().st_size > 0

    def test_create_pdf_writes_file(self, basic_plot, tmp_path):
        """Verify create_pdf writes a PDF file."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        page.create_pdf(file_basename="test_output", filepath=str(tmp_path))
        pdf_path = tmp_path / "plots" / "test_output.pdf"
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0

    def test_render_with_traces(self, populated_plot):
        """Verify rendering succeeds with traces, notes, and legend."""
        page = Page(plot_count=1)
        page.add_plot(populated_plot)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)
        assert len(result) > 100

    def test_render_with_histogram(self, basic_plot):
        """Verify rendering succeeds with histogram data."""
        basic_plot.add_histogram(
            axis=1, xdata=np.random.randn(100).tolist(),
            num_bins=20, color=LT_BLUE_1
        )
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)

    def test_render_scope_plot(self, scope):
        """Verify scope_plot renders successfully."""
        scope.add_trace(
            data=[(t * 5e-7, 2.5 * np.sin(t * 1e7)) for t in range(11)],
            color=LT_RED_1,
        )
        page = Page(plot_count=1)
        page.add_plot(scope)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)

    def test_render_with_second_y_axis(self, basic_plot):
        """Verify rendering with second y-axis works."""
        basic_plot.make_second_y_axis("Power (W)", (0, 10), 0, 5, False)
        basic_plot.add_trace(
            axis=1, data=[(x, x * 5) for x in range(11)],
            color=LT_RED_1, legend="V"
        )
        basic_plot.add_trace(
            axis=2, data=[(x, x * 0.5) for x in range(11)],
            color=LT_BLUE_1, legend="P"
        )
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)

    def test_render_with_log_axes(self):
        """Verify rendering with log axes works."""
        p = plot(
            plot_title="Log Plot",
            plot_name="LP01",
            xaxis_label="FREQUENCY (Hz)",
            yaxis_label="GAIN (dB)",
            xlims=(1, 1e6),
            ylims=(-60, 20),
            xminor=9,
            xdivs=6,
            yminor=0,
            ydivs=8,
            logx=True,
            logy=False,
        )
        p.add_trace(
            axis=1, data=[(10**x, -x * 10) for x in range(7)],
            color=LT_RED_1, legend="Gain"
        )
        page = Page(plot_count=1)
        page.add_plot(p)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)

    def test_multiple_plots_on_page(self, basic_plot):
        """Verify multiple plots can be rendered on one page."""
        p2 = plot(
            plot_title="Plot 2", plot_name="P2",
            xaxis_label="X", yaxis_label="Y",
            xlims=(0, 10), ylims=(0, 10),
            xminor=0, xdivs=5, yminor=0, ydivs=5,
            logx=False, logy=False,
        )
        page = Page(plot_count=2)
        page.add_plot(basic_plot)
        page.add_plot(p2)
        result = page.create_svg(file_basename=None)
        assert isinstance(result, bytes)


def _find_text_element(svg, text_content):
    """Find the <text ...> element containing the given text and return its attributes."""
    pattern = r"<text\s([^>]*)>[^<]*" + re.escape(text_content)
    match = re.search(pattern, svg)
    if match:
        return match.group(1)
    pattern = r"<text\s([^>]*)>\s*<[^>]*>[^<]*" + re.escape(text_content)
    match = re.search(pattern, svg)
    return match.group(1) if match else None


def _has_style_prop(attrs, prop, value_pattern):
    """Check if an attribute string contains a CSS property matching a value pattern.

    Handles both individual properties (font-size: 7px) and the CSS font
    shorthand (font: 700 7px 'Arial') used by different matplotlib versions.
    """
    if re.search(prop + r":\s*" + value_pattern, attrs):
        return True
    font_match = re.search(r"font:\s*([^;\"]+)", attrs)
    if font_match:
        font_val = font_match.group(1)
        if prop == "font-size":
            return bool(re.search(r"(?<!\w)" + value_pattern, font_val))
        if prop == "font-weight":
            return bool(re.search(value_pattern, font_val))
        if prop == "font-family":
            return bool(re.search(r"['\"]?\w+['\"]?\s*$", font_val))
    return False


class TestSvgContent:
    """End-to-end SVG content assertions verifying matplotlib interface surface."""

    @pytest.fixture
    def svg_with_note(self, basic_plot):
        """Render a plot with a custom-fontsize note to SVG."""
        basic_plot.add_trace(
            axis=1, data=[(x, x * 10) for x in range(-10, 11)],
            color=LT_RED_1, legend="Trace A",
        )
        basic_plot.add_note(note="ANNOTATION_XYZ", location=[0.5, 0.5],
                           use_axes_scale=False, fontsize=12)
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        return page.create_svg(file_basename=None).decode("utf-8")

    @pytest.fixture
    def svg_basic(self, basic_plot):
        """Render a basic plot with a trace and legend to SVG."""
        basic_plot.add_trace(
            axis=1, data=[(x, x * 10) for x in range(-10, 11)],
            color=LT_RED_1, legend="Trace A",
        )
        basic_plot.add_legend(axis=1, location=(0.1, 0.9))
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        return page.create_svg(file_basename=None).decode("utf-8")

    def test_title_bold_9pt5(self, svg_basic):
        """Verify title appears with bold weight and 9.5px font size."""
        attrs = _find_text_element(svg_basic, "Test Plot")
        assert attrs is not None, "Title text element not found in SVG"
        assert _has_style_prop(attrs, "font-size", r"9\.5px")
        assert _has_style_prop(attrs, "font-weight", r"(700|bold)")

    def test_axis_label_fontsize_7(self, svg_basic):
        """Verify axis labels are rendered with font-size 7px."""
        for label in ["VOLTAGE (V)", "CURRENT (mA)"]:
            attrs = _find_text_element(svg_basic, label)
            assert attrs is not None, f"Axis label '{label}' not found in SVG"
            assert _has_style_prop(attrs, "font-size", r"7px")

    def test_plot_name_fontsize_4(self, svg_basic):
        """Verify plot name appears with font-size 4px."""
        attrs = _find_text_element(svg_basic, "TP01")
        assert attrs is not None, "Plot name text element not found in SVG"
        assert _has_style_prop(attrs, "font-size", r"4px")

    def test_font_family_set(self, svg_basic):
        """Verify font-family is set on text elements (Arial or platform fallback)."""
        attrs = _find_text_element(svg_basic, "Test Plot")
        assert attrs is not None
        assert _has_style_prop(attrs, "font-family", r".+")

    def test_note_text_present(self, svg_with_note):
        """Verify note text appears in SVG output."""
        assert "ANNOTATION_XYZ" in svg_with_note

    def test_note_fontsize_rendered(self, svg_with_note):
        """Verify the custom note fontsize appears on the note element."""
        attrs = _find_text_element(svg_with_note, "ANNOTATION_XYZ")
        assert attrs is not None, "Note text element not found in SVG"
        assert _has_style_prop(attrs, "font-size", r"12px")

    def test_default_note_fontsize_7(self, basic_plot):
        """Verify default note fontsize 7 appears on the note element."""
        basic_plot.add_note(note="DEFAULT_NOTE_ABC")
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        svg = page.create_svg(file_basename=None).decode("utf-8")
        attrs = _find_text_element(svg, "DEFAULT_NOTE_ABC")
        assert attrs is not None, "Default note text element not found in SVG"
        assert _has_style_prop(attrs, "font-size", r"7px")

    def test_trace_color_in_svg(self, svg_basic):
        """Verify trace color appears in SVG as rgb or hex."""
        assert re.search(
            r"rgb\(153,\s*0,\s*51\)|#990033|rgb\(60%,\s*0%,\s*20%\)",
            svg_basic)

    def test_tick_label_fontsize_7(self, svg_basic):
        """Verify tick labels use font-size 7px (multiple text elements)."""
        matches = re.findall(
            r"<text[^>]*(?:font-size:\s*7px|font:\s*7px|font:\s*\S+\s+7px)[^>]*>",
            svg_basic)
        assert len(matches) >= 2

    def test_linear_helv_cond_replacement(self, svg_basic):
        """Verify 'Linear Helv Cond' is collapsed to 'LinearHelvCond' if present."""
        assert "Linear Helv Cond" not in svg_basic

    def test_scope_plot_xaxis_label(self, scope):
        """Verify scope plot renders x-axis label at 7px."""
        scope.add_trace(
            data=[(t * 5e-7, 2.5) for t in range(11)],
            color=LT_RED_1,
        )
        page = Page(plot_count=1)
        page.add_plot(scope)
        svg = page.create_svg(file_basename=None).decode("utf-8")
        attrs = _find_text_element(svg, "500ns/DIV")
        assert attrs is not None, "Scope x-axis label not found in SVG"
        assert _has_style_prop(attrs, "font-size", r"7px")

    def test_arrow_text_in_svg(self, basic_plot):
        """Verify arrow annotation text appears in SVG output."""
        basic_plot.add_arrow(
            text="ARROW_MARKER_42", text_location=[0.3, 0.7],
            arrow_tip=[0.5, 0.5], use_axes_scale=False,
        )
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        svg = page.create_svg(file_basename=None).decode("utf-8")
        assert "ARROW_MARKER_42" in svg

    def test_legend_text_in_svg(self, svg_basic):
        """Verify legend text appears in SVG output."""
        assert "Trace A" in svg_basic


class TestPlotCreateSvgShortcut:
    """Tests for plot.create_svg convenience method."""

    def test_returns_bytes(self, populated_plot, tmp_path):
        """Verify plot.create_svg returns SVG bytes."""
        result = populated_plot.create_svg(
            file_basename="shortcut_test",
        )
        assert isinstance(result, bytes)
        assert b"<svg" in result


class TestPlotCreateCsv:
    """Tests for plot.create_csv method."""

    def test_creates_csv_file(self, populated_plot, tmp_path):
        """Verify CSV file is created."""
        populated_plot.create_csv(
            file_basename="csv_test", filepath=str(tmp_path)
        )
        csv_path = tmp_path / "csv" / "csv_test.csv"
        assert csv_path.exists()

    def test_csv_headers(self, basic_plot, tmp_path):
        """Verify CSV has correct column headers."""
        basic_plot.add_trace(
            axis=1, data=[(1, 2), (3, 4)], color=LT_RED_1, legend="Signal"
        )
        basic_plot.create_csv(file_basename="header_test", filepath=str(tmp_path))
        csv_path = tmp_path / "csv" / "header_test.csv"
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "Signal_x" in headers[0] or "Signal" in headers[0]

    def test_csv_data_rows(self, basic_plot, tmp_path):
        """Verify CSV contains the correct number of data rows."""
        basic_plot.add_trace(
            axis=1, data=[(1, 10), (2, 20), (3, 30)],
            color=LT_RED_1, legend="Data"
        )
        basic_plot.create_csv(file_basename="rows_test", filepath=str(tmp_path))
        csv_path = tmp_path / "csv" / "rows_test.csv"
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 4  # header + 3 data rows

    def test_csv_duplicate_legend(self, basic_plot, tmp_path):
        """Verify duplicate legends are handled without crashing."""
        basic_plot.add_trace(
            axis=1, data=[(1, 10)], color=LT_RED_1, legend="Same"
        )
        basic_plot.add_trace(
            axis=1, data=[(2, 20)], color=LT_BLUE_1, legend="Same"
        )
        basic_plot.create_csv(
            file_basename="dup_test", filepath=str(tmp_path)
        )
        csv_path = tmp_path / "csv" / "dup_test.csv"
        assert csv_path.exists()


class TestMultipagePdf:
    """Tests for Multipage_pdf class."""

    def test_init_empty(self):
        """Verify Multipage_pdf starts with empty page_list."""
        mpdf = Multipage_pdf()
        assert mpdf.page_list == []

    def test_add_page(self, basic_plot):
        """Verify add_page appends to page_list."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        mpdf = Multipage_pdf()
        mpdf.add_page(page)
        assert len(mpdf.page_list) == 1

    def test_create_pdf(self, basic_plot, tmp_path):
        """Verify create_pdf writes a multi-page PDF file."""
        page1 = Page(plot_count=1)
        page1.add_plot(basic_plot)
        p2 = plot(
            plot_title="Page 2", plot_name="P2",
            xaxis_label="X", yaxis_label="Y",
            xlims=(0, 1), ylims=(0, 1),
            xminor=0, xdivs=5, yminor=0, ydivs=5,
            logx=False, logy=False,
        )
        page2 = Page(plot_count=1)
        page2.add_plot(p2)
        mpdf = Multipage_pdf()
        mpdf.add_page(page1)
        mpdf.add_page(page2)
        mpdf.create_pdf(file_basename="multi_test", filepath=str(tmp_path))
        pdf_path = tmp_path / "plots" / "multi_test.pdf"
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


class TestPageSvgComments:
    """Tests for Page.add_comment and SVG comment embedding."""

    def test_add_comment_stores(self, basic_plot):
        """Verify add_comment stores the text."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        page.add_comment("Test comment")
        assert "Test comment" in page._svg_comments

    def test_comments_in_svg_output(self, basic_plot):
        """Verify comments appear in SVG output."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        page.add_comment("My comment here")
        result = page.create_svg(file_basename=None)
        assert b"<!-- My comment here -->" in result

    def test_double_dash_sanitized(self, basic_plot):
        """Verify double-dashes are sanitized in comments."""
        page = Page(plot_count=1)
        page.add_plot(basic_plot)
        page.add_comment("test--value")
        assert page._svg_comments[0] == "test‐‐value"


class TestColorGen:
    """Tests for color_gen class."""

    def test_returns_tuple(self):
        """Verify color_gen returns a tuple."""
        cg = color_gen()
        color = cg()
        assert isinstance(color, tuple)
        assert len(color) == 3

    def test_cycles_through_colors(self):
        """Verify colors cycle through MARCOM palette."""
        cg = color_gen()
        colors = [cg() for _ in range(5)]
        assert colors == MARCOM_COLORSfracRGB

    def test_rollover(self):
        """Verify rollover wraps around to first color."""
        cg = color_gen(rollover=True)
        for _ in range(5):
            cg()
        sixth = cg()
        assert sixth == MARCOM_COLORSfracRGB[0]

    def test_no_rollover_raises(self):
        """Verify rollover=False raises IndexError when exhausted."""
        cg = color_gen(rollover=False)
        for _ in range(5):
            cg()
        with pytest.raises(IndexError):
            cg()

    def test_reset(self):
        """Verify reset restarts from first color."""
        cg = color_gen()
        cg()
        cg()
        cg.reset()
        assert cg() == MARCOM_COLORSfracRGB[0]


class TestColorConversions:
    """Tests for color conversion utility functions."""

    @pytest.mark.parametrize("cmyk,expected", [
        ((0, 0, 0, 0), (1, 1, 1)),
        ((1, 0, 0, 0), (0, 1, 1)),
        ((0, 1, 0, 0), (1, 0, 1)),
        ((0, 0, 1, 0), (1, 1, 0)),
        ((0, 0, 0, 1), (0, 0, 0)),
    ])
    def test_cmyk_to_fracrgb(self, cmyk, expected):
        """Verify CMYK to fractional RGB conversion."""
        result = CMYK_to_fracRGB(cmyk)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("rgb,expected", [
        ((1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 0.0)),
        ((0, 0, 0), (0, 0, 0, 1)),
    ])
    def test_fracrgb_to_cmyk(self, rgb, expected):
        """Verify fractional RGB to CMYK conversion."""
        result = fracRGB_to_CMYK(rgb)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("web,expected", [
        ("FF0000", (1.0, 0.0, 0.0)),
        ("00FF00", (0.0, 1.0, 0.0)),
        ("0000FF", (0.0, 0.0, 1.0)),
        ("000000", (0.0, 0.0, 0.0)),
        ("FFFFFF", (1.0, 1.0, 1.0)),
    ])
    def test_webrgb_to_fracrgb(self, web, expected):
        """Verify web hex to fractional RGB conversion."""
        result = webRGB_to_fracRGB(web)
        assert result == pytest.approx(expected)

    def test_webrgb_to_rgb(self):
        """Verify web hex to 0-255 RGB conversion."""
        assert webRGB_to_RGB("FF8000") == (255, 128, 0)

    def test_fracrgb_to_rgb(self):
        """Verify fractional RGB to 0-255 RGB conversion."""
        assert fracRGB_to_RGB((1.0, 0.0, 0.0)) == (255, 0, 0)
        assert fracRGB_to_RGB((0.0, 1.0, 0.0)) == (0, 255, 0)

    def test_rgb_to_fracrgb(self):
        """Verify 0-255 RGB to fractional RGB conversion."""
        assert RGB_to_fracRGB((255, 0, 0)) == (1.0, 0.0, 0.0)

    def test_roundtrip_fracrgb_rgb(self):
        """Verify fracRGB -> RGB -> fracRGB roundtrip."""
        original = (0.6, 0.2, 0.8)
        rgb = fracRGB_to_RGB(original)
        back = RGB_to_fracRGB(rgb)
        assert back == pytest.approx(original, abs=1 / 255.0)

    def test_roundtrip_web_frac(self):
        """Verify webRGB -> fracRGB -> webRGB roundtrip (via RGB)."""
        original = "336699"
        frac = webRGB_to_fracRGB(original)
        rgb = fracRGB_to_RGB(frac)
        web_back = RGB_to_webRGB(rgb)
        assert int(web_back[0], 16) == 0x33
        assert int(web_back[1], 16) == 0x66
        assert int(web_back[2], 16) == 0x99


class TestDataFromFile:
    """Tests for data_from_file utility function."""

    def test_reads_csv_data(self, tmp_path):
        """Verify data_from_file reads comma-separated x,y pairs."""
        data_file = tmp_path / "test_data.csv"
        data_file.write_text("1.0,10.0\n2.0,20.0\n3.0,30.0\n")
        result = data_from_file(str(data_file))
        assert result == [(1.0, 10.0), (2.0, 20.0), (3.0, 30.0)]

    def test_returns_list_of_tuples(self, tmp_path):
        """Verify return type is list of tuples."""
        data_file = tmp_path / "single.csv"
        data_file.write_text("5.5,6.6\n")
        result = data_from_file(str(data_file))
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2


class TestModuleConstants:
    """Tests for module-level constants."""

    def test_marcom_colors_count(self):
        """Verify MARCOM_COLORS has 5 entries."""
        assert len(MARCOM_COLORS) == 5

    def test_marcom_colors_fracrgb_count(self):
        """Verify MARCOM_COLORSfracRGB has 5 entries."""
        assert len(MARCOM_COLORSfracRGB) == 5

    def test_marcom_colors_fracrgb_format(self):
        """Verify each MARCOM color is a 3-tuple of floats in [0,1]."""
        for color in MARCOM_COLORSfracRGB:
            assert isinstance(color, tuple)
            assert len(color) == 3
            for component in color:
                assert 0.0 <= component <= 1.0

    def test_unicode_constants(self):
        """Verify unicode constants have expected values."""
        assert DELTA == "Δ"
        assert DEGC == "°C"
        assert DEG == "°"

    def test_lt_colors_are_tuples(self):
        """Verify named LT colors are 3-tuples."""
        for color in [LT_RED_1, LT_BLUE_1, LT_BLACK]:
            assert isinstance(color, tuple)
            assert len(color) == 3
