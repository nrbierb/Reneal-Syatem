#! /usr/bin/python3
"""
# Perform the cleanup actions needed at the end of the school year.
# This includes the removal of student files from the year prior,
# cleaning up the current files, moving those to a different directory,
# and finally creating a fresh client_home_student directory structure.
"""
import glob
import grp
import localFunctions
import math
import os
import pwd
import shutil
import sys
import time
import updateStudentList
import fileManagementFunctions

PROGRAM_NAME = "endOfYearCleanup"
PROGRAM_VERSION = "0.8"
PROGRAM_DESCRIPTION = "Move all student and class files and cleanup /client_home_students"
LAST_YEAR_DIRECTORY = "/client_home_students/last_year/"


def human_format_local_function(number):
    """
    Format integers in "human units like K, M, G
    This is a copy of the function from manugrandio, Aug 13, 2017
    This function is named local_function here to shaw that it is
    in a temporary place until an updated systemLibrary file can be
    added in all local sites.
    :param number:
    :return:
    """
    if number == 0:
        return '0.0 '
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(math.floor(math.log(number, k)))
    return '%.1f %s' % (number / k ** magnitude, units[magnitude])


def remove_unwanted_files(path, extensions, max_size):
    removed_files_count = 0
    removed_files_size = 0
    remaining_files_count = 0
    remaining_files_size = 0
    if os.path.exists(path):
        for root, dirs, files in os.walk(path):
            for currentFile in files:
                try:
                    full_path_name = os.path.join(root, currentFile)
                    if not os.path.islink(full_path_name):
                        file_size = os.path.getsize(full_path_name)
                        if any(currentFile.lower().endswith(ext) for ext in
                               extensions) \
                                or (file_size > max_size):
                            removed_files_count += 1
                            removed_files_size += file_size
                            os.remove(full_path_name)
                        else:
                            remaining_files_count += 1
                            remaining_files_size += file_size
                except OSError:
                    pass
        num_students = len(glob.glob(path+"/F*/*/*"))
        print("""
%d oversize or media files in student directories have been removed
    from the last year backup to save %sB space.
    %d student files, total size %sB, have been moved for %d students.
    """
              % (removed_files_count,
                 human_format_local_function(removed_files_size),
                 remaining_files_count,
                 human_format_local_function(remaining_files_size),
                 num_students))


def remove_broken_links(path):
    for root, dirs, files in os.walk(path):
        for currentFile in files:
            try:
                full_path_name = os.path.join(root, currentFile)
                if not os.path.exists(full_path_name):
                    os.remove(full_path_name)
            except OSError:
                pass


def make_special_dirs(name, permission, uid, gid):
    """
    Make directories in /client_home_students
    :param name:
    :param permission:
    :param uid:
    :param gid:
    :return:
    """
    full_name = "InvalidName"
    try:
        full_name = os.path.join("/client_home_students", name)
        os.mkdir(full_name)
        os.chown(full_name, uid, gid)
        os.chmod(full_name, permission)
    except OSError as e:
        print("Failed to create directory %s: %s" % (full_name, e))

def ok_to_run():
    """
    Query that the user really wants to do this.
    :return:
    """
    global LAST_YEAR_DIRECTORY
    first_warning_text = \
        localFunctions.color_text("purple","""
Warning: This will remove all files in that were in /client_home_students/last_year
  and then move all student files and classes from this year into that directory.
  It can only be run once each year. 
  Do you wish to run this program?""")
    second_warning_text = localFunctions.color_text("purple", """
Are you sure you want to run this? (yes/no)""")
    serious_warning_text = localFunctions.color_text("red", """
--------------------------------------------------------
Warning! The directory /client_home_students/last_year has been changed in 
    the last 30 days. This probably means that endOfYearCleanup has been run for
    this year. If it has already been run you will destroy all files and classes
    that were created last year. 
--------------------------------------------------------
Do you really want to do this?""")
    try:
        if os.path.exists(LAST_YEAR_DIRECTORY) and \
            (time.time() - os.path.getctime(LAST_YEAR_DIRECTORY) < 30*24*3600):
            #print(serious_warning_text)
            if not get_yes_or_no(serious_warning_text,repeat_times=2, default=False, negative_text="""
Good. That is safer. Check dates in the client_home_students/last_year directory to
  confirm that endOfYearCleanup has been run this year. If not, then run this again.
  """):
                return False
        else:
            if not get_yes_or_no(first_warning_text, repeat_times=2, default=False,
                                 negative_text="OK. I will not do anything. Quitting."):
                return False
        return get_yes_or_no(second_warning_text, repeat_times=2, default=False,
                                 negative_text="OK. I will not do anything. Quitting.")
    except IOError:
        return False

