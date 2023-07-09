#!/usr/bin/python3
"""
# ------------------------------------------------------------------------------
# Copyright (C) 2017-2021 Neal R Bierbaum
# This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
# This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
# ------------------------------------------------------------------------------

This utility must be run as root because it uses commands that require
root privilege. It must have root only write permission.
This utility integrates many different tests and checks to provide a
simple way to check key elements of the LTSP server.
It checks these daemons:
  dhcp3
  bind9
  squid
  squidGuard
  shorewall
  nfsd
  apache
  cupsd
  sshd
  mysqld
  ntpd
It uses the smartctl utilty to check for disk problems.
It checks the backup status log files to confirm that backups are being
 performed.
It checks the partition usage to determine if a partition has too little
space left.
It reads the loadmonitor files to check the peak usages.
It checks cpu load by process looking for runaway processes.
It checks network interfaces for activity.
It tests internetfile" connectivity with a ping

This version is for 16.04 only. The commands for managing processes
have been changed so this is reflected in the code. The previous code lines
remain but are commented out.
"""
import argparse
import configparser
import collections
import csv
import itertools
import os
import pwd
import re
import subprocess
import sys
import tabulate
import time
import urllib.error
import urllib.parse
import urllib.request

import PyQt4.QtGui

import localFunctions
import localFunctionsPy3
import backgroundFunctions
import networkFunctions
import rebuildSquidCache
import cleanUsersTrash
import sysChkIO
import systemCheckGui
import checkUserHomeSize
import systemCleanup

# the required daemons list has three values per process: the descriptive name,
# the process name seen in the ps command, and the command for restart

# Daemon names are different for 16.04 because a system status command is used rather
# than an analysis of a ps list
RequiredDaemons1604 = {"isc-dhcp-server": (
    "network boot server", "systemctl restart isc-dhcp-server "),
    "bind9": (
        "internet name server", "systemctl restart  bind9 "),
    #"squid": (
    #    "internet cache server", "systemctl restart squid "),
    "nfs-kernel-server": ("network file system server",
                          "systemctl restart  nfs-kernel-server "),
    "nbd-server": ("network block file server",
                   "systemctl restart nbd-server"),
    "openvpn": ("remote management server",
                "systemctl restart  openvpn "),
    "apache2": (
        "local web server", "systemctl restart  apache2 "),
    "cups-browsed": ("printer queue server",
                     "systemctl restart cups-browsed "),
    "sshd": (
        "remote access server", "systemctl restart  sshd "),
    "mysql": (
        "database server", "systemctl restart  mysql "),
    "ntp": ("time server", "systemctl restart  ntp "),
    "tftpd-hpa": (
        "tftp server", "systemctl restart tftpd-hpa"),
    "shorewall": (
        "firewall / router", "systemctl restart shorewall "),
    "ka-lite": (
        "Kahn Academy server", "systemctl restart ka-lite"),
    "kiwix": ("Wikipedia server", "systemctl restart kiwix"),
    "monitor-inactive": ("rebuild student homes server",
                         "systemctl restart monitor-inactive "),
    "system-monitor": ("system load monitor server",
                       "systemctl restart system-monitor"),
    "system-performance-monitor": (
        "system performance monitor server",
        "systemctl restart system-performance-monitor")}
OtherSystemProcesses = {}
ConfigurationFile = '/etc/systemCheck.conf'
LoadmonitorDir = '/var/log/loadmonitor'
MirrorLogFilename = '/var/log/mirror/mirror.log'
RotatedMirrorLogFilename = '/var/log/mirror/mirror.log.1'
MaxMirrorAge = 2
GrubFilename = '/boot/grub/grub.cfg'
StandardGrubFile = 'grub.cfg.OSprimary'
EmergencyGrubFile = 'grub.cfg.OSprimaryDiskFailure'
MirrorFilename = '/usr/local/etc/mirror/mirror.cfg'
SingleDiskMirrorFile = 'mirror.cfg.OSSingleDiskPrimary'
# global root nameserver that should be a stable address
IpPingTargetAddr = "8.8.8.8"
InternetPingHost = "1.1.1.1"
VPNHost = "10.8.0.1"
MainServerIpAddress = "192.168.2.1"
ProblemReported = False
ProgramVersion = "2.5 LTSP"
ProgramName = "systemCheck"
TestTimerStart = 0.0
LogDirectory = "/var/log/systemCheck"

class Configuration:
    """
    A class to read and store global configuration values. These values
    may come from a configuration file, the command line, or settings 
    in the GUI.
    """

    def __init__(self, read_command_line=True):
        """
        initialization order is important. The file is read first, then the
        command line so that command line args can override config file.
        Later, GUI values may be used to override everything else.
        """
        global ConfigurationFile
        # Set default values
        self.params_dict = \
            dict(internet_available=True, look_for_local_hosts=True,
                 config_filename=ConfigurationFile,
                 report_local_hosts_not_found=True,
                 internet_interface="internet",
                 check_internet_quality=True,
                 unused_interfaces=[],
                 os_version="16.04",
                 screen_dimensions="1280x1024",
                 inactive_daemons=[],
                 use_gui=False,
                 check_networks=True,
                 problems_only=False,
                 default_output_filename="/tmp/systemCheckLog",
                 output_filename="", output_dirname="", write_log=False,
                 user=os.getenv("SUDO_USER"))

        self.command_line_params_dict = {}
        self.config_file_params_dict = {}
        self.gui_params_dict = {}
        if read_command_line:
            self.parse_command_line()
        self.params_dict['config_filename'] = \
            self.command_line_params_dict.get('config_filename',
                                              self.params_dict[
                                                  'config_filename'])
        if 'config_filename' in self.params_dict:
            self.read_configuration_file()
            self.params_dict.update(self.config_file_params_dict)
        self.params_dict.update(self.command_line_params_dict)
        self.generate_default_output_filename()

    def read_configuration_file(self):
        """
        Read a simple configuration file  and return a dictionary with parsed 
        results. The  config_params argument is a dictionary with default
        values to protect against a missing or damaged configuration file
        """
        if "config_filename" in self.params_dict:
            try:
                open(self.params_dict["config_filename"], 'r')
                config = configparser.RawConfigParser({},
                                                      collections.OrderedDict,
                                                      True)
                config.read(self.params_dict["config_filename"])
                try:
                    self.config_file_params_dict["internet_available"] = \
                        config.getboolean("Internet", "internet_available")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict["internet_interface"] = \
                        config.get("Internet", "internet_interface")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict["check_internet_quality"] = \
                        config.getboolean("Internet", "check_internet_quality")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict["look_for_local_hosts"] = \
                        config.get("Network Interfaces", "look_for_local_hosts")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict[
                        "report_local_hosts_not_found"] = \
                        config.get("Network Interfaces",
                                   "report_local_hosts_not_found")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict["os_version"] = \
                        config.get("System", "os_version")
                except configparser.NoOptionError:
                    pass
                try:
                    self.config_file_params_dict["screen_dimensions"] = \
                        config.get("System", "screen_dimensions")
                except configparser.NoOptionError:
                    pass
                val = None
                try:
                    val = config.get("System", "inactive_daemons")
                    self.config_file_params_dict["inactive_daemons"] = []
                except configparser.NoOptionError:
                    pass
                if val:
                    self.config_file_params_dict["inactive_daemons"] = \
                        val.split(",")
                try:
                    val = None
                    val = config.get("Network Interfaces", "unused_interfaces")
                except configparser.NoOptionError:
                    pass
                if val:
                    self.config_file_params_dict["unused_interfaces"] = \
                        [a.strip() for a in val.split(",")]
                else:
                    self.config_file_params_dict["unused_interfaces"] = []
            except IOError:
                pass

    def parse_command_line(self):
        """
        Process any arguments on the command line as the final value for a parameter.
        Normally there will be no arguments.
        """
        global ProgramVersion, ProgramName
        commandline_parser = argparse.ArgumentParser(prog="systemCheck")
        commandline_parser.add_argument('-v', "--version", action='version',
                                        version='%s: %s' % (
                                            ProgramName, ProgramVersion))
        commandline_parser.add_argument('-n', '--no_internet',
                                        dest="no_internet",
                                        action='store_true',
                                        help='No internet available. Do not test internet.')
        commandline_parser.add_argument('-c', "--no_client_check",
                                        dest="no_client_check",
                                        action="store_true",
                                        help="No check for ltsp clients. This will speed up the tests.")
        commandline_parser.add_argument('-C', '--report_no_clients',
                                        help='do not report no ltsp clients as error',
                                        action='store_true',
                                        dest='no_client_report')
        commandline_parser.add_argument('-k', "--no_internet_quality_check",
                                        dest="no_internet_quality_check",
                                        action="store_true",
                                        help="No check for internet quality. This will speed up the tests.")
        commandline_parser.add_argument('-K', '--no-network-check',
                                        action="store_true",
                                        dest="no_network_check",
                                        help="do not perform any lab or internet network test")
        commandline_parser.add_argument('-p', "--problems_only",
                                        dest="problems_only",
                                        action="store_true",
                                        help="report only problems, no progress or suggested actions")
        commandline_parser.add_argument('-q', '--quiet', dest="quiet",
                                        action='store_true',
                                        help="Print final result only.")
        commandline_parser.add_argument('-f', '--config_filename',
                                        dest='config_filename',
                                        default="/etc/systemCheck.conf")
        commandline_parser.add_argument('-o', '--output_file',
                                        dest="output_filename")
        commandline_parser.add_argument('-u', '--unused_interface',
                                        dest='unused_interface',
                                        action='append',
                                        help="This can be used several times for multiple inactive interfaces")
        commandline_parser.add_argument('-i', '--inet_interface,',
                                        dest='inet_interface')
        commandline_parser.add_argument('-m', '--monitor_interval',
                                        dest='monitor_interval',
                                        default=0.0, type=float,
                                        help='The number of past minutes to examine load monitor records')
        commandline_parser.add_argument('-g', '--gui', dest="use_gui",
                                        action='store_true',
                                        help='Run the program in a gui interface')
        try:
            opt = commandline_parser.parse_args()
            if opt.no_internet:
                # change only if set on command line
                self.command_line_params_dict["internet_available"] = False
            if opt.no_client_check:
                # change only if set on command line
                self.command_line_params_dict["look_for_local_hosts"] = False
            if opt.no_client_report:
                # change only if set on command line
                self.command_line_params_dict[
                    "report_local_hosts_not_found"] = False
            if opt.no_internet_quality_check:
                # change only if set on command line
                self.command_line_params_dict["check_internet_quality"] = False
            if opt.no_network_check:
                self.command_line_params_dict["check_networks"] = False
            if opt.no_client_report:
                # change only if set on command line
                self.command_line_params_dict["no_client_report"] = False
            self.command_line_params_dict["quiet"] = opt.quiet
            self.command_line_params_dict["problems_only"] = opt.problems_only
            if opt.config_filename:
                self.command_line_params_dict[
                    "config_filename"] = opt.config_filename
            else:
                self.command_line_params_dict["config_filename"] = ""
            self.command_line_params_dict[
                "output_filename"] = opt.output_filename
            if opt.unused_interface:
                self.command_line_params_dict[
                    'unused_interfaces'] = opt.unused_interface
            if opt.inet_interface:
                self.command_line_params_dict[
                    'inet_interface'] = opt.inet_interface
            self.command_line_params_dict['use_gui'] = opt.use_gui
        except argparse.ArgumentError as e:
            print("Error in the command line argumennts: %s" % e)

    def update_from_gui(self, gui_connector):
        if gui_connector:
            self.params_dict.update(gui_connector.gui_config)
            if gui_connector.gui_config["internet_available"]:
                try:
                    self.params_dict['unused_interfaces'].remove("internet")
                except (KeyError, ValueError):
                    pass
            if self.get_value("write_log"):
                self.set_value("output_filename",
                               config_store.get_value(
                                   "default_output_filename"))
            else:
                self.set_value("output_filename", "")

    def generate_default_output_filename(self):
        if not self.get_value("output_dirname", None):
            userhome = "~%s" % self.get_value("user", "")
            dirname = os.path.join(os.path.expanduser(userhome), "sysCheckLog")
            if os.path.isdir(dirname):
                self.params_dict["output_dirname"] = dirname
        if os.path.isdir(self.get_value("output_dirname", False)):
            self.params_dict["default_output_filename"] = os.path.join(
                self.get_value("output_dirname"),
                'sysCheckRun' + time.strftime('.%m%d-%H%M')) + '.txt'

    def get_value(self, param_name, default=None):
        return self.params_dict.get(param_name, default)

    def set_value(self, param_name, value):
        self.params_dict[param_name] = value


