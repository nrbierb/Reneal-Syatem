#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
This file contains shared functions for several local applications.
"""

import argparse
import errno
import getpass
import logging
import os
import re
import subprocess
import sys
import string
import time
import traceback
import pwd

PROGRAM_VERSION = "1.8"
REPORTED_ERRORS = []
TestTimerStart = 0.0

UUIDS = {"primary_root": "5790d9ca-1394-4a22-9c70-ab58249f78ed",
         "primary_root_copy": "6c05c773-4b66-4bd5-ab66-fa31ac9e89ff",
         "primary_squid": "8e41b914-529a-436a-bd59-f4129e7ee2b7",
         "primary_client_home_students": "1a909698-7155-4398-a947-5aab7162268d",
         "primary_client_home": "4e21e144-4d81-4c08-b7fb-060159c61847",
         "primary_uefi": "0x1111AAAA",
         "secondary_root": "445a42ac-8fc3-40a6-b492-1aba39d9f431",
         "secondary_root_copy": "8dac8597-d07c-42b0-bf40-d6bb9ea28c87",
         "secondary_squid": "a70df590-44c8-40a2-b346-570cb51a621a",
         "secondary_client_home_student": "50bd12b2-0607-4878-8c81-819fe935e39d",
         "secondary_client_home": "dfbcad8f-4c6b-435d-afdd-38e6151a7434",
         "secondary_uefi": "0x2222BBBB",
         "utility_os": "35b7486d-f7da-4f7b-8d9f-f1491e7640fa"}


def initialize_app(name, version, description, perform_parse=True):
    commandline_parser = argparse.ArgumentParser(prog=name,
                                                 description=description)
    commandline_parser.add_argument('-v', "--version", action='version',
                                    version=version)
    if perform_parse:
        commandline_parser.parse_args()
    return commandline_parser


# ----------------------------------------------------------------------
def run_command(command, reraise_error=False, result_as_list=True,
                merge_stderr=True, print_error=False, no_stderr=False):
    """
    Run the command and return a list of the lines in the response.
    If the command fails then the exception subprocess.CalledProcessError.
    This should be handled by the caller.
    """
    try:
        if no_stderr:
            output = subprocess.check_output(command, shell=True,
                                             universal_newlines=True,
                                             stderr=subprocess.DEVNULL)
        elif merge_stderr:
            output = subprocess.check_output(command, shell=True,
                                             universal_newlines=True,
                                             stderr=subprocess.STDOUT)
        else:
            output = subprocess.check_output(command, shell=True,
                                             universal_newlines=True)
    except subprocess.CalledProcessError as e:
        output = e.output
        if str(e.output):
            e.output = "--Command %s failed with error: %s" % (command, e.output)
        else:
            e.output = "--Command %s failed." % command
        if print_error:
            print(e.output)
        if reraise_error:
            raise
    result = output
    if result_as_list:
        result = str(output).splitlines()
    return result


# ----------------------------------------------------------------------
def command_run_successful(command):
    """
    Run a single command and test for correct completion
    """
    result = True
    try:
        subprocess.check_output(command, shell=True,
                                universal_newlines=True,
                                stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        result = False
    return result


# ----------------------------------------------------------------------
def error_exit(message, exit_code=1, quiet=False, use_gui=False, show_color=False):
    """
    Perform an immediate exit from the program
    after printing the message on stderr.
    """
    if not quiet:
        if use_gui:
            gui_report_error(message)
        else:
            if show_color:
                message = color_text("red", message)
            print(message)
    sys.exit(exit_code)


def gui_report_error(error_text):
    display_text = color_text("red", error_text, bold=True, use_gui=True)
    command = "zenity --error --text='%s'" % display_text
    command_run_successful(command)


def confirm_root_user(program_name, use_gui=False):
    if getpass.getuser() != "root":
        error_exit(
            'This command must be run as the root user.\n Use "sudo %s"'
            % program_name, errno.EPERM, use_gui=use_gui)


def cleanup_string(original_string, title_case=False,
                   further_remove_characters=".,", join_character="",
                   replace_enya=True, remove_leading_numbers=False):
    """
    Change unusable special characters to similar ascii.
    Remove most punctuation characters
    :param original_string:
    :param title_case: Convert to title case if true
    :param further_remove_characters: other characters that should not be in string
    :param join_character: the character used to connect the parts of the string after
            cleanup
    :param replace_enya: replace the enya with "n" or "N"
    :param remove_leading_numbers: Names may be prefixed with leading numbers
            that should be removed but student group names may have leading numbers
    :return: processed string
    """
    try:
        enyas = u'ñÑ'
        legal_characters = string.printable + enyas
        # remove all garbage characters
        clean_string = ''.join(
            [s for s in original_string if s in legal_characters])
        clean_string = clean_string.strip()
        # if this is just a number for a grade, return it immediately
        if clean_string.isdigit():
            return clean_string
        if remove_leading_numbers:
            clean_string = clean_string.strip("0123456789.")
        # Always remove unwanted stuff at both ends
        clean_string = clean_string.strip(".-")
        clean_string = clean_string.strip()
        target_characters = '!"#$%&\'()*+/:;<=>?@[\\]^`{|}~' + \
                            further_remove_characters
        replacement_characters = " " * len(target_characters)
        if replace_enya:
            target_characters += enyas
            replacement_characters += 'nN'
        cleanup_translator = str.maketrans(target_characters,
                                           replacement_characters)
        clean_string = clean_string.translate(cleanup_translator)
        if title_case:
            clean_string = clean_string.title()
        clean_string = join_character.join(clean_string.split())
        return clean_string.strip()
    except ValueError:
        return "---"


def natural_sort_key(key_text):
    """ Create a sort key for a sort like humans expect. Derived from example in
    "https://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python"
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    key_str = [convert(c) for c in re.split('([0-9]+)', key_text)]
    return key_str

