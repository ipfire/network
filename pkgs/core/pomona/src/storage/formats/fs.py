#!/usr/bin/python

import os
import tempfile

import isys

import util

from ..errors import *
from . import DeviceFormat, register_device_format

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

fs_configs = {}

def get_kernel_filesystems():
    fs_list = []
    for line in open("/proc/filesystems").readlines():
        fs_list.append(line.split()[-1])
    return fs_list

global kernel_filesystems
kernel_filesystems = get_kernel_filesystems()

class FS(DeviceFormat):
    """ Filesystem class. """
    _type = "Abstract Filesystem Class"  # fs type name
    _mountType = None                    # like _type but for passing to mount
    _name = None
    _mkfs = ""                           # mkfs utility
    _modules = []                        # kernel modules required for support
    _resizefs = ""                       # resize utility
    _labelfs = ""                        # labeling utility
    _fsck = ""                           # fs check utility
    _migratefs = ""                      # fs migration utility
    _defaultFormatOptions = []           # default options passed to mkfs
    _defaultMountOptions = ["defaults"]  # default options passed to mount
    _defaultLabelOptions = []
    _defaultCheckOptions = []
    _defaultMigrateOptions = []
    _migrationTarget = None
    lostAndFoundContext = None

    def __init__(self, installer, *args, **kwargs):
        """ Create a FS instance.

            Keyword Args:

                device -- path to the device containing the filesystem
                mountpoint -- the filesystem's mountpoint
                label -- the filesystem label
                uuid -- the filesystem UUID
                mountopts -- mount options for the filesystem
                size -- the filesystem's size in MiB
                exists -- indicates whether this is an existing filesystem

        """
        if self.__class__ is FS:
            raise TypeError("FS is an abstract class.")

        self.installer = installer

        DeviceFormat.__init__(self, self.installer, *args, **kwargs)
        # TODO: fsprofiles and other ways to add format args
        self.mountpoint = kwargs.get("mountpoint")
        self.mountopts = kwargs.get("mountopts")
        self.label = kwargs.get("label")

        # filesystem size does not necessarily equal device size
        self._size = kwargs.get("size")
        self._mountpoint = None     # the current mountpoint when mounted
        if self.exists:
            self._size = self._getExistingSize()

        self._targetSize = self._size

        if self.supported:
            self.loadModule()

    def _setTargetSize(self, newsize):
        """ Set a target size for this filesystem. """
        if not self.exists:
            raise FSError("filesystem has not been created")

        if newsize is None:
            # unset any outstanding resize request
            self._targetSize = None
            return

        if not self.minSize < newsize < self.maxSize:
            raise ValueError("invalid target size request")

        self._targetSize = newsize

    def _getTargetSize(self):
        """ Get this filesystem's target size. """
        return self._targetSize

    targetSize = property(_getTargetSize, _setTargetSize,
                          doc="Target size for this filesystem")

    def _getSize(self):
        """ Get this filesystem's size. """
        size = self._size
        if self.resizable and self.targetSize != size:
            size = self.targetSize
        return size

    size = property(_getSize, doc="This filesystem's size, accounting "
                                  "for pending changes")

    def _getExistingSize(self):
        """ Determine the size of this filesystem.  Filesystem must
            exist.
        """
        size = 0

        if self.mountable:
            origMountPoint = self._mountpoint

            tmppath = tempfile.mkdtemp(prefix='getsize-', dir='/tmp')
            self.mount(mountpoint=tmppath, options="ro")
            buf = os.statvfs(tmppath)
            self.unmount()
            os.rmdir(tmppath)

            self._mountpoint = origMountPoint

            size = (buf.f_frsize * buf.f_blocks) / 1024.0 / 1024.0

        return size

    @property
    def currentSize(self):
        """ The filesystem's current actual size. """
        size = 0
        if self.exists:
            size = self._size
        return float(size)

    def _getFormatOptions(self, options=None):
        argv = []
        if options and isinstance(options, list):
            argv.extend(options)
        argv.extend(self.defaultFormatOptions)
        argv.append(self.device)
        return argv

    def doFormat(self, *args, **kwargs):
        """ Create the filesystem.

            Arguments:

                None

            Keyword Arguments:

                intf -- InstallInterface instance
                options -- list of options to pass to mkfs

        """
        intf = kwargs.get("intf")
        options = kwargs.get("options")

        if self.exists:
            raise FormatCreateError("filesystem already exists", self.device)

        if not self.formattable:
            return

        if not self.mkfsProg:
            return

        if self.exists:
            return

        if not os.path.exists(self.device):
            raise FormatCreateError("device does not exist", self.device)

        argv = self._getFormatOptions(options=options)

        self.installer.window = None
        self.installer.window = self.installer.intf.progressWindow(_("Formatting"),
                                                                   _("Creating filesystem on %s...") % (self.device,),
                                                                   100, pulse = True)

        try:
            rc = util.execWithPulseProgress(self.mkfsProg,
                                             argv,
                                             stdout="/dev/tty5",
                                             stderr="/dev/tty5",
                                             progress=w)
        except Exception as e:
            raise FormatCreateError(e, self.device)
        finally:
            if self.installer.window:
                self.installer.window.pop()

        if rc:
            raise FormatCreateError("format failed: %s" % rc, self.device)

        self.exists = True
        self.notifyKernel()

    def doMigrate(self, intf=None):
        if not self.exists:
            raise FSError("filesystem has not been created")

        if not self.migratable or not self.migrate:
            return

        if not os.path.exists(self.device):
            raise FSError("device does not exist")

        # if journal already exists skip
        if isys.ext2HasJournal(self.device):
            self.installer.log.info("Skipping migration of %s, has a journal already." % self.device)
            return

        argv = self._defaultMigrateOptions[:]
        argv.append(self.device)
        try:
            rc = util.execWithRedirect(self.migratefsProg,
                                       argv,
                                       stdout = "/dev/tty5",
                                       stderr = "/dev/tty5",
                                       searchPath = 1)
        except Exception as e:
            raise FSMigrateError("filesystem migration failed: %s" % e, self.device)

        if rc:
            raise FSMigrateError("filesystem migration failed: %s" % rc, self.device)

        # the other option is to actually replace this instance with an
        # instance of the new filesystem type.
        self._type = self.migrationTarget

    @property
    def resizeArgs(self):
        argv = [self.device, "%d" % (self.targetSize,)]
        return argv

    def doResize(self, *args, **kwargs):
        """ Resize this filesystem to new size @newsize.

            Arguments:

                None

            Keyword Arguments:

                intf -- InstallInterface instance

        """
        intf = kwargs.get("intf")

        if not self.exists:
            raise FSResizeError("filesystem does not exist", self.device)

        if not self.resizable:
            raise FSResizeError("filesystem not resizable", self.device)

        if self.targetSize == self.currentSize:
            return

        if not self.resizefsProg:
            return

        if not os.path.exists(self.device):
            raise FSResizeError("device does not exist", self.device)

        self.doCheck(intf=intf)

        w = None
        if intf:
            w = intf.progressWindow(_("Resizing"),
                                    _("Resizing filesystem on %s...")
                                    % (self.device,),
                                    100, pulse = True)

        try:
            rc = util.execWithPulseProgress(self.resizefsProg,
                                            self.resizeArgs,
                                            stdout="/dev/tty5",
                                            stderr="/dev/tty5",
                                            progress=w)
        except Exception as e:
            raise FSResizeError(e, self.device)
        finally:
            if w:
                w.pop()

        if rc:
            raise FSResizeError("resize failed: %s" % rc, self.device)

        # XXX must be a smarter way to do this
        self._size = self.targetSize
        self.notifyKernel()

    def _getCheckArgs(self):
        argv = []
        argv.extend(self.defaultCheckOptions)
        argv.append(self.device)
        return argv

    def doCheck(self, intf=None):
        if not self.exists:
            raise FSError("filesystem has not been created")

        if not self.fsckProg:
            return

        if not os.path.exists(self.device):
            raise FSError("device does not exist")

        w = None
        if intf:
            w = intf.progressWindow(_("Checking"),
                                    _("Checking filesystem on %s...")
                                    % (self.device),
                                    100, pulse = True)

        try:
            rc = util.execWithPulseProgress(self.fsckProg,
                                            self._getCheckArgs(),
                                            stdout="/dev/tty5",
                                            stderr="/dev/tty5",
                                            progress = w)
        except Exception as e:
            raise FSError("filesystem check failed: %s" % e)
        finally:
            if w:
                w.pop()

        if rc >= 4:
            raise FSError("filesystem check failed: %s" % rc)

    def loadModule(self):
        """Load whatever kernel module is required to support this filesystem."""
        global kernel_filesystems

        if not self._modules or self.mountType in kernel_filesystems:
            return

        for module in self._modules:
            try:
                rc = util.execWithRedirect("modprobe", [module],
                                           stdout="/dev/tty5", stderr="/dev/tty5",
                                           searchPath=1)
            except Exception as e:
                self.installer.log.error("Could not load kernel module %s: %s" % (module, e))
                self._supported = False
                return

            if rc:
                self.installer.log.error("Could not load kernel module %s" % module)
                self._supported = False
                return

        # If we successfully loaded a kernel module, for this filesystem, we
        # also need to update the list of supported filesystems.
        kernel_filesystems = get_kernel_filesystems()

    def mount(self, *args, **kwargs):
        """ Mount this filesystem.

            Arguments:

                None

            Keyword Arguments:

                options -- mount options (overrides all other option strings)
                chroot -- prefix to apply to mountpoint
                mountpoint -- mountpoint (overrides self.mountpoint)
        """
        options = kwargs.get("options", "")
        chroot = kwargs.get("chroot", "/")
        mountpoint = kwargs.get("mountpoint")

        if not self.exists:
            raise FSError("filesystem has not been created")

        if not mountpoint:
            mountpoint = self.mountpoint

        if not mountpoint:
            raise FSError("no mountpoint given")

        if self.status:
            return

        if not isinstance(self, NoDevFS) and not os.path.exists(self.device):
            raise FSError("device %s does not exist" % self.device)

        # XXX os.path.join is FUBAR:
        #
        #         os.path.join("/mnt/foo", "/") -> "/"
        #
        #mountpoint = os.path.join(chroot, mountpoint)
        mountpoint = os.path.normpath("%s/%s" % (chroot, mountpoint))
        util.mkdirChain(mountpoint)

        # passed in options override default options
        if not options or not isinstance(options, str):
            options = self.options

        try:
            rc = isys.mount(self.device, mountpoint,
                            fstype=self.mountType,
                            options=options,
                            bindMount=isinstance(self, BindFS))
        except Exception as e:
            raise FSError("mount failed: %s" % e)

        if rc:
            raise FSError("mount failed: %s" % rc)

        self._mountpoint = mountpoint

    def unmount(self):
        """ Unmount this filesystem. """
        if not self.exists:
            raise FSError("filesystem has not been created")

        if not self._mountpoint:
            # not mounted
            return

        if not os.path.exists(self._mountpoint):
            raise FSError("mountpoint does not exist")

        rc = isys.umount(self._mountpoint, removeDir = False)
        if rc:
            raise FSError("umount failed")

        self._mountpoint = None

    def _getLabelArgs(self, label):
        argv = []
        argv.extend(self.defaultLabelOptions)
        argv.extend([self.device, label])
        return argv

    def writeLabel(self, label):
        """ Create a label for this filesystem. """
        if not self.exists:
            raise FSError("filesystem has not been created")

        if not self.labelfsProg:
            return

        if not os.path.exists(self.device):
            raise FSError("device does not exist")

        argv = self._getLabelArgs(label)
        rc = util.execWithRedirect(self.labelfsProg,
                                   argv,
                                   stderr="/dev/tty5",
                                   searchPath=1)
        if rc:
            raise FSError("label failed")

        self.label = label
        self.notifyKernel()

    @property
    def isDirty(self):
        return False

    @property
    def mkfsProg(self):
        """ Program used to create filesystems of this type. """
        return self._mkfs

    @property
    def fsckProg(self):
        """ Program used to check filesystems of this type. """
        return self._fsck

    @property
    def resizefsProg(self):
        """ Program used to resize filesystems of this type. """
        return self._resizefs

    @property
    def labelfsProg(self):
        """ Program used to manage labels for this filesystem type. """
        return self._labelfs

    @property
    def migratefsProg(self):
        """ Program used to migrate filesystems of this type. """
        return self._migratefs

    @property
    def migrationTarget(self):
        return self._migrationTarget

    @property
    def utilsAvailable(self):
        # we aren't checking for fsck because we shouldn't need it
        for prog in [self.mkfsProg, self.resizefsProg, self.labelfsProg]:
            if not prog:
                continue

            if not filter(lambda d: os.access("%s/%s" % (d, prog), os.X_OK),
                          os.environ["PATH"].split(":")):
                return False

        return True

    @property
    def supported(self):
        return self._supported and self.utilsAvailable

    @property
    def mountable(self):
        return (self.mountType in kernel_filesystems) or \
               (os.access("/sbin/mount.%s" % (self.mountType,), os.X_OK))

    @property
    def defaultFormatOptions(self):
        """ Default options passed to mkfs for this filesystem type. """
        # return a copy to prevent modification
        return self._defaultFormatOptions[:]

    @property
    def defaultMountOptions(self):
        """ Default options passed to mount for this filesystem type. """
        # return a copy to prevent modification
        return self._defaultMountOptions[:]

    @property
    def defaultLabelOptions(self):
        """ Default options passed to labeler for this filesystem type. """
        # return a copy to prevent modification
        return self._defaultLabelOptions[:]

    @property
    def defaultCheckOptions(self):
        """ Default options passed to checker for this filesystem type. """
        # return a copy to prevent modification
        return self._defaultCheckOptions[:]

    def _getOptions(self):
        options = ",".join(self.defaultMountOptions)
        if self.mountopts:
            # XXX should we clobber or append?
            options = self.mountopts
        return options

    def _setOptions(self, options):
        self.mountopts = options

    options = property(_getOptions, _setOptions)

    @property
    def migratable(self):
        """ Can filesystems of this type be migrated? """
        return bool(self._migratable and self.migratefsProg and
                    filter(lambda d: os.access("%s/%s"
                                               % (d, self.migratefsProg,),
                                               os.X_OK),
                           os.environ["PATH"].split(":")) and
                    self.migrationTarget)

    def _setMigrate(self, migrate):
        if not migrate:
            self._migrate = migrate
            return

        if self.migratable and self.exists:
            self._migrate = migrate
        else:
            raise ValueError("Cannot set migrate on non-migratable filesystem")

    migrate = property(lambda f: f._migrate, lambda f,m: f._setMigrate(m))

    @property
    def type(self):
        _type = self._type
        if self.migrate:
            _type = self.migrationTarget

        return _type

    @property
    def mountType(self):
        if not self._mountType:
            self._mountType = self._type

        return self._mountType

    # These methods just wrap filesystem-specific methods in more
    # generically named methods so filesystems and formatted devices
    # like swap and LVM physical volumes can have a common API.
    def create(self, *args, **kwargs):
        if self.exists:
            raise FSError("Filesystem already exists")

        DeviceFormat.create(self, *args, **kwargs)

        return self.doFormat(*args, **kwargs)

    def setup(self, *args, **kwargs):
        """ Mount the filesystem.

            THe filesystem will be mounted at the directory indicated by
            self.mountpoint.
        """
        return self.mount(**kwargs)

    def teardown(self, *args, **kwargs):
        return self.unmount(*args, **kwargs)

    @property
    def status(self):
        # FIXME check /proc/mounts or similar
        if not self.exists:
            return False
        return self._mountpoint is not None


