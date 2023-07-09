#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Define a set of file and directory cleanup actions that can be used by other
programs.
"""

import argparse
import glob
import os
import os.path
import re
import copy
import shutil
import subprocess
import syslog
import pwd
import time
import localFunctions
import localFunctionsPy3
import cleanUsersTrash
import fileManagementFunctions
import serveStudentUseWeb

PROTECTED_DIRECTORIES = ["/", "/bin", "/boot", "/cdrom", "/dev", "/etc",
                         "/home",
                         "/initrd.img", "/lib", "/lib64", "/lost+found",
                         "/opt", "/proc", "/root",
                         "/run", "/sbin", "/Squid", "/srv", "/sys", "/usr",
                         "/var", "/vmlinuz"]

PROGRAM_NAME = "systemCleanup"
VERSION = "0.8.2"
WRITE_TO_SYSLOG = True
STUDENT_GROUP_ID = 3000


class FilteredDirectory:
    """
    A class used to generate a list of directories and files safe to remove.
    It will not include any subdirectories that are mount points or belong
    to an active user
    """

    def __init__(self, top_level_directory, exclusions, other_protected_users,
                 prune_active_owner=True):
        if not os.path.isabs(top_level_directory):
            # protection for improper directory - nothing will be removed or touched
            try:
                os.mkdir("/tmp/none")
            except OSError:
                pass
            top_level_directory = "/tmp/none"
        self.top_level_directory = top_level_directory
        self.exclusions = self.build_exclusion_list(top_level_directory, exclusions)
        self.prune_active_owner = prune_active_owner
        uids, gids, user_names = get_active_users_ids()
        self.active_uids = uids
        uids, gids, names = convert_users_to_uids(other_protected_users)
        self.active_uids.extend(uids)
        try:
            self.mounted_filesystems = localFunctions.get_mounted_filesystems()
            self.filtered_list = self.list_contents(top_level_directory)
        except subprocess.SubprocessError:
            self.filtered_list = []
        self.filtered_list_dict = {"full dirs": [], "empty dirs": [],
                                   "other": [], "all": self.filtered_list}

    @staticmethod
    def build_exclusion_list(top_level_directory, exclusions):
        """
        convert any names relative to top level directory to absolute
        :param top_level_directory
        :param exclusions:
        :return:
        """
        exclusion_list = []
        for name in exclusions:
            if os.path.isabs(name):
                exclusion_list.append(name)
            else:
                exclusion_list.append(os.path.join(top_level_directory, name))
        return exclusion_list

    @staticmethod
    def list_contents(directory):
        """
        this will list all of the contents of the directory except the
        ltsp fuse mounts which should not be in the list of possible candidates
        to remove anyway.
        :param directory:
        :return:
        """
        global PROTECTED_DIRECTORIES
        error_str = ""
        try:
            if directory in PROTECTED_DIRECTORIES:
                error_str = "'%s' is a protected directory" % directory
            if not directory == os.path.realpath(directory):
                error_str = "'%s' is not a an absolute path without symlinks." % directory
            if not os.path.exists(directory):
                error_str = "'%s' is not a valid directory name" % directory
        except (OSError, TypeError):
            return []
        if error_str:
            print(error_str)
            return []
        command = "find %s -mindepth 1 -maxdepth 1" % directory
        # fuse mounts are reported on stderr and that is ignored
        return localFunctions.run_command(command, no_stderr=True,
                                          merge_stderr=False)

    def filter_out_active_users(self, file_list):
        """
        Remove all directories that belong to an active_user or are ltspfs
        mounted fs
        :param file_list:
        :return:
        """
        file_list_copy = copy.deepcopy(file_list)
        for entry in file_list_copy:
            try:
                owner_uid = os.stat(entry).st_uid
                if owner_uid in self.active_uids:
                    remove_list_entry(file_list, entry)
            except (PermissionError, FileNotFoundError):
                # this is ltspfs mounted fs or a /tmp file that went away
                remove_list_entry(file_list, entry)
        return file_list

    def has_mounted_filesystems(self, dir_name):
        test_name = re.escape(dir_name + "/")
        for mounted_dir_name in self.mounted_filesystems:
            if re.match(test_name, mounted_dir_name):
                return True
        return False

    def is_mounted_filesystem(self, filename):
        """
        Use list of mounted filesystems to search for filename. Remove filename
        from list of mounted filesystems if found
        :param filename:
        :return:
        """
        return remove_list_entry(self.mounted_filesystems, filename)

    def filter_out_mounted(self, file_list):
        """
        Remove names from list that are mount points or have mount points
        underneath them. Directories that are left are safe to remove recursively
        as are files, etc
        :param file_list:
        :return:
        """
        if file_list:
            file_list_copy = copy.deepcopy(file_list)
            for entry in file_list_copy:
                if entry in self.mounted_filesystems:
                    remove_list_entry(file_list, entry)
                elif os.path.isdir(entry) and self.has_mounted_filesystems(entry):
                    # recursively
                    remove_list_entry(file_list, entry)
                    current_list = self.list_contents(entry)
                    extra_files = self.filter_out_mounted(current_list)
                    file_list.extend(extra_files)
        return file_list

    def filter_out_excluded(self, file_list):
        """
        Remove anything in the exclude list
        """
        if file_list and self.exclusions:
            file_list_copy = copy.deepcopy(file_list)
            for entry in file_list_copy:
                if remove_list_entry(self.exclusions, entry):
                    remove_list_entry(file_list, entry)
        return file_list

    def generate_filtered_list(self):
        """
        The primary external call that will perform all functions an return a safe
        list.
        :param self:
        :return:
        """
        if self.filtered_list:
            if self.prune_active_owner:
                self.filtered_list = self.filter_out_active_users(
                    self.filtered_list)
            self.filtered_list = self.filter_out_mounted(self.filtered_list)
            self.filtered_list = self.filter_out_excluded(self.filtered_list)
            self.filtered_list = self.filter_out_mounted(self.filtered_list)
            self.filtered_list = self.filter_out_excluded(self.filtered_list)
        return self.filtered_list

    def get_filtered_lists(self):
        """
        Create 3 lists of candidates for deletion
        :return (files, empty_dirs, full_dirs):
        """
        self.generate_filtered_list()
        for entry in self.filtered_list:
            if os.path.isdir(entry) and not os.path.islink(entry):
                if any(os.scandir(entry)):
                    self.filtered_list_dict["full dirs"].append(entry)
                else:
                    self.filtered_list_dict["empty dirs"].append(entry)
            else:
                self.filtered_list_dict["other"].append(entry)
        return self.filtered_list_dict


def remove_list_entry(target_list, entry):
    try:
        target_list.remove(entry)
        return True
    except ValueError:
        return False


def get_active_users_ids():
    user_name_list = localFunctions.run_command("who -s", no_stderr=True)
    user_uids, user_gids, user_names = convert_users_to_uids(user_name_list)
    return user_uids, user_gids, user_names


# ----------------------------------------------------------------------
def convert_users_to_uids(user_name_list):
    user_names = []
    user_uids = []
    user_gids = {}
    for user in user_name_list:
        try:
            name = user.split()[0]
            user_names.append(name)
            user_uids.append(pwd.getpwnam(name).pw_uid)
            gid = pwd.getpwnam(name).pw_gid
            count = user_gids.get(gid, 0) + 1
            user_gids[gid] = count
        except (KeyError, IndexError, AttributeError):
            pass
    return user_uids, user_gids, user_names


# ----------------------------------------------------------------------
def clean_dir(top_level_directory, exclusions, prune_active_owner,
              other_protected_users, report_in_syslog=True):
    message = ""
    try:
        try:
            if os.path.ismount(top_level_directory) and \
                    top_level_directory != "/client_home_students":
                return "'%s' is a mounted filesystem. Not checked." %top_level_directory
        except (OSError, TypeError):
            return "'%s' is not a directory" %str(top_level_directory)
        lister = FilteredDirectory(top_level_directory=top_level_directory,
                                   exclusions=exclusions,
                                   prune_active_owner=prune_active_owner,
                                   other_protected_users=other_protected_users)
        filtered_dict = lister.get_filtered_lists()
        # print(top_level_directory)
        # print(filtered_dict)
        files_removed = []
        dirs_removed = []
        if filtered_dict:
            for entry in filtered_dict["other"]:
                # print("other: " + entry)
                try:
                    os.remove(entry)
                    files_removed.append(entry)
                except (OSError, FileNotFoundError, KeyError):
                    pass
            for entry in filtered_dict["empty dirs"]:
                # print("empty: " + entry)
                try:
                    os.rmdir(entry)
                    dirs_removed.append(entry)
                except (OSError, FileNotFoundError, KeyError):
                    pass
            for entry in filtered_dict["full dirs"]:
                # print("full: " + entry)
                try:
                    shutil.rmtree(entry)
                    dirs_removed.append(entry)
                except (OSError, FileNotFoundError, KeyError):
                    pass
        if files_removed:
            message = 'Removed %d files from %s' % (len(files_removed),
                                                      top_level_directory)
        if dirs_removed:
            if files_removed:
                message += "\n  "
            message += "Removed %d directories from %s" % (len(dirs_removed),
                                                           top_level_directory)
    except:
        pass
    return message

# ----------------------------------------------------------------------
def unmount_dead_ltsp_mounts():
    """
    Unmount ltspfs filesystems mounted on /media/username when user username is no
    longer active.
    :return:
    """
    ltsp_filesystems = localFunctions.get_mounted_filesystems(ltspfs_only=True)
    user_uids, user_gids, user_names = get_active_users_ids()
    unmounted_list = ""
    message = ""
    for filesystem in ltsp_filesystems:
        path_parts = filesystem.strip('/').split('/')
        if path_parts[0] == "media":
            if path_parts[1] not in user_names:
                if localFunctions.command_run_successful('umount %s' %filesystem):
                    unmounted_list = unmounted_list + filesystem + ", "
    if unmounted_list:
        message = "Unmounted these ltsp filesystems belonging to inactive users: %s" %unmounted_list
    return message


# ----------------------------------------------------------------------
def clean_os_copies(base_dir):
    """
    Remove any content except mount points in OS_Copies directory with protection
    for mounted fs. Also used in backupAllFilesystems to cleanup the OS_Copies
    directory in them. base_dir should always be in the form /xxx/OS_Copies
    :param base_dir:
    :return:
    """
    if os.path.basename(base_dir) == "OS_Copies" and os.path.isabs(base_dir):
        mount_points = [os.path.join(base_dir, mp_dir) for mp_dir in
                        ("ClientHomeCopy",
                         "ClientHomeStudentsCopy",
                         "MainServerD2",
                         "MainServerCopy",
                         "MainServerD2Copy",
                         "SquidCopy")
                        ]
        # clean out everything except the mount list dirs
        clean_dir(base_dir, exclusions=mount_points, prune_active_owner=False,
                  other_protected_users=[])
        for mount_point in mount_points:
            try:
                if not os.path.ismount(mount_point) and \
                        any(os.scandir(mount_point)):
                    clean_dir(mount_point, exclusions="",
                              prune_active_owner=False,
                              other_protected_users=[])
            except (FileNotFoundError, NotADirectoryError):
                pass


# ----------------------------------------------------------------------
def clean_tmp():
    message = clean_dir("/tmp", exclusions=[], prune_active_owner=True,
                        other_protected_users=["root", "nbd"])
    try:
        for name in glob.glob("/tmp/rsync-*"):
            os.remove(name)
        if os.path.exists("/tmp/shallalist.tar.gz"):
            os.remove("/tmp/shallalist.tar.gz")
        shutil.rmtree("/tmp/BL", ignore_errors=True)
    except (OSError, FileNotFoundError):
        pass
    return message


# ----------------------------------------------------------------------
def clean_client_home_teachers_files(max_media_file_size=500e6, logger=None):
    """
    remove teachers trash and mozilla cache, and media files
    :return:
    """
    accounts = cleanUsersTrash.get_group_users_names("teacher")
    cleanUsersTrash.empty_users_trash(accounts, log=False)
    for account in accounts:
        mozilla_cache_dir = "~%s/.cache/mozilla/firefox" % account
        thumbnail_cache_dir = "~%s/.cache/thumbnails/" % account
        localFunctions.command_run_successful(
            "/bin/rm -r %s/*" % mozilla_cache_dir)
        localFunctions.command_run_successful(
            "/bin/rm -r %s/*/*" % thumbnail_cache_dir)
        directory = os.path.join("/client_home/teachers", account)
        oversize_files = []
        if os.path.exists(directory):
            media_files_by_class, media_size_by_class, oversize_files, \
            total_media_size, oversize_media_size = \
                fileManagementFunctions.get_media_files(directory,
                                                        {"video": max_media_file_size, "audio": 1e7,
                                                         "photo": 2e6, "other": 1})
        serveStudentUseWeb.delete_invalid_files(oversize_files, logger)


# ----------------------------------------------------------------------
def clean_client_home_students_top_level(exclusions, prune_active_owner,
                               other_protected_users, report_in_syslog=True):
    message = ""
    all_exclusions = ["GuestUser", "Classes", "FormOne", "FormTwo", "FormThree",
                      "FormFour", "FormFive", "FormSix", "FormSeven", "FormEight", "FormNine",
                      "FormTen", "FormEleven", "FormTwelve", "last_year", "lost+found"]
    all_exclusions.extend(exclusions)
    trash_dirs = glob.glob("/client_home_students/.Trash*")
    all_exclusions.extend(trash_dirs)
    message += clean_dir("/client_home_students", exclusions=all_exclusions,
                         prune_active_owner=prune_active_owner,
                         other_protected_users=other_protected_users,
                         report_in_syslog=report_in_syslog)
    for tdirname in trash_dirs:
        try:
            stats = os.stat(tdirname)
            shutil.rmtree(tdirname)
            os.mkdir(tdirname)
            os.chown(tdirname, stats.st_uid, stats.st_gid)
        except (OSError, TypeError) as e:
            pass
    return message
# ----------------------------------------------------------------------
def clean_client_home_local(exclusions, prune_active_owner,
                            other_protected_users, rebuild_student_home):
    global STUDENT_GROUP_ID
    # always do the standard actions
    message = ""
    try:
        all_exclusions = ["student" + str(i) for i in range(1,
                                            localFunctionsPy3.number_of_student_accounts() + 1)]
        all_exclusions.extend(exclusions)
        message += clean_dir("/client_home_local", exclusions=all_exclusions,
                             prune_active_owner=False, other_protected_users=[])
        # if no students logged in -- cleanout and rebuild all accounts
        if rebuild_student_home:
            user_uids, user_gids, user_names = get_active_users_ids()
            if STUDENT_GROUP_ID not in user_gids or not prune_active_owner:
                command = "/usr/local/bin/rebuildStudentHomeDirectories --clean --syslog"
                if localFunctions.command_run_successful(command):
                    message += "\nCleaned and rebuilt all homes in /client_home_local"
            else:
                message += clean_dir("/client_home_local", exclusions=exclusions,
                                     prune_active_owner=True, other_protected_users=[])
                command = "/usr/local/bin/rebuildStudentHomeDirectories --build-missing --syslog"
                if localFunctions.command_run_successful(command):
                    message += "\nRebuilt all removed homes in /client_home_local"
    except:
        pass
    return message


# ----------------------------------------------------------------------
def clean_opt(remove_alt_image=False):
    """
    Remove normally unneeded files from /opt/ltsp
    :return:
    """
    clean_dir(top_level_directory="/opt/ltsp", exclusions=["images", "i386", "amd64"],
              prune_active_owner=False, other_protected_users=[], report_in_syslog=False)
    clean_dir(top_level_directory="/opt/ltsp/images", exclusions=["amd64.img", "i386.img"],
              prune_active_owner=False, other_protected_users=[], report_in_syslog=False)
    try:
        if remove_alt_image:
            if localFunctions.command_run_successful("grep i386 /etc/ltsp/ltspd/conf"):
                #if grep succussful we are using i386
                os.remove("/opt/ltsp/images/amd64.img")
            else:
                os.remove("/opt/ltsp/images/i386.img")
    except OSError:
        pass

# ----------------------------------------------------------------------
def clean_media(exclusions=[], prune_active_owner=True, other_protected_users=[]):
    """
    Remove static files and hanging mounts in media. There is special care to avoid
    ltspfs and temp mounted filesystems.
    :return:
    """
    umount_result_message = unmount_dead_ltsp_mounts()
    clean_result_message = clean_dir("/media", exclusions=exclusions,
                               prune_active_owner=prune_active_owner,
                               other_protected_users=other_protected_users)
    return "%s %s" %(clean_result_message, umount_result_message)


# ----------------------------------------------------------------------
def force_logout(group_id):
    """
    This is a very dangerous action that will kill all processes of all users
    with the group_id. This should normally only be used at times when no one
    in that group is working. This is written as separate commands here rather
    than an external script to hide it from general use
    :param group_id:
    :return:
    """
    command = "pgrep --group=%d" % group_id
    if localFunctions.command_run_successful(command):
        # Call for a kill only if some processes are running
        command = "pkill --group=%d" % group_id
        localFunctions.command_run_successful(command)
        # wait a bit for processes to exit normally, then do a hard kill
        time.sleep(2.0)
        command = "pkill --signal=KILL --group=%d" % group_id
        localFunctions.command_run_successful(command)


class Syslogger:
    def __init__(self, common_prefix="", really_write=True):
        self.common_prefix = common_prefix
        self.really_write = really_write

    def log_message(self, text, priority=syslog.LOG_INFO):
        out_text = self.common_prefix + text
        if self.really_write:
            lines = out_text.splitlines()
            for line in lines:
                syslog.syslog(priority, line)
        else:
            print(out_text)


if __name__ == '__main__':
    parser = localFunctions.initialize_app(PROGRAM_NAME, VERSION,
                """Remove unwanted files in /media, /OS_Copies, /client_home_students, /mnt,
      and /var/crash.  Optionally will clean the teacher home directories and student saved files.""",
		 perform_parse=False)
    parser.add_argument("--force_student_logout", dest="force_student_logout",
                        action='store_true',
                        help="Kill all processes from all students to allow full clean and account rebuild")
    parser.add_argument("--clean_teachers_accounts", dest="clean_teachers_accounts",
                         action="store_true",
                         help="Clean out extremely large media files and file types that are not\n" +\
                              "appropriate for storage on the server in each teacher's home directory")
    parser.add_argument("--clean_students_accounts", dest="clean_students_accounts",
                         action="store_true",
                         help="Clean out very large media files and file types that are not\n" +\
                                "appropriate for storage on the server in each student's personal directory\n" +\
                                " and in the Guest User directory")
    parser.add_argument("--max_media_filesize", dest="max_media_filesize", type=float, default=500,
                         help="The maximum media file size in Mb that will not be deleted when cleaning teachers accounts")
    force_student_logout = False
    clean_teachers_accounts = False
    clean_students_accounts = False
    max_media_filesize = 500e6
    try:
        args = parser.parse_args()
        force_student_logout = args.force_student_logout
        clean_teachers_accounts = args.clean_teachers_accounts
        clean_students_accounts = args.clean_students_accounts
        max_media_filesize = int (args.max_media_filesize) * 1e6
    except argparse.ArgumentError as err:
        print("Error in the command line arguments: %s" % err)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    syslogger = Syslogger("", WRITE_TO_SYSLOG)
    syslogger.log_message(
        "systemCleanup starting to remove junk from the filesystems")
    InfoLogger = localFunctions.create_timestamped_logger("InfoLogger",
                                                          "/var/log/cleanup/info.log")
    DeleteFilesLogger = localFunctions.create_timestamped_logger("DeleteLogger",
                                                          "/var/log/cleanup/delete_info.log")
    InfoLogger.info("***** Starting System Cleanup *****")
    initial_size = localFunctions.get_filesystem_space_used("/")
    clean_os_copies("/OS_Copies")
    clean_opt()
    result_message = clean_media(exclusions=[], prune_active_owner=True,
                                 other_protected_users=[])
    if result_message:
        syslogger.log_message(result_message)
    for dirname in ("/mnt", "/var/crash"):
        result_message = clean_dir(dirname, exclusions=[],
                                   prune_active_owner=False,
                                   other_protected_users=[])
        if result_message:
            syslogger.log_message(result_message)
    if force_student_logout:
        force_logout(STUDENT_GROUP_ID)
    if result_message:
        syslogger.log_message(result_message)
    result_message = clean_client_home_local(exclusions=[],
                                             prune_active_owner=True,
                                             other_protected_users=[],
                                             rebuild_student_home=True)
    if result_message:
        syslogger.log_message(result_message)
    result_message = clean_client_home_students_top_level(exclusions=[],
                                             prune_active_owner=True,
                                             other_protected_users=[])
    if result_message:
        syslogger.log_message(result_message)
    clean_tmp()
    message, delta = localFunctions.change_in_filesystem_size("/", initial_size)
    change_message = "%s after performing a System Cleanup" % message
    syslogger.log_message(change_message)
    InfoLogger.info("----- Finished System Cleanup %s ------" % message)
    print(change_message)
    if clean_teachers_accounts:
        initial_size = localFunctions.get_filesystem_space_used("/client_home")
        clean_client_home_teachers_files(max_media_filesize, DeleteFilesLogger)
        message, delta = localFunctions.change_in_filesystem_size("/client_home", initial_size)
        change_message = "%s after performing a System Cleanup" % message
        syslogger.log_message(change_message)
        print(change_message)
    if clean_students_accounts:
        initial_size = localFunctions.get_filesystem_space_used("/client_home_students")
        dirs_removed, files_removed, invalid_files = \
            serveStudentUseWeb.noninteractive_clean_students_directories(
            {"video": 1e7, "audio": 3e6, "photo": 1e6, "other": 1}, DeleteFilesLogger)
        message, delta = localFunctions.change_in_filesystem_size("/client_home_students",
                                                                  initial_size)
        change_message = "%s after performing a System Cleanup" % message
        syslogger.log_message(change_message)
        print(change_message)
