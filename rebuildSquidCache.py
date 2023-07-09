#! /usr/bin/python3
"""
Rebuild the squid cache partition. The squid cache on the secondary disk 
is rebuilt as well to assure that both caches are ext4 file types.
"""
import os
import os.path
import re
import subprocess
import sys
import syslog
import time
import shutil

import localFunctions

TWO_DISKS = True
PROGRAM_NAME = "rebuildSquidCache"
PROGRAM_DESCRIPTION = \
    "Erase and recreate the squid file partition. Use only if squid fails to start."
PROGRAM_VERSION = "1.2"


# ----------------------------------------------------------------------

def get_uuids(mount_point):
    """
    should end up with a list of two uuids, one each for the
    squid partition on the two disks.
    """
    uuids = {}
    for name in os.listdir("/etc"):
        if name.startswith("fstab"):
            filename = os.path.join("/etc", name)
            if os.path.isfile(filename):
                uuid = get_mount_info(mount_point, filename)
                if uuid:
                    uuids[uuid] = 1
    return list(uuids.keys())


def get_mount_info(mount_point, fstab_name):
    """
    Read fstab to get information about a mount_point.
    Return the UUID.
    """
    uuid = ""
    try:
        fstab = open(fstab_name, "r").read()
        matchobj = re.search(r'UUID=(\S+)\s+' + mount_point, fstab)
        if matchobj:
            uuid = matchobj.groups()[0]
    except IOError:
        pass
    return uuid


def get_filesys_info(uuid):
    """
    Get the partition and label from blkid for the
    partition with the uuid.
    """
    blkinfo = localFunctions.run_command("blkid", result_as_list=False)
    matchobj = re.search(
        r'^(/dev/\S+):\s+LABEL=\"([^\"]+)\"\s+UUID=\"' + uuid, blkinfo, re.M)
    if matchobj:
        device, label = matchobj.groups()
    else:
        device = ""
        label = ""
    return device, label


def uuid_doesnt_exist():
    """
    Print error if there should be two disks but only one is found
    :return:
    """
    global TWO_DISKS
    if TWO_DISKS:
        # print only once
        print("""
        Do you have both disks in the server? I could not make the partions on
        both of the disks. I wll try to build only a single disk squid.
        """)
        TWO_DISKS = False


def force_umount(device):
    """
    If filesystem cannot be unmounted because of files open, kill the
    processes that have the files open. Then attempt to unmount it
    """
    command = "lsof %s" % device
    return_result = localFunctions.run_command(command, merge_stderr=False,
                                               result_as_list=True,
                                               no_stderr=True)
    for line in return_result:
        mobj = re.match(r'(\w+)\s+(\d+)\s+', line)
        if mobj:
            process = mobj.group(1)
            proc_id = int(mobj.group(2))
            if proc_id > 100:
                # Kill the process that has an open file on the partition
                # Try a gentle kill first, but use a -9 if necessary
                log_status(
                    "Killed process %s to unmount %s" % (process, device))
                if not localFunctions.command_run_successful(
                        "kill %d" % proc_id):
                    log_status("Required kill -9")
                    localFunctions.command_run_successful(
                        "kill -9 %d" % proc_id)
    try:
        command = 'umount %s' % device
        localFunctions.run_command(command, reraise_error=True)
    except subprocess.CalledProcessError as e:
        log_status("force_umount still could not unmount %s: %s"
                   % (device, e))


def rebuild_filesystem(uuid):
    """
    Make an ext4 filesystem on the partition identified by the uuid
    """
    device, label = get_filesys_info(uuid)
    if device and label:
        if localFunctions.command_run_successful("findmnt %s" % device):
            try:
                command = 'umount %s' % device
                localFunctions.run_command(command, reraise_error=True)
            except subprocess.CalledProcessError:
                force_umount(device)
        command = 'mkfs.ext4 -L "%s" -U "%s" %s' % (label, uuid, device)
        try:
            localFunctions.run_command(command, reraise_error=True)
            log_status("Reformatted squid partition %s" % device)
        except subprocess.CalledProcessError as e:
            log_status(
                "filesystem rebuild for %s failed: %s" % (label, e.output),
                is_error=True, fatal=False, exit_code=e.returncode)
    else:
        uuid_doesnt_exist()