def sort_nicely(target_list, return_copy=False):
    """ Sort the given list in the way that humans expect.
    This is a modified version of an example in
    "https://stackoverflow.com/questions/2669059/how-to-sort-alpha-numeric-set-in-python"
    """
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    if return_copy:
        return sorted(target_list, key=alphanum_key)
    else:
        return target_list.sort(key=alphanum_key)


def get_all_active_users_by_class():
    """
    This will return a list of usernames that have running processes -- ie.
    logged in users and system processes
    :return: a dictionary of 3 lists: "normal users", "system users" and
        "all users"
    """
    ps_list = run_command('ps -eo user:40,gid --no-headers')
    ps_split_list = [n.split() for n in set(ps_list)]
    normal_users = [n[0] for n in ps_split_list if int(n[1]) > 999
                    and n[0] != "root"]
    system_users = [n[0] for n in ps_split_list if int(n[1]) < 10000]
    all_users = normal_users + system_users
    return {"all users": all_users, "normal users": normal_users,
            "system users": system_users}


def color_text(color, text, bold=True, use_gui=False):
    """
    Very primitive with just red, blue, and green.
    This just returns the string with the wrapper ansi codes.
    :param color:
    :param text:
    :param bold:
    :param use_gui
    :return:
    """
    if use_gui:
        if bold:
            text = "<b>" + text + "</b>"
        text = '<span color="%s">%s</span>' % (color, text)
    else:
        colors = {
            "red": "\033[38;5;1m",
            "green": "\033[38;5;28m",
            "blue": "\033[38;5;27m",
            "purple": "\033[38;5;93m",
            "Black": '\033[0;30m',
            "DarkRed": '\033[0;31m',
            "DarkGreen": '\033[0;32m',
            "DarkYellow": '\033[0;33m',
            "DarkBlue": '\033[0;34m',
            "DarkMagenta": '\033[0;35m',
            "DarkCyan": '\033[0;36m',
            "Gray": '\033[0;37m',
            "DarkGray": '\033[1;90m',
            "Red": '\033[1;91m',
            "Green": '\033[1;92m',
            "Yellow": '\033[1;93m',
            "Blue": '\033[1;94m',
            "Magenta": '\033[1;95m',
            "Cyan": '\033[1;96m',
            "White": '\033[1;97m'
        }
        bold_leader = "\033[01m"
        reset = "\033[0m"
        try:
            if bold:
                leader = bold_leader + colors[color]
            else:
                leader = colors[color]
            text = leader + text + reset
        except KeyError:
            pass
    return text


def findall_in_file(filename, search_re, reraise_error=False):
    """
    Open filename readonly and create a list of all lines that matched the
    regular expression
    :param filename:
    :param search_re:
    :param reraise_error:
    :return list of matching lines:
    """
    groups_values = []
    try:
        with open(filename, "r") as f:
            file_text = f.read()
            match_groups = re.findall(search_re, file_text, re.S + re.M)
            if match_groups:
                for m in match_groups:
                    groups_values.append(m)
    except OSError:
        if reraise_error:
            raise
        else:
            pass
    return groups_values


