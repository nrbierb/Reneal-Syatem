#! /bin/bash
# runner.sh will run a specially crafted file that can contain multiple scripts,
# file to install, and key files that are used to check contents, serve as flags
# special action, and describe the purpose of the file.
# A .run file is a tar.gz file that is first expanded in the /tmp directory.
# The contents are validated, then a bash script named "run.sh" is executed.
# If successful, the bash script "test.sh" is run.
# The required files in tar file are:
# 1. manifest -- a list of all files to confirm no file missing
# 2. md5sums  -- a list of the md5sums of all files that are compared with
#                computed the computed md5um for each file
# 3. run.sh   -- the executable bash script that is called to perform all actions
# Optional files:
# 1. test.sh  -- a shell script to be run only upon successful completion of run.sh
# 2. description.txt -- a text file that describes the purpose or actions of the .run
#         file. It is shown in the startup dialog and in the permanent info log file
# 3. use_sudo -- an empty file that, if present, will run gksudo before the run.sh
# 4. test_use_sudo -- an empty file that, if present, will run gksudo before the test.sh
# 5... any other files, directories, etc.
# This program is meant to be assigned as the default for the .run file extension
# for sysadmins so that the .run files can be easily started with just a double click.

export PROGRAM_NAME="Runner"
export PROGRAM_VERSION="0.8"
if [[ $# -lt 1 ]]; then
    SOURCE_FILE=$(zenity --file-selection --file-filter="*.run" title="Select the .run file to use." 2>/dev/null)
    if [[ "${SOURCE_FILE}" = "" ]]; then
        zenity --error --text="No file chosen.\n   Goodbye." --title="$PROGRAM_NAME" 2>/dev/null
        exit 127
    fi
else
    if [[ $1 = "-v" ]]; then
        echo ${PROGRAM_VERSION}
        exit 0
    elif [[ $1 = "-h" ]]; then
        echo "Run special update files. These normally end with a .run extension."
        echo "Usage: runner FILENAME"
        echo "       If no filename given, it will open a file selection dialog."
        exit 0
    else
        SOURCE_FILE=$( realpath "$1" )
        echo "${SOURCE_FILE}"
    fi
fi

export SOURCE_FILE
export WORKING_DIR=/tmp
TIME_EXTENSION=$(date +"%m%d-%H%M")
export TIME_EXTENSION
RUNFILE_NAME=$(basename ${SOURCE_FILE%\.*})
export RUNFILE_NAME
export UPDATE_ID=${RUNFILE_NAME}-${TIME_EXTENSION}
CACHE_DIR=${WORKING_DIR}/$(basename ${SOURCE_FILE%\.*})-${TIME_EXTENSION}
export CACHE_DIR
export LOGFILE=${CACHE_DIR}.log
export ERR_LOGFILE=${CACHE_DIR}.errorlog
export COMBINED_LOGFILE=${CACHE_DIR}.report
export RUNNER_LOG_DIR=/var/log/reneal-update
export COMPLETED_RUNS_LOG="${RUNNER_LOG_DIR}"/completed_runs.log
export DESCRIPTION=""
export FILE_LS="Value Not Avail"
export FILE_MD5SUM="Value Not Avail"
#SERVER_NAME=$(/usr/local/bin/serverName)
SERVER_NAME="main-server"
export SERVER_NAME
export SCRIPT_WRAPPER="/usr/local/share/apps/scriptWrapper.sh"
export ACTION="Upacking"
export MONITOR_PID="10000000"
FIFO=$(mktemp -u)
mkfifo "${FIFO}"

__show_info () {
    zenity --info --text="$1" --title="$PROGRAM_NAME" 2>/dev/null
}

__show_question () {
    zenity --question --text="$1" --title="$PROGRAM_NAME" 2>/dev/null
}

__show_error () {
    zenity --error --text="<span color =\"red\"><b>$1</b></span>" --title="$PROGRAM_NAME" 2>/dev/null
}

__show_running () {
    (tail -f "${FIFO}" |zenity --progress --pulsate --auto-close --no-cancel --title="$PROGRAM_NAME $ACTION" 2>/dev/null)&
}

__close_progressbar () {
    echo "100" >"${FIFO}"
}

__show_failure () {
    __show_error "Fatal Error!
    ${SOURCE_FILE}
    could not be correctly run. Nothing was done. The problem was:

    <i>$1</i>

    Please message or email Rene or Neal with a copy of
        <i>${COMBINED_LOGFILE}</i>
    Send the copy of the file if possible.
    You should also send a photo of the report window that will open
    when you click OK.

    When you make a photo please be sure that you include ALL of the text.
    If the text is longer than one window scroll to the top, take a photo,
    then scroll down and take another. If it is wider, use the bottom scroll
    bar to scroll right and take anther photo. ALL of the information in
    is important."
    }

__view_file () {
    zenity --text-info --title="Result" --filename="${1}" --no-wrap --width=850 --height=650 2>/dev/null
}

__monitor_file() {
    xfce4-terminal -e "tail -f ${1}" --title="${2}" --hide-menubar &>/dev/null &
    MONITOR_PID=$!
}

__log_error () {
    echo "$1" >> "${ERR_LOGFILE}"
}

__quit_on_error () {
    #This is called when the .run file itself is bad
    __log_error ""
    __log_error "$1"
    __make_logs
    __show_failure "$1"
    __view_file "${COMBINED_LOGFILE}"
    __cleanup
    exit 1
}

__cleanup () {
    cd /
    __close_progressbar
    rm -f "${FIFO}" 2>/dev/null
    if ps -o pid= -p ${MONITOR_PID} &> /dev/null; then
        kill ${MONITOR_PID} &> /dev/null
    fi
}

__make_combined_log () {
    echo "--- ${RUNFILE_NAME} -- ${SERVER_NAME} -- ${TIME_EXTENSION} ---" > "${COMBINED_LOGFILE}"
    echo "- Update File Info:  ${FILE_LS}" >> "${COMBINED_LOGFILE}"
    echo "- Update File md5sum:  ${FILE_MD5SUM}" >> "${COMBINED_LOGFILE}"
    echo "- Reneal Update Program:  ${PROGRAM_NAME} ${PROGRAM_VERSION}" >> "${COMBINED_LOGFILE}"
    echo >> " +++++ Update Description +++++" >> "${COMBINED_LOGFILE}"
    echo "${DESCRIPTION}" >> "${COMBINED_LOGFILE}"
    echo " +++++ Actions Log Entries +++++" >> "${COMBINED_LOGFILE}"
    cat "${LOGFILE}" >> "${COMBINED_LOGFILE}"
    echo "" >> "${COMBINED_LOGFILE}"
    if [[ $(stat -c%s "${ERR_LOGFILE}") != 0 ]]; then
        echo " +++++ Error Log Entries +++++" >> "${COMBINED_LOGFILE}"
        cat "${ERR_LOGFILE}" >> "${COMBINED_LOGFILE}"
        echo "" >> "${COMBINED_LOGFILE}"
    fi
    echo "+++++ End +++++" >> "${COMBINED_LOGFILE}"
}

__update_system_logfiles () {
    if [ ! -d "${RUNNER_LOG_DIR}" ] ; then
        mkdir "${RUNNER_LOG_DIR}"
        chown root:sysadmin "${RUNNER_LOG_DIR}"
        chmod 775 "${RUNNER_LOG_DIR}"
    fi
    header="

********** $UPDATE_ID **********
    "
    echo "$header" >> "${RUNNER_LOG_DIR}"/error.log
    cat "${ERR_LOGFILE}" >> "${RUNNER_LOG_DIR}"/error.log
    echo "$header" >> "${RUNNER_LOG_DIR}"/info.log
    cat "${COMBINED_LOGFILE}" >> "${RUNNER_LOG_DIR}"/info.log
}

__make_logs () {
    __make_combined_log
    __update_system_logfiles
}

__record_successful_run () {
    echo "${TIME_EXTENSION} $( __checksum ${SOURCE_FILE} ) ${RUNFILE_NAME} "  >> "${COMPLETED_RUNS_LOG}"
}

__make_cachedir () {
    if ! mkdir "$1" 2>> "${ERR_LOGFILE}" ; then
        __quit_on_error "Could not make the directory $1."
    fi
}

__check_manifest () {
    cd "$1" || __quit_on_error "Could not cd into $1"
    if [ ! -f ./manifest ]; then
        __cleanup
        __quit_on_error "The file named 'manifest', the list of files, is missing"
    fi
    local missing_files=false
    while read -r filename ; do
        if [ ! -f "${filename}" ]; then
            __log_error "${filename} is missing"
            missing_files=true
        fi
    done < ./manifest
    if ${missing_files} ; then
        __cleanup
        __quit_on_error "${SOURCE_FILE} is missing one or more files in it."
    fi
}

__check_files () {
    cd "$1" || __quit_on_error "Could not cd into $1"
    if [[ -f ./md5sums ]]; then
        md5sum --check ./md5sums 2>>"${ERR_LOGFILE}" |grep ": FAILED" >> "${ERR_LOGFILE}"
        md5sum --check ./md5sums &> /dev/null
        if [[ $? -ne 0 ]]; then
            __cleanup
            __quit_on_error "Some files were damaged and can not be used."
        fi
    else
        __cleanup
        __quit_on_error "The file named 'md5sums' that contains the validation information for the program files is missing."
    fi
}

__check_labtype_ok() {
    [[ -d /client_home/.WorkstationImage ]]
    local is_maclab=$?
    if [[ -f mac_only ]] && [[ $is_maclab -ne 0 ]]; then
        __quit_on_error "This should be run ONLY in a Mac Lab."
    elif [[ -f ltsp_only ]] && [[ $is_maclab -eq 0 ]]; then
        __quit_on_error "This should be run ONLY in a LTSP Lab."
    else
        return 0
    fi
}


__checksum () {
    read -a cs_array <<< "$( md5sum ${1} )"
    echo "${cs_array[0]}"
}

__unpack_it () {
    ACTION="Unpacking"
    __show_running
    echo "  ---- Unpacking ----" >>  "${LOGFILE}"
    echo "  ---- Unpacking ----" >>  "${ERR_LOGFILE}"
    __make_cachedir "$2"
    cd "$2" || __quit_on_error "Could not cd into $2"
    if ! /usr/bin/zstdcat -T0 "$1" 2>> "${ERR_LOGFILE}" | tar xf - >> "${LOGFILE}" 2>> "${ERR_LOGFILE}" ; then
        if ! [[ -f /usr/bin/zstd ]]; then
            echo "zstd not on computer" >> "${ERR_LOGFILE}"
        fi
        echo "Failed decompression with zstd. Trying lzcat" >> "${ERR_LOGFILE}"
        if ! /usr/bin/lzcat "$1" 2>> "${ERR_LOGFILE}" | tar xf - >> "${LOGFILE}" 2>> "${ERR_LOGFILE}" ; then
            echo "Failed decompression with lzcat" >> "${ERR_LOGFILE}"
            __cleanup
            __quit_on_error "Could not unpack $1"
        fi
    fi
    __check_manifest "$2"
    __check_files "$2"
    __close_progressbar
}

__save_runfile_copy () {
    if [[ $(stat --format=%s "$1") -lt 5000000 ]]; then
        mkdir -p /var/local/reneal-updates/
        echo "Made copy of $1 in /var/local/reneal-updates"
        cp "$1" /var/local/reneal-updates/
    fi
}

__perform_run_script () {
    __show_running
    echo "  ---- Running Update ----" >>  "${LOGFILE}"
    echo "  ---- Running Update ----" >>  "${ERR_LOGFILE}"
    if [[ -f use_sudo ]]; then
        echo Running "${RUNFILE_NAME}" as superuser
        echo Logfile: "${LOGFILE}"
        echo "  ---- Running As Superuser ----" >> "${LOGFILE}"
        if [[ $EUID -ne 0 ]]; then
            gksudo --description="${RUNFILE_NAME}" "${SCRIPT_WRAPPER}" "${CACHE_DIR}"/run.sh "${LOGFILE}" "${ERR_LOGFILE}"
        else
            "${SCRIPT_WRAPPER}" "${CACHE_DIR}"/run.sh "${LOGFILE}" "${ERR_LOGFILE}"
        fi
    else
        echo Running "${RUNFILE_NAME}"
        echo Logfile: "${LOGFILE}"
        "${SCRIPT_WRAPPER}" "${CACHE_DIR}"/run.sh "${LOGFILE}" "${ERR_LOGFILE}"
    fi
    __close_progressbar
    local result=$?
    return ${result}
}

__test_result () {
    ACTION="Testing"
    __show_running
    echo "  ---- Performing Test ----" >>  "${LOGFILE}"
    echo "  ---- Performing Test ----" >>  "${ERR_LOGFILE}"
    if [[ -f test_use_sudo ]]; then
        echo "  ---- Testing As Superuser ----" >> "${LOGFILE}"
        if [[ $EUID -ne 0 ]]; then
            gksudo --description="${RUNFILE_NAME}" "${SCRIPT_WRAPPER}" "${CACHE_DIR}/"test.sh "${LOGFILE}" "${ERR_LOGFILE}"
        else
            "${SCRIPT_WRAPPER}" "${CACHE_DIR}"/test.sh "${LOGFILE}" "${ERR_LOGFILE}"
        fi
    else
        "${SCRIPT_WRAPPER}" "${CACHE_DIR}"/test.sh  "${LOGFILE}" "${ERR_LOGFILE}"
    fi
    __close_progressbar
    local result=$?
    return ${result}
}

__report_success () {
    __close_progressbar
    echo "  -------- Successful run. --------" >> "${LOGFILE}"
    __make_logs
    __record_successful_run
    __show_info "<span color =\"green\"><b>Completed Successfully!!</b>
    Please message or email Rene or Neal with a copy of:
        <i>$COMBINED_LOGFILE</i>
    Send the copy of the file if possible.
    You should also send a photo of the report window that will open
    when you click OK.

    When you make a photo please be sure that you include ALL of the text.
    If the text is longer than one window scroll to the top, take a photo,
    then scroll down and take another. If it is wider, use the bottom scroll
    bar to scroll right and take anther photo. ALL of the information in
    is important.</span>"
    __view_file "${COMBINED_LOGFILE}"
}

__report_failure() {
    __close_progressbar
    echo "  -------- Failed run. --------" >> "${LOGFILE}"
    echo "  -------- Failed run. --------" >> "${ERR_LOGFILE}"
    __make_logs
    __show_error "${1}

    Please message or email Rene or Neal with a copy of:
        <i>$COMBINED_LOGFILE</i>
    Send the copy of the file if possible.
    You should also send a photo of the report window that will open
    when you click OK.

    When you make a photo please be sure that you include ALL of the text.
    If the text is longer than one window scroll to the top, take a photo,
    then scroll down and take another. If it is wider, use the bottom scroll
    bar to scroll right and take anther photo. ALL of the information in
    is important."
    __view_file "${COMBINED_LOGFILE}"
}

__ask_to_run() {
    txt=""
    if [[ -f "${CACHE_DIR}"/description.txt ]]; then
        DESCRIPTION=$(cat "${CACHE_DIR}"/description.txt)
        txt+="<b>Description:</b>
"
        txt+="$DESCRIPTION
"
    fi
    txt+="<span color =\"green\">Do you want to run <b>${SOURCE_FILE}</b>?</span>"
    zenity --question --text="$txt" --no-wrap --ok-label="Run" --cancel-label="Quit" --title="$PROGRAM_NAME" 2>/dev/null
}

__run_it () {
    #set +m
    ACTION="Running"
    rm "${LOGFILE}" "${ERR_LOGFILE}" 2>/dev/null
    touch "${LOGFILE}" "${ERR_LOGFILE}"
    #__save_runfile_copy "${SOURCE_FILE}"
    cd "${CACHE_DIR}" || __quit_on_error "Could not cd into ${CACHE_DIR}"
    __check_labtype_ok
    if [ -f ./monitor_log ]; then
        __monitor_file "${LOGFILE}" "${RUNFILE_NAME}"
    fi
    if __perform_run_script ; then
        if [[ -f ./test.sh ]] ; then
            if __test_result ; then
                __report_success
            else
                __report_failure "The program that checked the update results reported errors."
            fi
        else
            __report_success
        fi
    else
        __report_failure "The program performing the update reported errors."
    fi
    __cleanup
}

if [ -f "${SOURCE_FILE}" ]; then
    FILE_LS=`ls -l "${SOURCE_FILE}"`
    FILE_MD5SUM=`md5sum "${SOURCE_FILE}"`
    if [[ -r "${SOURCE_FILE}" ]]; then
        __unpack_it "${SOURCE_FILE}" "${CACHE_DIR}"

        if __ask_to_run ; then
            touch "${LOGFILE}"
            touch "${ERR_LOGFILE}"
            __run_it
        fi
    else
        __quit_on_error "${SOURCE_FILE} cannot be read."
    fi
else
    __quit_on_error "${SOURCE_FILE} does not exist."
fi


