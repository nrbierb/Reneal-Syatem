#!/bin/bash 
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "System Check checks and tests many different parts and processes
in the server. If it finds a problem it will fix it if it can and tell you
that the problem has been fixed.
If SystemCheck cannot fix the problem it report the problem
and tell you what you should do to fix the problem.

If SystemCheck reports that it needs you to perform an action to fix
a problem please do that fix action immediately. The problem will
not be fixed until you follow the instructions System Check gives
you." \
-i "/usr/local/share/share/icons64/systemCheck.png" \
"System Check" \
"/usr/local/share/apps/systemCheckWithGui.sh"
