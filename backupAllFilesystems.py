#!/usr/bin/env python3
# coding:utf-8
# Author:  N. R. Bierbaum --<>
# Purpose: System Backup
# Created: 02/19/2013

import configparser
import argparse
import collections
import os
import re
import subprocess
import sys
import syslog
import tempfile
import time
import localFunctions
import systemCleanup

# The initial logfile name used before the successful read of the configuration
# file. The filename from the logfile is normally the same.
InitialLogFileName = "/var/log/mirror/mirror.log"
PROGRAM_NAME = "backupAllFilesystems"
PROGRAM_DESCRIPTION = """Mirror all of the file systems configured
                        in /usr/local/etc/mirror/mirror.cfg."""
PROGRAM_VERSION = "2.1"


class FilesystemManager:
    """
    Mount, sync, and unmount filesystems as necessary
    """

    def __init__(self, task):
        self.source_dir = task["source_dir"]
        self.dest_dir = task["dest_dir"]
        self.unmount_src = task["unmount_src"]
        self.unmount_dest = task["unmount_dest"]
        self.disk_to_spindown = task["disk_to_spindown"]
        self.status_text = ""

    # ----------------------------------------------------------------------

    def mount_filesystem(self, full_dirname, mount_type="rw"):
        """
        Mount the filesystem for work
        """
        command_successful, is_mounted = self.check_mount(full_dirname)
        if command_successful and (not is_mounted):
            # not mounted, but check was without error
            try:
                command_prefix, dirname = \
                    self.split_remote_filesystem_info(full_dirname)
                command = "%s /bin/mount %s %s" \
                          % (command_prefix, mount_type, dirname)
                subprocess.check_output(command, stderr=subprocess.PIPE,
                                        shell=True)
                # confirm successful mount
                command_successful, is_mounted = self.check_mount(full_dirname)
            except subprocess.CalledProcessError as e:
                try:
                    self.status_text = "Failed to mount %s: %s" % (full_dirname,
                                                                   e.stderr.decode(
                                                                       sys.getfilesystemencoding()))
                except UnicodeDecodeError:
                    pass
                is_mounted = False
        return is_mounted

    # ----------------------------------------------------------------------
    def unmount_filesystem(self, full_dirname):
        """
        Unmount the specified filesystem under the fuool_dirname
        :param full_dirname:
        :return:
        """
        dirname = ""
        try:
            command_successful, is_mounted = self.check_mount(full_dirname)
            if command_successful and is_mounted:
                command_prefix, dirname = \
                    self.split_remote_filesystem_info(full_dirname)
                subprocess.check_output("%s /bin/umount %s"
                                        % (command_prefix, dirname),
                                        stderr=subprocess.PIPE, shell=True)
                try:
                    self.status_text = "%s   %s unmounted.\n" % (
                        self.status_text, dirname)
                except UnicodeDecodeError:
                    self.status_text = "error in sync text"
                    pass
        except (subprocess.CalledProcessError, UnicodeDecodeError) as e:
            self.status_text = "%s   %s unmount failed: %s\n" \
                               % (self.status_text, dirname,
                                  e.stderr.decode(
                                      sys.getfilesystemencoding()))

    # ----------------------------------------------------------------------

    def mount_filesystems(self):
        """
        Mount both filesystems to prepare for rsync
        """
        return (self.mount_filesystem(self.source_dir, "--read-only") and
                self.mount_filesystem(self.dest_dir, "--rw"))

        # ----------------------------------------------------------------------

    def unmount_filesystems(self):
        """
        If specified in the configuration, unmount a filesystem after the
        rsync is complete. This will protect against unwanted writing and will
        allow the disk to spin down after remaining idle. Note: set the
        idle spindown time in /etc/hdparm.conf.
        """
        for unmount, full_dirname in ((self.unmount_src, self.source_dir),
                                      (self.unmount_dest, self.dest_dir)):
            if unmount:
                self.unmount_filesystem(full_dirname)
        # allow time for disk unmounts
        time.sleep(4.0)
        # set the idle time and then perform immediate spindown.
        # Note: this should be done only once during the mirroring
        # after all actions with the secondary disk have been completed
        if self.disk_to_spindown:
            try:
                primary_device, secondary_device = localFunctions.get_disk_devices()
                if secondary_device:
                    subprocess.check_call("/sbin/hdparm -S 240 /dev/%s"
                                          % secondary_device, shell=True)
                    subprocess.check_call("/sbin/hdparm -y /dev/%s"
                                          % secondary_device, shell=True)
                    self.status_text += "   /dev/%s set to standby (not spinning).\n" \
                                        % secondary_device
            except subprocess.CalledProcessError:
                pass

    def check_mount(self, dirname):
        """
        Use the shell command /bin/mountpoint to determine if the
        filesystem is mounted. If there is a hostname, use a ssh
        command to test
        """
        command_successful = False
        is_mounted = False
        command_prefix, dirname = self.split_remote_filesystem_info(dirname)
        # check if already mounted
        try:
            subprocess.check_output("%s mountpoint -q %s "
                                    % (command_prefix, dirname),
                                    stderr=subprocess.PIPE,
                                    shell=True)
            # is mounted
            command_successful = True
            is_mounted = True
        except subprocess.CalledProcessError as e:
            # not mounted, maybe an error in trying
            if e.stderr:
                command_successful = False
                try:
                    self.status_text = str(
                        e.stderr.decode(sys.getfilesystemencoding()))
                except UnicodeDecodeError:
                    pass
            else:
                command_successful = True
        return command_successful, is_mounted

    def get_status_text(self):
        return self.status_text

    # ----------------------------------------------------------------------
    @staticmethod
    def split_remote_filesystem_info(dirname):
        """
        Check directory name. If it is remote (has hostname:fsname)
        split into the hostname and directory name and create the
        ssh command prefix to run a command remotely.
        """
        command_prefix = ""
        path = dirname.split(":")
        if len(path) == 2:
            hostname = path[0]
            dirname = path[1]
            command_prefix = "ssh %s " % hostname
        return command_prefix, dirname


