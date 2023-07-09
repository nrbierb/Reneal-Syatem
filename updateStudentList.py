#!/usr/bin/python3
# -*- coding: utf-8 -*-
import csv
import re
import datetime
import os
import argparse
import operator
import copy
import io
import getpass
import sys
import localFunctions

# define these here for easy readability and change
VERSION = "1.3"
PROGRAM_NAME = "updateStudentList"
BASE_DIRECTORY = "/client_home/share/"
# use this for test only -- comment out for real version
# BASE_DIRECTORY = "./testStudentLists/"
PRIMARY_FILE = "student_list.csv"
STUDENT_LIST_FILENAME = BASE_DIRECTORY + PRIMARY_FILE
BACKUP_DIRECTORY = BASE_DIRECTORY + "old_student_lists"
SOURCE_FILES_DIRECTORY = BASE_DIRECTORY + "student_source_lists"
FILE_OWNERUID = 1001
FILE_OWNERGID = 1001

SchoolParams = localFunctions.school_params()
StudentGroupName = SchoolParams["StudentGroupName"]
StudentGroupNameRE = SchoolParams["StudentGroupNameRE"]
ClassYearName = SchoolParams["ClassYearName"]
ClassYearNameRE = SchoolParams["ClassYearNameRE"]
YearList = SchoolParams["YearList"]
RnYearList = SchoolParams["RnYearList"]
DisplayYearList = SchoolParams["DisplayYearList"]
YearListMatch = SchoolParams["YearListMatch"]
RnYearListMatch = SchoolParams["RnYearListMatch"]
ValueNames = ("Last Name", "First Name", "Middle Name", StudentGroupName,
              ClassYearName)
ReportingText = ""
UseGui = False


class StudentListFile:
    """
    This class represents the list of students, its backup,
    and management actions. for the list
    """

    def __init__(self):
        global BASE_DIRECTORY, BACKUP_DIRECTORY, PRIMARY_FILE, ReportingText, UseGui
        self.student_list_file_name = BASE_DIRECTORY + PRIMARY_FILE
        self.student_data = []

    def file_is_current(self):
        """
        confirm that the date is within the school year
        """
        current_date = datetime.date.today()
        file_edit_date = datetime.date.fromtimestamp(os.stat(
            self.student_list_file_name).st_mtime)
        # this assumes that the country is Tanzania. Simple, just the same year
        current_school_year_start = current_date.replace(month=1, day=1)
        if localFunctions.school_params("Country") == "Philippines":
            # Philippines is more complex - June through March
            current_date_tuple = current_date.timetuple()
            current_month = current_date_tuple.tm_mon
            current_year = current_date_tuple.tm_year
            # Same year as school start at Jun
            current_school_year_start = current_date.replace(month=6, day=1)
            if current_month < 5:
                # school start was last year
                current_school_year_start = current_date.replace(
                    year=current_year - 1,
                    month=6, day=1)
        compare_date = current_school_year_start - datetime.timedelta(30)
        return file_edit_date > compare_date

    def is_valid(self):
        return os.path.exists(
            self.student_list_file_name) and self.file_is_current()

    def move_current_file_to_backup(self):
        """
        Move the current student list file to the backup directory and rename 
        with a creation date extension. It is not an error if the file does not
        exist.
        :return: 
        """
        global ReportingText, UseGui
        if os.path.exists( self.student_list_file_name):
            try:
                file_edit_date = datetime.date.fromtimestamp(os.stat(
                    self.student_list_file_name).st_mtime)
                if not os.path.exists(BACKUP_DIRECTORY):
                    os.mkdir(BACKUP_DIRECTORY, 0o775)
                    os.chown(BACKUP_DIRECTORY, FILE_OWNERUID, FILE_OWNERGID)
                new_name = "%s/%s.%s" % (
                    BACKUP_DIRECTORY, PRIMARY_FILE, file_edit_date.isoformat())
                os.rename(self.student_list_file_name, new_name)
                os.chown(new_name, FILE_OWNERUID, FILE_OWNERGID)
                ReportingText += localFunctions.color_text("purple",
                       "Last year's student_list.csv file has been moved to %s. " \
                                        % new_name, use_gui=UseGui)
            except OSError:
                localFunctions.error_exit(
                    "Unable to move the old student_list file. Try 'sudo updateStudentList'",
                    use_gui=UseGui)

    def write_student_list_file(self, student_data):
        """
        Create a new student list file with a fixed header and the data from
        the student_data_object
        :return: 
        """
        global ValueNames, UseGui
        try:
            self.student_data = student_data
            student_list_file = open(self.student_list_file_name, "w",
                                     encoding='latin1')
            writer = csv.writer(student_list_file)
            writer.writerow(ValueNames)
            for i in range(len(self.student_data)):
                writer.writerow(self.student_data[i][0:5])
            student_list_file.close()
        except IOError:
            localFunctions.error_exit(
                "Unable to write the student_list file. Try 'sudo updateStudentList'",
                use_gui=UseGui)
        try:
            # set to correct ownership and permissions
            os.chmod(self.student_list_file_name, 0o644)
            # if this is run as root make sure file still belongs to sysadmin
            if getpass.getuser() == "root":
                os.chown(self.student_list_file_name, FILE_OWNERUID,
                         FILE_OWNERGID)
        except OSError:
            localFunctions.error_exit(
                """Unable set permissions or ownership on the student_list file.
Try 'sudo updateStudentList'""", use_gui=UseGui)

    def create(self, student_data):
        """
        If an out of date student list file exists move it to a backup name.
        Then, if no file exists, create a new one with headers but no data.
        :return:
        """
        global ReportingText, UseGui
        if os.path.exists(self.student_list_file_name):
            if not self.file_is_current():
                # move to backup directory and rename
                self.move_current_file_to_backup()
            else:
                # just rename
                backup_name = self.student_list_file_name + ".old"
                os.rename(self.student_list_file_name, backup_name)
                ReportingText += localFunctions.color_text("purple",
                                    'The prior student_list.csv file has been moved to:\n\t%s\n'
                                    % backup_name, use_gui=UseGui)
        self.write_student_list_file(student_data)

    def count_unique(self, column_index):
        check_dict = {}
        try:
            for row in self.student_data:
                check_dict[row[column_index]] = 1
        except IndexError:
            pass
        return len(check_dict.keys())

    def report_stats(self, initial_count):
        """
        :return: 
        """
        return """
    Total Students: %d
    Students Added: %d
    %ss: %d
    %ss: %d""" % (len(self.student_data),
                  (len(self.student_data) - initial_count),
                  StudentGroupName,
                  max(self.count_unique(3), self.count_unique(4)),
                  ClassYearName, self.count_unique(4))


