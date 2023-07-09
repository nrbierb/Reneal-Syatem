#!/usr/bin/env python3
# coding:utf-8
# Author:   --<N. Bierbaum>
# Purpose:
# Created: 03/01/2017

"""
Remove all contents of "trash" folders for all users.
use When filesystem is too full or as desired.
"""

import argparse
import glob
import grp
import os
import os.path
import subprocess
import syslog
import tabulate
import localFunctions
import backgroundFunctions

TRASH_DIRECTORY = ".local/share/Trash/"
PROGRAM_DESCRIPTION = \
    """Empty the trash of one or more users.
    With no arguments it will clean for all teachers.
    Must be run with sudo."""
PROGRAM_VERSION = "1.1"
ErrorLogger = None

def get_group_users_names(group_name):
    """
    Return the names of all users that are a member of the group
    """
    users = []
    try:
        gid = grp.getgrnam(group_name).gr_gid
        with open('/etc/passwd', 'r') as pwfile:
            for line in pwfile:
                try:
                    parts = line.split(':')
                    if int(parts[3]) == gid:
                        users.append(parts[0])
                except (IndexError, ValueError, AttributeError):
                    pass
    except (IOError, TypeError, KeyError):
        pass
    return users

def create_table(result_data, header_line, indent=0, html_table=False):
    if html_table:
        table_type = "html"
    elif indent:
        tabulate.PRESERVE_WHITESPACE = True
        table_type = "plain"
    else:
        table_type = "psql"
    return tabulate.tabulate(result_data, header_line, table_type)

def empty_users_trash(users, trash_directory=TRASH_DIRECTORY, log=False,
                      table_indent=0, max_size = 0, days_old = 0,  error_logger=ErrorLogger):

    trash_removed = {}
    result_table = ""
    result_table_html = ""
    total_trash_removed = 0
    has_empty_trash_command = localFunctions.command_run_successful(
        "which trash-empty")
    try:
        for name in users:
            try:
                user_name = name.strip()
                if not localFunctions.command_run_successful("id %s" % user_name):
                    print("Error: User '%s' does not exist. Check spelling." % user_name)
                    continue
                user_tilde_name = "~" + user_name
                user_home = os.path.expanduser(user_tilde_name)
                user_trashdir = os.path.join(user_home, trash_directory)
                if os.path.isdir(user_trashdir):
                    user_trashdir_files= user_trashdir +"*/*"
                    #check for files in the trash
                    if glob.glob(user_trashdir_files):
                        trash_size_string = localFunctions.run_command(
                            "du -s %s" %user_trashdir,
                            result_as_list=False, merge_stderr=False)
                        initial_trash_size = int(trash_size_string.split()[0])
                        #if max_size set, only empty trash if there is more than that
                        if max_size and initial_trash_size < max_size:
                            continue
                        if has_empty_trash_command:
                            command = "su %s -c 'trash-empty %d'" % (user_name, days_old)
                        else:
                            #perform rm as the user for safety --don't want root rm -r'ing
                            command = 'su -c "/bin/rm -r %s" %s' %(user_trashdir_files, user_name)
                        if localFunctions.command_run_successful(command):
                            trash_size_string = localFunctions.run_command(
                                "du -s %s" %user_trashdir,
                                result_as_list=False, merge_stderr=False)
                            final_trash_size = int(trash_size_string.split()[0])
                            size_change = initial_trash_size - final_trash_size
                            if size_change:
                                total_trash_removed += size_change
                                value_string = localFunctions.convert_to_readable(
                                    size_change)
                                if value_string:
                                    trash_removed[user_name] = value_string
            except (OSError, ValueError, IndexError) as e:
                if error_logger:
                    error_logger.error("cleanupUsersTrash empty_users_trash: %s" %e)
        if trash_removed:
            data = []
            indent_text = " " * table_indent
            header_line = [indent_text + "User Name", "Trash Removed"]
            for name in users:
                if name in trash_removed:
                    data.append([indent_text + name, trash_removed[name]])
                    if log:
                        syslog.syslog("User trash removed: '%s' %s"
                                      %(name, trash_removed[name]))
            result_table = create_table(data, header_line)
            result_table_html = create_table(data, header_line, table_indent, html_table=True)
    except (OSError, KeyError):
        pass
    return trash_removed, result_table, result_table_html, total_trash_removed

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="cleanUsersTrash",
                                     description=PROGRAM_DESCRIPTION)
    parser.add_argument("-v", "--version", action="version",
                        version=PROGRAM_VERSION)
    parser.add_argument("-f", "--accounts-file", dest="accounts_file",
                        help="File that has list of account names to empty")
    parser.add_argument("-g", "--group-name", dest="group_name",
                        help="The group name of the users to be cleaned",
                        default="teacher")
    parser.add_argument("-l", "--log to syslog", dest="log",
                        help="Report trash emptied in syslog",
                        action="store_true")
    parser.add_argument("-m" "--max-size", dest="max_trash_size",
                        help="Empty trash only if more than this amount (KB, MB, GB extensions allowed)",
                        default="0")
    parser.add_argument("-o", "--older", dest="days_old", type=int,
                        help="Number of days old before emptied.",
                        default=0)
    parser.add_argument("-q", "--quiet", dest="quiet",
                        help="No text output",
                        action="store_true")
    parser.add_argument("-s", "--scheduled", dest="scheduled",
                        help="Regularly run by cron",
                        action="store_true")
    parser.add_argument("-a", "--include-sysadmin", dest="include_sysadmin",
                        help="Include sysdamin in users for empty",
                        action="store_true")
    parser.add_argument("user_names", nargs='*',
                        help="Names of users that will have trash emptied. "+\
                             "No other users will be processed. Normally left blank.")
    opt = parser.parse_args()
    localFunctions.confirm_root_user("cleanUsersTrash")
    accounts = opt.user_names
    if not accounts:
        if opt.accounts_file:
            try:
                accounts_file = open(opt.accounts_file, "r")
                accounts = accounts_file.readlines()
                accounts_file.close()
            except IOError:
                localFunctions.error_exit(
                    "Could not read accounts list file", 1, opt.quiet)
        else:
            accounts = get_group_users_names(opt.group_name)
            if opt.include_sysadmin:
                accounts.append("sysadmin")
    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers("/var/log/cleanup/info.log",
                                                                 "/var/log/cleanup/error.log")
    purpose = "Scheduled" if opt.scheduled else "Commanded"
    InfoLogger.info("***** Starting %s Trash Cleanup *****" %purpose)
    max_trash_size = localFunctions.convert_from_readable(opt.max_trash_size)/1024
    trash_removed, result_table, result_table_html, total_trash_removed = \
        empty_users_trash(accounts, log=opt.log, max_size=max_trash_size, days_old=opt.days_old,
                          error_logger=ErrorLogger)
    if not total_trash_removed:
        trash_removed_str = "no"
    else:
        trash_removed_str = localFunctions.convert_to_readable(total_trash_removed,
                                                           always_show_fraction=True)
    InfoLogger.info("----- Finished %s Trash Cleanup %s trash removed.------" % (purpose,
                                                                                 trash_removed_str))
    if not opt.quiet:
        print(result_table)
        usertype = "user" if opt.user_names else opt.group_name
        print("%d of %d %ss had trash removed."
              %(len(trash_removed),len(accounts), usertype))
