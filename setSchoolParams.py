#!/usr/bin/python3
# -*- coding: utf-8 -*-


import subprocess
import localFunctions
import localFunctionsPy3
import sys

SYSTEM_CONFIGURATION_FILE = '/etc/systemCheck.conf'
SCHOOL_CONFIGURATION_FILE = '/etc/schoolParams.conf'
PROGRAM_VERSION = "0.8"
PROGRAM_NAME = "setSchoolParams"

def get_values_from_dialog(school_name, num_client_computers):
    try:
        command = """yad --form --title="My School's Info" --width=600\
            --image=gtk-about --image-on-top --focus=1 \
            --text="<b>Information About My School</b>" --text-align=center \
            --field="<b>School Name</b>" "%s" \
            --field="<b>Number of Computers</b>:NUM" %s""" \
                  % (school_name, num_client_computers)
        new_values = localFunctions.run_command(command, reraise_error=True, result_as_list=False,
                                                merge_stderr=False, print_error=False,
                                                no_stderr=False)
        school_name, num_computers_str, junk = new_values.split(
            "|")
        num_client_computers = int(float(num_computers_str))
    except subprocess.CalledProcessError:
        raise
    return school_name, num_client_computers

def get_school_info():
    school_name = localFunctionsPy3.get_conf_file_value(SCHOOL_CONFIGURATION_FILE, "School Info",
                                                     "school_name")
    num_client_computers = localFunctionsPy3.get_conf_file_value(SCHOOL_CONFIGURATION_FILE, "Lab Info",
                                                              "num_client_computers")
    return school_name, num_client_computers

def set_school_info(school_name, num_client_computers):
    localFunctionsPy3.set_conf_file_value(SCHOOL_CONFIGURATION_FILE, "School Info",
                                                     "school_name", school_name)
    localFunctionsPy3.set_conf_file_value(SCHOOL_CONFIGURATION_FILE,
                                                              "Lab Info", "num_client_computers",
                                                              num_client_computers)
    localFunctionsPy3.set_conf_file_value(SCHOOL_CONFIGURATION_FILE, "Lab Info",
                                                              "num_student_accounts",
                                                              str(int(num_client_computers) +4 ))

def in_list(l, value):
    try:
        l.index(value)
        return True
    except (ValueError, AttributeError):
        return False


if __name__ == '__main__':
    description = "Set configuration parameters about the school to use within system programs."
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, description=description,
                                  perform_parse=True)
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    school_name, num_client_computers = get_school_info()
    try:
        new_school_name, new_num_client_computers = \
            get_values_from_dialog(school_name, num_client_computers)
    except subprocess.CalledProcessError:
        sys.exit()
    set_school_info(new_school_name, str(new_num_client_computers))
