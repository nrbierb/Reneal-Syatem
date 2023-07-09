#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s \
-d "Update the student list file that is used by the
Student Sign In window when students log in. This list is
important because no student's personal area can be created
without their name in the list.
This app starts by opening a file choice dialog where you can
choose one or more files of students information that are
added in a special form to the servers student_list file. The
files of information can contain the names of students already
in the list because the student will be added to the list only
once. When you have chosen the files the app will show the
number of students added and the the total number of students.
Read the Help page or the Reneal Admin manual before using this
app for the first time." \
-i "/usr/local/share/share/icons64/item_list.png" \
"Update Student List" \
"/usr/local/share/apps/updateStudentList.py -g"

