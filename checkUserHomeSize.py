#!/usr/bin/env python3
# coding:utf-8
# Author:   --<N. Bierbaum>
# Purpose: 
# Created: 02/28/2013

"""
Check the size of the users trash area to determine
those users that need to be reminded.
"""

import argparse
import glob
import operator
import os
import os.path
import re
import subprocess
import sys
import tabulate
import localFunctions
import systemCleanup
import fileManagementFunctions

TRASH_DIRECTORY = ".local/share/Trash/"
PROGRAM_DESCRIPTION = \
    """Check the filespace used by one or more users.
    With no arguments it will show the results for all teachers."""
PROGRAM_VERSION = "1.1"

StudentsList = []
TeachersList = []


def get_group_users_names(group_name):
    """
    Return the names of all users that are a member of the group
    """
    users = []
    try:
        f = os.popen('/usr/bin/getent group %s' % group_name)
        result = f.read()
        if not f.close():
            gid = result.split(':')[2]
            pwfile = open('/etc/passwd', 'r')
            for line in pwfile:
                if line.split(':')[3] == gid:
                    users.append(line.split(':')[0])
    except subprocess.CalledProcessError:
        pass
    return users


def get_directory_size(directory_full_path):
    """
    Use the linux "du -s" command to get the number of kilobytes of storage
    used in the directory and it children.
    """
    size = 0
    if os.path.isdir(directory_full_path):
        command = '/usr/bin/du -s %s' % directory_full_path
        try:
            result = localFunctions.run_command(command, reraise_error=True,
                                                result_as_list=False)
            size = int(result.split()[0])
        except subprocess.CalledProcessError:
            pass
    return size


def create_options_dict():
    """
    create a dict theat contains all of the entries for the configuration.
    All are set to default values. This external calling program should then
    change values as required before calling perform_check
    :return poptions dict:
    """
    options_dict = {'sort_media_size': False, 'sort_home_size': True,
                    'sort_trash_size': False, 'group_name': 'teacher',
                    'accounts': [], 'quiet': True, 'print_output': False,
                    'spreadsheet_form': False, 'num_accounts_shown': 0,
                    'table_indent': 0, 'max_media_size': "0K",
                    'accounts_file': None, 'output_file': None,
                    'show students': False, 'html_table': False,
                    "show_trash": True}
    return options_dict


class User:
    def __init__(self, account_name):
        self.account_name = account_name.strip()
        self.account_name_for_sort = natural_sort_key(self.account_name)
        tildename = "~" + self.account_name
        self.home_directory = os.path.expanduser(tildename)
        self.home_size = 0
        self.trash_size = 0
        self.media_size = 0
        self.media_file_count = 0
        self.valid = False
        self.fill_values()

    def fill_values(self):
        global TRASH_DIRECTORY
        if os.path.isdir(self.home_directory):
            try:
                self.home_size = get_directory_size(self.home_directory)
                trashdir = os.path.join(self.home_directory, TRASH_DIRECTORY)
                self.trash_size = get_directory_size(trashdir)
                media_files_by_class, media_size_by_class, oversize_files, self.media_size,\
                oversize_media_size = \
                    fileManagementFunctions.get_media_files(self.home_directory,
                                            {"video": 2e7, "audio": 2e6, "photo": 5e5, "other": 1})
                self.media_file_count = len(oversize_files)
                self.valid = True
            except OSError:
                pass

    def is_valid(self):
        return self.valid

    def get_account_name(self):
        return self.account_name

    def get_home_size_string(self):
        return localFunctions.convert_to_readable(self.home_size, storage_size = True)

    def get_trash_size_string(self):
        return localFunctions.convert_to_readable(self.trash_size)

    def get_media_size_string(self):
        media_size_string = ""
        if self.media_file_count:
            size = localFunctions.convert_to_readable(self.media_size / 1024)
            count = self.media_file_count
            media_size_string = "%s  (%d)" % (size, count)
        return media_size_string

    def media_size_exceeded(self, max_kb_media):
        return self.media_size > max_kb_media


class Student:
    def __init__(self, directory_path, name=""):
        self.directory = directory_path
        self.name = name
        self.directory_name_for_sort = natural_sort_key(directory_path)
        self.directory_size = 0
        self.media_size = 0
        self.media_file_count = 0
        self.valid = False
        self.fill_values()

    def fill_values(self):
        if os.path.isdir(self.directory):
            try:
                self.directory_size = get_directory_size(self.directory)
                media_files_by_class, all_media_files, self.media_size = \
                    systemCleanup.get_media_files(self.directory)
                self.media_file_count = len(all_media_files)
                self.valid = True
            except OSError:
                pass

    def is_valid(self):
        return self.valid

    def get_directory_name(self):
        return self.directory

    def get_shorter_directory_name(self):
        return os.path.relpath(self.directory, "/client_home_students")

    def get_directory_size_string(self):
        return localFunctions.convert_to_readable(self.directory_size)

    def get_media_size_string(self):
        media_size_string = ""
        if self.media_file_count:
            size = localFunctions.convert_to_readable(self.media_size / 1024)
            count = self.media_file_count
            media_size_string = "%s  (%d)" %(size, count)
        return media_size_string

    def get_student_name(self):
        if not self.name:
            dirname = os.path.basename(self.directory)
            try:
                lastname, firstname = dirname.split("-")
                self.name = firstname + " " + lastname
            except ValueError:
                self.name = dirname
        return self.name

    def media_size_exceeded(self, max_kb_media):
        return self.media_size > max_kb_media

