#
# bootloader.py: anaconda bootloader shims
#
# Erik Troan <ewt@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2001-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import isys
import partedUtils
import os
import sys
import inutil
import string
import crypt
import random
import shutil
import struct
from copy import copy
from flags import flags
from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

from fsset import *

from pyfire.translate import _, N_
import pyfire.executil

dosFilesystems = ('FAT', 'fat16', 'fat32', 'ntfs', 'hpfs')

def doesDualBoot():
    return 1

def checkForBootBlock(device):
    fd = os.open(device, os.O_RDONLY)
    buf = os.read(fd, 512)
    os.close(fd)
    if len(buf) >= 512 and struct.unpack("H", buf[0x1fe: 0x200]) == (0xaa55,):
        return True
    return False

# takes a line like #boot=/dev/hda and returns /dev/hda
# also handles cases like quoted versions and other nonsense
def getBootDevString(line):
    dev = string.split(line, '=')[1]
    dev = string.strip(dev)
    dev = string.replace(dev, '"', '')
    dev = string.replace(dev, "'", "")
    return dev

# hack and a half
# there's no guarantee that data is written to the disk and grub
# reads both the filesystem and the disk.  suck.
def syncDataToDisk(dev, mntpt, instRoot = "/"):
    import isys, fsset
    isys.sync()
    isys.sync()
    isys.sync()

    # and xfs is even more "special" (#117968)
    if fsset.isValidXFS(dev):
        pyfire.executil.execWithRedirect("/usr/sbin/xfs_freeze",
                                         ["/usr/sbin/xfs_freeze", "-f", mntpt],
                                         stdout = "/dev/tty5",
                                         stderr = "/dev/tty5",
                                         root = instRoot)
        pyfire.executil.execWithRedirect("/usr/sbin/xfs_freeze",
                                         ["/usr/sbin/xfs_freeze", "-u", mntpt],
                                         stdout = "/dev/tty5",
                                         stderr = "/dev/tty5",
                                         root = instRoot)

class BootyNoKernelWarning:
    def __init__ (self, value=""):
        self.value = value

    def __str__ (self):
        return self.value

class KernelArguments:

    def get(self):
        return self.args

    def set(self, args):
        self.args = args

    def chandevget(self):
        return self.cargs

    def chandevset(self, args):
        self.cargs = args

    def append(self, args):
        if self.args:
            # don't duplicate the addition of an argument (#128492)
            if self.args.find(args) != -1:
                return
            self.args = self.args + " "
        self.args = self.args + "%s" % (args,)


    def __init__(self):
        newArgs = []
        # look for kernel arguments we know should be preserved and add them
        ourargs = ["speakup_synth=", "apic", "noapic", "apm=", "ide=nodma",
                   "noht", "acpi=", "video=", "pci="]
        f = open("/proc/cmdline")
        cmdline = f.read()[:-1]
        f.close()
        cmdlineargs = cmdline.split(" ")
        for arg in cmdlineargs:
            for check in ourargs:
                if arg.startswith(check):
                    newArgs.append(arg)

        self.args = " ".join(newArgs)