class NetworkInterface:
    """
    A class that contains all of the data and the test and analysis
    functions for the individual interface. 
    """

    def __init__(self, name, reporter, config):
        self.name = name
        self.reporter = reporter
        self.config = config
        self.used = True
        self.auto = False
        self.allow_hoplug = False
        self.static_ip = False
        self.dhcp_ip = False
        self.slave_interface = False
        self.bond_master = ""
        self.bond_interface = False
        self.local_interface = False
        self.internet_interface = False
        self.wireless_interface = False
        self.vpn_interface = False
        self.loopback_interface = False
        self.ssid = ""
        self.up = False
        self.running = False
        self.ip_address = ""
        self.mac_address = ""
        self.tx_packets = 0
        self.rx_packets = 0
        self.tx_errors = 0
        self.rx_errors = 0
        self.active_hosts = []
        self.hosts_searched = False

    # ----------------------------------------------------------------------
    def slave_interface_master(self):
        """
        If a slave interface return the bond master.
        If not, return ""
        """
        if self.slave_interface:
            return self.bond_master
        else:
            return ""

    # ----------------------------------------------------------------------
    def get_slave_interfaces(self, all_interfaces_list):
        interfaces = []
        if self.bond_interface:
            for interface in all_interfaces_list:
                if (interface.slave_interface and
                        interface.bond_master == self.name):
                    interfaces.append(interface)
        return interfaces

    # ----------------------------------------------------------------------4
    def requires_test(self):
        """
        Check only physical interfaces that are used. includes the
        internet interface if configuration is no internet. Slave interfaces
        are checked in bond interface testing so they are skipped induvidually.
        """
        skip_internet = self.internet_interface and \
                        not self.config.get_value("internet_available", True)
        skip_nonphysical = self.loopback_interface or self.vpn_interface
        return ((not (skip_internet or skip_nonphysical or
                      self.slave_interface)) and self.used)

    # ----------------------------------------------------------------------
    def fully_active(self):
        return (self.up and self.running and self.ip_address and
                (self.tx_packets or self.rx_packets))

    # ----------------------------------------------------------------------
    def set_address_source(self, text):
        if text == "static":
            self.static_ip = True
        elif text == "dhcp":
            self.dhcp_ip = True
        elif text == "loopback":
            self.loopback_interface = True

    # ----------------------------------------------------------------------
    def dhcp_failed(self):
        return (self.running and self.dhcp_ip and
                not self.ip_address)

    # ----------------------------------------------------------------------
    def set_internet_interface(self, is_internet):
        self.internet_interface = is_internet

    # ----------------------------------------------------------------------
    def get_status(self):
        """
        Read ifconfig for current status of interface
        """

        ip_address_info_re = re.compile(r'\s*inet addr:([\d.]+)')
        mac_address_info_re = re.compile(r'\s*HWaddr ([\w:]+)')
        rx_address_info_re = re.compile(r'\s*RX packets:(\d*)\s*errors:(\d*)')
        tx_address_info_re = re.compile(r'\s*TX packets:(\d*)\s*errors:(\d*)')
        detailed_result = str(localFunctions.run_command('/sbin/ifconfig ' +
                                                         self.name, False,
                                                         False))
        self.up = detailed_result.find("UP") != -1
        self.running = (detailed_result.find("RUNNING") != -1)
        self.slave_interface = (detailed_result.find("SLAVE") != -1)
        self.bond_interface = (detailed_result.find("MASTER") != -1)
        for line in detailed_result.splitlines():
            address_match_obj = ip_address_info_re.search(line)
            if address_match_obj:
                self.ip_address = \
                    address_match_obj.group(1)
                continue
            address_match_obj = mac_address_info_re.search(line)
            if address_match_obj:
                self.mac_address = \
                    address_match_obj.group(1)
                continue
            count_match_obj = rx_address_info_re.match(line)
            if count_match_obj:
                self.rx_packets = int(count_match_obj.group(1))
                self.rx_errors = int(count_match_obj.group(2))
                continue
            count_match_obj = tx_address_info_re.match(line)
            if count_match_obj:
                self.tx_packets = int(count_match_obj.group(1))
                self.tx_errors = int(count_match_obj.group(2))

    # ----------------------------------------------------------------------
    def get_hosts_on_interface(self):
        """
        Use fping to perform a ping sweep across the subnet to look for
        other active hosts. This should be only on an active, non-slave ethernet
        network. This should be done only after all status tests are complete
        to avoid running on a non-functioning interface. The test is only needed
        on a local interface -- if there is no host (modem) on the internet side
        it will be diagnosed by other test.
        """
        if self.fully_active() and self.requires_test() and self.local_interface:
            address_bytes = self.ip_address.split('.')
            subnet_address = '%s.%s.%s.0' % (address_bytes[0], address_bytes[1],
                                             address_bytes[2])
            command = '/usr/bin/fping  -A -a -r 0 -i 1 -g %s/24 2>/dev/null' \
                      % subnet_address
            try:
                result = localFunctions.run_command(command,
                                                    reraise_error=False,
                                                    result_as_list=True)
                self.hosts_searched = True
                for line in result:
                    if line and (line.find("ICMP") == -1):
                        host_addr = line.split()[0]
                        if not (self.ip_address == host_addr):
                            self.active_hosts.append(host_addr)
            except subprocess.CalledProcessError:
                pass

    # ----------------------------------------------------------------------
    def restart_interface(self):
        """
        Use ifdown and ifup to attempt to restart the interface.
        Report starting the action and the result.
        """
        self.reporter.report_starting_fix("interface restart",
                                          [self.name, self.name])
        # record problem at start
        dhcp_only = self.dhcp_failed()
        if self.up:
            command = "timeout 15 ifdown %s --force" % self.name
            localFunctions.run_command(command)
        command = "ifup %s" % self.name
        localFunctions.run_command(command)
        self.get_status()
        if self.fully_active():
            self.reporter.report_fix_result("interface fixed", [self.name],
                                            fixed=True)
            successful = True
        elif self.dhcp_failed():
            if not dhcp_only:
                # some problem was fixed
                self.reporter.report_fix_result("partial interface fix",
                                                [self.name], fixed=False)
            if self.internet_interface:
                self.reporter.report_requires_user_action_problem(error_message_name="",
                                                                  values=[],
                                                                  action_message_name="restart modem",
                                                                  increment_problem_count=False)
            else:
                self.reporter.report_requires_user_action_problem(error_message_name="",
                                                                  values=[],
                                                                  action_message_name="restart other computer",
                                                                  increment_problem_count=False)
            # adjust for two problems reported - fixable and user actio
            self.reporter.adjust_problems_count(problems_found_change=-1)
            # not really successful, but this blocks further reporting for
            # other error cases when it is really only the dhcp that is bad
            successful = True
        else:
            self.reporter.report_fix_result("interface fix failed", [self.name],
                                            fixed=False)
            successful = False
        return successful

    # ----------------------------------------------------------------------
    def analyze_bond_interface(self, all_interfaces_list):
        """
        Check all bond slave interfaces. This is needs
        to be run only if the bond interface is alive
        itself.
        """
        analysis_complete = False
        if self.bond_interface:
            slave_interfaces = self.get_slave_interfaces(all_interfaces_list)
            interface_position = {"lab1": "top", "lab2": "bottom"}
            if self.fully_active():
                for interface in slave_interfaces:
                    if not interface.running and interface.used:
                        self.reporter.report_requires_user_action_problem(
                            "one lab interface not running",
                            values=[interface.name],
                            action_message_name="one lab interface not running action",
                            action_values=[interface.name,
                                           interface_position.get(
                                               interface.name, "top"),
                                           interface.name, interface.name])
            elif not self.up:
                self.reporter.report_fixable_problem("interface not up",
                                                     [self.name])
                # the interface is fully turned off
                self.restart_interface()
            else:
                interface_phrase = "%d separate ethernet interfaces" % len(slave_interfaces)
                if len(slave_interfaces) == 1:
                    interface_phrase = "a single ethernet interface"
                self.reporter.report_requires_user_action_problem(
                    "bond interface not running",
                    values=[self.name, interface_phrase],
                    action_message_name="turn on network switch",
                    action_values=[])
            analysis_complete = True
        return analysis_complete

    # ----------------------------------------------------------------------
    def analyze_dhcp_interface(self):
        """
        If this is a dhcp interface that is running but does not have an ip address then
        the dhcp from the other end was not run or it failed. Use ifdown and then ifup 
        to try to set it."""
        analysis_complete = False
        if self.dhcp_failed():
            self.reporter.report_fixable_problem("dhcp failed", [self.name])
            self.restart_interface()
            analysis_complete = True
        return analysis_complete

    # ----------------------------------------------------------------------
    def analyze_other_hosts_on_interface(self):
        if (self.fully_active() and self.hosts_searched and
                len(self.active_hosts) == 0):
            # the computers interface always is in the list
            if self.local_interface:
                if self.config.get_value("report_local_hosts_not_found", True):
                    self.reporter.report_requires_user_action_problem(
                        error_message_name="no local hosts found problem",
                        values=[],
                        action_message_name="no local hosts found action")
                    # elif self.internet_interface:
                    #        self.reporter.report_problem("no modems found", [self.name])

    # ----------------------------------------------------------------------
    def count_number_of_local_hosts(self):
        count = 0
        if self.local_interface:
            count = len(self.active_hosts)
        return count

    # ----------------------------------------------------------------------
    def analyze_interface(self, all_interfaces_list):
        """
        Perform complete analysis on an individual interface. Loopback, vpn,
        and slave interfaces are ignored.
        """
        if self.requires_test():
            # no longer report error about no clients
            # self.analyze_other_hosts_on_interface()
            if self.analyze_bond_interface(all_interfaces_list):
                pass
            elif self.analyze_dhcp_interface():
                pass
            elif not self.up:
                self.reporter.report_fixable_problem("interface not up",
                                                     [self.name])
                if not self.restart_interface():
                    self.reporter.report_requires_user_action_problem(
                        error_message_name="", values=[],
                        action_message_name="interface could not come up",
                        action_values=[self.name],
                        increment_problem_count=False)
            elif not self.running:
                if self.wireless_interface:
                    self.reporter.report_requires_user_action_problem(
                        error_message_name="wireless not running",
                        values=[self.name],
                        action_message_name="check wireless")
                else:
                    if self.internet_interface:
                        other_end = "internet modem"
                    else:
                        other_end = "ethernet switch"
                    self.reporter.report_requires_user_action_problem(
                        error_message_name="interface not running",
                        values=[self.name],
                        action_message_name="check cable",
                        action_values=[self.name, other_end])


