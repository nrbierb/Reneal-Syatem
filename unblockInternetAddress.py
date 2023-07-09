#!/usr/bin/python3
# -*- coding: utf-8 -*-

import localFunctions
import subprocess
import sys

SQUIDGUARD_BLACKLIST = "editable-blacklist"
SQUIDGUARD_DB = "/var/lib/squidguard/db/editable-blacklist/domains"
BACKUP_DB = "/var/lib/squidguard/db/editable-blacklist/domains.older"
DESCRIPTION = "Remove a website from the blocked list to allow browser access."

PROGRAM_NAME = "unblockInternetAddress"
PROGRAM_VERSION = "0.5"


def get_block_for_removal():
    """
    Show form to get a new blocked address
    :return:
    """
    command = """cat %s | yad --list --text="Select Website To Not Block" \
                --title="Unblock Website" \
                --column="Blocked Websites" --width 400 --height 400 """ % SQUIDGUARD_DB
    try:
        remove_choice = localFunctions.run_command(command, reraise_error=True,
                                                   result_as_list=False)
    except subprocess.CalledProcessError:
        confirm_cancel()
    if not remove_choice:
        warn_nothing_set()
    return remove_choice.strip().strip("|")


def remove_block_from_blacklist(blocked_address):
    """
    :param blocked_address:
    :return:
    """
    try:
        with open(SQUIDGUARD_DB, 'r') as f:
            blocked_addrs = f.readlines()
        remove_address = blocked_address + "\n"
        remove_index = blocked_addrs.index(remove_address)
        if remove_index == -1:
            warn_not_in_list(blocked_address)
        blocked_addrs.pop(remove_index)
        localFunctions.copy_file(SQUIDGUARD_DB, BACKUP_DB)
        with open(SQUIDGUARD_DB, "w") as f:
            f.writelines(blocked_addrs)
    except (IndexError, OSError):
        warn_update_problem()


def update_and_restart_squid():
    command = "/usr/bin/squidGuard -c /etc/squidguard/squidGuard.conf.editable-only -C all"
    updated = localFunctions.command_run_successful(command)
    if updated:
        command = "chown -R proxy:proxy /var/lib/squidguard/db"
        localFunctions.command_run_successful(command)
        command = "systemctl restart squid"
        updated = localFunctions.command_run_successful(command)
    return updated


def confirm_cancel():
    command = 'zenity --info --title="Canceled" --text="<b>Block Websites Canceled.\nNothing changed.</b>"'
    localFunctions.command_run_successful(command)
    sys.exit()


def warn_nothing_set():
    command = 'zenity --error --title="Nothing Set" --text="<b>No address was entered</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="Nothing Set", quiet=True)


def warn_not_in_list(blocked_address):
    text = "<b>'%s' is not in the blocked list.</b>" % blocked_address
    command = 'zenity --error --title="Not In List" --text="%s"' % text
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="Not in list", quiet=True)


def announce_update(blocked_address):
    text = "<b>'%s' has been removed from\n the list of blocked websites</b>" % blocked_address
    command = 'zenity --info --title="Website Block Added" --text="%s"' % text
    localFunctions.command_run_successful(command)


def warn_update_problem():
    command = 'zenity --error --title="Failed Update" --text="<b>Failed to start blocking the website</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="Failed update", quiet=True)


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    target_block = get_block_for_removal()
    remove_block_from_blacklist(target_block)
    if update_and_restart_squid():
        announce_update(target_block)
    else:
        warn_update_problem()