class BootImages:
    """A collection to keep track of boot images available on the system.
    Examples would be:
    ('linux', 'Red Hat Linux', 'ext2'),
    ('Other', 'Other', 'fat32'), ...
    """
    def __init__(self):
        self.default = None
        self.images = {}

    def getImages(self):
        """returns dictionary of (label, longlabel, devtype) pairs
        indexed by device"""
        # return a copy so users can modify it w/o affecting us
        return copy(self.images)

    def setImageLabel(self, dev, label, setLong = 0):
        orig = self.images[dev]
        if setLong:
            self.images[dev] = (orig[0], label, orig[2])
        else:
            self.images[dev] = (label, orig[1], orig[2])

    def setDefault(self, default):
        # default is a device
        self.default = default

    def getDefault(self):
        return self.default

    # XXX this has internal anaconda-ish knowledge.  ick
    def setup(self, diskSet, fsset):
        devices = {}
        devs = self.availableBootDevices(diskSet, fsset)
        for (dev, type) in devs:
            devices[dev] = 1

        # These partitions have disappeared
        for dev in self.images.keys():
            if not devices.has_key(dev):
                del self.images[dev]

        # These have appeared
        for (dev, type) in devs:
            if not self.images.has_key(dev):
                if type in dosFilesystems and doesDualBoot():
                    self.images[dev] = ("Other", "Other", type)
                else:
                    self.images[dev] = (None, None, type)

        if not self.images.has_key(self.default):
            entry = fsset.getEntryByMountPoint('/')
            self.default = entry.device.getDevice()
            (label, longlabel, type) = self.images[self.default]
            if not label:
                self.images[self.default] = ("linux", getProductName(), type)

    # XXX more internal anaconda knowledge
    def availableBootDevices(self, diskSet, fsset):
        devs = []
        foundDos = 0
        for (dev, type) in diskSet.partitionTypes():
            if type in dosFilesystems and not foundDos and doesDualBoot():
                import isys
                import partedUtils

                part = partedUtils.get_partition_by_name(diskSet.disks, dev)
                if part.native_type not in partedUtils.dosPartitionTypes:
                    continue

                try:
                    bootable = checkForBootBlock(dev)
                    devs.append((dev, type))
                    foundDos = 1
                except Exception, e:
                    #log("exception checking %s: %s" %(dev, e))
                    pass
            elif ((type == 'ntfs' or type =='hpfs') and not foundDos and doesDualBoot()):
                devs.append((dev, type))
                # maybe questionable, but the first ntfs or fat is likely to
                # be the correct one to boot with XP using ntfs
                foundDos = 1

        slash = fsset.getEntryByMountPoint('/')
        if not slash or not slash.device or not slash.fsystem:
            raise ValueError,("Trying to pick boot devices but do not have a "
                              "sane root partition. Aborting install.")
        devs.append((slash.device.getDevice(), slash.fsystem.getName()))

        devs.sort()
        return devs

class bootloaderInfo:
    def useGrub(self):
        return self.useGrubVal

    def setForceLBA(self, val):
        pass

    def setPassword(self, val, isCrypted = 1):
        pass

    def getPassword(self):
        pass

    def getDevice(self):
        return self.device

    def setDevice(self, device):
        self.device = device

        (dev, part) = getDiskPart(device)
        if part is None:
            self.defaultDevice = "mbr"
        else:
            self.defaultDevice = "partition"

    def createDriveList(self):
        # create a drive list that we can use for drive mappings
        # XXX has pomona internals knowledge
        import isys
        drives = isys.hardDriveDict().keys()
        drives.sort(isys.compareDrives)

        # now filter out all of the drives without media present
        drives = filter(lambda x: isys.mediaPresent(x), drives)

        return drives

    def updateDriveList(self, sortedList=[]):
        self._drivelist = self.createDriveList()

        # If we're given a sort order, make sure the drives listed in it
        # are put at the head of the drivelist in that order.  All other
        # drives follow behind in whatever order they're found.
        if sortedList != []:
            revSortedList = sortedList
            revSortedList.reverse()

            for i in revSortedList:
                try:
                    ele = self._drivelist.pop(self._drivelist.index(i))
                    self._drivelist.insert(0, ele)
                except:
                    pass

    def _getDriveList(self):
        if self._drivelist is not None:
            return self._drivelist
        self.updateDriveList()
        return self._drivelist

    def _setDriveList(self, val):
        self._drivelist = val
    drivelist = property(_getDriveList, _setDriveList)

    def __init__(self):
        self.args = KernelArguments()
        self.images = BootImages()
        self.device = None
        self.defaultDevice = None  # XXX hack, used by kickstart
        self.useGrubVal = 0      # only used on x86
        self.configfile = None
        self.kernelLocation = "/boot/"
        self.forceLBA32 = 0
        self.password = None
        self.pure = None
        self.above1024 = 0
        self._drivelist = None

