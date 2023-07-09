#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'master'
"""
Send mail report of system usage to fixed destination
"""

import os
import os.path
import MySQLdb
import datetime
import hashlib
import subprocess
import sys
import time
import shutil
import smtplib
import syslog
import email.errors
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import localFunctions
import reporter
import backgroundFunctions

NUM_DAYS_RECORDS = 90
MAX_ATTACH_SIZE = 5
TMP_DIRECTORY = "/tmp/infofiles"
SPLIT_FILES_DIRECTORY = TMP_DIRECTORY + "splits"
SQL_DUMP_FILENAME = TMP_DIRECTORY + "/mon.sql"
CSV_FILENAME = TMP_DIRECTORY + "/mon.csv"
SYSTEM_CHECK_LOG_FILENAME = "/var/log/systemCheck/systemCheck.log"
LOGGING_DIRECTORY = "/var/log/smtpreporter"
InfoLogger = None
ErrorLogger = None
EMAIL_SENDER = "mainserver@reneal.duckdns.org"
EMAIL_RECEIVER = "reneal.datasender@gmail.com"
SENDGRID_USERNAME = "apikey"
SENDGRID_API_KEY = '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'
SENDGRID_SMTP_RELAY = "smtp.sendgrid.net"
DATABASE_HOST = "192.168.2.1"
VERSION = "0.9"


class FileHandler:
    """
    Manage individual files to be attachemnts
    """

    def init(self, original_filename, remove_original):
        self.original_file = original_filename
        self.remove_original = remove_original
        self.compressed_file = None
        self.result_file = None
        self.result_chunks_list = []
        self.full_file_md5sum = ""
        self.result_chunks_md5sums = {}
        self.is_split = False

    def generate_md5sum(self, filename):
        try:
            with open(filename, "rb") as f:
                bytes = f.read()  # read file as bytes
                return hashlib.md5(bytes).hexdigest()
        except OSError:
            pass
        return ""

    def compress_file(self):
        """
        Compress file with 7z. Creates filename.7z.
        and remove original
        :param filename:
        :return:
        """
        try:
            delete_flag = "-sdel" if self.remove_original else ""
            command = "/usr/bin/7z a  %s %s %s" \
                              %(delete_flag, self.original_file, self.compressed_file)
            result = localFunctions.run_command(command, reraise_error = True,
                                                result_as_list=False, print_error=True)
        except subprocess.CalledProcessError as e:
            result = False
        return result

    def split_file(self):
        """
        split file into parts with linux split program
        :return:
        """
        global MAX_ATTACH_SIZE, SPLIT_FILES_DIRECTORY
        try:
            if os.path.getsize(self.compressed_file) > MAX_ATTACH_SIZE:
                self.is_split = True
                os.mkdir(SPLIT_FILES_DIRECTORY)
                command = "split -b %dm -d %s %s/%s" %(MAX_ATTACH_SIZE,
                                                       self.compressed_file,
                                                       SPLIT_FILES_DIRECTORY,
                                                       self.compressed_file)
                result = localFunctions.run_command(command, reraise_error = True,
                                                    result_as_list=False, print_error=True)
                self.result_chunks_list = [os.path.join(SPLIT_FILES_DIRECTORY, f)
                                           for f in os.listdir(SPLIT_FILES_DIRECTORY)]
                self.result_chunks_list.sort()
                for f in self.result_chunks_list:
                    self.result_chunks_md5sums[f] = self.generate_md5sum(f)
        except (OSError,subprocess.CalledProcessError) as e:
            error_message = "Failed to split %s. Error: %s" %(self.compressed_file, e)
            ErrorLogger.error(error_message)


    def process_file(self):
        """
        Perform all processing on original file
        :return:
        """
        self.compressed_file = self.compress_file()
        self.full_file_md5sum = self.generate_md5sum(self.compressed_file)
        self.split_file()

    def get_single_file(self):
        return self.result_file, self.full_file_md5sum

    def get_split_files(self):
        if self.is_split:
            return self.result_chunks_list, self.result_chunks_md5sums
        else:
            return None, None

