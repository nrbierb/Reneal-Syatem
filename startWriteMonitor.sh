#!/usr/bin/env bash
#start the write monitor daemon to write system information at regular
#intervals
s
tart-stop-daemon --start -b -c monitord -g monitord --exec=/usr/local/bin//writeMonitorFile
logger Started write monitor daemon
