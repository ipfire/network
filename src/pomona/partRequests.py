#
# partRequests.py: partition request objects and management thereof
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Harald Hoyer <harald@redhat.de>
#
# Copyright 2002-2005 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Partition request objects and management thereof."""

import parted
import inutil
import string
import os, sys, math

from constants import *

import fsset
import partedUtils
import partIntfHelpers

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

import logging
log = logging.getLogger("pomona")

class DeleteSpec:
    """Defines a preexisting partition which is intended to be removed."""
    def __init__(self, drive, start, end):
        """Initializes a DeleteSpec.

        drive is the text form of the drive
        start is the start sector of the deleted partition
        end is the end sector of the deleted partition
        """

        self.drive = drive
        self.start = start
        self.end = end

    def __str__(self):
        return "drive: %s  start: %s  end: %s" % (self.drive, self.start, self.end)

class RequestSpec:
    """Generic Request specification."""
    def __init__(self, fstype, size = None, mountpoint = None, format = None,
                 badblocks = None, preexist = 0, fslabel = None,
                 migrate = None, origfstype = None, bytesPerInode = 4096):
        """Create a generic RequestSpec.
        This should probably never be externally used.
        """

        self.fstype = fstype
        self.mountpoint = mountpoint
        self.size = size
        self.format = format
        self.badblocks = badblocks

        self.migrate = migrate
        self.origfstype = origfstype
        self.fslabel = fslabel
        self.fsopts = None

        if bytesPerInode == None:
            self.bytesPerInode = 4096
        else:
            self.bytesPerInode = bytesPerInode

        self.device = None
        """what we currently think the device is"""

        self.uniqueID = None
        """uniqueID is an integer and *MUST* be unique."""

        self.ignoreBootConstraints = 0
        """Booting constraints should be ignored for this request."""

        self.preexist = preexist
        """Did this partition exist before we started playing with things?"""

        self.protected = 0
        """Is this partitiion 'protected', ie does it contain install media."""

        self.dev = None
        """A Device() as defined in fsset.py to correspond to this request."""

    def __str__(self):
        if self.fstype:
            fsname = self.fstype.getName()
        else:
            fsname = "None"

        str = ("Generic Request -- mountpoint: %(mount)s  uniqueID: %(id)s\n"
               "  type: %(fstype)s  format: %(format)s  badblocks: %(bb)s\n"
               "  device: %(dev)s  migrate: %(migrate)s  fslabel: %(fslabel)s\n"
               "  bytesPerInode:  %(bytesPerInode)s  options: '%(fsopts)s'"
               % {"mount": self.mountpoint, "id": self.uniqueID,
                  "fstype": fsname, "format": self.format, "bb": self.badblocks,
                  "dev": self.device, "migrate": self.migrate,
                  "fslabel": self.fslabel, "bytesPerInode": self.bytesPerInode,
                  "fsopts": self.fsopts})
        return str

    def getActualSize(self, partitions, diskset):
        """Return the actual size allocated for the request in megabytes."""
        sys.stderr.write("WARNING: Abstract RequestSpec.getActualSize() called\n")

    def getDevice(self, partitions):
        """Return a device to solidify."""
        sys.stderr.write("WARNING: Abstract RequestSpec.getDevice() called\n")

    def toEntry(self, partitions):
        """Turn a request into a fsset entry and return the entry."""
        device = self.getDevice(partitions)

        # pin down our partitions so that we can reread the table
        device.solidify()

        if self.fstype.getName() == "swap":
            mountpoint = "swap"
        else:
            mountpoint = self.mountpoint

        entry = fsset.FileSystemSetEntry(device, mountpoint, self.fstype,
                                         origfsystem=self.origfstype,
                                         bytesPerInode=self.bytesPerInode,
                                         options=self.fsopts)
        if self.format:
            entry.setFormat(self.format)

        if self.migrate:
            entry.setMigrate(self.migrate)

        if self.badblocks:
            entry.setBadblocks(self.badblocks)

        if self.fslabel:
            entry.setLabel(self.fslabel)

        return entry

    def setProtected(self, val):
        """Set the protected value for this partition."""
        self.protected = val

    def getProtected(self):
        """Return the protected value for this partition."""
        return self.protected

    def getPreExisting(self):
        """Return whether the partition existed before we started playing."""
        return self.preexist

    def doMountPointLinuxFSChecks(self):
        """Return an error string if the mountpoint is not valid for Linux FS."""
        mustbeonroot = ('/bin','/dev','/sbin','/etc','/lib','/root',
                        '/mnt', 'lost+found', '/proc')
        mustbeonlinuxfs = ('/', '/boot', '/var', '/tmp', '/usr', '/home',
                           '/usr/share', '/usr/lib' )

        # these are symlinks so you cant make them mount points
        otherexcept = ('/var/mail', '/usr/tmp')

        if not self.mountpoint:
            return None

        if self.fstype is None:
            return None

        if self.fstype.isMountable():
            if self.mountpoint in mustbeonroot:
                return _("This mount point is invalid. The %s directory must "
                         "be on the / file system.") % (self.mountpoint,)
            elif self.mountpoint in otherexcept:
                return _("The mount point %s cannot be used.  It must "
                         "be a symbolic link for proper system "
                         "operation.  Please select a different "
                         "mount point.") % (self.mountpoint,)

            if not self.fstype.isLinuxNativeFS():
                if self.mountpoint in mustbeonlinuxfs:
                    return _("This mount point must be on a linux file system.")

        return None

    # requestSkipList is a list of uids for requests to ignore when
    # looking for a conflict on the mount point name.  Used in lvm
    # editting code in disk druid, for example.
    def isMountPointInUse(self, partitions, requestSkipList=None):
        """Return whether my mountpoint is in use by another request."""
        mntpt = self.mountpoint
        if not mntpt:
            return None

        if partitions and partitions.requests:
            for request in partitions.requests:
                if requestSkipList is not None and request.uniqueID in requestSkipList:
                    continue

                if request.mountpoint == mntpt:
                    if (not self.uniqueID or request.uniqueID != self.uniqueID):
                        return _("The mount point \"%s\" is already in use, "
                                 "please choose a different mount point."
                               % (mntpt))
        return None

    def doSizeSanityCheck(self):
        """Sanity check that the size of the request is sane."""
        if not self.fstype:
            return None

        if not self.format:
            return None

        if self.size and self.size > self.fstype.getMaxSizeMB():
            return (_("The size of the %s partition (%10.2f MB) "
                      "exceeds the maximum size of %10.2f MB.")
                    % (self.fstype.getName(), self.size,
                       self.fstype.getMaxSizeMB()))
        return None

    # set skipMntPtExistCheck to non-zero if you want to handle this
    # check yourself. Used in lvm volume group editting code, for example.
    def sanityCheckRequest(self, partitions, skipMntPtExistCheck=0):
        """Run the basic sanity checks on the request."""
        # see if mount point is valid if its a new partition request
        mntpt = self.mountpoint
        fstype = self.fstype
        preexist = self.preexist
        format = self.format

        rc = self.doSizeSanityCheck()
        if rc:
            return rc

        rc = partIntfHelpers.sanityCheckMountPoint(mntpt, fstype, preexist, format)
        if rc:
            return rc

        if not skipMntPtExistCheck:
            rc = self.isMountPointInUse(partitions)
            if rc:
                return rc

        rc = self.doMountPointLinuxFSChecks()
        if rc:
            return rc

        return None

    def formatByDefault(self):
        """Return whether or not the request should be formatted by default."""
        def inExceptionList(mntpt):
            exceptlist = [ '/home' ]
            for q in exceptlist:
                if os.path.commonprefix([mntpt, q]) == q:
                    return 1
            return 0

        # check first to see if its a Linux filesystem or not
        formatlist = ['/boot', '/var', '/tmp', '/usr']

        if not self.fstype:
            return 0

        if not self.fstype.isLinuxNativeFS():
            return 0

        if self.fstype.isMountable():
            mntpt = self.mountpoint
            if mntpt == "/":
                return 1

            if mntpt in formatlist:
                return 1

            for p in formatlist:
                if os.path.commonprefix([mntpt, p]) == p:
                    if inExceptionList(mntpt):
                        return 0
                    else:
                        return 1
        else:
            if self.fstype.getName() == "swap":
                return 1

        # be safe for anything else and default to off
        return 0


