#!/usr/bin/python3
"""
Use a spreadsheet with the names and birthdates of teachers
to create named teacher accounts
"""
import sys, csv, localFunctions, subprocess

PROGRAM_NAME = "createTeachersFromSpreadsheet"
PROGRAM_DESCRIPTION = "Create teacher accounts from names and birtdaes in a csv spreadsheet"
PROGRAM_VERSION = "0.9"


def exit_with_error(message):
    """
    Simple function to provide error exit with message
    """
    print("""Error: 
    %s """ % message)
    sys.exit(-1)


def create_account(account_name, password, full_name):
    """
    Use the createTeacherAccount.py to actually create teh teachers 
    account.
    """
    command = '/usr/local/bin/createTeacherAccount.py --account_name=%s --password=%s --full_name="%s"' \
              % (account_name, password, full_name)
    try:
        localFunctions.run_command(command, reraise_error=True)
    except subprocess.CalledProcessError as e:
        error_message = "Failed to create account for '%s'. Reason: %s" % (account_name, e)
        exit_with_error(error_message)


def read_spreadsheet(filename, test_only):
    """
    Open a csv spreadsheet, read the entries,
    and generate an array of user account names 
    and passwords.
    """
    try:
        f = open(filename, "r")
        reader = csv.DictReader(f)
        i = 0
        for entry in reader:
            first_name = entry["First Name"].lower()
            last_name = entry["Last Name"].lower()
            birthdate = entry["Date of Birth"]
            full_name = first_name.title() + " " + last_name.title()
            user_name = "%s_%s" % (first_name[0], last_name)
            password = birthdate.replace('/', '')
            if test_only:
                print("%-15s %s %s" % (user_name, password, full_name))
            else:
                create_account(user_name, password, full_name)
    except Exception as e:
        error_message = "Failed while creating accounts. Reason: %s" % e
        exit_with_error(error_message)


if __name__ == "__main__":
    parser = localFunctions.initialize_app(PROGRAM_NAME, PROGRAM_VERSION, PROGRAM_DESCRIPTION,
                                           perform_parse=False)
    parser.add_argument("-t", "--test", action="store_true", dest="test",
                        help="List the accounts that would be created. Do not create accounts.",
                        default=False)
    parser.add_argument("spreadsheet_name", nargs=1,
                        help="The name of the csv spreadsheet of teachers",
                        metavar="teacher_spreadsheet")
    opt = parser.parse_args()
    if opt.test:
        print("These are the accounts that would be created:")
    else:
        localFunctions.confirm_root_user(PROGRAM_NAME)
    if not opt.spreadsheet_name:
        localFunctions.error_exit(
            """A spreadsheet file must be given. 
            The format is three columns with the header:
            "First Name" "Last Name" "Date of Birth"
            It should be in csv form with a comma as separator.
            Date of Birth is in the form: mm/dd/yyyy
            """)
    read_spreadsheet(opt.spreadsheet_name[0], opt.test)
