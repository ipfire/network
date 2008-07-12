#
# fsset.py: filesystem management
#
# Matt Wilson <msw@redhat.com>
#
# Copyright 2001-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import string
import isys
import inutil
import os
import resource
import posix
import stat
import errno
import parted
import sys
import struct
import partitioning
import partedUtils
import types
from flags import flags

from pyfire.translate import _, N_

import logging
log = logging.getLogger("pomona")

class BadBlocksError(Exception):
    pass

class SuspendError(Exception):
    pass

class OldSwapError(Exception):
    pass

### XXX we have to check this and find useful mpoints
defaultMountPoints = ['/', '/boot', '/home', '/tmp', '/usr', '/var', '/opt']

fileSystemTypes = {}

def fileSystemTypeGetDefault():
    if fileSystemTypeGet('ext3').isSupported():
        return fileSystemTypeGet('ext3')
    elif fileSystemTypeGet('ext2').isSupported():
        return fileSystemTypeGet('ext2')
    else:
        raise ValueError, "You have neither ext3 or ext2 support in your kernel!"

def fileSystemTypeGet(key):
    return fileSystemTypes[key]

def fileSystemTypeRegister(klass):
    fileSystemTypes[klass.getName()] = klass

def fileSystemTypeGetTypes():
    return fileSystemTypes.copy()

def getUsableLinuxFs():
    rc = []
    for fsType in fileSystemTypes.keys():
        if fileSystemTypes[fsType].isMountable() and \
                        fileSystemTypes[fsType].isLinuxNativeFS():
            rc.append(fsType)

    # make sure the default is first in the list, kind of ugly
    default = fileSystemTypeGetDefault()
    defaultName = default.getName()
    if defaultName in rc:
        del rc[rc.index(defaultName)]
        rc.insert(0, defaultName)
    return rc

def devify(device):
    if device in ["proc", "devpts", "sysfs", "tmpfs"]:
        return device
    elif device == "sys":
        return "sysfs"
    elif device == "shm":
        return "tmpfs"
    elif device != "none" and device[0] != '/':
        return "/dev/" + device
    else:
        return device

class LabelFactory:
    def __init__(self):
        self.labels = None

    def createLabel(self, mountpoint, maxLabelChars):
        if self.labels == None:
            self.labels = {}
            diskset = partedUtils.DiskSet()
            diskset.openDevices()
            labels = diskset.getLabels()
            del diskset
            self.reserveLabels(labels)

        if len(mountpoint) > maxLabelChars:
            mountpoint = mountpoint[0:maxLabelChars]
        count = 0
        while self.labels.has_key(mountpoint):
            count = count + 1
            s = "%s" % count
            if (len(mountpoint) + len(s)) <= maxLabelChars:
                mountpoint = mountpoint + s
            else:
                strip = len(mountpoint) + len(s) - maxLabelChars
                mountpoint = mountpoint[0:len(mountpoint) - strip] + s
        self.labels[mountpoint] = 1

        return mountpoint

    def reserveLabels(self, labels):
        if self.labels == None:
            self.labels = {}
        for device, label in labels.items():
            self.labels[label] = 1

    def isLabelReserved(self, label):
        if self.labels == None:
            return False
        elif self.labels.has_key(label):
            return True
        else:
            return False

labelFactory = LabelFactory()

class FileSystemType:
    kernelFilesystems = {}
    def __init__(self):
        self.deviceArguments = {}
        self.formattable = 0
        self.checked = 0
        self.name = ""
        self.linuxnativefs = 0
        self.partedFileSystemType = None
        self.partedPartitionFlags = []
        self.maxSizeMB = 8 * 1024 * 1024
        self.supported = -1
        self.defaultOptions = "defaults"
        self.migratetofs = None
        self.extraFormatArgs = []
        self.maxLabelChars = 16
        self.packages = []

    def isKernelFS(self):
        """Returns True if this is an in-kernel pseudo-filesystem."""
        return False

    def mount(self, device, mountpoint, readOnly=0, bindMount=0,
              instroot=""):
        if not self.isMountable():
            return
        inutil.mkdirChain("%s/%s" %(instroot, mountpoint))
        isys.mount(device, "%s/%s" %(instroot, mountpoint),
                fstype = self.getName(),
                readOnly = readOnly, bindMount = bindMount)

    def umount(self, device, path):
        isys.umount(path, removeDir = 0)

    def getName(self, quoted = 0):
        """Return the name of the filesystem.  Set quoted to 1 if this
        should be quoted (ie, it's not for display)."""
        if quoted:
            if self.name.find(" ") != -1:
                return "\"%s\"" %(self.name,)
        return self.name

    def getNeededPackages(self):
        return self.packages

    def registerDeviceArgumentFunction(self, klass, function):
        self.deviceArguments[klass] = function

    def badblocksDevice(self, entry, windowCreator, chroot='/'):
        if windowCreator:
            w = windowCreator(_("Checking for Bad Blocks"),
                                                                                    _("Checking for bad blocks on /dev/%s...")
                                                                            % (entry.device.getDevice(),), 100)
        else:
            w = None

        devicePath = entry.device.setupDevice(chroot)
        args = [ "badblocks", "-vv", devicePath ]

        # entirely too much cutting and pasting from ext2FormatFileSystem
        fd = os.open("/dev/tty5", os.O_RDWR | os.O_CREAT | os.O_APPEND)
        p = os.pipe()
        childpid = os.fork()
        if not childpid:
            os.close(p[0])
            os.dup2(p[1], 1)
            os.dup2(p[1], 2)
            os.close(p[1])
            os.close(fd)
            os.execvp(args[0], args)
            log.critical("failed to exec %s", args)
            os._exit(1)

        os.close(p[1])

        s = 'a'
        while s and s != ':':
            try:
                s = os.read(p[0], 1)
            except OSError, args:
                (num, str) = args
                if (num != 4):
                    raise IOError, args
            os.write(fd, s)

        num = ''
        numbad = 0
        while s:
            try:
                s = os.read(p[0], 1)
                os.write(fd, s)

                if s not in ['\b', '\n']:
                    try:
                        num = num + s
                    except:
                        pass
                else:
                    if s == '\b':
                        if num:
                            l = string.split(num, '/')
                            val = (long(l[0]) * 100) / long(l[1])
                            w and w.set(val)
                    else:
                        try:
                            blocknum = long(num)
                            numbad = numbad + 1
                        except:
                            pass

                if numbad > 0:
                    raise BadBlocksError

                num = ''
            except OSError, args:
                (num, str) = args
                if (num != 4):
                    raise IOError, args

        try:
            (pid, status) = os.waitpid(childpid, 0)
        except OSError, (num, msg):
            log.critical("exception from waitpid in badblocks: %s %s" % (num, msg))
            status = None
        os.close(fd)

        w and w.pop()

        if numbad > 0:
            raise BadBlocksError

        # have no clue how this would happen, but hope we're okay
        if status is None:
            return

        if os.WIFEXITED(status) and (os.WEXITSTATUS(status) == 0):
            return

        raise SystemError

    def formatDevice(self, entry, progress, chroot='/'):
        if self.isFormattable():
            raise RuntimeError, "formatDevice method not defined"

    def migrateFileSystem(self, device, message, chroot='/'):
        if self.isMigratable():
            raise RuntimeError, "migrateFileSystem method not defined"

    def labelDevice(self, entry, chroot):
        pass

    def clobberDevice(self, entry, chroot):
        pass

    def isFormattable(self):
        return self.formattable

    def isLinuxNativeFS(self):
        return self.linuxnativefs

    def readProcFilesystems(self):
        f = open("/proc/filesystems", 'r')
        if not f:
            pass
        lines = f.readlines()
        for line in lines:
            fields = string.split(line)
            if fields[0] == "nodev":
                fsystem = fields[1]
            else:
                fsystem = fields[0]
            FileSystemType.kernelFilesystems[fsystem] = None

    def isMountable(self):
        if not FileSystemType.kernelFilesystems:
            self.readProcFilesystems()

        return FileSystemType.kernelFilesystems.has_key(self.getName()) or self.getName() == "auto"

    def isSupported(self):
        if self.supported == -1:
            return self.isMountable()
        return self.supported

    def isChecked(self):
        return self.checked

    def getDeviceArgs(self, device):
        deviceArgsFunction = self.deviceArguments.get(device.__class__)
        if not deviceArgsFunction:
            return []
        return deviceArgsFunction(device)

    def getPartedFileSystemType(self):
        return self.partedFileSystemType

    def getPartedPartitionFlags(self):
        return self.partedPartitionFlags

    # note that this returns the maximum size of a filesystem in megabytes
    def getMaxSizeMB(self):
        return self.maxSizeMB

    def getDefaultOptions(self, mountpoint):
        return self.defaultOptions

    def getMigratableFSTargets(self):
        retval = []
        if not self.migratetofs:
            return retval

        for fs in self.migratetofs:
            if fileSystemTypeGet(fs).isSupported():
                retval.append(fs)

        return retval

    def isMigratable(self):
        if len(self.getMigratableFSTargets()) > 0:
            return 1
        else:
            return 0


class reiserfsFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = parted.file_system_type_get("reiserfs")
        self.formattable = 1
        self.checked = 1
        self.linuxnativefs = 1
        self.supported = -1
        self.name = "reiserfs"
        self.packages = [ "reiserfs-utils" ] ### XXX do we need this?

        self.maxSizeMB = 8 * 1024 * 1024

    def formatDevice(self, entry, progress, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)
        p = os.pipe()
        os.write(p[1], "y\n")
        os.close(p[1])

        rc = inutil.execWithRedirect("mkreiserfs",
                                                                                                                        [devicePath],
                                                                                                                        stdin = p[0],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)

        if rc:
            raise SystemError

    def labelDevice(self, entry, chroot):
        devicePath = entry.device.setupDevice(chroot)
        label = labelFactory.createLabel(entry.mountpoint, self.maxLabelChars)
        rc = inutil.execWithRedirect("reiserfstune",
                                                                                                                        ["--label", label, devicePath],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)
        if rc:
            raise SystemError
        entry.setLabel(label)

fileSystemTypeRegister(reiserfsFileSystem())

class xfsFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = parted.file_system_type_get("xfs")
        self.formattable = 1
        self.checked = 1
        self.linuxnativefs = 1
        self.name = "xfs"
        self.maxSizeMB = 16 * 1024 * 1024
        self.maxLabelChars = 12
        self.supported = -1
        self.packages = [ "xfsprogs" ] ### XXX do we need this?

    def formatDevice(self, entry, progress, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)

        rc = inutil.execWithRedirect("mkfs.xfs",
                                                                                                                        ["-f", "-l", "internal",
                                                                                                                         "-i", "attr=2", devicePath],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)

        if rc:
            raise SystemError

    def labelDevice(self, entry, chroot):
        devicePath = entry.device.setupDevice(chroot)
        label = labelFactory.createLabel(entry.mountpoint, self.maxLabelChars)
        db_cmd = "label " + label
        rc = inutil.execWithRedirect("xfs_db",
                                                                                                                        ["-x", "-c", db_cmd, devicePath],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)
        if rc:
            raise SystemError
        entry.setLabel(label)

fileSystemTypeRegister(xfsFileSystem())

class extFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = None
        self.formattable = 1
        self.checked = 1
        self.linuxnativefs = 1
        self.maxSizeMB = 8 * 1024 * 1024
        self.packages = [ "e2fsprogs" ] ### XXX do we need this?

    def labelDevice(self, entry, chroot):
        devicePath = entry.device.setupDevice(chroot)
        label = labelFactory.createLabel(entry.mountpoint, self.maxLabelChars)

        rc = inutil.execWithRedirect("e2label",
                                                                                                                        [devicePath, label],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)
        if rc:
            raise SystemError
        entry.setLabel(label)

    def formatDevice(self, entry, progress, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)
        devArgs = self.getDeviceArgs(entry.device)
        args = [ "mke2fs", devicePath, "-i", str(entry.bytesPerInode) ]

        args.extend(devArgs)
        args.extend(self.extraFormatArgs)

        log.info("Format command:  %s\n" % str(args))

        rc = ext2FormatFilesystem(args, "/dev/tty5",
                                                                                                                progress,
                                                                                                                entry.mountpoint)
        if rc:
            raise SystemError

    def clobberDevice(self, entry, chroot):
        device = entry.device.setupDevice(chroot)
        isys.ext2Clobber(device)

    # this is only for ext3 filesystems, but migration is a method
    # of the ext2 fstype, so it needs to be here.  XXX should be moved
    def setExt3Options(self, entry, message, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)

        # if no journal, don't turn off the fsck
        if not isys.ext2HasJournal(devicePath):
            return

        rc = inutil.execWithRedirect("tune2fs",
                                                                                                                        ["-c0", "-i0", "-Odir_index",
                                                                                                                         "-ouser_xattr,acl", devicePath],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)

class ext2FileSystem(extFileSystem):
    def __init__(self):
        extFileSystem.__init__(self)
        self.name = "ext2"
        self.partedFileSystemType = parted.file_system_type_get("ext2")
        self.migratetofs = ['ext3']

    def migrateFileSystem(self, entry, message, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)

        if not entry.fsystem or not entry.origfsystem:
            raise RuntimeError, ("Trying to migrate fs w/o fsystem or "
                                                                                             "origfsystem set")
        if entry.fsystem.getName() != "ext3":
            raise RuntimeError, ("Trying to migrate ext2 to something other "
                                                                                             "than ext3")

        # if journal already exists skip
        if isys.ext2HasJournal(devicePath):
            log.info("Skipping migration of %s, has a journal already.\n" % devicePath)
            return

        rc = inutil.execWithRedirect("tune2fs",
                                                                                                                        ["-j", devicePath ],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)

        if rc:
            raise SystemError

        # XXX this should never happen, but appears to have done
        # so several times based on reports in bugzilla.
        # At least we can avoid leaving them with a system which won't boot
        if not isys.ext2HasJournal(devicePath):
            log.warning("Migration of %s attempted but no journal exists after "
                                                            "running tune2fs.\n" % (devicePath))
            if message:
                rc = message(_("Error"),
                                                                 _("An error occurred migrating %s to ext3.  It is "
                                                                         "possible to continue without migrating this "
                                                                         "file system if desired.\n\n"
                                                                         "Would you like to continue without migrating %s?")
                                                                % (devicePath, devicePath), type = "yesno")
                if rc == 0:
                    sys.exit(0)
                    entry.fsystem = entry.origfsystem ### XXX what is this?
                else:
                    extFileSystem.setExt3Options(self, entry, message, chroot)

fileSystemTypeRegister(ext2FileSystem())

