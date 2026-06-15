"""Oscilloscope waveform dump utilities.

>>> from PyICe.data_utils.oscilloscope_waveform_dump import dict_print

"""
from PyICe.lab_instruments.oscilloscope import oscilloscope
from PyICe import lab_core
from PyICe.lab_utils.sqlite_data import sqlite_data
import numpy
import json
import re

try:
    from bokeh.models import Toggle
    from bokeh import colors
    # https://docs.bokeh.org/en/latest/docs/reference/colors.html#bokeh-colors-color

    from bokeh.plotting import show, output_file, figure
    from bokeh.io import curdoc
    from bokeh.layouts import layout
except Exception:
    import traceback
    traceback.print_exc()
    print("Broken Bokeh")
    Toggle = None  # type: ignore[assignment]
    colors = None  # type: ignore[assignment]
    show = None  # type: ignore[assignment]
    output_file = None  # type: ignore[assignment]
    figure = None  # type: ignore[assignment]
    curdoc = None  # type: ignore[assignment]
    layout = None  # type: ignore[assignment]


class dict_print(dict):
    """Dict_print.

    >>> from PyICe.data_utils.oscilloscope_waveform_dump import dict_print
    >>> dict_print is not None
    True

    """
    def __str__(self):
        """Return string representation.
        Provides a human-readable string for debugging and display.

        Provides a human-readable representation for debugging and logging.


        >>> from PyICe.data_utils.oscilloscope_waveform_dump import dict_print
        >>> hasattr(dict_print, '__str__')
        True

        Returns:
            String representation.
        """
        ret_str = ""
        max_key_len = 0
        for key, value in self.items():
            max_key_len = len(key) if len(key) > max_key_len else max_key_len
            if isinstance(value, list) and len(value) >= 4:
                ret_str += f"{key}:\t[{value[0]}, {value[1]}, ..., {value[-2]}, {value[-1]}]\n"
            else:
                ret_str += f"{key}:\t{value}\n"
        return ret_str.expandtabs(max_key_len + 2)