class Rsyncer:
    # ----------------------------------------------------------------------
    def __init__(self, task):
        """
        Set basic parameters
        """
        self.name = task["name"]
        self.source_dir = task["source_dir"]
        self.dest_dir = task["dest_dir"]
        self.exclude_file = task["exclude_file"]
        self.delete_files = task["delete_files"]
        self.nice = task["nice"]
        self.ionice = task["ionice"]
        self.nocache = task["nocache"]
        self.unmount_src = task["unmount_src"]
        self.unmount_dest = task["unmount_dest"]
        self.disk_to_spindown = task["disk_to_spindown"]
        self.max_percent_full = task["max_percent_full"]
        self.stderr_file = tempfile.TemporaryFile()
        self.status_text = ""
        self.sync_successful = False
        self.filesystemManager = FilesystemManager(task)

    # ----------------------------------------------------------------------
    def clean_dest_dir_before_rsync(self):
        """
        Clean areas in the destination dir that will not be rsynced and
        should be empty.
        :return:
        """
        # confirm again that the filesystem is mounted
        command_successful, is_mounted = self.filesystemManager.check_mount(
            self.dest_dir)
        if command_successful and is_mounted:
            try:
                if self.dest_dir.find("MainServer") != -1:
                    for dirname in ("media", "tmp", "client_home_local", "mnt"):
                        full_dirname = os.path.join(self.dest_dir, dirname)
                        systemCleanup.clean_dir(full_dirname, exclusions=[],
                                                prune_active_owner=True,
                                                other_protected_users=[])
                    systemCleanup.clean_os_copies(os.path.join(self.dest_dir, "OS_Copies"))
                elif self.dest_dir.find("ClientHomeStudentsCopy") != -1:
                    command = 'find %s -name ".Trash-*" -exec rm -r {} \;' % self.dest_dir
                    localFunctions.command_run_successful(command)
            except OSError:
                pass

    # ----------------------------------------------------------------------
    def perform_rsync(self):
        """
        Confirm that the source and destination hosts and filesystems
        are good and are mounted. Then perform the rsync recording the
        verbose results.
        """
        if self.filesystemManager.mount_filesystems():
            used_space = get_used_space(self.source_dir)
            dest_fs_percent_used_start = get_used_space(self.dest_dir)
            self.clean_dest_dir_before_rsync()
            if used_space < self.max_percent_full:
                try:
                    exclude_command = ""
                    delete_command = ""
                    nice_command = ""
                    if self.exclude_file and os.path.exists(self.exclude_file):
                        exclude_command = "--exclude-from=%s" % self.exclude_file
                    if self.delete_files:
                        delete_command = "--delete"
                    if self.nice:
                        nice_command = "nice --adjustment=%d" % self.nice
                    if self.ionice:
                        ionice_command = "/usr/bin/ionice --class=3"
                    else:
                        ionice_command = ""
                    if self.nocache and os.path.exists("/usr/bin/nocache"):
                        nocache_command = "/usr/bin/nocache"
                    else:
                        nocache_command = ""
                    command_prefix = "%s %s %s" % (
                        nocache_command, ionice_command,
                        nice_command)
                    log_filename = "/tmp/rsync-%s.txt" \
                                   % self.name
                    if os.path.exists(log_filename):
                        os.remove(log_filename)
                    rsync_command = \
                        "%s /usr/bin/rsync -axH  --log-file=%s %s %s %s %s" \
                        % (command_prefix, log_filename, delete_command,
                           exclude_command, self.source_dir, self.dest_dir)
                    subprocess.check_output(
                        rsync_command, stderr=subprocess.PIPE, shell=True)
                    self.sync_successful = True
                    self.status_text = process_rsync_log(log_filename)
                    self.status_text += "   %s start %d%% full  finish %d%% full\n" \
                                        % (self.dest_dir, dest_fs_percent_used_start,
                                           get_used_space(self.dest_dir))
                except subprocess.CalledProcessError as e:
                    text = str(e.stderr.decode(sys.getfilesystemencoding()))
                    if text.find("vanish") == -1:
                        self.status_text = text
                        self.sync_successful = False
            else:
                # not enough space, nothing done
                self.status_text = "The source directory (%s) was too full. (%d%%)" \
                                   % (self.source_dir, used_space)
                self.sync_successful = False
        else:
            self.status_text = self.filesystemManager.get_status_text()
            self.sync_successful = False
        self.filesystemManager.unmount_filesystems()
        self.status_text += self.filesystemManager.get_status_text()
        return self.sync_successful, self.status_text


