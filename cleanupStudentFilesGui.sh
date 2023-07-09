#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d """Remove personal files not for schoolwork from students
directories in /client_home_students""" \
-i "/usr/local/share/share/icons/broom.png" \
"Student Files Cleanup" \
"/usr/local/share/apps/cleanupStudentFiles.sh"

