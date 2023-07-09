#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
from PyQt4 import QtGui, uic
import localFunctions
import networkFunctions

VERSION = "0.9"

INTERFACE_FILE_NAMES = ("/etc/network/interfaces.wireless_bond1",
                        "/etc/network/interfaces.wireless_bond2")


class MyWindow(QtGui.QDialog):
    def __init__(self):
        super(MyWindow, self).__init__()
        uic.loadUi('setupWirelessInterface.ui', self)
        self.show()


class WirelessNetwork:
    def __init__(self):

        self.network_interface = ""
        self.configured_interface = ""
        self.prior_name = ""
        self.cell_names = []
        self.cell_qualities = []
        self.live_networks = []
        self.name = ""
        self.password = ""

    def load_info(self):
        network_interfaces, self.cell_names, self.cell_qualities = \
            networkFunctions.get_wireless_info()
        if not network_interfaces:
            self.warn_wireless_not_available()
        self.network_interface = network_interfaces[0]
        self.get_configured_wireless_interface()
        if self.network_interface != self.configured_interface:
            self.warn_wireless_not_matching()
        try:
            if not self.cell_names:
                self.live_networks = ["< None Found >"]
            for i in range(len(self.cell_names)):
                network_line = "%d. %s\n      %s" % (i + 1, self.cell_names[i],
                                                     self.cell_qualities[i])
                self.live_networks.append(network_line)
        except IndexError:
            pass

    def get_configured_wireless_interface(self):
        """
        Confirm that wireless has been chosen for internet. If not, warn and exit.
        If so, return the interface that has been configured.
        :return:
        """
        if networkFunctions.internet_interface_file_network_type() != "wireless":
            text = "Please run 'Choose Internet Interface' and select " + \
                   "'Wireless Interface' before running this app."
            show_message(QtGui.QMessageBox.Critical, "Run First", text)
            sys.exit(-1)
        else:
            self.configured_interface = networkFunctions.internet_network_interface()
        return self.configured_interface

    def warn_wireless_not_available(self):
        text = "No active wireless interface found. Rerun " + \
               "'Choose Network Interface', select 'Wireless Interface', and reboot. " + \
               "If you can't select 'Wireless Interface', this computer does not " + \
               "have a usable wireless."
        show_message(QtGui.QMessageBox.Critical, "No Wireless", text)
        sys.exit(-1)

    def warn_wireless_not_matching(self):
        text = """
The discovered wireless interface '%s' is different
from theconfigured wireless interface '%s'. 
Please rerun 'Choose Internet "Interface' to reset 
the configured interface.""" \
               % (self.network_interface, self.configured_interface)
        show_message(QtGui.QMessageBox.Critical, "Error in Configuration", text)
        sys.exit(-1)

    def show_available_networks(self, window_network_listbox):
        for line in self.live_networks:
            item = QtGui.QListWidgetItem(line)
            window_network_listbox.addItem(item)
            if "Quality=" in line:
                quality = line.split("=")[1]
                if quality:
                    q = int(quality.split('/')[0]) / int(quality.split('/')[1])
                    if q > 0.8:
                        color = QtGui.QColor("green")
                    elif q > 0.5:
                        color = QtGui.QColor("darkgoldenrod")
                    else:
                        color = QtGui.QColor("red")
                    item.setForeground(color)

    def set_configuration(self, name, password):
        if not (name and password):
            show_message(QtGui.QMessageBox.Critical,
                         "Incomplete Entry",
                         "The name or password was not entered.\n" +
                         "The network was not set and will not start.")
            sys.exit(-1)
        for filename in INTERFACE_FILE_NAMES:
            self.name = name
            self.password = password
            networkFunctions.write_wireless_network_file(filename,
                                                         self.network_interface,
                                                         self.name,
                                                         self.password)

    def restart_network(self):
        show_message(QtGui.QMessageBox.Information, "Network Restart",
                     "Restart wireless network. It may take more than a minute.\n" +
                     "Click Ok to begin the restart.")
        if networkFunctions.interface_is_up(self.network_interface):
            localFunctions.command_run_successful(
                "timeout 30 ifdown %s --force" % self.network_interface)
        if not localFunctions.command_run_successful(
                "timeout -s 9 30 ifup " + self.network_interface):
            if self.name not in self.cell_names:
                error_text = "\n'%s' is not in the list of active wireless routers.\n" % self.name
            else:
                error_text = " "
            text = "The wireless was not restarted sucessfully.%s" % error_text + \
                   "Rerun this app to confirm that '%s' has a good signal " % self.name + \
                   "and that you have entered the correct password. " + \
                   "If there are still problems, rerun 'Choose Network Interface' and reboot."
            # cleanup  errored state
            localFunctions.command_run_successful("timeout 30 ifdown --force" +
                                                  self.network_interface)
            show_message(QtGui.QMessageBox.Warning, "Network Failed to Start",
                         text)
        else:
            text = "Success!\nThe interface is active and talking to your wireless router. " + \
                   "Run 'Check Wireless' to see the quality of your link and then run " + \
                   "'System Check' to confirm everything working. If it is not, " + \
                   "reboot to setup all internet services."
            show_message(QtGui.QMessageBox.Information, "Network Restarted",
                         text)

def show_message(message_type, title, text):
    msgBox = QtGui.QMessageBox(
        message_type, title, text,
        QtGui.QMessageBox.Ok)
    msgBox.exec_()


if __name__ == '__main__':
    localFunctions.initialize_app("setupWirelessInterface", VERSION,
                                  "Set wireless network name and password.")
    app = QtGui.QApplication(sys.argv)
    wireless_network = WirelessNetwork()
    wireless_network.load_info()
    window = MyWindow()
    wireless_network.show_available_networks(window.AvailableNetworksList)
    app.exec_()
    if window.result():
        wireless_network.set_configuration(window.NetworkNameBox.text(),
                                           window.NetworkPasswordBox.text())
        wireless_network.restart_network()
    else:
        print("Setup Canceled")
    sys.exit()
