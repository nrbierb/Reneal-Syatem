#!/usr/bin/env python3

import csv
import os
import re
import subprocess
import sys
import time
import atexit
import localFunctions
import backgroundFunctions
import networkFunctions

PROGRAM_VERSION = "1.1.1"
PROGRAM_NAME = "systemPerformanceMonitor"
ERROR_LOGFILE = "/var/log/loadmonitor/error.log"
INFO_LOGFILE = "/var/log/loadmonitor/info.log"
InfoLogger = None
ErrorLogger = None
DEBUG=False

class SysMonitor:
    """
    The SysMonitor class logs key system activity parameters
    at regular intervals. Most of the monitored data comes from
    the /proc file system.
    These parameters are:
    1.CPU load system, user, and idle from /proc/stat
    2.Network interface raw packets in and out by interface
        from /proc/net/dev
    3.Swap activity from vm_stats
    4.Memory usage and swap.
    All data is stored within python lists. No checkpoints are
    written to disk. This allows the monitor to be run on diskless
    systems.
    """

    def __init__(self, interface_names):
        self.swap_partition = ""
        self.interface_names = interface_names
        self.create_re()
        self.initialized = False
        self.prior_cpu_counts = [0, 0, 0, 0]
        self.network_interfaces = {}
        self.prior_network_interfaces = {}
        self.prior_swap_counts = [0, 0]
        self.network_interfaces = {}
        self.swap_partition = []
        self.cpu_use = []
        self.mem_use = []
        self.swap_activity = []
        self.num_users = [0]
        self.time = []
        self.epoch_time = 0
        self.loadavg = [0.0]

    def create_re(self):
        """
        create compiled regular expressions for all proc file data extraction
        """
        self.cpu_re = re.compile(r'^cpu\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)')
        # self.memstat_re = re.compile(r'^(\w+)\D*(\d+).*', re.M)
        self.net_re = re.compile(r'^\s*(\w+):\s+(\d.+)$')
        self.load_re = re.compile(r'^(\S*)')

    def open_proc_files(self):
        self.stat_file = open("/proc/stat", "r")
        self.net_file = open("/proc/net/dev", "r")
        # self.mem_file = open("/proc/meminfo", "r")
        self.loadavg_file = open("/proc/loadavg", "r")
        self.vmstat_file = open("/proc/vmstat")

    def read_proc_files(self):
        self.stat_data = self.stat_file.read()
        self.net_data = self.net_file.read()
        # self.mem_use = self.mem_file.read()
        self.loadavg_data = self.loadavg_file.read()
        self.vm_data = self.vmstat_file.read()

    def close_proc_files(self):
        self.stat_file.close()
        self.net_file.close()
        # self.mem_file.close()
        self.loadavg_file.close()
        self.vmstat_file.close()

    @staticmethod
    def correct_for_rollover(prior_value, current_value):
        """
        This is a static function to correct the counter
        value for 32 bit (int) rollover. The counter values should be
        monotonically increasing, so if the current_value is less then
        rollover has occured. The delta is then the current  + max - prior
        """
        corrected = int(current_value)
        if current_value < prior_value:
            # counters probably use unsigned values but test
            # sys.maxint returns a signed max so if the prior
            # value is greater than maxint then it is unsigned
            if prior_value > sys.maxsize:
                max_val = sys.maxsize * 2 + 1
            else:
                max_val = sys.maxsize
            corrected = corrected + max_val - \
                        prior_value
        return corrected

    def delta(self, prior_value, current_value):
        """
        Return a delta between the current value and a private one.
        Correct for rollover.
        """
        corrected_current = self.correct_for_rollover(int(prior_value),
                                                      int(current_value))
        delta_value = corrected_current - int(prior_value)
        return delta_value

    def determine_swap_partition(self):
        """
        Use info from the swaps file to determine the swap disk partition
        """
        for line in self.vm_data.splitlines():
            if line.startswith("/dev"):
                swap_partition = line.split()[0]
                self.swap_partition = swap_partition.split('/')[2]
                break

    def sample_cpu_usage(self):
        """
        Read stat file, process, and return the tuple of percentages
        (user,user_nice, sys, and idle). 
        """
        cpu_data = self.cpu_re.findall(self.stat_data)[0]
        if self.initialized:
            sum_deltas = 0
            delta_val = [0, 0, 0, 0]
            percent = [0.0, 0.0, 0.0, 0.0]
            for i in range(0, 4):
                delta_val[i] = self.delta(self.prior_cpu_data[i], cpu_data[i])
                sum_deltas += delta_val[i]
            if sum_deltas > 0:
                for i in range(0, 4):
                    use = float(delta_val[i]) / float(sum_deltas)
                    percent[i] = round(use, 2)
            self.cpu_use = percent
        # always log the current as the prior for the next sample
        self.prior_cpu_data = cpu_data

    def sample_net_usage(self):
        """
        Process the netfile data to produce lists of
        data about the interfaces.
        """
        match_list = re.findall(r'^\s*(\w+):\s+([\d\s]+$)', self.net_data,
                                re.MULTILINE)
        # this list will have a single element for each
        # ethernet interface. Each element has two parts,
        # the interface name and a string of all of the
        # data for the interface
        for element in match_list:
            interface_name = element[0]
            if interface_name in self.interface_names:
                # the interfaces will be discovered at the first sampling
                # create a list for the interface keyed by interface name
                if interface_name not in self.network_interfaces:
                    self.network_interfaces[interface_name] = [0, 0]
                    self.prior_network_interfaces[interface_name] = [0, 0]
                interface_counts = element[1].split()
                delta_val = [0, 0]
                if self.initialized:
                    delta_val[0] = self.delta(self.prior_network_interfaces[ \
                                                  interface_name][0],
                                              interface_counts[0])
                    delta_val[1] = self.delta(self.prior_network_interfaces[ \
                                                  interface_name][1],
                                              interface_counts[8])
                    self.network_interfaces[interface_name] = delta_val
                # build a new list and replace the current
                current_vals = [0, 0]
                current_vals[0] = interface_counts[0]
                current_vals[1] = interface_counts[8]
                self.prior_network_interfaces[interface_name] = \
                    current_vals

    def sample_mem_usage(self):
        """
        Get  info about memory usage - total, used, swap total
        and swap used from memstats
        """
        # process the memstats file into a dictionary by varname
        # stats = self.memstat_re.findall(self.mem_use)
        # mem_dict = {}
        # for list_element in stats:
        #     mem_dict[list_element[0]] = list_element[1]
        # used_mem = float(mem_dict.get("Active", 0))
        # available_mem = float(mem_dict.get("MemTotal", 0)) - used_mem
        # free_swap = float(mem_dict.get("SwapFree", 0))
        # used_swap = float(mem_dict.get("SwapTotal", 0)) - free_swap
        free_data = localFunctions.run_command('free -m', result_as_list=False)
        values = re.findall(r'\s+(\d+)', free_data, re.MULTILINE)
        # self.mem_use = (used_mem, available_mem, used_swap, free_swap)
        if values:
            self.mem_use = (values[1], values[5], values[7], values[8])
        else:
            self.mem_use = ("0", "0", "0", "0")

    def sample_loadavg(self):
        """
        Get just the first value, the 1 minute average from 
        /proc/loadavg
        """
        self.loadavg[0] = float(self.loadavg_data.split()[0])

    def sample_time(self):
        """
        Add the current time to the list of sample times.
        """
        time_val_list = list(time.localtime()[1:6])
        seconds_today = time_val_list[2] * 3600 + time_val_list[3] * 60 + \
                        time_val_list[4]
        time_val_list.append(seconds_today)
        self.time = time_val_list
        self.epoch_time = (int(time.time()))

    def sample_users(self):
        """
        Count the number of unique users
        """
        try:
            users_dict = {}
            users = subprocess.check_output('who')
            for line in users.splitlines():
                users_dict[line.split()[0]] = 1
            self.num_users[0] = len(users_dict)
        except OSError:
            pass

    def sample_vm_swaps(self):
        vm_dict = {}
        try:
            for line in self.vm_data.splitlines():
                line_vals = line.split()
                vm_dict[line_vals[0]] = int(line_vals[1])
            swap_info = [vm_dict["pswpin"], vm_dict["pswpout"]]
            if self.initialized:
                delta_val = [0, 0]
                for i in (0, 1):
                    delta_val[i] = self.delta(self.prior_swap_counts[i],
                                              swap_info[i])
                self.swap_activity = delta_val
                # always log the current as the prior for the next sample
            else:
                self.swap_activity = [0, 0]
            self.prior_swap_counts = swap_info
        except KeyError:
            self.swap_activity = [0, 0]

    def perform_sample(self):
        """
        Capture all information for a single sample
        """
        try:
            self.open_proc_files()
            self.read_proc_files()
            self.close_proc_files()
            self.sample_time()
            self.sample_vm_swaps()
            self.sample_net_usage()
            self.sample_cpu_usage()
            self.sample_mem_usage()
            self.sample_loadavg()
            self.sample_users()
        except Exception as err_val:
            ErrorLogger.error("Error in perform_sample: \n" +
                              localFunctions.generate_exception_string(err_val))
    def initialize(self):
        """
        Perform first sample to populate prior values for initial
        reporting
        """
        self.initialized = False
        self.perform_sample()
        self.initialized = True

    def write_header(self, file):
        w = csv.writer(file)
        headers = ["Month", "Day", "Hour", "Minute", "Second", "Seconds Today",
                   "Num Users", "CPU User", "CPU Nice", "CPU Sys", "CPU Idle",
                   "Load Avg", "Mem Used", "Mem Available", "Swap Used",
                   "Swap Free",
                   "Swap Reads", "Swap Writes"]
        for interface_name in self.interface_names:
            interface_header = [
                interface_name + " Bytes In",
                interface_name + " Bytes Out"]
            headers.extend(interface_header)
        headers.extend(["Epoch Time"])
        w.writerow(headers)

    def write_data(self, file):
        try:
            w = csv.writer(file)
            data = self.time
            data.extend(self.num_users)
            data.extend(self.cpu_use)
            data.extend(self.loadavg)
            data.extend(self.mem_use)
            data.extend(self.swap_activity)
            for interface_name in self.interface_names:
                if interface_name in self.network_interfaces:
                    intfc_data = self.network_interfaces.get(interface_name)
                else:
                    intfc_data = [0, 0, 0, 0]
                data.extend(intfc_data)
            data.append(self.epoch_time)
            w.writerow(data)
        except Exception as err_val:
            ErrorLogger.error("Error in write_data:\n" +
                              localFunctions.generate_exception_string(err_val))


