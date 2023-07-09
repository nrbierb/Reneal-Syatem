#!/usr/bin/env python3
# coding:utf-8
# Author:  Neal Bierbaum --<nrbierb@gmail.com>
# Purpose:
# Created: 02/14/2013

"""
This program checks for student users who have recently logged out and have not
yet had their home directory rebuilt from the appropriate template or have no
home directory at all.
It will then rebuild the home directory.
"""

import os
import re
import subprocess
import sys
import syslog
import pwd
import localFunctions
import localFunctionsPy3
import systemCleanup

PROGRAM_DESCRIPTION = \
    "Replace the home directories for students which have just logged out."
PROGRAM_VERSION = "1.4"
PROGRAM_NAME = "replaceInactiveStudentHomeDirs"


def find_active_users():
    """
    Create a dictionary keyed by user of all users with an active process
    with the count of processes as the dictionary entry. This dictionary and
    a "valid" flag are returned. If the /bin/ps fails the valid is false to
    indicate that the users are unknown and the result should not be used.
    """
    active_users = {}
    valid = True
    try:
        command = '/bin/ps -e --format=user:20 --no-headers'
        user_names = localFunctions.run_command(command, result_as_list=True,
                                                reraise_error=True)
        for user in user_names:
            if user in active_users:
                active_users[user] += 1
            else:
                active_users[user] = 1
    except subprocess.CalledProcessError:
        valid = False
    return active_users, valid


def get_users_ip_address(user, remote_users):
    """
    Determine the host address of the user from the information
    about the primary shell process
    """
    ip_address = remote_users.get(user, None)
    if not ip_address:
        try:
            command = '/bin/ps -f -u ' + user
            user_process_listing = localFunctions.run_command(command,
                                                              reraise_error=True,
                                                              result_as_list=False)
            match = re.search(r'(?:LTSP_CLIENT=)(\d+\.\d+\.\d+\.\d+)',
                              user_process_listing)
            if match:
                ip_address = match.group(1)
        except subprocess.CalledProcessError:
            pass
    return ip_address


def check_hosts(hosts_dict):
    """
    Ping all hosts in hosts dict to confirm alive.
    Remove all entries that are not alive.
    :param hosts_dict:
    :return:
    """
    if hosts_dict:
        command = "fping -uq -i 2 -p 10 -B 1.0 %s" % " ".join(hosts_dict.keys())
        dead_hosts = localFunctions.run_command(command)
        for host in dead_hosts:
            hosts_dict.pop(host, "")
    return hosts_dict


def find_who_users():
    """
    Create a list of users on the local server and a list of remote users
    with who command
    :return dict of local users and dict of remote users with ip:
    """
    user_info = localFunctions.run_command('who', result_as_list=False)
    local_users = set()
    remote_users = {}
    re_string = "^(\S+)\s+tty"
    local_users.update(re.findall(re_string, str(user_info),
                                  re.MULTILINE))
    re_string = "^(\S+)\s+pts.*\((.*)\)"
    for entry in re.findall(re_string, str(user_info),
                            re.MULTILINE):
        remote_users[entry[0]] = entry[1]
    return local_users, remote_users


def find_orphan_users(user_dict):
    """
    Create a dictionary of all users  (not daemons) that do not
    have a "bash" process. The dictionary is keyed by user and
    contains all of the users processes in a dictionary keyed by process
    command and containing the pid.
    """
    try:
        processes = localFunctions.run_command(
            '/bin/ps -e --format=user:20,uid,gid,pid,comm',
            result_as_list=True, reraise_error=True)
        for process in processes:
            try:
                if len(process.split()) == 5:
                    user, uid_str, gid_str, pid_str, command = process.split()
                    uid = int(uid_str)
                    gid = int(gid_str)
                    pid = int(pid_str)
                    if (int(gid) > 999) and (int(uid) > 999):
                        # a user, not a daemon
                        if user not in user_dict:
                            user_dict[user] = {}
                        user_dict[user][command] = pid
            except ValueError:
                continue
        local_users, remote_users = find_who_users()
        check_host_dict = {}
        for user, user_processes in list(user_dict.items()):
            # remove all that have a bash or sh process
            if ("bash" in user_processes or "sh" in user_processes) \
                    and user not in local_users:
                user_ip_address = get_users_ip_address(user, remote_users)
                if user_ip_address:
                    check_host_dict[user_ip_address] = user
        alive_host_dict = check_hosts(check_host_dict)
        for user in local_users:
            user_dict.pop(user, None)
        for user in alive_host_dict.values():
            user_dict.pop(user, None)
    except subprocess.CalledProcessError as err_val:
        report_error("Failed process in find_orphan_users %s" % err_val)
        pass
    return user_dict