# XXX preexistings store start/end as sectors, new store as cylinders. ICK
class PartitionSpec(RequestSpec):
    """Object to define a requested partition."""

    def __init__(self, fstype, size = None, mountpoint = None,
                 preexist = 0, migrate = None, grow = 0, maxSizeMB = None,
                 start = None, end = None, drive = None, primary = None,
                 format = None, multidrive = None, bytesPerInode = 4096,
                 fslabel = None):
        """Create a new PartitionSpec object.

        fstype is the fsset filesystem type.
        size is the requested size (in megabytes).
        mountpoint is the mountpoint.
        grow is whether or not the partition is growable.
        maxSizeMB is the maximum size of the partition in megabytes.
        start is the starting cylinder/sector (new/preexist).
        end is the ending cylinder/sector (new/preexist).
        drive is the drive the partition goes on.
        primary is whether or not the partition should be forced as primary.
        format is whether or not the partition should be formatted.
        preexist is whether this partition is preexisting.
        migrate is whether or not the partition should be migrated.
        multidrive specifies if this is a request that should be replicated
            across _all_ of the drives in drive
        bytesPerInode is the size of the inodes on the filesystem.
        fslabel is the label to give to the filesystem.
        """

        # if it's preexisting, the original fstype should be set
        if preexist == 1:
            origfs = fstype
        else:
            origfs = None

        RequestSpec.__init__(self, fstype = fstype, size = size,
                             mountpoint = mountpoint, format = format,
                             preexist = preexist, migrate = None,
                             origfstype = origfs, bytesPerInode = bytesPerInode,
                             fslabel = fslabel)
        self.type = REQUEST_NEW

        self.grow = grow
        self.maxSizeMB = maxSizeMB
        self.requestSize = size
        self.start = start
        self.end = end

        self.drive = drive
        self.primary = primary
        self.multidrive = multidrive

        # should be able to map this from the device =\
        self.currentDrive = None
        """Drive that this request will currently end up on."""

    def __str__(self):
        if self.fstype:
            fsname = self.fstype.getName()
        else:
            fsname = "None"

        if self.origfstype:
            oldfs = self.origfstype.getName()
        else:
            oldfs = "None"

        if self.preexist == 0:
            pre = "New"
        else:
            pre = "Existing"

        str = ("%(n)s Part Request -- mountpoint: %(mount)s uniqueID: %(id)s\n"
               "  type: %(fstype)s  format: %(format)s  badblocks: %(bb)s\n"
               "  device: %(dev)s drive: %(drive)s  primary: %(primary)s\n"
               "  size: %(size)s  grow: %(grow)s  maxsize: %(max)s\n"
               "  start: %(start)s  end: %(end)s  migrate: %(migrate)s  "
               "  fslabel: %(fslabel)s  origfstype: %(origfs)s\n"
               "  bytesPerInode: %(bytesPerInode)s  options: '%(fsopts)s'"
               % {"n": pre, "mount": self.mountpoint, "id": self.uniqueID,
                  "fstype": fsname, "format": self.format, "dev": self.device,
                  "drive": self.drive, "primary": self.primary,
                  "size": self.size, "grow": self.grow, "max": self.maxSizeMB,
                  "start": self.start, "end": self.end, "bb": self.badblocks,
                  "migrate": self.migrate, "fslabel": self.fslabel,
                  "origfs": oldfs, "bytesPerInode": self.bytesPerInode,
                  "fsopts": self.fsopts})
        return str


    def getDevice(self, partitions):
        """Return a device to solidify."""
        self.dev = fsset.PartitionDevice(self.device)
        return self.dev

    def getActualSize(self, partitions, diskset):
        """Return the actual size allocated for the request in megabytes."""
        part = partedUtils.get_partition_by_name(diskset.disks, self.device)
        if not part:
            raise RuntimeError, "Checking the size of a partition which hasn't been allocated yet"
        return partedUtils.getPartSizeMB(part)

    def doSizeSanityCheck(self):
        """Sanity check that the size of the partition is sane."""
        if not self.fstype:
            return None
        if not self.format:
            return None
        ret = RequestSpec.doSizeSanityCheck(self)
        if ret is not None:
            return ret

        if (self.size and self.maxSizeMB and (self.size > self.maxSizeMB)):
            return (_("The size of the requested partition (size = %s MB) "
                      "exceeds the maximum size of %s MB.")
                    % (self.size, self.maxSizeMB))

        if self.size and self.size < 0:
            return _("The size of the requested partition is "
                     "negative! (size = %s MB)") % (self.size)

        if self.start and self.start < 1:
            return _("Partitions can't start below the first cylinder.")

        if self.end and self.end < 1:
            return _("Partitions can't end on a negative cylinder.")

        return None

