#!/usr/bin/python3
#  -*- coding: utf-8 -*-

# From implementation generated from reading ui file 'SystemTest.ui'
#
# Created: Fri Mar 28 06:14:57 2014
#      by: PyQt4 UI code generator 4.9.1
#

from PyQt4 import QtCore, QtGui
import systemCheck

ActiveGuiConnector = None

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

ui = None

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(581, 700)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("DejaVu Sans"))
        MainWindow.setFont(font)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.gridGroupBox = QtGui.QGroupBox(self.centralwidget)
        self.gridGroupBox.setAutoFillBackground(True)
        self.gridGroupBox.setFlat(False)
        self.gridGroupBox.setObjectName(_fromUtf8("gridGroupBox"))
        self.gridLayout = QtGui.QGridLayout(self.gridGroupBox)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.internetAvailableCheckbox = QtGui.QCheckBox(self.gridGroupBox)
        self.internetAvailableCheckbox.setChecked(True)
        self.internetAvailableCheckbox.setObjectName(_fromUtf8("internetAvailableCheckbox"))
        self.gridLayout.addWidget(self.internetAvailableCheckbox, 0, 0, 1, 1)
        self.clientActiveCheckbox = QtGui.QCheckBox(self.gridGroupBox)
        self.clientActiveCheckbox.setChecked(True)
        self.clientActiveCheckbox.setObjectName(_fromUtf8("clientActiveCheckbox"))
        self.gridLayout.addWidget(self.clientActiveCheckbox, 1, 0, 1, 1)
        self.writeLogCheckbox = QtGui.QCheckBox(self.gridGroupBox)
        self.writeLogCheckbox.setChecked(False)
        self.writeLogCheckbox.setObjectName(_fromUtf8("writeLogCheckbox"))
        self.gridLayout.addWidget(self.writeLogCheckbox, 0, 1, 1, 1)
        self.testQualityCheckbox = QtGui.QCheckBox(self.gridGroupBox)
        self.testQualityCheckbox.setChecked(False)
        self.testQualityCheckbox.setObjectName(_fromUtf8("checkQualityCheckbox"))
        self.gridLayout.addWidget(self.testQualityCheckbox, 1, 1, 1, 1)
        self.verticalLayout.addWidget(self.gridGroupBox)
        self.runStatusLabel = QtGui.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("DejaVu Sans"))
        self.runStatusLabel.setFont(font)
        self.runStatusLabel.setObjectName(_fromUtf8("runStatusLabel"))
        self.verticalLayout.addWidget(self.runStatusLabel)
        self.progressBar = QtGui.QProgressBar(self.centralwidget)
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setInvertedAppearance(False)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.verticalLayout.addWidget(self.progressBar)
        self.testProgessLabel = QtGui.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("DejaVu Sans"))
        self.testProgessLabel.setFont(font)
        self.testProgessLabel.setObjectName(_fromUtf8("testProgessLabel"))
        self.verticalLayout.addWidget(self.testProgessLabel)
        self.statusTextBox = QtGui.QTextEdit(self.centralwidget)
        self.statusTextBox.setObjectName(_fromUtf8("statusTextBox"))
        self.verticalLayout.addWidget(self.statusTextBox)
        self.testResultsLabel = QtGui.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("DejaVu Sans"))
        self.testResultsLabel.setFont(font)
        self.testResultsLabel.setObjectName(_fromUtf8("testResultsLabel"))
        self.verticalLayout.addWidget(self.testResultsLabel)
        self.resultsTextBox = QtGui.QTextEdit(self.centralwidget)
        self.resultsTextBox.setObjectName(_fromUtf8("resultsTextBox"))
        self.verticalLayout.addWidget(self.resultsTextBox)
        self.runButton = QtGui.QPushButton(self.centralwidget)
        self.runButton.setMaximumSize(QtCore.QSize(100, 50))
        font = QtGui.QFont()
        font.setFamily(_fromUtf8("DejaVu Sans"))
        font.setPointSize(13)
        font.setBold(True)
        font.setWeight(75)
        self.runButton.setFont(font)
        self.runButton.setDefault(True)
        self.runButton.setFlat(False)
        self.runButton.setObjectName(_fromUtf8("runButton"))
        self.verticalLayout.addWidget(self.runButton)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 581, 26))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menuFile = QtGui.QMenu(self.menubar)
        self.menuFile.setObjectName(_fromUtf8("menuFile"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.actionClose = QtGui.QAction(MainWindow)
        self.actionClose.setObjectName(_fromUtf8("actionClose"))
        self.menuFile.addAction(self.actionClose)
        self.menubar.addAction(self.menuFile.menuAction())
        #----self.actionQuit = QtGui.QAction(MainWindow)
       # self.actionQuit.setObjectName(_fromUtf8("actionQuit"))
        self.menuHelp = QtGui.QMenu(self.menubar)
        self.menuHelp.setObjectName(_fromUtf8("menuHelp"))
        self.actionHelp = QtGui.QAction(MainWindow)
        self.actionHelp.setObjectName(_fromUtf8("actionHelp"))
        self.actionAbout = QtGui.QAction(MainWindow)
        self.actionAbout.setObjectName(_fromUtf8("actionAbout"))
        self.menuHelp.addAction(self.actionHelp)
        self.menuHelp.addAction(self.actionAbout)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.actionHelp.triggered.connect(self.openHelpMessage)
        self.actionAbout.triggered.connect(self.openAboutMessage)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.runButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.centralwidget.update)
        QtCore.QObject.connect(self.runButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.statusTextBox.clear)
        QtCore.QObject.connect(self.runButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.resultsTextBox.clear)
        QtCore.QObject.connect(self.runButton, QtCore.SIGNAL(_fromUtf8("clicked()")), self.progressBar.reset)
        QtCore.QObject.connect(self.runButton, QtCore.SIGNAL(_fromUtf8("clicked()")), GuiRunCheck)
        QtCore.QObject.connect(self.actionClose, QtCore.SIGNAL(_fromUtf8("activated()")), MainWindow.close)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "System Check", None, QtGui.QApplication.UnicodeUTF8))
        self.gridGroupBox.setTitle(QtGui.QApplication.translate("MainWindow", "Test Options", None, QtGui.QApplication.UnicodeUTF8))
        self.internetAvailableCheckbox.setToolTip(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p>Uncheck if your school has no internet connection or internet modem. Then no tests will be run for the internet and System Check can finish much faster.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.internetAvailableCheckbox.setText(QtGui.QApplication.translate("MainWindow", "Internet Available", None, QtGui.QApplication.UnicodeUTF8))
        self.clientActiveCheckbox.setToolTip(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p>Uncheck if there are no client computers running on the local network. Then no tests will be run to look for clients and System Check can finish much faster. Ok to leave checked all of the time.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.clientActiveCheckbox.setText(QtGui.QApplication.translate("MainWindow", "Clients Active", None, QtGui.QApplication.UnicodeUTF8))
        self.writeLogCheckbox.setText(QtGui.QApplication.translate("MainWindow", "Write Log", None, QtGui.QApplication.UnicodeUTF8))
        self.writeLogCheckbox.setToolTip(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p>Check to write a log of this run.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.testQualityCheckbox.setToolTip(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p>Uncheck if you do not wish to perform internet quality checks if the internet is working. Then no test will be made and System Check can finish faster. Ok to leave checked all of the time.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.testQualityCheckbox.setText(QtGui.QApplication.translate("MainWindow", "Test Internet Quality", None, QtGui.QApplication.UnicodeUTF8))
        self.runStatusLabel.setText(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Test Progress</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.progressBar.setToolTip(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p>The estimated percentage of the test completed so far.</p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.testProgessLabel.setText(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Run Status</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.testResultsLabel.setText(QtGui.QApplication.translate("MainWindow", "<html><head/><body><p align=\"center\"><span style=\" font-weight:600;\">Test Results</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.runButton.setToolTip(QtGui.QApplication.translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'DejaVu Sans\'; font-size:13pt; font-weight:600; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><span style=\" font-weight:400;\">Click to start the System Check</span></p></body></html>", None, QtGui.QApplication.UnicodeUTF8))
        self.runButton.setText(QtGui.QApplication.translate("MainWindow", "Run Test", None, QtGui.QApplication.UnicodeUTF8))
        self.menuFile.setTitle(QtGui.QApplication.translate("MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.actionClose.setText(QtGui.QApplication.translate("MainWindow", "Close", None, QtGui.QApplication.UnicodeUTF8))
        self.menuHelp.setTitle(QtGui.QApplication.translate("MainWindow", "Help", None))
        self.actionHelp.setText(QtGui.QApplication.translate("MainWindow", "Help", None))
        self.actionAbout.setText(QtGui.QApplication.translate("MainWindow", "About", None))


    def openHelpMessage(self):
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.NoIcon)
        msg.setText("""<html><head/><body>
            <p align="center"><b>Quick Help</b></p>
            <ul><font color="#008000"><b>
                <li>Check or uncheck the options for tests at the top of the window</li>
                <li>Click the "Run Test" button to start all tests</li>
                <li>Monitor the test actions as they occur in the top window.</li>
                <li>Review the results in the lower box once the test is completed.</li>
                <li>Perform any recommended tasks.</li>
                <li>Rerun the check just by clicking the "Run Test" button.</li>
            </b></font></ul>
            </body></html>""")
        msg.setWindowTitle("Help")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        return msg.exec_()

    def openAboutMessage(self):
        """
        Simple info dialog used for the "About" button.
        :return:
        """
        msg = QtGui.QMessageBox()
        msg.setIcon(QtGui.QMessageBox.NoIcon)
        msg.setText("""<html><head/><body>
            <p align="center"><b>systemCheck</b></p>
            <p align="center">Version %s</p>
            <p>This program is designed aid system administrators.</p>
            <p>Use the program to identify and fix
            many problems with the entire computer lab.
            <p>Copyright 2017-2022 by Neal Bierbaum, Reneal IEO</p>
            <p>Released under open source license GPL 3</p>
            </body></html>""" %systemCheck.ProgramVersion)
        msg.setWindowTitle("About")
        msg.setStandardButtons(QtGui.QMessageBox.Ok)
        return msg.exec_()


class GuiConnector:
    """
    Manage the communications between the systemCheck base program and the
    GUI interface.
    """
    def __init__(self, system_config, gui, app):
        """
        :param system_config:
        :param gui:
        :return: none
        """
        global ActiveGuiConnector
        self.system_config = system_config
        self.gui = gui
        self.app = app
        self.gui_config = {}
        self.message_colors = {"information":"DarkSlateGray", "problem":"OrangeRed",
            "requires user action":"Maroon","fixable problem":"DarkBlue",
            "fixing problem":"Blue", "fix result good":"DarkGreen",
            "fix result bad":"DarkOrange", "serious problem":"Red", "values":"DarkSlateGray",
            "no problems":"Green"}
        self.initialize_gui_config()
        ActiveGuiConnector = self

    def initialize_gui_config(self):
        """
        Set the check boxes depending upon the current configuration derived from
        from the default values and the configuration file. This is important to uncheck
        internet checkboxes if no internet is available
        """
        try:
            self.gui.internetAvailableCheckbox.setChecked(self.system_config.params_dict["internet_available"])
            self.gui.testQualityCheckbox.setChecked(self.system_config.params_dict["check_internet_quality"] and 
                                                    self.system_config.params_dict["internet_available"])
        except:
            pass
        
    def generate_gui_config(self):
        self.gui_config = {}
        self.gui_config["internet_available"] = self.gui.internetAvailableCheckbox.isChecked()
        self.gui_config["look_for_local_hosts"] = self.gui.clientActiveCheckbox.isChecked()
        self.gui_config["check_internet_quality"] = self.gui.testQualityCheckbox.isChecked()
        self.gui_config["write_log"] = self.gui.writeLogCheckbox.isChecked()

    def getGuiConfig(self):
        return self.gui_config

    def update_gui(self):
        while self.app.hasPendingEvents():
            self.app.processEvents()

    def insert_progress_text(self, progress_text):
        self.gui.statusTextBox.insertPlainText(progress_text + "\n")
        self.update_gui()

    def show_percent_complete(self, percent_complete):
        self.gui.progressBar.setValue(percent_complete)
        self.update_gui()

    def generate_information_text(self, entry_type, prefix, message_text, emphasized=False):
        if emphasized:
            html_text = '<div style="color:%s"><b>%s-->  %s</b></div><br></br>' \
                %(self.message_colors.get(entry_type, "DarkGrey"), prefix, message_text)
        else:
            html_text = '<div style="color:%s"><b>%s-->  </b>%s</div><br></br>' \
                %(self.message_colors.get(entry_type, "DarkGrey"), prefix, message_text)
        return html_text

    def insert_information_text(self, entry_type, prefix, message_text, emphasized=False):
        html_text = self.generate_information_text(entry_type, prefix, message_text, emphasized)
        self.gui.resultsTextBox.insertHtml(html_text)
        self.update_gui()

    def insert_simple_text(self, entry_type, message_text, emphasized=False):
        if emphasized:
            html_text = '<div style="color:%s"><b>%s</b></div><br></br>' \
                %(self.message_colors.get(entry_type, "DarkGrey"), message_text)
        else:
            html_text = '<div style="color:%s">%s</div><br></br>' \
                %(self.message_colors.get(entry_type, "DarkGrey"), message_text)
        self.gui.resultsTextBox.insertHtml(html_text)
        self.update_gui()

def GuiRunCheck():
    global ActiveGuiConnector
    ActiveGuiConnector.generate_gui_config()
    systemCheck.runCheck(ActiveGuiConnector.system_config, ActiveGuiConnector)

# if __name__ == "__main__":
#     import sys
#     app = QtGui.QApplication(sys.argv)
#     MainWindow = QtGui.QMainWindow()
#     ui = Ui_MainWindow()
#     ui.setupUi(MainWindow)
#     MainWindow.show()
#     sys.exit(app.exec_())

