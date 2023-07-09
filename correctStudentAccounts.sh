#!/bin/bash
#the teachers version is correct
cp /client_home/.user_shared_config/teacher/.config/autostart/ltsp-client-fs-mounter.desktop \
    /usr/local/etc/shared_configuration/student/.config/autostart/ltsp-client-fs-mounter.desktop
#permissons and ownership were wrong in several places
chown -R root:root /usr/local/etc/shared_configuration
find /usr/local/etc/shared_configuration -type f -exec chmod 644 {} \;
find /usr/local/etc/shared_configuration -type d -exec chmod 755 {} \;
echo Problems fixed.
echo Please log in as a student on a client to confirm success.
echo If other students are already logged in, ask them to log out and log in again.