class Ext2FS(FS):
    """ ext2 filesystem. """
    _type = "ext2"
    _mkfs = "mke2fs"
    _modules = ["ext2"]
    _resizefs = "resize2fs"
    _labelfs = "e2label"
    _fsck = "e2fsck"
    _formattable = True
    _supported = True
    _resizable = True
    _bootable = True
    _linuxNative = True
    _maxSize = 8 * 1024 * 1024
    _minSize = 0
    _defaultFormatOptions = []
    _defaultMountOptions = ["defaults"]
    _defaultCheckOptions = ["-f", "-p", "-C", "0"]
    _dump = True
    _check = True
    _migratable = True
    _migrationTarget = "ext3"
    _migratefs = "tune2fs"
    _defaultMigrateOptions = ["-j"]

    @property
    def minSize(self):
        """ Minimum size for this filesystem in MB. """
        size = self._minSize
        if self.exists and os.path.exists(self.device):
            buf = util.execWithCapture(self.resizefsProg,
                                        ["-P", self.device],
                                        stderr="/dev/tty5")
            size = None
            for line in buf.splitlines():
                if "minimum size of the filesystem:" not in line:
                    continue

                (text, sep, minSize) = line.partition(": ")

                size = int(minSize) / 1024.0

            if size is None:
                self.installer.log.warning("failed to get minimum size for %s filesystem "
                            "on %s" % (self.mountType, self.device))
                size = self._minSize

        return size

    @property
    def isDirty(self):
        return isys.ext2IsDirty(self.device)

    @property
    def resizeArgs(self):
        argv = ["-p", self.device, "%dM" % (self.targetSize,)]
        return argv

