#!/usr/bin/python3
# -*- coding: utf-8 -*-

import glob
import os
import subprocess
import tempfile
import time

import localFunctions
import networkFunctions

INTERNET_OFF_FILENAME = "/tmp/internet-off-*.txt"
INTERNET_OFF_DIR = "/tmp"
INTERNET_OFF_PREFIX = "internet-off-"
INTERNET_OFF_SUFFIX = ".txt"
PROGRAM_NAME = "internetControl"
PROGRAM_VERSION = "0.5"


def check_internet_turned_off():
    """
    if squid is not active and there is the flag file "internet-offXXXXX' in /tmp
    then there is no internet access via browser for users.
    :return: internet_turned_off, internet_functional
    """
    internet_turned_off = False
    if not networkFunctions.proxy_server_working() and glob.glob(INTERNET_OFF_FILENAME):
        internet_turned_off = True
    return internet_turned_off


def turn_off_internet(expiration_time_string):
    """
    Stop squid and set a flag file to indicate that squid has purposely been
    shut down. The flag file contains the expiration_time -- the time to
    remove the file and restart squid
    :return:
    """
    tmp_file, filename = tempfile.mkstemp(prefix=INTERNET_OFF_PREFIX, suffix=INTERNET_OFF_SUFFIX,
                     dir=INTERNET_OFF_DIR, text=True)
    with open(filename, "w") as f:
        f.write(expiration_time_string)
    return localFunctions.command_run_successful("systemctl stop squid")


def turn_on_internet():
    """
    if internet is turned off, remove all flag files and start squid
    :return:
    """
    if check_internet_turned_off():
        for filename in glob.iglob(INTERNET_OFF_FILENAME):
            os.remove(filename)
        localFunctions.command_run_successful("systemctl restart squid")
    return not check_internet_turned_off()


def turn_on_dialog():
    command = 'yad --text="<b>The browser internet access is turned off.\nTurn on?</b>" '
    command += '--text-align="center"'
    result = localFunctions.command_run_successful(command)
    if not result:
        command = 'yad --text="<b>Internet remains off</b>" --button="gtk-ok":0'
        localFunctions.command_run_successful(command)
    return result


def turn_off_dialog():
    top_text1 = "<b>Browser internet access is on.</b>"
    top_text2 = "<b>Turn off?</b>\n"
    middle_text = "<b>Time period off:</b>"
    end_text1 = "<b>\nBrowser internet access can be turned on</b>"
    end_text2 = "<b>at any time.</b>"
    end_text3 = "<b>Just click the Internet On/Off button</b>"
    choice_text = "One Hour,Two Hours,Until Server Reboot"
    command = 'yad --form --separator=" " --item-separator="," --align="center" --field="%s":LBL --field="%s":LBL --field="%s":CB --field="%s":LBL --field="%s":LBL --field="%s":LBL "" "" "%s" "" "" ""' \
              % (top_text1, top_text2, middle_text, end_text1, end_text2, end_text3, choice_text)
    try:
        command_result = localFunctions.run_command(command, reraise_error=True,
                                                    result_as_list=False)
    except subprocess.SubprocessError:
        command_result = ""
    if not command_result:
        return "", "Still On"
    expire_time = 0
    choice = command_result.strip()
    now = int(time.time())
    if choice == "One Hour":
        expire_time = now + 3600
    elif choice == "Two Hours":
        expire_time = now + 7200
    return str(expire_time), choice

def announce_internet_on():
    command = "zenity --info --text='<b>Browser internet access is on</b>'"
    localFunctions.command_run_successful(command)

def announce_internet_off(time_period):
    command = "zenity --info --text='<b>Browser internet access is off for %s</b>'" %time_period
    localFunctions.command_run_successful(command)

if __name__ == '__main__':
    description = "Turn internet access on and off."
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, description=description,
                                  perform_parse=True)
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    if check_internet_turned_off():
        if turn_on_dialog():
            if turn_on_internet():
                announce_internet_on()
    else:
        expiration_time_string, time_period = turn_off_dialog()
        if expiration_time_string:
            if turn_off_internet(expiration_time_string):
                announce_internet_off(time_period)
