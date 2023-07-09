#!/usr/bin/python3
# -*- coding: utf-8 -*-

import localFunctions
import networkFunctions
import subprocess
import os
import re
import ipaddress

FORM_VALUES = {"address": "192.168.1.2", "netmask": "255.255.255.0", "gateway": "192.168.1.1"}
INITIAL_FORM_VALUES = {"address": "192.168.1.2", "netmask": "255.255.255.0", "gateway": "192.168.1.1"}
FORM_TUPLES = {"address": [0, 0, 0, 0], "netmask": [255, 255, 255, 0],
               "gateway": [0, 0, 0, 0]}
BAD_FORM_REASON = ""
TEMPLATE_FILE = "/etc/network/template_interfaces.manual_bond2"
INTERFACE_FILE = "/etc/network/interfaces.manual_bond2"
LINK_FILE = "/etc/network/interfaces"
DHCP_INTERFACE_FILE = "/etc/network/interfaces.ethernet_bond2"
PROGRAM_DESCRIPTION = \
    "Set address for internet interface if needed."
PROGRAM_VERSION = "0.8"
PROGRAM_NAME = "setInternetIpAddress"


def process_ip_address_string(input_string, max_val=254):
    bad_string_reason = ""
    cleaned_string = ""
    nl = []
    try:
        if not input_string:
            bad_string_reason += "Empty address entry.\n"
        else:
            parts = input_string.split(".")
            if len(parts) != 4:
                bad_string_reason += \
                    """Incorrect number of dot separated parts:
                    Found %d, should be 4.\n""" % len(parts)
            else:
                for part in parts:
                    try:
                        number = int(part)
                        if not (0 <= number <= max_val):
                            error = "%d is not in the range 0-%d\n" % (number, max_val)
                            bad_string_reason += error
                            continue
                        nl.append(number)
                    except (TypeError, ValueError):
                        if part:
                            error = "'%s' is not a number.\n" %part
                        else:
                            error = "Missing a value in the address.\n"
                        bad_string_reason += error
        cleaned_string = "%d.%d.%d.%d" % (nl[0], nl[1], nl[2], nl[3])
    except (AttributeError, IndexError):
        bad_string_reason += "'%s' could not be processed.\n" % input_string
    return cleaned_string, nl, bad_string_reason


def process_form_value(value_string, max_val, name, error_header):
    global FORM_VALUES, FORM_TUPLES, BAD_FORM_REASON
    cleaned_string, number_list, bad_string_reason = \
        process_ip_address_string(value_string, max_val)
    if bad_string_reason:
        BAD_FORM_REASON += "%s not correct:\n%s\n" % (
        error_header, bad_string_reason)
        FORM_VALUES[name] = ""
        FORM_TUPLES[name] = [0, 0, 0, 0]
    else:
        FORM_VALUES[name] = cleaned_string
        FORM_TUPLES[name] = number_list

def check_address_in_network():
    global FORM_VALUES, BAD_FORM_REASON
    subnet = ipaddress.IPv4Network("%s/%s" %(FORM_VALUES["gateway"], FORM_VALUES["netmask"]),
                        strict=False)
    gateway_address = ipaddress.IPv4Network("%s/32" %FORM_VALUES["gateway"])
    ip_address = ipaddress.IPv4Network("%s/32" %FORM_VALUES["address"])
    same_address = gateway_address.overlaps(ip_address)
    in_subnet = ip_address.overlaps(subnet)
    subnet_min = next(subnet.hosts())
    subnet_max = subnet.broadcast_address -1
    if same_address:
        BAD_FORM_REASON += 'The network address and host address\ncannot be the same.'
    if not in_subnet:
        BAD_FORM_REASON += \
            'The network address %s is not in the gateways subnet.\nAddresses must be between %s and %s' \
            %(FORM_VALUES["address"], subnet_min, subnet_max)



def generate_form():
    global FORM_VALUES, BAD_FORM_REASON
    BAD_FORM_REASON = ""
    command = """yad --title="Set Internet IP" --borders=20 --form \
--field="<b>Network Address</b>" "%s" \
--field="<b>Netmask</b>" "%s" \
--field="<b>Gateway</b>" "%s" \
--field="Ignore values and use DHCP instead:CHK" \
--field="Note:All values should be in standard\n    IPv4 dotted notation:LBL" """\
              % (FORM_VALUES["address"], FORM_VALUES["netmask"],
                 FORM_VALUES["gateway"])
    try:
        result = localFunctions.run_command(command, reraise_error=True,
                                            result_as_list=False,
                                            merge_stderr=False,
                                            no_stderr=True)
        return result
    except subprocess.CalledProcessError as e:
        cancel_program()


