#! /usr/bin/python3

__author__ = 'master'
"""
Monitor system activity and load for the server and client.
This activity includes the list of users with further indication of
sleep (screensaver). All data is recorded in a SQL database.
This program is meant to run as a continuous background daemon
started by systemd.
"""

import MySQLdb
import atexit
import os
import re
import subprocess
import sys
import time
import backgroundFunctions
import localFunctions

PROGRAM_NAME = "SystemMonitor"
STUDENT_SCREENSAVER = "epicycle"
TEACHER_SCREENSAVER = "penrose"
STUDENT_SIGNIN = "studentSignIn"
SAMPLE_TIME = 60
ERROR_LOGFILE = "/var/log/sysmonitor/error.log"
INFO_LOGFILE = "/var/log/sysmonitor/info.log"
CLIENT_COMPUTER_DATA_DIRECTORY = "/client_home/share/.client_info"
InfoLogger = None
ErrorLogger = None
Systemd = None
VERSION = 1.1


# --------------------------------------------------------------------

class DbWriter:
    """
    Generalize all db functions for consistency and flexibility.
    """

    def __init__(self, db_name, password, user_name, host="localhost"):
        self.db_name = db_name
        self.password = password
        self.user_name = user_name
        self.host = host
        self.time = 0
        self.connector = None
        self.cursor = None

    def connect_to_database(self):
        """
        Create the connection to the database. This may be called more than once
        if the connection is lost
        :return:
        """
        global Systemd
        try:
            self.connector = MySQLdb.connect(db=self.db_name, passwd=self.password,
                                             user=self.user_name, host=self.host)
            self.cursor = self.connector.cursor(MySQLdb.cursors.DictCursor)
            # Error: should not be zeroed here. Line only left in as marker for
            # fix for existing systems
            # self.time = 0
        except MySQLdb.DatabaseError as edb:
            ErrorLogger.critical(
                "Could not connect to database: %s \nWILL EXIT NOW." % edb)
            # If we can't open the database we can't do anything -- so quit
            sys.exit(-1)

    def close_connection(self):
        try:
            if self.cursor:
                self.cursor.close()
            if self.connector:
                self.connector.close()
        except MySQLdb.Error as edb:
            ErrorLogger.error("Failed to close db connection: %s" % edb)

    def set_time(self):
        """
        Set the time for the start of each loop to compute the actual time that the
        recording loop took
        :return:
        """
        self.time = time.time()
        # only for tracking - run from command line if this is uncommented
        # print self.time

    def get_single_value(self, query, caller=""):
        try:
            self.cursor.execute(query)
            return self.cursor.fetchone()
        except MySQLdb.Error as edb:
            ErrorLogger.error(
                "%s: select query %s failed with error %s" % (
                    caller, query, edb))
            raise

    def insert_record(self, query, caller=""):
        try:
            self.connector.query(query)
            self.connector.commit()
        except MySQLdb.Error as edb:
            ErrorLogger.error(
                "%s: insert query %s failed with error %s" % (
                    caller, query, edb))
            raise

    def update_record(self, query, caller=""):
        try:
            self.connector.query(query)
        except MySQLdb.Error as edb:
            ErrorLogger.error(
                "%s: update query %s failed with error %s" % (
                    caller, query, edb))
            raise

    def add_server_memory(self, server_memory):
        """
        Record server memory usage
        :param server_memory: ServerMemory object
        :return:
        """
        query = "INSERT INTO MemoryUse (Time, MbytesTotal, MbytesUsed, MbytesFree, " + \
                "MbytesCache, MbytesAvailable, MbytesSwapUsed, MbytesSwapFree)" + \
                "VALUES (%d,%s,%s,%s,%s,%s,%s,%s);" \
                % (self.time,
                   server_memory["MbytesTotal"],
                   server_memory["MbytesUsed"],
                   server_memory["MbytesFree"],
                   server_memory["MbytesCache"],
                   server_memory["MbytesAvailable"],
                   server_memory["MbytesSwapUsed"],
                   server_memory["MbytesSwapFree"])
        self.insert_record(query, "add_server_memory")

    def add_server_cpu(self, server_cpu):
        """
        Record information about CPU usage since last sample
        :param server_cpu: ServerCpu object
        :return:
        """
        query = "INSERT INTO CpuUse ( Time, PercentUserTime, PercentSystemTime," + \
                "PercentNiceTime, PercentIoWait, PercentFreeTime) VALUES (%d,%f,%f,%f,%f,%f);" \
                % (
                    self.time,
                    server_cpu["PercentUserTime"],
                    server_cpu["PercentSystemTime"],
                    server_cpu["PercentNiceTime"],
                    server_cpu["PercentIoWait"],
                    server_cpu["PercentFreeTime"])
        self.insert_record(query, "add_server_cpu")

    def add_logged_in_users(self, users):
        """
        Record information about all logged in users.
        The users data is in a dictionary keyed by user name with
        active status as as value
        One row per user
        :param users: list of users
        :return null:
        """
        query = ""
        try:
            for user in users:
                query = "INSERT INTO UsersLoggedIn (Time, UserId, UserActive)" + \
                        " VALUES (%d, %d, %d);" % (self.time, user[0], user[1])
                self.connector.query(query)
            self.connector.commit()
        except MySQLdb.Error as e:
            ErrorLogger.error(
                "Failed to add logged in user: query %s failed with error %s" % (
                    query, e))
            raise

    def add_user(self, user_name, uid, user_type):
        """
        create a record in the database user table
        :param user_name:
        :param uid:
        :param user_type:
        :return:
        """
        query = "INSERT INTO Users (UserName, UserType, UID) " + \
                "VALUES ('%s', '%s', %d);" % (user_name, user_type, uid)
        self.insert_record(query, "add_user")

    def get_user_by_value_name(self, value_name, value):
        """
        Get the table index for the user by name
        :param value_name: ["id","name","account_type","uid"]
        :param value
        :return user index:
        """
        if value_name == "Index":
            query = "SELECT * FROM Users WHERE Users.Index = %d;" % value
        else:
            query = "SELECT * FROM Users WHERE %s ='%s';" % (value_name, value)
        return self.get_single_value(query, "get_user_by_value_name")

    def add_client_computer(self, mac_address, memory, description):
        """
        Create record to describe a client computer
        :param mac_address:
        :param memory:
        :param description:
        :return:
        """
        query = "INSERT INTO ClientComputers (" \
                "MacAddress,CurrentData,DataUpdateTime," + \
                "Memory, Description) VALUES ('%s', %d, %d, %d, '%s');" \
                % (mac_address, 1, int(self.time), int(memory), description)
        self.insert_record(query, "add_client_computer")

    def get_client_computer(self, mac_address):
        """
        Get the table index for the user by name
        :param  mac_address
        :return user index:
        """
        query = "SELECT * FROM ClientComputers WHERE MacAddress ='%s' AND CurrentData = 1;" \
                % mac_address
        return self.get_single_value(query, "get_client_computer")

    def get_client_computer_from_id(self, client_computer_id):
        """

        :param client_computer_id:
        :return:
        """
        query = "SELECT * FROM ClientComputers WHERE ClientComputers.Index = %d;" % client_computer_id
        return self.get_single_value(query, "get_client_computer_from_id")

    def mark_client_computer_obsolete(self, client_computer_id):
        """
        :param client_computer_id:
        :return:
        """
        query = "UPDATE ClientComputers SET CurrentData = 0 WHERE ClientComputers.Index = %d;" \
                % client_computer_id
        self.update_record(query, "mark_client_computer_obsolete")

    def add_clients(self, clients):
        """
        Record information about memory use in each active client
        One row per client
        :param clients  list of client computer
        :return null:
        """
        query = ""
        try:
            for client in clients:
                value_dict = client.get_data()
                query = "INSERT INTO ClientResourceUse (Time, ClientComputerId, " + \
                        "MbytesAvailable, CpuIdle) VALUES (%d, %d, %f, %f);" \
                        % (self.time, value_dict["ClientComputerId"],
                           float(value_dict["memory_available"]),
                           float(value_dict["cpu_idle"]))
                self.connector.query(query)
            if clients:
                self.connector.commit()
        except MySQLdb.DatabaseError as edb:
            ErrorLogger.error(
                "Failed to add active client info: query %s failed with error %s" % (
                    query, edb))
            raise

    def add_summary(self, summary_data):
        """

        :param summary_data:
        :return:
        """
        query = "INSERT INTO SummaryData (Time, UserCount, ActiveUserCount, StudentCount," \
                "ActiveStudentCount, TeacherCount, ActiveTeacherCount, ClientComputerCount) " \
                "VALUES (%d, %d, %d, %d, %d, %d, %d, %d)" \
                % (self.time, summary_data["UserCount"],
                   summary_data["ActiveUserCount"],
                   summary_data["StudentCount"],
                   summary_data["ActiveStudentCount"],
                   summary_data["TeacherCount"],
                   summary_data["ActiveTeacherCount"],
                   summary_data["ClientComputerCount"])
        self.insert_record(query, "add_summary")