class ext3FileSystem(extFileSystem):
    def __init__(self):
        extFileSystem.__init__(self)
        self.name = "ext3"
        self.extraFormatArgs = [ "-j" ]
        self.partedFileSystemType = parted.file_system_type_get("ext3")

    def formatDevice(self, entry, progress, chroot='/'):
        extFileSystem.formatDevice(self, entry, progress, chroot)
        extFileSystem.setExt3Options(self, entry, progress, chroot)

fileSystemTypeRegister(ext3FileSystem())

class swapFileSystem(FileSystemType):
    enabledSwaps = {}

    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = parted.file_system_type_get("linux-swap")
        self.formattable = 1
        self.name = "swap"
        self.maxSizeMB = 8 * 1024 * 1024
        self.linuxnativefs = 1
        self.supported = 1
        self.maxLabelChars = 15

    def mount(self, device, mountpoint, readOnly=0, bindMount=0, instroot = None):
        pagesize = resource.getpagesize()
        buf = None
        if pagesize > 2048:
            num = pagesize
        else:
            num = 2048
        try:
            fd = os.open(device, os.O_RDONLY)
            buf = os.read(fd, num)
        except:
            pass
        finally:
            try:
                os.close(fd)
            except:
                pass

        if buf is not None and len(buf) == pagesize:
            sig = buf[pagesize - 10:]
            if sig == 'SWAP-SPACE':
                raise OldSwapError
            if sig == 'S1SUSPEND\x00' or sig == 'S2SUSPEND\x00':
                raise SuspendError

        isys.swapon(device)

    def umount(self, device, path):
        # unfortunately, turning off swap is bad.
        raise RuntimeError, "unable to turn off swap"

    def formatDevice(self, entry, progress, chroot='/'):
        file = entry.device.setupDevice(chroot)
        rc = inutil.execWithRedirect("mkswap",
                                                                                                                        ['-v1', file],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5",
                                                                                                                        searchPath = 1)
        if rc:
            raise SystemError

    def labelDevice(self, entry, chroot):
        file = entry.device.setupDevice(chroot)
        devName = entry.device.getDevice()
        # we'll keep the SWAP-* naming for all devs but Compaq SMART2
        # nodes (#176074)
        if devName[0:6] == "cciss/":
            swapLabel = "SW-%s" % (devName)
        elif devName.startswith("mapper/"):
            swapLabel = "SWAP-%s" % (devName[7:],)
        else:
            swapLabel = "SWAP-%s" % (devName)
        label = labelFactory.createLabel(swapLabel, self.maxLabelChars)
        rc = inutil.execWithRedirect("mkswap",
                                                                                                                        ['-v1', "-L", label, file],
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5",
                                                                                                                        searchPath = 1)
        if rc:
            raise SystemError
        entry.setLabel(label)

    def clobberDevice(self, entry, chroot):
        pagesize = resource.getpagesize()
        dev = entry.device.setupDevice(chroot)
        try:
            fd = os.open(dev, os.O_RDWR)
            buf = "\0x00" * pagesize
            os.write(fd, buf)
        except:
            pass
        finally:
            try:
                os.close(fd)
            except:
                pass

fileSystemTypeRegister(swapFileSystem())

class FATFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = parted.file_system_type_get("fat32")
        self.formattable = 1
        self.checked = 0
        self.maxSizeMB = 1024 * 1024
        self.name = "vfat"
        self.packages = [ "dosfstools" ]

    def formatDevice(self, entry, progress, chroot='/'):
        devicePath = entry.device.setupDevice(chroot)
        devArgs = self.getDeviceArgs(entry.device)
        args = [ devicePath ]
        args.extend(devArgs)

        rc = inutil.execWithRedirect("mkdosfs", args,
                                                                                                                        stdout = "/dev/tty5",
                                                                                                                        stderr = "/dev/tty5", searchPath = 1)
        if rc:
            raise SystemError

fileSystemTypeRegister(FATFileSystem())

class NTFSFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.partedFileSystemType = parted.file_system_type_get("ntfs")
        self.formattable = 0
        self.checked = 0
        self.name = "ntfs"

fileSystemTypeRegister(NTFSFileSystem())

class ForeignFileSystem(FileSystemType):
    def __init__(self):
        FileSystemType.__init__(self)
        self.formattable = 0
        self.checked = 0
        self.name = "foreign"

    def formatDevice(self, entry, progress, chroot='/'):
        return

fileSystemTypeRegister(ForeignFileSystem())

class PsudoFileSystem(FileSystemType):
    def __init__(self, name):
        FileSystemType.__init__(self)
        self.formattable = 0
        self.checked = 0
        self.name = name
        self.supported = 0

    def isKernelFS(self):
        return True

class ProcFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "proc")

fileSystemTypeRegister(ProcFileSystem())

class SysfsFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "sysfs")

fileSystemTypeRegister(SysfsFileSystem())

class DevptsFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "devpts")
        self.defaultOptions = "gid=5,mode=620"

    def isMountable(self):
        return 0

fileSystemTypeRegister(DevptsFileSystem())

class DevshmFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "tmpfs")

    def isMountable(self):
        return 0

fileSystemTypeRegister(DevshmFileSystem())

class AutoFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "auto")

    def mount(self, device, mountpoint, readOnly=0, bindMount=0, instroot = None):
        errNum = 0
        errMsg = "cannot mount auto filesystem on %s of this type" % device

        if not self.isMountable():
            return
        inutil.mkdirChain("%s/%s" %(instroot, mountpoint))
        if flags.selinux:
            ret = isys.resetFileContext(mountpoint, instroot)
            log.info("set SELinux context for mountpoint %s to %s" %(mountpoint, ret))

        for fs in getFStoTry (device):
            try:
                isys.mount (device, mountpoint, fstype = fs, readOnly = readOnly,
                        bindMount = bindMount)
                return
            except SystemError, (num, msg):
                errNum = num
                errMsg = msg
                continue

        raise SystemError (errNum, errMsg)

    def umount(self, device, path):
        isys.umount(path, removeDir = 0)

fileSystemTypeRegister(AutoFileSystem())

class BindFileSystem(PsudoFileSystem):
    def __init__(self):
        PsudoFileSystem.__init__(self, "bind")

    def isMountable(self):
        return 1

fileSystemTypeRegister(BindFileSystem())