class x86BootloaderInfo(bootloaderInfo):
    def setPassword(self, val, isCrypted = 1):
        if not val:
            self.password = val
            self.pure = val
            return

        if isCrypted and self.useGrubVal == 0:
            #log("requested crypted password with lilo; ignoring")
            self.pure = None
            return
        elif isCrypted:
            self.password = val
            self.pure = None
        else:
            salt = "$1$"
            saltLen = 8

        saltchars = string.letters + string.digits + './'
        for i in range(saltLen):
            salt += random.choice(saltchars)

        self.password = crypt.crypt(val, salt)
        self.pure = val

    def getPassword (self):
        return self.pure

    def setForceLBA(self, val):
        self.forceLBA32 = val

    def getPhysicalDevices(self, device):
        # This finds a list of devices on which the given device name resides.
        # Accepted values for "device" are physical disks ("hda"),
        # and real partitions on physical disks ("hda1").
        #
        return [device]

    def writeGrub(self, instRoot, fsset, bl, langs, kernelList, chainList,
                                                            defaultDev):

        images = bl.images.getImages()
        rootDev = fsset.getEntryByMountPoint("/").device.getDevice()

        if not os.path.isdir(instRoot + '/boot/grub/'):
            os.mkdir(instRoot + '/boot/grub', 0755)

        cf = '/boot/grub/grub.conf'
        self.perms = 0600
        if os.access (instRoot + cf, os.R_OK):
            self.perms = os.stat(instRoot + cf)[0] & 0777
            os.rename(instRoot + cf, instRoot + cf + '.backup')

        grubTarget = bl.getDevice()
        target = "mbr"
        if (grubTarget.startswith('rd/') or grubTarget.startswith('ida/') or
                        grubTarget.startswith('cciss/') or
                        grubTarget.startswith('sx8/') or
                        grubTarget.startswith('mapper/')):
            if grubTarget[-1].isdigit():
                if grubTarget[-2] == 'p' or \
                                (grubTarget[-2].isdigit() and grubTarget[-3] == 'p'):
                    type = "partition"
        elif grubTarget[-1].isdigit() and not grubTarget.startswith('md'):
            target = "partition"

        f = open(instRoot + cf, "w+")

        f.write("# grub.conf generated by pomona\n")
        f.write("#\n")

        bootDev = fsset.getEntryByMountPoint("/boot")
        grubPath = "/grub"
        cfPath = "/"
        if not bootDev:
            bootDev = fsset.getEntryByMountPoint("/")
            grubPath = "/boot/grub"
            cfPath = "/boot/"
            f.write("# NOTICE:  You do not have a /boot partition.  "
                    "This means that\n")
            f.write("#          all kernel and initrd paths are relative "
                    "to /, eg.\n")
        else:
            f.write("# NOTICE:  You have a /boot partition.  This means "
                    "that\n")
            f.write("#          all kernel and initrd paths are relative "
                    "to /boot/, eg.\n")

        bootDevs = self.getPhysicalDevices(bootDev.device.getDevice())
        bootDev = bootDev.device.getDevice()

        f.write('#          root %s\n' % self.grubbyPartitionName(bootDevs[0]))
        f.write("#          kernel %svmlinuz-version ro "
                "root=/dev/%s\n" % (cfPath, rootDev))
        f.write("#          initrd %sinitrd-version.img\n" % (cfPath))
        f.write("#boot=/dev/%s\n" % (grubTarget))

        # keep track of which devices are used for the device.map
        usedDevs = {}

        # get the default image to boot... first kernel image here
        default = 0

        f.write('default=%s\n' % (default))

        # get the default timeout
        timeout = 5
        f.write('timeout=%d\n' %(timeout,))

        # we only want splashimage if they're not using a serial console
        if os.access("%s/boot/grub/splash.xpm.gz" %(instRoot,), os.R_OK):
            f.write('splashimage=%s%sgrub/splash.xpm.gz\n'
                                    % (self.grubbyPartitionName(bootDevs[0]), cfPath))
            f.write("hiddenmenu\n")

        for dev in self.getPhysicalDevices(grubTarget):
            usedDevs[dev] = 1

        if self.password:
            f.write('password --md5 %s\n' % (self.password))

        for (kernelName, kernelVersion, kernelTag, kernelDesc) in kernelList:
            kernelFile = "%s%skernel%s" % (cfPath, sname, kernelTag,)

            initrd = "/boot/initrd-%s%s.img" % (kernelVersion, kernelTag,)

            # make initramfs
            pyfire.executil.execWithRedirect("/sbin/mkinitramfs",
                                         ["/sbin/mkinitramfs", "-v", "-f", "%s" % initrd,
                                          "%s%s" % (kernelVersion, kernelTag,), ],
                                         stdout = "/dev/tty5", stderr = "/dev/tty5",
                                         root = instRoot)

            f.write('title %s (%s - %s)\n' % (name, kernelDesc, kernelVersion))
            f.write('\troot %s\n' % self.grubbyPartitionName(bootDevs[0]))

            realroot = getRootDevName(initrd, fsset, rootDev, instRoot)
            realroot = " root=%s" %(realroot,)

            f.write('\tkernel %s ro%s' % (kernelFile, realroot))
            if self.args.get():
                f.write(' %s' % self.args.get())
            f.write('\n')

            if os.access (instRoot + initrd, os.R_OK):
                f.write('\tinitrd %sinitrd-%s%s.img\n' % (cfPath, kernelVersion, kernelTag,))

        for (label, longlabel, device) in chainList:
            if ((not longlabel) or (longlabel == "")):
                continue
            f.write('title %s\n' % (longlabel))
            f.write('\trootnoverify %s\n' % self.grubbyPartitionName(device))