# --------------------------------------------------------------------

class UserAccountManager:
    """
    The class that creates entries and queries the users database table.
    """

    def __init__(self, db_writer):
        self.db_writer = db_writer

    def create_user(self, user_name):
        """
        create a user in the user database table
        :param user_name:
        :return:
        """
        try:
            # determine user type and encode for database
            command = "/usr/bin/id -u " + user_name
            uid = run_command(command, result_as_list=False,
                              timeout=3.0, reraise_error=True)
            command = "/usr/bin/groups " + user_name
            output = run_command(command, result_as_list=False,
                                 timeout=3.0, reraise_error=True)
            groups = output.split(":")[1]
            if groups.count("sudo"):
                # admin users are in superusers group but might be
                # in others so look for them first
                user_type = "Admin"
            elif groups.count("teacher"):
                # all teachers are in teacher group
                user_type = "Teacher"
            elif groups.count("student"):
                # students are only in student group
                user_type = "Student"
            else:
                user_type = "Other"
            self.db_writer.add_user(user_name, int(uid), user_type)
        except subprocess.CalledProcessError as err_val:
            ErrorLogger.error("create_user failed: %s"
                              % localFunctions.generate_exception_string(err_val))

    def get_user_index(self, user_name):
        """
        Query the User table in the database to get the table index
        for the named user. If the entry does not exist then create it
        and query again. This is special because there is the strict
        one to one mapping between user name and user index that is used
        create a user record if it does not exist
        :param user_name:
        :return:
        """
        try:
            user = self.db_writer.get_user_by_value_name("UserName", user_name)
            if not user:
                self.create_user(user_name)
                user = self.db_writer.get_user_by_value_name("UserName",
                                                             user_name)
            # first element in tuple in a list
            return user.get("Index", 0)
        except Exception as err_val:
            ErrorLogger.error("get_user_index failed: %s"
                              % localFunctions.generate_exception_string(err_val))
            return 0

    def get_user_record_by_value_name(self, value_name, value):
        """
        Return a full dictionary of values for a user given
         the search parameter of "value_name" with the value "value"
        :param value_name:
        :param value:
        :return user_dict:
        """
        try:
            user = self.db_writer.get_user_by_value_name(value_name, value)
        except Exception as err_val:
            ErrorLogger.error("get_user_record_by_value_name failed: %s"
                              % localFunctions.generate_exception_string(err_val))
            user = None
        return user


