"""L Tspice waveform reader utilities.

>>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader

"""
from scipy.interpolate import interp1d
from PyICe.lab_utils.eng_string import eng_string
import numpy


class LTspice_wavereader():
    """L tspice_wavereader.

    >>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader
    >>> LTspice_wavereader is not None
    True

    """
    def __init__(self, file_name):
        """Initialize LTspice waveform reader from exported text file.

           To export a record of one or more waveforms in a waveform pane, right click in the plane, drop down to 'File' menu and select 'export data as text'.

           From the dialog box you should be able to select multiple traces by name and save to a new file.
           The output file format is a simple tab delimited schema with the channel names on the first line.
           Each successive line contains a row data, also tab delimited in the same order as the header row.
           For some reason the file seems to have an extra line feed after the last record.

           This script endevors to parse the file and return a Python record of the individual columns.

           The resultant data structure is a dictionary with the header row values as the keys and a list of values found for each column as the values for each key.
           It is incumbent upon the user to massage the record further, for example zipping times and voltages if need be for the data analysis.


        >>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader
        >>> LTspice_wavereader is not None
        True

        Args:
            file_name: File path string.
        """
        self.file_name = file_name

    def read_file(self, floats=True):
        """As returned from the file, each data value would be a string.

           The argument 'floats' (default True) converts all the values to floats presuming that was the intent of the LTCspice excercise.


        >>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader
        >>> hasattr(LTspice_wavereader, 'read_file')
        True

        Args:
            floats: Floats to use.
        """
        rows = []
        file = open(self.file_name, "r")
        firstline = True
        self.data = {}
        keys = []
        for line in file:
            if firstline:
                keys = line.strip().split("\t")
                firstline = False
            else:
                rows.append(line.strip().split("\t"))
        file.close()
        column = 0              # Dictionaries are ordered since Python 3.6
        for key in keys:
            self.data[key] = []
            for row in rows:
                self.data[key].append(
                    float(row[column]) if floats else row[column])
            column += 1

    def resample_timeseries(self, timestep, verbose=False):
        """This utility can be used to resample the data with a known fixed time step so that an FFT may be taken.

           LTspice, as with all versions of Spice, generates variable time steps as needed for covergence.
           The first column of data (first dictionary key) is presumed to be the indepdendent variable, or common indepedent variable, across all columns - almost invariably "time".
           The original series is destroyed and replaced with the resampled version.


        >>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader
        >>> hasattr(LTspice_wavereader, 'resample_timeseries')
        True

        Args:
            timestep: Timestep to use.
            verbose: If True, print debug output.
        """
        keys = [key for key in self.data.keys()]
        native_times = self.data[keys[0]]
        start = native_times[0]
        stop = native_times[-1]
        new_times = numpy.linspace(
            start=start,
            stop=stop,
            num=round(
                (stop - start) / timestep),
            endpoint=True,
            retstep=False,
            dtype=None,
            axis=0)

        if verbose:
            print("Resampling Time Series, Please wait....")
            print(
                f"Original size: {eng_string(x=len(native_times), fmt=':.2g', si=True, units=' Points')}")
            print(
                f"New size:      {eng_string(x=len(new_times), fmt=':.2g', si=True, units=' Points')}")

        self.data[keys[0]] = new_times
        for data_series in keys[1:]:
            if verbose:
                print(f"Processing: {data_series}")
            interp_function = interp1d(
                x=native_times,
                y=self.data[data_series],
                kind='linear')
            self.data[data_series] = [
                interp_function(time) for time in new_times]
        if verbose:
            print("Resampling Complete!")

    def get_results(self):
        """Return the current results.
        Returns the stored results value from the object's internal state.
        Returns the stored results from the object's internal state.

        Returns the stored results from the object's internal state.


        >>> from PyICe.data_utils.LTspice_waveform_reader import LTspice_wavereader
        >>> hasattr(LTspice_wavereader, 'get_results')
        True

        Returns:
            The current results.
        """
        return self.data
