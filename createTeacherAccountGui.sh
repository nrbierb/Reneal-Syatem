#! /bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Create a new teacher account.
The account name will be the first letter of the first name,
a '_' and the last name. The password will be the birthdate
but without the '/'s for example 01052000.
The password may be changed after creating the account using
the Change Teacher Password app." \
-i "/usr/local/share/share/icons64/male-add.png" \
"Create Teacher Account" \
"/usr/local/share/apps/createTeacherAccount.sh"

