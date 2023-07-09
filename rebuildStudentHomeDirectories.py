#!/usr/bin/env python3
"""
This is a simple program to rebuild the child and student home directories.
These are by default located in /client_home_local.
The directories are first deleted and then new ones are built by extracting
the tar file for the account type. These files are by default located in 
/usr/local/etc/account_templates. This must be run as superuser.
"""

import argparse
import os
import pwd
import random
import shutil
import string
import subprocess
import sys
import syslog
import time
import localFunctions
import localFunctionsPy3
from datetime import datetime

# add all of these globals to expose useful parameters
accounts_info = []
StudentBaseName = "student"
StudentGroup = "student"
StudentAccountBaseDirectory = "/client_home_local"
ImageName = "student_image"
ImageBase = "/usr/local/etc/account_templates"
RemoveCommand = "/bin/rm -rf "
FirefoxConfigFile = ".mozilla/firefox/firefox103/prefs.js"
OldFirefoxConfigFile = ".mozilla/firefox/firefox88/prefs.js"
PROGRAM_NAME = "rebuildStudentHomeDirectories"
PROGRAM_DESCRIPTION = "Create home directories from the student template"
PROGRAM_VERSION = "1.3b"
ErrorText = ""
FailedAccounts = ""
DEBUG = False
USE_SYSLOG = True
AccountsCreatedCount = 0

MOVED_DIR_BASE_NAME = "/tmp/student-delete."

def remove_account_directory(directory_name=""):
    """
    Fully remove the directory and contents
    :param directory_name:
    :return:
    """
    # confirm that directory exists and is in the correct main directory for
    # safety
    global MOVED_DIR_BASE_NAME, ErrorText
    path_parts = os.path.split(directory_name)
    if (os.path.exists(directory_name) and
            path_parts[0] == StudentAccountBaseDirectory and
            len(path_parts) > 1):
        # ensure that the gvfs file system is not present
        command = "/bin/umount %s/.gvfs 2> /dev/null" % directory_name
        localFunctions.run_command(command)
        # move this out of the way and then delete to assure that the slow delete
        # will not affect further actions
        extension = ''.join(random.choice(string.ascii_letters) for i in range(10))
        new_location = "%s.%s" % (MOVED_DIR_BASE_NAME, extension)
        try:
            if localFunctions.run_command(
                    "/bin/mv %s %s;" % (directory_name, new_location), reraise_error=True):
                directory_name = new_location
        except subprocess.SubprocessError as e:
            ErrorText += "\n Could not move to %s: %s" % (new_location, e)
        command = "/bin/rm -rf %s;" % directory_name
        localFunctions.run_command(command)


def replace_home_directory(account_name, source_image, group, retries=0):
    """
    Remove the prior directory, untar a replacement, move it to the final
    destination, and set correct ownership.
    """
    global ErrorText, FailedAccounts, AccountsCreatedCount
    try:
        home_directory = os.path.expanduser("~" + account_name)
        remove_account_directory(home_directory)
        if retries:
            localFunctions.run_command("sync -f /client_home_local")
        clean_trash(account_name)
        command = "cp -a %s %s" % (source_image, home_directory)
        localFunctions.run_command(command, reraise_error=True)
        command = "grep -lr REPLACE_TEXT %s" % home_directory
        try:
            files_to_change = localFunctions.run_command(command,
                                                         reraise_error=True)
        except subprocess.SubprocessError:
            ErrorText += "\nFirst grep on account %s failed." % (account_name)
            time.sleep(0.3)
            files_to_change = localFunctions.run_command(command,
                                                         reraise_error=True)
        wait_count = 0
        for filename in files_to_change:
            if not os.path.exists(filename) and wait_count < 3:
                wait_count += 1
                time.sleep(0.3)
            command = 'sed -i s/REPLACE_TEXT/%s/g "%s"' % (
                    account_name, filename)
            try:
                localFunctions.run_command(command, reraise_error=True)
            except subprocess.SubprocessError:
                ErrorText += "\nFirst sed on account %s failed." % (account_name)
                if wait_count < 4:
                    wait_count +=1
                    time.sleep(0.3)
                localFunctions.run_command(command, reraise_error=True)
        command = "chown -R %s:%s %s;" % (
            account_name, group, home_directory)
        localFunctions.run_command(command, reraise_error=True)
        command = "chown root %s/%s %s/%s;" % (home_directory, FirefoxConfigFile,
                                               home_directory, OldFirefoxConfigFile)
        localFunctions.run_command(command)
        # assure that the file used as a marker for a used account is removed
        flag_file = home_directory + "/.xsession-errors"
        if os.path.lexists(flag_file):
            os.remove(flag_file)
        log_message("Replaced home directory for %s" % account_name)
        AccountsCreatedCount +=1
    except subprocess.CalledProcessError as err:
        text = "Error on home directory replacement for account %s:\n %s" \
               % (account_name, err.stdout)
        if retries < 3:
            retries += 1
            log_message("  Retrying rebuild for %s" %account_name)
            localFunctions.run_command("sync -f /client_home_local")
            replace_home_directory(account_name, source_image, group,
                                   retries)
        else:
            log_message(
                "    Failed to rebuild home directory for %s" % account_name)
            FailedAccounts = "%s %s" % (FailedAccounts, account_name)
        ErrorText += "\n" + text


