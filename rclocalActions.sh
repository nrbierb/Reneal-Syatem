#!/usr/bin/env bash
#Verison 0.9
#setup initial login screen
/usr/local/share/apps/updateLoginBackground.py --initial-screen
#Cleanup entire system, rebuild all student home files
/usr/local/share/apps/systemCleanup.py --force_student_logout
#assure that multicast route is set after bond0 is alive
ip route add 232.43.0.0/16 dev bond0
#assure that key files have correct permissions
/usr/local/share/apps/resetLdso.py
#assure that all daemons are alive
systemCheck -c -k -n -q -o /tmp/startupSystemCheck
sleep 30
#update login screen with status after settling
/usr/local/share/apps/updateLoginBackground.py
