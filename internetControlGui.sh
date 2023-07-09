#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "If you have internet, turn internet browser access on or off.
This can be used to temporarily shutdown the internet while
teaching classes, etc. It does not shutdown the internet connection
or internet hardware - it just stops computers in the lab
from using it when turned off. When a user attempts to open a webpage
on the internet they will see 'The proxy Server is refusing connections.'
The local internet will still work.

This acts instantly and can be used as often as you wish without
harming the true internet hardware connection or critical internal
server internet actions. If the internet is off it turns the internet
back on." \
-i "/usr/local/share/share/icons64/internet-onoff.png" \
"Internet On/Off" \
"/usr/local/share/apps/internetControl.py"