class NewPartitionSpec(PartitionSpec):
    """Object to define a NEW requested partition."""

    def __init__(self, fstype, size = None, mountpoint = None,
                 grow = 0, maxSizeMB = None,
                 start = None, end = None,
                 drive = None, primary = None, format = None):
        """Create a new NewPartitionSpec object.

        fstype is the fsset filesystem type.
        size is the requested size (in megabytes).
        mountpoint is the mountpoint.
        grow is whether or not the partition is growable.
        maxSizeMB is the maximum size of the partition in megabytes.
        start is the starting cylinder.
        end is the ending cylinder.
        drive is the drive the partition goes on.
        primary is whether or not the partition should be forced as primary.
        format is whether or not the partition should be formatted.
        """

        PartitionSpec.__init__(self, fstype = fstype, size = size,
                               mountpoint = mountpoint, grow = grow,
                               maxSizeMB = maxSizeMB, start = start,
                               end = end, drive = drive, primary = primary,
                               format = format, preexist = 0)
        self.type = REQUEST_NEW

class PreexistingPartitionSpec(PartitionSpec):
    """Request to represent partitions which already existed."""

    def __init__(self, fstype, size = None, start = None, end = None,
                 drive = None, format = None, migrate = None,
                 mountpoint = None):
        """Create a new PreexistingPartitionSpec object.

        fstype is the fsset filesystem type.
        size is the size (in megabytes).
        start is the starting sector.
        end is the ending sector.
        drive is the drive which the partition is on.
        format is whether or not the partition should be formatted.
        migrate is whether or not the partition fs should be migrated.
        mountpoint is the mountpoint.
        """

        PartitionSpec.__init__(self, fstype = fstype, size = size,
                               start = start, end = end, drive = drive,
                               format = format, migrate = migrate,
                               mountpoint = mountpoint, preexist = 1)
        self.type = REQUEST_PREEXIST