class ReportsGenerator:
    """
    Generate and compress and split all three reports to be sent.
    These reports are:
    SQL dmp of database for NUM_DAYS_RECORDS back
    Summary report csv file
    Copy of systemCheck logfile
    """

    def __init__(self, schoolname, days_back, max_attach_size):
        self.datestring = datetime.date.today().strftime("%m-%d-%Y")
        self.schoolname = schoolname
        self.id = schoolname + "-" + self.datestring
        self.sql_filename = "SystemMonitor-" + self.id + ".sql"
        self.csv_filename = os.path.join("Summary-)
        self.systemCheckLog_filename = systemCheckLog_filename
        self.days_back = days_back
        self.max_attach_size = max_attach_size
        self.split_list = []
        self.full_size_md5sum = ""
        self.split_list_md5sums = {}

    def modify_sql_db(self, db_name):
        global DATABASE_HOST
        try:
            connector = MySQLdb.connect(db=modified_db_name,
                                        passwd="mysqlAdmin", user="root",
                                        host=DATABASE_HOST)
            for tablename in ("ClientResourceUse", "CpuUse", "MemoryUse",
                              "SummaryData", "UsersLoggedIn"):
                earliest_time = time.time() - self.days_back * 24 * 3600
                query = "DELETE FROM %s WHERE Time < %d" % (
                    tablename, earliest_time)
                connector.query(query)
                connector.commit()
        except MySQLdb.DatabaseError as err:
            syslog.syslog(syslog.LOG_ERR, "Error in modifying db: %s" % err)
            raise MySQLdb.DatabaseError

    def generate_sql_dump(self):
        global DATABASE_HOST
        db_copy_name = "SystemMonitorCopy"
        copy_command = 'mysqldbcopy --source=root:mysqlAdmin@%s ' % DATABASE_HOST + \
                       '--destination=root:mysqlAdmin@%s  ' % DATABASE_HOST + \
                       'SystemMonitor:%s' % db_copy_name
        dump_command = 'mysqldump -u root --password="mysqlAdmin" --databases %s > %s' \
                       % (db_copy_name, self.sql_filename)
        drop_command = 'echo "DROP DATABASE IF EXISTS %s" | mysql -u root --password="mysqlAdmin"' \
                       % db_copy_name
        try:
            #assure nothing left from a previous run
            localFunctions.run_command(drop_command, reraise_error=True)
            localFunctions.run_command(copy_command, reraise_error=True)
            self.modify_sql_db(db_copy_name)
            localFunctions.run_command(dump_command, reraise_error=True)
            localFunctions.run_command(drop_command, reraise_error=True)
        except (subprocess.CalledProcessError, MySQLdb.DatabaseError) as err:
            ErrorLogger.error("Error in create_sql_dump: %s" % err)


    def generate_sql_attachment_files(self):
        self.generate_sql_dump()
        sql_file_handler = FileHandler(self.sql_filename, remove_original=True)
        sql_file_handler.process_file()
        return sql_file_handler

    def generate_csv_attachment_file(self):
        reporter.generate_csv_report(self.csv_filename)
        csv_file_handler = FileHandler(self.csv_filename)
        return csv_file_handler

    def generate_system_check_log(self):
        try:
            system_check_copy =  os.path.join(TMP_DIRECTORY, "systemCheck.log")
            shutil.copy("/var/log/systemCheck/systemCheck.log",
                        self.systemCheckLog_filename)
            system_check_file_handler = FileHandler(self.systemCheckLog_filename)
            return system_check_file_handler
        except IOError as err:
            ErrorLogger.error("Error in generate_system_check_log: %s" %err)
            return None

class MessageGenerator:
    def __init__(self, schoolname):
        self.datestring = datetime.date.today().strftime("%m-%d-%Y")
        self.schoolname = schoolname
        self.id = schoolname + "-" + self.datestring
        self.mimetype = "application/octet-stream"
        self.msg = MIMEMultipart()

    def create_message(self, subject_line_extension, message_text):
        global EMAIL_SENDER, EMAIL_RECEIVER
        self.msg["From"] = EMAIL_SENDER
        self.msg["To"] = EMAIL_RECEIVER
        self.msg["Subject"] = "%s Usage %s %s" %(self.schoolname, self.datestring,
                                                 subject_line_extension)
        self.msg.attach(MIMEText(message_text))

    def add_attachment(self, attachment_file):
        try:
            with open(attachment_file, "rb") as f:
                attachment = MIMEApplication(f.read(), self.mimetype)
                attachment.add_header('Content-Disposition', 'attachment',
                                  filename=attachment_file)
                self.msg.attach(attachment)
        except (OSError, email.errors.MessageError) as err:
            ErrorLogger.error("Failed to create attachment %s: %s"
                              %(attachment_file, err))

    def get_message(self):
        return self.msg


def setup_logging():
    """
    Create logging directories if needed, then setup info and error_loggers
    :return info_logger, error_logger:
    """
    global LOGGING_DIRECTORY
    info_filename = LOGGING_DIRECTORY + "/info.log"
    error_filename = LOGGING_DIRECTORY + "/error.log"
    if not os.path.exists(LOGGING_DIRECTORY):
        os.makedirs(LOGGING_DIRECTORY,0755)
        os.chown(LOGGING_DIRECTORY,1,143)
    return backgroundFunctions.create_loggers(info_filename, error_filename)

# ********************************************************************


if __name__ == "__main__":
    try:
        commandline_parser = localFunctions.initialize_app(name="sendInfoSMTP",
                                                           version=VERSION,
                                                           description="Send system monitor email to fixed destination",
                                                           perform_parse=False)
        commandline_parser.add_argument("--days-back", dest="days_back",
                                        default=NUM_DAYS_RECORDS, type=int,
                                        help="previous number of days reported")
        commandline_parser.add_argument("--max-attach-size", dest="max_attach_size",
                                        default=MAX_ATTACH_SIZE, type=int,
                                        help="number of megabyes per email attachment")
        commandline_parser.add_argument("--email-dest", dest="email_dest",
                                        type=str, default=EMAIL_RECEIVER,
                                        help="destination email address")
        args = commandline_parser.parse_args()
        ERRO
        school_name = reporter.get_schoolname()
        report_generator = ReportsGenerator( school_name, SQL_DUMP_FILENAME,
                                             CSV_FILENAME, SYSTEM_CHECK_LOG_FILENAME,
                                             args.days_back, args.max_attach_size)

        syslog.syslog(
            "sendInfoSMTP v. %s Preparing system monitor information. %i days"
            % (VERSION, args.days_back))
        report_generator.generate_reports()



