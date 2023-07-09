#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import os.path
import subprocess
import localFunctions
import hashlib


def get_media_extensions_by_class():
    filename_extensions_by_class = {
        "audio": ('mp3', 'aif', 'aiff', 'wav', 'flac', 'ogg', 'wma'),
        "video": ('mp4', 'mp5', 'mov', 'flv', 'wmv', 'swf', 'mkv', 'webm', 'mpg',
                  'vob', 'avi', 'avichd', 'asf'),
        "photo": ('jpg', 'jpeg', 'png', 'gif', 'tiff'),
        "other": ('iso', 'exe')}
    filename_extension_list = []
    for media_class in filename_extensions_by_class.keys():
        filename_extension_list.extend(filename_extensions_by_class[media_class])
    return filename_extensions_by_class, filename_extension_list


class MediaFile:
    __slots__ = ("filename", "fullname", "hashname", "size", "type")


def get_media_files(directory, max_size_by_type_dict={}, skip_dirs=[]):
    """
    Recursively scan a directory for defined filetypes and sizes. This is used
    can be used for reporting and cleaning teacher or students file usage.
    Note: This uses the temporary memory tmpfs named /tmp/checkutils.
    Use the command:
        mkdir /tmp/checkutils
        mount -t tmpfs tmpfs /tmp/checkutils
    to create this filesystem for the temporary file used here.
    :param directory:
    :param max_size_by_type_dict:
    :param skip_dirs:
    :return:
    """
    media_ext_by_class, filename_extension_list = get_media_extensions_by_class()
    media_files_by_class = {}
    media_size_by_class = {}
    for file_class in media_ext_by_class.keys():
        media_files_by_class[file_class] = []
        media_size_by_class[file_class] = 0
    total_media_size = 0
    oversize_media_size = 0
    count = 0
    oversize_files = []
    full_path = os.path.expanduser(directory)
    try:
        if os.path.isdir(full_path):
            tmp_file = "/tmp/find_result.txt"
            path_arg = ""
            for skip_dir in skip_dirs:
                path_arg += ' -path "%s/%s" -prune -o ' % (full_path, skip_dir)
            command = 'find "%s" -xdev %s -type f -printf "%%s,%%p\\n" > %s' \
                      % (full_path, path_arg, tmp_file)
            localFunctions.run_command(command, reraise_error=True, result_as_list=False)
            trash_path = "%s/.local/share/Trash" % full_path
            if os.path.isdir(trash_path):
                command = 'find "%s" -xdev -type f -printf "%%s,%%p\\n" |grep -v trashinfo >> %s' \
                          % (trash_path, tmp_file)
                localFunctions.run_command(command, reraise_error=False, result_as_list=False)
            with open(tmp_file, "r") as f:
                try:
                    for line in f:
                        count += 1
                        try:
                            size_str, filename = line.strip().split(",", 1)
                            filename_lower = filename.lower()
                            found = False
                            for type in media_files_by_class.keys():
                                if found:
                                    break
                                for ext in media_ext_by_class[type]:
                                    if filename_lower.find("." + ext) != -1:
                                        size = int(size_str)
                                        mediafile = MediaFile()
                                        mediafile.fullname = filename
                                        mediafile.filename = os.path.basename(filename)
                                        mediafile.size = size
                                        mediafile.hashname = \
                                            hash_filename(filename, size)
                                        mediafile.type = type
                                        media_files_by_class[type].append(mediafile)
                                        total_media_size += size
                                        media_size_by_class[type] += size
                                        if size > max_size_by_type_dict[type]:
                                            oversize_files.append(mediafile)
                                            oversize_media_size += size
                                        found = True
                                        break
                        except (ValueError, KeyError) as e:
                            print(str(e))
                            pass
                except UnicodeDecodeError:
                    pass
            os.unlink(tmp_file)
    except (IndexError, OSError, subprocess.CalledProcessError):
        pass
    return media_files_by_class, media_size_by_class, oversize_files, total_media_size, oversize_media_size