def replace_line_in_file(in_filename, out_filename, re_lineid,
                         replacement_line, reraise_error=False):
    """
    Open the file in_filename readonly, scan line by line and replacing any line that has
    a motch to the lineid regular expression with the replacement line. Close in_filename.
    Then open the our_filename for write, and write the modified text. in_filename
    and out_filename can be the same so the the file is overwritten in place.
    :param in_filename:
    :param out_filename
    :param re_lineid:
    :param replacement_line:
    :param reraise_error:
    :return:
    """
    try:
        id_re = re.compile(re_lineid)
        with open(in_filename, "r") as f:
            lines = f.read().splitlines()
        count = 0
        for i in range(len(lines)):
            if id_re.match(lines[i]):
                lines[i] = replacement_line
                count += 1
        with open(out_filename, "w") as f:
            f.write('\n'.join(lines))
        return count
    except OSError:
        if reraise_error:
            raise
        else:
            return -1


def copy_file(original_file, new_file):
    """
    Use the standard linx copy command to assure that all attributes
    are copied. DO not catch exception so that it will be carried to
    caller
    :param original_file:
    :param new_file:
    :return:
    """
    command = '/bin/cp -p %s %s' % (original_file, new_file)
    result = run_command(command, reraise_error=True, result_as_list=False,
                         merge_stderr=True, print_error=False, no_stderr=False)
    return result


def generate_exception_string(err_val):
    """
    Generate a detailed error message for an exception.
    :param err_val:
    :return:
    """
    error_string = str(err_val) + "\n"
    err_info = sys.exc_info()
    if err_info:
        tb = err_info[2]
        for line in traceback.format_tb(tb, 1):
            error_string += (line + "\n")
        traceback.clear_frames(tb)
    return error_string