class StudentData:
    """
    Maintain all data processed by the source file processors in simple
    database and provide it to the student list generator to create the new file.
    Only one of these exists in the program.
    """

    def __init__(self):
        global ValueNames, YearList, ReportingText
        self.all_values_dict = {}
        self.all_values_list = []
        self.data_list = []
        for name in ValueNames:
            self.all_values_dict[name] = []

    def add(self, source_file_data):
        global DisplayYearList
        self.all_values_list = copy.deepcopy(self.data_list)
        for i in range(len(source_file_data["Last Name"])):
            try:
                row = []
                for name in ValueNames:
                    val = source_file_data[name][i]
                    if not val:
                        val = ""
                    row.append(val)
                # add a value used for sorting the class year.
                # It will not be used in the final data
                sort_index = 100
                try:
                    year = source_file_data[ClassYearName][i]
                    sort_index = DisplayYearList.index(year)
                except ValueError:
                    pass
                row.append(sort_index)
                self.all_values_list.append(row)
            except LookupError:
                pass

    def update_data_list(self):
        """
        Remove duplicates and sort
        :return: 
        """
        check_dict = {}
        self.data_list = []
        for row in self.all_values_list:
            key = tuple(row)
            if key not in check_dict:
                check_dict[key] = "exists"
                self.data_list.append(row)
        # duplicate_count = len(self.all_values_list) - len(self.data_list)
        self.data_list.sort(key=operator.itemgetter(5, 3, 0, 1, 2))

    def insert(self, source_file_data):
        self.add(source_file_data)
        self.update_data_list()
        return len(self.data_list)

    def get_data(self):
        return self.data_list


