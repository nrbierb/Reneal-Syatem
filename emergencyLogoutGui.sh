#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -G \
-d "This app should be used only if you cannot log
out normally. Any unsaved work will be lost.
It will not affect any server system processes." \
-i "/usr/local/share/share/icons64/emergency-exit.png" \
"Emergency Logout" \
"/usr/local/share/apps/emergencyLogout.sh"

