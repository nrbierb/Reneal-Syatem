#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
A library of functions to support backround processes
This includes loggers and logger handlers,
systemd interaction, and loop time support functions
"""

import logging
import logging.handlers
import os
import sys
import syslog
import time
import atexit
import psutil
from systemd.daemon import notify
import localFunctions


def fill_loop_time(loop_time_interval, start_time):
    """
    Add extra sleep time to assure that the loop is precisely the interval.
    :param loop_time_interval:
    :return:
    """
    stop_time = time.time()
    loop_time = stop_time - start_time
    if loop_time_interval > loop_time:
        # tiny adjustment at end
        time.sleep(loop_time_interval - loop_time - 0.001)
    return time.time()


class SystemdSupport:
    """
    Provide support for systemd messaging if started by systemd
    """

    def __init__(self):
        """
        Determine if started by systemd and set value
        """
        self.systemd_active = self.systemd_active()
        if self.systemd_active:
            atexit.register(self.report_stop)

    @staticmethod
    def systemd_active():
        return psutil.Process(os.getpid()).ppid() == 1

    def report_start(self):
        if self.systemd_active:
            notify("READY=1")
            notify("STATUS=Active")
            notify("MAINPID=%d" % os.getpid())

    def update_watchdog(self):
        if self.systemd_active:
            notify("WATCHDOG=1")

    def report_stop(self):
        if self.systemd_active:
            notify("STOPPING=1")
            notify("STATUS=Stopped")


# --------------------------------------------------------------------

def setup_logger(logger_name, log_file, level, formatter):
    if log_file:
        logger = logging.getLogger(logger_name)
        fileHandler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=200000, backupCount=5)
        fileHandler.setFormatter(formatter)
        logger.setLevel(level)
        logger.addHandler(fileHandler)


def create_loggers(info_log_filename, error_log_filename):
    """
    Create reporting loggers for a program. Create each logger only if the
    log filename is given. If name is empty string, return none for that
    logger. This allows the creation of a single loggere of the appropriate type
    if that is all the program needs.
    :param info_log_filename:
    :param error_log_filename:
    :return:
    """
    InfoLogger = None
    ErrorLogger = None
    if info_log_filename:
        setup_logger("InfoLogger", info_log_filename, level=logging.INFO, formatter=
            logging.Formatter('%(asctime)s %(message)s'))
        InfoLogger = logging.getLogger("InfoLogger")
    if error_log_filename:
        setup_logger("ErrorLogger", error_log_filename, level=logging.ERROR,
                     formatter=
                     logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
        ErrorLogger = logging.getLogger("ErrorLogger")
    return InfoLogger, ErrorLogger


def log_start(systemd, program_name, InfoLogger):
    """
    Write the start time to the info log
    :return:
    """
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    if InfoLogger:
        if uptime_seconds < 45.0:
            InfoLogger.info("*** Starting %s at bootup" % program_name)
        else:
            InfoLogger.info("*** Starting %s" % program_name)
    syslog.syslog("--%s is running" % program_name)
    systemd.report_start()


def log_stop(systemd, program_name, InfoLogger):
    """
    Wrtie the end time if it is a normal shutdown
    :return:
    """
    if InfoLogger:
        InfoLogger.info("    --- Stopping %s" % program_name)
    syslog.syslog("--%s is stopping" % program_name)
    logging.shutdown()
    systemd.report_stop()

def setup_systemd_and_start(program_name, info_loggger, error_logger):
    """
    Perform initial start actions that setup connection to systemd,
    suhtdown if there is another instance of this program already running.
    and finally log the start.
    If debug skip all actions and return a null systemd
    :return : systemd
    """
    systemd = SystemdSupport()
    atexit.register(log_stop, systemd, program_name,
                    info_loggger)
    shutdown_if_running(program_name, error_logger)
    log_start(systemd, program_name, info_loggger)
    return systemd

def shutdown_if_running(program_name, ErrorLogger=None):
    """
    Two copies of this program should not be running at the same time.
    :return:
    """
    try:
        pid_list = []
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=["pid", "cmdline"])
            command_line = " ".join(pinfo["cmdline"])
            if program_name in command_line and "systemctl" not in command_line:
                pid_list.append(pinfo["pid"])
        if pid_list:
            my_pid = os.getpid()
            parent_pid = os.getppid()
            if pid_list.count(my_pid):
                pid_list.remove(my_pid)
            if pid_list.count(parent_pid):
                pid_list.remove(parent_pid)
        # If the other running copy still exists shutdown this one.
        # Otherwise, let this one start up
        if len(pid_list) > 0:
            #check if it is may parent .That is still ok
            message = "Another %s running. Shutting down." % program_name
            syslog.syslog(message)
            if ErrorLogger:
                try:
                    ErrorLogger.error(message)
                except AttributeError:
                    pass
            sys.exit(0)
    except Exception as err_val:
        if ErrorLogger:
            try:
                ErrorLogger.error("Shutdown_if_running had exception: %s"
                              % localFunctions.generate_exception_string(err_val),
                              sys.stderr)
            except AttributeError:
                pass
        sys.exit(1)
