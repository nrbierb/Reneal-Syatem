#!/bin/bash
txt="<span color =\"red\"><b>Use this program only if the normal logout does not work.
If possible save all files and close all windows before clicking ok.
Then you will be instantly logged out.</b></span>"
if yad --title="Emergency Logout" --text="$txt" --no-wrap --text-align="center" --fixed --border=20 2>/dev/null ; then
    killall -u "$USER"
fi