register_device_format(Ext2FS)


class Ext3FS(Ext2FS):
    """ ext3 filesystem. """
    _type = "ext3"
    _defaultFormatOptions = ["-t", "ext3"]
    _migrationTarget = "ext4"
    _modules = ["ext3"]
    _defaultMigrateOptions = ["-O", "extents"]

    @property
    def migratable(self):
        """ Can filesystems of this type be migrated? """
        return (flags.cmdline.has_key("ext4migrate") and
                Ext2FS.migratable)

register_device_format(Ext3FS)


class Ext4FS(Ext3FS):
    """ ext4 filesystem. """
    _type = "ext4"
    _bootable = False
    _defaultFormatOptions = ["-t", "ext4"]
    _migratable = False
    _modules = ["ext4"]

register_device_format(Ext4FS)


class FATFS(FS):
    """ FAT filesystem. """
    _type = "vfat"
    _mkfs = "mkdosfs"
    _modules = ["vfat"]
    _labelfs = "dosfslabel"
    _fsck = "dosfsck"
    _formattable = True
    _maxSize = 1024 * 1024
    _defaultMountOptions = ["umask=0077", "shortname=winnt"]

register_device_format(FATFS)


class BTRFS(FS):
    """ btrfs filesystem """
    _type = "btrfs"
    _mkfs = "mkfs.btrfs"
    _modules = ["btrfs"]
    _resizefs = "btrfsctl"
    _formattable = True
    _linuxNative = True
    _bootable = False
    _maxLabelChars = 256
    _supported = True
    _dump = True
    _check = True
    _maxSize = 16 * 1024 * 1024

    def _getFormatOptions(self, options=None):
        argv = []
        if options and isinstance(options, list):
            argv.extend(options)
        argv.extend(self.defaultFormatOptions)
        if self.label:
            argv.extend(["-L", self.label])
        argv.append(self.device)
        return argv

    @property
    def resizeArgs(self):
        argv = ["-r", "%dm" % (self.targetSize,), self.device]
        return argv

