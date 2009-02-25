#
# isys.py - installer utility functions and glue for C module
#
# Copyright (C) 2001, 2002, 2003, 2004, 2005, 2006, 2007  Red Hat, Inc.
# All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author(s): Matt Wilson <msw@redhat.com>
#            Erik Troan <ewt@redhat.com>
#            Jeremy Katz <katzj@redhat.com>
#

import _isys
import string
import os
import os.path
import socket
import stat
import posix
import sys
import iutil
import warnings
import resource
import re
import struct
import pyfire.hal

import logging
log = logging.getLogger("pomona")
import warnings

mountCount = {}
raidCount = {}

MIN_RAM = _isys.MIN_RAM
EARLY_SWAP_RAM = _isys.EARLY_SWAP_RAM

## Get the amount of free space available under a directory path.
# @param path The directory path to check.
# @return The amount of free space available, in
def pathSpaceAvailable(path):
    return _isys.devSpaceFree(path)


mdadmOutput = "/tmp/mdadmout"

## An error occured when running mdadm.
class MdadmError(Exception):
    ## The constructor.
    # @param args The arguments passed to the mdadm command.
    # @param name The the name of the RAID device used in the mdadm command.
    def __init__(self, args, name=None):
        self.args = args
        self.name = name
        self.log = self.getCmdOutput()

    ## Get the output of the last mdadm command run.
    # @return The formatted output of the mdadm command which caused an error.
    def getCmdOutput(self):
        f = open(mdadmOutput, "r")
        lines = reduce(lambda x,y: x + [string.strip(y),], f.readlines(), [])
        lines = string.join(reduce(lambda x,y: x + ["   %s" % (y,)], \
                                    lines, []), "\n")
        return lines

    def __str__(self):
        s = ""
        if not self.name is None:
            s = " for device %s" % (self.name,)
        command = "mdadm " + string.join(self.args, " ")
        return "'%s' failed%s\nLog:\n%s" % (command, s, self.log)

def _mdadm(*args):
    try:
        lines = iutil.execWithCapture("mdadm", args, stderr = mdadmOutput)
        lines = string.split(lines, '\n')
        lines = reduce(lambda x,y: x + [y.strip(),], lines, [])
        return lines
    except:
        raise MdadmError, args

def _getRaidInfo(drive):
    log.info("mdadm -E %s" % (drive,))
    try:
        lines = _mdadm("-E", drive)
    except MdadmError:
        ei = sys.exc_info()
        ei[1].name = drive
        raise ei[0], ei[1], ei[2]

    info = {
            'major': "-1",
            'minor': "-1",
            'uuid' : "",
            'level': -1,
            'nrDisks': -1,
            'totalDisks': -1,
            'mdMinor': -1,
        }

    for line in lines:
        vals = string.split(string.strip(line), ' : ')
        if len(vals) != 2:
            continue
        if vals[0] == "Version":
            vals = string.split(vals[1], ".")
            info['major'] = vals[0]
            info['minor'] = vals[1]
        elif vals[0] == "UUID":
            info['uuid'] = vals[1]
        elif vals[0] == "Raid Level":
            info['level'] = int(vals[1][4:])
        elif vals[0] == "Raid Devices":
            info['nrDisks'] = int(vals[1])
        elif vals[0] == "Total Devices":
            info['totalDisks'] = int(vals[1])
        elif vals[0] == "Preferred Minor":
            info['mdMinor'] = int(vals[1])
        else:
            continue

    if info['uuid'] == "":
        raise ValueError, info

    return info

def _stopRaid(mdDevice):
    log.info("mdadm --stop %s" % (mdDevice,))
    try:
        _mdadm("--stop", mdDevice)
    except MdadmError:
        ei = sys.exc_info()
        ei[1].name = mdDevice
        raise ei[0], ei[1], ei[2]

def raidstop(mdDevice):
    log.info("stopping raid device %s" %(mdDevice,))
    if raidCount.has_key (mdDevice):
        if raidCount[mdDevice] > 1:
            raidCount[mdDevice] = raidCount[mdDevice] - 1
            return
        del raidCount[mdDevice]

    devInode = "/dev/%s" % mdDevice

    try:
        _stopRaid(devInode)
    except:
        pass

def _startRaid(mdDevice, mdMinor, uuid):
    log.info("mdadm -A --uuid=%s --super-minor=%s %s" % (uuid, mdMinor, mdDevice))
    try:
        _mdadm("-A", "--uuid=%s" % (uuid,), "--super-minor=%s" % (mdMinor,), \
                mdDevice)
    except MdadmError:
        ei = sys.exc_info()
        ei[1].name = mdDevice
        raise ei[0], ei[1], ei[2]