class FileSystemSet:
    def __init__(self):
        self.messageWindow = None
        self.progressWindow = None
        self.waitWindow = None
        self.mountcount = 0
        self.migratedfs = 0
        self.reset()
        self.volumesCreated = 0

    def isActive(self):
        return self.mountcount != 0

    def registerMessageWindow(self, method):
        self.messageWindow = method

    def registerProgressWindow(self, method):
        self.progressWindow = method

    def registerWaitWindow(self, method):
        self.waitWindow = method

    def reset (self):
        self.entries = []
        proc = FileSystemSetEntry(Device(device="proc"), '/proc',
                                                                                                                fileSystemTypeGet("proc"))
        self.add(proc)
        sys = FileSystemSetEntry(Device(device="sys"), '/sys',
                                                                                                        fileSystemTypeGet("sysfs"))
        self.add(sys)
        pts = FileSystemSetEntry(Device(device="devpts"), '/dev/pts',
                                                                                                        fileSystemTypeGet("devpts"), "gid=5,mode=620")
        self.add(pts)
        shm = FileSystemSetEntry(Device(device="shm"), '/dev/shm',
                                                                                                        fileSystemTypeGet("tmpfs"))
        self.add(shm)

    def verify (self):
        for entry in self.entries:
            if type(entry.__dict__) != type({}):
                raise RuntimeError, "fsset internals inconsistent"

    def add (self, newEntry):
        # Should object A be sorted after object B?  Take mountpoints and
        # device names into account so bind mounts are sorted correctly.
        def comesAfter(a, b):
            mntA = a.mountpoint
            mntB = b.mountpoint
            devA = a.device.getDevice()
            devB = b.device.getDevice()

            if not mntB or not devB:
                return True
            if not mntA or not devA:
                return False

            if (mntA.startswith(mntB) and mntA != mntB) or (devA.startswith(mntB) and devA != devB):
                return True
            else:
                return False

        # Remove preexisting duplicate entries - pseudo filesystems are
        # duplicate if they have the same filesystem type as an existing one.
        # Otherwise, they have to have the same device and mount point
        # (required to check for bind mounts).
        for existing in self.entries:
            if (isinstance (newEntry.fsystem, PsudoFileSystem) and existing.fsystem.getName() == newEntry.fsystem.getName()) or (existing.device.getDevice() == newEntry.device.getDevice() and existing.mountpoint == newEntry.mountpoint):
                self.remove(existing)

                ### debuggin'
                #log.info ("fsset at %s\n"
                #                                       "adding entry for %s\n"
                #                                       "entry object %s, class __dict__ is %s",
                #                                       self, entry.mountpoint, entry,
                #                                       isys.printObject(entry.__dict__))

        insertAt = 0

        # Special case for /.
        if newEntry.mountpoint == "/":
            self.entries.insert(insertAt, newEntry)
            return

        # doesn't matter where these get added, so just put them at the end
        if not newEntry.mountpoint or not newEntry.mountpoint.startswith("/") or self.entries == []:
            self.entries.append(newEntry)
            return

        for entry in self.entries:
            if comesAfter(newEntry, entry):
                insertAt = self.entries.index(entry)+1

        self.entries.insert(insertAt, newEntry)

    def remove (self, entry):
        self.entries.remove(entry)

    def getEntryByMountPoint(self, mount):
        for entry in self.entries:
            if entry.mountpoint == mount:
                return entry
        return None

    def getEntryByDeviceName(self, dev):
        for entry in self.entries:
            if entry.device.getDevice() == dev:
                return entry
        return None

    def copy(self):
        new = FileSystemSet()
        for entry in self.entries:
            new.add(entry)
        return new

    def fstab(self):
        format = "%-23s %-23s %-7s %-15s %d %d\n"
        fstab = ""
        for entry in self.entries:
            if entry.mountpoint:
                if entry.getLabel():
                    device = "LABEL=%s" % (entry.getLabel(),)
                else:
                    device = devify(entry.device.getDevice())
                fstab = fstab + entry.device.getComment()
                fstab = fstab + format % (device, entry.mountpoint,
                                                                                                                        entry.fsystem.getName(),
                                                                                                                        entry.options, entry.fsck,
                                                                                                                        entry.order)
        return fstab

    def mtab(self):
        format = "%s %s %s %s 0 0\n"
        mtab = ""
        for entry in self.entries:
            if not entry.isMounted():
                continue
            if entry.mountpoint:
                # swap doesn't end up in the mtab
                if entry.fsystem.getName() == "swap":
                    continue
                if entry.options:
                    options = "rw," + entry.options
                else:
                    options = "rw"
                mtab = mtab + format % (devify(entry.device.getDevice()),
                                                                                                                entry.mountpoint,
                                                                                                                entry.fsystem.getName(),
                                                                                                                options)
        return mtab


    def write(self, prefix):
        f = open(prefix + "/etc/fstab", "w")
        f.write(self.fstab())
        f.close()

        # touch mtab
        open(prefix + "/etc/mtab", "w+")
        f.close()

    ## XXX
    def mkDevRoot(self, instPath):
        root = self.getEntryByMountPoint("/")
        dev = "%s/dev/%s" % (instPath, root.device.getDevice())
        rdev = os.stat(dev).st_rdev

        #if not os.path.exists("%s/dev/root" %(instPath,)):
        #       os.mknod("%s/dev/root" % (instPath,), stat.S_IFBLK | 0600, rdev)

    # return the "boot" device
    def getBootDev(self):
        mntDict = {}
        bootDev = None
        for entry in self.entries:
            mntDict[entry.mountpoint] = entry.device

        if mntDict.has_key("/boot"):
            bootDev = mntDict['/boot']
        elif mntDict.has_key("/"):
            bootDev = mntDict['/']

        return bootDev

    def bootloaderChoices(self, diskSet, bl):
        ret = {}
        bootDev = self.getBootDev()

        if bootDev is None:
            log.warning("no boot device set")
            return ret

        ret['boot'] = (bootDev.device, N_("First sector of boot partition"))
        ret['mbr']  = (bl.drivelist[0], N_("Master Boot Record (MBR)"))
        return ret

    # set active partition on disks
    # if an active partition is set, leave it alone; if none set
    # set either our boot partition or the first partition on the drive active
    def setActive(self, diskset):
        dev = self.getBootDev()

        if dev is None:
            return

        bootDev = dev.device

        for drive in diskset.disks.keys():
            foundActive = 0
            bootPart = None
            disk = diskset.disks[drive]
            part = disk.next_partition()
            while part:
                if not part.is_active():
                    part = disk.next_partition(part)
                    continue

                if not part.is_flag_available(parted.PARTITION_BOOT):
                    foundActive = 1
                    part = None
                    continue

                if part.get_flag(parted.PARTITION_BOOT):
                    foundActive = 1
                    part = None
                    continue

                if not bootPart:
                    bootPart = part

                if partedUtils.get_partition_name(part) == bootDev:
                    bootPart = part

                part = disk.next_partition(part)

            if bootPart and not foundActive:
                bootPart.set_flag(parted.PARTITION_BOOT, 1)

            if bootPart:
                del bootPart

    def formatSwap(self, chroot, forceFormat=False):
        formatted = []
        notformatted = []

        for entry in self.entries:
            if (not entry.fsystem or not entry.fsystem.getName() == "swap" or
                    entry.isMounted()):
                continue
            if not entry.getFormat():
                if not forceFormat:
                    notformatted.append(entry)
                    continue
            try:
                self.formatEntry(entry, chroot)
                formatted.append(entry)
            except SystemError:
                if self.messageWindow:
                    self.messageWindow(_("Error"),
                                                                                             _("An error occurred trying to "
                                                                                                     "initialize swap on device %s.  This "
                                                                                                     "problem is serious, and the install "
                                                                                                     "cannot continue.\n\n"
                                                                                                     "Press <Enter> to reboot your system.")
                                                                                            % (entry.device.getDevice(),))
                sys.exit(0)

        for entry in formatted:
            try:
                self.labelEntry(entry, chroot)
            except SystemError:
                # should be OK, fall back to by device
                pass

        # find if there's a label on the ones we're not formatting
        for entry in notformatted:
            dev = entry.device.getDevice()
            if not dev or dev == "none":
                continue
            try:
                label = isys.readFSLabel(dev)
            except:
                continue
            if label:
                entry.setLabel(label)

    def turnOnSwap(self, chroot, upgrading=False):
        def swapErrorDialog (msg, format_button_text, entry):
            buttons = [_("Skip"), format_button_text, _("Reboot")]
            ret = self.messageWindow(_("Error"), msg, type="custom",
                                                                                                                    custom_buttons=buttons,
                                                                                                                    custom_icon="warning")
            if ret == 0:
                self.entries.remove(entry)
            elif ret == 1:
                self.formatEntry(entry, chroot)
                entry.mount(chroot)
                self.mountcount = self.mountcount + 1
            else:
                sys.exit(0)

        for entry in self.entries:
            if (entry.fsystem and entry.fsystem.getName() == "swap"
                            and not entry.isMounted()):
                try:
                    entry.mount(chroot)
                    self.mountcount = self.mountcount + 1
                except OldSwapError:
                    if self.messageWindow:
                        msg = _("The swap device:\n\n     /dev/%s\n\n"
                                                        "is a version 0 Linux swap partition. If you "
                                                        "want to use this device, you must reformat as "
                                                        "a version 1 Linux swap partition. If you skip "
                                                        "it, the installer will ignore it during the "
                                                        "installation.") % (entry.device.getDevice())

                        swapErrorDialog(msg, _("Reformat"), entry)
                except SuspendError:
                    if self.messageWindow:
                        if upgrading:
                            msg = _("The swap device:\n\n     /dev/%s\n\n"
                                                            "in your /etc/fstab file is currently in "
                                                            "use as a software suspend partition, "
                                                            "which means your system is hibernating. "
                                                            "To perform an upgrade, please shut down "
                                                            "your system rather than hibernating it.") \
                                                    % (entry.device.getDevice())
                        else:
                            msg = _("The swap device:\n\n     /dev/%s\n\n"
                                                            "in your /etc/fstab file is currently in "
                                                            "use as a software suspend partition, "
                                                            "which means your system is hibernating. "
                                                            "If you are performing a new install, "
                                                            "make sure the installer is set "
                                                            "to format all swap partitions.") \
                                                    % (entry.device.getDevice())

                        # choose your own adventure swap partitions...
                        msg = msg + _("\n\nChoose Skip if you want the "
                              "installer to ignore this partition during "
                              "the upgrade.  Choose Format to reformat "
                              "the partition as swap space.  Choose Reboot "
                              "to restart the system.")

                        swapErrorDialog(msg, _("Format"), entry)
                    else:
                        sys.exit(0)

                except SystemError, (num, msg):
                    if self.messageWindow:
                        if upgrading:
                            self.messageWindow(_("Error"),
                                                                                                            _("Error enabling swap device "
                                                                                                            "%s: %s\n\n"
                                                                                                            "The /etc/fstab on your "
                                                                                                            "upgrade partition does not "
                                                                                                            "reference a valid swap "
                                                                                                            "partition.\n\n"
                                                                                                            "Press OK to reboot your "
                                                                                                            "system.")
                                                                                                    % (entry.device.getDevice(), msg))
                        else:
                            self.messageWindow(_("Error"),
                                                                                                    _("Error enabling swap device "
                                                                                                     "%s: %s\n\n"
                                                                                                     "This most likely means this "
                                                                                                     "swap partition has not been "
                                                                                                     "initialized.\n\n"
                                                                                                     "Press OK to reboot your "
                                                                                                     "system.")
                                                                                            % (entry.device.getDevice(), msg))
                    sys.exit(0)

    def labelEntry(self, entry, chroot):
        label = entry.device.getLabel()
        if label:
            entry.setLabel(label)
            if labelFactory.isLabelReserved(label):
                entry.device.doLabel = 1
        if entry.device.doLabel is not None:
            entry.fsystem.labelDevice(entry, chroot)

    def formatEntry(self, entry, chroot):
        if entry.mountpoint:
            log.info("formatting %s as %s" %(entry.mountpoint, entry.fsystem.name))
        entry.fsystem.clobberDevice(entry, chroot)
        entry.fsystem.formatDevice(entry, self.progressWindow, chroot)

    def badblocksEntry(self, entry, chroot):
        entry.fsystem.badblocksDevice(entry, self.progressWindow, chroot)

    def getMigratableEntries(self):
        retval = []
        for entry in self.entries:
            if entry.origfsystem and entry.origfsystem.isMigratable():
                retval.append(entry)

        return retval

    def formattablePartitions(self):
        list = []
        for entry in self.entries:
            if entry.fsystem.isFormattable():
                list.append (entry)
        return list

    def checkBadblocks(self, chroot='/'):
        for entry in self.entries:
            if (not entry.fsystem.isFormattable() or not entry.getBadblocks()
                            or entry.isMounted()):
                continue
            try:
                self.badblocksEntry(entry, chroot)
            except BadBlocksError:
                log.error("Bad blocks detected on device %s",entry.device.getDevice())
                if self.messageWindow:
                    self.messageWindow(_("Error"),
                                                                                            _("Bad blocks have been detected on "
                                                                                                    "device /dev/%s. We do "
                                                                                                    "not recommend you use this device."
                                                                                                    "\n\n"
                                                                                                    "Press <Enter> to reboot your system")
                                                                                            % (entry.device.getDevice(),))
                sys.exit(0)

            except SystemError:
                if self.messageWindow:
                    self.messageWindow(_("Error"),
                                                                                             _("An error occurred searching for "
                                                                                                    "bad blocks on %s.  This problem is "
                                                                                                    "serious, and the install cannot "
                                                                                                    "continue.\n\n"
                                                                                                    "Press <Enter> to reboot your system.")
                                                                                                    % (entry.device.getDevice(),))
                sys.exit(0)

    def makeFilesystems(self, chroot='/'):
        formatted = []
        notformatted = []
        for entry in self.entries:
            if (not entry.fsystem.isFormattable() or not entry.getFormat()
                            or entry.isMounted()):
                notformatted.append(entry)
                continue
            try:
                self.formatEntry(entry, chroot)
                formatted.append(entry)
            except SystemError:
                if self.messageWindow:
                    self.messageWindow(_("Error"),
                                                                                             _("An error occurred trying to "
                                                                                                    "format %s.  This problem is "
                                                                                                    "serious, and the install cannot "
                                                                                                    "continue.\n\n"
                                                                                                    "Press <Enter> to reboot your system.")
                                                                                            % (entry.device.getDevice(),))
                sys.exit(0)

        for entry in formatted:
            try:
                self.labelEntry(entry, chroot)
            except SystemError:
                # should be OK, we'll still use the device name to mount.
                pass

        # go through and have labels for the ones we don't format
        for entry in notformatted:
            dev = entry.device.getDevice()
            if not dev or dev == "none":
                continue
            if not entry.mountpoint or entry.mountpoint == "swap":
                continue
            try:
                label = isys.readFSLabel(dev)
            except:
                continue
            if label:
                entry.setLabel(label)
            else:
                self.labelEntry(entry, chroot)

    def haveMigratedFilesystems(self):
        return self.migratedfs

    def migrateFilesystems(self, chroot='/'):
        if self.migratedfs:
            return

        for entry in self.entries:
            if not entry.origfsystem:
                continue

            if not entry.origfsystem.isMigratable() or not entry.getMigrate():
                continue
            try:
                entry.origfsystem.migrateFileSystem(entry, self.messageWindow, chroot)
            except SystemError:
                if self.messageWindow:
                    self.messageWindow(_("Error"),
                                                                                             _("An error occurred trying to "
                                                                                                     "migrate %s.  This problem is "
                                                                                                     "serious, and the install cannot "
                                                                                                     "continue.\n\n"
                                                                                                     "Press <Enter> to reboot your system.")
                                                                                            % (entry.device.getDevice(),))
                sys.exit(0)

            self.migratedfs = 1

    def mountFilesystems(self, pomona, raiseErrors = 0, readOnly = 0):
        #protected = pomona.method.protectedPartitions()
        protected = []

        for entry in self.entries:
            # Don't try to mount a protected partition, since it will already
            # have been mounted as the installation source.
            if not entry.fsystem.isMountable() or (protected and entry.device.getDevice() in protected):
                continue

            try:
                log.info("trying to mount %s on %s" %(entry.device.getDevice(), entry.mountpoint))
                entry.mount(pomona.rootPath, readOnly = readOnly)
                self.mountcount = self.mountcount + 1
            except OSError, (num, msg):
                if self.messageWindow:
                    if num == errno.EEXIST:
                        self.messageWindow(_("Invalid mount point"),
                                                                                                 _("An error occurred when trying "
                                                                                                        "to create %s.  Some element of "
                                                                                                        "this path is not a directory. "
                                                                                                        "This is a fatal error and the "
                                                                                                        "install cannot continue.\n\n"
                                                                                                        "Press <Enter> to reboot your "
                                                                                                        "system.") % (entry.mountpoint,))
                    else:
                        self.messageWindow(_("Invalid mount point"),
                                                                                                 _("An error occurred when trying "
                                                                                                         "to create %s: %s.  This is "
                                                                                                         "a fatal error and the install "
                                                                                                         "cannot continue.\n\n"
                                                                                                         "Press <Enter> to reboot your "
                                                                                                         "system.") % (entry.mountpoint, msg))
                    sys.exit(0)
            except SystemError, (num, msg):
                if raiseErrors:
                    raise SystemError, (num, msg)

                if self.messageWindow:
                    if not entry.fsystem.isLinuxNativeFS():
                        ret = self.messageWindow(_("Unable to mount filesystem"),
                                                                                                                         _("An error occurred mounting "
                                                                                                                                "device %s as %s.  You may "
                                                                                                                                "continue installation, but "
                                                                                                                                "there may be problems.") %
                                                                                                                                (entry.device.getDevice(),
                                                                                                                                entry.mountpoint),
                                                                                                                                type="custom", custom_icon="warning",
                                                                                                                                custom_buttons=[_("_Reboot"), _("_Continue")])

                        if ret == 0:
                            sys.exit(0)
                        else:
                            continue
                    else:
                        if pomona.id.getUpgrade() and not entry.getLabel():
                            errStr = _("Error mounting device %s as %s: "
                                                                     "%s\n\n"
                                                                     "Devices in /etc/fstab should be "
                                                                     "specified by label, not by device name."
                                                                     "\n\n"
                                                                     "Press OK to reboot your system.") % (entry.device.getDevice(), entry.mountpoint, msg)
                        else:
                            errStr = _("Error mounting device %s as %s: "
                                                                    "%s\n\n"
                                                                    "This most likely means this "
                                                                    "partition has not been formatted."
                                                                    "\n\n"
                                                                    "Press OK to reboot your system.") % (entry.device.getDevice(), entry.mountpoint, msg)

                        self.messageWindow(_("Error"), errStr)

                        sys.exit(0)

    def filesystemSpace(self, chroot='/'):
        space = []
        for entry in self.entries:
            if not entry.isMounted():
                continue
            # we can't put swap files on swap partitions; that's nonsense
            if entry.mountpoint == "swap":
                continue
            path = "%s/%s" % (chroot, entry.mountpoint)
            try:
                space.append((entry.mountpoint, isys.fsSpaceAvailable(path)))
            except SystemError:
                log.error("failed to get space available in filesystemSpace() for %s" %(entry.mountpoint,))

        def spaceSort(a, b):
            (m1, s1) = a
            (m2, s2) = b

            if (s1 > s2):
                return -1
            elif s1 < s2:
                return 1
            return 0

        space.sort(spaceSort)
        return space

    def hasDirtyFilesystems(self, mountpoint):
        ret = []

        for entry in self.entries:
            # XXX - multifsify, virtualize isdirty per fstype
            if entry.fsystem.getName() != "ext2": continue
            if entry.getFormat(): continue
            if isinstance(entry.device.getDevice(), BindMountDevice): continue

            try:
                if isys.ext2IsDirty(entry.device.getDevice()):
                    log.info("%s is a dirty ext2 partition" % entry.device.getDevice())
                    ret.append(entry.device.getDevice())
            except Exception, e:
                log.error("got an exception checking %s for being dirty, hoping it's not" %(entry.device.getDevice(),))

        return ret

    def umountFilesystems(self, instPath, ignoreErrors = 0, swapoff = True):
        # XXX remove special case
        try:
            isys.umount(instPath + '/proc/bus/usb', removeDir = 0)
            log.info("Umount USB OK")
        except:
