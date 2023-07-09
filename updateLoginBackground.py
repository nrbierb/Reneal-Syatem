#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Create a new status image, overlay on login background image, and update lightdm login manager.
"""

import argparse
import enum
import os.path
import re
import subprocess
import time

import jinja2

import localFunctions
import localFunctionsPy3
import sysChkIO
import systemCheck

JINJA_HTML_TEMPLATE_FILE = 'loginInfoTemplate.html'
GENERATED_BACKGROUND_IMAGE = "/tmp/info_background.jpg"
FINAL_BACKGROUND_IMAGE = "/etc/lightdm/lightdm.conf.d/info_background.jpg"
SERVER_LOGIN_BACKGROUND = "ServerLoginBackground.jpg"
SERVER_LOGIN_DISK2_BACKGROUND = "ServerLoginBackgroundDrive2.jpg"
SUPPORT_FILES_PATH = "/usr/local/share/share"
LOGFILE = "/var/log/systemCheck/loginUpdate.log"
PROGRAM_NAME = "updateLoginBackground"
VERSION = 0.8


class WindowConstants:
    def __init__(self, template_css_status, status_icon_filename, alt_icon_text,
                 status_header_text, action_comment_start, action_comment_stop):
        self.template_css_status = template_css_status
        self.status_icon_file = os.path.join(SUPPORT_FILES_PATH, status_icon_filename)
        self.alt_icon_text = alt_icon_text
        self.status_header_text = status_header_text
        self.action_comment_start = action_comment_start
        self.action_comment_stop = action_comment_stop


class ServerStatus(enum.Enum):
    no_problems = WindowConstants("status_no_error", "green-check-mark-icon.svg", "check_mark_icon",
                                  "Everything Good", "<!--", "-->")
    problems_minor = WindowConstants("status_info", "dialog-information.png", "information icon",
                                     "Minor Problems", "<!--", "-->")
    problems_action = WindowConstants("status_error_action", "dialog-warning.png", "warning icon",
                                      "Problems Require Action Now", "", "")
    serious_problems = WindowConstants("status_serious_error", "dialog-error.png", "error_icon",
                                       "READ! Serious Problems Require Action Immediately!", "", "")
    system_startup = WindowConstants("status_startup", "dialog-information.png", "information_icon",
                                     "Starting Server", "<!--", "-->")


class BackgroundGenerator:
    def __init__(self):
        # setup for default standard screen
        global SERVER_LOGIN_BACKGROUND, SUPPORT_FILES_PATH, JINJA_HTML_TEMPLATE_FILE
        self.background_image_filename = os.path.join(SUPPORT_FILES_PATH,
                                                      SERVER_LOGIN_BACKGROUND)
        self.screen_width = 1280
        self.screen_height = 1024
        self.info_window_width = 550
        self.info_window_height = 430
        self.jinja_template_file = os.path.join(SUPPORT_FILES_PATH, JINJA_HTML_TEMPLATE_FILE)
        self.jinja_template = None
        self.rendered_html_file = '/tmp/login_info.html'
        self.generated_info_image = '/tmp/info_image.png'
        self.final_info_image = '/tmp/final_info_image.png'
        self.unscaled_background_image = "/tmp/unscaled_background_image.jpg"

    def create_html_file(self, status_enum, generated_info_text, generated_action_text):
        write_log(generated_info_text)
        env = jinja2.Environment(loader=jinja2.PackageLoader('updateLoginBackground', ""))
        self.jinja_template = env.get_template(JINJA_HTML_TEMPLATE_FILE, SUPPORT_FILES_PATH)
        parsed_template_text = self.jinja_template.render(
            status=status_enum.value.template_css_status,
            icon_file=status_enum.value.status_icon_file,
            alt_image=status_enum.value.alt_icon_text,
            update_time=time.strftime("%I:%M %p", time.localtime()),
            header_text=status_enum.value.status_header_text,
            info_text=generated_info_text,
            action_text=generated_action_text,
            action_comment_start=status_enum.value.action_comment_start,
            action_comment_stop=status_enum.value.action_comment_stop)
        with open(self.rendered_html_file, "w") as f:
            f.write(parsed_template_text)

    def get_screen_dimensions(self):
        width = 0
        height = 0
        try:
            width_str, height_str = localFunctionsPy3.get_conf_file_value("/etc/systemCheck.conf",
                                                                          "System",
                                                                          "screen_dimensions").split("x")
            width = int(width_str)
            height = int(height_str)
        except (ValueError, TypeError):
            pass
        if width > 1000 and height > 600:
            self.screen_width = width
            self.screen_height = height
        return self.screen_width, self.screen_height

    def select_background(self, running_on_backup=False):
        global SERVER_LOGIN_DISK2_BACKGROUND
        if running_on_backup:
            self.background_image_filename = os.path.join(SUPPORT_FILES_PATH,
                                                          SERVER_LOGIN_DISK2_BACKGROUND)
        return self.background_image_filename

    def create_background_file(self):
        global GENERATED_BACKGROUND_IMAGE
        try:
            self.get_screen_dimensions()
            command = "xvfb-run /usr/bin/wkhtmltoimage -q --width %d %s %s" \
                      % (self.info_window_width,  self.rendered_html_file,
                         self.generated_info_image)
            localFunctions.run_command(command, reraise_error=True)
            command = "/usr/bin/convert %s -bordercolor lightblue -frame 12x12+4+6 %s" % (
                self.generated_info_image, self.final_info_image)
            localFunctions.run_command(command, reraise_error=True)
            command = "/usr/bin/convert %s %s -gravity northeast -composite %s" \
                      % (self.background_image_filename, self.final_info_image,
                         self.unscaled_background_image)
            localFunctions.run_command(command, reraise_error=True)
            command = '/usr/bin/convert -resize "%dx%d!" %s %s' % (
                self.screen_width, self.screen_height,
                self.unscaled_background_image, GENERATED_BACKGROUND_IMAGE)
            localFunctions.run_command(command, reraise_error=True)
            return True
        except subprocess.CalledProcessError:
            return False


class StatusChecker:
    def __init__(self):
        self.display_status_text = "No Problems Found"
        self.raw_status_text = ""
        self.display_action_text = "No actions are required."
        self.raw_action_text = ""
        self.report_info = {}
        self.server_status = ServerStatus.no_problems
        self.systemCheckConfiguration = None
        self.systemCheckReporter = None
        self.systemChecker = None
        self.textReporter = None

    def setup_SystemCheckConfiguration(self):
        self.systemCheckConfiguration = systemCheck.Configuration(read_command_line=False)
        self.systemCheckConfiguration.params_dict["check_networks"] = False
        self.systemCheckConfiguration.params_dict["problems_only"] = False
        self.systemCheckConfiguration.params_dict["quiet"] = True

    def setup_systemCheck_objects(self):
        self.setup_SystemCheckConfiguration()
        self.systemCheckReporter = sysChkIO.Reporter(self.systemCheckConfiguration,
                                                     gui_connector=None,
                                                     report_progress_messages=False,
                                                     output_filename="",
                                                     username="", line_width=400, verbose=False,
                                                     use_stringbuffer=True)
        self.textReporter = self.systemCheckReporter.txt_reporter
        self.systemChecker = systemCheck.SystemChecker(self.systemCheckReporter,
                                                       self.systemCheckConfiguration)

    def perform_check(self):
        """
        perform the system check and generate the raw results.
        :return:
        """
        self.systemChecker.perform_tests()
        self.systemChecker.analyze_results()
        self.report_info = self.systemCheckReporter.get_report_info()

    def generate_summary(self):
        if self.report_info["Reboot Required"]:
            self.display_action_text = \
                "Request all users to log off and shut down their computers. Then reboot the server."
        elif self.report_info["Further Action Required"]:
            self.display_action_text = "Login as sysadmin. Run systemCheck then do the actions it directs.</br>"
            # for action in user_actions:
            #    self.display_action_text += action + "</br>"
        if self.report_info["Problems Found"] == 0:
            self.display_status_text += "<h3></br>No problems found.</h3></br>"
        else:
            self.display_status_text += "<h3></br>-------------------------------</br>%s</h3></br>" \
                                        % self.textReporter.generate_problems_count_string(
                self.report_info["Problems Found"],
                self.report_info["Problems Fixed"],
                self.report_info["Number Further Actions"])

    def determine_status(self):
        if self.report_info["Serious Problem"]:
            self.server_status = ServerStatus.serious_problems
        elif self.report_info["Further Action Required"]:
            self.server_status = ServerStatus.problems_action
        elif self.report_info["Problems Found"]:
            self.server_status = ServerStatus.problems_minor
        else:
            self.server_status = ServerStatus.no_problems

    def process_results(self):
        self.raw_status_text = self.report_info["Report Stringbuffer"].getvalue()
        self.display_status_text = self.raw_status_text.replace("\n", "</br>")
        self.generate_summary()
        self.determine_status()

    def generate_status_report(self):
        self.setup_systemCheck_objects()
        self.perform_check()
        self.process_results()
        return self.systemCheckReporter.get_report_info()

    def get_status_text(self):
        return self.display_status_text

    def get_action_text(self):
        return self.display_action_text

    def get_status(self):
        return self.server_status


def get_using_backup_disk():
    try:
        with open("/etc/fstab") as f:
            fstab_text = f.read()
            using_backup_disk = re.search(r'--Secondary Server Disk Active--', fstab_text)
    except OSError:
        using_backup_disk = False
    return using_backup_disk


def write_log(generated_text):
    with open(LOGFILE, "a") as f:
        header = "\n==========  %s  ==========" % time.strftime("%I:%M %p", time.localtime())
        f.write(header)
        print_text = generated_text.replace("<h3></br>-------------------------------</br>",
                                            "--------------------------------------\n")
        print_text = print_text.replace("</br>", '\n')
        print_text = print_text.replace("<h3>", "")
        print_text = print_text.replace("</h3>", "")
        print_text = print_text.replace("-- ", "")
        print_text += '\n'
        f.write(print_text)


def restart_lightdm_when_no_user():
    info = str(localFunctions.run_command("ps -ef",
                                          False, False))
    no_user_logged_in = (info.find("xfwm4") == -1)
    if no_user_logged_in:
        localFunctions.command_run_successful("systemctl restart lightdm")


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, VERSION,
                                           """Use a version of systemCheck to create a status message and display on login screen.""",
                                           perform_parse=False)
    parser.add_argument("--initial-screen", dest="initial_screen",
                        action='store_true',
                        help="Display special static screen that does not run the system checks. "
                             "Used at boot.")
    initial_screen = False
    try:
        args = parser.parse_args()
        initial_screen = args.initial_screen
    except argparse.ArgumentError as err:
        print("Error in the command line arguments: %s" % err)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    #Always remove the files in /var/crash to pervent error messages in sysadmin window
    localFunctions.command_run_successful("rm /var/crash/*")
    backgroundGenerator = BackgroundGenerator()
    status = ServerStatus.system_startup
    if initial_screen:
        backgroundGenerator.select_background(get_using_backup_disk())
        backgroundGenerator.create_html_file(status,
                                             "\nInitial Startup. \nStatus check will wait one to two minutes for server to complete startup.",
                                             "No actions are required.\n")
    else:
        statusChecker = StatusChecker()
        report_info = statusChecker.generate_status_report()
        if report_info["Problems Fixed"]:
            # write to log file, then rerun to get updated file for the login screen
            write_log(statusChecker.get_status_text())
            statusChecker = StatusChecker()
            problems_fixed = statusChecker.generate_status_report()
        backgroundGenerator.select_background(get_using_backup_disk())
        backgroundGenerator.create_html_file(statusChecker.get_status(),
                                             statusChecker.get_status_text(),
                                             statusChecker.get_action_text())
    if backgroundGenerator.create_background_file():
        os.rename(GENERATED_BACKGROUND_IMAGE, FINAL_BACKGROUND_IMAGE)
        restart_lightdm_when_no_user()
