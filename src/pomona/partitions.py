#
# partitions.py: partition object containing partitioning info
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Harald Hoyer <harald@redhat.de>
#
# Copyright 2002-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
"""Overarching partition object."""

import parted
import inutil
import isys
import string
import os, sys

from constants import *

import fsset
import partedUtils
import partRequests

import pyfire
from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

class Partitions:
    """Defines all of the partition requests and delete requests."""
    def __init__ (self, diskset = None):
        """Initializes a Partitions object.

        Can pass in the diskset if it already exists.
        """
        self.requests = []
        """A list of RequestSpec objects for all partitions."""

        self.deletes = []
        """A list of DeleteSpec objects for partitions to be deleted."""

        self.autoPartitionRequests = []
        """A list of RequestSpec objects for autopartitioning.
        These are setup by the installclass and folded into self.requests
        by auto partitioning."""

        self.autoClearPartType = CLEARPART_TYPE_ALL
        """What type of partitions should be cleared?"""

        self.autoClearPartDrives = None
        """Drives to clear partitions on (note that None is equiv to all)."""

        self.nextUniqueID = 1
        """Internal counter.  Don't touch unless you're smarter than me."""

        self.reinitializeDisks = 0
        """Should the disk label be reset on all disks?"""

        self.zeroMbr = 0
        """Should the mbr be zero'd?"""

        # partition method to be used.  not to be touched externally
        self.useAutopartitioning = 1
        self.useFdisk = 0

        if diskset:
            diskset.refreshDevices()
            self.setFromDisk(diskset)

    def setFromDisk(self, diskset):
        """Clear the delete list and set self.requests to reflect disk."""
        self.deletes = []
        self.requests = []
        labels = diskset.getLabels()
        drives = diskset.disks.keys()
        drives.sort()
        for drive in drives:
            disk = diskset.disks[drive]
            part = disk.next_partition()
            while part:
                if part.type & parted.PARTITION_METADATA:
                    part = disk.next_partition(part)
                    continue

                format = None
                if part.type & parted.PARTITION_FREESPACE:
                    ptype = None
                elif part.type & parted.PARTITION_EXTENDED:
                    ptype = None
                elif part.get_flag(parted.PARTITION_RAID) == 1:
                    ptype = fsset.fileSystemTypeGet("software RAID")
                elif part.get_flag(parted.PARTITION_LVM) == 1:
                    ptype = fsset.fileSystemTypeGet("physical volume (LVM)")
                else:
                    ptype = partedUtils.get_partition_file_system_type(part)

                # XXX FIXME: we don't handle ptype being None very well, so
                # just say it's foreign.  Should probably fix None
                # handling instead some day.
                if ptype is None:
                    ptype = fsset.fileSystemTypeGet("foreign")

                start = part.geom.start
                end = part.geom.end
                size = partedUtils.getPartSizeMB(part)
                drive = partedUtils.get_partition_drive(part)

                spec = partRequests.PreexistingPartitionSpec(ptype,
                                                             size = size,
                                                             start = start,
                                                             end = end,
                                                             drive = drive,
                                                             format = format)
                spec.device = fsset.PartedPartitionDevice(part).getDevice()

                # set label if makes sense
                if ptype and ptype.isMountable() and \
                                (ptype.getName() == "ext2" or ptype.getName() == "ext3"):
                    if spec.device in labels.keys():
                        if labels[spec.device] and len(labels[spec.device])>0:
                            spec.fslabel = labels[spec.device]

                self.addRequest(spec)
                part = disk.next_partition(part)

    def addRequest(self, request):
        """Add a new request to the list."""
        if not request.uniqueID:
            request.uniqueID = self.nextUniqueID
            self.nextUniqueID = self.nextUniqueID + 1
        self.requests.append(request)
        self.requests.sort()

        return request.uniqueID

    def addDelete(self, delete):
        """Add a new DeleteSpec to the list."""
        self.deletes.append(delete)
        self.deletes.sort()

    def removeRequest(self, request):
        """Remove a request from the list."""
        self.requests.remove(request)

    def getRequestByMountPoint(self, mount):
        """Find and return the request with the given mountpoint."""
        for request in self.requests:
            if request.mountpoint == mount:
                return request

        return None

    def getRequestByDeviceName(self, device):
        """Find and return the request with the given device name."""
        if device is None:
            return None

        for request in self.requests:
            if request.device == device:
                return request

        return None

    def getRequestsByDevice(self, diskset, device):
        """Find and return the requests on a given device (like 'hda')."""
        if device is None:
            return None

        drives = diskset.disks.keys()
        if device not in drives:
            return None

        rc = []
        disk = diskset.disks[device]
        part = disk.next_partition()
        while part:
            dev = partedUtils.get_partition_name(part)
            request = self.getRequestByDeviceName(dev)

            if request:
                rc.append(request)
            part = disk.next_partition(part)

        if len(rc) > 0:
            return rc
        else:
            return None

    def getRequestByID(self, id):
        """Find and return the request with the given unique ID.

        Note that if id is a string, it will be converted to an int for you.
        """
        if type(id) == type("a string"):
            id = int(id)
            for request in self.requests:
                if request.uniqueID == id:
                    return request
        else: ### XXX debug
            log.debug("%s is not a string!" % (id,))
        return None

    def getBootableRequest(self):
        """Return the name of the current 'boot' mount point."""
        bootreq = None

        bootreq = self.getRequestByMountPoint("/boot")

        if not bootreq:
            bootreq = self.getRequestByMountPoint("/")

        if bootreq:
            return [ bootreq ]
        return None

    def getBootableMountpoints(self):
        """Return a list of bootable valid mountpoints for this arch."""
        # FIXME: should be somewhere else, preferably some sort of arch object
        return [ "/boot", "/" ]

    def isBootable(self, request):
        """Returns if the request should be considered a 'bootable' request.

        This basically means that it should be sorted to the beginning of
        the drive to avoid cylinder problems in most cases.
        """
        bootreqs = self.getBootableRequest()
        if not bootreqs:
            return 0

        for bootreq in bootreqs:
            if bootreq == request:
                return 1

        return 0

    def sortRequests(self):
        """Resort the requests into allocation order."""
        n = 0
        while n < len(self.requests):
            for request in self.requests:
  # for sized requests, we want the larger ones first
                if (request.size and self.requests[n].size and
                                (request.size < self.requests[n].size)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp
  # for cylinder-based, sort by order on the drive
                elif (request.start and self.requests[n].start and
                                (request.drive == self.requests[n].drive) and
                                (request.type == self.requests[n].type) and
                                (request.start > self.requests[n].start)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp
                # finally just use when they defined the partition so
                # there's no randomness thrown in
                elif (request.size and self.requests[n].size and
                                (request.size == self.requests[n].size) and
                                (request.uniqueID < self.requests[n].uniqueID)):
                    tmp = self.requests[n]
                    index = self.requests.index(request)
                    self.requests[n] = request
                    self.requests[index] = tmp

            n = n + 1

        tmp = self.getBootableRequest()

        boot = []
        if tmp:
            for req in tmp:
                boot.append(req)

        # remove the bootables from the request
        for bootable in boot:
            self.requests.pop(self.requests.index(bootable))

        # move to the front of the list
        boot.extend(self.requests)
        self.requests = boot

    def sanityCheckAllRequests(self, diskset, baseChecks = 0):
        """Do a sanity check of all of the requests.

        This function is called at the end of partitioning so that we
        can make sure you don't have anything silly (like no /, a really
        small /, etc).  Returns (errors, warnings) where each is a list
        of strings or None if there are none.
        If baseChecks is set, the basic sanity tests which the UI runs prior to
        accepting a partition will be run on the requests as well.
        """
        checkSizes = [('/usr', 250), ('/tmp', 50), ('/var', 384),
                      ('/home', 100), ('/boot', 75)]
        warnings = []
        errors = []

        slash = self.getRequestByMountPoint('/')
        if not slash:
            errors.append(_("You have not defined a root partition (/), "
                            "which is required for installation of %s "
                            "to continue.") % (name,))

        if slash and slash.getActualSize(self, diskset) < 250:
            warnings.append(_("Your root partition is less than 250 "
                              "megabytes which is usually too small to "
                              "install %s.") % (name,))

        bootreqs = self.getBootableRequest() or []
        # FIXME: missing a check to ensure this is gpt.
        for br in bootreqs:
            dev = br.device
            # simplified getDiskPart() for sata only
            if dev[-2] in string.digits:
                num = dev[-2:]
            elif dev[-1] in string.digits:
                num = dev[-1]
            else:
                continue # we should never get here, but you never know...
            if int(num) > 4:
                print dev, num
                errors.append(_("Your boot partition isn't on one of "
                                "the first four partitions and thus "
                                "won't be bootable."))

        for (mount, size) in checkSizes:
            req = self.getRequestByMountPoint(mount)
            if not req:
                continue
            if req.getActualSize(self, diskset) < size:
                warnings.append(_("Your %s partition is less than %s "
                                  "megabytes which is lower than recommended "
                                  "for a normal %s install.")
                                % (mount, size, name))

        foundSwap = 0
        swapSize = 0
        usesUSB = False
        usesFireWire = False

        for request in self.requests:
            if request.fstype and request.fstype.getName() == "swap":
                foundSwap = foundSwap + 1
                swapSize = swapSize + request.getActualSize(self, diskset)
            if baseChecks:
                rc = request.doSizeSanityCheck()
                if rc:
                    warnings.append(rc)
                rc = request.doMountPointLinuxFSChecks()
                if rc:
                    errors.append(rc)
                if rc:
                    errors.append(rc)
                if not hasattr(request,'drive'):
                    continue
            for x in request.drive or []:
                if isys.driveUsesModule(x, ["usb-storage", "ub"]):
                    usesUSB = True
                elif isys.driveUsesModule(x, ["sbp2"]):
                    usesFireWire = True

        if usesUSB:
            warnings.append(_("Installing on a USB device.  This may "
                              "or may not produce a working system."))

        if usesFireWire:
            warnings.append(_("Installing on a FireWire device.  This may "
                              "or may not produce a working system."))

        bootreqs = self.getBootableRequest()
        if bootreqs:
            for bootreq in bootreqs:
                # XFS causes all kinds of disasters for being /boot.
                # disallow it. #138673 and others.
                if (bootreq and bootreq.fstype and
                                bootreq.fstype.getName() == "xfs"):
                    errors.append("Bootable partitions cannot be on an XFS filesystem.")

        if foundSwap == 0:
            warnings.append(_("You have not specified a swap partition.  "
                              "Although not strictly required in all cases, "
                              "it will significantly improve performance for "
                              "most installations."))

        # XXX number of swaps not exported from kernel and could change
        if foundSwap >= 32:
            warnings.append(_("You have specified more than 32 swap devices.  "
                              "The kernel for %s only supports 32 "
                              "swap devices.") % (name,))

        mem = inutil.memInstalled()
        rem = mem % 16384
        if rem:
            mem = mem + (16384 - rem)
        mem = mem / 1024

        if foundSwap and (swapSize < (mem - 8)) and (mem < 1024):
            warnings.append(_("You have allocated less swap space (%dM) than "
                              "available RAM (%dM) on your system.  This "
                              "could negatively impact performance.")
                            % (swapSize, mem))

        if warnings == []:
            warnings = None
        if errors == []:
            errors = None

        return (errors, warnings)

    def copy(self):
        """Deep copy the object."""
        new = Partitions()
        for request in self.requests:
            new.addRequest(request)
        for delete in self.deletes:
            new.addDelete(delete)
        new.autoPartitionRequests = self.autoPartitionRequests
        new.autoClearPartType = self.autoClearPartType
        new.autoClearPartDrives = self.autoClearPartDrives
        new.nextUniqueID = self.nextUniqueID
        new.useAutopartitioning = self.useAutopartitioning
        new.useFdisk = self.useFdisk
        new.reinitializeDisks = self.reinitializeDisks
        return new

    def getClearPart(self):
        """Get the kickstart directive related to the clearpart being used."""
        clearpartargs = []
        if self.autoClearPartType == CLEARPART_TYPE_ALL:
            clearpartargs.append('--all')
        else:
            return None

        if self.reinitializeDisks:
            clearpartargs.append('--initlabel')

        if self.autoClearPartDrives:
            drives = string.join(self.autoClearPartDrives, ',')
            clearpartargs.append('--drives=%s' % (drives))

        return "#clearpart %s\n" %(string.join(clearpartargs))

    def deleteAllLogicalPartitions(self, part):
        """Add delete specs for all logical partitions in part."""
        for partition in partedUtils.get_logical_partitions(part.disk):
            partName = partedUtils.get_partition_name(partition)
            request = self.getRequestByDeviceName(partName)
            self.removeRequest(request)
            if request.preexist:
                drive = partedUtils.get_partition_drive(partition)
                delete = partRequests.DeleteSpec(drive, partition.geom.start,
                                                 partition.geom.end)
                self.addDelete(delete)

    def containsImmutablePart(self, part):
        """Returns whether the partition contains parts we can't delete."""
        if not part or (type(part) == type(1)):
            return None

        if not part.type & parted.PARTITION_EXTENDED:
            return None

        disk = part.disk
        while part:
            if not part.is_active():
                part = disk.next_partition(part)
                continue

            device = partedUtils.get_partition_name(part)
            request = self.getRequestByDeviceName(device)

            if request:
                if request.getProtected():
                    return _("the partition in use by the installer.")

            part = disk.next_partition(part)

        return None
