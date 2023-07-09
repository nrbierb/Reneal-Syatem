#! /bin/bash


interface_line=( `grep dhcp /etc/network/interfaces` )
if [[ ! -z $interface_line ]]; then
    interface=${interface_line[1]}
    if [[ `whoami` == "root" ]]; then
        ip link |grep $interface |grep "NO-CARRIER" > /dev/null
        if [ $? -ne 0 ]; then

            if [ $? -eq 0 ]; then
                zenity --title="Internet Control" --question --text="The internet is active. Turn off?" 2>/dev/null
                if [ $? -ne 0 ]; then
                    echo "No Change. The internet is still on."
                else
                    mktemp "/tmp/Squid-Off.XXXXXX"
                    systemctl stop squid
                fi
            else
                zenity --title="Internet Control" --question --text="The internet has been turned off by sysadmin. Turn on?" 2>/dev/null
                if [ $? -ne 0 ]; then
                    echo "No Change. The  internet is still off."
                else
                    rm /tmp/Squid-Off*
                    systemctl start squid
                    logger "Restarted squid to enable internet"
                fi
             fi
        else
            zenity --info --text="The ethernet internet interface is not connected." 2> /dev/null
        fi
    else
        zenity --error --text="You must be super user! Use sudo" 2>/dev/null
    fi
else
    zenity --error --text="You don't have any kind of interface to the internet"
fi
