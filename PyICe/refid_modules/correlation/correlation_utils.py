import csv


class CorrelationUtils:
    def __init__(self):
        self.index_file = "file/location.csv"

    def get_stdf_info(self, dut_id):
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
                    stdf_file = row[1]
                    part_ids = row[2] # or hash or something.
                    break
        target_data_dict = STDFParser(stdf_file, part_ids)
        return target_data_dict

    def append_stdf_index(self, dut_id, stdf_file_location, part_id):
        """
        Adds a new line to the existing index.
        Args:
            dut_id: Unique name of the dut with which ATE data was collected.
            stdf_file_location: Location of the stdf file that has the ATE data collected.
            part_id: The value of the 'PART_ID' in the PRR of the dut in question.

        Returns:
        N/A
        """
        with open(self.index_file, 'a') as index_file:
            csvwriter = csv.writer(index_file)
            csvwriter.writerow([dut_id, stdf_file_location, part_id])
