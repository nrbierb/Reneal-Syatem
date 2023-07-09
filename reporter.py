#!/usr/bin/python3
__author__ = 'master'
"""
Read the SystemMonitor database to create a report on
the usage of the server and associated clients.
"""

import MySQLdb
import argparse
import configparser
import csv
import collections
import datetime
import time
import subprocess
import os
import os.path
import re
import sys
import shutil

VERSION = "0.9.5"
# IMPORTANT--SAMPLE_TIME should be identical to the value in the
# SystemMonitor monitoring daemon
SAMPLE_TIME = 60
# scaling for partial periods should be limited tono more than 1 day in period
WEEK_MIN_SCALING = 1 / 7.0
MONTH_MIN_SCALING = 1 / 20.0


# --------------------------------------------------------------------

class DbReader:
    """
    Generalize all db functions for consistency and flexibility.
    """

    def __init__(self, db_name, password, user_name, host="localhost"):
        try:
            self.connector = MySQLdb.connect(db=db_name, passwd=password,
                                             user=user_name, host=host)
        except StandardError:
            print ("""
Error:
    It looks like the mysql database server is not running.
    Run systemCheck and then try this program again.
    If that does not work run the command "sudo service mysql restart"
    and try this program again.
    If that still does not work then this server may never have been set
    up to use the system monitor.
            """)
            sys.exit(-1)
        self.cursor = self.connector.cursor()  # MySQLdb.cursors.DictCursor)

    def return_list(self, sql_query_text):
        """

        :param sql_query_text:
        :return:
        """
        try:
            self.cursor.execute(sql_query_text)
            return self.cursor.fetchall()
        except MySQLdb.Error as e:
            print ("Query %s failed with error %s" % (sql_query_text, e))
            return []

    def return_single_value(self, sql_query_text):
        try:
            self.cursor.execute(sql_query_text)
            return self.cursor.fetchone()
        except MySQLdb.Error as e:
            print ("Query %s failed with error %s" % (sql_query_text, e))
            return None

    def return_cursor(self, sql_query_text):
        try:
            self.cursor.execute(sql_query_text)
            return self.cursor
        except MySQLdb.Error as e:
            print ("Query %s failed with error %s" % (sql_query_text, e))
            return None


class TimePeriod:
    """
    A simple class to define basic parameters of a sample time period:
    start_time., stop_time, and scaling factor (the fraction of the period
    that is valid
    """

    def __init__(self, start_time, stop_time, period_time):
        """
        Basic parameter for peroid. All are unsigned integer values of
        unix time
        :param start_time:
        :param stop_time:
        :param period_time: The total number seconds in complete period
        :return:
        """
        self.start_time = start_time
        self.stop_time = stop_time
        self.period_time = period_time
        self.scaling_factor = 1.0

    def compute_scaling_factor(self):
        """
        Compute the fracion of time of the defined period that the
        the start_time and stop time represent. Round up to assure that
        scaling is no less than one exra day.
        :return: the computed scaling factor
        """
        actual_period_measured = self.stop_time - self.start_time
        if actual_period_measured < self.period_time:
            seconds_per_day = 60 * 60 * 24
            # use integer division to assure round down, the add 1
            days_min = actual_period_measured // seconds_per_day
            days = (max(days_min + 1), 1)
            adjusted_period = seconds_per_day * days
            self.scaling_factor = self.period_time / adjusted_period
        else:
            self.scaling_factor = 1.0
        return self.scaling_factor

    def get_period_start(self):
        return self.start_time

    def get_period_end(self):
        return self.stop_time

    def get_scaling_factor(self):
        return self.scaling_factor