# ----------------------------------------------------------------------

class PasswdBackup:
    """
    Backup changes about teacher accounts from source to backup.
    Only teacher information is updated to keep an otherwise frozen OS copy
    up to date with teachers for login
    """

    def __init__(self, task):
        sd = task["source_dir"]
        dd = task["dest_dir"]
        self.source_passwd_filename = os.path.join(sd, "etc/passwd")
        self.source_shadow_filename = os.path.join(sd, "etc/shadow")
        self.backup_passwd_filename = os.path.join(dd, "etc/passwd")
        self.backup_shadow_filename = os.path.join(dd, "etc/shadow")
        self.source_group_filename = os.path.join(sd, "etc/group")
        self.source_gshadow_filename = os.path.join(sd, "etc/gshadow")
        self.backup_group_filename = os.path.join(dd, "etc/group")
        self.backup_gshadow_filename = os.path.join(dd, "etc/gshadow")
        self.passwd_info = collections.OrderedDict()
        self.shadow_info = collections.OrderedDict()
        self.group_info = {}
        self.gshadow_info = {}
        self.successful = True
        self.status_text = ""
        self.filesystemManager = FilesystemManager(task)

    def get_info_from_source(self):
        """
        Get the current information from the source passwd and shadow files.
        :return:
        """
        try:
            # Use detailed regular expressions to accept only correctly formatted entries in passwd or shadow
            passwd_re = re.compile(r'^\s*([\w\-_.]+:[^:]*:\d+:2000:[^:]*:[^:]*:.*bin.*)\s*$', re.M)
            shadow_re = re.compile(r'^\s*[\w\-_.]+:.*:\d+:\d+:[^:]*:[^:]*:.*$')
            with open(self.source_passwd_filename, "r") as pwf:
                contents = pwf.read()
                # find only teacher entries that have all parts -- not damaged or truncated
                teacher_entries = passwd_re.findall(contents)
                for line in teacher_entries:
                    name = self.get_name(line)
                    self.passwd_info[name] = line + "\n"
            with open(self.source_shadow_filename, "r") as sf:
                all_entries = {}
                for line in sf:
                    m = shadow_re.match(line)
                    if m:
                        clean_line = m.group()
                        name = self.get_name(clean_line)
                        all_entries[name] = clean_line + "\n"
                for name in self.passwd_info.keys():
                    try:
                        self.shadow_info[name] = all_entries[name]
                    except KeyError:
                        pass
        except (IOError, IndexError) as e:
            self.successful = False
            self.status_text = "\n   Failed to read information from the passwd source files: %s\n" % e

    def get_group_info_from_source(self):
        """
        Very simple function to get epoptes line in group -- the only thing that changes for teachers
        :return:
        """
        try:
            group_re = re.compile(r'^\s*epoptes:.*$', re.M)
            with open(self.source_group_filename, "r") as pwf:
                contents = pwf.read()
                epoptes_line = group_re.findall(contents)
                for line in epoptes_line:
                    self.group_info["epoptes"] = line + "\n"
            with open(self.source_gshadow_filename, "r") as pwf:
                contents = pwf.read()
                epoptes_line = group_re.findall(contents)
                for line in epoptes_line:
                    self.gshadow_info["epoptes"] = line + "\n"
        except (IOError, IndexError) as e:
            self.successful = False
            self.status_text = "\n   Failed to read information from the group source files: %s\n" % e

    def update_backup_file(self, original_filename, source_info):
        """
        :param original_filename:
        :param source_info:
        Update either the passwd or shadow file by repaceing or adding lines for each teacher
        account line found in the source file.
        :return:
        """
        if self.successful:
            try:
                new_filename = original_filename + ".new"
                with open(original_filename, "r") as old_backup:
                    with open(new_filename, "w") as new_backup:
                        new_lines = []
                        for orig_line in old_backup:
                            if len(orig_line.strip()):
                                name = self.get_name(orig_line)
                                new_lines.append(
                                    source_info.pop(name, orig_line))
                            else:
                                print("empty line")
                        # remaining teacher_account entries are new
                        new_lines.extend(source_info.values())
                        new_backup.writelines(new_lines)
                for i in ("chmod", "chown"):
                    localFunctions.command_run_successful("%s --reference=%s %s" \
                                                          % (i, original_filename, new_filename))
                localFunctions.copy_file(original_filename, original_filename + ".old")
                localFunctions.copy_file(new_filename, original_filename)
                os.remove(new_filename)
                if original_filename == "/etc/password":
                    self.status_text += "\n"
                self.status_text += "   %s updated successfully.\n" % original_filename
            except (OSError, IOError) as err:
                self.successful = False
                self.status_text += "\n   %s failed update: %s\n" % (original_filename, err)
        return self.successful, self.status_text

    @staticmethod
    def get_name(entry):
        try:
            return re.findall(r'^\s*([\w\-_.]+):', entry)[0]
        except IndexError:
            return ""

    def file_needs_backup(self, source_file_name, backup_file_name):
        try:
            needs_backup = False
            if os.path.exists(backup_file_name):
                needs_backup = os.path.getctime(source_file_name) > \
                               os.path.getctime(backup_file_name)
            else:
                localFunctions.copy_file(backup_file_name + ".release",
                                         backup_file_name)
                needs_backup = True
        except (OSError, subprocess.CalledProcessError) as e:
            self.status_text = "   Passwd backup failed:\n     %s" % e
            self.successful = False
            needs_backup = False
        return needs_backup

    def backup_passwd_info(self):
        if self.filesystemManager.mount_filesystems():
            try:
                passwd_file_needs_backup = self.file_needs_backup(self.source_passwd_filename,
                                                                  self.backup_passwd_filename)
                shadow_file_needs_backup = self.file_needs_backup(self.source_shadow_filename,
                                                                  self.backup_shadow_filename)
                if passwd_file_needs_backup or shadow_file_needs_backup:
                    self.get_info_from_source()
                    if passwd_file_needs_backup:
                        self.update_backup_file(self.backup_passwd_filename,
                                                self.passwd_info)
                    if shadow_file_needs_backup:
                        self.update_backup_file(self.backup_shadow_filename,
                                                self.shadow_info)
                else:
                    self.status_text = "\n   Passwd and shadow files already up to date.\n"
                group_file_needs_backup = self.file_needs_backup(self.source_group_filename,
                                                                 self.backup_group_filename)
                gshadow_file_needs_backup = self.file_needs_backup(self.source_gshadow_filename,
                                                                   self.backup_gshadow_filename)
                if group_file_needs_backup or gshadow_file_needs_backup:
                    self.get_group_info_from_source()
                    self.update_backup_file(self.backup_group_filename, self.group_info)
                    self.update_backup_file(self.backup_gshadow_filename, self.gshadow_info)
                else:
                    self.status_text += "   Group and gshadow files already up to date.\n"
            except (OSError, subprocess.CalledProcessError) as e:
                self.status_text = "   Passwd backup failed:\n     %s" % e
                self.successful = False
        else:
            self.status_text = self.filesystemManager.get_status_text()
            self.successful = False
        # always try unmount in case the mount partially succeeded
        self.filesystemManager.unmount_filesystems()
        self.status_text += self.filesystemManager.get_status_text()
        return self.successful, self.status_text