def raidstart(mdDevice, aMember):
    log.info("starting raid device %s" %(mdDevice,))
    if raidCount.has_key(mdDevice) and raidCount[mdDevice]:
        raidCount[mdDevice] = raidCount[mdDevice] + 1
        return

    raidCount[mdDevice] = 1

    mdInode = "/dev/%s" % mdDevice
    mbrInode = "/dev/%s" % aMember

    if os.path.exists(mdInode):
        minor = os.minor(os.stat(mdInode).st_rdev)
    else:
        minor = int(mdDevice[2:])
    try:
        info = _getRaidInfo(mbrInode)
        if info.has_key('mdMinor'):
            minor = info['mdMinor']
        _startRaid(mdInode, minor, info['uuid'])
    except:
        pass

## Remove the superblock from a RAID device.
# @param device The complete path to the RAID device name to wipe.
def wipeRaidSB(device):
    try:
        fd = os.open(device, os.O_WRONLY)
    except OSError, e:
        log.warning("error wiping raid device superblock for %s: %s", device, e)
        return

    try:
        _isys.wiperaidsb(fd)
    finally:
        os.close(fd)
    return

## Get the raw superblock from a RAID device.
# @param The basename of a RAID device to check.  This device node does not
#        need to exist to begin with.
# @return A RAID superblock in its raw on-disk format.
def raidsb(mdDevice):
    return raidsbFromDevice("/dev/%s" % mdDevice)

## Get the superblock from a RAID device.
# @param The full path to a RAID device name to check.  This device node must
#        already exist.
# @return A tuple of the contents of the RAID superblock, or ValueError on
#         error.
def raidsbFromDevice(device):
    try:
        info = _getRaidInfo(device)
        return (info['major'], info['minor'], info['uuid'], info['level'],
                info['nrDisks'], info['totalDisks'], info['mdMinor'])
    except:
        raise ValueError

def getRaidChunkFromDevice(device):
    fd = os.open(device, os.O_RDONLY)
    rc = 64
    try:
        rc = _isys.getraidchunk(fd)
    finally:
        os.close(fd)
    return rc

## Set up an already existing device node to be used as a loopback device.
# @param device The full path to a device node to set up as a loopback device.
# @param file The file to mount as loopback on device.
# @param readOnly Should this loopback device be used read-only?
def losetup(device, file, readOnly = 0):
    if readOnly:
        mode = os.O_RDONLY
    else:
        mode = os.O_RDWR
    targ = os.open(file, mode)
    loop = os.open(device, mode)
    try:
        _isys.losetup(loop, targ, file)
    finally:
        os.close(loop)
        os.close(targ)

def lochangefd(device, file):
    loop = os.open(device, os.O_RDONLY)
    targ = os.open(file, os.O_RDONLY)
    try:
        _isys.lochangefd(loop, targ)
    finally:
        os.close(loop)
        os.close(targ)

## Disable a previously setup loopback device.
# @param device The full path to an existing loopback device node.
def unlosetup(device):
    loop = os.open(device, os.O_RDONLY)
    try:
        _isys.unlosetup(loop)
    finally:
        os.close(loop)

def ddfile(file, megs, pw = None):
    buf = '\x00' * (1024 * 256)

    fd = os.open(file, os.O_RDWR | os.O_CREAT)

    total = megs * 4            # we write out 1/4 of a meg each time through

    if pw:
        (fn, title, text) = pw
        win = fn(title, text, total - 1)

    for n in range(total):
        os.write(fd, buf)
        if pw:
            win.set(n)

    if pw:
        win.pop()

    os.close(fd)

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

    log.debug("isys.py:mount()- going to mount %s on %s with options %s" %(device, location, flags))
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

## Get the SMP status of the system.
# @return True if this is an SMP system, False otherwise.
def smpAvailable():
    return _isys.smpavailable()

htavailable = _isys.htavailable

## Disable swap.
# @param path The full path of the swap device to disable.
def swapoff(path):
    return _isys.swapoff (path)

## Enable swap.
# @param path The full path of the swap device to enable.
def swapon(path):
    return _isys.swapon (path)

## Load a keyboard layout for text mode installs.
# @param keymap The keyboard layout to load.  This must be one of the values
#               from rhpl.KeyboardModels.
def loadKeymap(keymap):
    return _isys.loadKeymap (keymap)

