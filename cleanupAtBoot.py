#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Remove files that may have been left around after shutdown.
It checks for any sort of mounted filesystems to assure that no
external usb drives, etc are accidentally erased
"""


import os
import syslog

import localFunctions
import systemCleanup
import backgroundFunctions

PROGRAM_NAME = "cleanupAtBoot"
VERSION = "0.8"
WRITE_TO_SYSLOG = True

if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, VERSION,
        """Remove unwanted files in /media, client_home_local, 
/client_home_students, /var/tmp, and /var/crash
Normally run only as last part of system boot.""")
    localFunctions.confirm_root_user(PROGRAM_NAME)
    syslogger = systemCleanup.Syslogger("cleanupAtBoot: ", WRITE_TO_SYSLOG)
    syslogger.log_message("Starting cleanup at boot")
    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers("/var/log/cleanup/info.log",
                                                                 "/var/log/cleanup/error.log")
    InfoLogger.info("***** Starting Cleanup At Boot *****")
    initial_size = localFunctions.get_filesystem_space_used("/")
    on_server = os.uname()[1].startswith("main-server")
    if on_server:
        systemCleanup.clean_client_home_local(exclusions=[],prune_active_owner=False,
                                              other_protected_users=[], rebuild_student_home=True)
        systemCleanup.clean_os_copies("/OS_Copies")
        command = 'find /client_home_students -name ".Trash-*" -exec rm -r {} \;'
        localFunctions.command_run_successful(command)
        command = 'find /var/tmp -name "kdecache*" -exec rm -r {} \;'
        localFunctions.command_run_successful(command)
    else:
        # must be a mac client
        if not localFunctions.command_run_successful("timeout 5 /bin/findmnt 2>&1 >/dev/null"):
            # this could occur with nfs problems on client
            message = "Could not get filesystem data with 'findmnt'. Nothing done."
            syslogger.log_message(message, syslog.LOG_ERR)
            localFunctions.error_exit(message)
    for dirname in ("/mnt", "/var/crash"):
        result_message=""
        result_massage = systemCleanup.clean_dir(dirname, exclusions=[],
                                prune_active_owner=False,
                                other_protected_users=[])
        if result_message:
            syslogger.log_message(result_message)
    result_message = systemCleanup.clean_media(exclusions=[],
                                               prune_active_owner=True,
                                               other_protected_users=[])
    if result_message:
        syslogger.log_message(result_message)
    message, delta = localFunctions.change_in_filesystem_size("/", initial_size)
    change_message = "%s after cleanup at boot" % message
    syslogger.log_message(change_message)
    InfoLogger.info("----- Finished Cleanup At Boot %s ------" % message)