def school_params(configuration_filename="/etc/schoolParams.conf"):
    """
    Use the school configuration file to provide complex values used in
    multiiple programs.
    The default values of "Tanzania", Secondary", and "Secondary School" are
    set as backup it the configuration file is missing.
    example /etc/schoolParams.conf file
    Country = Tanzania
    SchoolType = Secondary
    SchoolName = My Fine School
    """
    params_dict = {"Country": "Tanzania", "SchoolType": "Secondary",
                   "SchoolName": "", "NumStudentAccounts": 30}
    parser_re = re.compile(r'^\s*(?P<name>[a-zA-z]+)\s*=\s*(?P<value>.+)')
    try:
        f = open(configuration_filename, 'r')
        for line in f.readlines():
            match = parser_re.match(line)
            try:
                if match:
                    name_str = match.group("name").lower()
                    if name_str.startswith("cou"):
                        params_dict["Country"] = match.group("value")
                    elif name_str.find("type") != -1:
                        params_dict["SchoolType"] = match.group("value")
                    elif name_str.find("name") != -1:
                        params_dict["SchoolName"] = match.group("value")
                    elif name_str.startswith("numst"):
                        try:
                            params_dict["NumStudentAccounts"] = \
                                int(match.group("value"))
                        except ValueError:
                            pass
            except IndexError:
                pass
    except (OSError, re.error):
        pass
    # Cleanup values read from file by using minimal amount of text from
    # the front of the string
    if params_dict["Country"].lower().startswith("phi"):
        params_dict["Country"] = "Philippines"
    else:
        params_dict["Country"] = "Tanzania"
    if params_dict["SchoolType"].lower().startswith("inte"):
        params_dict["SchoolType"] = "Integrated"
    elif params_dict["SchoolType"].lower().startswith("col"):
        params_dict["SchoolType"] = "College"
    elif params_dict["SchoolType"].lower().startswith("pri"):
        params_dict["SchoolType"] = "Primary"
    else:
        params_dict["SchoolType"] = "Secondary"
    if not params_dict["SchoolName"]:
        params_dict["SchoolName"] = params_dict["SchoolType"] + " School"
    if params_dict["Country"] == "Tanzania":
        params_dict["StudentGroupName"] = "Stream"
        params_dict["StudentGroupNameRE"] = 'ream'
        params_dict["SchoolYearStartMonth"] = 1
        params_dict["SchoolYearEndMonth"] = 11
        params_dict["LastNameColumnTitle"] = "Surname"
        if params_dict["SchoolType"] == "Secondary":
            params_dict["ClassYearName"] = "Form Level"
            params_dict["ClassYearNameRE"] = "orm"
            # values repeated for mapping from YearListMatch
            params_dict["YearList"] = ["Form One", "Form Two",
                                       "Form Three", "Form Four",
                                       "Form Five", "Form Six",
                                       "Form One", "Form Two",
                                       "Form Three", "Form Four",
                                       "Form Five", "Form Six"]
            params_dict["RnYearList"] = ["Form One", "Form Two",
                                         "Form Three", "Form Four",
                                         "Form Five", "Form Six"]
            # single values list to be used in display lists
            params_dict["DisplayYearList"] = ["Form One", "Form Two",
                                              "Form Three", "Form Four",
                                              "Form Five", "Form Six"]
            params_dict["YearListMatch"] = ["ne", "wo", "re", "ur", "ve", "ix",
                                            "1", "2", "3", "4", "5", "6"]
            params_dict["RnYearListMatch"] = ["i", "ii", "iii", "iv", "v", "vi"]
        else:
            params_dict["ClassYearName"] = "Standard Level"
            params_dict["ClassYearNameRE"] = "dard"
            params_dict["YearList"] = ["Standard One", "Standard Two",
                                       "Standard Three", "Standard Four",
                                       "Standard Five", "Standard Six",
                                       "Standard Seven",
                                       "Standard One", "Standard Two",
                                       "Standard Three", "Standard Four",
                                       "Standard Five", "Standard Six",
                                       "Standard Seven"]
            params_dict["DisplayYearList"] = ["Standard One", "Standard Two",
                                              "Standard Three", "Standard Four",
                                              "Standard Five", "Standard Six",
                                              "Standard Seven"]
            params_dict["YearListMatch"] = ["ne", "wo", "ee", "ur", "iv", "ix",
                                            "en",
                                            "1", "2", "3", "4", "5", "6", "7"]
            # roman numerals not used in Philippines
            params_dict["RnYearList"] = []
            params_dict["RnYearListMatch"] = []
    elif params_dict["SchoolType"] == "College":
        params_dict["StudentGroupName"] = "Section"
        params_dict["StudentGroupNameRE"] = "ecti"
        params_dict["ClassYearName"] = "Class Year"
        params_dict["ClassYearNameRE"] = "ear"
        params_dict["YearList"] = ["First Year", "Second Year", "Third Year",
                                   "Fourth Year",
                                   "First Year", "Second Year", "Third Year",
                                   "Fourth Year"]
        params_dict["DisplayYearList"] = ["First Year", "Second Year",
                                          "Third Year", "Fourth Year"]
        params_dict["YearListMatch"] = ["rs", "ec", "hi", "rt",
                                        "1", "2", "3", "4"]
        params_dict["SchoolYearStartMonth"] = 8
        params_dict["SchoolYearEndMonth"] = 6
    else:
        # Country = Philippines
        params_dict["ClassYearName"] = "Grade"
        params_dict["ClassYearNameRE"] = "rad"
        params_dict["StudentGroupName"] = "Section"
        params_dict["StudentGroupNameRE"] = "ecti"
        params_dict["LastNameColumnTitle"] = "Last Name"
        if params_dict["SchoolType"] == "Primary":
            params_dict["YearList"] = ["Grade 1", "Grade 2", "Grade 3",
                                       "Grade 4", "Grade 5",
                                       "Grade 6"]
            params_dict["DisplayYearList"] = params_dict["YearList"]
            params_dict["YearListMatch"] = ["1", "2", "3", "4", "5", "6"]
        elif params_dict["SchoolType"] == "Integrated":
            params_dict["YearList"] = ["Grade 1", "Grade 2", "Grade 3",
                                       "Grade 4", "Grade 5",
                                       "Grade 6", "Grade 7",
                                       "Grade 8", "Grade 9",
                                       "Grade 10", "Grade 11",
                                       "Grade 12"]
            params_dict["DisplayYearList"] = params_dict["YearList"]
            params_dict["YearListMatch"] = ["1", "2", "3", "4", "5", "6",
                                            "7", "8", "9", "10", "11", "12"]
        else:  # level Secondary -- the most common
            params_dict["YearList"] = ["Grade 7", "Grade 8", "Grade 9",
                                       "Grade 10",
                                       "Grade 11", "Grade 12"]
            params_dict["DisplayYearList"] = params_dict["YearList"]
            params_dict["YearListMatch"] = ["7", "8", "9", "10", "11", "12"]
        params_dict["SchoolYearStartMonth"] = 6
        params_dict["SchoolYearEndMonth"] = 3
    params_dict["LowerCaseStudentGroupName"] = params_dict[
        "StudentGroupName"].lower()
    return params_dict