class SourceFileProcessor:
    """
    Read and extract data from a single input file to be used in
    creation or expansion of the student list. An instance of this class
    should be created for each file in the command line list. If a
    current student list file exists it should also be read as a source.
    """

    def __init__(self, source_file_name, student_data):
        global ValueNames, ReportingText
        self.source_file_name = source_file_name
        self.student_data = student_data
        self.file_contents = []
        self.data_dict = {}
        for name in ValueNames:
            self.data_dict[name] = []

    def readfile(self):
        """
        Read a single file. Do not handle exceptions so that they
        may be handled by caller.
        :param self:
        :return:
        """
        source_file = open(self.source_file_name, "r", encoding='latin1')
        self.file_contents = source_file.readlines()
        source_file.close()

    def valid_file(self):
        global ReportingText, UseGui
        valid = True
        try:
            if not os.path.exists(self.source_file_name):
                ReportingText += localFunctions.color_text("Red",
                                   "File \"%s\" does not exist.\n" % self.source_file_name,
                                   use_gui=UseGui)
                valid = False
            self.readfile()
            if not self.file_contents:
                ReportingText += localFunctions.color_text("Red",
                                   "File \"%s\" is empty.\n" % self.source_file_name,
                                   use_gui=UseGui)
                valid = False
        except IOError:
            ReportingText += localFunctions.color_text("Red",
                               "File \"%s\" cannot be read.\n" % self.source_file_name,
                               use_gui=UseGui)
            valid = False
        return valid

    @staticmethod
    def create_header(data):
        """
        If only three columns determine which column contains which data.
        The column with a comma is the name column
        :return:
        """
        value_dicts = [{}, {}, {}]
        max_splits = [0, 0, 0]
        for column in [0, 1, 2]:
            reader = csv.reader(data)
            for line in reader:
                value = line[column]
                clean_value = localFunctions.cleanup_string(value,
                                                            further_remove_characters="",
                                                            join_character=" ")
                if clean_value:
                    value_dicts[column][clean_value] = 1
                    word_count = len(clean_value.split())
                    if word_count > max_splits[column]:
                        max_splits[column] = word_count
        column_names = ["", "", ""]
        index = [0, 1, 2]
        counts = [len(value_dicts[0]), len(value_dicts[1]), len(value_dicts[2])]
        student_groups_used = False
        for i in index:
            # find the name
            vd = list(value_dicts[i].keys())
            value = vd[0]
            if counts[i] == max(counts) and (value.find(",") > 1 or
                                             max_splits[i] > 1):
                column_names[i] = "Name"
        for i in index:
            if not column_names[i]:
                vd = list(value_dicts[i].keys())
                value = vd[0]
                if SourceFileProcessor.correct_year_name(value) \
                        and (counts[i] == min(counts) or student_groups_used):
                    column_names[i] = ClassYearName
                    continue
                else:
                    column_names[i] = StudentGroupName
                    student_groups_used = True
                    continue
        return column_names

    @staticmethod
    def correct_year_name(value):
        global YearListMatch, YearList, RnYearListMatch, RnYearList
        corrected_value = ""
        lower_case = value.lower().strip()
        if value:
            # look for exact match on roman numerals first
            for i in range(len(RnYearListMatch) - 1, -1, -1):
                if lower_case == RnYearListMatch[i]:
                    corrected_value = RnYearList[i]
                    break
            # roman numeral not found, check for year names and numbers
            if not corrected_value:
                for i in range(len(YearListMatch) - 1, -1, -1):
                    try:
                        lower_case.index(YearListMatch[i])
                        corrected_value = YearList[i]
                        break
                    except (ValueError, IndexError):
                        corrected_value = ""
        return corrected_value

    @staticmethod
    def process_header(first_line):
        global StudentGroupNameRE, ClassYearNameRE, ClassYearName
        converted_values = []
        invalid_count = 0
        missing = {"Name": 1, StudentGroupName: 1, ClassYearName: 1}
        for value in first_line:
            value = localFunctions.cleanup_string(value,
                                                  further_remove_characters=",./:;",
                                                  join_character=" ").lower()
            try:
                if re.search(r'irst', value, re.IGNORECASE):
                    converted_values.append("First Name")
                elif re.search(r'last', value, re.IGNORECASE) \
                        or re.search(r'surn', value, re.IGNORECASE):
                    converted_values.append("Last Name")
                    missing.pop("Name")
                elif re.search(r'dle ', value, re.IGNORECASE):
                    converted_values.append("Middle Name")
                elif re.search(StudentGroupNameRE, value, re.IGNORECASE):
                    converted_values.append(StudentGroupName)
                    missing.pop(StudentGroupName)
                elif re.search(ClassYearNameRE, value, re.IGNORECASE):
                    converted_values.append(ClassYearName)
                    missing.pop(ClassYearName)
                elif re.match(r'\s?name', value, re.IGNORECASE):
                    converted_values.append("Name")
                    missing.pop("Name")
                else:
                    invalid_count += 1
                    converted_values.append("Unknown" + str(invalid_count))
            except KeyError:
                pass
        return converted_values, invalid_count, missing

    def read_header(self, first_line):
        converted, invalid_count, missing = self.process_header(first_line)
        header_line_exists = True
        if len(missing) == 3:
            # no required header names exist -- it must no be a header
            header_line_exists = False
        elif invalid_count:
            # not all header columns were valid -- ignore the header line
            if missing:
                converted = []
        return converted, header_line_exists, missing

    def remove_empty_columns(self):
        """
        Check the first line of the data file for any empty columns. These are 
        an artifact of some spreadsheets. Remove the first empty column from 
        the data so that it will not cause problems later. This is called 
        recursively until all empty columns have been removed.
        :return: 
        """
        reader = csv.reader(self.file_contents)
        first_line = next(reader)
        try:
            for i in range(len(first_line)):
                val = localFunctions.cleanup_string(first_line[i],
                                                    title_case=False,
                                                    further_remove_characters=",",
                                                    join_character=" ")
                if not val:
                    # this seems very convoluted in form. It is done to assure
                    # that the file contents is in the correct csv file form
                    reader = csv.reader(self.file_contents)
                    rewrite_file = io.StringIO()
                    writer = csv.writer(rewrite_file)
                    for line in reader:
                        line.pop(i)
                        writer.writerow(line)
                    rewrite_file.seek(0)
                    self.file_contents = rewrite_file.readlines()
                    rewrite_file.close()
                    return True
            return False
        except IOError:
            return False

    def read_csv_file(self, header):
        csv_dict_reader = csv.DictReader(self.file_contents, fieldnames=header,
                                         restkey="Unknown", restval=" ")
        has_info = False
        for line in csv_dict_reader:
            # filter out lines with missing values
            try:
                name_key = "Name"
                if "Last Name" in line:
                    name_key = "Last Name"
                if not line[name_key]:
                    continue
                for key in header:
                    if key not in self.data_dict:
                        self.data_dict[key] = []
                    self.data_dict[key].append(line[key])
            except KeyError:
                pass
            has_info = True
        return has_info

    def split_names(self, name_list):
        """
        The name can be in the form "lastname , firstname" or
        "firstname lastname".
        Split and add to data_dict with the keys last_name and first name
        :return: 
        """
        for key in ("First Name", "Middle Name", "Last Name"):
            if key not in self.data_dict:
                self.data_dict[key] = []
        for name in name_list:
            try:
                # force a space to always be after a period
                name = name.replace(".", ". ")
                # A single quote can be within a Swahili name. Remove it rather
                # than replace it with a space
                name = name.replace("'", "")
                clean_name = localFunctions.cleanup_string(name,
                                                           title_case=True,
                                                           further_remove_characters="",
                                                           join_character=" ",
                                                           remove_leading_numbers=True)
                # if the name is of the form last name, first name split on the
                # comma
                split_name = clean_name.split(',')
                if len(split_name) > 1:
                    self.data_dict["Last Name"].append(split_name[0].strip())

                    self.data_dict["First Name"].append(split_name[1].strip())
                    self.data_dict["Middle Name"].append("")
                else:
                    # The name is probably first middle last, no comma
                    split_name = clean_name.rsplit(" ", 1)
                    if len(split_name) > 1:
                        self.data_dict["Last Name"].append(
                            split_name[1].strip())

                        self.data_dict["First Name"].append(
                            split_name[0].strip())
                        self.data_dict["Middle Name"].append("")
            except IndexError:
                pass

    def process_file(self):
        """
        Perform all of the actions necessary to read a single file, 
        convert the data as required for the StudentData object, and return
        the converted info
        :return: 
        """
        self.readfile()
        while self.remove_empty_columns():
            continue
        csv_reader = csv.reader(self.file_contents)
        first_line = next(csv_reader)
        header, header_line_exists, missing = self.read_header(first_line)
        if header_line_exists and missing:
            missing_str = "A column for the '%s'" % missing.popitem()[0]
            if missing:
                for col_name in missing:
                    missing_str = "%s and '%s'" % (missing_str, col_name)
            missing_str = missing_str + " is missing."
            raise StopIteration(
                "ERROR: File %s not used:\n    %s\n"
                % (self.source_file_name, missing_str))
        elif len(first_line) > 3 and not header_line_exists:
            raise StopIteration(
                """ERROR: File %s not used:
    There is no header row and some extra columns.
    The program cannot guess which columns are which.
    Please add a header row at the top of the spreadsheet.\n"""
                % self.source_file_name)
        else:
            class_year = ""
            student_group = ""
            if header and header_line_exists:
                # there was a header and all values could be changed to correct
                # names so get rid of the current header to prepare to add the
                # new one
                self.file_contents.pop(0)
            else:
                if header_line_exists:
                    # bad header -- get rid of line
                    self.file_contents.pop(0)
                if len(first_line) == 3 and len(self.file_contents):
                    header = self.create_header(self.file_contents)
                else:
                    # guess that it is just the name
                    header = ["Name"]
            # now we are ready to work with a dict_reader
            if self.read_csv_file(header):
                if "Name" in self.data_dict:
                    self.split_names(self.data_dict["Name"])
                try:
                    if not (self.data_dict[ClassYearName] and
                            self.data_dict[StudentGroupName]):
                        raise StopIteration(
                            "ERROR: File %s not used:  At least one value for %s and %s must be set.\n"
                            % (self.source_file_name, StudentGroupName,
                               ClassYearName))
                except KeyError:
                    raise StopIteration(
                        "ERROR: File %s not used:  There must be columns for %s and %s.\n"
                        % (
                            self.source_file_name, StudentGroupName,
                            ClassYearName))
                for column in ("Last Name", "First Name", "Middle Name"):
                    converted_values = []
                    # make all columns equal length.
                    if column != "Last Name":
                        shorter_by = len(self.data_dict["Last Name"]) - \
                                     len(self.data_dict[column])
                        if shorter_by > 0:
                            self.data_dict[column] = self.data_dict[column] + \
                                                     [''] * shorter_by
                    for val in self.data_dict[column]:
                        converted_values.append(
                            localFunctions.cleanup_string(val,
                                                          title_case=True,
                                                          join_character=" ",
                                                          further_remove_characters=",",
                                                          remove_leading_numbers=True))
                    self.data_dict[column] = converted_values
                converted_values = []
                line_number = 1
                for val in self.data_dict[ClassYearName]:
                    line_number += 1
                    corrected_year = self.correct_year_name(val)
                    if corrected_year:
                        # a correct year was found and can be used repeatedly
                        class_year = corrected_year
                    if not class_year:
                        raise StopIteration(
                            "ERROR: File %s not used:\n    Line %d:  '%s'  is not the name of a %s.\n"
                            % (self.source_file_name, line_number, val,
                               ClassYearName))
                    converted_values.append(class_year)
                self.data_dict[ClassYearName] = converted_values
                converted_values = []
                for val in self.data_dict[StudentGroupName]:
                    corrected_group = localFunctions.cleanup_string(val,
                                                                    join_character=" ",
                                                                    further_remove_characters=",")
                    if corrected_group:
                        student_group = corrected_group
                    if not student_group:
                        raise StopIteration(
                            "ERROR: File %s not used: %s and %s must be entered in the first row."
                            % (self.source_file_name, StudentGroupName,
                               ClassYearName))
                    converted_values.append(student_group)
                self.data_dict[StudentGroupName] = converted_values
        return self.data_dict