register_device_format(BTRFS)

class XFS(FS):
    """ XFS filesystem """
    _type = "xfs"
    _mkfs = "mkfs.xfs"
    _modules = ["xfs"]
    _labelfs = "xfs_admin"
    _defaultFormatOptions = ["-f"]
    _defaultLabelOptions = ["-L"]
    _maxLabelChars = 16
    _maxSize = 16 * 1024 * 1024
    _formattable = True
    _linuxNative = True
    _supported = True
    _dump = True
    _check = True

register_device_format(XFS)

class NTFS(FS):
    """ ntfs filesystem. """
    _type = "ntfs"
    _resizefs = "ntfsresize"
    _fsck = "ntfsresize"
    _resizable = True
    _minSize = 1
    _maxSize = 16 * 1024 * 1024
    _defaultMountOptions = ["defaults"]
    _defaultCheckOptions = ["-c"]

    @property
    def minSize(self):
        """ The minimum filesystem size in megabytes. """
        size = self._minSize
        if self.exists and os.path.exists(self.device):
            minSize = None
            buf = util.execWithCapture(self.resizefsProg,
                                       ["-m", self.device],
                                       stderr = "/dev/tty5")
            for l in buf.split("\n"):
                if not l.startswith("Minsize"):
                    continue
                try:
                    min = l.split(":")[1].strip()
                    minSize = int(min) + 250
                except Exception, e:
                    minSize = None
                    self.installer.log.warning("Unable to parse output for minimum size on %s: %s" %(self.device, e))

            if minSize is None:
                self.installer.log.warning("Unable to discover minimum size of filesystem "
                            "on %s" %(self.device,))
            else:
                size = minSize

        return size

    @property
    def resizeArgs(self):
        # You must supply at least two '-f' options to ntfsresize or
        # the proceed question will be presented to you.
        argv = ["-ff", "-s", "%dM" % (self.targetSize,), self.device]
        return argv

