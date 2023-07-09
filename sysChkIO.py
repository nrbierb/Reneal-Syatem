#!/usr/bin/python3
"""
This file contains the python modules for text io and GUI for the systemCheck
program. All texts that are used in the program output are maintained in this
file in sysChkTxt.
"""
import textwrap, re, sys, time, pwd, os, io


class SysChkText:
    # ----------------------------------------------------------------------
    def __init__(self):
        self.sysChkTxtDict = {}
        self.sysChkTxtDict["fix worked"] = \
            "OK, the fix worked."
        self.sysChkTxtDict["fix failed"] = \
            "Sorry, but the fix attempt failed."

    # ----------------------------------------------------------------------
    def add_process_check_texts(self):
        """
        Texts to be shown with process check actions and errors.
        """
        self.sysChkTxtDict["try start process"] = \
            "Restarting the %s process '%s' with the command '%s'"
        self.sysChkTxtDict["failed processes"] = \
            "These required system processes have stopped:%s\n Will now restart them."
        self.sysChkTxtDict["failed process"] = \
            "This required system process has stopped:%s Will now restart it."
        self.sysChkTxtDict["failed restart processes"] = \
            "These required system processes were not successfully restarted or\n" + \
            "          failed again just after restart: %s"
        self.sysChkTxtDict["failed restart process"] = \
            "This required system process was not successfully restarted or \n" + \
            "          failed again just after restart: %s"
        self.sysChkTxtDict["process restart failed"] = \
            "This process could not be restarted successfully. \n" + \
            "This was the reported error: %s"
        self.sysChkTxtDict["process failed restart"] = \
            """The failure to restart %s means that other 
            problems that are caused by this failure may appear in the other tests.
            You should try restarting the server and then rerunning
            System Check. If the problem remains then analyze any error
            reports and possibly log files for further ideas."""
        self.sysChkTxtDict["process restart successful"] = \
            """All required processes now running.  This may fix your problem.
            Please run System Check again to check if all problems are solved."""
        self.sysChkTxtDict["proxy test failed"] = \
            """The proxy server refuses the connection. Will try squid process restart. """
        self.sysChkTxtDict["proxy restart successful"] = \
            """The proxy server is now working correctly."""
        self.sysChkTxtDict["kahn test failed"] = \
            """The server for Kahn Academy is not running correctly.
            Will try server restart. """
        self.sysChkTxtDict["kahn restart successful"] = \
            """The server for Kahn Academy is now working correctly"""
        self.sysChkTxtDict["kahn needs further work problem"] = \
            """The Kahn Academy server is still not working correctly. """
        self.sysChkTxtDict["kahn needs further work action"] = \
            """Attempt to restart the Kahn Academy server with the commands:
        "sudo systemctl stop ka-lite"
        "sudo systemctl start ka-lite"
        Check the messages at the end of /var/log/syslog.
        """
        self.sysChkTxtDict["openvpn test failed"] = \
            """The openvpn remote network is not running correctly.
            Will try restart. """
        self.sysChkTxtDict["openvpn restart successful"] = \
            """Openvpn is now working correctly"""
        self.sysChkTxtDict["openvpn restart failed"] = \
            """Openvpn is still not working. This may be a problem in the
            remote end or in the internet connection."""
        self.sysChkTxtDict["root process cpu use"] = \
            """A system process is using too much cpu -- it has probably failed and locked up."""
        self.sysChkTxtDict["reboot server strong"] = \
            """Reboot Server >> You should request users to logout and shutdown the clients,
        then reboot the server."""
        self.sysChkTxtDict["root process cpu use action"] = \
            """This system process has probably failed:
%s
        Reboot the server.  If this problem happens more than once, please take a photo 
        of this message to send to the Reneal team."""
        self.sysChkTxtDict["report problem process"] = "%s"
        self.sysChkTxtDict["problem cpu process action"] = \
            """Problem Process:
%s
        Check the problem process's user and consider stopping the process. 
        To stop, use the ID from the table in the command "sudo kill ID". 
        Run System Check once more. If the same process is still a problem 
        type "sudo kill -9 ID".
        Check the manual or Reneal Superusers Group for further information."""
        self.sysChkTxtDict["problem memory process action"] = \
            """Problem Process:
%s
        This high memory usage process is probably bad.
        If you do not recognize it and know that it should use so 
        much memory or if the memory usage is above 50%% stop the process.
        To stop, use the ID from the table in the command "sudo kill ID".
        Run System Check once more. If the same process is still a problem
        type "sudo kill -9 ID".
        Check the manual or Reneal Superusers Group for further information."""

    # ----------------------------------------------------------------------
    def add_disk_check_texts(self):
        """
        """
        self.sysChkTxtDict["active disk failing"] = \
            """WARNING: The %s disk drive (%s), the disk that is currently running the OS 
        reports that it is failing."""
        self.sysChkTxtDict["active disk failing action"] = \
            """Tell all users to log off NOW and shutdown all client computers."
        Then run the command "sudo emergency_mirror". 
        After this completes, run the command "sudo smartctl -a %s", 
        take a photo of the command output.  Do not turn off the server until everything finishes.
        Contact the Reneal team as soon as possible"""
        self.sysChkTxtDict["primary disk failure action"] = \
            """Wait two minutes after turnoff to let the system cool, then turn
        back on again. The system should boot from the backup drive."""
        self.sysChkTxtDict["backup disk failure"] = \
            """WARNING: The backup disk %s reports that it is failing."""
        self.sysChkTxtDict["backup disk failure action"] = \
            """The backup disk %s  should be replaced and rebuilt. 
        No user file backups can be performed until is replaced."""
        self.sysChkTxtDict["running on backup disk"] = \
            """The server is running from the backup disk drive."""
        self.sysChkTxtDict["disk missing"] = \
            """The %s disk drive has either completely failed,
        is unplugged, or has been removed from the computer."""
        self.sysChkTxtDict["disk missing action"] = \
            """Report that the %s disk drive is missing 
        to the Reneal team immediately. Click the button "Computer Information"
        on the Dashboard and send the team a photo of the result window. 
        Check the state of the Reneal tamper seal markers on the 
        server case to detect if it has been opened. """
    # ----------------------------------------------------------------------
    def add_filesystem_check_texts(self):
        self.sysChkTxtDict["file system not mounted"] = \
            "The file system partition %s mounted on %s which is used for %s is not mounted."
        self.sysChkTxtDict["filesystem requires check"] = \
            """The file system partition %s for the file system %s must be
            checked for errors."""
        self.sysChkTxtDict["fsck start"] = \
            """Starting a check on partition %s for the file system %s 
            with the command fsck -p %s. This may take some time. """
        self.sysChkTxtDict["fsck no errors"] = \
            "The check showed no errors"
        self.sysChkTxtDict["fsck errors corrected"] = \
            "The check corrected small errors."
        self.sysChkTxtDict["fsck failed"] = \
            "The check on partition %s failed. It reported: %s"
        self.sysChkTxtDict["run fsck"] = \
            """Run the command "sudo fsck -f %s". As it runs it will ask if you
        you wish to correct an error that it has found. Answer "yes" for up to
        10 of these requests. If it continues to ask you for still more fixes
        answer no. If there are many questions the filesystem is badly damaged
        and probably cannot be used. Refer to the manual for further info.
        If the command reports that all errors are fixed rerun System Check to 
        properly mount it. """
        self.sysChkTxtDict["trying mount"] = \
            "Trying to mount the partition %s as filesystem %s"
        self.sysChkTxtDict["mount successful"] = \
            "Mount completed. This may solve problems with %s"
        self.sysChkTxtDict["mount failed"] = \
            "Failed to mount the filesystem. Error reported: %s"

    # ----------------------------------------------------------------------
    def add_interface_check_texts(self):
        """
        Numerous texts about interface problems and status.
        """
        self.sysChkTxtDict["interface restart"] = \
            """I will try to restart the
        interface with the commands "ifconfig %s down" and then "ifconfig %s up". 
        This will take a little time."""
        self.sysChkTxtDict["interface fixed"] = \
            "The network interface %s is now working correctly."
        self.sysChkTxtDict["partial interface fix"] = \
            """The network interface %s has been partially fixed.
        It is running but still has no ip address."""
        self.sysChkTxtDict["interface fix failed"] = \
            "This did not fix the problem with %s."
        self.sysChkTxtDict["one lab interface not running"] = \
            """The lab ethernet interface "%s" is not running."""
        self.sysChkTxtDict["one lab interface not running action"] = \
            """The lab ethernet interface "%s" (probably the %s network card) is not running.
        The cable is likely disconnected or it is bad. Check the lights on
        the interfaces and the switch to determine which ethernet interface
        has the problem and then unplug and replug the connector on both the
        server and the switch. If that does not work then try the command
        "sudo ifdown %s" and then "sudo ifup %s". If that does not work then the
        interface card in the server or the port on the network switch may be
        bad. If this will be a permanent problem (cable broken), use "Interface Warning Off" app
        to mark interface 'Failed'"""
        self.sysChkTxtDict["bond interface not running"] = \
            """The bonded network connection %s which uses %s is not running."""
        self.sysChkTxtDict["turn on network switch"] = \
            "Check the lab's ethernet network switch - it is probably turned off."
        self.sysChkTxtDict["dhcp failed"] = \
            """The %s interface is running but does not have
            its automatically assigned ip address."""
        self.sysChkTxtDict["restart modem"] = \
            """Try restarting the internet modem and then run System Check 
        again after the modem is finished booting. If this still does not work 
        check the light on the modem for the connection to the internet after 
        the modem restarts. The modem itself may be bad or not configured 
        correctly. Check the manual for your modem further information.
        The internet will not work until this problem is corrected."""
        self.sysChkTxtDict["restart other computer"] = \
            """Try restarting the other computer that this server is connected to and
        then run systemCheck again."""
        self.sysChkTxtDict["interface not running"] = \
            """Interface %s is not running."""
        self.sysChkTxtDict["check cable"] = \
            """Check for lights on the interface %s and on
        the %s. Unplug and then fully plug in the cable on both ends. If this
        does not fix the problem you may have a bad cable or bad interface. Try 
        replacing the cable and retest."""
        self.sysChkTxtDict["wireless not running"] = \
            """Wireless interface %s is not working correctly."""
        self.sysChkTxtDict["check wireless"] = \
            """Run "Check Wireless" to determine the problem with the wireless. 
        Confirm that the wireless adapter is plugged in
        and that the wireless router is turned on and in range.
        """
        self.sysChkTxtDict["interface not up"] = \
            """The interface %s has not started successfully and is not up."""
        self.sysChkTxtDict["interface could not come up"] = \
            """The interface %s could not be started. Have you just removed 
        or replaced the ethernet card or, if wireless, the wireless USB? 
        If so, see the System Administrator's Manual for more information.
        If not, try rebooting the computer.
        If you are still not successful then the interface hardware may 
        have failed."""
        self.sysChkTxtDict["no local hosts found problem"] = \
            """No active computers could be found on the lab network."""
        self.sysChkTxtDict["no local hosts found action"] = \
            """If some client computers are on but none are seen then there may be a 
        problem with the server interfaces or the network switch. 
        If only one client computer is turned on, that computer may be the problem.
        Try starting one or two more computers and rerun System Check."""
        self.sysChkTxtDict["local host count"] = \
            "Number of computers on the local network: %s "

    def add_internet_texts(self):
        self.sysChkTxtDict["internet off"] = \
            """The browser internet access has been turned off by sysadmin but will turn on %s"""
        self.sysChkTxtDict["internet off action"""] = \
            """If you want to turn internet access on right now use the button Internet On/Off in
        the System Management Applications panel."""
        self.sysChkTxtDict["proxy bad"] = \
            """There is a problem with the network caching squid proxy service."""
        self.sysChkTxtDict["nameserver bad"] = \
            """There is a problem with the way the server finds network addresses."""
        self.sysChkTxtDict["internet interface down"] = \
            """The internet is down. The network connection from the server to the internet
        router is bad."""
        self.sysChkTxtDict["internet interface down action"] = \
            """If you do not have internet click on the button "Interface Warning Off"
        on the System Management Applications panel and set "Internet Connected" to "No".
        If you do have internet check that the internet router is turned on and that 
        the ethernet cable is connected. Check the cable by unplugging and then 
        plugging back in both ends."""
        self.sysChkTxtDict["retrying internet tests"] = \
            """Some fixes have been performed after repairing some problems that
        could cause the internet to fail. Will retry internet connection one
        more time to see if the the internet will work now.            """
        self.sysChkTxtDict["router ping failed"] = \
            """The test ping to the internet router failed. The server interface
        and the router interface are OK. There must be a problem inside the
        router. """
        self.sysChkTxtDict["router ping failed action"] = \
            """Turn the power to the internet modem off and back on and reboot it.
        Check the lights as it starts to be sure that it ethernet interface
        starts up and blinks. After it is fully started run System Check again."""
        self.sysChkTxtDict["internet down"] = \
            """The internet is down but there is no problem in the server.
        Your internet service from outside may be down or the internet router
        might not be working.  Turn the internet router off and then back on. 
        Watch the lights as it starts to see if it starts correctly and shows a 
        connection to the outside internet link. If it does not show the 
        connection then your service has failed. Wait a while to see if it 
        returns and if necessary report the problem to your internet service 
        provider. 
        Read the manual for your internet router for other information."""
        self.sysChkTxtDict["firewall restart"] = \
            """There might be a problem with the server firewall. I will try restarting it.
        Run System Check again to confirm fix. If the problem still exists then it
        is probably some problem with the internet service provider. Try restarting
        the internet modem. Maybe that will fix it."""
        self.sysChkTxtDict["no modems found"] = \
            """No modem could be found on the internet interface %s. If the modem is turned on
        restart it and run System Check again. If the restart does not help then there may
        be some problem with this interface."""
        self.sysChkTxtDict["internet quality"] = "Internet connection quality: %s"

    def add_other_texts(self):
        self.sysChkTxtDict["no backup log"] = \
            """The backup log could not be found or it was empty."""
        self.sysChkTxtDict["backup old"] = """Backups are too old.
        The last backup of the primary OS filesystem "/" was %s.
        The last backup of the home directories "/client_home" was %s.
        The last backup of the student directories "/client_home_students" was %s.
        The last backup of the entire system was %s. """
        self.sysChkTxtDict["backup failed"] = """Some filesystem backups failed.
        %s%s"""
        self.sysChkTxtDict["run backup action"] = """Run the system backup now with
        the command "sudo backupAllFilesystems". The backup may run for many
        minutes and could slightly slow down your users. If this error still exists
        after 15 minutes look at the end of the file /var/log/mirror/mirror.log to
        see the problem."""
        self.sysChkTxtDict["review mirror file"] = \
            """Click the View System Logs button and choose "mirror.log" in the result
        window. Scroll to the end of the  text window. Then take a photo of the window
        with the text and send to the Reneal team."""
        self.sysChkTxtDict["os partition full"] = \
            """The system partition "/" has only %s (%.1f%%) free."""
        self.sysChkTxtDict["clean os partition"] = \
            """The system partition is so full that System Check must try to remove
        some files. This should not affect the system, but remember to report 
        this has been done if you need to report a later problem to the Reneal team."""
        self.sysChkTxtDict["sysadmin home excessive problem"] = \
            """The sysadmin home directory size is %s. This is excess use and abuse
        of the sysadmin account and may cause server failure."""
        self.sysChkTxtDict["sysadmin home excessive action"] = \
            """The sysadmin home directory now has %s. This excess use and abuse
        of the sysadmin account for file storage MUST BE FIXED IMMEDIATELY!!
        You may make the system completely unusable if you do not remove all
        files that are not in the standard distribution for sysadmin. If these
        files are necessary for the school, move them into a personal directory.
        If not, delete them. The sysadmin account should be used >>only<< 
        for direct system administration work. No files for ANY other purpose
        should be stored in this account."""
        self.sysChkTxtDict["sysadmin home too large"] = \
            """The sysadmin home directory has %s. Please remove larger files 
        such as videos that you may have stored in this directory, then rerun
        SystemCheck to see if enough space is available. The sysadmin account 
        should be used >>only<< for direct system administration work. No files
        for any other purpose should be stored in this account."""
        self.sysChkTxtDict["sysadmin home cleaned"] = \
            """Some files have been removed from the sysadmin home directory to 
        try to create enough space in the "/" partition that the server can run 
        correctly. %s of files in Download, large files over 100MB, larger videos,
        and audio files have been deleted."""
        self.sysChkTxtDict["find other files to remove"] = \
            """The "/" directory is still too full for safe use. Please run the
        command "sudo du -sh /*" in a terminal window, take a photo of the text,
        and send to Reneal team. Be sure that ALL of the results of the command 
        are in the photo. You may need to make the terminal window larger to show all of the text."""
        self.sysChkTxtDict["root partition still too full"] = \
            """System Check failed to create enough free space in the "/" partition.
        It is still %d%% full."""
        self.sysChkTxtDict["cleared enough root partition space"] = \
            """System Check removed enough files to increase partition "/" free space.
        It is now %d%% full."""
        self.sysChkTxtDict["emergency clean client_home"] =\
            """The /client_home disk partition has only %s free space(%.1f%%). 
        This must be corrected. If /client_home becomes completely full teachers will 
        not be able to log in."""
        self.sysChkTxtDict["emergency cleaning teachers"] = \
            """Extremely large media files greater than %s will be removed from teachers 
        home directories to attempt to free space. These media files are probably 
        personal movies."""
        self.sysChkTxtDict["cleaning result"] = \
            """%s of files was removed from %s. It now has %s (%.1f%%) free space."""
        self.sysChkTxtDict["client_home partition full"] = \
            """The users partition "/client_home" has only %d GB free space."""
        self.sysChkTxtDict["client_home find files to remove"] = \
            """Remove some files from /client_home to free space before before teachers 
        will no longer be able log in.
        The 4 teachers using the most space are:
%s
        After deleting files run "df -h /client_home" to see how full the disk is."""
        self.sysChkTxtDict["teachers large trash"] = \
            """Remind teachers to regularly empty trash.
        These teachers had more than %dMB trash in their file trash bin:
%s
        Their trash was emptied by systemCheck."""
        self.sysChkTxtDict["emergency clean client_home_students"] = \
            """The students partition "/client_home_students" has only %s (%.1f%%) free space.
            Some files must be removed."""
        self.sysChkTxtDict["emergency cleaning client_home_students"] = \
            """Removing student personal media files like the Dashboard app 
            Cleanup Student Files does, but without any possiblity of marking some new files good.
            The app should be run more often to prevent this."""
        self.sysChkTxtDict["client_home_students cleaning result"] = \
            """Students files in /client_home_students were cleaned up. %d files were removed. 
            %s
            /client_home_students now has %s (%.1f%%) free space."""
        self.sysChkTxtDict["client_home_students partition full"] = \
            """The students partition "/client_home_students" has only %s (%.1f%%) free space."""
        self.sysChkTxtDict["run Cleanup Student Files app"] = \
            """Run the dashboard app "Cleanup Student Files" to remove students personal,
            not for school use files."""
        self.sysChkTxtDict["starting proxy cache rebuild"] = \
            """Starting rebuild of the squid proxy cache disk partition. This will
        take a minute to complete."""
        self.sysChkTxtDict["cache rebuild successful"] = \
            """The rebuild of the squid cache was successful. The squid proxy
        server is now running."""
        self.sysChkTxtDict["cache rebuild failed"] = \
            """The rebuild of the squid cache failed. The squid proxy
        server is still not running. Try rebooting the server."""
        self.sysChkTxtDict["squid needs further work"] = \
            """The squid proxy server is still not working. Try rebooting the server."""
        self.sysChkTxtDict["ltsp image missing"] = \
            """The ltsp client image file is missing. Client computers cannot boot
        until it is rebuilt."""
        self.sysChkTxtDict["starting ltsp image build"] = \
            """Starting rebuild of the LTSP client image file. This will take about
        two minutes to complete."""
        self.sysChkTxtDict["ltsp image ok"] = \
            """The LTSP client image file rebuild succeeded.
        Clients should now be able to reboot and run."""
        self.sysChkTxtDict["ltsp image rebuild failed"] = \
            "The LTSP client image rebuild failed. Clients will not boot."
        self.sysChkTxtDict["ltsp image rebuild manually"] = \
            """You will need to rebuild the LTSP client image by a direct command. Type the command
        "sudo ltsp-update-image amd64". If that fails, reboot, and choose the next backup copy to 
        boot from in the boot menu and contact the Reneal team."""
        self.sysChkTxtDict["ltsp image rebuild manually too full"] = \
           """The LTSP client image rebuild failed -- probably because there is no disk space.
        Run the command "sudo systemCleanup --force-student-logout" to attempt to get further
        disk space, then rerun systemCheck to try to rebuild the LTSP image again.
        If that fails, reboot, and choose the next backup copy to boot from in the boot menu.
        Contact the Reneal team."""
        self.sysChkTxtDict["load high"] = \
            """The CPU load was above %d%% for %1.0f minutes for the last %2.1f hours (%2.1f%%)."""
        self.sysChkTxtDict["load high action"] = \
            """To find the reason that the cpu load is high click the button "Task Viewer" on the
        System Management Applications panel and look at the top tasks for CPU > 50%. If it stays 
        high for more than 30 seconds consider using the button SuperUser Task Control to choose
        and stop it but be careful and read the warnings. 
        High loads may make the computer seem slow to users."""
        self.sysChkTxtDict["suggest rerun"] = """Please rerun System Check to confirm that the fixed
        problems are no longer reported."""
        self.sysChkTxtDict["suggest reboot"] = \
            """Some problems remain that might be fixed by rebooting the server.
        Please request all users to log off and shutdown all network clients before rebooting."""
        self.sysChkTxtDict["tbd"] = \
            """Not yet written. Message name: "%s" """

    def add_progress_texts(self):
        self.sysChkTxtDict["test start"] = "Starting tests"
        self.sysChkTxtDict["checking disks"] = "Starting disk checks"
        self.sysChkTxtDict["checking processes"] = "Starting process checks"
        self.sysChkTxtDict["checking interfaces"] = "Starting to check interfaces"
        self.sysChkTxtDict["hosts ping"] = "Starting to look for clients on network"
        self.sysChkTxtDict["start internet check"] = \
            """Starting internet tests. 
        If the internet is down these tests may take one or two minutes."""
        self.sysChkTxtDict["start internet ping check"] = \
            "Starting internet ping test"
        self.sysChkTxtDict["start internet name check"] = \
            "Starting internet name and address test"
        self.sysChkTxtDict["start internet browse check"] = \
            "Starting internet browsing test"
        self.sysChkTxtDict["start internet quality check"] = \
            """Starting internet quality test
            This may take a minute to perform."""
        self.sysChkTxtDict["checks complete"] = \
            "Completed Tests"
        self.sysChkTxtDict["starting analysis"] = \
            "Starting test result analysis"
        self.sysChkTxtDict["finished analysis"] = \
            "Completed test result analysis"

    # ----------------------------------------------------------------------
    def load_texts(self):
        self.add_disk_check_texts()
        self.add_filesystem_check_texts()
        self.add_interface_check_texts()
        self.add_internet_texts()
        self.add_other_texts()
        self.add_process_check_texts()
        self.add_progress_texts()

    # ----------------------------------------------------------------------
    def get_text(self, message_name):
        return self.sysChkTxtDict.get(message_name,
                """Invalid message id: '%s'.
                This is a program error and not the actual message.
                Please report this to the Superuser group.""" % message_name)


