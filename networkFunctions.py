#!/usr/bin/python3
# -*- coding: utf-8 -*-
# this file contains shared functions for network applications.

import localFunctions
import glob
import os
import re
import subprocess
import time

INTERNET_OFF_FILENAME = "/tmp/internet-off-*.txt"
INTERNET_OFF_DIR = "/tmp"
INTERNET_OFF_PREFIX = "internet-off-"
INTERNET_OFF_SUFFIX = ".txt"
PROGRAM_VERSION = 0.7


def internet_interface_file_network_type():
    """
    Determine the currently configured internet connection type from the
    interfaces link filename
    :return:
    """
    interface_link = localFunctions.run_command("ls -l /etc/network/interfaces",
                                                result_as_list=False)
    type = "ethernet"
    if "wireless" in interface_link:
        type = "wireless"
    if "no_internet" in interface_link:
        type = "no_internet"
    return type


def network_interface_type_count():
    """
    Determine the number of etherent and wireless hardware interfaces
    :return:
    """
    ethernet_count = 0
    wireless_count = 0
    try:
        interfaces = localFunctions.run_command("lshw -c network ",
                                                reraise_error=False, result_as_list=True)
        for line in interfaces:
            if "description: Ethernet" in line:
                ethernet_count += 1
            elif "description: Wireless" in line:
                wireless_count += 1
            if "logical name: bond0" in line:
                # bond0 is a logical rather that physical interface but is reported
                # as etherent. Correct the count.
                ethernet_count -= 1
    except subprocess.CalledProcessError as e:
        localFunctions.add_error_report("Failed to get interfaces information %s"
                                        % e)
    return ethernet_count, wireless_count


def internet_network_interface():
    interface_name_list = localFunctions.findall_in_file("/etc/network/interfaces",
                                                         r'external.*?iface\s+(\w+)')
    if interface_name_list:
        return interface_name_list[0]
    else:
        return ""


def interface_is_up(interface_name):
    command = "ip link |grep %s |grep UP" % interface_name
    return localFunctions.run_command(command, result_as_list=False) != ""


def proxy_server_working():
    """
    Confirm that the proxy is workingis by making a http query to the
    local webserver at the proxy port.
    """
    command = "nc -w 1 main-server.lcl 3128"
    return localFunctions.command_run_successful(command)


def internet_should_be_off(restart=False):
    """
    Check for internet off flag files, remove expired ones, and check again.
    An empty flag file is invalid so it is removed immediately.
    Return the count of files left -f nonzero squid should be off.
    :return:
    """
    compare_time = int(time.time())
    expire_text = ""
    for flag_file in glob.iglob(INTERNET_OFF_FILENAME):
        with open(flag_file, "r") as f:
            expire_time_string = f.read()
            f.close()
            if not expire_time_string:
                os.remove(flag_file)
            elif int(expire_time_string) == 0:
                expire_text = "until server reboot"
            elif int(expire_time_string) > compare_time:
                time_remaining = int(expire_time_string) - compare_time
                expire_text = "in less %d minutes" % ((int((time_remaining + 150) / 300) + 1) * 5)
            else:
                os.remove(flag_file)
        if not glob.glob(INTERNET_OFF_FILENAME) and restart:
            # all files have just been removed so should restart
            localFunctions.command_run_successful("systemctl restart squid")
            time.sleep(4)
    return expire_text


def get_wireless_statistics(wireless_interface=" "):
    name = ""
    quality = ""
    signal_level = ""
    data = localFunctions.run_command("iwconfig " + wireless_interface,
                                      result_as_list=False)
    match_list = re.search(r'ESSID:"([^"]+)".+Quality=(\d+\/\d+).+Signal level=([-\w ]+)',
                           data, re.S)
    if match_list:
        name, quality, signal_level = match_list.groups()
    return name, quality, signal_level


def get_wireless_info():
    scan_info = localFunctions.run_command("iwlist scan 2>/dev/null", result_as_list=True,
                                           merge_stderr=False)
    interfaces = []
    ids = []
    qualities = []
    if len(scan_info) > 1:
        for line in scan_info:
            if "No scan results" in line:
                interfaces.append(line.split()[0])
                break
            if "Failed to read scan data" in line:
                interfaces.append(line.split()[0])
                break
            if "Scan completed" in line:
                interfaces.append(line.split()[0])
            elif "ESSID:" in line:
                ids.append(line.split('"')[1])
            elif "Quality=" in line:
                qualities.append(line.split()[0])
    return interfaces, ids, qualities


def get_wireless_name():
    scan_info = localFunctions.run_command("iwconfig 2>/dev/null", result_as_list=True,
                                           merge_stderr=False)
    interfaces = []
    for index in range(1, len(scan_info)):
        if scan_info[index].strip().startswith("Mode:"):
            interfaces.append(scan_info[index - 1].split()[0])
    return interfaces


def write_wireless_network_file(filename, interface_name, wireless_network_name="UNKNOWN",
                                password="UNKNOWN"):
    """
    Write the block into the interfaces file for the wireless internet interface
    :param filename:
    :param interface_name:
    :param wireless_network_name:
    :param password:
    :return:
    """
    network_block = """allow-hotplug %s
iface %s inet dhcp
wpa-ssid %s
wpa-psk  %s
""" % (interface_name, interface_name, wireless_network_name, password)
    temp_filename = os.path.join("/tmp", os.path.basename(filename))
    try:
        in_file = open(filename, "r")
        out_file = open(temp_filename, "w")
        skip = False
        skipped_lines = 0
        for line in in_file:
            if "(wireless)" in line:
                skip = True
                out_file.write(line)
                out_file.write(network_block)
                continue
            # do not write old network block. use line count as
            # failsafe if #end not found
            elif skip and "#end" not in line and skipped_lines < 6:
                skipped_lines += 1
                continue
            skip = False
            out_file.write(line)
        out_file.close()
        os.rename(temp_filename, os.path.realpath(filename))
    except OSError as e:
        print("Failed to write interfaces file for wireless: %s" % e)