#           f.write('\tmakeactive\n')
            f.write('\tchainloader +1')
            f.write('\n')
            usedDevs[device] = 1

        f.close()
        os.chmod(instRoot + "/boot/grub/grub.conf", self.perms)

        try:
            # make symlink for /etc/grub.conf (config files belong in /etc)
            if os.access (instRoot + "/etc/grub.conf", os.R_OK):
                os.rename(instRoot + "/etc/grub.conf", instRoot + "/etc/grub.conf.backup")
                os.symlink("../boot/grub/grub.conf", instRoot + "/etc/grub.conf")
        except:
            pass

        for dev in self.getPhysicalDevices(rootDev) + bootDevs:
            usedDevs[dev] = 1

        if os.access(instRoot + "/boot/grub/device.map", os.R_OK):
            os.rename(instRoot + "/boot/grub/device.map", instRoot + "/boot/grub/device.map.backup")

        f = open(instRoot + "/boot/grub/device.map", "w+")
        f.write("# this device map was generated by pomona\n")
        devs = usedDevs.keys()
        usedDevs = {}
        for dev in devs:
            drive = getDiskPart(dev)[0]
            if usedDevs.has_key(drive):
                continue
            usedDevs[drive] = 1
        devs = usedDevs.keys()
        devs.sort()
        for drive in devs:
            # XXX hack city.  If they're not the sort of thing that'll
            # be in the device map, they shouldn't still be in the list.
            if not drive.startswith('md'):
                f.write("(%s)     /dev/%s\n" % (self.grubbyDiskName(drive), drive))
        f.close()

        args = "--stage2=/boot/grub/stage2 "
        if self.forceLBA32:
            args = "%s--force-lba " % (args,)

        sysconf = '/etc/sysconfig/grub'
        if os.access (instRoot + sysconf, os.R_OK):
            self.perms = os.stat(instRoot + sysconf)[0] & 0777
            os.rename(instRoot + sysconf, instRoot + sysconf + '.backup')
        # if it's an absolute symlink, just get it out of our way
        elif (os.path.islink(instRoot + sysconf) and
                                os.readlink(instRoot + sysconf)[0] == '/'):
            os.rename(instRoot + sysconf, instRoot + sysconf + '.backup')
        f = open(instRoot + sysconf, 'w+')
        f.write("boot=/dev/%s\n" %(grubTarget,))
        # XXX forcelba never gets read back...
        if self.forceLBA32:
            f.write("forcelba=1\n")
        else:
            f.write("forcelba=0\n")
        f.close()

        cmds = []
        for bootDev in bootDevs:
            gtPart = self.getMatchingPart(bootDev, grubTarget)
            gtDisk = self.grubbyPartitionName(getDiskPart(gtPart)[0])
            bPart = self.grubbyPartitionName(bootDev)
            cmd = "root %s\n" % (bPart,)

            stage1Target = gtDisk
            if target == "partition":
                stage1Target = self.grubbyPartitionName(gtPart)

            cmd += "install %s%s/stage1 d %s %s/stage2 p %s%s/grub.conf" % \
                   (args, grubPath, stage1Target, grubPath, bPart, grubPath)
            cmds.append(cmd)

        log.info("GRUB commands:")
        for cmd in cmds:
            log.info("\t%s\n", cmd)

        if cfPath == "/":
            syncDataToDisk(bootDev, "/boot", instRoot)
        else:
            syncDataToDisk(bootDev, "/", instRoot)

        # copy the stage files over into /boot
        pyfire.executil.execWithRedirect("/usr/sbin/grub-install",
                                         ["/usr/sbin/grub-install", "--just-copy"],
                                         stdout = "/dev/tty5", stderr = "/dev/tty5",
                                         root = instRoot)

        # really install the bootloader
        for cmd in cmds:
            p = os.pipe()
            os.write(p[1], cmd + '\n')
            os.close(p[1])
            import time

            # FIXME: hack to try to make sure everything is written
            #        to the disk
            if cfPath == "/":
                syncDataToDisk(bootDev, "/boot", instRoot)
            else:
                syncDataToDisk(bootDev, "/", instRoot)

            pyfire.executil.execWithRedirect("/usr/sbin/grub" ,
                                             [ "grub",  "--batch", "--no-floppy",
                                             "--device-map=/boot/grub/device.map" ],
                                             stdin = p[0],
                                             stdout = "/dev/tty5", stderr = "/dev/tty5",
                                             root = instRoot)
            os.close(p[0])

        return ""

    def getMatchingPart(self, bootDev, target):
        bootName, bootPartNum = getDiskPart(bootDev)
        devices = self.getPhysicalDevices(target)
        for device in devices:
            name, partNum = getDiskPart(device)
            if name == bootName:
                return device
        return devices[0]

    def grubbyDiskName(self, name):
        return "hd%d" % self.drivelist.index(name)

    def grubbyPartitionName(self, dev):
        (name, partNum) = getDiskPart(dev)
        if partNum != None:
            return "(%s,%d)" % (self.grubbyDiskName(name), partNum)
        else:
            return "(%s)" %(self.grubbyDiskName(name))

    def write(self, instRoot, fsset, bl, langs, kernelList, chainList, defaultDev, intf):
        out = self.writeGrub(instRoot, fsset, bl, langs, kernelList, chainList, defaultDev)

    def getArgList(self):
        args = bootloaderInfo.getArgList(self)

        if self.forceLBA32:
            args.append("--lba32")
        if self.password:
            args.append("--md5pass=%s" %(self.password))

        # XXX add location of bootloader here too

        return args

    def __init__(self):
        bootloaderInfo.__init__(self)
        self.useGrubVal = 1
        self.kernelLocation = "/boot/"
        self.configfile = "/etc/lilo.conf"
        self.password = None
        self.pure = None

