#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
setupWireless: A simple program to write the wireless network name and password
into the /etc/network/interfaces file. Keywords "NETWORK_NAME" and "NETWORK_PASSWORD"
must be in the template interfaces file
"""
import localFunctions
import subprocess
import sys

DIALOG = 'zenity --text="Setup Wireless" --add-entry="Wireless Network Name" --add-entry="WirelessPassword" --forms'
INTERFACE_CONFIGURATION_FILE_TEMPLATE = "/etc/network/interfaces.template"
INTERFACE_CONFIGURATION_FILE = "/etc/network/interfaces"

def user_dialog():
    try:
        result = subprocess.run(DIALOG, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, shell=True, check=True)
        network_name, network_password = result.stdout.strip().split("|")
        if len(network_name) and len(network_password):
            return network_name, network_password
        else:
            localFunctions.error_exit("Please enter both network name and password",
                                      -1)
    except (subprocess.CalledProcessError, ValueError):
        localFunctions.error_exit("Wireless setup values entered incorrectly. Please rerun this program.", -1)

def write_values_in_file(network_name, network_password):
    try:
        with open(INTERFACE_CONFIGURATION_FILE, "r") as config_file:
            config_lines = config_file.read().splitlines(keepends=True)
        with open("/tmp/test", "w") as config_file:
            for line in config_lines:
                if line != "\n":
                    if line.find("wpa-ssid") != -1:
                        line = "wpa-ssid %s\n" %network_name
                    elif line.find("wpa-psk") != -1:
                        line = "wpa-psk %s\n" %network_password
                config_file.write(line)
    except IOError as e:
        localFunctions.error_exit("Wireless setup failed to create the configuration file. Review error," \
              "confirm sudo, then try again. ERROR: %s" %e, -1)
        sys.exit(-1)

def restart_network():
    print("This may take a minute. Ignore errors if the wireless is not available now.")
    if localFunctions.command_run_successful("ifdown internet"):
        if localFunctions.command_run_successful("ifup internet"):
            print("Connected successfully. Test the wireless connection")
        else:
            print("""
Failed to make a connection to the wireless router. 
Check name and password and rerun this app.""")
    else:
        print("""
Failed to shutdown the wireless interface. 
Please reboot to start the wireless correctly.""")

if  __name__ == '__main__':
    network_name, network_password = user_dialog()
    write_values_in_file(network_name, network_password)
    restart_network()