class oscilloscope_waveform_dump(oscilloscope):
    """Oscilloscope_waveform_dump.

    >>> from PyICe.data_utils.oscilloscope_waveform_dump import oscilloscope_waveform_dump
    >>> oscilloscope_waveform_dump is not None
    True

    """
    def __init__(self, interface_visa):
        """interface_visa.
        Stores configuration in ``_base_name`` for use by other methods.

        Calls the parent constructor to inherit base behavior, and initializes 1 instance attribute that configure the object's behavior.


        >>> from PyICe.data_utils.oscilloscope_waveform_dump import oscilloscope_waveform_dump
        >>> oscilloscope_waveform_dump is not None
        True

        Args:
            interface_visa: VISA interface instance.
        """
        self._base_name = "agilent_3034a"
        lab_core.scpi_instrument.__init__(
            self, "agilent_3034a @ {}".format(interface_visa))
        # Clears self._interfaces list, so must happen before
        # add_interface_visa(). --FL 12/21/2016
        lab_core.delegator.__init__(self)
        self.add_interface_visa(interface_visa)
        self.get_interface().write(":WAVeform:FORMat BYTE")
        # maximum number of points by default (scope must be stopped)
        self.get_interface().write(":WAVeform:POINts:MODE RAW")
        self.get_interface().write(":WAVeform:POINts MAXimum")

    def _get_channel_data(self, channel_num):
        self.get_interface().write(f":Waveform:Source CHANNel{channel_num}")
        return self.fetch_waveform_data()

    def _get_scope_time_info(self):
        # Requires Waveform Source to be set to an acive channel
        self.time_info = {}
        self.time_info["points"] = int(self.get_interface().ask(
            ":WAVeform:POINts?"))         # int(preamble[2])
        self.time_info["x_increment"] = float(
            # float(preamble[4])
            self.get_interface().ask(":WAVeform:XINCrement?"))
        self.time_info["x_origin"] = float(self.get_interface().ask(
            ":WAVeform:XORigin?"))      # float(preamble[5])
        self.time_info["x_reference"] = float(
            # float(preamble[6])
            self.get_interface().ask(":WAVeform:XREFerence?"))
        self.time_info["x_scale"] = self.time_info["x_increment"] * \
            self.time_info["points"] / 10
        # self.time_info["x_values"] = [(x - self.time_info["x_reference"]) * self.time_info["x_increment"] + self.time_info["x_origin"] for x in range(self.time_info["points"])]
        xvalues_gen = map(
            lambda x: (
                x -
                self.time_info["x_reference"]) *
            self.time_info["x_increment"] +
            self.time_info["x_origin"],
            range(
                self.time_info["points"]))
        self.time_info["x_values"] = numpy.fromiter(
            xvalues_gen, dtype=numpy.dtype('<d'))
        return self.time_info

    def fetch_active_scope_channels(self):
        """Return fetch active scope channels result.
        Sends the ``:Display`` SCPI command to the instrument.

        Sends the corresponding SCPI command string to the instrument over the bus.


        >>> from PyICe.data_utils.oscilloscope_waveform_dump import oscilloscope_waveform_dump
        >>> hasattr(oscilloscope_waveform_dump, 'fetch_active_scope_channels')
        True

        Returns:
            The fetched data.
        """
        results_dict = dict_print()
        for num in [1, 2, 3, 4]:
            displayed = int(
                self.get_interface().ask(
                    f":Channel{num}:Display?"))
            results_dict[f'channel_{num}_active'] = displayed
            if displayed:
                results_dict[f"channel_{num}"] = self._get_channel_data(num)
                for key, value in self.get_waveform_scaling().items():
                    results_dict[f"channel_{num}_{key}"] = value
                results_dict[f'channel_{num}_name'] = self.user_query_waveform_name(
                    num)
        if len(results_dict):
            results_dict.update(self._get_scope_time_info())
            print(f"Number of points captured = {results_dict['points']}")
        return results_dict

    def user_query_waveform_name(self, channel_number):
        """Return user query waveform name result.

        Supports the ``oscilloscope_waveform_dump`` workflow by performing the described operation.


        >>> from PyICe.data_utils.oscilloscope_waveform_dump import oscilloscope_waveform_dump
        >>> hasattr(oscilloscope_waveform_dump, 'user_query_waveform_name')
        True

        Args:
            channel_number: Physical channel number.

        Returns:
            The user-selected value.
        """
        resp = ""
        while not len(resp):
            resp = input(f"What's channel_{channel_number} measuring: ")
        return resp

    def data_to_sqlite(self, db_filename='scope_data.sqlite'):
        """Return data to sqlite result.

        Supports the ``oscilloscope_waveform_dump`` workflow by performing the described operation.


        >>> from PyICe.data_utils.oscilloscope_waveform_dump import oscilloscope_waveform_dump
        >>> hasattr(oscilloscope_waveform_dump, 'data_to_sqlite')
        True

        Args:
            db_filename: Db filename to use.

        Returns:
            The converted data.
        """
        logger = lab_core.logger(database=db_filename, use_threads=False)
        scope_data = self.fetch_active_scope_channels()
        logger.add_data_channels(scope_data)
        for ch in logger:
            if re.match(r"^channel_[1234]$", ch.get_name()):
                ch._set_type_affinity('PyICeBLOB')
            elif re.match(r"^x_values$", ch.get_name()):
                ch._set_type_affinity('PyICeBLOB')
        db_tablename = ''
        while not len(db_tablename):
            db_tablename = input("What would you like the table name to be: ")
        logger.new_table(db_tablename)
        _sd = logger.log_data(scope_data)  # noqa: F841
        logger.stop()
        # return sd
        return db_tablename


