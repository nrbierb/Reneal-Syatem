#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Set which warnings will be reported on the status window
of the login page.
Set Internet Connected to 'No' if you if you are not connected
to the internet.

Select  'Failed' for a Lab Interface if it is permanently failed.
That might be a bad ethernet cable that you are unable to
replace or some other problem that will not be quickly fixed.

Select 'Working' as soon as the connection on that interface
is working again or if you wish to test the interface." \
-i "/usr/local/share/share/icons64/network-error.png" \
"Interface Warning Off" \
"/usr/local/share/apps/setSystemCheckWarnings.py"

