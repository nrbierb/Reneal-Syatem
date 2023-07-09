#!/usr/bin/env bash
# This will build a file to be used by the runner script.
# The directory that contains the files must contain a shell script file
# named run.sh that performs (or at least initiates) the runner's actions.
# The directory need not contain the special files "manifest' or 'md5sumx' --
# they will be generated in this script. All other files must be in the directory
# in the same directory tree that will be used during the exectuton. The run.sh
# script will be executed from within this directory.
# The result of this script will be a gzipped tar file with the extension .run.
# The script takes two arguments:
#   1.The directory with the files for the .run. Only files needed in this
#       package should be in this directory
#   2. The name of the resulting .run file without the .run extension -- this
#       will be added.

VERSION=0.7
__help() {
    echo "Usage: source_directory destination_filename"
    exit 0
}

__generate_target_filename () {
    #replace spaces with _
    TARGET_BASE_NAME=${TARGET_BASE_NAME// /_}
    #Strip off the extension .run if already on the filename given in the command
    if [[ "${TARGET_BASE_NAME##*.}" == "run" ]] ; then
        TARGET_BASE_NAME=${TARGET_BASE_NAME%\.*}
    fi
}

__create_compressed_file_with_zstd () {
    tar cf - . | /usr/bin/zstdmt -15 - -o "${TARGET_NO_EXT_NAME}".run
    echo "used zstd"
}

__create_compressed_file_with_lzma () {
    tar cf "${TARGET_NO_EXT_NAME}".tar .
    /usr/bin/lzma "${TARGET_NO_EXT_NAME}".tar
    mv "${TARGET_NO_EXT_NAME}".tar.lzma "${TARGET_NO_EXT_NAME}".run
}

ARG_COUNT=$#
CURRENT_DIR="$(pwd)"
TARGET_DIR="${CURRENT_DIR}"

if [[ ${ARG_COUNT} -eq 0 ]]; then
    __help
else
    case "$1" in
    "-v")
        echo "${VERSION}"
        exit 0
    ;;
    "-h")
        __help
    ;;
    *)
        if [[ -d "${1}" ]]; then
            SOURCE_DIR="${1}"
        else
            echo "The first argument is not a valid directory name"
            exit -1
        fi
        case ${ARG_COUNT} in
            1 )
                TARGET_BASE_NAME=$(basename "$SOURCE_DIR")
                ;;
            2 )
                TARGET_BASE_NAME="$2"
                ;;
            * )
                if [[ -d "${3}" ]]; then
                    TARGET_DIR="${3}"
                else
                    echo "The third argument is not a valid directory name"
                    exit -1
                fi
        esac
    esac
fi

SOURCE_DIR=$1



cd "${SOURCE_DIR}"
if [[ $? -ne 0 ]] ; then
    echo "Cannot use source directory. Quitting"
    exit -1
fi

if [ ! -f run.sh ] ; then
    echo "Missing run.sh file. Unusable, Quitting"
    exit -1
fi


rm md5sums &> /dev/null
touch manifest
find . -type f > manifest
MD5_FILE=$(mktemp)
find . -type f -exec md5sum {} \; > "${MD5_FILE}"
mv "${MD5_FILE}" ./md5sums
__generate_target_filename
TARGET_NO_EXT_NAME="${TARGET_DIR}/${TARGET_BASE_NAME}"
which /usr/bin/zstdmt > /dev/null
if [ $? -eq 0 ]; then
    __create_compressed_file_with_zstd
else
    __create_compressed_file_with_lzma
fi
cd "${CURRENT_DIR}"
