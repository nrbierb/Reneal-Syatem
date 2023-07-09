#!/usr/bin/python3
"""
Create a new named teacher account. The home directory for
the teacher is created from the template in /usr/local/etc/account_templates.
"""
import argparse
import localFunctions
import os
import pexpect
import re
import subprocess
import sys

TeachersHome = "/client_home/teachers"
ExtraGroups = ["epoptes"]
PROGRAM_NAME = "createTeacherAccount"
PROGRAM_DESCRIPTION = "Create a new teacher account"
PROGRAM_VERSION = "1.2"
UseGui = False

def exit_with_error(message):
    """
    Simple function to provide error exit with message
    """
    global UseGui
    text = """Error: 
    %s
    The new account has not been created.""" % message
    if UseGui:
        gui_report_result(text)
    else:
        print(text)
    sys.exit(-1)


def interactive_entry():
    """
    Question the user about all parameters necessary for
    a teacher account in the standard form. The user name is 
    created from the teachers first and last name in the form
    f_llll where f is the first initial and llll is the last name.
    The password is derived from the birthday as ddmmyyyy(Tanzania).
    """
    try:
        print("Given (first) Name: ")
        fn = sys.stdin.readline().strip().title()
        print("Famiy (last) Name: ")
        ln = sys.stdin.readline().strip().title()
        print("Birthdate (dd/mm/yyyy): ")
        birthdate = sys.stdin.readline().strip()
        print("Is this correct (Yn)? %s %s  -- %s" % (fn, ln, birthdate))
        answer = sys.stdin.readline().strip()
        if len(answer) > 0 and answer[0] == "n":
            print("OK. I will not create an account")
            sys.exit(-1)
        account_name, user_name, password, error_text = \
            process_values(fn, ln, birthdate)
        if error_text:
                exit_with_error(error_text)
    except Exception as e:
        message = \
            'The account was not created. The reported error was: "%s"' % e
        exit_with_error(message)
    return account_name, user_name, password

def process_values(first_name, last_name, birthdate):
    error_text = ""
    account_name = ""
    user_name = ""
    password = ""
    if not (first_name and last_name):
        error_text = "Both first and last name must be entered.\n"
    else:
        account_name = first_name.lower()[0] + '_' + last_name.lower()
        user_name = first_name + ' ' + last_name
    if not re.match(r'\d\d/\d\d/\d\d\d\d', birthdate):
        error_text += "The birthdate must be in the form dd/mm/yyyy.\n   All numbers are needed.\n"
    else:
        password = birthdate.replace('/', '')
    return account_name, user_name, password, error_text



def run_adduser(account_name, full_name, password, home_directory):
    """
    Use the adduser shell script to create the basic account
    """
    try:
        command = \
            "adduser --conf=/usr/local/etc/adduserTeacher.conf --home=%s --firstuid=2001 --ingroup=teacher %s" \
            % (home_directory, account_name)
        adduser = pexpect.spawn(command)
        index = adduser.expect_exact(['password:', 'exists.'])
        if index == 0:
            # normal case creating new account
            adduser.sendline(password)
            adduser.expect_exact('password:')
            adduser.sendline(password)
            adduser.expect_exact("Full Name []:")
            adduser.sendline(full_name)
            adduser.expect_exact("[]:")
            adduser.sendline("")
            adduser.expect_exact("[]:")
            adduser.sendline("")
            adduser.expect_exact("[]:")
            adduser.sendline("")
            adduser.expect_exact("[]:")
            adduser.sendline("")
            adduser.expect_exact("[Y/n]")
            adduser.sendline("Y")
            adduser.expect(pexpect.EOF)
        elif index == 1:
            adduser.expect(pexpect.EOF)
            error_message = 'The account "%s" already exists.' % account_name
            exit_with_error(error_message)
    except Exception as e:
        error_message = 'The intial account was not created successfully: "%s"' % e
        exit_with_error(error_message)


def create_home_from_tarfile(account_name, home_directory):
    """
    Use the teacher home tarfile to create an initialized
    home directory.
    """
    account_tarfile = "/usr/local/etc/account_templates/teacher.tgz"
    shell_script = \
        "cd /tmp; rm -rf teacher; tar xzf %s; rm -rf %s; mv teacher %s; chown -R %s:teacher %s" \
        % (account_tarfile, home_directory, home_directory, account_name,
           home_directory)
    error_message = """
        There was some error in creating the users home directory %s.
        If it exists run "sudo rm -rf %s" and retry create_new_teacher_account
        """ % (home_directory, home_directory)
    try:
        result = localFunctions.run_command(shell_script)
        if result:
            exit_with_error(error_message)
    except OSError:
        exit_with_error(error_message)