###############
# end of boot loader objects... these are just some utility functions used

# return (disk, partition number) eg ('hda', 1)
def getDiskPart(dev):
    cut = len(dev)
    if (dev.startswith('rd/') or dev.startswith('ida/') or
            dev.startswith('cciss/') or dev.startswith('sx8/') or
            dev.startswith('mapper/')):
        if dev[-2] == 'p':
            cut = -1
        elif dev[-3] == 'p':
            cut = -2
    else:
        if dev[-2] in string.digits:
            cut = -2
        elif dev[-1] in string.digits:
            cut = -1

    name = dev[:cut]

    # hack off the trailing 'p' from /dev/cciss/*, for example
    if name[-1] == 'p':
        for letter in name:
            if letter not in string.letters and letter != "/":
                name = name[:-1]
                break

    if cut < 0:
        partNum = int(dev[cut:]) - 1
    else:
        partNum = None

    return (name, partNum)

# hackery to determine if we should do root=LABEL=/ or whatnot
# as usual, knows too much about pomona
def getRootDevName(initrd, fsset, rootDev, instRoot):
    if not os.access(instRoot + initrd, os.R_OK):
        return "/dev/%s" % (rootDev,)
    try:
        rootEntry = fsset.getEntryByMountPoint("/")
        if rootEntry.getUuid() is not None:
            return "UUID=%s" %(rootEntry.getUuid(),)
        elif rootEntry.getLabel() is not None and rootEntry.device.doLabel is not None:
            return "LABEL=%s" %(rootEntry.getLabel(),)
        return "/dev/%s" %(rootDev,)
    except:
        return "/dev/%s" %(rootDev,)

# returns a product name to use for the boot loader string
def getProductName():
    # XXX Check /etc/ipfire-release here...
    return "IPFire Linux"