class DiskInfo:

    def __init__(self, name, device, primary, system_checker):
        self.name = name
        self.device = device
        self.primary = primary
        self.system_checker = system_checker
        self.exists = True
        self.bad = False
        self.health = ""
        self.active_os = False

    def check_disks_health(self):
        """Perform smart check to determine health from report.
        Note the this now uses /usr/local/sbin/new-smartctl, the most current
        version as of April 2022 which was built on the server. It understands
        nvme disks."""
        try:
            self.exists = localFunctions.command_run_successful(
                '/usr/local/sbin/smartctl --info ' + self.device)
            try:
                command = "/usr/local/sbin/smartctl -H " + self.device
                check_result = localFunctions.run_command(command,
                                                          result_as_list=False)
                regexp_options = re.MULTILINE | re.IGNORECASE
                # This is for test only!!!!!!!!!!!!!!!!!!!!!!!!
                # if self.device == "/dev/sdNone":
                #     check_result = """
                #     smartctl 5.41 2011-06-09 r3365 [x86_64-linux-3.2.0-74-generic] (local build)
                #     Copyright (C) 2002-11 by Bruce Allen, http://smartmontools.sourceforge.net
                #
                #     === START OF READ SMART DATA SECTION ===
                #     SMART overall-health self-assessment test result: FAILED
                #      """
                if len(re.findall(r'result:\s+(fail)', check_result,
                                  regexp_options)):
                    self.bad = True
                    # header shows that disk is failing so report all of disk test
                    command = '/usr/sbin/smartctl -a ' + self.device
                    self.health = localFunctions.run_command(
                        command,
                        result_as_list=False)
            except subprocess.CalledProcessError as e:
                self.health = e.output
                # bit 3 indicates the disk is failing
                if e.returncode & 8:
                    self.bad = True
        except Exception as e:
            self.system_checker.function_errors["check_disks_health"] = str(e)

    # Code using old smartctl
    # def check_disks_health(self):
    #     if self.device.startswith("/dev/nvme"):
    #         self.check_nvme_disks_health()
    #     else:
    #         self.check_sd_disk_health()
    #
    # def check_sd_disk_health(self):
    #     """
    #     Use smartctl to check disk state.
    #     """
    #     try:
    #         self.exists = localFunctions.command_run_successful(
    #             '/usr/sbin/smartctl --info ' + self.device)
    #         try:
    #             command = "/usr/sbin/smartctl -H " + self.device
    #             check_result = localFunctions.run_command(command,
    #                                                       result_as_list=False)
    #             regexp_options = re.MULTILINE | re.IGNORECASE
    #             # This is for test only!!!!!!!!!!!!!!!!!!!!!!!!
    #             # if self.device == "/dev/sdNone":
    #             #     check_result = """
    #             #     smartctl 5.41 2011-06-09 r3365 [x86_64-linux-3.2.0-74-generic] (local build)
    #             #     Copyright (C) 2002-11 by Bruce Allen, http://smartmontools.sourceforge.net
    #             #
    #             #     === START OF READ SMART DATA SECTION ===
    #             #     SMART overall-health self-assessment test result: FAILED
    #             #      """
    #             if len(re.findall(r'result:\s+(fail)', check_result,
    #                               regexp_options)):
    #                 self.bad = True
    #                 # header shows that disk is failing so report all of disk test
    #                 command = '/usr/sbin/smartctl -a ' + self.device
    #                 self.health = localFunctions.run_command(
    #                     command,
    #                     result_as_list=False)
    #         except subprocess.CalledProcessError as e:
    #             self.health = e.output
    #             # bit 3 indicates the disk is failing
    #             if e.returncode & 8:
    #                 self.bad = True
    #     except Exception as e:
    #         self.system_checker.function_errors["check_disks_health"] = str(e)
    #
    # def check_nvme_disks_health(self):
    #     """
    #     Use smartctl to check disk state.
    #     """
    #     try:
    #         self.exists = localFunctions.command_run_successful(
    #             '/usr/sbin/nvme list | grep "%s"' %self.device)
    #         try:
    #             command = "/usr/sbin/nvme smart-log " + self.device
    #             check_result = localFunctions.run_command(command,
    #                                                       result_as_list=False)
    #             regexp_options = re.MULTILINE | re.IGNORECASE
    #             error_count = re.findall(r'^critical_warning\s+:\s+(\d+)', check_result,
    #                               regexp_options)
    #             if int(error_count[0]) > 0:
    #                 self.bad = True
    #                 self.health = localFunctions.run_command(
    #                     command, result_as_list=False)
    #         except subprocess.CalledProcessError as e:
    #             self.health = e.output
    #             # bit 3 indicates the disk is failing
    #             if e.returncode & 8:
    #                 self.bad = True
    #     except Exception as e:
    #         self.system_checker.function_errors["check_disks_health"] = str(e)

    def set_active_os(self):
        self.active_os = True


