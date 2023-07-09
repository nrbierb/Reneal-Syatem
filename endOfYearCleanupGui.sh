#!/bin/bash
/usr/local/share/apps/runCommandInUI.sh -s --geometry=90x40 \
-d "Prepare the server and students setup for a new year.
This will move the student-list and the content of the
students work directories (except media files) in a folder
for the previous year. The student area is now clean for
the new year.

Run only one time each school year!" \
-i "/usr/local/share/share/icons64/fluffy-broom.png" \
"End of Year Cleanup" \
"/usr/local/share/apps/endOfYearCleanup.py"