# --------------------------------------------------------------------

class LoggedInUserData:
    """
    The primary class that runs the shell commands and extracts the
    information.
    """

    def __init__(self, user_account_manager):
        self.user_account_manager = user_account_manager
        self.users_dict = {}
        self.users_list = []
        # this should always be empty

    def get_user_names(self):
        """
        Call all shell commands to get the raw data.
        """
        try:
            # build dictionary of all users known to server
            # dictionary avoids multiple listings for a users
            for line in run_command("/usr/bin/who --user", result_as_list=True):
                self.users_dict[line.split()[0]] = True
        except subprocess.CalledProcessError as e:
            ErrorLogger.error("get_user_names failed: %s" % e)

    def get_user_status(self):
        """
        Get a list of processes and check for special processs that indicate that
        the user is not active. If found in a line mark the user as
        not active in the user dictionary.
        """
        global STUDENT_SCREENSAVER, TEACHER_SCREENSAVER, STUDENT_SIGNIN
        try:
            for user_name in self.users_dict.keys():
                command = "/bin/ps -f -u " + user_name
                return_value = run_command(command, result_as_list=True,
                                           timeout=3.0)
                for line in return_value:
                    if line.count(STUDENT_SCREENSAVER) or \
                            line.count(TEACHER_SCREENSAVER) or \
                            line.count(STUDENT_SIGNIN):
                        self.users_dict[user_name] = False
        except subprocess.CalledProcessError as e:
            ErrorLogger.error("get_user_status failed: %s" % e)

    def generate_data(self):
        """
        :return: Null
        """
        self.get_user_names()
        self.get_user_status()
        for name in self.users_dict.keys():
            user_id = self.user_account_manager.get_user_index(name)
            self.users_list.append((user_id, self.users_dict[name]))
        return self.users_list

    def get_data(self):
        return self.users_list