class Reporter:
    """
    A simple class to abstract the interface between a text command 
    reporter and a GUI based reporter. It supports output of the text version
    to a file (for logging, etc)rather than stdout
    """

    # ----------------------------------------------------------------------
    def __init__(self, config, gui_connector=None, report_progress_messages=False,
                 output_filename="", username="", line_width=70, verbose=False,
                 use_stringbuffer=False):
        if gui_connector:
            self.gui_reporter = GuiReporter(config, gui_connector, report_progress_messages,
                                            output_filename)
        else:
            self.gui_reporter = None
        self.config = config
        self.output_filename = output_filename
        self.username = username
        self.message_library = SysChkText()
        self.message_library.load_texts()
        self.output_file = None
        self.use_stringbuffer = use_stringbuffer
        self.report_stringbuffer = io.StringIO()
        self.log_stringbuffer = io.StringIO()
        self.action_messages = []
        self.suggest_reboot=False
        try:
            if self.output_filename:
                self.output_file = open(self.output_filename, 'a')
                sys.stdout = self.output_file
                sys.stderr = self.output_file
                self.write_header()
            elif self.use_stringbuffer:
                sys.stdout = self.report_stringbuffer
                sys.stderr = self.report_stringbuffer
            else:
                # reset if necessary
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stdout__
        except IOError as e:
            print("Unable to log to output_file '%s': %s" \
                  % (output_filename, e))
        self.problems_found = 0
        self.problems_fixed = 0
        self.further_action_required = False
        self.serious_problems = False
        self.txt_reporter = TextReporter(report_progress_messages,
                                         line_width, verbose, self.output_file)

    # ----------------------------------------------------------------------
    def get_report_info(self):
        return {"Report Stringbuffer": self.report_stringbuffer,
                "Problems Found": self.problems_found,
                "Problems Fixed": self.problems_fixed,
                "Further Action Required": self.further_action_required,
                "Number Further Actions": len(self.action_messages),
                "Serious Problem": self.serious_problems,
                "Reboot Required": self.suggest_reboot}

    # ----------------------------------------------------------------------
    def generate_text(self, message_name, values):
        try:
            message_text = self.message_library.get_text(message_name)
            if len(values) and (message_text.find('%') > -1):
                message_text = message_text % tuple(values)
        except Exception as e:
            message_text = str(e)
        return message_text

    # ----------------------------------------------------------------------
    def report_values(self, message_name, values, indent=8):
        if not (message_name and type(values) is list):
            return
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_values(message_text, indent_count=indent)
        if self.gui_reporter:
            self.gui_reporter.report_values(message_text, indent_count=indent)

    # ----------------------------------------------------------------------
    def adjust_problems_count(self, problems_found_change=0,
                              problems_fixed_change=0):
        self.problems_found += problems_found_change
        self.problems_fixed += problems_fixed_change

    # ----------------------------------------------------------------------
    def report_progress(self, message_name, values=[], level=1, reformat_text=True):
        if not (message_name and type(values) is list):
            return
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_progress(message_text, reformat_text, level)
        if self.gui_reporter:
            self.gui_reporter.report_progress(message_text, reformat_text, level)

    # ----------------------------------------------------------------------
    def report_problem(self, message_name, values=[], reformat_text=True,
                       increment_problem_count=True, html_text=""):
        """
        """
        if not (message_name and type(values) is list):
            return
        if increment_problem_count:
            self.problems_found += 1
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_problem(message_text, reformat_text)
        if self.gui_reporter:
            if html_text:
                self.gui_reporter.report_problem(html_text, False)
            else:
                self.gui_reporter.report_problem(message_text, reformat_text)

    # ----------------------------------------------------------------------
    def report_requires_user_action_problem(self, error_message_name="",  values=[],
                                            action_message_name="tbd",
                                            action_values=[],
                                            reformat_text=True,
                                            increment_problem_count=True, html_text="",
                                            suggest_reboot=False):
        """
        """
        if increment_problem_count:
            self.problems_found += 1
        self.further_action_required = True
        if error_message_name:
            error_message_text = self.generate_text(error_message_name, values)
        else:
            error_message_text = ""
        if action_message_name == "tbd":
            action_values = [error_message_name]
        if action_message_name:
            self.action_messages.append(self.generate_text(action_message_name,
                                                           action_values))
        if error_message_text:
            self.txt_reporter.report_problem(error_message_text, reformat_text)
        if self.gui_reporter and error_message_text:
            if html_text:
                self.gui_reporter.report_problem(html_text, False)
            else:
                self.gui_reporter.report_problem(error_message_text, reformat_text)
        self.suggest_reboot = suggest_reboot

    # ----------------------------------------------------------------------
    def report_fixable_problem(self, message_name, values=[], reformat_text=True):
        """
        """
        if not (message_name and type(values) is list):
            return
        self.problems_found += 1
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_fixable_problem(message_text, reformat_text)
        if self.gui_reporter:
            self.gui_reporter.report_fixable_problem(message_text, reformat_text)

    # ----------------------------------------------------------------------
    def report_starting_fix(self, message_name, values=[],
                            reformat_text=True):
        """
        """
        if not (message_name and type(values) is list):
            return
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_starting_fix(message_text, reformat_text)
        if self.gui_reporter:
            self.gui_reporter.report_starting_fix(message_text, reformat_text)

    # ----------------------------------------------------------------------
    def report_fix_result(self, message_name, values=[],
                          reformat_text=True, fixed=True):
        """
        """
        if not (message_name and type(values) is list):
            return
        if fixed:
            self.problems_fixed += 1
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_fix_result(message_text, reformat_text)
        if self.gui_reporter:
            self.gui_reporter.report_fix_result(message_text, reformat_text, fixed)

    # ----------------------------------------------------------------------
    def report_serious_problem(self, message_name, values=[], reformat_text=True):
        """
        This is a serious problem that requires the attention
        of the user. It should be presented in the most obvious
        manner and will show up in the final results.
        """
        if not (message_name and type(values) is list):
            return
        self.problems_found += 1
        self.serious_problems = True
        message_text = self.generate_text(message_name, values)
        self.txt_reporter.report_serious_problem(message_text, reformat_text)
        if self.gui_reporter:
            self.gui_reporter.report_serious_problem(message_text, reformat_text)

    # ----------------------------------------------------------------------
    def show_percent_complete(self, percent_complete):
        """
        This is used for the progress bar in the GUI. It
        does nothing with a text interface
        """
        self.txt_reporter.show_percent_complete(percent_complete)
        if self.gui_reporter:
            self.gui_reporter.show_percent_complete(percent_complete)

    # ----------------------------------------------------------------------
    def generate_suggest_reboot_message(self, suggest_reboot=False, reason=""):
        restart_message = ""
        if suggest_reboot:
            restart_message = self.generate_text("suggest reboot", [reason])
        return restart_message

    # ----------------------------------------------------------------------
    def report_summary(self, problem_reported, suggest_rebooting):
        num_actions_required = len(self.action_messages)
        self.suggest_reboot = suggest_rebooting
        suggest_reboot_message = self.generate_suggest_reboot_message(suggest_rebooting)
        if self.config.get_value("problems_only"):
            self.action_messages = []
        self.txt_reporter.report_summary(problem_reported, suggest_reboot_message,
                                         self.problems_found, self.problems_fixed,
                                         self.action_messages, num_actions_required)
        if self.gui_reporter:
            self.gui_reporter.report_summary(problem_reported, suggest_reboot_message,
                                             self.problems_found, self.problems_fixed,
                                             self.action_messages, num_actions_required)
    # ----------------------------------------------------------------------
    def write_header(self):
        """
        Write a brief header to log start of run time. This is done only it the output
        is to a file.
        """
        print("--------------------- Starting System Check at %s ---------------------\n" \
              % time.ctime())

    def write_tail(self):
        """
        Write a brief tail to log end of run time. This is done only it the output
        is to a file.
        """
        print("\n--------------------- Completed System Check at %s ---------------------\n" \
              % time.ctime())

    def cleanup(self):
        """
        Do final actions to close files, etc
        """
        if self.output_file:
            self.write_tail()
            self.output_file.close()
            if self.gui_reporter:
                os.chown(self.output_filename, pwd.getpwnam(self.username).pw_uid,
                         pwd.getpwnam(self.username).pw_gid)