def correct_internal_values(account_name, home_directory):
    """
    Change some values in the home files to this user.
    """
    try:
        command = \
            "find %s -type f -exec sed -i s/REPLACE_TEXT/\%s/g {} \;" \
            % (home_directory, account_name)
        localFunctions.run_command(command, reraise_error=True)
        # lock the files that should not be changed
        command = "chown root:root %s %s" \
                  % (os.path.join(home_directory, ".xscreensaver"),
                     os.path.join(home_directory, ".config/menus/*"))
        localFunctions.run_command(command, reraise_error=True)
        command = "chmod 700 %s" % home_directory
        localFunctions.run_command(command, reraise_error=True)
    except subprocess.CalledProcessError as e:
        error_message = \
            'The account home directory modifications were not completed successfully: "%s"' % e
        exit_with_error(error_message)


def add_username_to_groups(account_name, groups=[]):
    """
    add the user account name to other groups in /etc/groups and /etc/gshadow
    :param account_name:
    :param groups:
    :return:
    """
    if len(groups):
        for group in groups:
            try:
                command = "gpasswd --add %s %s" %(account_name, group)
                localFunctions.run_command(command, reraise_error=True)
            except subprocess.CalledProcessError as e:
                print ("Failed to add %s to the group %s" %(account_name, group))

def gui_form():
    first = ""
    last = ""
    birthdate = ""
    form_line = \
        'zenity --forms --title="Create Teacher Account" --text="Create Teacher" --add-entry="First Name" ' +\
        '--add-entry="Last Name" --add-entry="Birthday\nDD/MM/YYYY" 2>/dev/null'
    result = localFunctions.run_command(form_line, result_as_list=False)
    if result:
        first, last, birthdate = result.split("|")
        first = first.title()
        last = last.title()
        birthdate = birthdate.strip()
        return first, last, birthdate
    else:
        gui_perform_cancel()

def gui_perform_cancel():
    command = 'zenity --warning --title="Canceled" --text="Account not created."'
    localFunctions.command_run_successful(command)
    sys.exit()

def use_gui():
    first, last, birthdate = gui_form()
    account_name, user_name, password, error_text = \
        process_values(first, last, birthdate)
    while error_text:
        command = 'yad --image="/usr/share/icons/gnome/48x48/status/dialog-warning.png" --title="Error In Entry" ' + \
                  '--text="%s\nDo you want to retry?"' %error_text
        if localFunctions.command_run_successful(command):
            error_text = ""
            account_name, user_name, password = use_gui()
            return account_name, user_name, password
        else:
            gui_perform_cancel()
    message_line = '"Is this correct?\n\nFirst Name:\t%s\nLast Name:\t%s\nBirthday:\t%s"' \
        %(first, last, birthdate)
    command = 'zenity --question --title="Confirm OK" --text=%s' %message_line
    result = localFunctions.command_run_successful(command)
    if result:
        return account_name, user_name, password
    else:
        gui_perform_cancel()

def gui_report_result(result):
    command = 'zenity --info --title="Account Created" --text="%s"' %result
    localFunctions.command_run_successful(command)

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description=PROGRAM_DESCRIPTION,
    #                                  prog=PROGRAM_NAME)
    # parser.add_argument("-v", "--version", action="version",
    #                     version=PROGRAM_VERSION)
    parser = localFunctions.initialize_app(PROGRAM_NAME,PROGRAM_VERSION,
                               PROGRAM_DESCRIPTION, False)
    parser.add_argument("--account_name", dest="account_name",
                        help="The user name for the account.",
                        default="", metavar="account_name")
    parser.add_argument("--password", dest="password",
                        help="The password for the account.",
                        default="", metavar="password")
    parser.add_argument("--full_name", dest="full_name",
                        help="The full name of the user for the account.",
                        default="", metavar="full_name")
    parser.add_argument("-g", "--gui", dest="gui",
                        help="Use gui input.",
                        action="store_true")
    opt = parser.parse_args()
    UseGui = opt.gui
    localFunctions.confirm_root_user(PROGRAM_NAME)
    if UseGui:
        account_name, full_name, password = use_gui()
    else:
        account_name = opt.account_name
        if not opt.full_name:
            full_name = account_name.title()
        else:
            full_name = opt.full_name.strip('"')
        password = opt.password
        if not (account_name or password):
            # normal case -- interactive creation
            account_name, full_name, password = interactive_entry()
        elif not (account_name and password):
            # error, both are needed if either given
            message = """
            Both account name and password are required if you 
            use the command line arguments.
            """
            exit_with_error(message)
    home_directory = os.path.join(TeachersHome, account_name)
    run_adduser(account_name, full_name, password, home_directory)
    add_username_to_groups(account_name, ExtraGroups)
    create_home_from_tarfile(account_name, home_directory)
    correct_internal_values(account_name, home_directory)
    result_text = """
Account created successfully for %s
Login name: %s
Password: %s
Please login as this user to confirm success.
""" % (full_name, account_name, password)
    if UseGui:
        gui_report_result(result_text)
    else:
        print(result_text)