# --------------------------------------------------------------------

class ClientComputer:
    """
    The primary class for the client computer table.
    """

    def __init__(self, db_writer, mac_address, data):
        """
        :param db_writer
        :param mac_address - unique factor for each computer
        :param data
        :return:
        """
        self.data = data
        self.mac_address = mac_address
        self.memory_size = data["system_memory"]
        self.db_writer = db_writer
        self.id = None

    def create_database_record(self):
        """
        Get the further information necessary and create a record in the
        ClientComputer table
        :return:
        """
        self.db_writer.add_client_computer(self.mac_address,
                                           self.memory_size,
                                           self.data["cpu_model"])

    def get_memory_size_from_database(self):
        memory_size_from_database = 0
        if self.id:
            database_record = \
                self.db_writer.get_client_computer_from_id(self.id)
            if database_record:
                memory_size_from_database = database_record["Memory"]
        return int(memory_size_from_database)

    def get_client_computer_id(self):
        """

        :return: client id if found, 0 if not
        """
        client_id = None
        database_record = \
            self.db_writer.get_client_computer(self.mac_address)
        if database_record:
            client_id = database_record["Index"]
        return client_id

    def get_index(self):
        """
        Get the database index for the record of this computer. This will
        create a database record if it does not yet exist. If it does exist
        but the amount of system memory has changed then create a new record and
        mark the old as obsolete
        """
        try:
            self.id = self.get_client_computer_id()
            if int(self.memory_size) != self.get_memory_size_from_database():
                if self.id:
                    # The memory size has changed since the record was created so
                    # mark current record obsolete
                    self.db_writer.mark_client_computer_obsolete(self.id)
                self.create_database_record()
                self.id = self.get_client_computer_id()
        except Exception as err_val:
            ErrorLogger.error("ClientComputer.get_index failed: %s"
                              % localFunctions.generate_exception_string(err_val))
            self.id = 0
        return self.id


# --------------------------------------------------------------------

class ClientComputerResourceUse:
    """
    Information about a single client computer Each client is a separate
    object
    """

    def __init__(self, db_writer, mac_address, filename):
        """
        Create a client computer object with the ipaddress and macaddress
        already known
        :param mac_address:
        :param filename:
        :return:
        """
        self.db_writer = db_writer
        self.mac_address = mac_address
        self.filename = filename
        self.index = 0
        self.data = {"mac_address": mac_address}

    def read_client_file(self):
        """
        Read the file written by the client that has performance and descriptive
        data. The filename is the mac address of the client. This function
        reads the file, extracts the recorded values,
        :return:
        """
        try:
            f = open(self.filename, "r")
            content = f.read()
            f.close()
            self.data["cpu_model"] = re.findall(r'Model name:\s+([^\n]+)',
                                                content)[0]
            self.data["system_memory"] = re.findall(r'Mem:\s+(\d+)', content)[0]
            self.data["memory_available"] = re.findall(
                r'Mem:\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)', content)[0]
            self.data["cpu_idle"] = re.findall(r'ni,\s*([\d\.]+)\s+id,',
                                               content)[1]
        except IOError:
            self.data = None
            pass

    def get_computer_database_index(self):
        """
        Get the record index for the computer with the mac address
        This may cascade to create a record for a computer never seen before
        or a new record if the memory has changed in the computer
        :return:
        """
        computer = ClientComputer(self.db_writer, self.mac_address,
                                  self.data)
        if computer:
            self.data["ClientComputerId"] = computer.get_index()
        else:
            self.data = None

    def generate_data(self):
        """
        :return:
        """
        self.read_client_file()
        if self.data:
            self.get_computer_database_index()
        return self.data

    def get_data(self):
        return self.data