cachedDrives = None

## Clear the drive dict cache.
# This method clears the drive dict cache.  If the drive state changes (by
# loading and unloading modules, attaching removable devices, etc.) then this
# function must be called before any of the *DriveDict or *DriveList functions.
# If not, those functions will return information that does not reflect the
# current machine state.
def flushDriveDict():
    global cachedDrives
    cachedDrives = None

def driveDict(klassArg):
    import parted
    global cachedDrives
    if cachedDrives is None:
        new = {}
        for dev in pyfire.hal.get_devices_by_type("storage"):
            if dev['device'] is None: # none devices make no sense
                continue

            device = dev['device'].replace('/dev/','')
            # we can't actually use the sg devices, so ignore them
            if device.startswith("sg"):
                log.info("ignoring sg device %s" %(device,))
                continue

            # we can't actually use the st devices, so ignore them
            if device.startswith("st"):
                log.info("ignoring st device %s" %(device,))
                continue

            # we want to ignore md devices as they're not hard disks in our pov
            if device.startswith("md"):
                continue

            if dev['storage.drive_type'] != 'disk':
                new[device] = dev
                continue
            try:
                if not mediaPresent(device):
                    new[device] = dev
                    continue

                if device.startswith("sd"):
                    peddev = parted.PedDevice.get(dev['device'])
                    model = peddev.model

                    del peddev
                new[device] = dev
            except Exception, e:
                log.debug("exception checking disk blacklist on %s: %s" % \
                        (device, e))
        cachedDrives = new

    ret = {}
    for key,dev in cachedDrives.items():
        if dev['storage.drive_type'] == klassArg:
            ret[key] = dev
    return ret

## Get all the hard drives attached to the system.
# This method queries the drive dict cache for all hard drives.  If the cache
# is empty, this will cause all disk devices to be probed.  If the status of
# the devices has changed, flushDriveDict must be called first.
#
# @see flushDriveDict
# @see driveDict
# @return A dict of all the hard drive descriptions, keyed on device name.
def hardDriveDict():
    ret = {}
    dict = driveDict("disk")
    for item in dict.keys():
        try:
            ret[item] = dict[item]['description']
        except AttributeError:
            ret[item] = ""
    return ret

## Get all the removable drives attached to the system.
# This method queries the drive dict cache for all removable drives.  If the cache
# is empty, this will cause all disk devices to be probed.  If the status of
# the devices has changed, flushDriveDict must be run called first.
#
# @see flushDriveDict
# @see driveDict
# @return A dict of all the removable drive descriptions, keyed on device name.
def removableDriveDict():
    ret = {}
    dict = driveDict("disk")
    for item in dict.keys():
        if dict[item]['storage.removable'] != 0:
            try:
                ret[item] = dict[item]['description']
            except AttributeError:
                ret[item] = ""
    return ret

## Get all CD/DVD drives attached to the system.
# This method queries the drive dict cache for all hard drives.  If the cache
# is empty, this will cause all disk devices to be probed.  If the status of
# the devices has changed, flushDriveDict must be called first.
#
# @see flushDriveDict
# @see driveDict
# @return A sorted list of all the CD/DVD drives, without any leading /dev/.
def cdromList():
    list = driveDict("cdrom").keys()
    list.sort()
    return list

## Get all tape drives attached to the system.
# This method queries the drive dict cache for all hard drives.  If the cache
# is empty, this will cause all disk devices to be probed.  If the status of
# the devices has changed, flushDriveDict must be called first.
#
# @see flushDriveDict
# @see driveDict
# @return A sorted list of all the tape drives, without any leading /dev/.
def tapeDriveList():
    list = driveDict("tape").keys()
    list.sort()
    return list

## Calculate the broadcast address of a network.
# @param ip An IPv4 address as a string.
# @param nm A corresponding netmask as a string.
# @return A tuple of network address and broadcast address strings.
def inet_calcNetBroad(ip, nm):
    (ipaddr,) = struct.unpack('I', socket.inet_pton(socket.AF_INET, ip))
    ipaddr = socket.ntohl(ipaddr)

    (nmaddr,) = struct.unpack('I', socket.inet_pton(socket.AF_INET, nm))
    nmaddr = socket.ntohl(nmaddr)

    netaddr = ipaddr & nmaddr
    bcaddr = netaddr | (~nmaddr)

    nw = socket.inet_ntop(socket.AF_INET, struct.pack('!I', netaddr))
    bc = socket.inet_ntop(socket.AF_INET, struct.pack('!I', bcaddr))

    return (nw, bc)