# ----------------------------------------------------------------------
def get_used_space(dirname):
    """
    determine free space on file partition
    :param dirname:
    :return:
    """
    used_space_percent = 1
    try:
        if os.path.ismount(dirname):
            command = '/bin/df %s' % dirname
            result = localFunctions.run_command(command, reraise_error=True,
                                                merge_stderr=False)
            found_values = re.findall(r'(\d+)%', result[1])
            # confirm valid number
            used_space_value = int(found_values[0])
            if 1 < used_space_value < 101:
                used_space_percent = used_space_value
    except (subprocess.CalledProcessError, ValueError, IndexError):
        pass
    return used_space_percent


# ----------------------------------------------------------------------
def process_rsync_log(logfile_name):
    """
    Reduce the long rsync verbose output to a summary.
    """
    try:
        results = {">f+": 0, ">f.": 0, "cd+": 0, ".d.": 0, "*de": 0}
        log_f = open(logfile_name, "r")
        count = 0
        stats = ""
        for raw_line in log_f:
            count += 1
            try:
                line = str(raw_line)
                action = line.split()[3][:3]
                if action not in results:
                    results[action] = 0
                results[action] += 1
                if action == 'sen':
                    stats = line.split(" ", 3)[3]
            except (UnicodeDecodeError, IndexError):
                pass
        summary = """
   New files:%d  Changed files:%d 
   New/Changed dirs:%d Deleted:%d Total actions:%d
   Statistics: %s""" \
                  % (results[">f+"], results[">f."], results["cd+"],
                     results["*de"], count - 2, stats)
        return summary
    except IOError:
        return "Error: Failed to read logfile " + logfile_name


