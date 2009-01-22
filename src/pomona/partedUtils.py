#
# partedUtils.py: helper functions for use with parted objects
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Karsten Hopp <karsten@redhat.com>
#
# Copyright 2002-2003 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Helper functions for use when dealing with parted objects."""

import parted
import math
import os, sys, string, struct, resource

import fsset
import inutil, isys
import pyfire
from flags import flags
from partErrors import *
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

import logging
log = logging.getLogger("pomona")

fsTypes = {}

fs_type = parted.file_system_type_get_next ()
while fs_type:
    fsTypes[fs_type.name] = fs_type
    fs_type = parted.file_system_type_get_next (fs_type)

def get_flags(part):
    """Retrieve a list of strings representing the flags on the partition."""
    string=""
    if not part.is_active ():
        return string
    first=1
    flag = parted.partition_flag_next (0)
    while flag:
        if part.get_flag (flag):
            string = string + parted.partition_flag_get_name (flag)
            if first:
                first = 0
            else:
                string = string + ", "
        flag = parted.partition_flag_next(flag)
    return string

def start_sector_to_cyl(device, sector):
    """Return the closest cylinder (round down) to sector on device."""
    return int(math.floor((float(sector) / (device.heads * device.sectors)) + 1))

def end_sector_to_cyl(device, sector):
    """Return the closest cylinder (round up) to sector on device."""
    return int(math.ceil(float((sector + 1)) / (device.heads * device.sectors)))

def start_cyl_to_sector(device, cyl):
    "Return the sector corresponding to cylinder as a starting cylinder."
    return long((cyl - 1) * (device.heads * device.sectors))

def end_cyl_to_sector(device, cyl):
    "Return the sector corresponding to cylinder as a ending cylinder."
    return long(((cyl) * (device.heads * device.sectors)) - 1)

def getPartSize(partition):
    """Return the size of partition in sectors."""
    return partition.geom.length

def getPartSizeMB(partition):
    """Return the size of partition in megabytes."""
    return (partition.geom.length * partition.geom.dev.sector_size / 1024.0 / 1024.0)

def getDeviceSizeMB(dev):
    """Return the size of dev in megabytes."""
    return (float(dev.heads * dev.cylinders * dev.sectors) / (1024 * 1024) * dev.sector_size)

def get_partition_by_name(disks, partname):
    """Return the parted part object associated with partname.

    Arguments:
    disks -- Dictionary of diskname->PedDisk objects
    partname -- Name of partition to find

    Return:
    PedPartition object with name partname.  None if no such partition.
    """
    for diskname in disks.keys():
        disk = disks[diskname]
        part = disk.next_partition()
        while part:
            if get_partition_name(part) == partname:
                return part

            part = disk.next_partition(part)

    return None

def get_partition_name(partition):
    """Return the device name for the PedPartition partition."""
    if (partition.geom.dev.type == parted.DEVICE_DAC960
                    or partition.geom.dev.type == parted.DEVICE_CPQARRAY):
        return "%sp%d" % (partition.geom.dev.path[5:], partition.num)
    if (parted.__dict__.has_key("DEVICE_SX8") and
                    partition.geom.dev.type == parted.DEVICE_SX8):
        return "%sp%d" % (partition.geom.dev.path[5:], partition.num)

    drive = partition.geom.dev.path[5:]
    if (drive.startswith("cciss") or drive.startswith("ida") or
                    drive.startswith("rd") or drive.startswith("sx8") or
                    drive.startswith("mapper")):
        sep = "p"
    else:
        sep = ""
    return "%s%s%d" % (partition.geom.dev.path[5:], sep, partition.num)


def get_partition_file_system_type(part):
    """Return the file system type of the PedPartition part.

    Arguments:
    part -- PedPartition object

    Return:
    Filesystem object (as defined in fsset.py)
    """
    if part.fs_type is None and part.native_type == 0x41:
        ptype = fsset.fileSystemTypeGet("PPC PReP Boot")
    elif part.fs_type == None:
        return None
    elif part.fs_type.name == "linux-swap":
        ptype = fsset.fileSystemTypeGet("swap")
    elif (part.fs_type.name == "FAT" or part.fs_type.name == "fat16"
                            or part.fs_type.name == "fat32"):
        ptype = fsset.fileSystemTypeGet("vfat")
    else:
        try:
            ptype = fsset.fileSystemTypeGet(part.fs_type.name)
        except:
            ptype = fsset.fileSystemTypeGet("foreign")

    return ptype


