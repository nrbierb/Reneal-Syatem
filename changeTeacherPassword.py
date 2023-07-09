#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Use simple dialogs for gui based password change for a teacher's user account
"""

import localFunctions
import os
import re
import sys
import tempfile

ERROR_HEADER = ""
DEBUG = False
PROGRAM_NAME = "changeTeacherPassword.py"
VERSION = "0.9"


def get_account_names(groupid):
    """
    extract the user accounts from /etc/passwd for specified group
    The function creates a dictionary with the keys a combination of the
    account name and the name of the user and the value just the account name
    :param groupid:
    :return:
    """
    global ERROR_HEADER
    ERROR_HEADER = "Failed to read password file"
    accounts_dict = {}
    re_splitter = \
        re.compile(
            r'^(?P<aname>[^:]+):[^:]+:*\d+:(?P<gid>\d+):(?P<uname>[^,]*)[^:]+:(?P<home>[^:]*)')
    passwd = open("/etc/passwd", "r")
    for line in passwd:
        match_obj = re_splitter.match(line)
        if match_obj:
            values = match_obj.groupdict()
            if values["gid"] == groupid:
                combined = values["aname"] + " -- " + values["uname"].title()
                accounts_dict[combined] = values["aname"]
    return accounts_dict


def display_new_password_form(accounts_dict):
    global ERROR_HEADER
    ERROR_HEADER = "Unable to display or read new password form"
    result = {"name": "", "pw": "", "pw2": ""}
    names = list(accounts_dict.keys())
    localFunctions.sort_nicely(names)
    names_arg = "|".join(names)
    command = """zenity --forms --title "Change Teacher's Password" \\
    --text "Change Password\nMinimum 6 characters" --separator '\001' --add-combo "Teacher Name" --combo-values "%s" \\
    --add-entry "New Password" --add-entry "Repeat Password" """ % names_arg
    raw_result = localFunctions.run_command(command, reraise_error=False,
                                            result_as_list=False,
                                            merge_stderr=False,
                                            print_error=False)
    if not raw_result:
        password_unchanged("Change canceled")
    result["name"], result["pw"], result["pw2"] = raw_result.strip('\n').split(
            '\001')
    return check_form_completion(result, accounts_dict)


def check_form_completion(form_result, accounts_dict):
    """
    Check that a user has been chosen and that both password fields have been
    entered.
    :param form_result:
    :param accounts_dict:
    :return:
    """
    global ERROR_HEADER
    ERROR_HEADER = "Failed form input validation."
    if form_result["name"] not in list(accounts_dict.keys()):
        text = "You must choose the account.\n\t\tRetry or cancel."
        colored_text = localFunctions.color_text("red", text,
                        bold = True, use_gui = True)
        command = """zenity --title "Incomplete Entry" --error --text '%s' """ \
                  % colored_text
        localFunctions.command_run_successful(command)
        form_result = display_new_password_form(accounts_dict)
    return form_result


def confirm_password(form_result):
    """
    Check that passwords are the same.
    If not display retry form and get again
    """
    global ERROR_HEADER
    ERROR_HEADER = "Unable to confirm password"
    title = ""
    text = ""
    if not (form_result["pw"] and form_result["pw2"]):
        text = 'You must fill in both password fields\n\t'
        title = 'Passwords Required.'
    elif form_result['pw'] != form_result['pw2']:
        title = "Passwords Don't Match"
        text = 'Passwords do not match    \n\t'
    elif len(form_result['pw']) < 6 :
        title = 'Password Too Short'
        text = 'Password must be at least 6 characters long.\n\t'
    if text:
        c_text = localFunctions.color_text("red", text,
                                               bold=True, use_gui=True)
        color_name = localFunctions.color_text("blue", form_result["name"],
                                               bold=True, use_gui=True)
        color_text = c_text + color_name
        command = """zenity --forms --title "%s" \\
            --text '%s' --separator '\001' --add-entry "New Password" \\
            --add-entry "Repeat Password" """ % (title, color_text)
        raw_result = localFunctions.run_command(command, reraise_error=False,
                                                result_as_list=False,
                                                merge_stderr=False,
                                                print_error=False)
        if not raw_result:
            password_unchanged("Change canceled.")
        result = {"name": form_result["name"]}
        resarray = raw_result.split('\001')
        result["pw"] = resarray[0].strip()
        result["pw2"] = resarray[1].strip()
        form_result = confirm_password(result)
    return form_result


def confirm_change(display_name):
    """
    Show Question bo to correct information.
    :param display_name:
    :return:
    """
    global ERROR_HEADER
    ERROR_HEADER = "Confirm change dialog could not be shown or read"
    parts = display_name.split(" ", 2)
    aname = localFunctions.color_text("blue", parts[0], bold=True,
                                      use_gui=True)
    if len(parts) > 2:
        uname = localFunctions.color_text("blue", parts[2],
                                          bold=True, use_gui=True)
    else:
        uname = " "
    text = "You will change the password for:\n\nAccount Name: %s\n" % aname + \
           "User: %s\n\nIs this correct?" % uname
    command = 'zenity --question --text "%s"' % text
    if not localFunctions.command_run_successful(command):
        password_unchanged("Change canceled")


def set_password(account_name, password):
    """
    Set the user password for the account name using the linus chpasswd command.
    The input for the command is stored in a temporary file so that special
    characters in the password will not be corrupted in the bash shell.
    :param account_name: `````````````````
    :param password:
    :return:
    """
    global ERROR_HEADER
    ERROR_HEADER = "Set the password for '%s'" % account_name
    tmpfile = tempfile.mktemp()
    f = open(tmpfile, "w")
    f.write("%s:%s" % (account_name, password))
    f.close()
    command = "chpasswd < %s" % tmpfile
    if localFunctions.command_run_successful(command):
        os.remove(tmpfile)
        text = "Password changed for '%s'" % account_name
        color_text = localFunctions.color_text("green", text,
                                               bold=True, use_gui=True)
        localFunctions.command_run_successful(
            "zenity --title='Successful' --info --text '%s'" % color_text)
    else:
        os.remove(tmpfile)
        report_error("Password change command failed", None)


def password_unchanged(reason):
    global ERROR_HEADER
    ERROR_HEADER = "Password unchanged dialog could not be shown."
    text = "All passwords unchanged:\n    %s" % reason
    color_text = localFunctions.color_text("purple", text, bold=True,
                                           use_gui=True)
    localFunctions.command_run_successful(
        "zenity --title 'No Change' --info --text '%s'"
        % color_text)
    sys.exit(0)


def report_error(leader_text="", error=None):
    if error:
        if DEBUG:
            error_text = localFunctions.generate_exception_string(error)
        else:
            error_text = str(error)
    else:
        error_text = ""
    report_text = "The change of password failed.\n\n  %s\n  %s\n\nPlease retry one more time." % (
        leader_text, error_text)
    report_text = report_text.replace('"', '`').replace('<', '[').replace('>',
                                                                          ']')
    colored_text = localFunctions.color_text("red", report_text,
                                             bold=True, use_gui=True)
    command = """zenity --title "Password Change Failed" --error --text "%s" """ \
              % colored_text
    localFunctions.command_run_successful(command)
    sys.exit(1)


if __name__ == '__main__':
    try:
        localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
        parser = localFunctions.initialize_app(PROGRAM_NAME, VERSION,
                                               "GUI program to change teacher passwords",
                                               False)
        parser.add_argument("--mac", dest="mac_server",
                            help="The server is used for a mac lab with workstations.",
                            action="store_true")
        opt = parser.parse_args()
        mac_server = opt.mac_server
        account_dict = get_account_names("2000")
        fm_result = display_new_password_form(account_dict)
        if fm_result["name"]:
            confirmed_result = confirm_password(fm_result)
            if confirmed_result["pw"]:
                confirm_change(confirmed_result["name"])
                account_name = account_dict[confirmed_result["name"]]
                set_password(account_name, confirmed_result["pw"])
                if mac_server:
                    print("Updating workstations.")
                    # complicated use of sudo with -i flag required by gpg command
                    # in an internal program
                    ERROR_HEADER = "Update the workstation passwords"
                    command_text = "sudo -i /usr/local/share/apps/updateWorkstationPasswords.sh"
                    localFunctions.run_command(command_text, reraise_error=True)
            else:
                report_error("A blank password is not allowed", None)
    except Exception as err:
        report_error(ERROR_HEADER, err)
