#!/usr/bin/env bash
echo "This will mirror the primary partition to all other OS."
echo "It will not do anything with /client_home or /client_home_students"
backupAllFilesystems --config_file=/usr/local/etc/mirror/mirror.cfg.UpdateAllOS