class SystemChecker:
    """
    The class defines the functions to perform many different system checks fo
    the main-server of an LSTP computer center. These functions collect data 
    that is then used in analysis of system status and problems.
    """

    # ----------------------------------------------------------------------
    def __init__(self, reporter, config):
        global RequiredDaemons1604, OtherSystemProcesses
        self.reporter = reporter
        self.config = config
        self.daemons_list = RequiredDaemons1604
        self.other_system_processes_list = OtherSystemProcesses
        # remove inactive daemons from list
        if self.config.get_value("inactive_daemons", None):
            for inactive_daemon in self.config.get_value("inactive_daemons",
                                                         None):
                try:
                    self.daemons_list.pop(inactive_daemon, None)
                except KeyError:
                    pass
        self.requires_daemon_recheck = False
        self.function_errors = {}
        self.failed_processes = {}
        self.disks = {}
        self.primary_disk_device = "/dev/sda"
        self.disk_health_bad = False
        self.disk_mounts = {}
        self.using_backup_disk = False
        self.fs_backup_days_ago = {}
        self.fs_backup_failures = set()
        self.full_backup_days_ago = 0
        self.full_backup_failed = False
        self.last_backup_too_old = True
        self.empty_backup_log_file = True
        self.required_partitions = []
        self.requires_partition_recheck = False
        self.partition_free_space = {}
        self.partition_full = False
        self.ltsp_arch = "amd64"
        self.ltsp_image_ok = True
        self.load_monitor_minutes = 0.0
        self.load_above_70_minutes = 0.0
        self.load_above_80_minutes = 0.0
        self.network_interfaces = {}
        self.internet_interface = ""
        self.default_router = None
        self.router_ping_successful = False
        self.internet_ping_successful = False
        self.internet_accessible = False
        self.internet_quality = "Unknown"
        self.proxy_ok = False
        self.analyze_internet_access_retries = 0
        self.local_nameserver_alive = False
        self.internal_dns_good = False
        self.dns_good = False
        self.dns_initially_good = False
        self.local_nameserver_good = False
        self.dns_timed_out = False
        self.initial_nameserver = ""
        self.nameserver_changed = False
        self.problem_processes = {}
        self.proxy_server_ok = False
        self.kahn_academy_server_ok = False
        self.suggest_reboot = False
        self.fixed_problems = False
        self.target_number_remaining_accounts = 50
        self.student_accounts_removed = 0
        self.active_users = localFunctions.get_all_active_users_by_class()
        self.create_unused_interfaces()

    # ----------------------------------------------------------------------
    def check_daemons(self):
        """ 
        Check the running processes for all names contained in the process_name
        list. As each is found remove the name from the list. The list returned
        has only the processes that could not be found. This list should be
        empty.
        """
        try:
            # initialize failed_processes for fresh run each time
            self.failed_processes = {}
            for daemon_name in self.daemons_list.keys():

                result = localFunctions.run_command("systemctl is-active %s"
                                                    % daemon_name)
                if result[0] != "active":
                    #    print("%s: %s" %(daemon_name,result[0]))
                    # if not localFunctions.run_command("systemctl is-active %s |grep 'active'" %daemon_name):
                    self.failed_processes[daemon_name] = self.daemons_list[
                        daemon_name]
        except Exception as e:
            self.function_errors["check_daemons"] = str(e)

    # ----------------------------------------------------------------------
    def discover_disks(self):
        """
        Determine the device names of the system drives. There should normally be two devices, but
        for a single disk computer there iwll only be one. Hard drives have prefixes sd and nvme
        M.2 drives have prefixes "nvme". If there is a nvme drive it will be the primary.
        :return:
        """
        command = "lsblk -d -n -o NAME |grep -v sr |sort"
        all_disks = localFunctions.run_command(command, reraise_error=True, merge_stderr=False)
        system_disks = []
        for devname in all_disks:
            if devname.startswith("sd"):
                command = "find /dev/disk/by-id/ -lname '*%s'| grep 'ata'" %devname
                if localFunctions.command_run_successful(command):
                    system_disks.append("/dev/%s" %devname)
            elif devname.startswith("nvme"):
                system_disks.append("/dev/%s" % devname)
        self.disks[system_disks[0]] = DiskInfo("Primary Disk", system_disks[0], True, self)
        self.primary_disk_device = system_disks[0]
        try:
            if (not self.check_single_disk_system()) and len(system_disks) > 1:
                self.disks[system_disks[1]] = DiskInfo("Backup Disk", system_disks[1], False, self)
        except OSError:
            pass

    # ----------------------------------------------------------------------
    def check_disks_health(self):
        self.discover_disks()
        for disk in self.disks.values():
            disk.check_disks_health()
            if disk.bad:
                # recheck so it is not just an anaomoly
                time.sleep(0.5)
                disk.check_disks_health()
            if disk.bad or (not disk.exists):
                self.disk_health_bad = True

    # ----------------------------------------------------------------------
    def map_filesystems_disks(self):
        """
        Determine which disk has the active and /client_home partitions.
        """
        try:
            cleaner_re = re.compile(r'(^\D*)')
            result = localFunctions.run_command('df -l -t ext4')
            for line in result:
                # only read disk partition lines
                if line[0] == "/":
                    columns = line.split()
                    mount_point = columns.pop()
                    match_group = cleaner_re.match(columns[0])
                    if match_group:
                        self.disk_mounts[mount_point] = match_group.group(0)
            try:
                self.disks[self.disk_mounts['/']].set_active_os()
            except KeyError:
                self.disks[self.primary_disk_device].set_active_os()
            self.check_using_backup_disk()
        except Exception as e:
            self.function_errors["check_disks_health"] = str(e)

    # ----------------------------------------------------------------------
    def check_single_disk_system(self):
        return (
            os.path.realpath("/boot/grub/grub.cfg") == "/boot/grub/grub.cfg.OSprimarySingleDisk"
            or os.path.realpath("/boot/grub/grub.cfg") == "/boot/grub/grub.cfg.OScopySingleDisk" )

    # ----------------------------------------------------------------------
    def check_using_backup_disk(self):
        """
        Parse the fstab to confirm active disk even if the dev is renamed by the OS
        :return:
        """
        try:
            with open("/etc/fstab") as f:
                fstab_text = f.read()
                if re.search(r'--Secondary Server Disk Active--', fstab_text):
                    self.using_backup_disk = True
                    self.reporter.report_values("running on backup disk", [])
        except OSError:
            pass

    # ----------------------------------------------------------------------
    def get_using_backup_disk(self):
        return self.using_backup_disk

    # ----------------------------------------------------------------------
    def check_last_backup_time(self):
        """
        Read the copy disk log file to determine the time of the last backup.
        The entry for each mirror is: time partition-name action. The action
        is either "started","completed", or "failed" and the time is in the
        standard time.ctime format. The results are overwritten until the
        the final instance of the file.
        """
        global MirrorLogFilename, RotatedMirrorLogFilename, MaxMirrorAge
        try:
            completion_re = re.compile(
                r'\+\+.*\((\d*\.\d*)\).*---DailyJobs--- completed')
            completion_failed_re = re.compile(
                r'--.*\((\d*\.\d*)\).*---DailyJobs--- failed')
            fs_re = re.compile(r'\+\+.*\((\d*\.\d*)\)\s*\S*\s*(\S*).*completed')
            fs_failed_re = re.compile(r'--.*\((\d*\.\d*)\)\s*\S*\s*(\S*).*failed')
            if os.path.exists(MirrorLogFilename) and os.path.getsize(MirrorLogFilename):
                logname = MirrorLogFilename
            else:
                logname = RotatedMirrorLogFilename
            logfile = open(logname, 'r')
            completion_time = 0.0
            fs_completion_time = {}
            for line in logfile:
                self.empty_backup_log_file = False
                completion_match = completion_re.match(line)
                completion_failed_match = completion_failed_re.match(line)
                fs_match = fs_re.match(line)
                fs_failed_match = fs_failed_re.match(line)
                if completion_match:
                    comp_time = float(completion_match.group(1))
                    if comp_time > completion_time:
                        completion_time = comp_time
                        self.full_backup_failed = False
                elif completion_failed_match:
                    comp_time = float(completion_failed_match.group(1))
                    if comp_time > completion_time:
                        completion_time = comp_time
                        self.full_backup_failed = True
                elif fs_match:
                    comp_time, fs_name = float(fs_match.group(1)), fs_match.group(2)
                    if fs_name not in fs_completion_time:
                        fs_completion_time[fs_name] = comp_time
                    elif comp_time > fs_completion_time[fs_name]:
                        fs_completion_time[fs_name] = comp_time
                    self.fs_backup_failures.discard(fs_name)
                elif fs_failed_match:
                    comp_time, fs_name = float(fs_failed_match.group(1)), fs_failed_match.group(2)
                    if fs_name not in fs_completion_time:
                        fs_completion_time[fs_name] = comp_time
                    elif comp_time > fs_completion_time[fs_name]:
                        fs_completion_time[fs_name] = comp_time
                    self.fs_backup_failures.add(fs_name)
            self.full_backup_days_ago, interval = \
                prior_time_name(completion_time)
            self.last_backup_too_old = (interval > MaxMirrorAge)
            for name in fs_completion_time:
                self.fs_backup_days_ago[name], interval = prior_time_name(fs_completion_time[name])
            logfile.close()
        except OSError:
            # mirror log file was not present
            self.last_backup_too_old = True
            self.empty_backup_log_file = True
            self.full_backup_failed = False
            # create an empty file for the future
            f = open(MirrorLogFilename, "a")
            f.close()

    # ----------------------------------------------------------------------
    def fsck_partition(self, partition, file_system):
        """
        Perform a forced fsck of a partition. Report result in text
        associated with return code.
        """
        self.reporter.report_fixable_problem("filesystem requires check",
                                             [partition,
                                              file_system])
        self.reporter.report_starting_fix("fsck start", [partition,
                                                         file_system,
                                                         partition])
        ok_to_mount = True
        try:
            command = "/sbin/fsck -fp " + partition
            localFunctions.run_command(command, reraise_error=True)
            self.reporter.report_fix_result("fsck no errors", fixed=True)
        except subprocess.CalledProcessError as e:
            result = int(e.returncode)
            report = e.output
            if result == 1:
                self.reporter.report_fix_result("fsck errors corrected",
                                                fixed=True)
            else:
                self.reporter.report_serious_problem("fsck failed",
                                                     [file_system, partition])
                self.reporter.report_requires_user_action_problem(
                    error_message_name="", values=[],
                    action_message_name="run fsck",
                    action_values=[partition], increment_problem_count=False)
                # adjust for two problems reported - fixable and user action
                self.reporter.adjust_problems_count(problems_found_change=-1)
                ok_to_mount = False
        return ok_to_mount

    # ----------------------------------------------------------------------
    def get_required_file_systems(self):
        """
        Read /etc/fstab to find partitions which are auto mounted.
        """
        fstab = open("/etc/fstab", "r")
        for line in fstab:
            if ((line.find("UUID") != -1) and
                    (line.find("noauto") == -1) and
                    (line.find("#") == -1)):
                columns = line.split()
                file_system = {"partition": columns[0],
                               "mount point": columns[1]}
                self.required_partitions.append(file_system)

    # ----------------------------------------------------------------------
    def check_mounted_partitions(self):
        """
        Confirm that all partitions which should be mounted are mounted.
        If not, perform an fsck, then attempt to mount.
        """
        self.requires_partition_recheck = False
        self.get_required_file_systems()
        for fs in self.required_partitions:
            if fs["mount point"] not in localFunctions.get_mounted_filesystems():
                self.handle_unmounted_filesystem(fs)

    # ----------------------------------------------------------------------
    def check_partitions_free_space(self):
        """ 
        Use df to determine the remaining space in the partitions listed in
        the partition list. It returns a dictionary indexed by partitions of
        space remaining.
        """
        try:
            du_table = localFunctions.run_command(
                '/bin/df --local --type=ext4 --output=used,avail,target',
                reraise_error=True, merge_stderr=False, no_stderr=True)
        except subprocess.CalledProcessError as e:
            # The output will probably still have valid partition names
            # along with the error info
            du_table = e.output.splitlines()
            self.function_errors["check_partitions_free_space"] = e.returncode
        required_filesystems = [v["mount point"] for v in
                                self.required_partitions]
        for line in du_table:
            data_values = line.split()
            if data_values[2] in required_filesystems:
                used = float(data_values[0])
                avail = float(data_values[1])
                percent = round((avail / (used + avail)) * 100.0, 1)
                self.partition_free_space[data_values[2]] = \
                    {"percent": percent, "amount": round(avail / 1.0e6, 1)}
                if percent < 10.0:
                    self.partition_full = True
        #
        # result_re = re.compile(r'(\d+)%\s+(\S+)')
        # #result_re = re.compile(r'(\d+)(\S)')
        # for partition in partitions:
        #     if partition.startswith("/dev/sd"):
        #         match_obj = result_re.search(partition)
        #         if match_obj:
        #             percent_used, mount_point = match_obj.groups()
        #             self.partition_free_space[mount_point] = \
        #                 100 - int(percent_used)
        #             if float(percent_used) > 90.0:
        #                 #flag that at least one partition needs further work
        #

    # ----------------------------------------------------------------------
    def read_loadmonitor_file(self, filename, max_time_difference=0.0):
        """
        Parse loadmonitor csv file to read monitoring periods, load, memory, and
        swap usage. 
        """
        data_lines = []
        if max_time_difference:
            earliest_time = time.time() - max_time_difference * 60.0
        else:
            earliest_time = 0.0
        try:
            f = open(filename, "r")
            reader = csv.DictReader(f, restkey="Other", restval=0.0)
            for row in reader:
                if "Epoch Time" in row:
                    if float(row["Epoch Time"]) < earliest_time:
                        # skip lines before the earliest time to be analyzed
                        continue
                    else:
                        data_lines.append(row)
        except IOError as e:
            self.function_errors["check_recent_max_loads"] = str(e)
        return data_lines

    # ----------------------------------------------------------------------
    def check_recent_max_loads(self):
        """
        Read the recent loadmonitor files to determine peak loads. The file is in
        a csv form. The file entries only in the last monitor_interval minutes
        will be used. 
        """
        global LoadmonitorDir
        # 15 second sample intervals
        minutes_per_entry = 15.0 / 60.0
        try:
            # As a simple initial implementation read only the most
            # recent file.
            loadmon_files = os.listdir(LoadmonitorDir)
            # all files but the current have been compressed so they
            # have a gz extension
            for filename in loadmon_files:
                if filename.endswith(".csv"):
                    full_path = LoadmonitorDir + "/" + filename
                    data_lines = self.read_loadmonitor_file(full_path,
                                                            self.config.get_value(
                                                                "monitor_interval",
                                                                30.0))
                    cpu_loading = list(itertools.repeat(0, 10))
                    for line in data_lines:
                        cpu_loading[
                            int((0.999999 - float(line["CPU Idle"])) * 100)
                            // 10] += 1
                    self.load_monitor_minutes = len(
                        data_lines) * minutes_per_entry
                    if self.load_monitor_minutes < 10.0:
                        #too little time for valid values
                        self.load_above_70_minutes = 0.0
                        self.load_above_80_minutes = 0.0
                    else:
                        self.load_above_70_minutes = cpu_loading[
                                                         7] * minutes_per_entry
                        self.load_above_80_minutes = cpu_loading[
                                                         8] * minutes_per_entry
        except Exception as e:
            self.function_errors["check_recent_max_loads"] = str(e)

    # ----------------------------------------------------------------------
    def create_unused_interfaces(self):
        """
        Create all unused interfaces from the configuration file.
        These will be ignored in tests.
        """
        for interface_name in self.config.get_value("unused_interfaces", None):
            if interface_name != '""':
                self.initialize_interface_record(interface_name)
                self.network_interfaces[interface_name].used = False

    # ----------------------------------------------------------------------
    def initialize_interface_record(self, interface_name):
        if interface_name not in self.network_interfaces:
            self.network_interfaces[interface_name] = \
                NetworkInterface(interface_name, self.reporter, self.config)
        return self.network_interfaces[interface_name]

    # ----------------------------------------------------------------------
    def get_interface_record(self, interface_name):
        try:
            return self.network_interfaces[interface_name]
        except KeyError:
            return None

    # ----------------------------------------------------------------------
    def parse_interfaces_file(self):
        interfaces_file = '/etc/network/interfaces'
        iface_re = re.compile(r'\s*iface\s+(\w+)\s+inet\s+(\w+)')
        slave_re = re.compile(r'\s*bond-master\s*(\S*)')
        auto_re = re.compile(r'\s*auto\s+(\w+)')
        hotplug_re = re.compile(r'\s*allow-hotplug\s+(\w+)')
        ssid_re = re.compile(r'\s*wpa-ssid\s+(\w+)')
        try:
            f = open(interfaces_file, 'r')
            current_interface = None
            for line in f:
                match_obj = iface_re.match(line)
                if match_obj:
                    current_interface = self.initialize_interface_record(
                        match_obj.group(1))
                    current_interface.set_address_source(match_obj.group(2))
                    continue
                # auto and hotplug are not used now
                # match_obj = auto_re.match(line)
                # # note, because the auto line could be either before or after the iface
                # # line we will act as if the auto might be first defining an interface
                # # we won't change the current interface because the rest of the interface
                # # parameters must immediately follow the iface line
                # if match_obj:
                #     an_interface = self.initialize_interface_record(match_obj.group(1))
                #     an_interface.auto = True
                #     continue
                match_obj = ssid_re.match(line)
                if match_obj:
                    current_interface.wireless_interface = True
                    current_interface.ssid = match_obj.group(1)
                match_obj = slave_re.match(line)
                if match_obj:
                    current_interface.slave_interface = True
                    current_interface.bond_master = match_obj.group(1)
        except (IOError, re.error):
            return

    # ----------------------------------------------------------------------
    def parse_shorewall_file(self):
        """
        Use the shorewall interfaces definition file to determine the known
        interfaces and their function. 
        """
        shorewall_file = '/etc/shorewall/interfaces'
        interface_re = re.compile(r'\s*(loc|net|vpn)\s+(\w*)', re.I)
        try:
            f = open(shorewall_file, 'r')
            for line in f:
                data = interface_re.match(line)
                if data:
                    interface_name = data.group(2).lower()
                    interface_type = data.group(1).lower()
                    # this will create an interface if necessary, otherwise just
                    # return the existing object
                    interface = self.initialize_interface_record(interface_name)
                    if interface_type == "net":
                        self.internet_interface = interface_name
                        interface.internet_interface = True
                    else:
                        interface.local_interface = (interface_type == 'loc')
                        interface.vpn_interface = (interface_type == "vpn")
        except (IOError, re.error):
            return

    # ----------------------------------------------------------------------
    def initialize_interface_records(self):
        """
        Create all interface objects from data in configuration files.
        """
        self.create_unused_interfaces()
        self.parse_interfaces_file()
        self.parse_shorewall_file()

    # ----------------------------------------------------------------------
    def check_interfaces_state(self):
        """
        Use ifconfig to identify the interfaces and get information about each.
        Do not create an entry for interfaces listed in the config file as unused.
        This will assure that nothing else is done with these.
        """
        try:
            result = localFunctions.run_command('/sbin/ifconfig -a -s')
            interface_info_re = re.compile(
                r'(internet|lab\d+|bond\d+|wlan\d+|ppp\d+|tun\d+)[\s\d]+(\w+)')
            for line in result:
                match_obj = interface_info_re.match(line)
                if match_obj:
                    interface_name, status_flags = match_obj.groups()
                    interface = self.get_interface_record(interface_name)
                    if interface and interface.used:
                        interface.get_status()
        except Exception as e:
            self.function_errors["check_interfaces_state"] = str(e)

    # ----------------------------------------------------------------------
    def find_hosts_on_interfaces(self):
        """
        Search for hosts that will repond to a ping on 
        qualified networks interfaces
        """
        for interface in self.network_interfaces.values():
            if interface.fully_active():
                if ((self.config.get_value("look_for_local_hosts", True) and
                     interface.local_interface) or
                        (self.config.get_value("internet_available", True) and
                         interface.internet_interface)):
                    interface.get_hosts_on_interface()

    # ----------------------------------------------------------------------
    def find_default_router(self):
        """
        Use the "route" command to get the default router.
        This can then be quickly used to test the net interface.
        If there is no default route then other internet tests will not work.
        """
        command = "route -n"
        default_route_re = re.compile(r'^0\.0\.0\.0\s+(\S+)\s+0\.0\.0\.0')
        try:
            result = localFunctions.run_command(command)
            for line in result:
                match_obj = default_route_re.match(line)
                if match_obj:
                    self.default_router = match_obj.group(1)
                    self.check_router_connection()
                    break
        except Exception as e:
            self.function_errors["find_default_router"] = str(e)

    # ----------------------------------------------------------------------
    def check_router_connection(self):
        try:
            if self.network_interfaces[self.internet_interface].running:
                self.router_ping_successful = \
                    localFunctions.command_run_successful(
                        '/bin/ping -qn -c 3 -i 0.2 -W 2 %s >/dev/null 2>&1'
                        % self.default_router)
        except Exception as e:
            self.function_errors["check_router_connection"] = str(e)

    # ----------------------------------------------------------------------
    def check_internet_browsing(self, target_url="http://google.com",
                                max_retries=1):
        """
        Make an http request first through the proxy and then, if that does not
        work and it appears that the proxy is the problem, directly to the web.
        If the request through the proxy works then everything associated with the 
        internet is good.
        """
        # If the dns is no good then don't waste time with this.
        # It won't work.
        if self.analyze_internet_access_retries > max_retries:
            return
        if self.analyze_internet_access_retries > 0:
            self.reporter.report_problem("retrying internet tests",
                                         increment_problem_count=False)
        self.analyze_internet_access_retries += 1
        if not self.dns_good:
            self.internet_accessible = False
            return
        if not networkFunctions.internet_should_be_off():
            try:
                proxy = urllib.request.ProxyHandler(
                    {'http': 'http://main-server:3128'})
                opener = urllib.request.build_opener(proxy)
                query_result = opener.open(target_url)
                self.internet_accessible = True
                self.proxy_ok = True
            except urllib.error.URLError as e:
                errno = e.reason.errno
                self.proxy_ok = False
                try:
                    if errno == 111:
                        # the squid proxy was not working so try again with a
                        # direct one force direct, not a default proxy connection
                        # (works only inside main-server)
                        proxy = urllib.request.ProxyHandler({})
                        opener = urllib.request.build_opener(proxy)
                        query_result = opener.open(target_url)
                        self.internet_accessible = True
                except urllib.error.URLError:
                    self.internet_accessible = False
        else:
            try:
                proxy = urllib.request.ProxyHandler({})
                opener = urllib.request.build_opener(proxy)
                query_result = opener.open(target_url)
                self.internet_accessible = True
                #since the proxy is supposed to be off everything is working
                #as expected. set proxy_ok to True to stop attempts for restart
                #and error reporting
                self.proxy_ok = True
            except urllib.error.URLError:
                self.internet_accessible = False

    # ----------------------------------------------------------------------
    def check_internet_ping(self, known_internet_ip=IpPingTargetAddr):
        """
        Try a ping to a known internet ip address so that there is no
        dendency on DNS. If this works the internet is reachable but still
        might not be usable if there are dns problems.
        """
        try:
            command = '/bin/ping -qn -c 3 -i 0.2 -W 2 %s >/dev/null 2>&1' \
                      % known_internet_ip
            self.internet_ping_successful = localFunctions.command_run_successful(
                command)
        except Exception as e:
            self.function_errors["quick_internet_check"] = str(e)

    # ----------------------------------------------------------------------
    def check_internet_quality(self, target_host=InternetPingHost):
        """
        Test the quality of the internet with a longer ping test to check 
        for dropped packets. If the tun0 (vpn connection to remote server)
        is active, use that with a faster ping rate because it will not
        intentionally slow the ping response.
        """
        if self.config.get_value("check_internet_quality", True):
            if "tun0" in self.network_interfaces and \
                    self.network_interfaces["tun0"].up:
                command = 'ping -i 0.05 -s 200 -c 40 -q %s' % VPNHost
            else:
                command = 'ping -i 0.2 -s 64 -c 30 -q %s' % target_host
            try:
                ping_result = localFunctions.run_command(command, True, False)
                match = re.search(r'(\d+)%', ping_result)
                if match:
                    percent_loss = int(match.group(1))
                    if percent_loss == 0:
                        self.internet_quality = 'Excellent'
                    elif percent_loss < 5:
                        self.internet_quality = 'Good'
                    elif percent_loss < 9:
                        self.internet_quality = 'Fair'
                    elif percent_loss < 19:
                        self.internet_quality = 'Poor'
                    else:
                        self.internet_quality = 'Very Poor / Unusable'
            except subprocess.CalledProcessError:
                self.internet_quality = 'Not Tested'
                pass

    # ----------------------------------------------------------------------
    def check_local_dns_server(self):
        """
        Check if local nameserver has a status of active. If not,restart and
        check again after a short delay.
        """
        try:
            self.local_nameserver_alive = \
                localFunctions.command_run_successful(
                    '/usr/sbin/rndc status > /dev/null')
            if not self.local_nameserver_alive:
                # localFunctions.command_run_successful('service bind9 restart > /dev/null')
                localFunctions.command_run_successful(
                    'systemctl restart bind9 > /dev/null')
                time.sleep(2.0)
                self.local_nameserver_alive = \
                    localFunctions.command_run_successful(
                        '/usr/sbin/rndc status > /dev/null')
        except Exception as e:
            self.function_errors["check_local_dns_server"] = str(e)

    # ---------------------------------------------------------------------
    def make_dns_query(self, dig_args):
        """
        Make a single call with dig with all text after the command line.
        Return the tuple successful_query, unreacheable, nameserver
        """
        successful_query = False
        nameserver = ""
        try:
            result = localFunctions.run_command('dig ' + dig_args, True, False)
            if re.search(r'ANSWER SECTION', result):
                successful_query = True
            server_match = re.search(r'SERVER:\s*([\d.]*)', result)
            if server_match:
                nameserver = server_match.groups()[0]
        except subprocess.CalledProcessError as e:
            if e.returncode == 9:
                # This indicates that the query timed out with no servers
                # reachable -- thus no net access at all
                self.dns_timed_out = True
                self.internet_accessible = False
                successful_query = False
        return successful_query, nameserver

    # ---------------------------------------------------------------------
    def check_dns(self):
        """
        Check function of local nameserver and then full function.
        """
        try:
            # flush cache to assure the coming dns queries will come from the net
            # This fails if the local nameserver is dead
            self.local_nameserver_alive = \
                localFunctions.command_run_successful(
                    '/usr/sbin/rndc flush > /dev/null')
            # if the localname server is alive make a query that
            # does not require internet
            if self.local_nameserver_alive:
                self.internal_dns_good, server = self.make_dns_query(
                    '-x 127.0.0.1')
            # try to resolve a name
            self.dns_initially_good, self.initial_nameserver = \
                self.make_dns_query('google.com')
            if not (self.initial_nameserver == MainServerIpAddress or
                    self.initial_nameserver == "127.0.0.1"):
                self.local_nameserver_good, server = \
                    self.make_dns_query('@127.0.0.1 google.com')
            else:
                self.local_nameserver_good = self.dns_initially_good
            self.dns_good = self.dns_initially_good
        except Exception as e:
            self.function_errors['check_dns'] = str(e)

    @staticmethod
    def parse_time_string(time_string_with_colons):
        try:
            split_values = time_string_with_colons.split(":")
            if len(split_values) == 1:
                value = float(split_values[0])
            elif len(split_values) == 2:
                value = 60.0 * float(split_values[0]) + float(split_values[1])
            elif len(split_values) == 3:
                value = 3600.0 * float(split_values[0]) + 60.0 * float(split_values[1]) + \
                        float(split_values[2])
            elif len(split_values) == 4:
                value = 86400.0 * float(split_values[0]) + 3600.0 * float(split_values[1]) + \
                        60.0 * float(split_values[2]) + float(split_values[3])
            else:
                value = 1.0
            return value
        except (IndexError, ValueError, AttributeError):
            return 1.0

    # ----------------------------------------------------------------------
    def check_process_usage(self, param='pcpu', limit=80.0, scale_factor=1.0):
        try:
            command = '/bin/ps -e --no-headers --format=%s,pid,user,etime,time,args:40 --sort=-%s' \
                      % (param, param)
            processes = localFunctions.run_command(command, reraise_error=True)
            self.problem_processes[param] = {}
            for process in processes:
                proc_stats = process.split()
                if param == "pcpu":
                    try:
                        value = 1.0
                        # assure that the process has been running a while and has been using a
                        # a high percentage of cpu
                        etime_sec = self.parse_time_string(proc_stats[3])
                        if etime_sec > 180.0:
                            atime_sec = self.parse_time_string(proc_stats[4])
                            if (atime_sec / etime_sec) > 0.7:
                                value = float(proc_stats[0])
                    except (IndexError, ValueError):
                        value = 1.0
                else:
                    value = float(proc_stats[0])
                if value > limit:
                    scaled_value = value * scale_factor
                    string_value = "%3.1f" % scaled_value
                    self.problem_processes[param][proc_stats[1]] = \
                        {'percent usage': string_value, 'user': proc_stats[2],
                         'command': proc_stats[5]}
        except Exception as e:
            self.function_errors['processes_check'] = str(e)

    # ----------------------------------------------------------------------
    def check_runaway_processes(self):
        """
        Look for processes using all of a CPU.
        """

        self.check_process_usage("pcpu", 90.0)
        try:
            command_result = localFunctions.run_command("free",
                                                    reraise_error=True,
                                                    result_as_list=False)

            values = re.findall(
                r'(\d+)', command_result, re.MULTILINE)
            system_memory = float(values[0])
        except subprocess.SubprocessError:
            # if find memory size failed just use standard 16GB
            system_memory = 16246424
        memory_limit = system_memory * 0.4
        self.check_process_usage("rssize", memory_limit,
                                 100.0 / system_memory)

    # ----------------------------------------------------------------------
    def check_proxy_server(self, startup_wait=0.0):
        """
        Confirm that the proxy is workingis by making a http query to the
        local webserver at the proxy port. This will also restart the proxy
        server if it has been shut down and its shutdown period has expired.
        """
        networkFunctions.internet_should_be_off(restart=True)
        time.sleep(startup_wait)
        self.proxy_server_ok = networkFunctions.proxy_server_working()


    # ----------------------------------------------------------------------
    def restart_proxy_server(self):
        """
        Restart the squid process and check again.
        """
        localFunctions.run_command("systemctl stop squid")
        localFunctions.run_command("systemctl start squid")
        self.check_proxy_server(3)

    # ----------------------------------------------------------------------
    def rebuild_proxy_server_cache(self):
        """
        Stop squid, rebuild the /Squid partition, remount and
        restart squid
        :return: True -- Squid running False - Squid still not running
        """
        self.reporter.report_starting_fix("starting proxy cache rebuild")
        rebuild_successful = rebuildSquidCache.rebuild_squid_cache()
        if rebuild_successful:
            # rebuild was successful and squid is running
            self.reporter.report_fix_result("cache rebuild successful",
                                            fixed=True)
        else:
            self.reporter.report_fix_result("cache rebuild failed",
                                            fixed=False)
            self.reporter.suggest_reboot("Squid proxy cannot be restarted.")
            self.reporter.report_requires_user_action_problem(
                error_message_name="", values=[],
                action_message_name="squid needs further work",
                increment_problem_count=False)
        return rebuild_successful

    # ----------------------------------------------------------------------
    def check_kahn_academy_server(self):
        """
        Confirm that the Kahn Academy server is working by making a http query to the 
        local webserver at the kahn academy port. 
        """
        try:
            # if no proxy server then kahn wont work  so we assume good
            request = urllib.request.urlopen('http://main-server.lcl:8008')
            self.kahn_academy_server_ok = True
        except urllib.error.URLError as e:
            # If the proxy server is not running this will fail. If the error
            # is Connection Refused then the proxy is bad so assume that the
            # proxy is bad but kahn server is running
            reason = str(e)
            if reason.find("111") != -1:
                self.kahn_academy_server_ok = True
                self.proxy_server_ok = False
            else:
                self.kahn_academy_server_ok = False

    # ----------------------------------------------------------------------
    def restart_kahn_academy_server(self):
        """
        Perform a restart of the ka-lite webserver and cron job
        """
        localFunctions.run_command("systemctl stop ka-lite")
        localFunctions.run_command("systemctl start ka-lite")
        self.check_kahn_academy_server()

    # ----------------------------------------------------------------------
    def check_ltsp_image(self):
        """
        Confirm that the required ltsp image file exists
        :return:
        """
        try:
            with open("/etc/ltsp/dhcpd.conf", "r") as f:
                filetext = f.read()
            if filetext.find("amd64") != -1:
                self.ltsp_arch = "amd64"
                self.ltsp_image_ok = \
                    os.path.exists("/opt/ltsp/images/amd64.img") and \
                    os.path.getsize("/opt/ltsp/images/amd64.img") > 1.25e9
            else:
                self.ltsp_arch = "i386"
                self.ltsp_image_ok = \
                    os.path.exists("/opt/ltsp/images/i386.img") and \
                    os.path.getsize("/opt/ltsp/images/i386.img") > 1.25e9
        except (OSError, IOError):
            pass
        return self.ltsp_image_ok

    # ----------------------------------------------------------------------
    def rebuild_ltsp_image(self):
        """
        Rebuild the missing ltsp image file
        :return:
        """
        command = "/usr/sbin/ltsp-update-image -n %s" % self.ltsp_arch
        try:
            self.reporter.report_fixable_problem("ltsp image missing")
            self.reporter.report_starting_fix("starting ltsp image build")
            command_result = localFunctions.run_command(command,
                                                        reraise_error=True,
                                                        result_as_list=False)
        except Exception as e:
            self.function_errors["rebuild_ltsp_image"] = str(e)
        if self.check_ltsp_image():
            self.reporter.report_fix_result("ltsp image ok",
                                            fixed=True)
        else:
            self.reporter.report_fix_result("ltsp image rebuild failed",
                                            fixed=False)
            if self.root_partition_too_full(5.0):
                self.reporter.report_requires_user_action_problem(
                    error_message="", values=[],
                    action_message_name="ltsp image rebuild manually too full",
                    increment_problem_count=False)
            else:
                self.reporter.report_requires_user_action_problem(
                    error_message="", values=[],
                    action_message_name="ltsp image rebuild manually",
                    increment_problem_count=False)
        self.suggest_reboot = True
        return self.ltsp_image_ok

    # ----------------------------------------------------------------------
    def perform_tests(self):
        """
        """
        # self.reporter.report_progress("test start", level=0)
        # self.reporter.report_progress("checking disks")
        # self.check_mounted_partitions()
        # self.reporter.show_percent_complete(2)
        # self.check_disks_health()
        # self.reporter.show_percent_complete(3)
        # self.map_filesystems_disks()
        # self.reporter.show_percent_complete(4)
        # self.check_last_backup_time()
        # self.reporter.show_percent_complete(5)
        # self.check_partitions_free_space()
        # self.check_ltsp_image()
        # self.reporter.report_progress("checking processes")
        # self.check_processes()
        # self.reporter.show_percent_complete(7)
        # self.check_proxy_server()
        # self.check_kahn_academy_server()
        # self.reporter.show_percent_complete(8)
        # self.check_recent_max_loads()
        # self.reporter.show_percent_complete(9)
        # self.reporter.report_progress("checking interfaces")
        self.initialize_interface_records()
        self.check_interfaces_state()
        # if self.config.get_value("check_networks"):
            # if self.config.get_value("look_for_local_hosts", True):
            #     self.reporter.show_percent_complete(11)
            #     self.reporter.report_progress("hosts ping")
            #     self.find_hosts_on_interfaces()
            # self.reporter.show_percent_complete(35)
        if (self.config.get_value("internet_available", True) and
                self.internet_interface in self.network_interfaces and
                self.network_interfaces[self.internet_interface].running):
            self.find_default_router()
            self.reporter.show_percent_complete(37)
            if self.default_router:
                self.reporter.report_progress("start internet check",
                    reformat_text=False, level=1)
                self.check_local_dns_server()
                self.reporter.show_percent_complete(41)
                self.reporter.report_progress("start internet ping check",
                                              reformat_text=False, level=2)
                self.check_internet_ping()
                self.reporter.show_percent_complete(45)
                self.reporter.report_progress("start internet name check",
                                              reformat_text=False, level=2)
                self.check_dns()
                if self.dns_good:
                    self.reporter.show_percent_complete(50)
                    self.reporter.report_progress("start internet browse check",
                                                  reformat_text=False, level=2)
                    self.check_internet_browsing()
                    self.reporter.show_percent_complete(60)
                    if self.internet_accessible:
                        self.reporter.report_progress(
                            "start internet quality check",
                            reformat_text=False, level=2)
                        if self.config.get_value("check_internet_quality",
                                                 True):
                            self.check_internet_quality()
                            self.reporter.show_percent_complete(80)
        self.reporter.report_progress("checks complete", level=0)
        # self.reporter.show_percent_complete(80)

    # ----------------------------------------------------------------------
    def handle_failed_processes(self):
        """
        One or more process are not running. Report problem then try to restart.
        """
        process_names = ""
        for process_name, info in self.failed_processes.items():
            process_names += "\n      %s (%s)" % (info[0], process_name)
        if len(self.failed_processes) > 1:
            txt = "failed processes"
        else:
            txt = "failed process"
        self.reporter.report_fixable_problem(txt, [process_names], False)
        for process_name in self.failed_processes.keys():
            self.restart_failed_process(process_name)
        # give a little time for it to start and then if problems to crash again
        time.sleep(1)
        self.check_daemons()
        if len(self.failed_processes):
            if len(self.failed_processes) > 1:
                txt1 = "failed restart processes"
                txt2 = "these processes"
            else:
                txt1 = "failed restart process"
                txt2 = "the process"
            process_names = ""
            for process_name, process_info in self.failed_processes.items():
                process_names += "\n        %s (%s)" % (
                    process_info[0], process_name)
            self.reporter.report_problem(txt1, [process_names],
                                         reformat_text=False,
                                         increment_problem_count=False)
            self.reporter.report_problem("process failed restart", [txt2],
                                         reformat_text=False,
                                         increment_problem_count=False)
        else:
            self.reporter.report_fix_result("process restart successful",
                                            fixed=True)

    # ----------------------------------------------------------------------
    def restart_failed_process(self, process_name):
        """
        Use the command that is the third element of the process info tuple to restart the
        process.
        """
        process_info = ["", ""]
        if process_name in self.daemons_list:
            process_info = self.daemons_list[process_name]
        elif process_name in self.other_system_processes_list:
            process_info = self.other_system_processes_list[process_name]
        self.reporter.report_starting_fix("try start process",
                                          [process_name, process_info[0],
                                           process_info[1]])
        try:
            localFunctions.run_command(process_info[1], reraise_error=True,
                                       result_as_list=False)
            successful = True
        except subprocess.CalledProcessError as e:
            error_text = e.output
            self.reporter.report_problem("process restart failed",
                                         [error_text])
            successful = False
            self.suggest_reboot = True
        return successful

    # ----------------------------------------------------------------------
    def handle_unmounted_filesystem(self, filesystem):
        """
        Try to fix a single unmounted filesystem. First do a
        forced fsck to confirm that it is ok, then try to mount
        it.
        """
        problem_association = {"/Squid": "Internet proxy refused",
                               "/client_home": "teachers accounts, Kahn Academy, and Rachel",
                               "/client_home_students": "students saving files in their personal areas"}
        try:
            if filesystem["mount point"] == "/Squid":
                # Don't try fsck -- just rebuild. This will also restart squid
                self.rebuild_proxy_server_cache()
            else:
                self.reporter.report_fixable_problem("file system not mounted",
                                                     [filesystem["partition"],
                                                      filesystem["mount point"],
                                                      problem_association[filesystem[
                                                          "mount point"]]])
                ok_to_mount = self.fsck_partition(filesystem["partition"],
                                                  filesystem["mount point"])
                if ok_to_mount:
                    try:
                        self.reporter.report_starting_fix("trying mount",
                                                          [filesystem["partition"],
                                                           filesystem[
                                                               "mount point"]])
                        command = "/bin/mount " + filesystem["mount point"]
                        mount_result = localFunctions.run_command(command, True)
                        self.reporter.report_fix_result("mount successful",
                                                        [problem_association[
                                                             filesystem[
                                                                 "mount point"]]],
                                                        fixed=True)
                    except subprocess.CalledProcessError as e:
                        self.reporter.report_fix_result("mount failed",
                                                        [e.output], fixed=False)
                        self.suggest_reboot = True
        except KeyError:
            pass

    # ----------------------------------------------------------------------
    def handle_missing_disk(self):
        if not self.check_single_disk_system() and len(self.disks) < 2:
            disk_name = "backup" if self.get_using_backup_disk() else "primary"
            self.reporter.report_requires_user_action_problem("disk missing",
                                                      values=[disk_name],
                                                      action_message_name="disk missing action",
                                                      action_values=[disk_name])

    # ----------------------------------------------------------------------
    def handle_failed_disks(self):
        """
        One of the disks is reporting problems. Check the mount point on the
        disk and make an appropriate warning.
        """
        global GrubFilename, MirrorFilename
        global EmergencyGrubFile, SingleDiskMirrorFile, StandardGrubFile
        for disk in self.disks.values():
            if not disk.exists:
                self.reporter.report_requires_user_action_problem("disk missing",
                                                                  values=[disk.name, disk.device],
                                                                  action_message_name="disk missing action",
                                                                  action_values=[disk.name,
                                                                                 disk.device])
            elif disk.bad:
                if disk.active_os:
                    self.reporter.report_serious_problem("active disk failing",
                                                         [disk.name, disk.device])
                    self.reporter.report_requires_user_action_problem("", values=[],
                                                          action_message_name="active disk failing action",
                                                          action_values=[disk.device],
                                                          increment_problem_count=False)
                    if disk.primary:
                        self.reporter.report_requires_user_action_problem("", values=[],
                                                                          action_message_name="primary disk failure action",
                                                                          action_values=[],
                                                                          increment_problem_count=False)
                        if os.path.islink(GrubFilename):
                            try:
                                os.unlink(GrubFilename)
                            except OSError:
                                pass
                        if not os.path.exists(GrubFilename):
                            try:
                                os.symlink(EmergencyGrubFile, GrubFilename)
                            except OSError:
                                pass
                        if not os.path.exists(GrubFilename):
                            try:
                                os.symlink(StandardGrubFile, GrubFilename)
                            except OSError:
                                pass
                else:
                    self.reporter.report_serious_problem("backup disk failure", [disk.device])
                    self.reporter.report_requires_user_action_problem("", values=[],
                                                                      action_message_name="backup disk failure action",
                                                                      action_values=[disk.device],
                                                                      increment_problem_count=False)
                    if not disk.primary:
                        try:
                            os.unlink(MirrorFilename)
                        except OSError:
                            pass
                        try:
                            os.symlink(SingleDiskMirrorFile, MirrorFilename)
                        except OSError:
                            pass

    # ----------------------------------------------------------------------
    def handle_backup_too_old(self):
        """
        The last mirror occured too long ago. Warn the administrator and
        suggest manual run. Hold down test and report for first 20 minutes
        to allow time for backup to run.
        """
        try:
            uptime_res = localFunctions.run_command("uptime", result_as_list=False)
            match = re.search(r'up\s+(\d+)\smin', uptime_res)
            uptime = match.group(1)
            if int(uptime) < 20:
                return
        except (ValueError, AttributeError):
            pass
        if self.empty_backup_log_file:
            self.reporter.report_problem("no backup log")
        else:
            for fs_name in ("/", "/client_home/", "/client_home_students/"):
                if fs_name not in self.fs_backup_days_ago:
                    self.fs_backup_days_ago[fs_name] = "an unknown number of days ago"
            self.reporter.report_problem("backup old",
                                         [self.fs_backup_days_ago["/"],
                                          self.fs_backup_days_ago[
                                              "/client_home/"],
                                          self.fs_backup_days_ago[
                                              "/client_home_students/"],
                                          self.full_backup_days_ago])
        self.reporter.report_requires_user_action_problem(error_message_name="", values=[],
                                                          action_message_name="run backup action",
                                                          action_values=[],
                                                          increment_problem_count=False)

    # ----------------------------------------------------------------------
    def handle_backup_failed(self):
        """
        The last backup occured too long ago. Warn the administrator and
        suggest manual run. Hold down test and report for first 20 minutes
        to allow time for backup to run.
        """
        fs_report_text = ""
        for fs in self.fs_backup_failures:
            fs_report_text += "The last backup of %s failed.\n" %fs
        if self.full_backup_failed:
            status_text = ">>failed<<"
        else:
            status_text ="successful"
        full_backup_report_text = \
            "The full backup was reported %s %s." %(status_text, self.full_backup_days_ago)
        self.reporter.report_problem("backup failed", [fs_report_text, full_backup_report_text])
        self.reporter.report_requires_user_action_problem(error_message_name="", values=[],
                                                          action_message_name="review mirror file",
                                                          increment_problem_count=False)

    # ----------------------------------------------------------------------
    def root_partition_too_full(self, free_space_required):
        """
        A simole function to check size and return True if the root partition
        has less than free_space_required percent unused.
        :param free_space_required:
        :return:
        """
        self.check_partitions_free_space()
        return self.partition_free_space['/']["percent"] < free_space_required

    # ----------------------------------------------------------------------
    def handle_partitions_full(self):
        """
        Use the list of partitions which exceed the limits to warn the
        admininstrator and suggest action.
        """
        if self.partition_full:
            if self.root_partition_too_full(10.0):
                self.cleanup_root_partition()
                if self.root_partition_too_full(8.0):
                    self.emergency_cleanup_root_partition()
                if self.root_partition_too_full(10.0):
                    self.reporter.report_problem("os partition full",
                                                 [(100.0 -
                                                   self.partition_free_space[
                                                       '/']["percent"])])
            if ('/client_home' in self.partition_free_space and
                    (self.partition_free_space['/client_home'][
                         "percent"] < 5.0)):
                accounts = cleanUsersTrash.get_group_users_names("teacher")
                max_trash_size = 300
                trash_data, report_text, html_report_text = cleanUsersTrash.empty_users_trash(
                    accounts,
                    table_indent=10,
                    log=True, max_size=max_trash_size * 1000)
                if report_text:
                    self.reporter.report_requires_user_action_problem("",
                                                                      values=[],
                                                                      action_message_name="teachers large trash",
                                                                      action_values=[
                                                                          max_trash_size,
                                                                          report_text],
                                                                      increment_problem_count=False,
                                                                      reformat_text=False,
                                                                      html_text=html_report_text)
                cleanUsersTrash.empty_users_trash(accounts, log=False)
                if self.partition_free_space['/client_home']["amount"] < 20.0:
                    report_text, html_report_text = get_accounts_usage(count=4,
                                                                       sort_by_media_size=False,
                                                                       table_indent=10,
                                                                       students=False,
                                                                       show_trash=False)
                    if self.config.get_value("use_gui"):
                        report_text = html_report_text
                    self.reporter.report_requires_user_action_problem(
                        "client_home partition full",
                        values=[self.partition_free_space['/client_home'][
                                    "amount"]],
                        action_message_name="client_home find files to remove",
                        action_values=[report_text])
            if ('/client_home_students' in self.partition_free_space and
                    (self.partition_free_space['/client_home_students'][
                         "amount"] < 10.0)):
                systemCleanup.clean_client_home_students(exclusions=[], prune_active_owner=True,
                                                         other_protected_users=[])
                if self.partition_free_space['/client_home']["amount"] < 10.0:
                    report_text, html_report_text = get_accounts_usage(count=4,
                                                                       sort_by_media_size=True,
                                                                       table_indent=10,
                                                                       students=True)
                    if self.config.get_value("use_gui"):
                        report_text = html_report_text
                    self.reporter.report_requires_user_action_problem(
                        "client_home_students partition full",
                        values=[
                            self.partition_free_space['/client_home_students'][
                                "amount"]],
                        action_message_name="client_home_students find files to remove",
                        action_values=[report_text])

    # ----------------------------------------------------------------------
    def cleanup_root_partition(self):
        """
        Delete non-critical files if the root partition becomes too full.
        This should never happen in normal operation but removing some files may prevent
        complete failure.
        This is a lighterweight action that is done to perhaps prevent a warning.
        :return:
        """
        systemCleanup.clean_os_copies("/")
        systemCleanup.clean_opt(remove_alt_image=False, ltsp_arch=self.ltsp_arch)
        systemCleanup.clean_client_home_local(exclusions=[],
                                              prune_active_owner=True,
                                              other_protected_users=[],
                                              rebuild_student_home=False)
        self.clean_tmp(False)
        systemCleanup.clean_dir("/mnt", exclusions=[], prune_active_owner=False,
                                other_protected_users=[])
        systemCleanup.clean_dir("/var/crash", exclusions=[], prune_active_owner=False,
                                other_protected_users=[])
        systemCleanup.clean_dir("/media", exclusions=[], prune_active_owner=True,
                                other_protected_users=[])

    # ----------------------------------------------------------------------
    def emergency_cleanup_root_partition(self):
        """
        Delete non-critical files if the root partition becomes too full and may fail.
        This should never happen in normal operation but removing some files may prevent
        complete failure.
        This is a thorough action which performs the more sensitive removals only
        if the prior ones are insufficient.
        :return:
        """
        target_size = 8
        self.reporter.report_fixable_problem("os partition needs emptying")
        systemCleanup.clean_client_home_local(exclusions=[], prune_active_owner=True,
                                              other_protected_users=[], rebuild_student_home=True)
        self.clean_squid_mountpoint()
        self.clean_tmp(False)
        if self.root_partition_too_full(target_size):
            self.clean_sysadmin_and_master()
        if self.root_partition_too_full(target_size):
            systemCleanup.clean_opt(remove_alt_image=True,
                                    ltsp_arch=self.ltsp_arch)
        if self.root_partition_too_full(target_size):
            self.clean_tmp(True)
        if self.root_partition_too_full(target_size):
            self.clean_var()
        if self.root_partition_too_full(target_size):
            systemCleanup.clean_dir("/media", exclusions=[],
                                    prune_active_owner=False,
                                    other_protected_users=[])
        self.check_sysadmin_home_size()
        if self.root_partition_too_full(target_size):
            self.reporter.report_fix_result("root partition still too full",
                                            [100.0 -
                                             self.partition_free_space['/'][
                                                 "percent"]],
                                            fixed=False)
            self.suggest_reboot = True
        else:
            self.reporter.report_fix_result(
                "cleared enough root partition space",
                [100.0 - self.partition_free_space['/']["percent"]],
                fixed=True)

    # ----------------------------------------------------------------------
    @staticmethod
    def emergency_cleanup_client_home_partition():
        """
        remove teachers trash and mozilla cache
        :return:
        """
        accounts = cleanUsersTrash.get_group_users_names("teacher")
        cleanUsersTrash.empty_users_trash(accounts, 0)
        for account in accounts:
            mozilla_cache_dir = "~%s/.cache/mozilla/firefox" % account
            thumbnail_cache_dir = "~%s/.cache/thumbnails/" % account
            localFunctions.command_run_successful(
                "/bin/rm -r %s/*" % mozilla_cache_dir)
            localFunctions.command_run_successful(
                "/bin/rm -r %s/*/*" % thumbnail_cache_dir)
            localFunctions.command_run_successful(
                'find %s -type f -name "*.exe" -exec /bin/rm {} \;' % account)
            localFunctions.command_run_successful(
                'find %s -type f -name "*.iso" -size +100M -exec /bin/rm {} \;' % account)

    # ----------------------------------------------------------------------
    def owned_by_active_user(self, file_name):
        """
        Test id the file owner is one of the active users
        :param file_name:
        :return: True if owned by active user
        """
        return pwd.getpwuid(os.stat(file_name).st_uid).pw_name in \
                            self.active_users["all users"]

    # ----------------------------------------------------------------------
    def clean_sysadmin_and_master(self):
        """
        remove files from /home/sysadmin and /home/master
        :return:
        """
        sysadmin_size_before = localFunctions.get_directory_size("/home/sysadmin")
        for directory in ["/home/master/Downloads", "/home/sysadmin/Downloads"]:
            if self.get_directory_size(directory) > 50:
                # If there is only a small amount leave it. It won't help much but
                # and there may be useful stuff in it
                command = "/bin/rm -r %s/*" % directory
                localFunctions.command_run_successful(command)
        for user_name in "sysadmin","master":
            command = "su %s -c 'trash-empty'" % user_name
            localFunctions.command_run_successful(command)
        for directory in ["/home/master/", "/home/sysadmin/"]:
            # remove huge files
            command = "find %s -type f -size +100M -exec rm {} \;" % directory
            localFunctions.command_run_successful(command)
            media_files_by_class, all_media_files, total_media_size = \
                systemCleanup.get_media_files(directory)
            target_files = systemCleanup.get_media_files_by_class_and_size(media_files_by_class,
                                               "video", 10.0e6)
            target_files.extend(systemCleanup.get_media_files_by_class_and_size(
                media_files_by_class, "audio", 3.0e6))
            if directory == "/home/sysadmin/":
                target_files.extend(systemCleanup.get_media_files_by_class_and_size(
                    media_files_by_class, "other", 0))
            for file in target_files:
                try:
                    os.unlink(file)
                except OSError:
                    pass
        change = sysadmin_size_before - localFunctions.get_directory_size("/home/sysadmin")
        self.reporter.report_fix_result("sysadmin home cleaned",
            [localFunctions.convert_to_readable(change, storage_size=True)], fixed=False)
        return change

    # ----------------------------------------------------------------------
    def clean_var(self):
        """
        Remove files from /var/tmp and /var/log
        :return:
        """
        for dirname in os.listdir("/var/tmp"):
            try:
                if not (dirname.startswith("systemd") or
                        (time.time() - os.path.getmtime(dirname)) < 180000 or
                        self.owned_by_active_user(dirname)):
                    command = "/bin/rm -r %s" % os.path.join("/var/tmp",
                                                             dirname)
                    localFunctions.command_run_successful(command)
            except OSError:
                pass
        try:
            for info in os.walk("/var/log"):
                for filename in info[2]:
                    for ext in (".gz", ".1", ".2"):
                        if filename.endswith(ext) and not filename.startswith(
                                "loadmonitor.csv"):
                            os.remove(os.path.join(info[0], filename))
        except OSError:
            pass

    # ----------------------------------------------------------------------

    def clean_tmp(self, clean_thorougly=False):
        """
        Remove larger files and directories that do not belong to active users. Do not
        touch smaller files or directories because they may have some current use as flags
        :return:
        """
        try:
            du_list = localFunctions.run_command("du -sk /tmp/*",
                                                 result_as_list=True,
                                                 reraise_error=True,
                                                 merge_stderr=False)
            for entry in du_list:
                try:
                    entry_info = re.split(r'\s+', str(entry).strip(), 1)
                    size_in_kb = int(entry_info[0])
                    name = entry_info[1]
                    if not clean_thorougly:
                        # a more relaxed action to clean out stale big files
                        if (
                                size_in_kb > 10000 and not self.owned_by_active_user(name)
                                or name.startswith("rsync-")):
                            command = "/bin/rm -r %s" % name
                            localFunctions.command_run_successful(command)
                    else:
                        if name.startswith("/tmp/nbd-swap/"):
                            if size_in_kb > 50000:
                                command = "/bin/rm -r /tmp/nbd-swap/*"
                                localFunctions.command_run_successful(command)
                        elif ((size_in_kb > 8 and not self.owned_by_active_user(
                                name)) or
                              # if huge, delete even if owned by an active user -- maybe a runaway
                              size_in_kb > 100000):
                            # a more complete cleaning that might mess up things.
                            command = "/bin/rm -r %s" % name
                            localFunctions.command_run_successful(command)
                            self.suggest_reboot = True
                except (OSError, ValueError, IndexError):
                    pass
        except subprocess.CalledProcessError:
            pass

    def clean_squid_mountpoint(self):
        """
        If squid is running, stop it, unmount fs, remove anything in the /Squid mount point
        directory, then remount and restart.
        :return:
        """
        localFunctions.command_run_successful("systemctl stop squid")
        time.sleep(2)
        localFunctions.command_run_successful("umount /Squid")
        if not os.path.ismount("/Squid"):
            localFunctions.command_run_successful("rm -r /Squid/*")
        localFunctions.command_run_successful("mount /Squid")
        if os.path.ismount("/Squid"):
            localFunctions.command_run_successful("systemctl start squid")
        if not localFunctions.command_run_successful("systemctl is-active squid"):
            self.rebuild_proxy_server_cache()

    # ----------------------------------------------------------------------
    @staticmethod
    def get_directory_size(directory_name):
        """
        Determine the disk usage of a directories contents.
        :param directory_name:
        :return: diskspace used in Mbytes integer
        """
        size = 0
        try:
            command = "du -sm --one-file-system %s" % directory_name
            command_result = localFunctions.run_command(command,
                                                        reraise_error=True,
                                                        result_as_list=False,
                                                        merge_stderr=False,
                                                        print_error=False)
            size = int(command_result.split()[0])
        except (subprocess.CalledProcessError, ValueError):
            pass
        return size

    # ----------------------------------------------------------------------
    def check_sysadmin_home_size(self):
        """
        Check the size of the sysadmin home
        :return:
        """
        home_size = self.get_directory_size("/home/sysadmin")
        if home_size > 600:
            self.reporter.report_requires_user_action_problem(
                error_message_name="sysadmin home excessive problem",
                values=[home_size],
                action_message_name="sysadmin home excessive action",
                action_values=[home_size])
        elif home_size > 330:
            self.reporter.report_requires_user_action_problem(
                error_message_name="", values=[],
                action_message_name="sysadmin home too large",
                action_values=[home_size])

    # ----------------------------------------------------------------------
    def handle_proxy_server_restart(self):
        """
        Check if internet access is turned off so that squid should not be started
        Announce problem with squid, attempt restart and check result
        """
        if not networkFunctions.internet_should_be_off():
            self.reporter.report_fixable_problem("proxy test failed")
            self.restart_proxy_server()
            if self.proxy_server_ok:
                self.reporter.report_fix_result("proxy restart successful")
            else:
                self.rebuild_proxy_server_cache()

    # ----------------------------------------------------------------------

    def handle_kahn_academy_server_restart(self):
        """
        Announce problem with kahn academy server, attempt restart and report
        """
        self.reporter.report_fixable_problem("kahn test failed")
        self.restart_kahn_academy_server()
        if self.kahn_academy_server_ok:
            self.reporter.report_fix_result("kahn restart successful")
        else:
            self.reporter.report_requires_user_action_problem(
                error_message_name="kahn needs further work problem",
                action_message_name="kahn needs further work action",
                increment_problem_count=False)

    # ----------------------------------------------------------------------
    def analyze_load_minutes(self):
        """
        Check the number of minutes logged as above 80% and above 90% CPU usage.
        Report if the number seems high.
        """
        if self.load_monitor_minutes:
            above70 = self.load_above_70_minutes / self.load_monitor_minutes
            above80 = self.load_above_80_minutes / self.load_monitor_minutes
            if above70 > 0.1:
                self.reporter.report_requires_user_action_problem("load high", values=[70,
                                                                                       self.load_above_70_minutes,
                                                                                       self.load_monitor_minutes / 60.0,
                                                                                       above70 * 100.0],
                                                                  action_message_name="load high action")
            if above80 > 0.05:
                self.reporter.report_requires_user_action_problem("load high", values=[80,
                                                                                       self.load_above_80_minutes,
                                                                                       self.load_monitor_minutes / 60.0,
                                                                                       above80 * 100.0],
                                                                  action_message_name="load high action")

    # ----------------------------------------------------------------------
    def analyze_local_host_count(self):
        if self.config.get_value("look_for_local_hosts"):
            local_host_count = 0
            for name, interface in self.network_interfaces.items():
                local_host_count += interface.count_number_of_local_hosts()
            self.reporter.report_values("local host count",
                                        [str(local_host_count)], 0)

    # ----------------------------------------------------------------------
    def analyze_network_interfaces(self):
        """
        Use the information about each interface to warn of problems
        """
        for name, interface in self.network_interfaces.items():
            try:
                interface.analyze_interface(list(self.network_interfaces.values()))
            except Exception as e:
                self.function_errors["analyze_network_interfaces"] = \
                    "interface %s %s" %(name, str(e))

    # ----------------------------------------------------------------------
    def analyze_internet_access(self):
        """
        Use data collected by several tests to determine why the internet is not
        working. Failure of the isp connection is not only the most common but also
        the hardest to conclusively identify. It can really only be identified when everything
        else works ok.
        """
        step = ""
        try:
            internet_off_text = networkFunctions.internet_should_be_off()
            if internet_off_text and not networkFunctions.proxy_server_working():
                self.reporter.report_requires_user_action_problem(
                    error_message_name="internet off",
                    values=[internet_off_text],
                    action_message_name="internet off action")
            if self.proxy_ok:
                # all internet works -- don't bother with further analysis
                return
            if self.internet_accessible:
                if not networkFunctions.internet_should_be_off():
                    step = "restart squid"
                    if not (self.restart_proxy_server()):
                        #    self.reporter.suggest_reboot()
                        step = "analyze_internet_access_retries"
                        return self.analyze_internet_access_retries
                    step = "check_internet_browsing"
                    self.check_internet_browsing()
                    if self.proxy_ok:
                        self.reporter.report_fix_result("fix worked", fixed=True)
                    return
                else:
                    return
            step = "report tests"
            if self.internet_interface in self.network_interfaces and \
                    not self.network_interfaces[self.internet_interface].running:
                # If the interfaces is not running then that is the problem. Give only
                #  a short message
                self.reporter.report_problem("internet interface down")
                return
            if not self.router_ping_successful:
                self.reporter.report_requires_user_action_problem(
                    "router ping failed", values=[],
                    action_message_name="router ping failed action")
                return
            # If no hosts are found on the internet interfaces the problem has already been found.
            # This has already been reported with the interface analysis so don't mention here.
            # Now lets check DNS.
            if (self.internet_ping_successful and not self.dns_good) or \
                    not self.internal_dns_good:
                self.reporter.report_fixable_problem("nameserver bad")
                step = "bind 9 restart"
                if self.restart_failed_process("bind9"):
                    self.check_dns()
                    if self.dns_good:
                        step = "internet browsing after bind9 restart"
                        self.check_internet_browsing()
                        if self.proxy_ok:
                            self.reporter.report_fix_result("fix worked",
                                                            fixed=True)
                        return
            if self.internal_dns_good and not self.internet_ping_successful:
                # if the internal test is good but the network fails then the ISP connection
                # or the router is bad  This is the most common problem
                self.reporter.report_problem("internet down")
                return
            if self.internal_dns_good and self.dns_good:
                # Maybe a problem with shorewall
                self.reporter.report_fixable_problem("firewall restart")
                step = "restart shorewall"
                if self.restart_failed_process("shorewall"):
                    step = "internet browsing after shorewall restart"
                    self.check_internet_browsing()
                    if self.proxy_ok:
                        self.reporter.report_fix_result("fix worked", fixed=True)
                    return
                self.suggest_reboot = True
        except Exception as e:
            self.function_errors["analyze_internet_access"] = "Step '%s' %s" %(step, str(e))

    # ----------------------------------------------------------------------
    def analyze_mounted_partitions(self):
        try:
            mounted_filesystems = localFunctions.get_mounted_filesystems()
            for partition in self.required_partitions:
                if partition["mount point"] not in mounted_filesystems:
                    self.handle_unmounted_filesystem(partition)
        except Exception as e:
            self.function_errors["analyze_mounted_partitions"] = str(e)

    # ----------------------------------------------------------------------
    def analyze_problem_processes(self):
        """
        Report processes that are using too much memory or CPU. Perform the check just before the
        analysis in cse a problem has been fixed already.
        """
        self.check_runaway_processes()
        try:
            for resource in [("pcpu", "CPU"), ("rssize", "memory")]:
                root_process = False
                if self.problem_processes[resource[0]]:
                    intro = "Some processes are using too much %s:\n" % resource[1]
                    html_text = '%s</br><table>' % intro
                    html_text += '<tr><th>ID</th><th>Name</th><th>User</th><th>%Use</th></tr>\n'
                    for key, val in list(
                            self.problem_processes[resource[0]].items()):
                        html_text += "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s%%</td></tr>\n" \
                                     % (key, val["command"].strip(),
                                        val["user"].strip(), val["percent usage"])
                    html_text += "</table>"
                    processes_table = "        ID            Name            User       %Use\n"
                    for key, val in list(
                            self.problem_processes[resource[0]].items()):
                        processes_table += "      %5s  %20s  %8s   %s%%\n" \
                                           % (key, val["command"].strip(),
                                              val["user"].strip(),
                                              val["percent usage"])
                    header = ["    Process ID", "Program Name", "Process Owner",
                              "% Use"]
                    data = []
                    for key, val in list(
                            self.problem_processes[resource[0]].items()):
                        if val["user"].strip() == "root":
                            root_process = True
                        data.append(["    " + key, val["command"].strip(),
                                     val["user"].strip(),
                                     val["percent usage"] + "%"])
                    if self.config.get_value("use_gui"):
                        processes_table = tabulate.tabulate(data, header, "html")
                    else:
                        processes_table = tabulate.tabulate(data, header, "plain")
                    if resource[1] == "CPU":
                        if root_process:
                            self.reporter.report_serious_problem("root process cpu use")
                            self.reporter.report_requires_user_action_problem(
                                error_message_name="", values=[],
                                action_message_name="root process cpu use action",
                                action_values=[processes_table], increment_problem_count=False,
                                suggest_reboot=True)
                            self.suggest_reboot = True
                        else:
                            self.reporter.report_requires_user_action_problem(
                                error_message_name="report problem process",
                                values=[intro],
                                action_message_name="problem cpu process action",
                                action_values=[processes_table])
                    elif resource[1] == "memory":
                        self.reporter.report_requires_user_action_problem(
                            error_message_name="report problem process",
                            values=[intro],
                            action_message_name="problem memory process action",
                            action_values=[processes_table])
        except Exception as e:
            self.function_errors["analyze_problem_processes"] = str(e)

    # ----------------------------------------------------------------------
    def check_processes(self):
        """
        Confirm that all required daemon process are running and restart
        them if necessary. This is best done before runnoing any other tests
        because this may fix problems that would be discovered in these
        tests.
        """
        self.check_daemons()
        if self.failed_processes:
            self.handle_failed_processes()
            self.requires_daemon_recheck = True

    # ----------------------------------------------------------------------
    def analyze_results(self):
        """
        Use the test results to attempt to diagnose or fix problems.
        """
        # self.reporter.report_progress("starting analysis", level=0)
        #     self.analyze_local_host_count()
        # if self.disk_health_bad:
        #     self.handle_failed_disks()
        # if self.full_backup_failed or len(self.fs_backup_failures):
        #     self.handle_backup_failed()
        # elif self.last_backup_too_old:
        #     self.handle_backup_too_old()
        # if self.partition_full:
        #     self.handle_partitions_full()
        # if not self.ltsp_image_ok:
        #     self.rebuild_ltsp_image()
        # self.reporter.show_percent_complete(90)
        # if not self.proxy_server_ok:
        #     self.handle_proxy_server_restart()
        # if not self.kahn_academy_server_ok:
        #     self.handle_kahn_academy_server_restart()
        # self.analyze_load_minutes()
        # self.analyze_network_interfaces()
        # self.analyze_mounted_partitions()
        # self.analyze_problem_processes()
        # if self.config.get_value("check_networks") and \
        #         self.config.get_value("internet_available", True):
        self.analyze_internet_access()
        if not self.internet_quality == "Unknown":
            self.reporter.report_values("internet quality",
                                        [self.internet_quality], indent=0)
        internet_off_text = networkFunctions.internet_should_be_off()
        if internet_off_text and not networkFunctions.proxy_server_working():
            self.reporter.report_requires_user_action_problem(error_message_name="internet off",
                                                values=[internet_off_text],
                                                action_message_name="internet off action")
        # self.reporter.report_progress("finished analysis", level=0)
        # self.reporter.show_percent_complete(100)
        report_errors(self.function_errors)

# ----------------------------------------------------------------------
def get_accounts_usage(count=4, sort_by_media_size=False, table_indent=0,
                       show_trash=False, students=False):
    """
    Use the core of the checkUserHomesizeProgram to create a printed list
    of largest user home directories
    :param count:
    :param sort_by_media_size:
    :param table_indent:
    :param show_trash:
    :param students:
    :return: report tables
    """
    options = checkUserHomeSize.create_options_dict()
    options["num_accounts_shown"] = count
    options["sort_by_media_size"] = sort_by_media_size
    options["table_indent"] = table_indent
    options["show_trash"] = show_trash
    options["show_students"] = students
    report_table, html_report_table, data_results = checkUserHomeSize.perform_check(
        options)
    return report_table, html_report_table

# ----------------------------------------------------------------------
def prior_time_name(prior_time):
    """
    Convert the interval betwwen the prior epoch time and now
    to easily understandable forms.
    """
    if prior_time == 0:
        interval_name = "an unknown number of days ago"
        days = 100
    else:
        prior_day = time.gmtime(prior_time).tm_yday
        today = time.gmtime(time.time()).tm_yday
        days = today - prior_day
        if days == 0:
            interval_name = "today"
        elif days == 1:
            interval_name = "yesterday"
        else:
            interval_name = "%d days ago" % days
    return interval_name, days

# ----------------------------------------------------------------------
def setup_error_logger():
    """
    Create an error logger that can report messages in the file error.log in the
    /var/log/systemCheck directory. The logger is to be used only to report program
    errors, not detected system problems.
    :return:
    """
    global LogDirectory
    if not os.path.exists(LogDirectory):
        os.makedirs(LogDirectory)
    unused, error_lgr = backgroundFunctions.create_loggers(info_log_filename="",
                                         error_log_filename=LogDirectory + "/error.log")
    return error_lgr

# ----------------------------------------------------------------------
def report_errors(error_dict):
    """
    Report all exceptions caught in self.function_errors in the error log file
    :return:
    """
    global error_logger
    error_report_string = ""
    for error_name in error_dict:
        if error_dict[error_name]:
            func_err_string = "\t%s: %s\n" %(error_name, error_dict[error_name])
            error_report_string += func_err_string
    if error_report_string:
        error_logger.error(error_report_string)

# ----------------------------------------------------------------------
def record_screen_dimensions(gui_app):
    """
    get the dimsions of the screen and store in the systemCheck.conf file for use by
    other programs
    :param gui_app:
    :return:
    """
    screen_resolution = gui_app.desktop().screenGeometry()
    config_val = "%dx%d" % (screen_resolution.width(), screen_resolution.height())
    localFunctionsPy3.set_conf_file_value('/etc/systemCheck.conf', "System", "screen_dimensions",
                                       config_val)

# ----------------------------------------------------------------------
def initializeApp():
    print(os.path.abspath(sys.executable))
    if os.path.abspath(sys.executable) == "/usr/local/bin":
        sys.path.append("/usr/local/lib/python")

# ----------------------------------------------------------------------
def runCheck(config, gui_connector=None):
    config.update_from_gui(gui_connector)
    reporter = sysChkIO.Reporter(config=config,
                                 gui_connector=gui_connector,
                                 username=config.get_value("user"),
                                 report_progress_messages=
                                 not (config.get_value("quiet") or
                                      config.get_value("problems_only")),
                                 output_filename=config.get_value(
                                     "output_filename"))
    system_checker = SystemChecker(reporter=reporter, config=config)
    system_checker.perform_tests()
    system_checker.analyze_results()
    #reporter.report_summary(ProblemReported, system_checker.suggest_reboot)
    reporter.cleanup()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    localFunctions.confirm_root_user("systemCheck")
    error_logger = setup_error_logger()
    try:
        config_store = Configuration()
        if config_store.get_value("use_gui"):
            app = PyQt4.QtGui.QApplication([])
            record_screen_dimensions(app)
            MainWindow = PyQt4.QtGui.QMainWindow()
            gui = systemCheckGui.Ui_MainWindow()
            gui.setupUi(MainWindow)
            Gui_Connector = systemCheckGui.GuiConnector(config_store, gui, app)
            MainWindow.show()
            sys.exit(app.exec_())
        else:
            runCheck(config_store)
    except Exception as err_val:
        # serious error that caused program failure
        error_logger.error(
            "systemCheck failed with unknown error:\n " +
            localFunctions.generate_exception_string(err_val))
        print("SystemCheck failed.")