# --------------------------------------------------------------------

class ClientComputerData:
    """
    Find all client computers and check the memory usage.
    """

    def __init__(self, db_writer):
        self.db_writer = db_writer
        self.clients = []

    def process_client_files(self):
        """
        Read the files written by client computers that contain performance
        information. Once the file is read, remove it to prevent rereading
        a file. The client writes the file at a shorter interval than this
        read is performed. Thus an up-to-date file should always be available
        as long as the client host is running and the lack of a file for a
        client means that it is not running.
        :return:
        """
        global CLIENT_COMPUTER_DATA_DIRECTORY
        for filename in os.listdir(CLIENT_COMPUTER_DATA_DIRECTORY):
            full_filename = os.path.join(CLIENT_COMPUTER_DATA_DIRECTORY,
                                         filename)
            client_macaddr = self.get_mac_address(full_filename)
            if client_macaddr:
                client_data_reader = ClientComputerResourceUse(self.db_writer,
                                                               client_macaddr,
                                                               full_filename)
                if client_data_reader.generate_data():
                    self.clients.append(client_data_reader)
                # always delete file to assure that stale data is not recorded
                try:
                    os.remove(full_filename)
                except IOError:
                    pass

    @staticmethod
    def get_mac_address(filename):
        """
        Confirm that file exists, has the correct form of name, and is current.
        If so, return the mac address of the writer in a guranteed correct form
        :return:
        """
        macaddr = None
        if os.path.exists(filename):
            age = time.time() - os.path.getmtime(filename)
            short_filename = os.path.basename(filename)
            match = re.match(
                r'([\da-f]{2}):([\da-f]{2}):([\da-f]{2}):([\da-f]{2}):([\da-f]{2}):([\da-f]{2})\.sysinfo$',
                short_filename.lower())
            if abs(age) < float(SAMPLE_TIME) and match:
                macaddr = ":".join(match.groups())
        return macaddr

    def generate_data(self):
        self.process_client_files()
        return self.clients

    def get_data(self):
        return self.clients


# --------------------------------------------------------------------

class SummaryData:
    """
    A simple class to collect and write summary count values to make some report
    generation easier.
    """

    def __init__(self, user_account_manager, users_list, clients_list):
        self.return_values = \
            {"UserCount": 0, "ActiveUserCount": 0, "StudentCount": 0,
             "ActiveStudentCount": 0, "TeacherCount": 0,
             "ActiveTeacherCount": 0,
             "ClientComputerCount": 0}
        self.user_account_manager = user_account_manager
        self.users_list = users_list
        self.clients_list = clients_list

    def process_user_list(self):
        self.return_values["UserCount"] = len(self.users_list)
        for user in self.users_list:
            try:
                if user[1]:
                    self.return_values["ActiveUserCount"] += 1
                user_info = \
                    self.user_account_manager.get_user_record_by_value_name(
                        "Index", user[0])
                if user_info:
                    if user_info["UserType"] == "Student":
                        self.return_values["StudentCount"] += 1
                        if user[1]:
                            self.return_values["ActiveStudentCount"] += 1
                    elif user_info["UserType"] == "Teacher":
                        self.return_values["TeacherCount"] += 1
                        if user[1]:
                            self.return_values["ActiveTeacherCount"] += 1
            except IndexError as err_val:
                # handle empty user entry
                ErrorLogger.warning(
                    "process_user_list did not log all data to the summary user %s: %s"
                    % (user, localFunctions.generate_exception_string(err_val)))
                pass

    def process_client_computers(self):
        """
        Get the number of client computers active. The result from the ping and
        the number of client files are compared in case the writer in the celit
        hase failed or the ping has not found all active hosts.
        :return:
        """
        command_result = run_command(
            "/usr/bin/fping  -A -a -r 0 -i 1 -g 192.168.2.0/24 2>/dev/null",
            result_as_list=True, reraise_error=False)
        self.return_values["ClientComputerCount"] = \
            max(len(command_result) - 1, len(self.clients_list))

    def generate_data(self):
        self.process_user_list()
        self.process_client_computers()
        return self.return_values

    def get_data(self):
        return self.return_values


