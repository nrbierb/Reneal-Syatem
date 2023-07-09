#!/usr/bin/python3
# -*- coding: utf-8 -*-

import localFunctions
import networkFunctions
import re

PROGRAM_NAME = "checkWireless"
VERSION = 0.8

def get_statistics(wireless_interface):
    name = ""
    quality = ""
    signal_level = ""
    data = localFunctions.run_command( "iwconfig " + wireless_interface,
                                       result_as_list=False)
    match_list = re.search(r'ESSID:"([^"]+)".+Quality=(\d+\/\d+).+Signal level=-(\d+)',
                             data, re.S)
    if match_list:
        name, quality, signal_level = match_list.groups()
    return name, quality, signal_level

def get_configured_wireless_information():
    """
    Confirm that wireless has been chosen for internet. If not, warn and exit.
    If so, return the interface that has been configured.
    :return:
    """
    interface = ""
    name = ""
    if networkFunctions.internet_interface_file_network_type() == "wireless":
        values = localFunctions.findall_in_file("/etc/network/interfaces",
                                       r'external.*?iface\s+(\w+).*?ssid\s([\w\s].*?\w)\s*$')
        if len(values):
            interface = values[0][0]
            name = values[0][1]
    return interface, name

if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, VERSION,
            "Show wireless link quality.")
    interface, configured_name = get_configured_wireless_information()
    if interface:
        name, quality, signal_level = networkFunctions.get_wireless_statistics(interface)
        if quality:
            q = int(quality.split('/')[0]) / int(quality.split('/')[1])
            if q > 0.6:
                color= '#009900'
            elif q > 0.3:
                color = '#B8860B'
            else:
                color= '#990000'
            name = "<span font_weight='bold'>%s</span>" %name
            quality = "<span font_weight='bold' fgcolor='%s'>%s</span>" %(color, quality)
            signal_level = "<span font_weight='bold'>%s</span>" %signal_level
            result = "Network name: %s\nQuality: %s\nSignal level: %s" \
                     %(name, quality, signal_level)
            command = 'zenity --title="Wireless Link Status" --info ' +\
                '--text="%s" --icon-name="network-wireless"' %result
        else:
            text = "<span size='larger' fgcolor='#990000'>Wireless router '%s' was not detected.\n" %configured_name +\
                "It might be out of range or turned off.</span>"
            command = 'zenity --title="Wireless Link Status" --info ' + \
                      '--text="%s" --icon-name="network-error"' %text
    else:
        text = "No Wireless Configured."
        command = 'zenity --title="No Wireless" --warning '+\
            '--text="No wireless interface configured." --icon-name="network-error"'
    localFunctions.run_command(command)