def add_error_report(error_string):
    global REPORTED_ERRORS
    REPORTED_ERRORS.append(error_string)


def get_reported_errors():
    global REPORTED_ERRORS
    report_string = ""
    for err in REPORTED_ERRORS:
        report_string = "%s%s\n" % (report_string, err)
    return report_string


def starttimer():
    """
    Trivial  very lightweight timer for misc purposes.
    There is only one to be used with starttimer() and stoptimer()
    :return:
    """
    global TestTimerStart
    TestTimerStart = time.time()


def stoptimer():
    """
    Second part of timer. Be sure to call starttimer() first.
    It will print the time in ms
    :return:
    """
    total_time = 1000.0 * (time.time() - TestTimerStart)
    print("+++++++++++++ elapsed: %f.2 ms" % total_time)


def convert_to_readable(number, storage_size=True, convert_to_storage_size=False, always_show_fraction=False):
    """
    Convert an integer to a human readable text string. If storage size is True,
    then number is in 1 K binary and scaled by powers of 2.
    If storage False, the number is unscaled and scaled by powers of 10.
    """
    sign = ""
    if number < 0:
        number = -number
        sign = "-"
    if convert_to_storage_size and not storage_size:
        number = number / 2**10
        storage_size = True
    if storage_size:
        # storage size always reported in KB and using powers of two
        conversion_list = [(2 ** 30, "TB"), (2 ** 20, "GB"), (2 ** 10, "MB"), (1, "KB")]
    else:
        conversion_list = [(1e12, "Tb"), (1e9, "Gb"), (1e6, "Mb"), (1e3, "Kb"), (1, "  ")]
    try:
        for scaler, suffix in conversion_list:
            if number >= scaler:
                if scaler > 1 or always_show_fraction:
                    scaled = round(number / scaler, 1)
                    return "%s%.1f %s" % (sign, scaled, suffix)
                else:
                    scaled = round(number / scaler, 0)
                    return "%s%d %s" % (sign, scaled, suffix)
    except (ValueError, TypeError):
        return ""


def convert_from_readable(num_string):
    units = {"B": 1, "K": 2 ** 10, "M": 2 ** 20, "G": 2 ** 30, "T": 2 ** 40,
             "b": 1, "k": 1e3, "m": 1e6, "g": 1e9, "t": 1e12}
    try:
        num_string = num_string.strip().upper() + "B"
        num, extension = re.findall(r'^([\d.]+)\s*(\w)', num_string)[0]
        return float(num) * units[extension]
    except (KeyError, TypeError):
        return 0

def create_timestamped_logger(logger_name, log_file_name, level = logging.INFO):
    logger = None
    try:
        if log_file_name:
            logger = logging.getLogger(logger_name)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file_name, maxBytes=200000, backupCount=5)
            file_handler.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
            logger.setLevel(level)
            logger.addHandler(file_handler)
    except Exception:
        pass
    return logger


def get_filesystem_space_used(mount_name):
    command = '/bin/df "%s"' %mount_name
    kb_used = 0
    try:
        df_data = run_command(command, reraise_error=True, result_as_list=True,
                              merge_stderr=False)
        columns = df_data[1].split()
        kb_used = int(columns[2])
    except (subprocess.CalledProcessError, ValueError, IndexError, TypeError):
        pass
    return kb_used


def change_in_filesystem_size(mount_name, initial_size, size_now = 0):
    if not size_now:
        size_now = get_filesystem_space_used(mount_name)
    delta = size_now - initial_size
    change_text = "'%s' did not change in size" % mount_name
    if delta < 0:
        change_text = "'%s' size has decreased by %s." \
                      % (mount_name, convert_to_readable(-delta, storage_size=True))
    elif delta > 0:
        change_text = "'%s' size has increased by %s." \
                      % (mount_name, convert_to_readable(delta, storage_size=True))
    return change_text, delta


def get_directory_size(directory):
    try:
        command = "du -s --one-file-system %s" % directory
        du_result = run_command(command, reraise_error=True, result_as_list=False,
                                merge_stderr=False)
        kb_size = du_result.split()[0]
        return int(kb_size)
    except (subprocess.CalledProcessError, ValueError):
        return 0


