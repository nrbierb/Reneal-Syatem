#!/usr/bin/python3
"""
Write info about cpu and system usage to a file with a file
named  the mac address. This is done once every 30 seconds.
It is run on client computers to provide information to the system
monitor.
"""
import re
import subprocess
import os
import time,argparse

BasePath = "/client_home/share/.client_info"
DefaultInterval = 30
PROGRAM_DESCRIPTION = \
    """Write file containing info about cpu and memory.
    Runs continuously rewriting the file every interval seconds."""
PROGRAM_VERSION = "0.9"
PROGRAM_NAME = "writeMonitorFile"

def initialize_app(name, version, description):
    commandline_parser = argparse.ArgumentParser(prog=name,
                                                 description=description)
    commandline_parser.add_argument('-v', "--version", action='version',
                                    version=version)
    commandline_parser.parse_args()

def create_filename(base_directory):
    """
    Generate info file.
    """
    filename = "client.sysinfo"
    try:
        netinfo = subprocess.check_output("/sbin/ifconfig")
        mac_addresses = re.findall(r'HWaddr\s+([\w:]+)', netinfo)
        if mac_addresses:
            filename = mac_addresses[0] + '.sysinfo'
    except subprocess.CalledProcessError:
        pass
    filename = os.path.join(base_directory, filename)
    return filename


def generate_monitorfile(filename, interval):
    """
    Create the file filename after interval seconds.
    The interval in top command delays the writing until
    interval seconds after call
    :param filename:
    :param interval:
    :return:
    """
    try:
        data = subprocess.check_output('lscpu', shell=True)
        data += "--------------------------------------------------\n"
        data += subprocess.check_output('free -m', shell=True)
        data += "--------------------------------------------------\n"
        data += subprocess.check_output('/usr/bin/top -d %d -n 2 -b -u \!0' % interval,
                                        shell=True)
    except subprocess.CalledProcessError as e:
        time.sleep(interval)
        data = ""
    try:
        f = open(filename, 'w')
        f.write(data)
        f.close()
    except IOError:
        pass


if __name__ == "__main__":
    commandline_parser = argparse.ArgumentParser(prog=PROGRAM_NAME,
                                                 description=PROGRAM_DESCRIPTION)
    commandline_parser.add_argument('-v', "--version", action='version',
                                    version=PROGRAM_VERSION)
    commandline_parser.add_argument('-n', "--num-iterations", default=0,
                                    type=int, dest="num_iterations",
                                    help="Number of iterations. 0 means continuously")
    commandline_parser.add_argument("-i", "--interval", default = DefaultInterval,
                                    type=int, dest="interval", help=
                                    "Interval between writes")
    commandline_parser.add_argument("-d", "--directory", default=BasePath, dest="directory",
                                    help="Directory for file")
    commandline_parser.add_argument("-f", "--filename", default="", dest="filename",
                                    help="Filename. Default filename is MACADDR.sysinfo")
    opt = commandline_parser.parse_args()
    filename = os.path.join(opt.directory,opt.filename)
    if not opt.filename:
        filename = create_filename(opt.directory)
    if opt.num_iterations:
        for _ in range(opt.num_iterations):
            generate_monitorfile(filename, opt.interval)
    else:
        while True:
            generate_monitorfile(filename, opt.interval)