#                       log.error("Umount USB Fail")
            pass

        # take a slice so we don't modify self.entries
        reverse = self.entries[:]
        reverse.reverse()

        for entry in reverse:
            if entry.mountpoint == "swap" and not swapoff:
                continue
            entry.umount(instPath)

class FileSystemSetEntry:
    def __init__ (self, device, mountpoint,
                                                            fsystem=None, options=None,
                                                            origfsystem=None, migrate=0,
                                                            order=-1, fsck=-1, format=0,
                                                            badblocks = 0, bytesPerInode=4096):
        if not fsystem:
            fsystem = fileSystemTypeGet("ext2")
        self.device = device
        self.mountpoint = mountpoint
        self.fsystem = fsystem
        self.origfsystem = origfsystem
        self.migrate = migrate
        if options:
            self.options = options
        else:
            self.options = fsystem.getDefaultOptions(mountpoint)
        self.options += device.getDeviceOptions()
        self.mountcount = 0
        self.label = None
        if fsck == -1:
            self.fsck = fsystem.isChecked()
        else:
            self.fsck = fsck
        if order == -1:
            if mountpoint == '/':
                self.order = 1
            elif self.fsck:
                self.order = 2
            else:
                self.order = 0
        else:
            self.order = order
            if format and not fsystem.isFormattable():
                raise RuntimeError, ("file system type %s is not formattable, "
                                                                                                 "but has been added to fsset with format "
                                                                                                 "flag on" % fsystem.getName())
        self.format = format
        self.badblocks = badblocks
        self.bytesPerInode = bytesPerInode

    def mount(self, chroot='/', devPrefix='/dev', readOnly = 0):
        device = self.device.setupDevice(chroot, devPrefix=devPrefix)

        # FIXME: we really should migrate before turnOnFilesystems.
        # but it's too late now
        if (self.migrate == 1) and (self.origfsystem is not None):
            self.origfsystem.mount(device, "%s" % (self.mountpoint,),
                                                                                                            readOnly = readOnly,
                                                                                                            bindMount = isinstance(self.device,
                                                                                                            BindMountDevice),
                                                                                                            instroot = chroot)
        else:
            self.fsystem.mount(device, "%s" % (self.mountpoint,),
                                                                                            readOnly = readOnly,
                                                                                            bindMount = isinstance(self.device,
                                                                                            BindMountDevice),
                                                                                            instroot = chroot)

        self.mountcount = self.mountcount + 1

    def umount(self, chroot='/'):
        if self.mountcount > 0:
            try:
                self.fsystem.umount(self.device, "%s/%s" % (chroot, self.mountpoint))
                self.mountcount = self.mountcount - 1
            except RuntimeError:
                pass

    def setFileSystemType(self, fstype):
        self.fsystem = fstype

    def setBadblocks(self, state):
        self.badblocks = state

    def getBadblocks(self):
        return self.badblocks

    def getMountPoint(self):
        return self.mountpoint

    def setFormat (self, state):
        if self.migrate and state:
            raise ValueError, "Trying to set format bit on when migrate is set!"
        self.format = state

    def getFormat (self):
        return self.format

    def setMigrate (self, state):
        if self.format and state:
            raise ValueError, "Trying to set migrate bit on when format is set!"
        self.migrate = state

    def getMigrate (self):
        return self.migrate

    def isMounted (self):
        return self.mountcount > 0

    def getLabel (self):
        return self.label

    def setLabel (self, label):
        self.label = label

    def __str__(self):
        if not self.mountpoint:
            mntpt = "None"
        else:
            mntpt = self.mountpoint

        str = ("fsentry -- device: %(device)s   mountpoint: %(mountpoint)s\n"
                                 "  fsystem: %(fsystem)s format: %(format)s\n"
                                 "  ismounted: %(mounted)s  options: '%(options)s'\n"
                                 "  bytesPerInode: %(bytesPerInode)s label: %(label)s\n"
                                % {"device": self.device.getDevice(), "mountpoint": mntpt,
                                        "fsystem": self.fsystem.getName(), "format": self.format,
                                        "mounted": self.mountcount, "options": self.options,
                                        "bytesPerInode": self.bytesPerInode, "label": self.label})
        return str