def account_needs_processing(username):
    """
    Check users home directory to see if it has been used so it is eligible
    for replacement. It tests for the existence of the file ".xsession_errors"
    that is created every time the user logs in but is not included in the
    student template directory.
    """
    try:
        user_info = pwd.getpwnam(username)
        home_dir = user_info.pw_dir
        if os.path.exists(home_dir):
            # true if the target file exists
            target_file = ".xsession-errors"
            targetfile = os.path.join(home_dir, target_file)
            return os.path.exists(targetfile)
        else:
            # always True if users home is missing
            return True
    except KeyError:
        return False


def build_user_name_list():
    """
    Create a list of account names eligible for rebuild.
    """
    prefix = "student"
    name_list = [prefix + str(i) for i in range(1, localFunctionsPy3.number_of_student_accounts()
                                                + 1)]
    return name_list


def get_accounts_to_process(user_name_list):
    """
    Create a list of all users that have no processes running
    and have not yet had their home directories rebuilt.
    """
    active_users, user_dict_valid = find_active_users()
    if user_dict_valid:
        # if the dict with values is not active then the active
        # users are unknown so nothing should be done.
        return [username for username in user_name_list
                if (account_needs_processing(username) and
                    (username not in active_users))]


def kill_orphan_processes():
    """
    Kill all user processes of orphaned
    (those that do not have a controlling shell) users.
    """
    orphan_users = {}
    orphan_users = find_orphan_users(orphan_users)
    for user, processes in orphan_users.items():
        try:
            for pid in processes.values():
                if not localFunctions.command_run_successful(
                        "kill %d" % pid):
                    localFunctions.command_run_successful("kill -9 %d" % pid)
                    # finally, use the killall. This should have worked in the
                    # beginning but seems not to
        except subprocess.CalledProcessError:
            pass
        # finally, use the killall. This should have worked in the
        # beginning but seems not to

        localFunctions.command_run_successful(
            "killall -9 -u %s" % user)
        syslog.syslog("Killed %d processes of %s "
                      % (len(processes), user))


def report_error(error_text):
    syslog.syslog("Error:  " + error_text)
    print(error_text, file=sys.stderr)
    return True


def rebuild_home_dirs(account_list):
    """
    Rebuild the home directory for all users in the account list.
    """
    had_error = False
    analysis_program = "/usr/local/share/apps/processAnalysisData"
    try:
        if os.path.exists(analysis_program):
            names = ""
            for name in account_list:
                names += " " + name
            command = '%s %s' % (analysis_program, names )
            localFunctions.command_run_successful(command)
    except OSError:
        pass
    for user in account_list:
        try:
            command = "/usr/local/bin/rebuildStudentHomeDirectories --syslog -a " + user
            localFunctions.run_command(command, reraise_error=True)
        except subprocess.CalledProcessError as err_val:
            had_error = report_error(
                "Failed to rebuild student directory for %s:\n %s"
                % (user, err_val))
    return had_error


def cleanup_media_dir(target_accounts):
    """
    Remove directory and contents of /media/account_name if
    it is not a mounted filesystem for all account names.
    :param target_accounts:
    :return:
    """
    had_error = False
    try:
        for target_account in target_accounts:
            target_directory = os.path.join("/media", target_account)
            if os.path.exists(target_directory):
                systemCleanup.clean_dir(target_directory, exclusions=[],
                                        prune_active_owner=True, other_protected_users=[])
                try:
                    os.rmdir(target_directory)
                except OSError as err_val:
                    had_error = report_error(
                        "Failed to remove %s : %s" % (target_directory, err_val))
    except OSError as err_val:
        had_error = report_error(
            "cleanup_media_dir failed: %s" % err_val)
    return had_error


def cleanup_tmp(target_accounts):
    """
    Remove any content in client_home_local that belongs to the student account.
    This prevents any student from storing file in the tmp level directory. This
    is run before rebuilding the account.
    :param target_account:
    :return:
    """
    for target_account in target_accounts:
        command = "find /tmp/ -depth -user %s -exec rm --one-file-system -r -f {} \;" %target_account
        localFunctions.command_run_successful(command)

if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                  PROGRAM_DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    users_checked = build_user_name_list()
    kill_orphan_processes()
    target_accounts_list = get_accounts_to_process(users_checked)
    if target_accounts_list:
        print("-- " + ", ".join(target_accounts_list))
        error_occurred_rebuild = rebuild_home_dirs(target_accounts_list)
        error_occurred_cleanup = cleanup_media_dir(target_accounts_list)
        cleanup_tmp(target_accounts_list)
        if error_occurred_rebuild or error_occurred_cleanup:
            sys.exit(1)