class UserAccountChecker:

    def __init__(self, options_dict={}, user_account_list=[]):
        self.options = options_dict
        self.user_account_list = user_account_list
        self.users = []

    def create_users(self):
        for user_name in self.user_account_list:
            if not self.options["quiet"]:
                sys.stdout.write(".")
                sys.stdout.flush()
            user = User(user_name)
            if user.is_valid():
                self.users.append(user)
        if not self.options["quiet"]:
                sys.stdout.write("\n")

    def filter_excess_media_users(self, max_media_size):
        filtered_users = [user for user in self.users if
                          user.media_size> max_media_size]
        self.users = filtered_users

    def sort_users(self):
        self.users.sort(key=operator.attrgetter("account_name_for_sort"))
        if self.options["sort_home_size"]:
            self.users.sort(key=operator.attrgetter("home_size"), reverse=True)
        if self.options["sort_trash_size"]:
            self.users.sort(key=operator.attrgetter("trash_size"), reverse=True)
        if self.options["sort_media_size"]:
            self.users.sort(key=operator.attrgetter("media_size"), reverse=True)

    def process(self, max_media_size=0):
        if max_media_size:
            self.filter_excess_media_users(max_media_size)
        self.sort_users()

    def get_users(self):
        return self.users


class StudentPersonalAreaChecker:

    def __init__(self, options_dict):
        self.options = options_dict
        self.students = []

    def create_students(self):
        for directory in glob.iglob("/client_home_students/Form*/*/*"):
            student = Student(directory)
            if student.is_valid():
                self.students.append(student)

    def filter_excess_media_users(self, max_media_size):
        filtered_students = [student for student in self.students if
                             student.media_size > max_media_size]
        self.students = filtered_students

    def sort_students(self):
        self.students.sort(key=operator.attrgetter("directory_name_for_sort"))
        guest_user = Student("/client_home_students/GuestUser", "Guest User")
        if guest_user.is_valid():
            self.students.insert(0, guest_user)
        if self.options["sort_home_size"]:
            self.students.sort(key=operator.attrgetter("directory_size"), reverse=True)
        if self.options["sort_media_size"]:
            self.students.sort(key=operator.attrgetter("media_size"), reverse=True)

    def process(self, max_media_size=0):
        if max_media_size:
            self.filter_excess_media_users(max_media_size)
        self.sort_students()

    def get_students(self):
        return self.students


