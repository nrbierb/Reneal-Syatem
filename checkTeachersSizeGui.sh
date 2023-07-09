#!/usr/bin/env bash
/usr/local/share/apps/runCommandInUI.sh -s -G \
-d 'Get the size of each teachers personal directory.\n
Total size includes everything,
Trash size only includes the files in Trash.  It should be very small.
Media size includes all videos and music.  If this is large,
the teacher may be using the computer for personal storage.\n
The program may run for a minute or more if there are many
teacher accounts.' \
-i "/usr/local/share/share/icons64/magnify_glass.png" \
"Check Teachers Size" \
"/usr/local/share/apps/checkTeachersSize.sh"