def set_partition_file_system_type(part, fstype):
    """Set partition type of part to PedFileSystemType implied by fstype."""
    if fstype == None:
        return
    try:
        for flag in fstype.getPartedPartitionFlags():
            if not part.is_flag_available(flag):
                raise PartitioningError, ("requested FileSystemType needs "
                                                                                                                        "a flag that is not available.")
            part.set_flag(flag, 1)
            part.set_system(fstype.getPartedFileSystemType())
    except:
        print "Failed to set partition type to ",fstype.getName()
        pass

def get_partition_drive(partition):
    """Return the device name for disk that PedPartition partition is on."""
    return "%s" % (partition.geom.dev.path[5:])

def get_max_logical_partitions(disk):
    if not disk.type.check_feature(parted.DISK_TYPE_EXTENDED):
        return 0
    dev = disk.dev.path[5:]
    for key in max_logical_partition_count.keys():
        if dev.startswith(key):
            return max_logical_partition_count[key]
    # FIXME: if we don't know about it, should we pretend it can't have
    # logicals?  probably safer to just use something reasonable
    return 11

def map_foreign_to_fsname(type):
    """Return the partition type associated with the numeric type."""
    if type in allPartitionTypesDict.keys():
        return allPartitionTypesDict[type]
    else:
        return _("Foreign")

def filter_partitions(disk, func):
    rc = []
    part = disk.next_partition ()
    while part:
        if func(part):
            rc.append(part)
        part = disk.next_partition(part)

    return rc

def get_all_partitions(disk):
    """Return a list of all PedPartition objects on disk."""
    func = lambda part: part.is_active()
    return filter_partitions(disk, func)

def get_logical_partitions(disk):
    """Return a list of logical PedPartition objects on disk."""
    func = lambda part: (part.is_active() and part.type & parted.PARTITION_LOGICAL)
    return filter_partitions(disk, func)

def get_primary_partitions(disk):
    """Return a list of primary PedPartition objects on disk."""
    func = lambda part: part.type == parted.PARTITION_PRIMARY
    return filter_partitions(disk, func)

def getDefaultDiskType():
    """Get the default partition table type for this architecture."""
    return parted.disk_type_get("msdos")

archLabels = {'i386': ['msdos', 'gpt']}

def checkDiskLabel(disk, intf):
    """Check that the disk label on disk is valid for this machine type."""
    if disk.type.name == "msdos":
        return 0

    if intf:
        rc = intf.messageWindow(_("Warning"),
                                _("/dev/%s currently has a %s partition "
                                  "layout.  To use this drive for "
                                  "the installation of %s, it must be "
                                  "re-initialized, causing the loss of "
                                  "ALL DATA on this drive.\n\n"
                                  "Would you like to re-initialize this "
                                  "drive?")
                                %(disk.dev.path[5:], disk.type.name, name),
                                  type="custom", custom_buttons = [ _("_Ignore drive"),
                                  _("_Re-initialize drive") ], custom_icon="question")

        if rc == 0:
            return 1
        else:
            return -1
    else:
        return 1

# attempt to associate a parted filesystem type on a partition that
# didn't probe as one type or another.
def validateFsType(part):
    # we only care about primary and logical partitions
    if not part.type in (parted.PARTITION_PRIMARY,  parted.PARTITION_LOGICAL):
        return
    # if the partition already has a type, no need to search
    if part.fs_type:
        return

    # first fsystem to probe wins, so sort the types into a preferred
    # order.
    fsnames = fsTypes.keys()
    goodTypes = ['ext3', 'ext2']
    badTypes = ['linux-swap',]
    for fstype in goodTypes:
        fsnames.remove(fstype)
    fsnames = goodTypes + fsnames
    for fstype in badTypes:
        fsnames.remove(fstype)
    fsnames.extend(badTypes)

    # now check each type, and set the partition system accordingly.
    for fsname in fsnames:
        fstype = fsTypes[fsname]
        if fstype.probe_specific(part.geom) != None:
            # XXX verify that this will not modify system type
            # in the case where a user does not modify partitions
            part.set_system(fstype)
    return

def isLinuxNativeByNumtype(numtype):
    """Check if the type is a 'Linux native' filesystem."""
    linuxtypes = [0x82, 0x83, 0x8e, 0xfd]

    for t in linuxtypes:
        if int(numtype) == t:
            return 1

    return 0