class Device:
    def __init__(self, device = "none"):
        self.device = device
        self.label = None
        self.isSetup = 0
        self.doLabel = 1
        self.deviceOptions = ""

    def getComment (self):
        return ""

    def getDevice (self, asBoot = 0):
        return self.device

    def setupDevice (self, chroot='/', devPrefix='/dev'):
        return self.device

    def cleanupDevice (self, chroot, devPrefix='/dev'):
        pass

    def solidify (self):
        pass

    def getName(self):
        return self.__class__.__name__

    def getLabel(self):
        try:
            return isys.readFSLabel(self.setupDevice(), makeDevNode = 0)
        except:
            return ""

    def setAsNetdev(self):
        """Ensure we're set up so that _netdev is in our device options."""
        if "_netdev" not in self.deviceOptions:
            self.deviceOptions += ",_netdev"

    def isNetdev(self):
        """Check to see if we're set as a netdev"""
        if "_netdev" in self.deviceOptions:
            return True
        return False

    def getDeviceOptions(self):
        return self.deviceOptions

class DevDevice(Device):
    """ Device with a device node rooted in /dev that we just always use
        the pre-created device node for."""
    def __init__(self, dev):
        Device.__init__(self)
        self.device = dev

    def getDevice(self, asBoot = 0):
        return self.device

    def setupDevice(self, chroot='/', devPrefix='/dev'):
        return "/dev/%s" %(self.getDevice(),)


