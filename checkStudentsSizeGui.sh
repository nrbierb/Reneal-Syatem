#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d "Show the disk space used by each student.\n
 'Guest User' can be used by many students.
  It often has many personal and copied media files
  that should not be stored on the school's computer." \
-i "/usr/local/share/share/icons64/magnify_glass.png" \
"Check Students Size" \
"/usr/local/share/apps/checkStudentsSize.sh"