register_device_format(NTFS)


# if this isn't going to be mountable it might as well not be here
class NFS(FS):
    """ NFS filesystem. """
    _type = "nfs"
    _modules = ["nfs"]

    def _deviceCheck(self, devspec):
        if devspec is not None and ":" not in devspec:
            raise ValueError("device must be of the form <host>:<path>")

    @property
    def mountable(self):
        return False

    def _setDevice(self, devspec):
        self._deviceCheck(devspec)
        self._device = devspec

    def _getDevice(self):
        return self._device

    device = property(lambda f: f._getDevice(),
                      lambda f,d: f._setDevice(d),
                      doc="Full path the device this format occupies")

register_device_format(NFS)


class NFSv4(NFS):
    """ NFSv4 filesystem. """
    _type = "nfs4"
    _modules = ["nfs4"]

register_device_format(NFSv4)


class Iso9660FS(FS):
    """ ISO9660 filesystem. """
    _type = "iso9660"
    _formattable = False
    _supported = True
    _resizable = False
    _bootable = False
    _linuxNative = False
    _dump = False
    _check = False
    _migratable = False
    _defaultMountOptions = ["ro"]

register_device_format(Iso9660FS)


class NoDevFS(FS):
    """ nodev filesystem base class """
    _type = "nodev"

    def __init__(self, *args, **kwargs):
        FS.__init__(self, *args, **kwargs)
        self.exists = True
        self.device = self.type

    def _setDevice(self, devspec):
        self._device = devspec

register_device_format(NoDevFS)


class DevPtsFS(NoDevFS):
    """ devpts filesystem. """
    _type = "devpts"
    _defaultMountOptions = ["gid=5", "mode=620"]

register_device_format(DevPtsFS)


# these don't really need to be here
class ProcFS(NoDevFS):
    _type = "proc"

register_device_format(ProcFS)


class SysFS(NoDevFS):
    _type = "sysfs"

register_device_format(SysFS)


class TmpFS(NoDevFS):
    _type = "tmpfs"

register_device_format(TmpFS)


class BindFS(FS):
    _type = "bind"

    @property
    def mountable(self):
        return True

register_device_format(BindFS)
