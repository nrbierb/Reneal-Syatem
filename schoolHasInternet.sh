#!/usr/bin/env bash
# set the link to the correct file for systemCheck
# this will set the default value for the button to check internet

#code concept from "bash Cookbook"
read -p "Does this school have internet? (Yn)" answer
[ -z "$answer" ] && answer="y"

case "$answer" in
    [yY1] ) rm /etc/systemCheck.conf
        ln -s /etc/systemCheck.conf.with_internet /etc/systemCheck.conf
        printf "systemCheck will test the internet connection when it runs.\n"
        # error check
        ;;
    [nN0] ) rm /etc/systemCheck.conf
        ln -s /etc/systemCheck.conf.no_internet /etc/systemCheck.conf
        printf "systemCheck won't test the internet connection when it runs.\n"
        # error check
        ;;
    *     ) printf "%b" "Unexpected answer. '$answer'!  Nothing done.\n" >&2 ;;
esac

