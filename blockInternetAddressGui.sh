#!/bin/bash
#!/usr/bin/env bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Add a new internet website to be blocked. The new entry
should be in the same form as 'youtube.com'" \
-i "/usr/local/share/share/icons64/website-block.png" \
"Block Websites" \
"/usr/local/share/apps/blockInternetAddress.py"