class TimeFinder:
    """
    Generate arrays of time periods in unix time to
    work use with database queries. it will return an
    array of start and end times and percentage of the period
    when data is avalable. It will not return any periods that
    are either before the first recorded database entry or after the
    last.
    """

    def __init__(self, db_reader, num_months, num_weeks=0):
        self.db_reader = db_reader
        self.database_min_time = self.db_reader.return_single_value(
            "SELECT MIN(Time) from SummaryData")[0]
        self.database_max_time = self.db_reader.return_single_value(
            "SELECT MAX(Time) from SummaryData")[0]
        self.max_datetime = datetime.date.fromtimestamp(
            float(self.database_max_time))
        self.num_months = num_months
        self.num_weeks = num_weeks
        if not num_weeks:
            self.num_weeks = num_months * 4

    def get_weeks(self, end_time=0.0):
        """
        Create a list of tuples (start_time, end_time) in unix_time that
        define each week. The last week will be only partial - it is from the
        beginning of the week to the end time.
        The list is in time order -- earliest first.
        :param end_time: a unix timestamp
        :return: an ordered ist of tuples for each week (start, end)
        """
        if not end_time:
            end_time = self.database_max_time
        else:
            # assure that the end time is in the range of recorded values in the database
            end_time = min(self.database_max_time, end_time)
            end_time = max(self.database_min_time, end_time)
        sec_per_week = 7 * 24 * 3600
        # assure that the end time is in the range of recorded values in the database
        end_time = min(self.database_max_time, end_time)
        end_time = max(self.database_min_time, end_time)
        # adjust for the portion of the current week
        end_date_time = datetime.date.fromtimestamp(float(end_time))
        dt_start_of_week = end_date_time - datetime.timedelta(
            end_date_time.weekday())
        week_start = int(time.mktime(dt_start_of_week.timetuple()))
        weekly_periods = [TimePeriod(week_start, end_time, sec_per_week)]
        # weekly_periods = [(week_start, self.database_max_time)]
        for i in range(self.num_weeks - 1):
            week_end = week_start
            week_start = week_end - sec_per_week
            if week_start < self.database_min_time:
                weekly_periods.append(
                    TimePeriod(self.database_min_time, week_end,
                               sec_per_week))
                break
            else:
                weekly_periods.append(
                    TimePeriod(week_start, week_end, sec_per_week))
        # list is in reverser order (lastest first) so reverse
        weekly_periods.reverse()
        return weekly_periods

    def get_months(self, end_time=0):
        """
        Generate list for months simliar to weeks. This adds the complication
        of differing days per month
        :param end_time: a datetime objeect for the latest time to be reported
        :return
        """
        if not end_time:
            end_time = self.database_max_time
        else:
            # assure that the end time is in the range of recorded values in the database
            end_time = min(self.database_max_time, end_time)
            end_time = max(self.database_min_time, end_time)
        end_datetime = datetime.datetime.fromtimestamp(end_time)
        target_year = end_datetime.year
        target_month = end_datetime.month
        dt_month_start = datetime.date(target_year, target_month, 1)
        month_start = time.mktime(dt_month_start.timetuple())
        # use 30 days as a monthlong perod for scaling
        time_per_month = 60 + 60 * 24 * 30
        monthly_periods = [TimePeriod(month_start, end_time, time_per_month)]
        for i in range(self.num_months - 1):
            month_end = month_start - 1
            target_month -= 1
            if target_month < 1:
                target_month = 12
                target_year -= 1
            dt_month_start = datetime.date(target_year, target_month, 1)
            month_start = time.mktime(dt_month_start.timetuple())
            monthly_periods.append(
                TimePeriod(month_start, month_end, time_per_month))
            if month_start < self.database_min_time:
                break
        # list is in reverser order (lastest first) so reverse
        monthly_periods.reverse()
        return monthly_periods


