import csv


class CorrelationUtils:
    def __init__(self):
        self.index_file = "file/location.csv"

    def get_stdf_location(self, dut_id):
        """
        From a csv file that contains rows of identifying names of duts and the stdf file location that has the dut's
        ATE test data, return the location.
        Args:
            dut_id: The id of the dut with which the bench data was collected.

        Returns:
        A string found in the csv spelling out the file location of the given dut's ATE data.
        """
        with open(self.index_file, 'r') as index_file:
            csvreader = csv.reader(index_file)
            for row in csvreader:
                if row[0] is dut_id:
                    stdf_file = row[0]
                    break
        return stdf_file

    def append_stdf_index(self, dut_id, stdf_file_location):
        """
        Adds a new line to the existing index.
        Args:
            dut_id: Unique name of the dut with which ATE data was collected.
            stdf_file_location: Location of the stdf file that has the ATE data collected.

        Returns:
        N/A
        """
        with open(self.index_file, 'a') as index_file:
            csvwriter = csv.writer(index_file)
            csvwriter.writerow([dut_id, stdf_file_location])

    def consolidate_duts(self):
        '''I think an stdf file is only going to have one temperature in it,
        so we could have three different files for one DUT. Need to think 
        about how to determine which file we want, or if we want to merge 
        them all somehow.'''
        pass