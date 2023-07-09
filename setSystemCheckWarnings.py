#!/usr/bin/python3
# -*- coding: utf-8 -*-


import subprocess
import localFunctions
import localFunctionsPy3
import sys

SYSTEM_CONFIGURATION_FILE = '/etc/systemCheck.conf'
PROGRAM_VERSION = "0.8"
PROGRAM_NAME = "setSystemCheckWarnings"

def get_values_from_dialog(check_internet, lab1_inactive, lab2_inactive):
    if check_internet:
        internet_choice = '"Yes"\!"No"'
    else:
        internet_choice = '"No"\!"Yes"'
    if lab1_inactive:
        lab1_choice = '"Failed (Do not check)"\!"Working (Normal state)"'
    else:
        lab1_choice = '"Working (Normal state)"\!"Failed (Do not check)"'
    if lab2_inactive:
        lab2_choice = '"Failed (Do not check)"\!"Working (Normal state)"'
    else:
        lab2_choice = '"Working (Normal state)"!"Failed (Do not check)"'
    try:
        command = """yad --form --title="System Check Warnings" --width=600\
            --image=gtk-about --image-on-top --focus=1 \
            --text="<b>Control System Check Warnings</b>" --text-align=center \
            --field="<b>Internet Connected</b>:CB" %s \
            --field="<b>Lab Interface 1</b>:CB" %s \
            --field="<b>Lab Interface 2</b>:CB" %s""" \
                  % (internet_choice, lab1_choice, lab2_choice)
        new_values = localFunctions.run_command(command, reraise_error=True, result_as_list=False,
                                                merge_stderr=False, print_error=False,
                                                no_stderr=False)
        internet_active_str, lab1_inactive_str, lab2_inactive_str, junk = new_values.split(
            "|")
        check_internet = (internet_active_str == "Yes")
        lab1_inactive = (lab1_inactive_str == "Failed (Do not check)")
        lab2_inactive = (lab2_inactive_str == "Failed (Do not check)")
    except subprocess.CalledProcessError:
        raise
    return check_internet, lab1_inactive, lab2_inactive

def in_list(l, value):
    try:
        l.index(value)
        return True
    except (ValueError, AttributeError):
        return False

def get_systemCheck_configuration():
    internet_available = localFunctionsPy3.get_conf_file_value(SYSTEM_CONFIGURATION_FILE, "Internet",
                                                            "internet_available",
                                                            boolean_value=True)
    inactive_interfaces = localFunctionsPy3.get_conf_file_value(SYSTEM_CONFIGURATION_FILE,
                                                             "Network Interfaces",
                                                             "unused_interfaces", list_value=True)
    lab1_inactive = in_list(inactive_interfaces, "lab1")
    lab2_inactive = in_list(inactive_interfaces, "lab2")
    return internet_available, lab1_inactive, lab2_inactive


def set_systemCheck_configuration(check_internet, lab1_inactive, lab2_inactive):
    localFunctionsPy3.set_conf_file_value(SYSTEM_CONFIGURATION_FILE, "Internet", "internet_available",
                                       str(check_internet))
    inactive_interfaces = []
    if not check_internet:
        inactive_interfaces.append("internet")
    if lab1_inactive:
        inactive_interfaces.append("lab1")
    if lab2_inactive:
        inactive_interfaces.append("lab2")
    inactive_interfaces_str = ",".join(inactive_interfaces)
    localFunctionsPy3.set_conf_file_value(SYSTEM_CONFIGURATION_FILE, "Network Interfaces",
                                       "unused_interfaces",
                                       inactive_interfaces_str)


if __name__ == '__main__':
    description = "Set information about the server and lab to control unnecessary warnings."
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, description=description,
                                  perform_parse=True)
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    check_internet, lab1_inactive, lab2_inactive = get_systemCheck_configuration()
    try:
        new_check_internet, new_lab1_inactive, new_lab2_inactive = \
            get_values_from_dialog(check_internet, lab1_inactive, lab2_inactive)
    except subprocess.CalledProcessError:
        sys.exit()
    set_systemCheck_configuration(new_check_internet, new_lab1_inactive, new_lab2_inactive)
