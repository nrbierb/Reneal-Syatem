#!/usr/bin/python3
# -*- coding: utf-8 -*-

import subprocess
import localFunctions
import os
import os.path
import sys

PRIMARY_DISK_GRUB='grub.cfg.OSprimary'
SECONDARY_DISK_GRUB='grub.cfg.OSprimarySecondDiskDefault'
BASE_MOUNT=""
PROGRAM_VERSION = "0.5"
PROGRAM_NAME = "changeDefaultBootDisk"

def check_grub_file(filename, test_text):
    """
    Confirm the the primary file exists adn seems good
    :param filename:
    :return:
    """
    min_filesize = 7000
    good_file = False
    try:
        if os.path.isfile(filename) and not os.path.islink(filename):
            if os.path.getsize(filename) > min_filesize:
                with open(filename, "r") as f:
                    good_file = test_text in f.read()
    except OSError:
        return False
    return good_file

def check_grub_link(linked_filename, link_name,test_text):
    """

    :param linked_filename:
    :param link_name:
    :return:
    """
    if os.path.isfile(link_name) and os.path.islink(link_name) and \
        os.path.realpath(link_name) == linked_filename:
        return check_grub_file(linked_filename, test_text)

def set_grub_link(grub_directory, new_link_file, test_text):
    """
    Remove the existing link to grub.cfg and link the new filename
    to it.
    :param grub_directory:
    :param new_link:
    :return:
    """
    link_was_set = ""
    grub_link_target = os.path.join(grub_directory, "grub.cfg")
    grub_link_backup = grub_link_target + ".back"
    if os.path.islink(grub_link_target) \
        and check_grub_file(os.path.join(grub_directory, new_link_file),
                            test_text):
        try:
            os.rename(grub_link_target, grub_link_backup)
        except OSError:
            return "rename failed"
        try:
            os.symlink(new_link_file, grub_link_target)
            if not check_grub_link(check_grub_link(new_link_file)):
                return "link did not connect to correct file"
        except OSError:
            try:
                os.rename(grub_link_backup, grub_link_target)
            except OSError:
                return "failed to revert after linking problem"
    return "correctly set link"


#to be continued