ext2 = fileSystemTypeGet("ext2")

class PartitionDevice(Device):
    def __init__(self, partition):
        Device.__init__(self)
        if type(partition) != types.StringType:
            raise ValueError, "partition must be a string"
        self.device = partition

    def setupDevice(self, chroot="/", devPrefix='/dev'):
        path = '%s/%s' % (devPrefix, self.getDevice(),)
        return path

class PartedPartitionDevice(PartitionDevice):
    def __init__(self, partition):
        Device.__init__(self)
        self.device = None
        self.partition = partition

    def getDevice(self, asBoot = 0):
        if not self.partition:
            return self.device

        return partedUtils.get_partition_name(self.partition)

    def solidify(self):
        # drop reference on the parted partition object and note
        # the current minor number allocation
        self.device = self.getDevice()
        self.partition = None

class BindMountDevice(Device):
    def __init__(self, directory):
        Device.__init__(self)
        self.device = directory

    def setupDevice(self, chroot="/", devPrefix="/tmp"):
        return chroot + self.device

class SwapFileDevice(Device):
    def __init__(self, file):
        Device.__init__(self)
        self.device = file
        self.size = 0

    def setSize (self, size):
        self.size = size

    def setupDevice (self, chroot="/", devPrefix='/tmp'):
        file = os.path.normpath(chroot + self.getDevice())
        if not os.access(file, os.R_OK):
            if self.size:
                # make sure the permissions are set properly
                fd = os.open(file, os.O_CREAT, 0600)
                os.close(fd)
                isys.ddfile(file, self.size, None)
            else:
                raise SystemError, (0, "swap file creation necessary, but "
                                                                                        "required size is unknown.")
        return file

# This is a device that describes a swap file that is sitting on
# the loopback filesystem host for partitionless installs.
# The piggypath is the place where the loopback file host filesystem
# will be mounted
class PiggybackSwapFileDevice(SwapFileDevice):
    def __init__(self, piggypath, file):
        SwapFileDevice.__init__(self, file)
        self.piggypath = piggypath

    def setupDevice(self, chroot="/", devPrefix='/tmp'):
        return SwapFileDevice.setupDevice(self, self.piggypath, devPrefix)

class LoopbackDevice(Device):
    def __init__(self, hostPartition, hostFs):
        Device.__init__(self)
        self.host = "/dev/" + hostPartition
        self.hostfs = hostFs
        self.device = "loop1"

    def setupDevice(self, chroot="/", devPrefix='/tmp/'):
        if not self.isSetup:
            isys.mount(self.host[5:], "/mnt/loophost", fstype = "vfat")
            self.device = allocateLoopback("/mnt/loophost/redhat.img")
            if not self.device:
                raise SystemError, "Unable to allocate loopback device"
            self.isSetup = 1
            path = '%s/%s' % (devPrefix, self.getDevice())
        else:
            path = '%s/%s' % (devPrefix, self.getDevice())
            #isys.makeDevInode(self.getDevice(), path)
        path = os.path.normpath(path)
        return path

    def getComment (self):
        return "# LOOP1: %s %s /redhat.img\n" % (self.host, self.hostfs)

def makeDevice(dev):
    device = DevDevice(dev)
    return device