def sniffFilesystemType(device):
    """Sniff to determine the type of fs on device.

    device - name of device to sniff.  we try to create it if it doesn't exist.
    """

    if os.access(device, os.O_RDONLY):
        dev = device
    else:
        dev = "/tmp/" + device

    pagesize = resource.getpagesize()
    if pagesize > 2048:
        num = pagesize
    else:
        num = 2048

    try:
        fd = os.open(dev, os.O_RDONLY)
        buf = os.read(fd, num)
    except:
        return None
    finally:
        try:
            os.close(fd)
        except:
            pass

    if len(buf) < pagesize:
        try:
            log.error("Tried to read pagesize for %s in sniffFilesystemType and only read %s", dev, len(buf))
        except:
            pass
        return None

    # ext2 check
    if struct.unpack("<H", buf[1080:1082]) == (0xef53,):
        if isys.ext2HasJournal(dev):
            return "ext3"
        else:
            return "ext2"

    # xfs signature
    if buf.startswith("XFSB"):
        return "xfs"

    # 2.6 doesn't support version 0, so we don't like SWAP-SPACE
    if (buf[pagesize - 10:] == "SWAPSPACE2"):
        return "swap"

    if fsset.isValidReiserFS(dev):
        return "reiserfs"

    # FIXME:  we don't look for vfat
    ### XXX Check for reiser4

    return None