def generate_mirror_log_entry(result_text, sync_successful,
                              starting, is_mirror_log,
                              source_dir, dest_dir, task_type,
                              job_name):
    """
    Create a log file entry for a single instance of a filesystem
    backup. If is_mirror_log then add formatted time for programmatic
    processing.
    """
    line_separator = '.  '
    prefix = ""
    if is_mirror_log:
        line_separator = '\n'
    if sync_successful:
        result = "completed:%s" % result_text
        flag = "++"
    elif starting:
        result = "starting."
        flag = "**"
    else:
        result = "failed:%s  %s" % (line_separator, result_text)
        flag = "--"
    if is_mirror_log:
        prefix = "%s %s: (%s) " % (flag, time.asctime(), round(time.time(), 2))
    if job_name:
        entry = '%sMirror Job ---%s--- %s%s' % (prefix, job_name,
                                                result, line_separator)
    else:
        entry = "%s%s %s to %s %s%s" % (prefix, task_type, source_dir,
                                        dest_dir, result, line_separator)
    return entry


def log_results(result_text="", sync_successful=False, starting=True,
                mirror_logfile=InitialLogFileName, source_dir="", dest_dir="",
                task_type="Mirror", job_name=""):
    """
    Add log entries about a filesystem mirror to both the
    system log and a mirror specific log.
    """
    try:
        message = generate_mirror_log_entry(result_text, sync_successful,
                                            starting, False, source_dir, dest_dir,
                                            task_type, job_name)
        syslog.syslog(message)
    except IOError:
        pass
    try:
        logfile = open(mirror_logfile, "a")
        message = generate_mirror_log_entry(result_text, sync_successful,
                                            starting, True, source_dir, dest_dir,
                                            task_type, job_name)
        logfile.write(message)
        logfile.close()
    except IOError:
        pass