class ReportValues:
    def __init__(self, db_reader, user_type, status, time_period, max_count):
        self.db_reader = db_reader
        self.max_count = max_count
        self.value = 0.0
        self.start_time = time_period.get_period_start()
        self.stop_time = time_period.get_period_end()
        self.time_period = time_period
        self.scale_factor = time_period.get_scaling_factor()
        if status == "Active":
            self.column_name = "Active%sCount" % user_type
        else:
            self.column_name = "%sCount" % user_type
        # create the return dict filled with 0's
        self.value_dict = collections.OrderedDict()
        for i in range(1, max_count + 1):
            self.value_dict[i] = 0
        self.value_dict["> Count"] = 0
        self.value_dict["On Hours"] = 0
        self.value_dict["User Hours"] = 0
        self.value_dict["Active Hours"] = 0

    def fill_array_from_database(self):
        # for all
        i = 0
        try:
            for i in range(self.max_count + 2):
                if i == 0:
                    action = "SUM"
                else:
                    action = "COUNT"
                query = "SELECT %s(%s) FROM SummaryData WHERE Time >= %d AND Time <= %d " \
                        "AND %s >= %d" \
                        % (action, self.column_name, self.start_time,
                           self.stop_time,
                           self.column_name, i)
                samples_count = self.db_reader.return_single_value(query)[0]
                if not samples_count:
                    break
                if i == 0:
                    self.value_dict["User Hours"] = int(samples_count)
                elif i > self.max_count:
                    self.value_dict[self.max_count] -= int(samples_count)
                    self.value_dict["> Count"] = int(samples_count)
                elif i == 1:
                    self.value_dict[i] = int(samples_count)
                    self.value_dict["Active Hours"] = int(samples_count)
                else:
                    self.value_dict[i - 1] -= int(samples_count)
                    self.value_dict[i] = int(samples_count)
            # Get hours server turned on
            query = "SELECT COUNT(Time) FROM SummaryData WHERE Time >= %d AND Time <= %d " \
                    % (self.start_time, self.stop_time)
            self.value_dict["On Hours"] = \
                self.db_reader.return_single_value(query)[
                    0]
            return self
        except StandardError as e:
            print ("""Getting values from the database had an error.
  The type was %s, the time %d and the count %d. 
  The error was:%s""" % (self.column_name, self.start_time, i, e))

    def set_value(self, samples_count=1):
        """
        Count is the number of sample periods. The value is the
        number of hours repersentd by the count
        :return:
        """
        self.value = float(samples_count * SAMPLE_TIME) / 3600.0
        return self.value

    def get_raw_value(self):
        return self.value

    def get_scaling_factor(self):
        return self.time_period.get_scaling_factor()

    def get_scaled_value(self):
        return self.value * self.get_scaling_factor()

    def get_times(self):
        """
        Create datetime objects for start and finish time
        :return: start and end datetime objects
        """
        start_datetime = datetime.datetime.fromtimestamp(
            self.time_period.get_start_time())
        end_datetime = datetime.datetime.fromtimestamp(
            self.time_period.get_end_time())
        return start_datetime, end_datetime


class DataGatherer:
    """

    """

    def __init__(self, db_reader, time_finder, max_user_count=20):
        self.db_reader = db_reader
        self.time_finder = time_finder
        self.max_user_count = max_user_count
        self.reporter_dict = {}

    # def perform_count_query(self, ):
    def create_value_objects(self):
        """
        Create a dictionary of all ReportValue objects. The key is generated by the ReportValue
        object.
        :return:
        """
        reporter_count = 0
        for time_period in self.time_finder.get_weeks():
            for status in ("All", "Active"):
                for user_type in ("Teacher", "Student"):
                    # create a reporter object for each type and time period
                    reporter = ReportValues(self.db_reader, user_type, status,
                                            time_period,
                                            self.max_user_count)
                    self.reporter_dict[
                        ("Week", user_type, status, time_period)] = \
                        reporter.fill_array_from_database()
                    reporter_count += 1
        for time_period in self.time_finder.get_months():
            for status in ("All", "Active"):
                for user_type in ("Teacher", "Student"):
                    reporter = ReportValues(self.db_reader, user_type, status,
                                            time_period,
                                            self.max_user_count)
                    self.reporter_dict[
                        ("Month", user_type, status, time_period)] = \
                        reporter.fill_array_from_database()
                    reporter_count += 1
        if reporter_count == 0:
            """
Error:
    There was a problem with getting report data so the report is bad.
    If no other errors reported then the database dump may be OK.
    Return the .the .tbz file. """
        return self.reporter_dict, reporter_count