def readFstab(pomona):
    path = pomona.rootPath + '/etc/fstab'
    intf = pomona.intf
    fsset = FileSystemSet()

    # first, we look at all the disks on the systems and get any ext2/3
    # labels off of the filesystem.
    # temporary, to get the labels
    diskset = partedUtils.DiskSet(pomona)
    diskset.openDevices()
    labels = diskset.getLabels()

    labelToDevice = {}
    for device, label in labels.items():
        if not labelToDevice.has_key(label):
            labelToDevice[label] = device
        elif intf is not None:
            try:
                intf.messageWindow(_("Duplicate Labels"),
                                                                                         _("Multiple devices on your system are "
                                                                                                 "labelled %s.  Labels across devices must be "
                                                                                                 "unique for your system to function "
                                                                                                 "properly.\n\n"
                                                                                                 "Please fix this problem and restart the "
                                                                                                 "installation process.")
                                                                                                % (label,), type="custom", custom_icon="error",
                                                                                                        custom_buttons=[_("_Reboot")])
            except TypeError:
                intf.messageWindow(_("Invalid Label"),
                                                                                         _("An invalid label was found on device "
                                                                                                 "%s.  Please fix this problem and restart "
                                                                                                 "the installation process.")
                                                                                                % (device,), type="custom", custom_icon="error",
                                                                                                        custom_buttons=[_("_Reboot")])

                sys.exit(0)
        else:
            log.warning("Duplicate labels for %s, but no intf so trying "
                                                            "to continue" % (label,))

    # mark these labels found on the system as used so the factory
    # doesn't give them to another device
    labelFactory.reserveLabels(labels)

    loopIndex = {}

    f = open (path, "r")
    lines = f.readlines ()
    f.close()

    for line in lines:
        fields = string.split(line)

        if not fields: continue

        if line[0] == "#":
            # skip all comments
            continue

        # all valid fstab entries have 6 fields; if the last two are missing
        # they are assumed to be zero per fstab(5)
        if len(fields) < 4:
            continue
        elif len(fields) == 4:
            fields.append(0)
            fields.append(0)
        elif len(fields) == 5:
            fields.append(0)
        elif len(fields) > 6:
            continue

        if string.find(fields[3], "noauto") != -1: continue

        # shenanigans to handle ext3,ext2 format in fstab
        fstotry = fields[2]
        if fstotry.find(","):
            fstotry = fstotry.split(",")
        else:
            fstotry = [ fstotry ]
        fsystem = None
        for fs in fstotry:
            # if we don't support mounting the filesystem, continue
            if not fileSystemTypes.has_key(fs):
                continue
            fsystem = fileSystemTypeGet(fs)
            break
        # "none" is valid as an fs type for bind mounts (#151458)
        if fsystem is None and (string.find(fields[3], "bind") == -1):
            continue
        label = None
        if fields[0] == "none":
            device = Device()
        elif ((string.find(fields[3], "bind") != -1) and fields[0].startswith("/")):
            # it's a bind mount, they're Weird (tm)
            device = BindMountDevice(fields[0])
            fsystem = fileSystemTypeGet("bind")
        elif len(fields) >= 6 and fields[0].startswith('LABEL='):
            label = fields[0][6:]
            if labelToDevice.has_key(label):
                device = makeDevice(labelToDevice[label])
            else:
                log.warning ("fstab file has LABEL=%s, but this label "
                                                                 "could not be found on any file system", label)
                # bad luck, skip this entry.
                continue
        elif fields[2] == "swap" and not fields[0].startswith('/dev/'):
            # swap files
            file = fields[0]
            if file.startswith('/initrd/loopfs/'):
                file = file[14:]
                device = PiggybackSwapFileDevice("/mnt/loophost", file)
            else:
                device = SwapFileDevice(file)
        elif fields[0].startswith('/dev/loop'):
            # look up this loop device in the index to find the
            # partition that houses the filesystem image
            # XXX currently we assume /dev/loop1
            if loopIndex.has_key(device):
                (dev, fs) = loopIndex[device]
                device = LoopbackDevice(dev, fs)
        elif fields[0].startswith('/dev/'):
            device = makeDevice(fields[0][5:])
        else:
            device = Device(device = fields[0])

        # if they have a filesystem being mounted as auto, we need
        # to sniff around a bit to figure out what it might be
        # if we fail at all, though, just ignore it
        if fsystem == "auto" and device.getDevice() != "none":
            try:
                tmp = partedUtils.sniffFilesystemType("/dev/%s" %(device.setupDevice(),))
                if tmp is not None:
                    fsystem = tmp
            except:
                pass

        entry = FileSystemSetEntry(device, fields[1], fsystem, fields[3],
                           origfsystem=fsystem)
        if label:
            entry.setLabel(label)
        fsset.add(entry)
        return fsset

def getDevFD(device):
    try:
        fd = os.open(device, os.O_RDONLY)
    except:
        file = '/dev/' + device
        try:
            fd = os.open(file, os.O_RDONLY)
        except:
            return -1
    return fd

def isValidExt2(device):
    fd = getDevFD(device)
    if fd == -1:
        return 0

    buf = os.read(fd, 2048)
    os.close(fd)

    if len(buf) != 2048:
        return 0

    if struct.unpack("<H", buf[1080:1082]) == (0xef53,):
        return 1

    return 0

def isValidXFS(device):
    fd = getDevFD(device)
    if fd == -1:
        return 0

    buf = os.read(fd, 4)
    os.close(fd)

    if len(buf) != 4:
        return 0

    if buf == "XFSB":
        return 1

    return 0

def isValidReiserFS(device):
    fd = getDevFD(device)
    if fd == -1:
        return 0

    '''
    ** reiserfs 3.5.x super block begins at offset 8K
    ** reiserfs 3.6.x super block begins at offset 64K
    All versions have a magic value of "ReIsEr" at
    offset 0x34 from start of super block
    '''
    reiserMagicVal = "ReIsEr"
    reiserMagicOffset = 0x34
    reiserSBStart = [64*1024, 8*1024]
    bufSize = 0x40  # just large enough to include the magic value
    for SBOffset in reiserSBStart:
        try:
            os.lseek(fd, SBOffset, 0)
            buf = os.read(fd, bufSize)
        except:
            buf = ""

        if len(buf) < bufSize:
            continue

        if (buf[reiserMagicOffset:reiserMagicOffset+len(reiserMagicVal)] == reiserMagicVal):
            os.close(fd)
            return 1

    os.close(fd)
    return 0

# this will return a list of types of filesystems which device
# looks like it could be to try mounting as
def getFStoTry(device):
    rc = []

    if isValidXFS(device):
        rc.append("xfs")

    if isValidReiserFS(device):
        rc.append("reiserfs")

    if isValidExt2(device):
        if isys.ext2HasJournal(device):
            rc.append("ext3")
        rc.append("ext2")

    ### XXX FIXME: need to check for swap

    return rc

def allocateLoopback(file):
    found = 1
    for i in range(8):
        dev = "loop%d" % (i,)
        path = "/dev/loop%d" % (i,)
        try:
            isys.losetup(path, file)
            found = 1
        except SystemError:
            continue
        break
    if found:
        return dev
    return None

def ext2FormatFilesystem(argList, messageFile, windowCreator, mntpoint):
    if windowCreator:
        w = windowCreator(_("Formatting"),
                                                                                _("Formatting %s file system...") % (mntpoint,), 100)
    else:
        w = None

    fd = os.open(messageFile, os.O_RDWR | os.O_CREAT | os.O_APPEND)
    p = os.pipe()
    childpid = os.fork()
    if not childpid:
        os.close(p[0])
        os.dup2(p[1], 1)
        os.dup2(fd, 2)
        os.close(p[1])
        os.close(fd)
        os.execvp(argList[0], argList)
        log.critical("failed to exec %s", argList)
        os._exit(1)

    os.close(p[1])

    # ignoring SIGCHLD would be cleaner then ignoring EINTR, but
    # we can't use signal() in this thread?

    s = 'a'
    while s and s != '\b':
        try:
            s = os.read(p[0], 1)
        except OSError, args:
            (num, str) = args
            if (num != 4):
                raise IOError, args

        os.write(fd, s)

    num = ''
    while s:
        try:
            s = os.read(p[0], 1)
            os.write(fd, s)

            if s != '\b':
                try:
                    num = num + s
                except:
                    pass
            else:
                if num and len(num):
                    l = string.split(num, '/')
                    try:
                        val = (int(l[0]) * 100) / int(l[1])
                    except (IndexError, TypeError):
                        pass
                    else:
                        w and w.set(val)
                num = ''
        except OSError, args:
            (errno, str) = args
            if (errno != 4):
                raise IOError, args

    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (num, msg):
        log.critical("exception from waitpid while formatting: %s %s" %(num, msg))
        status = None
    os.close(fd)

    w and w.pop()

    # *shrug*  no clue why this would happen, but hope that things are fine
    if status is None:
        return 0

    if os.WIFEXITED(status) and (os.WEXITSTATUS(status) == 0):
        return 0

    return 1

# copy and paste job from booty/bootloaderInfo.py...
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
