#! /bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Change the password for the teacher's account.
This password will be set immediately so any logins
to the account after you choose 'OK' in this app will
need to use this password.
" \
-i "/usr/local/share/share/icons64/padlock.png" \
"Change Teacher Password" \
"/usr/local/share/apps/changeTeacherPassword.py"

