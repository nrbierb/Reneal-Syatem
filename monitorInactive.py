#! /usr/bin/python3
"""
Call the replaceInactiveStudentdirs program at regular
intervals. If it returns an error message then put 
the message in the syslog.
"""

import subprocess
import syslog
import time
import atexit
import localFunctions
import backgroundFunctions

PROGRAM_NAME = "monitorInactive"
PROGRAM_DESCRIPTION = \
    "Periodically check for recently logged out students and replace home directory"
PROGRAM_VERSION = "2.1"
ERROR_LOGFILE = "/var/log/replace-account/error.log"
INFO_LOGFILE = "/var/log/replace-account/info.log"
InfoLogger = None
ErrorLogger = None
DEBUG = False
MonitorInterval = 15


def main_loop(systemd_connector):
    start_time = time.time()
    while True:
        systemd_connector.update_watchdog()
        try:
            if DEBUG:
                command = "/home/master/CodeDevelopment/systemApps/replaceInactiveStudentHomeDirs.py"
            else:
                command = "/usr/local/bin/replaceInactiveStudentHomeDirs"

            result = localFunctions.run_command(command, result_as_list=False,
                                                reraise_error=True)
            if result:
                InfoLogger.info("Accounts rebuilt: \n%s" % result)
        except subprocess.CalledProcessError as err_val:
            ErrorLogger.error("replaceInactiveStudentHomeDirs failed: " +
                              err_val.output)
            syslog.syslog("replaceInactiveStudentHomeDirs failed: " +
                          err_val.output)
        except Exception as err_val:
            # serious error from system
            ErrorLogger.error(
                "replaceInactiveStudentHomeDirs failed with unknown error:\n " +
                localFunctions.generate_exception_string(err_val))
            syslog.syslog(
                "replaceInactiveStudentHomeDirs failed with unknown error:\n " +
                localFunctions.generate_exception_string(err_val))
        # adjust for time running the command
        start_time = backgroundFunctions.fill_loop_time(MonitorInterval, start_time)


if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                  PROGRAM_DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    systemd = backgroundFunctions.SystemdSupport()
    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers(INFO_LOGFILE,
                                                                 ERROR_LOGFILE)
    atexit.register(backgroundFunctions.log_stop, systemd, PROGRAM_NAME,
                    InfoLogger)
    #if not DEBUG:
    backgroundFunctions.shutdown_if_running(PROGRAM_NAME, ErrorLogger)
    backgroundFunctions.log_start(systemd, PROGRAM_NAME, InfoLogger)
    main_loop(systemd)