def write_separator(mirror_logfile=InitialLogFileName):
    with open(mirror_logfile, "a") as logfile:
        logfile.write('\n      -------------------------  %s  -------------------------\n\n'
                      %time.asctime())

def rotate_mirror_log(mirror_logfile="/var/log/mirror/mirror.log"):
    """
    If current mirror log file has more than max lines
    create new and rotate names in the standard log way.
    """
    try:
        stderr_file = tempfile.TemporaryFile()
        try:
            command = "shtool rotate --num-files=10 --size=500K --compress=gzip:6 %s" \
                      % mirror_logfile
            subprocess.check_output(command, stderr=stderr_file, shell=True)
        except subprocess.CalledProcessError as e:
                stderr_file.seek(0)
                message = "Failed to rotate mirror log files: %s" \
                          % e.stderr.decode(sys.getfilesystemencoding())
                syslog.syslog(message)
        stderr_file.close()
    except IOError:
        pass

def create_task_dict(config, taskname, nice, ionice, nocache):
    """
    process an entry in the mirror.cfg file to create a dictionary with all
    relevant values for the the task
    :param config:
    :param taskname:
    :param nice:
    :param ionice:
    :param nocache:
    :return:
    """
    task_dict = {"name": taskname,
                 "source_dir": config.get(taskname,
                                          "source_directory"),
                 "dest_dir": config.get(taskname,
                                        "destination_directory"),
                 "exclude_file": config.get(taskname,
                                            "exclude_list_file"),
                 "delete_files": config.getboolean(taskname,
                                                   "delete_unmatched_files"),
                 "max_percent_full": config.getint(taskname,
                                                   "max_percent_full",
                                                   fallback=97),
                 "nice": nice or config.getint(taskname,
                                               "nice"),
                 "nocache": nocache,
                 "ionice": ionice,
                 "unmount_src": config.getboolean(taskname,
                                                  "unmount_source_filesystem"),
                 "unmount_dest": config.getboolean(taskname,
                                                   "unmount_destination_filesystem"),
                 "disk_to_spindown": config.get(taskname,
                                                "disk_to_spindown"),
                 "mirror_logfile": config.get(taskname,
                                              "mirror_log_file")}
    return task_dict


