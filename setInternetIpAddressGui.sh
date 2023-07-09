#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Manually set the ip address for the internet interface to
connect to the internet router. Almost always this is done
automatically by the internet router, but this app lets you
the address if you need to. You can also change the interface to
go back to automatic address setting." \
-i "/usr/local/share/share/icons64/ipaddr.png" \
"Set Internet Address" \
"/usr/local/share/apps/setInternetIpAddress.py"

