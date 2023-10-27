import csv

class ATE_index_utils:
    def __init__(self):
        self.index_file = "file/location.csv"

    def get_stdf_location(self, dut_id):
        with open(self.index_file, 'r') as index_file:
            csvreader = csv.reader(index_file)
            for row in csvreader:
                if row[0] is dut_id:
                    stdf_file = row[0]
                    break
        return stdf_file

    def append_index(self, dut_id, stdf_file_location):
        with open(self.index_file, 'a') as index_file:
            csvwriter = csv.writer(index_file)
            csvwriter.writerow([dut_id, stdf_file_location])

    def consolidate_duts(self):
        '''I think an stdf file is only going to have one temperature in it,
        so we could have three different files for one DUT. Need to think 
        about how to determine which file we want, or if we want to merge 
        them all somehow.'''
        pass