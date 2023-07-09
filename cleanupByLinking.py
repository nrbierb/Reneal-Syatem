#!/usr/bin/python3
# -*- coding: utf-8 -*-

import localFunctions
import backgroundFunctions
import fileManagementFunctions
import subprocess
import datetime
import psutil

PROGRAM_NAME = "cleanupByLinking"
VERSION = 0.5
DESCRIPTION = """Reduce disk usage by symlinking files copied by students and hardlinking
files copied between students. Normally run as cron job."""
LinkLogger = None

class PartitionSizeReporter:
    def __init__(self, partition_name):
        self.partition_name = partition_name
        self.sampled_size_int_dict = {}
        self.timestamp_dict = {}


    def record_current_value(self, event_name):
        disk_usage = psutil.disk_usage("/client_home_students")
        self.sampled_size_int_dict[event_name] = disk_usage.used
        self.timestamp_dict[event_name] = datetime.datetime.now()


    def delta_size_int(self, first_event_name, second_event_name):
        try:
            delta_int = self.sampled_size_int_dict[first_event_name] - \
                        self.sampled_size_int_dict[second_event_name]
        except KeyError:
            delta_int = 0
        return delta_int

    def delta_size_string(self, first_event_name, second_event_name):
        return localFunctions.convert_to_readable(self.delta_size_int(first_event_name,
                                        second_event_name), storage_size=False,
                                        convert_to_storage_size=True, always_show_fraction=True)

    def create_end_report(self, num_symlinked, num_hardlinked):
        symlink_time = self.timestamp_dict["After symlink"] - self.timestamp_dict["Initial"]
        hardlink_time = self.timestamp_dict["After hardlink"] - self.timestamp_dict["After symlink"]
        report_str = "\n  Check symlink time: %0.1f sec\n  Check hardlink time: %0.1f sec\n" \
            %((symlink_time.seconds + symlink_time.microseconds/1e6),
              (hardlink_time.seconds + hardlink_time.microseconds/1e6))
        if not (num_symlinked or num_hardlinked):
            report_str += "  No changes.\n"
        else:
            report_str += "  %d files symlinked (%s)\n" % (num_symlinked,
                                                           self.delta_size_string("Initial",
                                                                                  "After symlink"))
            report_str += "  %d files hardlinked (%s)\n" % (num_hardlinked,
                                                            self.delta_size_string("After symlink",
                                                                                   "After hardlink"))
            report_str += "  Total size reduction: %s\n" %self.delta_size_string("Initial",
                                                                                   "After hardlink")
        disk_usage = psutil.disk_usage("/client_home_students")
        report_str += "  Partition space used: %s    Partition space free: %s    %%used: %0.2f" \
                      % (localFunctions.convert_to_readable(disk_usage.used, storage_size=False,
                                                            convert_to_storage_size=True,
                                                            always_show_fraction=True),
                         localFunctions.convert_to_readable(disk_usage.free, storage_size=False,
                                                            convert_to_storage_size=True,
                                                            always_show_fraction=True),
                         disk_usage.percent)
        return report_str


def report_linked_files(files_list, tag):
    global LinkLogger
    if files_list:
        for file_pair in files_list:
            try:
                report_line = "\t%s\t%s\t%s\n" % (
                    tag, file_pair[0], file_pair[1])
                LinkLogger.info(report_line)
            except IndexError:
                pass


def report_errors(errors):
    if errors:
        ErrorLogger.log("---------------------------------")
        for error in errors:
            ErrorLogger.log(error)


def create_hardlinks_between_common_student_files(min_size):
    """
    Create hard links between media files that one student has copied from another.
    This assures that only one real file exists in the system. Both file type and
    size are checked to prevent linking files that may be individual to each student.
    :return:
    """
    InfoLogger.info("Hardlinking:")
    filename_extensions_by_class, filename_extension_list = \
        fileManagementFunctions.get_media_extensions_by_class()
    linked_files_list, errors = fileManagementFunctions.convert_copies_to_hardlinks(
        "/client_home_students", filename_extension_list, min_size)
    report_linked_files(linked_files_list, "h")
    report_errors(errors)
    return len(linked_files_list)

def create_symlinks_from_all_shared_to_students():
    """
    Convert all copies of files from AllUsersShared that were copied into
    students personal directories.
    :return:
    """
    InfoLogger.info("Symlinking:")
    reference_directories = ["/client_home/AllUsersShared"]
    target_directories = ["/client_home_students/FormOne", "/client_home_students/FormTwo",
                          "/client_home_students/FormThree", "/client_home_students/FormFour",
                          "/client_home_students/FormFive", "/client_home_students/FormSix",
                          "/client_home_students/GuestUser"]
    linked_files_list, errors = fileManagementFunctions.symlink_copies_to_primary(
        reference_directories,
        target_directories)
    report_linked_files(linked_files_list, "s")
    report_errors(errors)
    return len(linked_files_list)


if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, VERSION, DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers("/var/log/cleanup/link_info.log",
                                                                 "/var/log/cleanup/link_error.log")
    LinkLogger = localFunctions.create_timestamped_logger(
        "LinkLogger", "/var/log/cleanup/linked_files.log")
    InfoLogger.info("\n***** Starting CleanupByLinking *****")
    partition_reporter = PartitionSizeReporter("/client_home_students")
    partition_reporter.record_current_value("Initial")
    num_symlinked = create_symlinks_from_all_shared_to_students()
    partition_reporter.record_current_value("After symlink")
    num_hardlinked = create_hardlinks_between_common_student_files("2M")
    partition_reporter.record_current_value("After hardlink")
    InfoLogger.info(partition_reporter.create_end_report(num_symlinked, num_hardlinked))
    InfoLogger.info("----- Completed CleaupByLinking -----")