def perform_filename_dialog():
    command = 'zenity --title="Choose One Or More Files Of Students Names To Add" --file-selection --multiple --file-filter="*.csv"  ' + \
              '--separator="|"  --filename="' + SOURCE_FILES_DIRECTORY + '" 2>/dev/null'
    result = localFunctions.run_command(command, result_as_list=False)
    if len(result) > 0:
        clean_names = result.strip()
        filename_list = clean_names.split('|')
    else:
        filename_list = []
    return filename_list


def force_move_of_student_list_to_backup():
    list_file = StudentListFile()
    list_file.move_current_file_to_backup()


def generate_output_text(bad_files, processed_files, student_list_file):
    global ReportingText, UseGui
    display_text = ReportingText + "\n"
    if bad_files:
        display_text += localFunctions.color_text("red",
                                                  "\nThese files could not be found, were empty, or could not be read:\n",
                                                  use_gui=True)
        for f in bad_files:
            display_text += localFunctions.color_text("red",
                                                      "    -- %s\n" % f,
                                                      use_gui=UseGui)
    if processed_files:
        display_text += localFunctions.color_text("black",
                                                  "These files were correctly processed:\n",
                                                  use_gui=UseGui)
        for f in processed_files:
            line = "    " + f + "\n"
            display_text += localFunctions.color_text("black", line,
                                                      use_gui=UseGui)
    display_text += localFunctions.color_text("blue",
                                              student_list_file.report_stats(
                                                  initial_student_count) + "\n",
                                              use_gui=UseGui)
    if len(processed_files) == len(addon_files):
        display_text += localFunctions.color_text("green",
                                                  "Update successful.\n",
                                                  use_gui=UseGui)
    else:
        display_text += localFunctions.color_text("red",
                                                  "Warning: Not all files processed. Student list incomplete.\n",
                                                  use_gui=UseGui)
    return display_text


