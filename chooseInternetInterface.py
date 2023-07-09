#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import os
import os.path
import localFunctions
import networkFunctions
from PyQt4 import QtGui, uic

VERSION = "0.9"
PROGRAM_NAME = "chooseInternetInterface"
ERROR_STRING = ""

class MyWindow(QtGui.QDialog):
    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('chooseInternetInterface.ui', self)
        self.show()


class NetworkInterfaceSetup:

    def __init__(self, ui_window):
        self.ui_window = ui_window
        self.wireless_count = 0
        self.ethernet_count = 0
        self.type = ""
        self.initial_type = ""
        self.link_filename = "interfaces.ethernet_bond2"
        self.wireless_interface_name = ""
        self.changed = True
        self.needs_restart = True

    def initialize(self):
        self.type = networkFunctions.internet_interface_file_network_type()
        self.ethernet_count, self.wireless_count = \
            networkFunctions.network_interface_type_count()
        if self.wireless_available():
            interfaces = networkFunctions.get_wireless_name()
            if interfaces:
                self.wireless_interface_name = interfaces[0]
        elif self.ethernet_count == 1:
            self.type = "no_internet"
        self.initial_type = self.type
        self.initialize_ui()

    def initialize_ui(self):
        self.ui_window.Wireless_button.setEnabled(self.wireless_available())
        self.ui_window.Ethernet_button.setChecked(True)
        if self.type == "wireless" and self.wireless_available():
            self.ui_window.Wireless_button.setChecked(True)
        elif self.type == "no_internet":
            self.ui_window.None_button.setChecked(True)

    def wireless_available(self):
        return self.wireless_count > 0

    def build_link_filename(self):
        if self.type == "wireless":
            bond_suffixes = ("wireless_only", "bond1", "bond1", "bond2", "bond2")
        else:
            bond_suffixes = ("empty", "bond1", "bond1", "bond2", "bond2")
        self.link_filename = ".%s_%s" % (self.type,
                                         bond_suffixes[self.ethernet_count])

    def setup_link(self):
        target_files = (("/etc/network", "interfaces"),
                        ("/etc/shorewall", "interfaces"),
                        ("/etc/shorewall", "masq"))
        try:
            for base_directory, target_filename in target_files:
                target = os.path.join(base_directory, target_filename)
                full_link_name = os.path.join(base_directory,
                                              target_filename + self.link_filename)
                if os.path.exists(full_link_name):
                    if not os.path.exists(target):
                        os.symlink(full_link_name, target)
                    elif not os.path.samefile(target, full_link_name):
                        os.unlink(target)
                        os.symlink(full_link_name, target)
        except OSError as e:
            localFunctions.add_error_report( "Setup Link failed: %s\n" %e)

    def setup_wireless(self):
        networkFunctions.write_wireless_network_file("/etc/network/interfaces",
                                                     self.wireless_interface_name)
        masq_line = self.wireless_interface_name + "\t\tbond0"
        localFunctions.replace_line_in_file("/etc/shorewall/masq",
                                            "/etc/shorewall/masq",
                                            r'\w+\s+\w+$', masq_line)
        interface_line = "net\t" + self.wireless_interface_name + "\tdetect\tdhcp"
        localFunctions.replace_line_in_file("/etc/shorewall/interfaces",
                                            "/etc/shorewall/interfaces",
                                            r'net\s+\w+\s+detect', interface_line)
        config_line = "internet_interface = " + self.wireless_interface_name
        localFunctions.replace_line_in_file("/etc/systemCheck.config",
                                            "/etc/systemCheck.config",
                                            r'\s*internet_interface = ',
                                            config_line)
        config_line = "internet_available = True"
        localFunctions.replace_line_in_file("/etc/systemCheck.config",
                                            "/etc/systemCheck.config",
                                            r'\s*internet_available = ',
                                            config_line)
        if not networkFunctions.interface_is_up(self.wireless_interface_name):
            localFunctions.command_run_successful("ifconfig %s up"
                                                  % self.wireless_interface_name)

    def set_type(self, interface_type):
        self.type = interface_type
        self.build_link_filename()
        self.setup_link()
        if self.type == "wireless" and self.wireless_interface_name:
            self.setup_wireless()


def restart_network():
    print("starting")


if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, VERSION,
                                  "Choose the type of interface used to connect to internet.")
    localFunctions.confirm_root_user(PROGRAM_NAME)
    app = QtGui.QApplication(sys.argv)
    window = MyWindow()
    network_interfaces = NetworkInterfaceSetup(window)
    network_interfaces.initialize()
    app.exec_()
    if window.result():
        if window.Ethernet_button.isChecked():
            network_interfaces.set_type("ethernet")
        elif window.Wireless_button.isChecked():
            network_interfaces.set_type("wireless")
        else:
            network_interfaces.set_type("no_internet")
    else:
        print("Change canceled.")
    sys.exit()