# --------------------------------------------------------------------

class ServerMemoryData:
    """
    """

    def __init__(self):
        self.memory_data = \
            {
                "MbytesTotal": 0,
                "MbytesUsed": 0,
                "MbytesFree": 0,
                "MbytesCache": 0,
                "MbytesAvailable": 0,
                "MbytesSwapUsed": 0,
                "MbytesSwapFree": 0
            }

    def generate_data(self):
        """
        Extract all required values from the command "free" on the server
        :return: full memory data
        """
        try:
            command_result = run_command("free -m", result_as_list=False,
                                         reraise_error=True,
                                         timeout=1)
            values = re.findall(
                r'(\d+)', command_result, re.MULTILINE)
            # array indexes com from format of the command 'free' output
            self.memory_data = {
                "MbytesTotal": values[0],
                "MbytesUsed": values[1],
                "MbytesFree": values[2],
                "MbytesCache": values[4],
                "MbytesAvailable": values[5],
                "MbytesSwapUsed": values[7],
                "MbytesSwapFree": values[8]
            }
        except subprocess.CalledProcessError as err_val:
            ErrorLogger.error(
                "Server 'free' memory check command failed: %s"
                % localFunctions.generate_exception_string(err_val))
        return self.memory_data

    def get_data(self):
        return self.memory_data


# --------------------------------------------------------------------

class ServerCpuData:
    """
    """

    def __init__(self):
        self.cpu_data = \
            {"PercentUserTime": 0.0,
             "PercentSystemTime": 0.0,
             "PercentNiceTime": 0.0,
             "PercentIoWait": 0.0,
             "PercentFreeTime": 0.0}

    def generate_data(self, mp_process_output):
        try:
            values = re.findall(r'\s\s(\d+\.\d+)',
                                str(mp_process_output), re.MULTILINE)
            if values:
                self.cpu_data = \
                    {"PercentUserTime": float(values[10]),
                     "PercentSystemTime": float(values[12]),
                     "PercentNiceTime": float(values[11]),
                     "PercentIoWait": float(values[13]),
                     "PercentFreeTime": float(values[19])}
        except Exception as err_val:
            ErrorLogger.error("ServerCpuData generate_data failed: %s"
                              % localFunctions.generate_exception_string(err_val))
        return self.cpu_data

    def get_data(self):
        return self.cpu_data


# --------------------------------------------------------------------

