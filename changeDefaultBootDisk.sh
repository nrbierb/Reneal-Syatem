#!/usr/bin/env bash

PRIMARY_DISK_GRUB='grub.cfg.OSprimary'
SECONDARY_DISK_GRUB='grub.cfg.OSprimarySecondDiskDefault'
BASE_MOUNT=""

function set_grub_link () {
    #set the link to the gru used for boot in the primary disks grub directory
    pushd $BASE_MOUNT/boot/grub
    rm grub.cfg
    ln -s $1 grub.cfg
    popd
}

function set_base_mount () {

}