def convert_users_to_uids(user_name_list):
    user_uids = []
    user_gids = {}
    for user in user_name_list:
        try:
            name = user.split()[0]
            user_uids.append(pwd.getpwnam(name).pw_uid)
            gid = pwd.getpwnam(name).pw_gid
            count = user_gids.get(gid, 0) + 1
            user_gids[gid] = count
        except (KeyError, IndexError, AttributeError):
            pass
    return user_uids, user_gids


def get_logged_in_users():
    user_name_list = run_command("/usr/bin/who -s", no_stderr=True)
    user_uids, user_gids = convert_users_to_uids(user_name_list)
    return user_uids, user_gids


def user_is_active(uid):
    active_users, active_groups = get_logged_in_users()
    return uid in active_users


def get_mounted_filesystems(ltspfs_only = False):
    """
    Return a list of fiesystems that are mounts. Any error in this functionget
    (probaby CalledProcessError) must be handled in calling function to assure
    correct action if list is invalid
    :return:
    """
    mounted_fs = []
    mounts = run_command('/bin/findmnt -l', no_stderr=True,
                         reraise_error=True)
    for mnt in mounts:
        try:
            values = mnt.split()
            if values[1].startswith("ltspfs"):
                mounted_fs.append(values[0])
            elif values[1].startswith("/dev/") and not ltspfs_only:
                mounted_fs.append(values[0])
        except (IndexError, TypeError):
            pass
    return mounted_fs


def determine_active_filesystem_partitions():
    """
    Map the currently mounted filesystems to the functional partitions
    :return:
    """
    global UUIDS
    command = 'lsblk -o"MOUNTPOINT,UUID" |grep "/"'
    try:
        result = run_command(command, result_as_list=True, reraise_error=True)
    except subprocess.SubprocessError as e:
        return {}
    filesystem_uuid_mapping = {}
    for line in result:
        key, value = line.strip().split()
        filesystem_uuid_mapping[key] = value
    partition_mapping = {v: k for k, v in UUIDS.items()}
    filesystem_partname_map = {filesystem: partition_mapping[filesystem_uuid_mapping[filesystem]]
                               for
                               filesystem in filesystem_uuid_mapping.keys()}
    return filesystem_partname_map

def get_disk_devices():
    """
    Get primary and backup disk device names
    :return:
    """
    primary_device = ""
    secondary_device = ""
    try:
        with open("/etc/fstab", "r") as f:
            fstab_text = f.read()
        uuid_mapping_list = re.findall(r'UUID=(\S+)\s+(\S+)\s', fstab_text)
        uuid_mapping = {}
        for pair in uuid_mapping_list:
            uuid_mapping[pair[1]] = pair[0]
        lsblk_text = run_command("lsblk -l -o NAME,UUID", result_as_list=False, reraise_error= True)
        primary_re = "(\S+)\d\s+" + uuid_mapping["/"]
        primary_device_l = re.findall(primary_re, lsblk_text)
        primary_device = primary_device_l[0].rstrip("p") if primary_device_l else ""
        secondary_re = "(\S+)\d\s+" + uuid_mapping["/OS_Copies/MainServerD2"]
        secondary_device_l = re.findall(secondary_re,lsblk_text)
        secondary_device = secondary_device_l[0] if secondary_device_l else ""
    except (IOError, IndexError, KeyError, re.error, subprocess.SubprocessError):
        pass
    return primary_device, secondary_device


def temp_mount_primary_partitions(temp_partition_mount_dirs):
    """
    Mount the primary set of partitions on a different set of
    mountpoints to allow access even if they are not aready mounted.
    Perform fsck if not already mounted.
    This is generally for filesystem maintenance actions.
    :param temp_partition_mount_dirs: a dictionary of partition_name:mount_dir
    :return:
    """
    global UUIDS
    temp_mounted_dirs = {}
    for partition in ("primary_root", "primary_client_home_students", "primary_client_home"):
        temp_mounted_dirs[partition] = ""
        uuid = UUIDS[partition]
        command = "e2fsck -f UUID=%s" % uuid
        command_run_successful(command)
        try:
            if not os.path.isdir(temp_partition_mount_dirs[partition]):
                os.mkdir(temp_partition_mount_dirs[partition])
            command = "mount UUID=%s %s" % (uuid, temp_partition_mount_dirs[partition])
            run_command(command, reraise_error=True)
            temp_mounted_dirs[partition] = temp_partition_mount_dirs[partition]
        except (OSError, subprocess.SubprocessError):
            pass
    return temp_mounted_dirs