class TextReporter:
    def __init__(self, report_progress_messages=False, line_width=70,
                 verbose=False, output_file=None):
        self.report_progress_messages = report_progress_messages
        self.line_width = line_width
        self.verbose = verbose
        self.textwrapper = textwrap.TextWrapper()
        self.output_file = output_file

    # ----------------------------------------------------------------------
    def generate_output_text(self, prefix, message_text, subsequent_indent='  ',
                             reformat_text=True):
        """
        """
        full_text = prefix + message_text
        if reformat_text:
            self.textwrapper.subsequent_indent = subsequent_indent
            # remove extra spaces
            full_text = re.sub(r'\s+', ' ', full_text)
            full_text = self.textwrapper.fill(full_text)
        return full_text

    # ----------------------------------------------------------------------
    def report_values(self, message_text, prefix="- ", indent_count=8):
        print(self.generate_output_text((' ' * indent_count) + prefix, message_text, '', False))

    # ----------------------------------------------------------------------
    def report_progress(self, message_text, reformat_text=True, level=1):
        if level == 0:
            prefix = "---- "
        elif level == 1:
            prefix = " ---- "
        else:
            prefix = "  ---- "
        if self.report_progress_messages:
            print(self.generate_output_text(prefix, message_text, '    ', reformat_text))

    # ----------------------------------------------------------------------
    def report_problem(self, message_text, reformat_text=False):
        """
        """
        print()
        print(self.generate_output_text("Problem> ", message_text, '        ', reformat_text))

    # ----------------------------------------------------------------------
    # def report_requires_user_action_problem(self, message_text, reformat_text):
    #     """
    #     """
    #     text = self.generate_output_text("  ", message_text, '    ', reformat_text)
    #     self.user_actions.append(text)

    # ----------------------------------------------------------------------
    def report_fixable_problem(self, message_text, reformat_text):
        """
        """
        print()
        print(self.generate_output_text("Will attempt to fix this problem- ", message_text,
                                        '    ', reformat_text))
        # ----------------------------------------------------------------------

    def report_starting_fix(self, message_text, reformat_text):
        """
        """
        print(self.generate_output_text("   Starting fix: ", message_text, '      ',
                                        reformat_text))

    # ----------------------------------------------------------------------
    def report_fix_result(self, message_text, reformat_text):
        """
        """
        print(self.generate_output_text("   Fix result: ", message_text, '      ',
                                        reformat_text))

    # ----------------------------------------------------------------------
    def report_serious_problem(self, message_text, reformat_text):
        """
        This is a serious problem that requires the attention
        of the user. It should be presented in the most obvious
        manner and will show up in the final results.
        """
        print()
        print("<<<< >>>>")
        print(self.generate_output_text("Serious Problem>>> ", message_text, '        ', reformat_text))

    # ----------------------------------------------------------------------
    def show_percent_complete(self, percent_complete):
        """
        This is used for the progress bar in the GUI. It
        does nothing with a text interface
        """
        pass

    # ----------------------------------------------------------------------
    def suggest_reboot(self, message_text):
        """
        """
        print(self.generate_output_text("Restart Server: ", message_text))

    def suggest_rerun(self, message_text):
        """
        """
        self.generate_output_text("", message_text)

    def generate_problems_count_string(self, problems_found, problems_fixed, num_actions_required):
        if problems_found:
            return ("-- %d %s found. %d %s fixed, %d %s %s action."
                    % (problems_found, pluralize("problem", problems_found),
                       problems_fixed, pluralize("problem", problems_fixed),
                       num_actions_required, pluralize("problem", num_actions_required),
                       pluralize("need", num_actions_required, inverse=True)))
        else:
            return "No problems found."

    def report_summary(self, problem_reported, suggest_reboot_message,
                       problems_found, problems_fixed, actions_required, num_actions_required):
        if actions_required:
            print()
            print("***** Do this next and then rerun System Check ******")
            for action in actions_required:
                print("Task> ",action)
                print()
        print(self.generate_problems_count_string(problems_found, problems_fixed,
                                                  num_actions_required))
        if problems_fixed > 0 and num_actions_required == 0:
            self.suggest_rerun("Please rerun System Check to confirm the fixes.")
        print("System Check completed.")