def read_configuration_file(filename, jobname, nice, ionice, nocache):
    """
    Read a simple configuration file  and return a dictionary with parsed
    results. The  config_params argument is a dictionary with default
    values to protect against a missing or damaged configuration file
    """
    default_logfile = ""
    mirror_tasks = []
    passwd_tasks = []
    error_text = ""
    fatal_error = False
    try:
        config = configparser.ConfigParser()
        config.read(filename)
        default_logfile = config.get("DEFAULT", "mirror_log_file")
        if config.has_section(jobname):
            for taskname in config.get(jobname, "passwd_list").splitlines():
                if config.has_section(taskname):
                    passwd_tasks.append(create_task_dict(config, taskname, nice, ionice, nocache))
            for taskname in config.get(jobname, "mirror_list").splitlines():
                if config.has_section(taskname):
                    mirror_tasks.append(create_task_dict(config, taskname, nice, ionice, nocache))
                else:
                    error_text += \
                        'Task "%s" not found in configuration file %s.\n' \
                        % (taskname, filename)
        else:
            error_text = \
                'Job name "%s" not found in configuration file %s.\n' \
                % (jobname, filename)
            fatal_error = True
    except (IOError, KeyError, configparser.NoOptionError, configparser.DuplicateOptionError) as e:
        error_text = 'Error while reading %s: %s' % (filename, e)
        fatal_error = True
    return default_logfile, passwd_tasks, mirror_tasks, error_text, fatal_error


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.prog = PROGRAM_NAME
    p.description = PROGRAM_DESCRIPTION
    p.add_argument('-v', "--version", action='version',
                   version=PROGRAM_VERSION)
    p.add_argument('-j', '--jobname',
                   dest='jobname',
                   help='The name of the job in the configuration file')
    p.add_argument('-f', '--config-file',
                   dest='config_file',
                   help='The name of the configuration file')
    p.add_argument('-n', '--nice', type=int, dest='nice',
                   help="The processes' nice value if different than what is in the configuration file.")
    p.add_argument("--ionice", action='store_true',
                   help='use ionice to reduce io priority')
    p.add_argument("--nocache", action='store_true',
                   help="Use nocache on rsync if nocache program is available")
    p.set_defaults(jobname='DailyJobs',
                   config_file='/usr/local/etc/mirror/mirror.cfg',
                   nice=5)
    try:
        opt = p.parse_args()
    except argparse.ArgumentError as err:
        print("Error in the command line arguments: %s" % err)
        sys.exit(1)
    if not os.path.exists(opt.config_file):
        print ("The config file '%s' does not exist" %opt.config_file)
        sys.exit(1)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    # check for current run -- do not run the program twice at the same time.

    default_logfile = InitialLogFileName
    # if there in no mirror log file, create one for later use.
    if not os.path.exists(default_logfile):
        try:
            f = open(default_logfile, "w")
            f.close()
        except IOError as err:
            print("Unable to create a logfile: %s" % err, file=sys.stderr)
            sys.exit(1)
    # rotate_mirror_log(default_logfile)
    write_separator(default_logfile)
    log_results(starting=True, mirror_logfile=default_logfile,
                job_name=opt.jobname)
    default_logfile, passwd_tasks, mirror_tasks, error_text, fatal_read_error = \
        read_configuration_file(opt.config_file, opt.jobname, opt.nice,
                                opt.ionice,
                                opt.nocache)
    if fatal_read_error:
        print("File system mirroring completely failed: %s"
              % error_text, file=sys.stderr)
        log_results(starting=False, job_name=opt.jobname, sync_successful=False,
                    result_text=error_text)
        sys.exit(-1)

    job_successful = True
    systemCleanup.clean_os_copies("/OS_Copies")
    for passwd_task in passwd_tasks:
        log_results(starting=True, result_text="", sync_successful=False,
                    mirror_logfile=passwd_task["mirror_logfile"],
                    source_dir=passwd_task["source_dir"],
                    dest_dir=passwd_task["dest_dir"],
                    task_type="Passwd Backup")
        try:
            passwdBacker = PasswdBackup(passwd_task)
            successful, result_text = passwdBacker.backup_passwd_info()
        except Exception as err:
            result_text = "   Passwd backup failed:\n     %s" % err
            successful = False
        log_results(starting=False, result_text=result_text,
                    sync_successful=successful,
                    mirror_logfile=passwd_task["mirror_logfile"],
                    source_dir=passwd_task["source_dir"],
                    dest_dir=passwd_task["dest_dir"],
                    task_type="Passwd Backup")
        job_successful = job_successful and successful
    for mirror_task in mirror_tasks:
        log_results(starting=True, result_text="", sync_successful=False,
                    mirror_logfile=mirror_task["mirror_logfile"],
                    source_dir=mirror_task["source_dir"],
                    dest_dir=mirror_task["dest_dir"],
                    task_type="Mirror")
        try:
            rsyncer = Rsyncer(mirror_task)
            successful, result_text = rsyncer.perform_rsync()
        except Exception as err:
            result_text = "   Mirror failed:\n     %s" % err
            successful = False
        log_results(starting=False,
                    result_text=result_text,
                    sync_successful=successful,
                    mirror_logfile=mirror_task["mirror_logfile"],
                    source_dir=mirror_task["source_dir"],
                    dest_dir=mirror_task["dest_dir"],
                    task_type="Mirror")
        job_successful = job_successful and successful
    log_results(starting=False, result_text="",
                sync_successful=job_successful,
                mirror_logfile=default_logfile,
                job_name=opt.jobname)
