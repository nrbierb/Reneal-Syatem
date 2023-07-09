#!/usr/bin/env bash
/usr/local/share/apps/runCommandInUI.sh -s -a --logfile=/tmp/admin_actions.log -g 100x30 \
-d """Show the status of the server's connection to the internet.
This app is useful only if you have internet and have a cable
from the server to the internet modem. If you do not have internet
it will always report that the connection is bad.""" \
-i "/usr/local/share/share/icons64/internet-status.png" \
"View Internet Status" \
"/usr/local/share/apps/internetCheck.py"