def plot_dumped_waveform(db_tablename, db_filename='scope_data.sqlite'):
    """Perform plot dumped waveform operation.
    Configures or updates the plot with the specified parameters.

    Generates or configures a visual representation of the data.


    >>> from PyICe.data_utils.oscilloscope_waveform_dump import plot_dumped_waveform
    >>> callable(plot_dumped_waveform)
    True

    Args:
        db_filename: Db filename to use.
        db_tablename: Db tablename to use.
    """
    db = sqlite_data(
        table_name=db_tablename,
        database_file=db_filename,
        timezone=None)
    output_file(filename=f'{db_tablename}.html', title=db_tablename)
    curdoc().theme = 'dark_minimal'
    plot = figure(title=db_tablename, width=1000, height=800)
    active_channels = {}
    channel_colors = {
        1: colors.named.gold,
        2: colors.named.forestgreen,
        3: colors.named.mediumblue,
        4: colors.named.fuchsia}
    (datetime, x_values, active_channels[1], active_channels[2], active_channels[3], active_channels[4]) = db.query(
        f'SELECT datetime,x_values, channel_1_active, channel_2_active, channel_3_active, channel_4_active FROM {db_tablename}').fetchone()
    toggles = {}
    for i in range(1, 5):
        if active_channels[i]:
            (ydata, data_name) = db.query(
                f'SELECT channel_{i}, channel_{i}_name FROM {db_tablename}').fetchone()
            this_line = plot.line(
                x=x_values,
                y=ydata,
                line_color=channel_colors[i],
                legend_label=f"{data_name}",
                alpha=.5)
            toggles[i] = Toggle(
                label=f'Show {data_name}',
                button_type='success',
                active=True,
                background=channel_colors[i])  # background does NOTHING!
            toggles[i].js_link('active', this_line, 'visible')
    show(layout([plot], list(toggles.values())))


def write_waveform_data(
        db_tablename, db_filename='scope_data.sqlite', output_filename=None):
    """Return write waveform data result.
    Formats and sends the command to the instrument.

    Writes data to the underlying target.


    >>> from PyICe.data_utils.oscilloscope_waveform_dump import write_waveform_data
    >>> callable(write_waveform_data)
    True

    Args:
        db_filename: Db filename to use.
        db_tablename: Db tablename to use.
        output_filename: Output filename to use.
    """
    if output_filename is None:
        output_filename = f'{db_tablename}.json'
    db = sqlite_data(
        table_name=db_tablename,
        database_file=db_filename,
        timezone=None)
    active_channels = {}
    (datetime, x_values, active_channels[1], active_channels[2], active_channels[3], active_channels[4]) = db.query(
        f'SELECT datetime,x_values, channel_1_active, channel_2_active, channel_3_active, channel_4_active FROM {db_tablename}').fetchone()
    scope_data = {}
    scope_data['x_values'] = x_values
    for i in range(1, 5):
        if active_channels[i]:
            (ydata, data_name) = db.query(
                f'SELECT channel_{i}, channel_{i}_name FROM {db_tablename}').fetchone()
            scope_data[data_name] = ydata

    class NumpyEncoder(json.JSONEncoder):
        """Special json encoder for numpy types."""

        def default(self, obj):
            """Return the default.

            Supports the ``NumpyEncoder`` workflow by performing the described operation.


            >>> from PyICe.data_utils.oscilloscope_waveform_dump import default
            >>> callable(default)
            True

            Args:
                obj: Obj to use.

            Returns:
                The default value.
            """
            if isinstance(obj, numpy.integer):
                return int(obj)
            elif isinstance(obj, numpy.floating):
                return float(obj)
            elif isinstance(obj, numpy.ndarray):
                return obj.tolist()
            elif isinstance(obj, numpy.bool_):
                return bool(obj)
            # elif isinstance(obj, datetime.datetime):
                # return obj.isoformat()
            return json.JSONEncoder.default(self, obj)
    with open(output_filename, 'w') as f:
        json.dump(scope_data, f, cls=NumpyEncoder)
    print(f'Scope data dumped to {output_filename} successfully.')


if __name__ == '__main__':
    answer = input("(P)lot data only or (C)ollect and plot or (D)ump JSON: ")
    if answer.lower() == "c":
        try:
            from create_user_files import create_my_scopefile
            from local.my_instruments import agilent_3034a
        except ImportError as e:
            raise ImportError("Collection mode requires local user files. See PyICe documentation.") from e
        create_my_scopefile()
        dump = oscilloscope_waveform_dump(agilent_3034a)
        db_tablename = dump.data_to_sqlite()
    elif answer.lower() == "p" or answer.lower() == "d":
        db_tablename = input(
            "Enter the table name in the preexisting scope_data.sqlite file: ")
    else:
        print(
            f"\n\nYour response was: '{answer}'.\nDon't know what '{answer}' is supposed to do.\nDoing nothing.\n\n")
        exit()
    if answer.lower() != "d":
        plot_dumped_waveform(db_tablename)
    elif answer.lower() == "d":
        write_waveform_data(db_tablename)
    else:
        raise Exception("I'm lost")