class ResultGenerator:
    """
    Dump the database as a file, generate a csv file from the roport data,
    and save bot as a compressed tar file.
    """

    def __init__(self, report_data, school_name, upper_dir_name="/tmp"):
        """

        :param report_data:
        :param school_name:
        """
        self.school_name = school_name
        self.report_data = report_data
        self.upper_dirname = upper_dir_name
        self.dirname = ""
        self.file_name_base = ""
        self.result_dirname = ""
        self.report_filename = ""
        self.dump_filename = ""
        self.tar_filename = ""
        self.temp_path_tar_filename = ""
        self.final_path_tar_filename = ""

    def generate_names(self):
        """
        Gnerate all filenames and directories from the schoolname and date
        :return:
        """
        time_suffix = time.strftime("%m_%d_%y", time.localtime())
        base_name = self.school_name.title().replace(" ", "")
        self.file_name_base = base_name + "_" + time_suffix
        self.result_dirname = self.file_name_base + "_dir"
        self.dirname = os.path.join(self.upper_dirname, self.result_dirname)
        self.report_filename = self.dirname + "/" + self.file_name_base + ".csv"
        self.dump_filename = self.dirname + "/" + self.file_name_base + ".sql"
        self.disk_report_filename = self.dirname + "/" + self.file_name_base + "-DiskReport.txt"
        self.systemcheck_report_filename = self.dirname + "/" + self.file_name_base + "-SysChk.log"
        self.tar_filename = self.file_name_base + ".tbz"
        self.temp_path_tar_filename = "/tmp/" + self.tar_filename
        self.final_path_tar_filename = self.dirname + "/" + self.tar_filename

    def make_result_directory(self):
        """
        If the directory already exists, remove it and its contents.
        Then create the directory
        :return:
        """
        if os.path.exists(self.dirname):
            try:
                shutil.rmtree(self.dirname)
            except OSError as e:
                print ("Could not remove the old directory: %s" % e)
        try:
            os.mkdir(self.dirname)
        except OSError:
            print ("""
Error:
    Could not create the directory "%s" in
        "%s" for the results.
    Please try using the option "--storagedir"
      on the command line -- maybe the /media directory that is your
      thumbdrive.
    If you have used the --storagedir option check the spelling
      of the directory.
    If nothing else works you can also rerun this program with a sudo.
            """ % (self.result_dirname, self.upper_dirname))
            sys.exit(-1)

    def dump_database(self):
        """
        Dump the complete SystemMontor database into file "filename".
        This is a text file and could be quite large. This why it is dumped
        to an external file.
        :return output from the mysqldump command:
        """
        dump_command = \
            "mysqldump --user=root --password=mysqlAdmin --add-drop-database --databases SystemMonitor "
        try:
            output = subprocess.check_output(dump_command, shell=True,
                                             universal_newlines=True,
                                             stderr=open(os.devnull, 'wb'))
        except subprocess.CalledProcessError as e:
            print ("""
Error:
    There was an error while doing the database dump.
    The error reported is:  "%s"
    The databse dump file may not be usable but the report probably is.
    """ % e)
            return "Error in dump: %s" % e
        return output

    def write_database_dump_file(self):
        """
        Create a file with the complete dump ot the sql SysetmMonitor tables.
        Prepend the requied atart sql commnad to make it directly loadable
        :return:
        """
        dump = self.dump_database()
        dump_file = open(self.dump_filename, "w")
        dump_file.write("USE SystemMonitor;\n")
        dump_file.write(dump)
        dump_file.close()

    def write_report_file(self, report_filename):

        outfile = open(report_filename, "w")
        writer = csv.writer(outfile)
        keys = list(self.report_data.keys())
        # keys.sort(cmp = key_compare)
        keys.sort(key=key_sort_val, reverse=True)
        sample_row = self.report_data[keys[0]].value_dict
        row_keys = list(sample_row.keys())
        row_header_list = ["Period Type", "User", "Status", "Start Time"]
        row_header_list.extend(row_keys)
        row_header = []
        for row_key in row_header_list:
            row_header.append(str(row_key))
        # row_header.append("Total Hours")
        writer.writerow(row_header)
        for key in keys:
            date = datetime.datetime.fromtimestamp(
                key[3].get_period_start()).strftime("%m/%d/%y")
            row_values = [key[0], key[1], key[2], date]
            # hour_sum = 0.0
            for row_key in row_keys:
                value = self.report_data[key].value_dict[row_key] / 60.0
                row_values.append(float("%3.2f" % value))
                # hour_sum += value
                # last_value = value
            # remove the "All" column in the sum
            # hour_sum -= last_value
            # row_values.append(float("%3.2f" %hour_sum))
            writer.writerow(row_values)
        outfile.close()

    @staticmethod
    def write_disk_report_file(disk_report_filename):
        try:
            output = subprocess.check_output("/usr/local/share/apps/checkDisks.py", shell=True,
                                             universal_newlines=True,
                                             stderr=open(os.devnull, 'wb'))
        except subprocess.CalledProcessError as e:
            output = "Failed to get disk report:\n %s" % e
        with open(disk_report_filename, "w") as f:
            f.write(output)

    @staticmethod
    def write_systemcheck_file(systemcheck_report_filename):
        try:
            if os.path.exists("/var/log/systemCheck/loginUpdate.log.1"):
                command = "cat /var/log/systemCheck/loginUpdate.log.1" + \
                          "/var/log/systemCheck/loginUpdate.log > " + systemcheck_report_filename
                subprocess.check_call(command, shell=True, stderr=open(os.devnull, 'wb'))
            else:
                shutil.copy("/var/log/systemCheck/loginUpdate.log", systemcheck_report_filename)
        except (subprocess.CalledProcessError, shutil.Error):
            with open(systemcheck_report_filename, 'w'):
                pass

    def prepare_for_sending(self):
        """
        Use the compresson command to create a single compressed file to return
        via email. The directory has been created and the report and dump files
        have been written into it.
        :return:
        """
        combine_command = "tar -cjf %s %s" % (self.temp_path_tar_filename,
                                              os.path.basename(self.dirname))
        try:
            # shange directory so no extra path elements in the tar file
            os.chdir(self.upper_dirname)
            output = subprocess.check_output(combine_command, shell=True,
                                             universal_newlines=True,
                                             stderr=subprocess.STDOUT)
            # now move the compressed file into the directory also
            shutil.move(self.temp_path_tar_filename,
                        self.final_path_tar_filename)
            # remove the large files
            os.remove(self.dump_filename)
            os.remove(self.disk_report_filename)
            os.remove(self.systemcheck_report_filename)
        except subprocess.CalledProcessError as e:
            print ("There was an error while doing the database dump: %s" % e)
            return False
        return True

    def write_all_result_files(self):
        """
        The primary function for writing all result files.
        It performs thes actions.
        1. Create a directory for the results
        2. Write a csv file that contaions the report results into the directory
        3. Perform a database dump of the SystemMonitor database, then write it
            as a sql dump file in the directory
        4. Create a compressed tar file of the directory.
        5. Move the tar file into the directory to prepare for a simple copy
            of all of the resutls in various forms that can be used to forward
            the data.
        :return:
        """
        self.generate_names()
        self.make_result_directory()
        self.write_database_dump_file()
        self.write_report_file(self.report_filename)
        self.write_disk_report_file(self.disk_report_filename)
        self.write_systemcheck_file(self.systemcheck_report_filename)
        return self.prepare_for_sending()