class MainLoop:
    """
    Perform all actions necessary to gather all data and
    insert it into the database
    """

    def __init__(self, db_writer):
        """
        :param db_writer:
        :return:
        """
        self.db_writer = db_writer
        self.user_account_manager = UserAccountManager(self.db_writer)

    def record_user_data(self):
        try:
            user_data_generator = LoggedInUserData(self.user_account_manager)
            user_data_generator.generate_data()
            self.db_writer.add_logged_in_users(user_data_generator.get_data())
            return user_data_generator.get_data()
        except Exception as err:
            ErrorLogger.error("record_user_data failed: %s" % err)
            raise

    def record_client_computer_data(self):
        try:
            client_computer_data_generator = ClientComputerData(self.db_writer)
            client_computer_data_generator.generate_data()
            self.db_writer.add_clients(
                client_computer_data_generator.get_data())
            return client_computer_data_generator.get_data()
        except Exception as err:
            ErrorLogger.error("record_client_computer_data failed: %s" % err)
            raise

    def record_summary_data(self, user_data, client_computer_data):
        try:
            summary_data_generator = SummaryData(self.user_account_manager,
                                                 user_data,
                                                 client_computer_data)
            summary_data_generator.generate_data()
            self.db_writer.add_summary(summary_data_generator.get_data())
            return summary_data_generator.get_data()
        except Exception as err:
            ErrorLogger.error("record_summary_data failed: %s" % err)
            raise

    def record_server_memory_data(self):
        try:
            server_memory_data_generator = ServerMemoryData()
            server_memory_data_generator.generate_data()
            self.db_writer.add_server_memory(
                server_memory_data_generator.get_data())
            return server_memory_data_generator.get_data()
        except Exception as err:
            ErrorLogger.error("record_server_memory_data failed: %s" % err)
            raise

    def record_server_cpu_data(self, mp_process_output):
        """
        Creater dabase entries for server cpu usage.
        :param mp_process_output: the text of the standard out from the
            mpstst process that is run in the highest level loop
        :return:
        """
        try:
            server_cpu_data_generator = ServerCpuData()
            server_cpu_data_generator.generate_data(mp_process_output)
            self.db_writer.add_server_cpu(server_cpu_data_generator.get_data())
            return server_cpu_data_generator.get_data()
        except Exception as err:
            ErrorLogger.error("record_server_cpu_data failed: %s" % err)
            raise

    def perform_single_loop(self, mp_process_output):
        try:
            self.db_writer.connect_to_database()
            user_data = self.record_user_data()
            client_computer_data = self.record_client_computer_data()
            summary_data = self.record_summary_data(user_data,
                                                    client_computer_data)
            server_memory_data = self.record_server_memory_data()
            if mp_process_output:
                server_cpu_data = self.record_server_cpu_data(mp_process_output)
            else:
                ErrorLogger.error("No mpstat output.")
        except Exception as err_val:
            ErrorLogger.error("perform single loop failed: %s"
                              % localFunctions.generate_exception_string(err_val))
        finally:
            try:
                self.db_writer.close_connection()
            except Exception:
                pass



# general purpose functions used by several classes

def run_command(command, reraise_error=False, result_as_list=True, timeout=0.0):
    """
    Run the command and return a list of the lines in the response.
    If the command fails then the exception subprocess.CalledProcessError.
    This should be handled by the caller.
    """
    try:
        if timeout:
            command = "timeout %f " % timeout + command
        output = subprocess.check_output(command, shell=True,
                                         universal_newlines=True,
                                         stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        output = e.output
        if reraise_error:
            raise
    result = output
    if result_as_list:
        result = str(output).splitlines()
    return result


# ********************************************************************

if __name__ == "__main__":

    InfoLogger, ErrorLogger = backgroundFunctions.create_loggers(
        INFO_LOGFILE, ERROR_LOGFILE)
    systemd = backgroundFunctions.SystemdSupport()
    atexit.register(backgroundFunctions.log_stop, systemd, PROGRAM_NAME,
                    InfoLogger)
    backgroundFunctions.shutdown_if_running(PROGRAM_NAME, ErrorLogger)
    backgroundFunctions.log_start(systemd, PROGRAM_NAME, InfoLogger)
    db_writer = DbWriter("SystemMonitor", "sysmonitorAdmin",
                         "system-monitor", "localhost")

    start_time = time.time()
    main_loop = MainLoop(db_writer)
    shell_command = "/usr/bin/mpstat %d 1" % (SAMPLE_TIME - 1)
    # run a single time tp get correct cpu data for first entry
    mp_process_output = run_command(shell_command, result_as_list=False)
    # run everyhing within a loop on mstat. This provides a background timer
    # thread in addition to the memory data.2
    while True:
        try:
            systemd.update_watchdog()
            start_time = backgroundFunctions.fill_loop_time(SAMPLE_TIME,
                                                            start_time)
            mp_process = subprocess.Popen(shell_command, shell=True,
                                          stdout=subprocess.PIPE)
            # now do everthing for a single iteration.
            db_writer.set_time()
            main_loop.perform_single_loop(mp_process_output)
            mp_process.wait()
            mp_process_output = mp_process.stdout.read()
            mp_process.stdout.close()
        except subprocess.CalledProcessError as err_val:
            ErrorLogger.error("Main loop error with mpstat: %s"
                              % localFunctions.generate_exception_string(
                err_val))
        except Exception as err_val:
            ErrorLogger.error("Main loop error: %s"
                              % localFunctions.generate_exception_string(
                err_val))
