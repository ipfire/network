#!/usr/bin/python

import _isys

import os
import string

mountCount = {}

## Mount a filesystem, similar to the mount system call.
# @param device The device to mount.  If bindMount is 1, this should be an
#               already mounted directory.  Otherwise, it should be a device
#               name.
# @param location The path to mount device on.
# @param fstype The filesystem type on device.  This can be disk filesystems
#               such as vfat or ext3, or pseudo filesystems such as proc or
#               selinuxfs.
# @param readOnly Should this filesystem be mounted readonly?
# @param bindMount Is this a bind mount?  (see the mount(8) man page)
# @param remount Are we mounting an already mounted filesystem?
# @return The return value from the mount system call.
def mount(device, location, fstype = "ext2", readOnly = 0, bindMount = 0, remount = 0, options = "defaults"):
    flags = None
    location = os.path.normpath(location)
    opts = string.split(options)

    # We don't need to create device nodes for devices that start with '/'
    # (like '/usbdevfs') and also some special fake devices like 'proc'.
    # First try to make a device node and if that fails, assume we can
    # mount without making a device node.  If that still fails, the caller
    # will have to deal with the exception.
    # We note whether or not we created a node so we can clean up later.

    if mountCount.has_key(location) and mountCount[location] > 0:
        mountCount[location] = mountCount[location] + 1
        return

    if readOnly or bindMount or remount:
        if readOnly:
            opts.append("ro")
        if bindMount:
            opts.append("bind")
        if remount:
            opts.append("remount")

    flags = ",".join(opts)

    #log.debug("isys.py:mount()- going to mount %s on %s with options %s" %(device, location, flags))
    rc = _isys.mount(fstype, device, location, flags)

    if not rc:
        mountCount[location] = 1

    return rc

## Unmount a filesystem, similar to the umount system call.
# @param what The directory to be unmounted.  This does not need to be the
#             absolute path.
# @param removeDir Should the mount point be removed after being unmounted?
# @return The return value from the umount system call.
def umount(what, removeDir = 1):
    what = os.path.normpath(what)

    if not os.path.isdir(what):
        raise ValueError, "isys.umount() can only umount by mount point"

    if mountCount.has_key(what) and mountCount[what] > 1:
        mountCount[what] = mountCount[what] - 1
        return

    rc = _isys.umount(what)

    if removeDir and os.path.isdir(what):
        os.rmdir(what)

    if not rc and mountCount.has_key(what):
        del mountCount[what]

    return rc