def key_sort_val(key):
    """
    Determine a value to be used in sorting the rows in tjhe report output.
    The explicit function is used rather than lambda so the computaion result
    can be seen.
    :param key:
    :return computed comparison key value:
    """
    val = 2 ** 32 * (key[0] == "Month") + 2 ** 31 * (key[1] == "Student") + \
          2 ** 30 * (key[2] == "Active") + (
                  int(key[3].get_period_start()) - 2 ^ 20)
    return val


def get_schoolname_from_gui(school_name):
    """
    Get the name of the school from a popup window
    :return: schoolname
    """
    if school_name == "Unknown_SchoolName":
        school_name = ""
    command = 'yad --entry --title "Enter Schoolname" ' + \
              '--text="Please enter the name of the school.\n' + \
              'Spaces in the name are OK." 2>/dev/null --entry-text="%s"' % school_name
    try:
        school_name = subprocess.check_output(command, shell=True,
                                              universal_newlines=True)
        school_name = school_name.strip()
    except subprocess.CalledProcessError:
        pass
    return school_name


def get_schoolname_from_openvpn():
    school_name = "Unknown_SchoolName"
    try:
        f = open("/etc/openvpn/client.conf", "r")
        file_contents = f.read()
        f.close()
        name_match = re.search(r'/etc/openvpn/keys/([\w\-_]+)\.key', file_contents)
        if name_match:
            sn = str(name_match.group(1)).replace("-main-server", "")
            school_name = sn.replace("-main-server", "").title().strip()
    except (OSError, IOError):
        pass
    return school_name


def get_school_name_from_wireguard(dummy_name):
    school_name = dummy_name
    try:
        with open("/etc/wireguard/wg0.conf", "r") as f:
            text = f.read()
            school_names = re.findall(r'#Client Name:\s*(\w+)-main', text)
            school_name = school_names[0].title()
            answer = input(
                'The wireguard file school name is "%s" Is this correct?(Y/n)? ' % school_name)
            if answer.lower() not in ('y', "yes", ""):
                school_name = dummy_name
    except (re.error, IOError):
        pass
    return school_name