def doProbeBiosDisks():
    return _isys.biosDiskProbe()

def doGetBiosDisk(mbrSig):
    return _isys.getbiosdisk(mbrSig)

biosdisks = {}
for d in range(80, 80 + 15):
    disk = doGetBiosDisk("%d" %(d,))
    #print "biosdisk of %s is %s" %(d, disk)
    if disk is not None:
        biosdisks[disk] = d

def compareDrives(first, second):
    if biosdisks.has_key(first) and biosdisks.has_key(second):
        one = biosdisks[first]
        two = biosdisks[second]
        if (one < two):
            return -1
        elif (one > two):
            return 1

    if first.startswith("hd"):
        type1 = 0
    elif first.startswith("sd"):
        type1 = 1
    elif (first.startswith("vd") or first.startswith("xvd")):
        type1 = -1
    else:
        type1 = 2

    if second.startswith("hd"):
        type2 = 0
    elif second.startswith("sd"):
        type2 = 1
    elif (second.startswith("vd") or second.startswith("xvd")):
        type2 = -1
    else:
        type2 = 2

    if (type1 < type2):
        return -1
    elif (type1 > type2):
        return 1
    else:
        len1 = len(first)
        len2 = len(second)

        if (len1 < len2):
            return -1
        elif (len1 > len2):
            return 1
        else:
            if (first < second):
                return -1
            elif (first > second):
                return 1

    return 0

def readFSUuid(device):
    if not os.path.exists(device):
        device = "/dev/%s" % device

    label = _isys.getblkid(device, "UUID")
    return label

def readFSLabel(device):
    if not os.path.exists(device):
        device = "/dev/%s" % device

    label = _isys.getblkid(device, "LABEL")
    return label

def readFSType(device):
    if not os.path.exists(device):
        device = "/dev/%s" % device

    fstype = _isys.getblkid(device, "TYPE")
    if fstype is None:
        # FIXME: libblkid doesn't show physical volumes as having a filesystem
        # so let's sniff for that.(#409321)
        try:
            fd = os.open(device, os.O_RDONLY)
            buf = os.read(fd, 2048)
        except:
            return fstype
        finally:
            try:
                os.close(fd)
            except:
                pass


    if fstype == "ext4":
        return "ext4dev"
    return fstype

def ext2Clobber(device):
    _isys.e2fsclobber(device)

def ext2IsDirty(device):
    label = _isys.e2dirty(device)
    return label

def ext2HasJournal(device):
    hasjournal = _isys.e2hasjournal(device);
    return hasjournal

def ejectCdrom(device):
    fd = os.open(device, os.O_RDONLY|os.O_NONBLOCK)

    # this is a best effort
    try:
        _isys.ejectcdrom(fd)
    except SystemError, e:
        log.warning("error ejecting cdrom (%s): %s" %(device, e))
        pass

    os.close(fd)

def driveUsesModule(device, modules):
    """Returns true if a drive is using a prticular module.  Only works
       for SCSI devices right now."""

    if not isinstance(modules, ().__class__) and not \
                    isinstance(modules, [].__class__):
        modules = [modules]

    if device[:2] == "hd":
        return False
    rc = False
    if os.access("/tmp/scsidisks", os.R_OK):
        sdlist=open("/tmp/scsidisks", "r")
        sdlines = sdlist.readlines()
        sdlist.close()
        for l in sdlines:
            try:
                # each line has format of:  <device>  <module>
                (sddev, sdmod) = string.split(l)

                if sddev == device:
                    if sdmod in modules:
                        rc = True
                        break
            except:
                pass
    return rc

## Check if a removable media drive (CD, USB key, etc.) has media present.
# @param device The basename of the device node.
# @return True if media is present in device, False otherwise.
def mediaPresent(device):
    try:
        fd = os.open("/dev/%s" % device, os.O_RDONLY)
    except OSError, (errno, strerror):
        # error 123 = No medium found
        if errno == 123:
            return False
        else:
            return True
    else:
        os.close(fd)
        return True

def vtActivate(num):
    _isys.vtActivate (num)

def isPsudoTTY(fd):
    return _isys.isPseudoTTY(fd)

## Flush filesystem buffers.
def sync():
    return _isys.sync ()

handleSegv = _isys.handleSegv
printObject = _isys.printObject
isVioConsole = _isys.isVioConsole
