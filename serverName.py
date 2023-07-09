#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Get the name of the server from the openvpn key name
"""
import re
import os.path
import localFunctionsPy3


def get_server_name():
    params_server_name = "Unavailable"
    vpn_server_name = "Unavailable"
    if os.path.exists("/etc/schoolParams.conf"):
        params_server_name = localFunctionsPy3.get_conf_file_value("/etc/schoolParams.conf",
                                                               "School Info", "school_name",
                                                               quiet=True)
    try:
        with open("/etc/openvpn/client.conf", "r") as f:
            contents = f.read()
            server_names = re.findall(r'key /etc/openvpn/keys/([^.]+)', contents, re.M)
            vpn_server_name = server_names[0]
    except OSError:
        pass
    return params_server_name, vpn_server_name


if __name__ == "__main__":
    param_name, vpn_name = get_server_name()
    print("params name '%s'  vpn name '%s'" % (param_name, vpn_name))