def bootloaderSetupChoices(pomona):
    if pomona.dir == DISPATCH_BACK:
        return
    pomona.id.bootloader.updateDriveList()

    choices = pomona.id.fsset.bootloaderChoices(pomona.id.diskset, pomona.id.bootloader)

    pomona.id.bootloader.images.setup(pomona.id.diskset, pomona.id.fsset)

    if pomona.id.bootloader.defaultDevice != None and choices:
        keys = choices.keys()
        # there are only two possible things that can be in the keys
        # mbr and boot.  boot is ALWAYS present.  so if the dev isn't
        # listed, it was mbr and we should nicely fall back to boot
        if pomona.id.bootloader.defaultDevice not in keys:
            log.warning("MBR not suitable as boot device; installing to partition")
            pomona.id.bootloader.defaultDevice = "boot"
        pomona.id.bootloader.setDevice(choices[pomona.id.bootloader.defaultDevice][0])
    elif choices and choices.has_key("mbr"):
        pomona.id.bootloader.setDevice(choices["mbr"][0])
    elif choices and choices.has_key("boot"):
        pomona.id.bootloader.setDevice(choices["boot"][0])

    bootDev = pomona.id.fsset.getEntryByMountPoint("/")
    if not bootDev:
        bootDev = pomona.id.fsset.getEntryByMountPoint("/boot")
    part = partedUtils.get_partition_by_name(pomona.id.diskset.disks,
                                             bootDev.device.getDevice())
    if part and partedUtils.end_sector_to_cyl(part.geom.dev, part.geom.end) >= 1024:
        pomona.id.bootloader.above1024 = 1

def writeBootloader(pomona):
    def dosync():
        isys.sync()
        isys.sync()
        isys.sync()

    if pomona.id.bootloader.defaultDevice == -1:
        log.error("No default boot device set")
        return

    w = pomona.intf.waitWindow(_("Bootloader"), _("Installing bootloader..."))

    kernelList = []
    otherList = []
    root = pomona.id.fsset.getEntryByMountPoint('/')
    if root:
        rootDev = root.device.getDevice()
    else:
        rootDev = None
    defaultDev = pomona.id.bootloader.images.getDefault()

    kernelLabel = None
    kernelLongLabel = None

    for (dev, (label, longlabel, type)) in pomona.id.bootloader.images.getImages().items():
        if (dev == rootDev) or (rootDev is None and kernelLabel is None):
            kernelLabel = label
            kernelLongLabel = longlabel
        elif dev == defaultDev:
            otherList = [(label, longlabel, dev)] + otherList
        else:
            otherList.append((label, longlabel, dev))

    if kernelLabel is None:
        log.error("unable to find default image, bailing")

    defkern = None
    for (kernelName, kernelVersion, kernelTag, kernelDesc) in pomona.backend.kernelVersionList(pomona):
        if not defkern:
            defkern = "%s%s" % (kernelName, kernelTag)

        if kernelTag is "-smp" and isys.smpAvailable():
            defkern = "%s%s" % (kernelName, kernelTag)

        kernelList.append((kernelName, kernelVersion, kernelTag, kernelDesc))

    f = open(pomona.rootPath + "/etc/sysconfig/kernel", "w+")
    f.write("# DEFAULTKERNEL specifies the default kernel package type\n")
    f.write("DEFAULTKERNEL=%s\n" %(defkern,))
    f.close()

    dosync()
    try:
        pomona.id.bootloader.write(pomona.rootPath, pomona.id.fsset, pomona.id.bootloader,
                                   pomona.id.instLanguage, kernelList, otherList, defaultDev,
                                   pomona.intf)
        w.pop()
    except BootyNoKernelWarning:
        w.pop()
        if pomona.intf:
            pomona.intf.messageWindow(_("Warning"),
                                      _("No kernel packages were installed on your "
                                        "system.  Your boot loader configuration "
                                        "will not be changed."))
    dosync()

# return instance of the appropriate bootloader for our arch
def getBootloader():
    return x86BootloaderInfo()

def hasWindows(bl):
    foundWindows = False
    for (k,v) in bl.images.getImages().iteritems():
        if v[0].lower() == 'other' and v[2] in x86BootloaderInfo.dosFilesystems:
            foundWindows = True
            break

    return foundWindows