def gui_report_result(bad_files, processed_files, student_list_file):
    display_text = generate_output_text(bad_files, processed_files,
                                        student_list_file)
    command = "zenity --info --title='Update Student List Results' --text='%s'" % display_text
    localFunctions.command_run_successful(command)


def print_result(bad_files, processed_files, student_list_file):
    print(generate_output_text(bad_files, processed_files, student_list_file))


if __name__ == '__main__':
    commandline_parser = argparse.ArgumentParser(prog=PROGRAM_NAME,
                                                 description=
                                                 "Create, update, or check the student_list file used for student sign in",
                                                 epilog="""
    Run the command with no arguments to open a file section dialog for one or
    more .csv files to be processed.
    If the  current student_list file is from the prior school year,
    it will be be moved to %s and renamed to
    student_list.csv.(date of creation)""" % BACKUP_DIRECTORY)
    commandline_parser.add_argument('-v', "--version", action='version',
                                    version=VERSION)
    commandline_parser.add_argument("-g", "--gui", dest="gui",
                                    help="Use gui for results.",
                                    action="store_true")
    opt = commandline_parser.parse_args()
    addon_files = perform_filename_dialog()
    if not addon_files:
        print (localFunctions.color_text("red",
                 "No source list files were chosen so the student list was not updated.\n"),
                                         flush=True)
        sys.exit()
    the_bad_files = []
    the_processed_files = []
    initial_student_count = 0
    UseGui = opt.gui
    the_student_database = StudentData()
    the_student_list_file = StudentListFile()
    continue_processing = True
    if the_student_list_file.is_valid():
        try:
            file_processor = SourceFileProcessor(STUDENT_LIST_FILENAME,
                                                 the_student_database)
            initial_student_count = the_student_database.insert(
                file_processor.process_file())
        except StopIteration as e:
            error_text = "updateStudentList failed because the existing " + \
                         the_student_list_file.student_list_file_name + " causes errors.\n\n" + \
                         str(e) + \
                         "\nEither edit the file to fix it or simply delete it and use all of the\n" + \
                         "source files to rebuild the entire student_list."
            ReportingText += localFunctions.color_text("red", error_text,
                                                       use_gui=UseGui)
            continue_processing = False
    if continue_processing:
        for filename in addon_files:
            if filename == '':
                continue
            file_processor = SourceFileProcessor(filename, the_student_database)
            if file_processor.valid_file():
                try:
                    the_student_database.insert(file_processor.process_file())
                    the_processed_files.append(filename)
                except StopIteration as e:
                    ReportingText += localFunctions.color_text("red", str(e),
                                                               use_gui=UseGui)
            else:
                the_bad_files.append(filename)
        the_student_list_file.create(the_student_database.get_data())
    if UseGui:
        gui_report_result(the_bad_files, the_processed_files, the_student_list_file)
    else:
        print_result(the_bad_files, the_processed_files, the_student_list_file)
