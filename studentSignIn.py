#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'studentSignIn1.ui'
#
# Created: Tue Mar  5 15:54:06 2013
#      by: PyQt4 UI code generator 4.9.1
#
"""
This is a gui application to be launched upon login in student accounts.
It successively uses a list of class year, section or class, and students
in the section to allow the student to identify themself. Each student has
their own personal area to store files. Once the student has chosen the
name the "Sign In" button is activated. Once clicked, symbolic links are 
placed for Documents, Projects, and the firefox bookmarks in the logged in
account home directory to the directories in the students personal
area. If the personal directory does not exist the setuid program
"makeStudentHomeDirectory" is called with the desired directory. This 
means that no student personal area directories need be explictly created
by the system administrator but all the personal directories should be 
prior to the start of a new school year to prevent buildup of obsolete
directories. 
The list of students with their class year and section is mainatained in 
a csv file that is read upon program start. This must be created by the
system administrator prior to the start of the school year and should 
contain information about all students.
If a person not in the student list log in as a student user
they can click the "Guest" button at any time. This will create links 
to a default personal area used by all who sign in as Guest.
The name for the students class year or grade varies by country. Currently
it is "Grade" for the Philippines and "Form Level" for Tanzania.  Philippine
colleges have yet another naming scheme. This means that
the column heading in the csv file and the label on the gui needs to be
change3d appropriately. Set the global variable ClassYearName to the
correct value/
See "makeStudentHomeDirectories" for further information about 
personal directory creation.
"""
import bisect
import csv
import os
import re
import subprocess
import sys
import localFunctions

from PyQt4 import QtGui, QtCore

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

VERSION = "1.04"
PROGRAM_NAME = "studentSignIn"

StudentDataFile = "/client_home/share/student_list.csv"
BaseDirectory = "/client_home_students"
GuestDirectory = os.path.join(BaseDirectory, "GuestUser")
SetupStudentDirectoryProgram = "/usr/local/share/apps/makeStudentPersonalDirectory"
SchoolParams = localFunctions.school_params()
Country = SchoolParams["Country"]
SchoolType = SchoolParams["SchoolType"]
ClassYearName = SchoolParams["ClassYearName"]
StudentGroupName = SchoolParams["StudentGroupName"]
YearList = SchoolParams["DisplayYearList"]

