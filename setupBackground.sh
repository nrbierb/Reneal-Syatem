#!/bin/bash
wkhtmltoimage -q --width 450 --height 350 ~/CodeDevelopment/systemCheck/info.html /tmp/info.png 
convert /tmp/info.png -bordercolor lightblue -frame 12x12+4+6 /tmp/framedinfo.png; 
convert /usr/share/backgrounds/ServerCautionHD.jpg /tmp/framedinfo.png -gravity northeast -composite /tmp/newbackground.jpg