class PersonalAreaChecker:
    def __init__(self, options_dict):
        self.options = options_dict
        self.user_checker = None
        self.student_checker = None
        self.accounts = []
        self.output_file = sys.stdout

    def get_user_account_names(self):
        if self.options["accounts_file"]:
            try:
                accounts_file = open(self.options["accounts_file"], "r")
                accounts = accounts_file.readlines()
                accounts_file.close()
            except IOError as e:
                localFunctions.error_exit(
                    "Could not read accounts list file: %s" % e, 1,
                    self.options["accounts_file"])
        elif self.options["accounts"]:
            accounts = self.options["accounts"]
        else:
            accounts = get_group_users_names(self.options["group_name"])
        return accounts

    def setup(self):
        try:
            if not self.options["print_output"]:
                self.options["quiet"] = True
            if self.options["output_file"] and self.options["print_output"]:
                try:
                    self.output_file = open(self.options["output_file"], 'w')
                except IOError as e:
                    localFunctions.error_exit("Failed output file open: %s" % e, 1,
                                      self.options["output_file"])
            max_media_size = localFunctions.convert_from_readable(self.options["max_media_size"])
            if self.options["show_students"]:
                self.student_checker = StudentPersonalAreaChecker(self.options)
                self.student_checker.create_students()
                self.student_checker.process(max_media_size)
            else:
                accounts = self.get_user_account_names()
                self.user_checker = UserAccountChecker(self.options, accounts)
                self.user_checker.create_users()
                self.user_checker.process(max_media_size)
        except KeyError:
            localFunctions.error_exit("Options dictionary missing values")

    def output_results(self):
        try:
            if self.user_checker:
                return self.output_user_results()
            else:
                return self.output_student_results()
        except KeyError:
            localFunctions.error_exit("Options dictionary missing values")

    def create_table(self, result_data, header_line):
        html_table = tabulate.tabulate(result_data, header_line, "html")
        if int(self.options["table_indent"]):
            tabulate.PRESERVE_WHITESPACE = True
            text_table = tabulate.tabulate(result_data, header_line, "plain")
        else:
            text_table = tabulate.tabulate(result_data, header_line, "psql")
        return text_table, html_table

    def output_user_results(self):
        if self.options["spreadsheet_form"] and self.options["print_output"]:
            for user in self.user_checker.get_users():
                self.output_file.write("%s,%d,%d,%d\n" % (user.get_account_name(),
                                                     user.home_size,
                                                     user.trash_size,
                                                     user.media_size))
        else:
            indent = " " * int(self.options["table_indent"])
            lines_output = 0
            result_data = []
            if self.options["show_trash"]:
                header_line = [indent+"User Name", "Total", "Trash", "Media Files"]
            else:
                header_line = [indent+"User Name", "Total", "Media Files"]

            for user in self.user_checker.get_users():
                if self.options["num_accounts_shown"] and lines_output >= \
                        int(self.options["num_accounts_shown"]):
                    break
                if self.options["show_trash"]:
                    data_line = [indent + user.get_account_name(),
                                 user.get_home_size_string(),
                                 user.get_trash_size_string(),
                                 user.get_illegal_size_string()]
                else:
                    data_line = [indent + user.get_account_name(),
                                 user.get_home_size_string(),
                                 user.get_illegal_size_string()]
                result_data.append(data_line)
                lines_output += 1
            text_table, html_table = self.create_table(result_data, header_line)
            if self.options["print_output"]:
                self.output_file.write(text_table +'\n')
            if self.options["print_output"] and self.output_file == sys.stdout \
                    and not self.options["quiet"] and self.options["show_trash"]:
                print("If there is much trash, open a Terminal Window,\nthen type 'sudo cleanUsersTrash' \nto empty all trash for %ss"
                      % self.options["group_name"])
            return text_table, html_table, self.user_checker

    def output_student_results(self):
        if self.options["spreadsheet_form"] and self.options["print_output"]:
            for student in self.student_checker.get_students():
                self.output_file.write("%s,%d,%d\n" % (student.get_shorter_directory_name(),
                                                     student.directory_size,
                                                     student.media_size))
        else:
            indent = " " * int(self.options["table_indent"])
            header_line = [indent+"Student Name", "Student Personal Directory", "Total", "Personal Files"]
            lines_output = 0
            result_data = []
            for student in self.student_checker.get_students():
                if self.options["num_accounts_shown"] and lines_output >= \
                        int(self.options["num_accounts_shown"]):
                    break
                data_line = [indent + student.get_student_name(),
                             student.get_shorter_directory_name(),
                             student.get_directory_size_string(),
                             student.get_illegal_size_string()]
                result_data.append(data_line)
            text_table, html_table = self.create_table(result_data, header_line)
            if self.options["print_output"]:
                self.output_file.write(text_table +'\n')
            return text_table, html_table, self.user_checker

def natural_sort_key(key_text):
    """ Create a sort key for a sort like humans expect. Derived from example in
    "https://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python"
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    key_str = [convert(c) for c in re.split('([0-9]+)', key_text)]
    return key_str

def perform_check(options_dict):
    try:
        checker = PersonalAreaChecker(options_dict)
        checker.setup()
        return checker.output_results()
    except Exception:
        # allow for complete failure to isolate from calling program
        return "", "", UserAccountChecker()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION)
    parser.add_argument("-v", "--version", action="version",
                        version=PROGRAM_VERSION)
    parser.add_argument("-f", "--accounts-file", dest="accounts_file",
                        help="File that has list of account names to check")
    parser.add_argument("-o", "--output-file", dest="output_file",
                        help="File to save results.")
    parser.add_argument("-S", "--show-students", dest="show_students",
                        help="Show usage in student personal directories, not teachers",
                        action="store_true")
    parser.add_argument("-g", "--group-name", dest="group_name",
                        help="The group name of the users to be checked",
                        default="teacher")
    parser.add_argument("-s", "--spreadsheet", dest="spreadsheet_form",
                        help="output in csv form for spreadsheet",
                        action="store_true")
    parser.add_argument("-t", "--sort-trash-size", dest="sort_trash_size",
                        help="Sort by the size of the users Trash",
                        action="store_true")
    parser.add_argument("-T", "--no_show_trash", dest="show_trash",
                        help="Do not show trash column",
                        action="store_false")
    parser.add_argument("-m", "--sort-media-size", dest="sort_media_size",
                        help="Sort by the size of all of the users media files.",
                        action="store_true")
    parser.add_argument("-A", "--sort-by-name-only", dest="sort_home_size",
                        help="Sort only the users name",
                        action="store_false")
    parser.add_argument("-M", "--max-media-size", dest="max_media_size",
                        help="Flag all accounts with media greater than this",
                        default="0b")
    parser.add_argument("-q", "--quiet", dest="quiet",
                        help="Show only the result", action="store_true")
    parser.add_argument("-c", "--count", dest="num_accounts_shown",
                        help="Number of sorted top accounts shown", default=0)
    parser.add_argument("-i", "--table-indent", dest="table_indent",
                        help="spaces indentation of printed table", default=0)
    parser.add_argument("accounts", metavar="account_name", nargs="*",
                        help='Account names to be checked. Use if no accounts_file is specified with "-f"')
    parser.set_defaults(sort_trash_size=False, sort_media_size=False, print_output=True)
    opts = parser.parse_args()
    localFunctions.confirm_root_user("checkUserHomeSize")
    perform_check(vars(opts))