def process_form(form_result):
    try:
        values = form_result.split("|")
    except AttributeError:
        values = ["", "","",""]
    try:
        if values[3] == "TRUE":
            setup_for_dhcp()
        process_form_value(values[0], 254, "address", "IP address")
        process_form_value(values[1], 255, "netmask", "Netmask")
        process_form_value(values[2], 254, "gateway", "Gateway address")
        if not BAD_FORM_REASON:
            check_address_in_network()
    except IndexError as e:
        localFunctions.error_exit(str(e), use_gui=True)

def compare_address_values(set1, set2):
    same = True
    for name in "address", "netmask", "gateway":
        if set1[name] != set2[name]:
            same = False
            break
    return same

def write_file():
    global TEMPLATE_FILE, INTERFACE_FILE, LINK_FILE, DHCP_INTERFACE_FILE
    global FORM_VALUES, INITIAL_FORM_VALUES
    field_associations = (("<<internet_address>>", FORM_VALUES["address"]),
                          ("<<internet_netmask>>", FORM_VALUES["netmask"]),
                          ("<<internet_gateway>>", FORM_VALUES["gateway"]))
    fin = open(TEMPLATE_FILE, 'r')
    file_text = fin.read()
    fin.close()
    for association in field_associations:
        file_text = file_text.replace(association[0], association[1])
    fout = open(INTERFACE_FILE, "w")
    fout.write(file_text)
    fout.close()

def set_file_link(source_file):
    global LINK_FILE
    try:
        os.remove(LINK_FILE)
    except FileNotFoundError:
        pass
    try:
        os.symlink(source_file, LINK_FILE)
    except OSError as err:
        error_string = "File symlink %s to %s failed: %s" \
                       % (source_file, LINK_FILE, err)
        localFunctions.error_exit(error_string, use_gui=True)

def setup_for_dhcp():
    command= 'zenity --title="Use DHCP?" --question ' + \
        '--text="<b>Should I use DHCP to set my internet interface address?</b>"'
    if localFunctions.command_run_successful(command):
        command='zenity --title="Using DHCP" --info' +\
        ' --text "<b>OK\nI will use DHCP.</b>"'
        localFunctions.command_run_successful(command)
        if os.path.samefile(LINK_FILE, DHCP_INTERFACE_FILE):
            exit_with_no_change()
        else:
            set_file_link(DHCP_INTERFACE_FILE)
            suggest_reboot()
        localFunctions.error_exit("Setup for DHCP.",  exit_code=0)
    else:
        command = 'zenity --title="Using Manual IP" --info' + \
                  ' --text "<b>I will use the manual setting you are making now.</b>"'
        localFunctions.command_run_successful(command)

def setup_for_manual():
    if os.path.samefile(LINK_FILE, INTERFACE_FILE) and \
        compare_address_values(FORM_VALUES, INITIAL_FORM_VALUES):
        exit_with_no_change()
    else:
        write_file()
        set_file_link(INTERFACE_FILE)
        suggest_reboot()

def suggest_reboot():
    command = 'zenity --title="Reboot To Set Network" --info --text="<b>Reboot to make the changes active.</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit("Completed change.")

def cancel_program():
    command = 'zenity --title="Nothing Set" --info --text="<b>Ok.\nNothing was done.</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit("Interface setup canceled.")

def read_existing_file():
    global INTERFACE_FILE, FORM_VALUES, INITIAL_FORM_VALUES
    try:
        with open(INTERFACE_FILE,"r") as f:
            text = f.read()
            values = re.findall(
                r'internet inet static\naddress (\d+\.\d+\.\d+\.\d+)\nnetmask (\d+\.\d+\.\d+\.\d+)\ngateway (\d+\.\d+\.\d+\.\d+)',
            text,re.S)
            process_form_value(values[0][0], 254, "address", "IP address")
            process_form_value(values[0][1], 255, "netmask", "Netmask")
            process_form_value(values[0][2], 254, "gateway", "Gateway address")
            for name in "address", "netmask", "gateway":
                INITIAL_FORM_VALUES[name] = FORM_VALUES[name]
    except OSError:
        pass

def exit_with_no_change():
    command = 'zenity --title="No Changes Made" --info --text="<b>No changes were made.</b>"'
    localFunctions.command_run_successful(command)
    localFunctions.error_exit("No changes made.", exit_code=0)

if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                  PROGRAM_DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    read_existing_file()
    BAD_FORM_REASON = "start"
    while BAD_FORM_REASON:
        form_result = generate_form()
        process_form(form_result)
        if BAD_FORM_REASON:
            display_text = localFunctions.color_text("red",'%s\n\nYou need to correct the form entries.' %BAD_FORM_REASON,
                                                     use_gui=True)
            command = """zenity --title 'Errors in Form' --warning --text='%s' """ %display_text
            localFunctions.command_run_successful(command)
    setup_for_manual()
