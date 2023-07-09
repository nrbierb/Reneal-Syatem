#!/usr/bin/python3
# -*- coding: utf-8 -*-

import localFunctions
import subprocess
import sys

SQUIDGUARD_BLACKLIST = "editable-blacklist"
SQUIDGUARD_DB = "/var/lib/squidguard/db/editable-blacklist/domains"
BACKUP_DB = "/var/lib/squidguard/db/editable-blacklist/domains.older"
DESCRIPTION = "Add a new website domain to the blacklist to be blocked."

PROGRAM_NAME = "blockInternetAddress"
PROGRAM_VERSION = "0.5"


def get_new_block():
    """
    Show form to get a new blocked address
    :return:
    """
    invalid_url = False
    command = """yad  --form --field="Block Website:" "" --field="Already Blocked Websites:TXT" \
        "`cat %s`" \
        --title="Add Blocked Website" --button=gtk-cancel:1 --button=gtk-add:0\
        --geometry=500x400 """ % SQUIDGUARD_DB
    try:
        form_data = localFunctions.run_command(command, reraise_error=True, result_as_list=False)
    except subprocess.CalledProcessError:
        confirm_cancel()
    parts = form_data.split("|")
    if len(parts) == 1:
        new_block = ""
    else:
        new_block = parts[0]
        if len(new_block) and len(new_block.split('.')) == 1:
            invalid_url = True
    return new_block, invalid_url


def add_block_to_blacklist(blocked_address):
    """
    :param blocked_address:
    :return:
    """
    try:
        with open(SQUIDGUARD_DB, 'r') as f:
            blocked_addrs = f.readlines()
        new_address = blocked_address + "\n"
        if blocked_addrs.count(new_address):
            warn_already_in_list(blocked_address)
        localFunctions.copy_file(SQUIDGUARD_DB, BACKUP_DB)
        blocked_addrs.append(new_address)
        localFunctions.sort_nicely(blocked_addrs)
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


def warn_invalid_address(blocked_address):
    text = "<b>'%s' is not a\nvalid internet address.</b>" % blocked_address
    command = 'zenity --error --title="Invalid Website Entry" --text="%s"' % text
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="Invalid URL", quiet=True)


def warn_already_in_list(blocked_address):
    text = "<b>'%s' is already\nin the blocked list.</b>" % blocked_address
    command = 'zenity --error --title="Already Blocked" --text="%s"' % text
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="already in list", quiet=True)


def announce_update(blocked_address):
    text = "<b>'%s' has been added\nto the list of blocked websites</b>" % blocked_address
    command = 'zenity --info --title="Website Block Added" --text="%s"' % text
    localFunctions.command_run_successful(command)


def warn_update_problem():
    command = 'zenity --error --title="Failed Update" --text="<b>Failed to start blocking the website</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit(message="Failed update", quiet=True)


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME, use_gui=True)
    new_block, invalid_address = get_new_block()
    if invalid_address:
        warn_invalid_address(new_block)
    if not new_block:
        warn_nothing_set()
        localFunctions.error_exit(message="Nothing read", quiet=True)
    add_block_to_blacklist(new_block)
    if update_and_restart_squid():
        announce_update(new_block)
    else:
        warn_update_problem()
