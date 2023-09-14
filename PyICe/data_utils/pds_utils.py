import re, random, xlsxwriter
COMMA_REPLACEMENT_STRING = hex(random.getrandbits(128))

class pds_reader():
    ''' Reads and parses an Eagle Test System's .pds "Datasheet" file into a reasonable datastructure.
        It may have errors, the Eagle schema is a complete C/F of made up nonesene making it difficult to interpret.
        Files structure is as follows:
            Result is a dictionary of test groups keyed by the group name.
                Each dictionary of test groups is a dictionary of tests keys by the test NUMBER.SUBTESTNUMBER.
                    Each test is a dictionary of parameters keyed by Eagle columns as described by the file section "Datasheet Variable Map".
        Method get_test(test_number, subtest_number) may be used to tease out a specific test record.'''
    def __init__(self, filename):
        with open(filename) as file:
            lines = file.readlines()
            self.data = {}
        for line in lines[:-1]:                 # skip first blank line (will always be that way?)
            if line.startswith("["):
                section = line.strip("[]\n")
                self.data[section] = []
            if line.startswith('"'):            # \"\ == secret key indicating a test?
                quoteds = re.findall('"([^"]*)"', line)
                for quoted in quoteds:
                    line = line.replace(quoted, quoted.replace(",",COMMA_REPLACEMENT_STRING))
                self.data[section].append(line.strip("\n"))
        self.get_column_map()
        self.find_test_groups()
        self.build_record()
    def get_column_map(self):
        self.column_map = []
        for column in self.data["Datasheet Variable Map"]:
            self.column_map.append(column.split(",")[1].strip('"'))
    def find_test_groups(self):
        self.test_groups = []
        for key in self.data:
            if key.startswith("T") and key[1].isdigit():
                self.test_groups.append(key)
    def build_record(self):
        self.results = {}
        for test_group in self.test_groups:
            self.results[test_group] = {}
            test_number = int(test_group.split("_")[0][1:]) # Is this always true, this schema is a disaster!
            for test in self.data[test_group]:
                params = [x.strip('"') for x in test.split(",")]
                this_test = zip(self.column_map, params[1:])# extra "" leader
                parameter = {}
                for column, param in this_test:
                    parameter[column] = param.replace(COMMA_REPLACEMENT_STRING, ",")
                self.results[test_group][f"{test_number}.{parameter['SubTestNmbr']}"] = parameter
    def get_test(self, test_number, subtest_number):
        for test_group in self.results:
            if f"{test_number}.{subtest_number}" in self.results[test_group].keys():
                return self.results[test_group][f"{test_number}.{subtest_number}"]
        print(f"PDS Reader: Sorry, couldn't find test: {test_number}.{subtest_number} in the record.")
    def generate_excel_report(self, file_name):
        columns  = ["TestNmbr","SubTestNmbr","DLogDesc","LoFTRm","HiFTRm","LoFTTrim","HiFTTrim","LoFTCold","HiFTCold","LoFTHot","HiFTHot","LoQARm","HiQARm","LoQACold","HiQACold","LoQACold1","HiQACold1","LoQAHot","HiQAHot","LoQAHot1","HiQAHot1","LoWS","HiWS","LoWS1","HiWS1",
"LoWS2","HiWS2","LoWSEng","HiWSEng","LoEng1","HiEng1","LoEng2","HiEng2","Units"]
        workbook = xlsxwriter.Workbook(file_name)
        for test_group in self.results:
            worksheet = workbook.add_worksheet(test_group)
            column_num = 0
            row_num = 0
            for column in columns:
                worksheet.write(row_num, column_num, column)
                column_num += 1
            row_num += 1
            for test in self.results[test_group]:
                column_num = 0
                for column in columns:
                    worksheet.write(row_num, column_num, self.results[test_group][test][column])
                    column_num += 1
                row_num += 1            
        workbook.close()

if __name__ == "__main__":
    # tests = pds_reader("short1.pds")
    tests = pds_reader("LT3390.pds")
    # for test_group in tests.results.keys():
        # print()
        # print()
        # print(test_group)
        # for test in tests.results[test_group].keys():
            # print(test)
            # print(tests.results[test_group][test])
            # print()
           
    # print()
    # print(tests.get_test(10,101)['DLogDesc'])
    # print(tests.get_test(10,101))
    # print()
    # print(tests.get_test(10,102)['DLogDesc'])
    # print(tests.get_test(10,102))
    
    tests.generate_excel_report('tables.xlsx')