class Ui_MainWindow(object):
    # ----------------------------------------------------------------------
    def __init__(self, the_integrator):
        """
        Setup constants and controller items
        """
        self.integrator = the_integrator

    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(583, 484)
        MainWindow.setStyleSheet(_fromUtf8(""))
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setMinimumSize(QtCore.QSize(583, 484))
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.Title = QtGui.QLabel(self.centralwidget)
        self.Title.setMinimumSize(QtCore.QSize(0, 60))
        self.Title.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        title_font = QtGui.QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title_font.setWeight(75)
        self.Title.setFont(title_font)
        self.Title.setFrameShape(QtGui.QFrame.NoFrame)
        self.Title.setObjectName(_fromUtf8("Title"))
        self.verticalLayout.addWidget(self.Title)
        self.YearFrame = QtGui.QFrame(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred,
                                       QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.YearFrame.sizePolicy().hasHeightForWidth())
        self.YearFrame.setSizePolicy(sizePolicy)
        self.YearFrame.setMinimumSize(QtCore.QSize(0, 60))
        self.YearFrame.setBaseSize(QtCore.QSize(400, 30))
        self.YearFrame.setAcceptDrops(False)
        self.YearFrame.setFrameShape(QtGui.QFrame.Box)
        self.YearFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.YearFrame.setLineWidth(2)
        self.YearFrame.setObjectName(_fromUtf8("YearFrame"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout(self.YearFrame)
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                       QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.YearLabel = QtGui.QLabel(self.YearFrame)
        labelfont = QtGui.QFont()
        labelfont.setPointSize(12)
        labelfont.setBold(True)
        labelfont.setWeight(75)
        self.YearLabel.setFont(labelfont)
        self.YearLabel.setObjectName(_fromUtf8("YearLabel"))
        self.horizontalLayout_3.addWidget(self.YearLabel)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem1)
        self.YearComboBox = QtGui.QComboBox(self.YearFrame)
        self.YearComboBox.setMinimumSize(QtCore.QSize(300, 35))
        boxfont = QtGui.QFont()
        boxfont.setPointSize(11)
        self.YearComboBox.setFont(boxfont)
        self.YearComboBox.setAutoFillBackground(False)
        self.YearComboBox.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.YearComboBox.setObjectName(_fromUtf8("YearComboBox"))
        self.horizontalLayout_3.addWidget(self.YearComboBox)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem2)
        self.verticalLayout.addWidget(self.YearFrame)
        spacerItem3 = QtGui.QSpacerItem(0, 15, QtGui.QSizePolicy.Minimum,
                                        QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem3)
        self.SectionFrame = QtGui.QFrame(self.centralwidget)
        self.SectionFrame.setMinimumSize(QtCore.QSize(400, 60))
        self.SectionFrame.setFrameShape(QtGui.QFrame.Box)
        self.SectionFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.SectionFrame.setLineWidth(2)
        self.SectionFrame.setObjectName(_fromUtf8("SectionFrame"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.SectionFrame)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem4 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem4)
        self.SectionLabel = QtGui.QLabel(self.SectionFrame)
        self.SectionLabel.setMinimumSize(QtCore.QSize(58, 0))
        self.SectionLabel.setFont(labelfont)
        self.SectionLabel.setObjectName(_fromUtf8("SectionLabel"))
        self.horizontalLayout_2.addWidget(self.SectionLabel)
        spacerItem5 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem5)
        self.SectionComboBox = QtGui.QComboBox(self.SectionFrame)
        self.SectionComboBox.setMinimumSize(QtCore.QSize(300, 35))
        self.SectionComboBox.setFont(boxfont)
        self.SectionComboBox.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.SectionComboBox.setObjectName(_fromUtf8("SectionComboBox"))
        self.horizontalLayout_2.addWidget(self.SectionComboBox)
        spacerItem6 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem6)
        self.verticalLayout.addWidget(self.SectionFrame)
        spacerItem7 = QtGui.QSpacerItem(20, 15, QtGui.QSizePolicy.Minimum,
                                        QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem7)
        self.NameFrame = QtGui.QFrame(self.centralwidget)
        self.NameFrame.setMinimumSize(QtCore.QSize(0, 60))
        self.NameFrame.setFrameShape(QtGui.QFrame.Box)
        self.NameFrame.setFrameShadow(QtGui.QFrame.Raised)
        self.NameFrame.setLineWidth(2)
        self.NameFrame.setObjectName(_fromUtf8("NameFrame"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.NameFrame)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        spacerItem8 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem8)
        self.NameLabel = QtGui.QLabel(self.NameFrame)
        self.NameLabel.setFont(labelfont)
        self.NameLabel.setObjectName(_fromUtf8("NameLabel"))
        self.horizontalLayout.addWidget(self.NameLabel)
        spacerItem9 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                        QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem9)
        self.NameComboBox = QtGui.QComboBox(self.NameFrame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                       QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.NameComboBox.sizePolicy().hasHeightForWidth())
        self.NameComboBox.setSizePolicy(sizePolicy)
        self.NameComboBox.setMinimumSize(QtCore.QSize(300, 35))
        self.NameComboBox.setFont(boxfont)
        self.NameComboBox.setInsertPolicy(QtGui.QComboBox.NoInsert)
        self.NameComboBox.setSizeAdjustPolicy(
            QtGui.QComboBox.AdjustToContentsOnFirstShow)
        self.NameComboBox.setObjectName(_fromUtf8("NameComboBox"))
        self.horizontalLayout.addWidget(self.NameComboBox)
        spacerItem10 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Fixed,
                                         QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem10)
        self.verticalLayout.addWidget(self.NameFrame)
        spacerItem11 = QtGui.QSpacerItem(20, 15, QtGui.QSizePolicy.Minimum,
                                         QtGui.QSizePolicy.Fixed)
        self.verticalLayout.addItem(spacerItem11)
        self.frame = QtGui.QFrame(self.centralwidget)
        self.frame.setMinimumSize(QtCore.QSize(0, 100))
        self.frame.setFrameShape(QtGui.QFrame.NoFrame)
        self.frame.setFrameShadow(QtGui.QFrame.Raised)
        self.frame.setObjectName(_fromUtf8("frame"))
        self.horizontalLayout_4 = QtGui.QHBoxLayout(self.frame)
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        spacerItem12 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                         QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem12)
        self.ButtonBox = QtGui.QFrame(self.frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                       QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.ButtonBox.sizePolicy().hasHeightForWidth())
        self.ButtonBox.setSizePolicy(sizePolicy)
        self.ButtonBox.setMinimumSize(QtCore.QSize(200, 100))
        self.ButtonBox.setBaseSize(QtCore.QSize(200, 60))
        self.ButtonBox.setFrameShape(QtGui.QFrame.Box)
        self.ButtonBox.setFrameShadow(QtGui.QFrame.Raised)
        self.ButtonBox.setLineWidth(2)
        self.ButtonBox.setObjectName(_fromUtf8("ButtonBox"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.ButtonBox)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.SignInButton = QtGui.QPushButton(self.ButtonBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                       QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.SignInButton.sizePolicy().hasHeightForWidth())
        self.SignInButton.setSizePolicy(sizePolicy)
        self.SignInButton.setMinimumSize(QtCore.QSize(130, 40))
        self.SignInButton.setBaseSize(QtCore.QSize(100, 40))
        buttonfont = QtGui.QFont()
        buttonfont.setPointSize(14)
        buttonfont.setBold(True)
        buttonfont.setWeight(75)
        self.SignInButton.setFont(buttonfont)
        self.SignInButton.setObjectName(_fromUtf8("SignInButton"))
        self.verticalLayout_2.addWidget(self.SignInButton)
        self.GuestButton = QtGui.QPushButton(self.ButtonBox)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Minimum,
                                       QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.GuestButton.sizePolicy().hasHeightForWidth())
        self.GuestButton.setSizePolicy(sizePolicy)
        self.GuestButton.setMinimumSize(QtCore.QSize(130, 40))
        self.GuestButton.setFont(buttonfont)
        self.GuestButton.setObjectName(_fromUtf8("GuestButton"))
        self.verticalLayout_2.addWidget(self.GuestButton)
        self.horizontalLayout_4.addWidget(self.ButtonBox)
        spacerItem13 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding,
                                         QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem13)
        self.verticalLayout.addWidget(self.frame)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QObject.connect(self.NameComboBox,
                               QtCore.SIGNAL(_fromUtf8("activated(int)")),
                               MainWindow.NameSelected)
        QtCore.QObject.connect(self.SectionComboBox,
                               QtCore.SIGNAL(_fromUtf8("activated(int)")),
                               MainWindow.SectionSelected)
        QtCore.QObject.connect(self.YearComboBox,
                               QtCore.SIGNAL(_fromUtf8("activated(int)")),
                               MainWindow.YearSelected)
        QtCore.QObject.connect(self.GuestButton,
                               QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.GuestButtonClicked)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        self.integrator.add_year_box(self.YearComboBox)
        self.integrator.add_section_box(self.SectionComboBox)
        self.integrator.add_name_box(self.NameComboBox)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(
            QtGui.QApplication.translate("MainWindow", "Student Sign In", None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.Title.setText(
            QtGui.QApplication.translate("MainWindow", "Sign In With Your Name",
                                         None, QtGui.QApplication.UnicodeUTF8))
        self.YearLabel.setText(
            QtGui.QApplication.translate("MainWindow", ClassYearName, None,
                                         QtGui.QApplication.UnicodeUTF8))
        help_text = "Choose your " + ClassYearName
        self.YearComboBox.setToolTip(
            QtGui.QApplication.translate("MainWindow", help_text, None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.SectionLabel.setText(
            QtGui.QApplication.translate("MainWindow", StudentGroupName, None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.NameLabel.setText(
            QtGui.QApplication.translate("MainWindow", "Student Name", None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.SignInButton.setToolTip(QtGui.QApplication.translate("MainWindow",
                                                                  "Sign in with your name. Your files will be saved in your personal space.",
                                                                  None,
                                                                  QtGui.QApplication.UnicodeUTF8))
        self.SignInButton.setText(
            QtGui.QApplication.translate("MainWindow", "Sign In", None,
                                         QtGui.QApplication.UnicodeUTF8))
        self.GuestButton.setToolTip(QtGui.QApplication.translate("MainWindow",
                                                                 "Sign in as guest user. You will have no special place to save files.",
                                                                 None,
                                                                 QtGui.QApplication.UnicodeUTF8))
        self.GuestButton.setText(
            QtGui.QApplication.translate("MainWindow", "Guest User", None,
                                         QtGui.QApplication.UnicodeUTF8))

    # ----------------------------------------------------------------------
    def deactivateSignInButton(self, MainWindow):
        """
        Make sign in button inactive. Change color and disconnect signal.
        """
        self.SignInButton.setStyleSheet("color:hsv(0,0,160)")
        QtCore.QObject.connect(self.SignInButton, QtCore.SIGNAL("clicked()"),
                               MainWindow.InactiveSignInButtonClicked)

    # ----------------------------------------------------------------------
    def activateSignInButton(self, MainWindow):
        """
        Prepare the sign in button for use. Change color, turn on, and set focus
        """
        self.SignInButton.setStyleSheet("color:hsv(0,0,0)")
        self.SignInButton.setDefault(True)
        QtCore.QObject.connect(self.SignInButton,
                               QtCore.SIGNAL(_fromUtf8("clicked()")),
                               MainWindow.ActiveSignInButtonClicked)


########################################################################
class EntryBox:
    """
    Extend the QComboBox to perform specific functions with internal state
    and data.
    """

    # ----------------------------------------------------------------------
    def __init__(self, combo_box):
        """Constructor"""

        self.status = "NotReady"
        self.combo_box = combo_box
        self.combo_box.clear()

    # ----------------------------------------------------------------------
    def set_choice_list(self, choice_list):
        """
        Remove all items in the combo box a instert all in list
        """
        self.combo_box.clear()
        self.combo_box.addItems(choice_list)

    # ----------------------------------------------------------------------
    def set_not_ready(self):
        """
        Set teh combo box to not usable. Clear all contents, 
        change status, and make uneditable.
        """
        self.status = "NotReady"
        self.combo_box.setCurrentIndex(-1)
        self.combo_box.clear()
        self.combo_box.setEditable(False)

    # ----------------------------------------------------------------------
    def set_active(self, choice_list):
        """
        Clear current selection, change color, and move cursor to
        the combo box to the combo_box
        """
        self.status = "Active"
        self.set_choice_list(choice_list)
        self.combo_box.setEditable(True)
        self.combo_box.setCurrentIndex(-1)

    # ----------------------------------------------------------------------
    def set_completed(self):
        """
        Clear current selection, change color, and move cursor to
        the combo box to the combo_box
        """
        self.status = "Completed"

    # ----------------------------------------------------------------------
    def selected_value(self):
        """
        Return the value from the combo box.
        """
        return str(self.combo_box.currentText())


########################################################################
class StudentAccountDatabase:
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, base_dirname):
        """Constructor"""
        global YearList
        self.base_dirname = base_dirname
        self.database = {}
        self.student_map = {}
        self.YearList = YearList
        for year in self.YearList:
            self.database[year] = {}

    # ----------------------------------------------------------------------
    def read_data_file(self, student_filename):
        """
        Build the database from a csv file that contains all of the information
        about the students. The file should begin with column names and include the
        columns "Grade" or "Form Level"(see above), "Section" or "Class Teacher", 
        "Student first name", "Student middle name", "Student last name".
        Column order is unimportant
        and any other columns will be ignored. Duplicate entries are allowed but 
        will only create a single entry.
        """
        try:
            f = open(student_filename, "r", encoding='latin1')
            reader = csv.DictReader(f)
            i = 0
            for entry in reader:
                try:
                    year_name = self.__cleanup_year(entry[ClassYearName])
                    section_name = self.__cleanup_section(entry[StudentGroupName])

                    student_name = "%s, %s %s" \
                                   % (self.__cleanup_to_display(entry["Last Name"]),
                                      self.__cleanup_to_display(
                                          entry["First Name"]),
                                      self.__cleanup_to_display(
                                          entry["Middle Name"]))
                    directory_name = "%s-%s%s" % (
                    self.__cleanup_string_for_directory_name(entry["Last Name"]),
                    self.__cleanup_string_for_directory_name(entry["First Name"]),
                    self.__cleanup_string_for_directory_name(entry["Middle Name"]))
                    student_key = self.__create_student_key(year_name,
                                                            section_name,
                                                            student_name)
                    try:
                        year_info = self.database[year_name]
                    except KeyError:
                        continue
                    try:
                        section_info = year_info[section_name]
                    except KeyError:
                        section_info = []
                        year_info[section_name] = section_info
                    # if not (self.student_map.has_key(student_key)):
                    if not student_key in self.student_map:
                        bisect.insort(section_info, student_name)
                        self.student_map[student_key] = directory_name
                        i += 1
                except KeyError as e:
                    continue
            if i == 0:
                #no names could be read
                return False
            return True
        except IOError:
            return False

    # ----------------------------------------------------------------------
    def get_section_names(self, class_year):
        """
        Get a list of sections for the class year.
        """
        try:
            return localFunctions.sort_nicely(self.database[class_year].keys(),
                                               return_copy=True)
        except (KeyError, IndexError):
            return []

    # ----------------------------------------------------------------------
    def get_student_names(self, class_year, section):
        """
        Get a list of the tuples of information for all
        students in the section.
        """
        try:
            return self.database[class_year][section]
        except (KeyError, IndexError):
            return []

    # ----------------------------------------------------------------------
    def get_dirname(self, class_year, section, student_name):
        """
        Return the full directory path. 
        """
        year_dirname = self.__cleanup_string_for_directory_name(class_year)
        section_dirname = self.__cleanup_string_for_directory_name(section)
        try:
            student_dirname = self.student_map[self.__create_student_key(
                class_year, section, student_name)]
        except KeyError:
            return ""
        return os.path.join(self.base_dirname, year_dirname, section_dirname,
                            student_dirname)

    # ----------------------------------------------------------------------
    @staticmethod
    def __cleanup_string_for_directory_name(text):
        """
        Replace or remove improper characters to create text that can be used
        in a directory name
        """
        return localFunctions.cleanup_string(text,title_case=False,
                              further_remove_characters=".,",
                              join_character="", replace_enya=True)

    # ----------------------------------------------------------------------
    @staticmethod
    def __cleanup_to_display(text):
        """
        Replace or remove problem characters for display
        """
        return localFunctions.cleanup_string(text,title_case=False, further_remove_characters="",
                              join_character=" ", replace_enya=False)

    # ----------------------------------------------------------------------
    @staticmethod
    def __cleanup_year(year_text):
        """
        look for year in whatever string given and change the text
        to the correct one
        """
        global Country, SchoolType
        if Country == "Tanzania" or SchoolType == "College":
            return StudentAccountDatabase.__cleanup_to_display(year_text)
        else:
            year = "7"
            find_list = re.findall(r'(\d+)', year_text)
            if len(find_list):
                year = find_list[0]
            return "Grade " + str(year)

    # ----------------------------------------------------------------------
    @staticmethod
    def __cleanup_section(section_text):
        """
        Cleanup section name to common format
        """
        if section_text:
            return StudentAccountDatabase.__cleanup_to_display(section_text)
        else:
            return "Not Set"

    # ----------------------------------------------------------------------
    @staticmethod
    def __create_student_key(year, section, student_name):
        """
        Combine year, section, and student name into a single string that
        can be used as a dictionary key.
        """
        return "%s-%s-%s" % (year, section, student_name)


########################################################################
class ActionsIntegrator:
    """
    This is the controller for all program actions. It contains the database 
    connects the data object for each combo box to the display,
    """

    # ----------------------------------------------------------------------
    def __init__(self, base_directory):
        """Constructor"""
        self.year_box = None
        self.section_box = None
        self.name_box = None
        self.database = StudentAccountDatabase(base_directory)

    # ----------------------------------------------------------------------
    def LoadDatabase(self, data_file, main_window):
        """
        """
        created = self.database.read_data_file(data_file)
        if not created:
            message = """The list of students could not be read correctly.
You will be signed in as a guest.
You will not be setup to use your personal area.
Please tell your teacher about the problem."""
            QtGui.QMessageBox.warning(main_window, "Automatic Sign In As Guest",
                                      message)
            setup_session(GuestDirectory, self)
            sys.exit()

    # ----------------------------------------------------------------------
    def add_year_box(self, combo_box):
        """
        """
        global YearList
        self.year_box = EntryBox(combo_box)
        self.year_box.set_active(YearList)

    # ----------------------------------------------------------------------
    def add_section_box(self, combo_box):
        """
        """
        self.section_box = EntryBox(combo_box)
        self.section_box.set_not_ready()

        # ----------------------------------------------------------------------

    def add_name_box(self, combo_box):
        """
        """
        self.name_box = EntryBox(combo_box)
        self.name_box.set_not_ready()

        # ----------------------------------------------------------------------

    def year_selected(self):
        """
        """
        self.year_box.set_completed()
        section_list = self.database.get_section_names(
            self.year_box.selected_value())
        self.section_box.set_active(section_list)
        self.name_box.set_not_ready()

        # ----------------------------------------------------------------------

    def section_selected(self):
        """
        Acion to be performed when a vlue is selected in the section box.
        This will mark the box complete, get the list of student names
        in the section from the database, and load them into the name
        combo box.
        """
        self.section_box.set_completed()
        name_list = self.database.get_student_names(
            self.year_box.selected_value(),
            self.section_box.selected_value())
        self.name_box.set_active(name_list)

    # ----------------------------------------------------------------------
    def name_selected(self):
        """
        Action to be performed when the user selects a value in the 
        name box. 
        """
        self.name_box.set_completed()

    # ----------------------------------------------------------------------
    def form_complete(self):
        """
        Confirm that a student account has been selected.
        """
        return ((self.year_box.selected_value() != "") and
                (self.section_box.selected_value() != "") and
                (self.name_box.selected_value() != ""))

    # ----------------------------------------------------------------------
    def student_directory(self):
        """
        Return the student directory to be used for the session.
        """
        if self.form_complete():
            return self.database.get_dirname(self.year_box.selected_value(),
                                             self.section_box.selected_value(),
                                             self.name_box.selected_value())
        else:
            return ""


########################################################################
class StudentSigninWindow(QtGui.QMainWindow):
    def __init__(self, the_integrator, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.integrator = the_integrator
        self.ui = Ui_MainWindow(the_integrator)
        self.ui.setupUi(self)
        self.ui.deactivateSignInButton(self)

    # ----------------------------------------------------------------------
    def YearSelected(self):
        """
        """
        self.integrator.year_selected()
        self.ui.deactivateSignInButton(self)

    # ----------------------------------------------------------------------
    def SectionSelected(self):
        """
        """
        self.integrator.section_selected()
        self.ui.deactivateSignInButton(self)

    # ----------------------------------------------------------------------
    def NameSelected(self):
        """
        """
        self.integrator.name_selected()
        self.ui.activateSignInButton(self)

    # ----------------------------------------------------------------------
    @staticmethod
    def InactiveSignInButtonClicked():
        """
        Do nothing with the click. This makes the button inactive.
        """
        pass

    # ----------------------------------------------------------------------
    def ActiveSignInButtonClicked(self):
        """
        Confirm that a student account has been selected, then setup
        the session with the students directory and close the window.
        """
        if self.integrator.form_complete():
            setup_session(self.integrator.student_directory(), self)

    # ----------------------------------------------------------------------
    def GuestButtonClicked(self):
        """
        Popup "are you sure?" query window to confirm, if OKed then
        set the session with a common guest directory and close window
        """
        global GuestDirectory
        message = """If you have an sign-in name, please use it.
Guests do not have their own folders.
Do you want to be a guest?"""
        # buttons = QtGui.QMessageBox.Cancel | QtGui.QMessageBox.Ok
        reply = QtGui.QMessageBox.question(self,
                                           "Guest Sign In OK?", message,
                                           QtGui.QMessageBox.Ok,
                                           QtGui.QMessageBox.Cancel)
        if reply == QtGui.QMessageBox.Ok:
            setup_session(GuestDirectory, self)

# # ----------------------------------------------------------------------
# def valid_directory(directory_name):
#     """
#     Assure that any directory to be used as a student directory is in the /client_home_students
#     top level directory and that the directory name has been correctly constructed.
#     :param directory_name:
#     :return:
#     """
#     real_name = os.path.realpath(directory_name)
#     name_parts = real_name.split(os.sep)
#     valid = (name_parts[0] == "" and name_parts[1] == "client_home_students"
#             and name_parts[2].startswith("Form") and name_parts[4].find("-") != -1)
#     return valid

def split_directory_name(directory_name):
    try:
        real_name = os.path.realpath(directory_name)
        all_parts = real_name.split(os.sep)
        all_parts.pop(0)
        return all_parts
    except (IndexError, OSError):
        return [""]

def valid_directory(directory_name, throw_exception=True, full_name_check=True,
                         must_exist=False):
    """
    Assure that any directory to be used as a student directory is in the /client_home_students
    top level directory and that the directory name has been correctly constructed.
    :param full_name_check:
    :param throw_exception:
    :param directory_name:
    :param must_exist:
    :return:
    """
    name_parts = split_directory_name(directory_name)
    try:
        valid = (name_parts[0] == "client_home_students"
                 and name_parts[1].startswith("Form") and name_parts[3].find("-") != -1)
    except (IndexError, OSError):
        valid = False
    return valid

# ----------------------------------------------------------------------
def setup_student_directory(student_directory):
    """
    Create the directory student_directory and populate it with the initial
    contents. If the student directory is the guest directory do not create
    a unique directory rather make all file in the guest directory world read
    and write so that they can be used by any student user.
    """
    global SetupStudentDirectoryProgram, GuestDirectory
    if student_directory == GuestDirectory:
        try:
            subprocess.check_call((SetupStudentDirectoryProgram,
                                   '--set_open_permissions', GuestDirectory))
            return True
        except subprocess.CalledProcessError:
            # ensure that there will be no loops of retries for guest
            return True
    elif not valid_directory(student_directory):
        return False
    else:
        try:
            # this is a unique student so set up directory appropriately
            subprocess.check_call((SetupStudentDirectoryProgram, "--year_name",
                                   ClassYearName, "--grouping_name",
                                   StudentGroupName,
                                   student_directory))
            return True
        except subprocess.CalledProcessError:
            return False

# ----------------------------------------------------------------------
def create_home_directory_symlinks(home_directory, link_name,
                                   student_directory, personal_link_name):
    """
    Create symlinks at both the top student level and at the desktop level
    """
    # for dirname in (home_directory, \
    try:
        local_name = os.path.join(home_directory, link_name)
        desktop_name = os.path.join(home_directory, "Desktop", link_name)
        if os.path.exists(local_name):
            os.remove(local_name)
        os.symlink(os.path.join(student_directory, personal_link_name),
                   local_name)
        if os.path.exists(desktop_name):
            os.remove(desktop_name)
        os.symlink(local_name, desktop_name)
    except OSError:
        pass


# ----------------------------------------------------------------------
def setup_session(student_directory, main_window):
    """
    """
    global GuestDirectory
    if not setup_student_directory(student_directory):
        # If the student directory was not the guest direcotry (i.e, not
        # registered as guest and the directory setup failed, change to guest user
        # and then set that up.
        message = "I could not create your personal area.\n" + \
                  "You will be signed in as a guest."
        QtGui.QMessageBox.warning(main_window,
                                  "Automatic Sign In As Guest", message)
        student_directory = GuestDirectory
        setup_student_directory(student_directory)
    home_directory = os.path.expanduser("~")
    for name in ("Documents", "Projects"):
        create_home_directory_symlinks(home_directory, name,
                                       student_directory, name)
    localFunctions.command_run_successful("chmod s-w Desktop")
    # symlink the firefox bookmarks -- future  enhancement
    # do not do this for guests
    #once the setup is complete, shut the window
    sys.exit(0)


if __name__ == "__main__":
    localFunctions.initialize_app(name=PROGRAM_NAME,version=VERSION,
                                  description="Graphic program to setup student "
                                              "work area by student name upon login")
    app = QtGui.QApplication(sys.argv)
    integrator = ActionsIntegrator(BaseDirectory)
    signinWindow = StudentSigninWindow(integrator)
    integrator.LoadDatabase(StudentDataFile, signinWindow)
    signinWindow.show()
    sys.exit(app.exec_())