class GuiReporter:
    """
    """

    def __init__(self, config, gui_connector, report_progress_messages, output_filename):
        self.config = config
        self.gui_connector = gui_connector
        self.report_progress_messages = report_progress_messages
        self.output_filename = output_filename

    # ----------------------------------------------------------------------
    def generate_output_text(self, prefix, message_text, subsequent_indent='  ',
                             reformat_text=True):
        """
        """
        return prefix + message_text

    # ----------------------------------------------------------------------
    def insert_information_text(self, problem_type, color, message_text, emphasized=False):
        """
        """
        self.gui_connector.insert_information_text(problem_type, message_text, emphasized)

    # ----------------------------------------------------------------------
    def report_progress(self, message_text, reformat_text=True, level=1):
        """
        """
        if level == 0:
            prefix = "---- "
        elif level == 1:
            prefix = "  ---- "
        else:
            prefix = "    ---- "
        if self.report_progress_messages:
            self.gui_connector.insert_progress_text(self.generate_output_text(prefix,
                                                          message_text, '    ', reformat_text))

    # ----------------------------------------------------------------------
    def report_problem(self, message_text, values=[], unused=False):
        self.gui_connector.insert_information_text("problem", 'Problem', message_text)

    # ----------------------------------------------------------------------
    # def report_requires_user_action_problem(self, message_text, values = [], unused=False):
    #     html_text = self.gui_connector.generate_information_text("requires user action",
    #                                                "User Action Needed", message_text)
    #     self.user_actions.append(html_text)
    # ----------------------------------------------------------------------
    def report_fixable_problem(self, message_text, unused=False):
        self.gui_connector.insert_information_text("fixable problem",
                                                   "Will attempt to fix this problem", message_text)

    # ----------------------------------------------------------------------
    def report_starting_fix(self, message_text, unused=False):
        self.gui_connector.insert_information_text("fixing problem", "  Starting fix",
                                                   message_text)

    # ----------------------------------------------------------------------
    def report_fix_result(self, message_text, reformat_text=False, fixed=True):
        if fixed:
            self.gui_connector.insert_information_text("fix result good",
                                                       "  Fix Succeeded", message_text)
        else:
            self.gui_connector.insert_information_text("fix result bad", "  Fix Failed",
                                                       message_text)

    # ----------------------------------------------------------------------
    def report_serious_problem(self, message_text, unused=False):
        """
        This is a serious problem that requires the attention
        of the user. It should be presented in the most obvious
        manner and will show up in the final results.
        """
        self.gui_connector.insert_information_text("serious problem", "Serious Problem",
                                                   message_text, emphasized=True)

    # ----------------------------------------------------------------------
    def report_values(self, message_text, prefix="", indent_count=8):
        self.gui_connector.insert_information_text("values", "Information", message_text)

    # ----------------------------------------------------------------------
    def show_percent_complete(self, percent_complete):
        """
        This is used for the progress bar in the GUI.
        """
        self.gui_connector.show_percent_complete(percent_complete)

    # ----------------------------------------------------------------------
    def report_summary(self, problem_reported, suggest_reboot_message,
                       problems_found, problems_fixed, actions_required,
                       num_actions_required):
        if actions_required:
            self.gui_connector.insert_simple_text("requires user action",
                                                  "***** Do this next and then rerun System Check ******")
            for action in actions_required:
                self.gui_connector.insert_information_text("requires user action", "Task", action)
        if problems_found:
            summary_text = "-- %d %s found. %d %s fixed, %d %s %s action." \
                           % (problems_found, pluralize("problem", problems_found),
                              problems_fixed, pluralize("problem", problems_fixed),
                              num_actions_required, pluralize("problem", num_actions_required),
                              pluralize("need", num_actions_required, inverse=True))
        else:
            summary_text = "No problems found."
        entry_type = "no problems"
        if problems_found:
            if problems_found == problems_fixed:
                entry_type = "fix result good"
            else:
                entry_type = "problem"
        self.gui_connector.insert_simple_text(entry_type, summary_text, True)
        if suggest_reboot_message:
            self.suggest_reboot(suggest_reboot_message)
        elif problems_fixed > 0 and num_actions_required == 0:
            self.suggest_rerun()
        self.gui_connector.insert_simple_text("information", "System Check completed.",
                                              True)

    # ----------------------------------------------------------------------
    def problems_fixed(self):
        return self.problems_fixed()

    # ----------------------------------------------------------------------
    def suggest_rerun(self, message_text=""):
        """
        """
        self.gui_connector.insert_simple_text("requires user action",
                                              "Please rerun System Check to confirm the fixes.")

    def suggest_reboot(self, message_text):
        """
        """
        self.gui_connector.insert_simple_text("requires user action",
                                              message_text)


# ----------------------------------------------------------------------
def pluralize(word, number, plural_suffix='s', inverse=False):
    """
    A simple function to generate the plural from the singular form of
    the word by adding the plural_suffix at the end if the number is
    > 1
    """
    plural = number > 1 or number == 0
    if (plural and not inverse) or (not plural and inverse):
        word += plural_suffix
    return word