# ----------------------------------------------------------------------
def get_yes_or_no(prompt, repeat_times=1, default=False, negative_text=""):
    """
    display the prompt then a yes/no on a new line. Repeat yes/no
    repeat_times if improper answer. Return True if yes, False if no,
    default if not correctly answered.
    :param prompt:
    :param repeat_times:
    :param default:
    :return:
    """
    try:
        if default:
            yes_no_text = localFunctions.color_text("green", "yes") + " / no"
        else:
            yes_no_text = "yes / " + localFunctions.color_text("green", "no")
        #prompt = localFunctions.color_text("blue", prompt)
        display_prompt = "%s (%s):\n" %(prompt, yes_no_text)
        reply_text = input(display_prompt)
        for i in range(0, repeat_times + 1):
            if reply_text == "yes":
                return True
            elif reply_text == "no":
                if negative_text:
                    print(negative_text)
                return False
            if i < repeat_times:
                reply_text = input(localFunctions.color_text("purple",'Please type "yes" or "no"\n'))
            else:
                print("Using the default choice: %s" %("Yes" if default else "No"))
                if not default and negative_text:
                    print(negative_text)
                return default
    except IOError:
        return False


if __name__ == '__main__':
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                  PROGRAM_DESCRIPTION)
    localFunctions.confirm_root_user(PROGRAM_NAME)
    if not ok_to_run():
        sys.exit(0)
    else:
        print("Performing cleanup.")
    root_uid = pwd.getpwnam("root").pw_uid
    root_gid = grp.getgrnam("root").gr_gid
    teacher_gid = grp.getgrnam("teacher").gr_gid
    shutil.rmtree(LAST_YEAR_DIRECTORY, ignore_errors=True)
    make_special_dirs("last_year", 0o755, root_uid, root_gid)
    for f in os.listdir("/client_home_students/"):
        #Remove all trash directories immediately to save time
        try:
            if f.startswith(".Trash"):
                os.removedirs(os.path.join("/client_home_students", f))
        except OSError:
            pass
    filename_extensions_by_class, filename_extension_list = \
        fileManagementFunctions.get_media_extensions_by_class()

    remove_unwanted_files("/client_home_students/", filename_extension_list, 2000000)
    try:
        shutil.copytree("/client_home_students/Classes",
                        "/client_home_students/last_year/Classes",
                        symlinks=False, ignore_dangling_symlinks=True)
    except OSError:
        pass
    shutil.rmtree("/client_home_students/Classes", ignore_errors=True)
    for f in os.listdir("/client_home_students/"):
        try:
            if f != "last_year" and f != "lost+found":
                os.rename(os.path.join("/client_home_students", f),
                          os.path.join(LAST_YEAR_DIRECTORY, f))
        except OSError:
            pass
    #Moving directories or deleting files may have broken links. Clean up.
    remove_broken_links("/client_home_students")
    try:
        make_special_dirs("GuestUser", 0o755, root_uid, root_gid)
        make_special_dirs("GuestUser/Documents", 0o777, root_uid, root_gid)
        make_special_dirs("GuestUser/Projects", 0o777, root_uid, root_gid)
        make_special_dirs("Classes", 0o775, root_uid, teacher_gid)
        total, used, free = shutil.disk_usage("/client_home_students")
        print("""The /client_home_students partition current status is:
        Total: %sB
        Used:  %sB
        Free:  %sB
        """ % (human_format_local_function(total),
               human_format_local_function(used),
               human_format_local_function(free)))
        if (free / (used + free)) < .25:
            print(
                "WARNING: less than 25% free remaining for next years students.")
    except OSError:
        pass
    updateStudentList.force_move_of_student_list_to_backup()
    print("End of year cleanup completed.\n")