class DiskSet:
    """The disks in the system."""

    skippedDisks = []

    def __init__ (self, pomona = None):
        self.disks = {}
        self.onlyPrimary = None
        self.pomona = pomona

    def onlyPrimaryParts(self):
        for disk in self.disks.values():
            if disk.type.check_feature(parted.DISK_TYPE_EXTENDED):
                return 0

        return 1

    def getLabels(self):
        """Return a list of all of the labels used on partitions."""
        labels = {}

        drives = self.disks.keys()
        drives.sort()

        for drive in drives:
            disk = self.disks[drive]
            func = lambda part: (part.is_active() and
                          not (part.get_flag(parted.PARTITION_RAID)
                          or part.get_flag(parted.PARTITION_LVM)))
            parts = filter_partitions(disk, func)
            for part in parts:
                node = get_partition_name(part)
                label = isys.readFSLabel(node)
                if label:
                    labels[node] = label

        return labels

    def findExistingRootPartitions(self, upgradeany = 0):
        """Return a list of all of the partitions which look like a root fs."""
        rootparts = []

        drives = self.disks.keys()
        drives.sort()

        for drive in drives:
            disk = self.disks[drive]
            part = disk.next_partition()
            while part:
                if (part.is_active() and (part.get_flag(parted.PARTITION_RAID)
                        or part.get_flag(parted.PARTITION_LVM))):
                    pass
                elif (part.fs_type and part.fs_type.name in fsset.getUsableLinuxFs()):
                    node = get_partition_name(part)

                try:
                    isys.mount(node, self.pomona.rootPath, part.fs_type.name)
                except SystemError, (errno, msg):
                    part = disk.next_partition(part)
                    continue

                if os.access(self.pomona.rootPath + '/etc/fstab', os.R_OK):
                    rootparts.append ((node, part.fs_type.name))

                isys.umount(self.pomona.rootPath)

                part = disk.next_partition(part)

        return rootparts

    def driveList(self):
        """Return the list of drives on the system."""
        drives = isys.hardDriveDict().keys()
        drives.sort (isys.compareDrives)
        return drives

    def drivesByName(self):
        """Return a dictionary of the drives on the system."""
        return isys.hardDriveDict()

    def savePartitions(self):
        """Write the partition tables out to the disks."""
        for disk in self.disks.values():
            if disk.dev.path[5:].startswith("sd") and disk.get_last_partition_num() > 15:
                log.debug("not saving partition table of disk with > 15 partitions")
                del disk
                continue

            log.info("disk.commit() for %s" % (disk.dev.path,))
            try:
                disk.commit()
            except:
                # if this fails, remove the disk so we don't use it later
                # Basically if we get here, badness has happened and we want
                # to prevent tracebacks from ruining the day any more.
                del disk
                continue

        self.refreshDevices()

    def refreshDevices(self):
        """Reread the state of the disks as they are on disk."""
        self.closeDevices()
        self.disks = {}
        self.openDevices()

    def closeDevices(self):
        """Close all of the disks which are open."""
        for disk in self.disks.keys():
            #self.disks[disk].close()
            del self.disks[disk]

    def clearDevices(self):
        def inClearDevs (drive, clearDevs):
            return (clearDevs is None) or (len(clearDevs) == 0) or (drive in clearDevs)

        clearDevs = []

        for drive in self.driveList():
            # ignoredisk takes precedence over clearpart (#186438).
            if drive in DiskSet.skippedDisks:
                continue

            deviceFile = "/dev/" + drive

            if not isys.mediaPresent(drive):
                DiskSet.skippedDisks.append(drive)
                continue

            try:
                dev = parted.PedDevice.get(deviceFile)
            except parted.error, msg:
                DiskSet.skippedDisks.append(drive)
                continue

    def openDevices(self):
        """Open the disks on the system and skip unopenable devices."""

        if self.disks:
            return

        if self.pomona is None:
            intf = None
            zeroMbr = None
        else:
            intf = self.pomona.intf
            zeroMbr = self.pomona.id.partitions.zeroMbr

        for drive in self.driveList():
            # ignoredisk takes precedence over clearpart (#186438).
            if drive in DiskSet.skippedDisks:
                continue
            deviceFile = "/dev/" + drive
            if not isys.mediaPresent(drive):
                DiskSet.skippedDisks.append(drive)
                continue

            clearDevs = []
            initAll = False

            try:
                dev = parted.PedDevice.get(deviceFile)
            except parted.error, msg:
                DiskSet.skippedDisks.append(drive)
                continue

            try:
                disk = parted.PedDisk.new(dev)
                self.disks[drive] = disk
            except parted.error, msg:
                recreate = 0
                if zeroMbr:
                    log.error("zeroMBR was set and invalid partition table "
                              "found on %s" % (dev.path[5:]))
                    recreate = 1
                elif intf is None:
                    DiskSet.skippedDisks.append(drive)
                    continue
                else:
                    format = drive

                    # if pomona is None here, we are called from labelFactory
                    if self.pomona is not None:
                        rc = intf.messageWindow(_("Warning"),
                                                _("The partition table on device %s was unreadable. "
                                                  "To create new partitions it must be initialized, "
                                                  "causing the loss of ALL DATA on this drive.\n\n"
                                                  "This operation will override any previous "
                                                  "installation choices about which drives to "
                                                  "ignore.\n\n"
                                                  "Would you like to initialize this drive, "
                                                  "erasing ALL DATA?") % (format,), type = "yesno")
                        if rc == 0:
                            DiskSet.skippedDisks.append(drive)
                            continue
                        elif rc != 0:
                            recreate = 1
                    else:
                        DiskSet.skippedDisks.append(drive)
                        continue

                if recreate == 1:
                    try:
                        disk = dev.disk_new_fresh(getDefaultDiskType())
                        disk.commit()
                    except parted.error, msg:
                        DiskSet.skippedDisks.append(drive)
                        continue

                    try:
                        disk = parted.PedDisk.new(dev)
                        self.disks[drive] = disk
                    except parted.error, msg:
                        DiskSet.skippedDisks.append(drive)
                        continue

            filter_partitions(disk, validateFsType)

            # check for more than 15 partitions (libata limit)
            if drive.startswith('sd') and disk.get_last_partition_num() > 15:
                rc = intf.messageWindow(_("Warning"),
                                        _("The drive /dev/%s has more than 15 "
                                          "partitions on it.  The SCSI "
                                          "subsystem in the Linux kernel does "
                                          "not allow for more than 15 partitons "
                                          "at this time.  You will not be able "
                                          "to make changes to the partitioning "
                                          "of this disk or use any partitions "
                                          "beyond /dev/%s15 in %s")
                                        % (drive, drive, name), type="custom",
                                           custom_buttons = [_("_Reboot"), _("_Continue")],
                                           custom_icon="warning")
                if rc == 0:
                    sys.exit(0)

            # check that their partition table is valid for their architecture
            ret = checkDiskLabel(disk, intf)
            if ret == 1:
                DiskSet.skippedDisks.append(drive)
                continue
            elif ret == -1:
                try:
                    disk = dev.disk_new_fresh(getDefaultDiskType())
                    disk.commit()
                except parted.error, msg:
                    DiskSet.skippedDisks.append(drive)
                    continue
                try:
                    disk = parted.PedDisk.new(dev)
                    self.disks[drive] = disk
                except parted.error, msg:
                    DiskSet.skippedDisks.append(drive)
                    continue

    def partitionTypes(self):
        """Return list of (partition, partition type) tuples for all parts."""
        rc = []
        drives = self.disks.keys()
        drives.sort()

        for drive in drives:
            disk = self.disks[drive]
            part = disk.next_partition ()
            while part:
                if part.type in (parted.PARTITION_PRIMARY,
                                 parted.PARTITION_LOGICAL):
                    device = get_partition_name(part)
                    if part.fs_type:
                        ptype = part.fs_type.name
                    else:
                        ptype = None
                    rc.append((device, ptype))
                part = disk.next_partition (part)

        return rc

    def diskState(self):
        """Print out current disk state.  DEBUG."""
        rc = ""
        for disk in self.disks.values():
            rc = rc + ("%s: %s length %ld, maximum "
                       "primary partitions: %d\n"
                       % (disk.dev.path,
                          disk.dev.model,
                          disk.dev.length,
                          disk.max_primary_partition_count))

            part = disk.next_partition()
            if part:
                rc = rc + ("Device    Type         Filesystem   Start      "
                           "End        Length        Flags\n")
                rc = rc + ("------    ----         ----------   -----      "
                           "---        ------        -----\n")
            while part:
                if not part.type & parted.PARTITION_METADATA:
                    device = ""
                    fs_type_name = ""
                    if part.num > 0:
                        device = get_partition_name(part)
                    if part.fs_type:
                        fs_type_name = part.fs_type.name
                    partFlags = get_flags (part)
                    rc = rc + ("%-9s %-12s %-12s %-10ld %-10ld %-10ld %7s\n"
                        % (device, part.type_name, fs_type_name,
                           part.geom.start, part.geom.end, part.geom.length, partFlags))
                    part = disk.next_partition(part)
        return rc

    def checkNoDisks(self):
        """Check that there are valid disk devices."""
        if len(self.disks.keys()) == 0:
            self.pomona.intf.messageWindow(_("No Drives Found"),
                                           _("An error has occurred - no valid devices were "
                                             "found on which to create new file systems. "
                                             "Please check your hardware for the cause "
                                             "of this problem."))
            return True
        return False