def clean_trash(user):
    """
    Clean out the contents of the trash directory for the user in the
    client_home_students area. This will delete everything in the
    directory for all users on all servers logged in with that UID
    """
    uid = pwd.getpwnam(user)[2]
    trash_dir = "/client_home_students/.Trash-%i" % uid
    try:
        if os.path.isdir(trash_dir):
            shutil.rmtree(trash_dir)
        os.makedirs(trash_dir)
        os.chown(trash_dir, uid, 3000)
    except (OSError, os.error, shutil.Error):
        # This will happen if nfs is not mounted
        pass


def log_message(message):
    global USE_SYSLOG
    if USE_SYSLOG:
        syslog.syslog(message)
    else:
        print(message)


if __name__ == "__main__":
    source_image = os.path.join(ImageBase, ImageName)
    count = localFunctionsPy3.number_of_student_accounts()
    epilog_text = "By default it will create %d numbered student accounts" \
                  % count
    parser = argparse.ArgumentParser(prog=PROGRAM_NAME,
                                     description=PROGRAM_DESCRIPTION,
                                     epilog=epilog_text)
    parser.add_argument("-v", "--version", action="version",
                        version=PROGRAM_VERSION)
    parser.add_argument('-a', '--account', dest='account_names',
                        action='append',
                        help="Rebuild this account. This can be used several times to add more accounts")
    parser.add_argument('-c', '--count', dest='count', default=count, type=int,
                        help='Create this many numbered student accounts')
    parser.add_argument('-m', '--build-missing', dest='build_missing',
                        action="store_true",
                        help='Create home dirs for all missing up to the count of students')
    parser.add_argument('-i', '--image-name', dest='source_image',
                        default=source_image,
                        help='Directory image of the student home directory')
    parser.add_argument("--clean", dest="clean_directory", action="store_true",
                        help="delete all contents in /client_home_local before starting rebuild")
    parser.add_argument("--syslog", dest="use_syslog", action="store_true",
                        help="send all messages to syslog intstead of stdout")
    parser.add_argument("--logerrors", dest="log_errors", action="store_true",
                        help="Log error messages. Useful in operational problem analysis.")
    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        localFunctions.error_exit("Error in command line: %s" % e)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    USE_SYSLOG = args.use_syslog
    accounts = args.account_names
    source_image = args.source_image
    if not os.path.isdir(source_image):
        localFunctions.error_exit(
            "Account template image %s does not exist. No accounts rebuilt."
            % source_image)
    if args.clean_directory:
        command = 'find /client_home_students -name ".Trash-*" -exec rm -r {} \;'
        localFunctions.command_run_successful(command)
        if localFunctions.command_run_successful(
                "find /client_home_local -mindepth 1 -maxdepth 1 -xdvv -exec /bin/rm -r {} \;"):
            syslog.syslog("Completely cleaned /client_home_local")
    if args.build_missing:
        accounts = [StudentBaseName + str(i) for i in range(1,count+1) if not
            os.path.exists(os.path.join('/client_home_local', StudentBaseName +str(i)))]
    if not accounts:
        accounts = [StudentBaseName + str(i) for i in range(1, count + 1)]
    for name in accounts:
        dt = datetime.now()
        replace_home_directory(name, source_image, StudentGroup)
        if DEBUG:
            print("    " + str(datetime.now() - dt))
    # assure all is pushed to fs
    localFunctions.run_command("sync -f /client_home_local")
    localFunctions.run_command("sync -f /client_home_students")
    # cleanup anything left in tmp
    localFunctions.run_command("rm -rf /tmp/student-delete.*")
    message = "rebuildStudentHomeDirectories finished. %d accounts created." \
                %AccountsCreatedCount
    log_message(message)
    if ErrorText and args.log_errors:
            log_message(ErrorText)
    if FailedAccounts:
        log_message("\n---------------------------------------------\n")
        log_message("These accounts were not rebuilt: " + FailedAccounts)
        sys.exit(-1)