def test_squid(test_delay=5.0):
    """
    Confirm that the proxy is working by using nc to test the proxy port 3128
    """
    try:
        time.sleep(test_delay)
        command = "nc -w 1 main-server.lcl 3128"
        localFunctions.run_command(command, reraise_error=True)
        return True
    except subprocess.CalledProcessError:
        return False


def log_status(message, is_error=False, fatal=False, exit_code=0):
    """
    Write a message to the syslog.
    Exit program if fatal is true
    :param message: The full text of the message to be written to syslog
    :param is_error: prefix log message With "Error"
    :param fatal: Exit program if true
    :param exit_code
    :return:
    """
    log_entry = "rebuildSquidCache: %s" % message
    if is_error:
        syslog.syslog("Error: %s" % log_entry)
    else:
        syslog.syslog(log_entry)
    if fatal:
        localFunctions.error_exit("rebuildSquidCache failed: %s" % message,
                                  exit_code)


def rebuild_squid_cache():
    """
    Actions:
    use fstab to get desired UUID  and label for /Squid
    use blkid and the UUID to find the disk partition
    stop squid3
    umount /Squid
    check for unmout
    mkfs.ext4 -U UUID -l label disk partition
    mount /Squid
    os.ismount to confirm mounted
    chown proxy:proxy /Squid
    squid3 -z to rebuild cache
    start squid3
    confirm proxy is running
    """
    global TWO_DISKS
    # The next two commands may give errors if squid is not running
    # or the Squid partition is already unmounted -- no problem
    localFunctions.run_command("systemctl stop squid")
    time.sleep(3)
    # the mount point is /Squid for both disks in appropriate versions
    # of fstab for each disk
    uuids = get_uuids("/Squid")
    if not len(uuids):
        print("""
Erorr: Could not find any disk mount points for squid.
""")
    for uuid in uuids:
        rebuild_filesystem(uuid)
    # filesystem is still unmounted so check space used so remove anything
    # in the root partition /Squid directory
    localFunctions.command_run_successful("rm -r /Squid/*")
    # now both partitions of the squid cache should be rebuilt.
    # rebuild the primary cache and then rsync the second to make
    # both usable
    try:
        if not localFunctions.command_run_successful("findmnt -m /Squid"):
            localFunctions.run_command("mount /Squid", reraise_error=True)
    except subprocess.CalledProcessError as e:
        log_status("Could not mount the /Squid partition: %s" % e.output,
                   is_error=True, fatal=True, exit_code=e.returncode)
    if os.path.ismount('/Squid'):
        shutil.chown("/Squid","proxy","proxy")
        localFunctions.run_command("chown proxy:proxy /Squid")
        localFunctions.run_command("squid -z")
        if TWO_DISKS:
            try:
                localFunctions.run_command("mount /OS_Copies/SquidCopy",
                                           reraise_error=True)
                if os.path.ismount("/OS_Copies/SquidCopy"):
                    localFunctions.run_command(
                        "chown proxy:proxy /OS_Copies/SquidCopy")
                    localFunctions.run_command(
                        "rsync -axH /Squid/ /OS_Copies/SquidCopy")
                    localFunctions.run_command("umount /OS_Copies/SquidCopy")
            except subprocess.CalledProcessError:
                pass
        localFunctions.run_command("systemctl restart squid")
        return test_squid(5.0)
    else:
        return False


if __name__ == "__main__":
    localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION,
                                  PROGRAM_DESCRIPTION)
    localFunctions.confirm_root_user("rebuildSquidCache")
    print("This will take a minute. Please wait.")
    if rebuild_squid_cache():
        print("""
    Everything should be good. Run systemCheck to test it, then try the internet browser.
        """)
        sys.exit(0)
    else:
        print("""
    There was some problem on squid start. Please run systemCheck, write down
    the error, and then reboot. After reboot, run systemCheck again then try
    the browser.
    """)
        sys.exit(1)