def get_school_name_from_params(dummy_name):
    """
    Get the value defined in schoolParams.conf
    Remove the "Secondary School" postfix from it and remove spaces.
    :return:
    """
    school_name = dummy_name
    try:
        config = configparser.ConfigParser()
        config.read("/etc/schoolParams.conf")
        fullname = config["School Info"]["school_name"].title()
        nospacename = fullname.replace(" ", "")
        school_name = re.sub(r'SecondarySchool$', '', nospacename)
        answer = input('The configured school name is "%s" Is this correct?(Y/n)? ' % school_name)
        if answer.lower() not in ('y', "yes", ""):
            school_name = dummy_name
    except (configparser.Error, IOError, re.error):
        pass
    return school_name


def get_school_name():
    dummy_name = "UnknownSchool"
    school_name = get_school_name_from_params(dummy_name)
    if school_name == dummy_name:
        school_name = get_school_name_from_wireguard(dummy_name)
    if school_name == dummy_name:
        if os.getenv("TERM") != "linux":
            # in a gui, not a raw terminal
            school_name = get_schoolname_from_gui(school_name)
        else:
            school_name = input('Please type in school name: ')
        if not school_name:
            school_name = dummy_name
    return school_name


def generate_csv_report(report_filename, num_months=60, max_user_count=20):
    """
    This can be called by another program to just create the csv report file.
    :param report_filename: This sould be the full path name
    :param num_months:
    :param max_user_count:
    :return:
    """
    db_reader = DbReader("SystemMonitor", "mysqlAdmin", "root", "localhost")
    time_finder = TimeFinder(db_reader, num_months, num_weeks=0)
    data_gatherer = DataGatherer(db_reader, time_finder, max_user_count)
    result, reporter_count = data_gatherer.create_value_objects()
    result_generator = ResultGenerator(result, "School", "/tmp")
    result_generator.write_report_file(report_filename)


def generate_disk_report():
    report_filename = "/tmp/diskReport.txt"
    try:
        output = subprocess.check_output("/usr/local/share/apps/checkDisks.py", shell=True,
                                         universal_newlines=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        output = "Failed to get disk report"
    with open(report_filename, "w") as f:
        f.write(output)
    return report_filename


def generate_systemcheck_report():
    report_filename = "/tmp/systemCheck.log"
    compressed_filename = report_filename + ".xz"
    try:
        if os.path.exists("/var/log/systemCheck/loginUpdate.log.1"):
            command = "cat /var/log/systemCheck/loginUpdate.log.1" + \
                      "/var/log/systemCheck/loginUpdate.log > " + report_filename
            subprocess.check_call(command, shell=True, stderr=subprocess.DEVNULL)
        else:
            shutil.copy("/var/log/systemCheck/loginUpdate.log", report_filename)
    except (subprocess.CalledProcessError, shutil.Error):
        with open(report_filename, 'w'):
            pass
    try:
        command = "xz " + report_filename
        subprocess.check_call(command, shell=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        with open(compressed_filename, 'w'):
            pass
    return compressed_filename


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect information from the SystemMonitor database")
    parser.add_argument("--months", dest="months", default=60, type=int,
                        help="The maximum number of months to report (default 18")
    parser.add_argument("--maxcount", dest="maxcount", default=20, type=int,
                        help="The maximum number of individual usage count buckets (default 20")
    parser.add_argument("--storagedir", dest="top_level_dir",
                        default="/tmp", type=str,
                        help="The directory for the result (default; the directory you are in)")
    parser.add_argument('-v', "--version", action='version',
                        version=VERSION)
    args = parser.parse_args()
    num_months = args.months
    max_user_count = args.maxcount
    top_level_dir_name = args.top_level_dir
    school_name = get_school_name()
    db_reader = DbReader("SystemMonitor", "mysqlAdmin", "root", "localhost")
    time_finder = TimeFinder(db_reader, num_months, num_weeks=0)
    data_gatherer = DataGatherer(db_reader, time_finder, max_user_count)
    result, reporter_count = data_gatherer.create_value_objects()
    result_generator = ResultGenerator(result, school_name, top_level_dir_name)
    successful = result_generator.write_all_result_files()
    if successful:
        location = ""
        if top_level_dir_name != ".":
            location = " Your results are in %s" % result_generator.dirname
        print ("The run completed successfully.%s" % location)
    else:
        "There was a problem with this run."
