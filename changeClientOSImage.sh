#! /bin/bash
if [[ -e /opt/ltsp/amd64 ]]; then
    if [[ `whoami` == "root" ]]; then
        dhcp_file=`readlink -f /etc/ltsp/dhcpd.conf`
        if [[ ${dhcp_file##*.} = "amd64" ]]; then
                zenity --title="Client Version Control" --question \
                    --text="You are using the 64 Bit Client OS. \nDo you want to change to 32 Bit so you can use older client computers?" 2>/dev/null
                if [ $? -ne 0 ]; then
                    zenity --title="No Change" --info --text "No Change, still Using 64 Bit OS."
                else
                    rm /etc/ltsp/dhcpd.conf
                    ln -s /etc/ltsp/dhcpd.conf.i386 /etc/ltsp/dhcpd.conf
                    if [[ ! -e /opt/ltsp/images/i386.img ]]; then
                        ltsp-update-image -n i386
                    fi
                    systemctl restart isc-dhcp-server
                    logger Changed to ltsp i386
                    zenity --title="Next Action" --info --text="Using the 32 Bit image.\nAll client computers should work.\nReboot the clients now." 2>/dev/null
                fi
            else
                zenity --title="Client Version Control" --question \
                    --text="You are using the 32 Bit Client OS. \nDo you want to change to 64 Bit OS?" 2>/dev/null
                if [ $? -ne 0 ]; then
                    zenity --title="No Change" --info --text "No Change, still Using 32 Bit OS."
                else
                    rm /etc/ltsp/dhcpd.conf
                    ln -s /etc/ltsp/dhcpd.conf.amd64 /etc/ltsp/dhcpd.conf
                    if [[ ! -e /opt/ltsp/images/amd64.img ]]; then
                        ltsp-update-image -n amd64
                    fi
                    systemctl restart isc-dhcp-server
                    logger Changed to ltsp amd64
                    zenity --title="Next Action" --info --text="Using the 64 Bit OS.\nOld Pentium 4 client computers will not work.\nReboot the clients now." 2>/dev/null
                fi
        fi
    else
        zenity --error --text="You must be super user! Use sudo" 2>/dev/null
    fi
else
    zenity --error --text="You have only a single 32 bit client 0S. No change is possible."
fi
