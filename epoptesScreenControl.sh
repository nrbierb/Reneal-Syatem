#! /bin/bash
SCALE_RESOLUTION="1024x768"
if [[ `/usr/local/bin/scaleScreen -S` == "No" ]]; then
    zenity --title="Epoptes Screen" --question --text="Setup for epoptes screen share?" 2>/dev/null
    if [[ $? -ne 0 ]]; then
        echo "No Change"
    else
        echo Set
        /usr/local/bin/scaleScreen  -s $SCALE_RESOLUTION
    fi
else
    zenity --title="Epoptes Screen" --question --text="Return screen to normal?" 2>/dev/null
    if [[ $? -ne 0 ]]; then
        echo "No Change"
    else
        echo Reset
        /usr/local/bin/scaleScreen -r
    fi
fi