# XXX is this all of the possibilities?
dosPartitionTypes = [ 1, 6, 7, 11, 12, 14, 15 ]

# master list of partition types
allPartitionTypesDict = {
        0 : "Empty",
        1: "DOS 12-bit FAT",
        2: "XENIX root",
        3: "XENIX usr",
        4: "DOS 16-bit <32M",
        5: "Extended",
        6: "DOS 16-bit >=32M",
        7: "NTFS/HPFS",
        8: "AIX",
        9: "AIX bootable",
        10: "OS/2 Boot Manager",
        0xb: "Win95 FAT32",
        0xc: "Win95 FAT32",
        0xe: "Win95 FAT16",
        0xf: "Win95 Ext'd",
        0x10: "OPUS",
        0x11: "Hidden FAT12",
        0x12: "Compaq Setup",
        0x14: "Hidden FAT16 <32M",
        0x16: "Hidden FAT16",
        0x17: "Hidden HPFS/NTFS",
        0x18: "AST SmartSleep",
        0x1b: "Hidden Win95 FAT32",
        0x1c: "Hidden Win95 FAT32 (LBA)",
        0x1e: "Hidden Win95 FAT16 (LBA)",
        0x24: "NEC_DOS",
        0x39: "Plan 9",
        0x40: "Venix 80286",
        0x41: "PPC_PReP Boot",
        0x42: "SFS",
        0x4d: "QNX4.x",
        0x4e: "QNX4.x 2nd part",
        0x4f: "QNX4.x 2nd part",
        0x51: "Novell?",
        0x52: "Microport",
        0x63: "GNU HURD",
        0x64: "Novell Netware 286",
        0x65: "Novell Netware 386",
        0x75: "PC/IX",
        0x80: "Old MINIX",
        0x81: "Linux/MINIX",
        0x82: "Linux swap",
        0x83: "Linux native",
        0x84: "OS/2 hidden C:",
        0x85: "Linux Extended",
        0x86: "NTFS volume set",
        0x87: "NTFS volume set",
        0x8e: "Linux LVM",
        0x93: "Amoeba",
        0x94: "Amoeba BBT",
        0x9f: "BSD/OS",
        0xa0: "IBM Thinkpad hibernation",
        0xa5: "BSD/386",
        0xa6: "OpenBSD",
        0xb7: "BSDI fs",
        0xb8: "BSDI swap",
        0xbf: "Solaris",
        0xc7: "Syrinx",
        0xdb: "CP/M",
        0xde: "Dell Utility",
        0xe1: "DOS access",
        0xe3: "DOS R/O",
        0xeb: "BEOS",
        0xee: "EFI GPT",
        0xef: "EFI (FAT-12/16/32)",
        0xf2: "DOS secondary",
        0xfd: "Linux RAID",
        0xff: "BBT"
}

max_logical_partition_count = {
        "hd": 59,
        "sd": 11,
        "ataraid/": 11,
        "rd/": 3,
        "cciss/": 11,
        "i2o/": 11,
        "iseries/vd": 3,
        "ida/": 11,
        "sx8/": 11,
        "xvd": 11,
}
