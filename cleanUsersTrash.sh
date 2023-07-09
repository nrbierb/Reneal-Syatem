#!/usr/bin/env bash
# script meant as cron job
/usr/local/share/apps/cleanUsersTrash.py --older=14 --quiet --group-name=teacher