def generate_logfile_name(logfile_prefix):
    """
    Generate a logfile name that is a combination of the
     the logfile root name, the time, and the csv extension.
    """
    if logfile_prefix == "stdout":
        name = "stdout"
    else:
        name = "%s.csv" % logfile_prefix
    return name


def record_results(monitor):
    if not monitor.interface_names:
        monitor.interface_names = list(monitor.network_interfaces.keys())
        monitor.interface_names.sort()
    if logfile_name == "stdout":
        monitor.write_data(sys.stdout)
    else:
        first_write = not (os.path.exists(logfile_name) and
                           os.stat(logfile_name).st_size)
        with open(logfile_name, "a") as file:
            if first_write:
                monitor.write_header(file)
            monitor.write_data(file)


# This will run the program for a fixed time or termination with
# a kill signal. It uses three arguments, sample interval, run time,
# and log file. If the log file exists the results are appended. If not,
# a new file is created.
# The defaults are:
# swap partition: no default
# Interface names : []
# Sample interval: 15 seconds
# Runtime: Unlimited
# Log File: standard out
if __name__ == "__main__":
    parser = localFunctions.initialize_app("systemPerformanceMonitor",
                                           PROGRAM_VERSION,
                                           "Monitor system load",
                                           perform_parse=False)
    parser.add_argument("-n", "--interface_names", dest="interface_names",
                        metavar="list of predefined interface names to be used in reports",
                        default="bond0")
    parser.add_argument("-i", "--interval", type=float,
                        dest="sample_interval",
                        metavar="sample interval (seconds)",
                        default="15")
    parser.add_argument("-r", "--runtime", type=float,
                        dest="runtime",
                        metavar="run time (minutes), 0 means unlimited",
                        default="0")
    parser.add_argument("-f", "--logfile_root_name", dest="logfile_prefix",
                        metavar="common part of generated filename",
                        default="stdout")
    parser.add_argument("-s", "--systemd", action="store_true", dest="systemd")
    opt = parser.parse_args()
    # convert to seconds
    runtime = opt.runtime * 60.0
    sample_interval = opt.sample_interval
    periods = max(int(runtime / sample_interval), 1)
    interface_names = []
    if opt.interface_names:
        interface_names = opt.interface_names.split(',')
        # Add internet interface
        interface_names.append(networkFunctions.internet_network_interface())
    monitor = SysMonitor(interface_names)
    systemd = backgroundFunctions.SystemdSupport()
    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers(INFO_LOGFILE,
                                                                 ERROR_LOGFILE)
    atexit.register(backgroundFunctions.log_stop, systemd, PROGRAM_NAME,
                    InfoLogger)
    if not DEBUG:
        backgroundFunctions.shutdown_if_running(PROGRAM_NAME, ErrorLogger)
    backgroundFunctions.log_start(systemd, PROGRAM_NAME, InfoLogger)
    logfile_name = generate_logfile_name(opt.logfile_prefix)
    monitor.initialize()
    starttime = time.time()
    while (periods > 0) or (opt.runtime == 0.0):
        systemd.update_watchdog()
        starttime = backgroundFunctions.fill_loop_time(sample_interval, starttime)
        monitor.perform_sample()
        record_results(monitor)
        periods -= 1
    sys.exit(0)
