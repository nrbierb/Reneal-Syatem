#!/usr/bin/python3
# -*- coding: utf-8 -*-

import re
import subprocess
import syslog
import localFunctions
from PyQt4.QtGui import QApplication

PROGRAM_NAME = "scaleScreen"
PROGRAM_VERSION = "0.7"
DEFAULT_LOW_RES = {"x": 1024, "y": 768}


class DisplaySetter:
    def __init__(self):
        # guess values
        self.name = "default"
        self.native_x_res = 1366
        self.native_y_res = 768
        self.current_x_res = self.native_x_res
        self.current_y_res = self.native_y_res
        self.normal_x_res = self.native_x_res
        self.normal_y_res = self.native_y_res
        self.scale_factor = 1.0

    def get_display_info(self):
        app = QApplication([])
        screen_size = app.desktop().screenGeometry()
        self.current_x_res, self.current_y_res = screen_size.width(), screen_size.height()
        try:
            full_info = localFunctions.run_command('xrandr -q 2>/dev/null', reraise_error=True,
                                                   result_as_list=False, merge_stderr=False)
            # line 1 has current status info
            match_obj = re.search(r'Screen 0:.*maximum\s(\d+)\D+(\d+)',
                                  full_info, re.MULTILINE)
            if match_obj:
                max_x, max_y = match_obj.groups()
                self.native_x_res = int(max_x)
                self.native_y_res = int(max_y)
            match_obj = re.search(r'^(\S+) connected', full_info, re.M)
            if match_obj:
                self.name = match_obj.group(1)
            match_obj = re.search(r'\s+(\d+)x(\d+).+\*',
                                  full_info, re.MULTILINE)
            if match_obj:
                normal_x, normal_y= match_obj.groups()
                self.normal_x_res = int(normal_x)
                self.normal_y_res = int(normal_y)
        except (subprocess.SubprocessError, IndexError):
            pass
        return self.current_x_res, self.current_y_res

    def simple_scale_display(self, target_x_res, target_y_res):
        """
        Scale the display to use the target x and y resolutions
        :param target_x_res:
        :param target_y_res:
        :return:
        """
        if target_x_res < 800 or target_y_res < 600 or \
                target_x_res > self.native_x_res * 1.2 or \
                target_y_res > self.native_y_res * 1.2:
            # ignore unreasonable settings
            return
        try:
            command = "xrandr --output %s --mode %dx%d" \
                      % (self.name, target_x_res, target_y_res)
            localFunctions.run_command(command, reraise_error=True)
            syslog.syslog("Set display %s to %dx%d" % (self.name,
                                                    target_x_res, target_y_res))
        except subprocess.SubprocessError:
            pass
            return self.current_x_res, self.current_y_res

    def compute_scale_factor(self, target_x_res, target_y_res):
        x_scale_factor = float(target_x_res) / float(self.normal_x_res)
        y_scale_factor = float(target_y_res) / float(self.normal_y_res)
        if x_scale_factor < y_scale_factor:
            self.scale_factor = x_scale_factor
        else:
            self.scale_factor = y_scale_factor

    def scale_display(self, target_x_res, target_y_res, no_scale=False):
        """
        Scale the display to use the target x and y resolutions
        This will use the xrander scale command. If tha command fails,
        then it will scale the screen directly
        :param target_x_res:
        :param target_y_res:
        :param no_scale:
        :return:
        """
        if target_x_res < 800 or target_y_res < 600 or \
                target_x_res > self.native_x_res * 1.2 or \
                target_y_res > self.native_y_res * 1.2:
            # ignore unreasonable settings
            return
        try:
            if no_scale:
                self.scale_factor = 1
            else:
                self.compute_scale_factor(target_x_res, target_y_res)
            command = "xrandr --output %s --scale %fx%f" \
                      % (self.name, self.scale_factor, self.scale_factor)
            localFunctions.run_command(command, reraise_error=True)
            syslog.syslog("Scaled display %s by %0.2f" % (self.name,
                                                          self.scale_factor))
        except subprocess.SubprocessError:
            try:
                command = "xrandr --output %s --mode %dx%d" \
                          % (self.name, target_x_res, target_y_res)
                localFunctions.run_command(command, reraise_error=True)
                syslog.syslog("Set display %s to %dx%d after scaling did not work." % (self.name,
                                                           target_x_res, target_y_res))
            except subprocess.SubprocessError:
                pass
                return self.current_x_res, self.current_y_res

    def reset_display_to_native(self):
        return self.scale_display(self.native_x_res, self.native_y_res, no_scale=True)

    def reset_display_to_standard(self):
        """
        Reset the display to the size set by user. If the normal display size
        has been changed by this program setting the screen size directly, return to
        maximum screen resolution.
        :return:
        """
        global DEFAULT_LOW_RES
        if self.normal_x_res == DEFAULT_LOW_RES["x"]:
            return self.reset_display_to_native()
        else:
            return self.scale_display(self.normal_x_res, self.normal_y_res, no_scale=True)

    def generate_scale_to_me_command(self):
        command = "/usr/local/bin/scaleDisplay -s %dx%d" \
                  % (self.current_x_res, self.current_y_res)
        return command

    def is_scaled(self):
        """
        return curent and native screen resolutions
        :return:
        """
        global DEFAULT_LOW_RES
        return "Yes" if self.current_x_res < self.normal_x_res or \
                        self.current_y_res < self.normal_y_res or \
                        self.current_x_res == DEFAULT_LOW_RES["x"]\
            else "No"

    def toggle_display_size(self):
        """
        Change screen resolution to the alternate.
        :return:
        """
        if self.is_scaled() == "Yes":
            return self.reset_display_to_standard()
        else:
            self.scale_display(DEFAULT_LOW_RES["x"], DEFAULT_LOW_RES["y"])
            return DEFAULT_LOW_RES["x"], DEFAULT_LOW_RES["y"]


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                           "Scale screen to fill specified screen resolution",
                                           perform_parse=False)
    parser.add_argument("-s", dest="screen_size",
                        help="Set desired screen resolution, XxY",
                        default="")
    parser.add_argument("-f",
                        help="Set to full computer hardware resolution",
                        action="store_true")
    parser.add_argument("-r",
                        help="Set to the normally used resolution",
                        action="store_true")
    parser.add_argument("-t",
                        help="Toggle display resolution between normal and fixed low res for screen share",
                        action="store_true")
    parser.add_argument("-c",
                        help="Output a command that can be used to scale computers to this display",
                        action="store_true")
    parser.add_argument("-S",
                        help="Return yes if screen resolution is below system normal",
                        action="store_true")
    opts = parser.parse_args()
    syslog.openlog()
    display_setter = DisplaySetter()
    display_setter.get_display_info()
    try:
        if opts.r:
            display_setter.reset_display_to_standard()
        elif opts.f:
            display_setter.reset_display_to_native()
        elif opts.t:
            display_setter.toggle_display_size()
        elif opts.c:
            print(display_setter.generate_scale_to_me_command())
        elif opts.S:
            print(display_setter.is_scaled())
        elif opts.screen_size:
            try:
                desired_x, desired_y = opts.screen_size.split('x')
                display_setter.scale_display(int(desired_x), int(desired_y))
            except ValueError as err:
                localFunctions.error_exit(
                    "Incorrect screen size argument: %s" % err)
        else:
            display_setter.reset_display_to_standard()
    except Exception as err:
        # try to return to the normal state ia problem --might work...
        display_setter.reset_display_to_standard()
        x_res, y_res = display_setter.get_display_info()
        print("Error recovery: Screen size: %d x %d" % (x_res, y_res))
        localFunctions.error_exit(str(err))
