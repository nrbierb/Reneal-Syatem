#!/usr/bin/env bash
#A simple wrapper for one command and a redirect to files for stdin and stdout
VERSION=0.6
__help () {
echo "
This is a simple wrapper program that will run one command in a bash shell with
redirect of stdout and stderr to separate files. The redirects use '>>' to append
to an existing file. The return value is the return value of the script.
Usage:
scriptWrapper       show this help
scriptWrapper -h    show this help
scriptWrapper -v    version
scriptWrapper scriptname
scriptWrapper scriptname  combined_filename
scriptWrapper scriptname  stdout_filename  stderr_filename"
}

case $# in
    "0")
        __help
        ;;
    "1")
        case "${1}" in
            "-h" | "--help")
                __help
                ;;
            "-v" | "--version")
                echo $VERSION
                ;;
            *   )
                /bin/bash "${1}"
                ;;
        esac
        ;;
    "2" )
        /bin/bash "${1}" &>> "${2}"
        ;;
    * )
        /bin/bash "${1}" >> "${2}" 2>> "${3}"
        ;;
    esac