def fill_hashed_file_datastore(search_directory, datastore, is_dict):
    if os.path.isdir(search_directory):
        command = 'find "%s" -xdev -type f -printf "%%f^%%s^%%p\\n"' \
                  % search_directory
        try:
            find_info = localFunctions.run_command(command, reraise_error=True,
                                                   result_as_list=True)
        except subprocess.SubprocessError:
            return datastore
        for info_line in find_info:
            name, size, fullname = info_line.strip().split("^")
            namehash = hash_filename(name, size)
            if is_dict:
                datastore[namehash] = fullname
            else:
                datastore.append((namehash, fullname))
    return datastore


def identify_matching_files(reference_directories, target_directories):
    matching_files = []
    reference_filelist_dict = {}
    target_filelist_list = []
    for directory in reference_directories:
        fill_hashed_file_datastore(directory, reference_filelist_dict, is_dict=True)
    for directory in target_directories:
        fill_hashed_file_datastore(directory, target_filelist_list, is_dict=False)
    for hashname, fullname in target_filelist_list:
        try:
            reference_file_fullname = reference_filelist_dict[hashname]
            matching_files.append((fullname, reference_file_fullname))
        except KeyError:
            pass
    return matching_files


def symlink_copies_to_primary(reference_directories, target_directories):
    matching_files_list = identify_matching_files(reference_directories, target_directories)
    symlink_list = []
    errors_list = []
    for target_filename, reference_filename in matching_files_list:
        try:
            os.unlink(target_filename)
            os.symlink(reference_filename, target_filename)
            symlink_list.append((reference_filename, target_filename))
        except OSError as e:
            errors_list.append("Symlink '%s'  '%s : %s'" % (reference_filename, target_filename, e))
    return symlink_list, errors_list


def convert_copies_to_hardlinks(target_directory, file_extensions="", min_size=4096):
    """
    :param target_directory:
    :param file_extensions: string list of file extensions to be checked, separated by commas)
    :param min_size: smallest size to be checked
    :return:
    """
    extension_arg = ""
    size_arg = ""
    errors = []
    linked_files_list = []
    matches_found = ["No duplicates"]
    if file_extensions:
        exts = ""
        for ext in file_extensions:
            exts += "'%s'," % ext
        ext_arg = exts.rstrip(",")
        extension_arg = "--ext-filter=onlyext:%s " % ext_arg
    if min_size:
        size_arg = "--ext-filter=size+:%s " % min_size
    list_matches_command = "/usr/local/bin/jdupes --one-file-system  " + \
                           "--quiet --no-prompt --recurse %s%s %s" % (
                           extension_arg, size_arg, target_directory)
    link_command = "/usr/local/bin/jdupes --one-file-system --link-hard " + \
                   "--quiet --no-prompt --recurse %s %s %s" % (
                   extension_arg, size_arg, target_directory)
    try:
        matches_found = localFunctions.run_command(list_matches_command, reraise_error=True,
                                                   result_as_list=True)
    except subprocess.CalledProcessError as e:
        errors.append("Seeking identical files to hardlink with jdupes failed: %s" % e)
    if matches_found[0].startswith("No duplicates") or errors:
        linked_files_list = []
    else:
        try:
            for l in range(3):
                # jdupes sometimes requires multiple runs to find all
                localFunctions.run_command(link_command, reraise_error=True,
                                           result_as_list=False)
                matches_remaining = localFunctions.run_command(list_matches_command,
                                                               reraise_error=True,
                                                               result_as_list=True)
                if matches_remaining[0].startswith("No duplicates"):
                    break
        except subprocess.CalledProcessError as e:
            errors.append("Hardlinking identical files with jdupes failed: %s" % e)
        while len(matches_found) > 1:
            if matches_found[0] and matches_found[1]:
                linked_files_list.append((matches_found[0], matches_found[1]))
            matches_found.pop(0)
    return linked_files_list, errors

def hash_filename(filename, size):
    return hashlib.sha256(str.encode(filename)).hexdigest() + str(size)
