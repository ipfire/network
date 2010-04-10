#/usr/bin/python

import copy
import math
import parted
import _ped

from errors import *
from formats import get_device_format_class, getFormat
from udev import *
from util import notify_kernel, numeric_type

def devicePathToName(devicePath):
    if devicePath.startswith("/dev/"):
        name = devicePath[5:]
    else:
        name = devicePath

    if name.startswith("mapper/"):
        name = name[7:]

    return name

class Device(object):
    """ A generic device.

        Device instances know which devices they depend upon (parents
        attribute). They do not know which devices depend upon them, but
        they do know whether or not they have any dependent devices
        (isleaf attribute).

        A Device's setup method should set up all parent devices as well
        as the device itself. It should not run the resident format's
        setup method.

            Which Device types rely on their parents' formats being active?
                DMCryptDevice

        A Device's teardown method should accept the keyword argument
        recursive, which takes a boolean value and indicates whether or
        not to recursively close parent devices.

        A Device's create method should create all parent devices as well
        as the device itself. It should also run the Device's setup method
        after creating the device. The create method should not create a
        device's resident format.

            Which device type rely on their parents' formats to be created
            before they can be created/assembled?
                VolumeGroup
                DMCryptDevice

        A Device's destroy method should destroy any resident format
        before destroying the device itself.

    """
    _type = "generic device"

    def __init__(self, installer, name, parents=None, description=''):
        """ Create a Device instance.

            Arguments:

                name -- the device name (generally a device node's basename)

            Keyword Arguments:

                parents -- a list of required Device instances
                description -- a string describing the device

        """
        self.installer = installer

        self._name = name
        if parents is None:
            parents = []
        elif not isinstance(parents, list):
            raise ValueError("parents must be a list of Device instances")
        self.parents = parents
        self.kids = 0
        self.description = description

        for parent in self.parents:
            parent.addChild()

    def __deepcopy__(self, memo):
        """ Create a deep copy of a Device instance.

            We can't do copy.deepcopy on parted objects, which is okay.
            For these parted objects, we just do a shallow copy.
        """
        new = self.__class__.__new__(self.__class__)
        memo[id(self)] = new
        shallow_copy_attrs = ('partedDisk', '_partedDevice',
                             '_partedPartition', '_origPartedDisk',
                             '_raidSet', 'installer', 'screen')
        for (attr, value) in self.__dict__.items():
            if attr in shallow_copy_attrs:
                setattr(new, attr, copy.copy(value))
            else:
                setattr(new, attr, copy.deepcopy(value, memo))

        return new

    def removeChild(self):
        self.kids -= 1

    def addChild(self):
        self.kids += 1

    def setup(self, intf=None):
        """ Open, or set up, a device. """
        raise NotImplementedError("setup method not defined for Device")

    def teardown(self, recursive=None):
        """ Close, or tear down, a device. """
        raise NotImplementedError("teardown method not defined for Device")

    def create(self, intf=None):
        """ Create the device. """
        raise NotImplementedError("create method not defined for Device")

    def destroy(self):
        """ Destroy the device. """
        raise NotImplementedError("destroy method not defined for Device")

    def setupParents(self):
        """ Run setup method of all parent devices. """
        for parent in self.parents:
            parent.setup()

    def teardownParents(self, recursive=None):
        """ Run teardown method of all parent devices. """
        for parent in self.parents:
            parent.teardown(recursive=recursive)

    def createParents(self):
        """ Run create method of all parent devices. """
        self.installer.log.info("NOTE: recursive device creation disabled")
        for parent in self.parents:
            if not parent.exists:
                raise DeviceError("parent device does not exist")
            #parent.create()

    def dependsOn(self, dep):
        """ Return True if this device depends on dep. """
        # XXX does a device depend on itself?
        if dep in self.parents:
            return True

        for parent in self.parents:
            if parent.dependsOn(dep):
                return True

        return False

    @property
    def status(self):
        """ This device's status.

            For now, this should return a boolean:
                True    the device is open and ready for use
                False   the device is not open
        """
        return False

    @property
    def name(self):
        """ This device's name. """
        return self._name

    @property
    def isleaf(self):
        """ True if this device has no children. """
        return self.kids == 0

    @property
    def typeDescription(self):
        """ String describing the device type. """
        return self._type

    @property
    def type(self):
        """ Device type. """
        return self._type

    @property
    def mediaPresent(self):
        return True


class StorageDevice(Device):
    """ A generic storage device.

        A fully qualified path to the device node can be obtained via the
        path attribute, although it is not guaranteed to be useful, or
        even present, unless the StorageDevice's setup method has been
        run.

        StorageDevice instances can optionally contain a filesystem,
        represented by an FS instance. A StorageDevice's create method
        should create a filesystem if one has been specified.
    """
    _type = "storage device"
    _devDir = "/dev"
    sysfsBlockDir = "class/block"
    _resizable = False

    def __init__(self, installer, device, format=None,
                 size=None, major=None, minor=None,
                 sysfsPath='', parents=None, exists=None):
        """ Create a StorageDevice instance.

            Arguments:

                device -- the device name (generally a device node's basename)

            Keyword Arguments:

                size -- the device's size (units/format TBD)
                major -- the device major
                minor -- the device minor
                sysfsPath -- sysfs device path
                format -- a DeviceFormat instance
                parents -- a list of required Device instances
                description -- a string describing the device

        """
        self.installer = installer

        # allow specification of individual parents
        if isinstance(parents, Device):
            parents = [parents]

        Device.__init__(self, installer, device, parents=parents)

        self.uuid = None
        self._format = None
        self._size = numeric_type(size)
        self.major = numeric_type(major)
        self.minor = numeric_type(minor)
        self.sysfsPath = sysfsPath
        self.exists = exists

        # this may be handy for disk, dmraid, mpath, mdraid
        self.diskLabel = None

        self.format = format
        self.fstabComment = ""
        self._targetSize = self._size

        self._partedDevice = None

    @property
    def partedDevice(self):
        if self.exists and self.status and not self._partedDevice:
            # We aren't guaranteed to be able to get a device.  In
            # particular, built-in USB flash readers show up as devices but
            # do not always have any media present, so parted won't be able
            # to find a device.
            try:
                self._partedDevice = parted.Device(path=self.path)
            except _ped.DeviceException:
                pass

        return self._partedDevice

    def _getTargetSize(self):
        return self._targetSize

    def _setTargetSize(self, newsize):
        self._targetSize = newsize

    targetSize = property(lambda s: s._getTargetSize(),
                          lambda s, v: s._setTargetSize(v),
                          doc="Target size of this device")

    @property
    def path(self):
        """ Device node representing this device. """
        return "%s/%s" % (self._devDir, self.name)

    def updateSysfsPath(self):
        """ Update this device's sysfs path. """
        sysfsName = self.name.replace("/", "!")
        path = os.path.join("/sys", self.sysfsBlockDir, sysfsName)
        self.sysfsPath = os.path.realpath(path)[4:]
        self.installer.log.debug("%s sysfsPath set to %s" % (self.name, self.sysfsPath))

    @property
    def formatArgs(self):
        """ Device-specific arguments to format creation program. """
        return []

    @property
    def resizable(self):
        """ Can this type of device be resized? """
        return self._resizable and self.exists

    def notifyKernel(self):
        """ Send a 'change' uevent to the kernel for this device. """
        if not self.exists:
            self.installer.log.debug("Not sending change uevent for non-existent device")
            return

        if not self.status:
            self.installer.log.debug("Not sending change uevent for inactive device")
            return

        path = os.path.normpath("/sys/%s" % self.sysfsPath)
        try:
            notify_kernel(path, action="change")
        except Exception, e:
            self.installer.log.warning("Failed to notify kernel of change: %s" % e)

    @property
    def fstabSpec(self):
        spec = self.path
        if self.format and self.format.uuid:
            spec = "UUID=%s" % self.format.uuid
        return spec

    def resize(self, intf=None):
        """ Resize the device.

            New size should already be set.
        """
        raise NotImplementedError("resize method not defined for StorageDevice")

    def setup(self, intf=None):
        """ Open, or set up, a device. """
        if not self.exists:
            raise DeviceError("device has not been created")

        self.setupParents()
        for parent in self.parents:
            parent.format.setup()

    def teardown(self, recursive=None):
        """ Close, or tear down, a device. """
        if not self.exists and not recursive:
            raise DeviceError("device has not been created")

        if self.status and self.format.exists:
            self.format.teardown()
            udev_settle(timeout=10)

        if recursive:
            self.teardownParents(recursive=recursive)

    def _getSize(self):
        """ Get the device's size in MB, accounting for pending changes. """
        if self.exists and not self.mediaPresent:
            return 0

        if self.exists and self.partedDevice:
            self._size = self.currentSize

        size = self._size
        if self.exists and self.resizable and self.targetSize != size:
            size = self.targetSize

        return size

    def _setSize(self, newsize):
        """ Set the device's size to a new value. """
        if newsize > self.maxSize:
            raise DeviceError("device cannot be larger than %s MB" %
                              (self.maxSize(),))
        self._size = newsize

    size = property(lambda x: x._getSize(),
                    lambda x, y: x._setSize(y),
                    doc="The device's size in MB, accounting for pending changes")

    @property
    def currentSize(self):
        """ The device's actual size. """
        size = 0
        if self.exists and self.partedDevice:
            size = self.partedDevice.getSize()
        elif self.exists:
            size = self._size
        return size

    @property
    def minSize(self):
        """ The minimum size this device can be. """
        if self.exists:
            self.setup()

        if self.format.minSize:
            return self.format.minSize
        else:
            return self.size

    @property
    def maxSize(self):
        """ The maximum size this device can be. """
        if self.format.maxSize > self.currentSize:
            return self.currentSize
        else:
            return self.format.maxSize

    @property
    def status(self):
        """ This device's status.

            For now, this should return a boolean:
                True    the device is open and ready for use
                False   the device is not open
        """
        if not self.exists:
            return False
        return os.access(self.path, os.W_OK)

    def _setFormat(self, format):
        """ Set the Device's format. """
        if not format:
            format = getFormat(None, installer=self.installer, device=self.path, exists=self.exists)
        if self._format and self._format.status:
            # FIXME: self.format.status doesn't mean much
            raise DeviceError("Cannot replace active format")

        self._format = format

    def _getFormat(self):
        return self._format

    format = property(lambda d: d._getFormat(),
                      lambda d,f: d._setFormat(f),
                      doc="The device's formatting.")

    def create(self, intf=None):
        """ Create the device. """
        if self.exists:
            raise DeviceError("device has already been created")

        self.createParents()
        self.setupParents()
        self.exists = True
        self.setup()

    def destroy(self):
        """ Destroy the device. """
        if not self.exists:
            raise DeviceError("device has not been created")

        if not self.isleaf:
            raise DeviceError("Cannot destroy non-leaf device")

        self.exists = False

    @property
    def removable(self):
        devpath = os.path.normpath("/sys/%s" % self.sysfsPath)
        remfile = os.path.normpath("%s/removable" % devpath)
        return (self.sysfsPath and os.path.exists(devpath) and
                os.access(remfile, os.R_OK) and
                open(remfile).readline().strip() == "1")

class DiskDevice(StorageDevice):
    """ A disk """
    _type = "disk"

    def __init__(self, installer, device, format=None,
                 size=None, major=None, minor=None, sysfsPath='', \
                 parents=None, initcb=None, initlabel=None):
        """ Create a DiskDevice instance.

            Arguments:

                device -- the device name (generally a device node's basename)

            Keyword Arguments:

                size -- the device's size (units/format TBD)
                major -- the device major
                minor -- the device minor
                sysfsPath -- sysfs device path
                format -- a DeviceFormat instance
                parents -- a list of required Device instances
                removable -- whether or not this is a removable device

                initcb -- the call back to be used when initiating disk.
                initlabel -- whether to start with a fresh disklabel


            DiskDevices always exist.
        """
        self.installer = installer
        StorageDevice.__init__(self, self.installer, device, format=format,
                                size=size, major=major, minor=minor, exists=True,
                               sysfsPath=sysfsPath, parents=parents)

        self.partedDisk = None

        if self.partedDevice:
            if initlabel:
                self.partedDisk = self.freshPartedDisk()
            else:
                try:
                    self.partedDisk = parted.Disk(device=self.partedDevice)
                except _ped.DiskLabelException:
                    # if we have a cb function use it. else an error.
                    if initcb is not None and initcb():
                        self.partedDisk = parted.freshDisk(device=self.partedDevice, \
                                ty = platform.getPlatform(None).diskType)
                    else:
                        raise DeviceUserDeniedFormatError("User prefered to not format.")

        # We save the actual state of the disk here. Before the first
        # modification (addPartition or removePartition) to the partition
        # table we reset self.partedPartition to this state so we can
        # perform the modifications one at a time.
        if self.partedDisk:
            self._origPartedDisk = self.partedDisk.duplicate()
        else:
            self._origPartedDisk = None

    def freshPartedDisk(self):
        labelType = platform.getPlatform(None).diskType
        return parted.freshDisk(device=self.partedDevice, ty=labelType)

    @property
    def mediaPresent(self):
        return self.partedDevice is not None

    @property
    def model(self):
        return getattr(self.partedDevice, "model", None)

    @property
    def size(self):
        """ The disk's size in MB """
        return super(DiskDevice, self).size
    #size = property(StorageDevice._getSize)

    def resetPartedDisk(self):
        """ Reset parted.Disk to reflect the actual layout of the disk. """
        self.partedDisk = self._origPartedDisk

    def removePartition(self, device):
        if not self.mediaPresent:
            raise DeviceError("Cannot remove partition from disk %s which has no media" % self.name)

        partition = self.partedDisk.getPartitionByPath(device.path)
        if partition:
            self.partedDisk.removePartition(partition)

    def addPartition(self, device):
        if not self.mediaPresent:
            raise DeviceError("cannot add partition to disk %s which has no media" % self.name)

        for part in self.partedDisk.partitions:
            self.installer.log.debug("Disk %s: partition %s has geom %s" % (self.name,
                                                             part.getDeviceNodeName(),
                                                             part.geometry))

        geometry = device.partedPartition.geometry
        constraint = parted.Constraint(exactGeom=geometry)
        partition = parted.Partition(disk=self.partedDisk,
                                     type=device.partedPartition.type,
                                     geometry=geometry)
        self.partedDisk.addPartition(partition, constraint=constraint)

    def probe(self):
        """ Probe for any missing information about this device.

            pyparted should be able to tell us anything we want to know.
            size, disklabel type, maybe even partition layout
        """
        if not self.diskLabel:
            self.installer.log.debug("Setting %s diskLabel to %s" % (self.name,
                                                      self.partedDisk.type))
            self.diskLabel = self.partedDisk.type

    def commit(self, intf=None):
        """ Commit changes to the device. """
        if not self.mediaPresent:
            raise DeviceError("cannot commit to disk %s which has no media" % self.name)

        self.setupParents()
        self.setup()

        # give committing 5 tries, failing that, raise an exception
        attempt = 1
        maxTries = 5
        keepTrying = True

        while keepTrying and (attempt <= maxTries):
            try:
                self.partedDisk.commit()
                keepTrying = False
            except parted.DiskException as msg:
                self.installer.log.warning(msg)
                attempt += 1

        if keepTrying:
            raise DeviceError("cannot commit to disk %s after %d attempts" % (self.name, maxTries,))

        # commit makes the kernel re-scan the partition table
        udev_settle()

    def destroy(self):
        """ Destroy the device. """
        if not self.mediaPresent:
            raise DeviceError("cannot destroy disk %s which has no media" % self.name)

        self.partedDisk.deleteAllPartitions()
        # this is perhaps a separate operation (wiping the disklabel)
        self.partedDisk.clobber()
        self.partedDisk.commit()
        self.teardown()

    def setup(self, intf=None):
        """ Open, or set up, a device. """
        if not os.path.exists(self.path):
            raise DeviceError("device does not exist")

class PartitionDevice(StorageDevice):
    """ A disk partition.

        On types and flags...

        We don't need to deal with numerical partition types at all. The
        only type we are concerned with is primary/logical/extended. Usage
        specification is accomplished through the use of flags, which we
        will set according to the partition's format.
    """
    _type = "partition"
    _resizable = True

    def __init__(self, installer, name, format=None,
                 size=None, grow=False, maxsize=None,
                 major=None, minor=None, bootable=None,
                 sysfsPath='', parents=None, exists=None,
                 partType=None, primary=False, weight=0):
        """ Create a PartitionDevice instance.

            Arguments:

                name -- the device name (generally a device node's basename)

            Keyword Arguments:

                exists -- indicates whether this is an existing device
                format -- the device's format (DeviceFormat instance)

                For existing partitions:

                    parents -- the disk that contains this partition
                    major -- the device major
                    minor -- the device minor
                    sysfsPath -- sysfs device path

                For new partitions:

                    partType -- primary,extended,&c (as parted constant)
                    grow -- whether or not to grow the partition
                    maxsize -- max size for growable partitions (in MB)
                    size -- the device's size (in MB)
                    bootable -- whether the partition is bootable
                    parents -- a list of potential containing disks
                    weight -- an initial sorting weight to assign
        """
        self.req_disks = []
        self.req_partType = None
        self.req_primary = None
        self.req_grow = None
        self.req_bootable = None
        self.req_size = 0
        self.req_base_size = 0
        self.req_max_size = 0
        self.req_base_weight = 0

        self._bootable = False

        StorageDevice.__init__(self, installer, name, format=format, size=size,
                               major=major, minor=minor, exists=exists,
                               sysfsPath=sysfsPath, parents=parents)

        if not exists:
            # this is a request, not a partition -- it has no parents
            self.req_disks = self.parents[:]
            for dev in self.parents:
                dev.removeChild()
            self.parents = []

        # FIXME: Validate partType, but only if this is a new partition
        #        Otherwise, overwrite it with the partition's type.
        self._partType = None
        self.partedFlags = {}
        self._partedPartition = None

        # FIXME: Validate size, but only if this is a new partition.
        #        For existing partitions we will get the size from
        #        parted.

        if self.exists:
            #self.partedPartition = parted.getPartitionByName(self.path)
            self._partedPartition = self.disk.partedDisk.getPartitionByPath(self.path)
            if not self._partedPartition:
                raise DeviceError("cannot find parted partition instance")

            # collect information about the partition from parted
            self.probe()
        else:
            # XXX It might be worthwhile to create a shit-simple
            #     PartitionRequest class and pass one to this constructor
            #     for new partitions.
            self.req_name = name
            self.req_partType = partType
            self.req_primary = primary
            self.req_max_size = numeric_type(maxsize)
            self.req_grow = grow
            self.req_bootable = bootable

            # req_size may be manipulated in the course of partitioning
            self.req_size = self._size

            # req_base_size will always remain constant
            self.req_base_size = self._size

            self.req_base_weight = weight

    def _setTargetSize(self, newsize):
        if newsize != self.currentSize:
            # change this partition's geometry in-memory so that other
            # partitioning operations can complete (e.g., autopart)
            self._targetSize = newsize
            disk = self.disk.partedDisk

            # resize the partition's geometry in memory
            (constraint, geometry) = self._computeResize(self.partedPartition)
            disk.setPartitionGeometry(partition=self.partedPartition,
                                      constraint=constraint,
                                      start=geometry.start, end=geometry.end)

    @property
    def path(self):
        """ Device node representing this device. """
        if not self.parents:
            # Bogus, but code in various places compares devices by path
            # So we must return something unique
            return self.name

        return "%s/%s" % (self.parents[0]._devDir, self.name)

    @property
    def partType(self):
        """ Get the partition's type (as parted constant). """
        try:
            ptype = self.partedPartition.type
        except AttributeError:
            ptype = self._partType

        if not self.exists and ptype is None:
            ptype = self.req_partType

        return ptype

    @property
    def isExtended(self):
        return self.partType & parted.PARTITION_EXTENDED

    @property
    def isLogical(self):
        return self.partType & parted.PARTITION_LOGICAL

    @property
    def isPrimary(self):
        return self.partType == parted.PARTITION_NORMAL

    @property
    def isProtected(self):
        return self.partType & parted.PARTITION_PROTECTED

    def _getPartedPartition(self):
        return self._partedPartition

    def _setPartedPartition(self, partition):
        """ Set this PartitionDevice's parted Partition instance. """
        if partition is None:
            path = None
        elif isinstance(partition, parted.Partition):
            path = partition.path
        else:
            raise ValueError("partition must be a parted.Partition instance")

        self._partedPartition = partition
        self.updateName()

    partedPartition = property(lambda d: d._getPartedPartition(),
                               lambda d,p: d._setPartedPartition(p))

    def _getWeight(self):
        return self.req_base_weight

    def _setWeight(self, weight):
        self.req_base_weight = weight

    weight = property(lambda d: d._getWeight(),
                      lambda d,w: d._setWeight(w))

    def updateSysfsPath(self):
        """ Update this device's sysfs path. """
        if not self.parents:
            self.sysfsPath = ''

        elif self.parents[0]._devDir == "/dev/mapper":
            dm_node = dm.dm_node_from_name(self.name)
            path = os.path.join("/sys", self.sysfsBlockDir, dm_node)
            self.sysfsPath = os.path.realpath(path)[4:]

        else:
            StorageDevice.updateSysfsPath(self)

    def updateName(self):
        if self.partedPartition is None:
            self._name = self.req_name
        else:
            self._name = \
                devicePathToName(self.partedPartition.getDeviceNodeName())

    def dependsOn(self, dep):
        """ Return True if this device depends on dep. """
        if isinstance(dep, PartitionDevice) and dep.isExtended and self.isLogical:
            return True

        return Device.dependsOn(self, dep)

    def _setFormat(self, format):
        """ Set the Device's format. """
        StorageDevice._setFormat(self, format)

    def _setBootable(self, bootable):
        """ Set the bootable flag for this partition. """
        if self.partedPartition:
            if self.flagAvailable(parted.PARTITION_BOOT):
                if bootable:
                    self.setFlag(parted.PARTITION_BOOT)
                else:
                    self.unsetFlag(parted.PARTITION_BOOT)
            else:
                raise DeviceError(_("boot flag not available for this "
                                    "partition"))

            self._bootable = bootable
        else:
            self.req_bootable = bootable

    def _getBootable(self):
        return self._bootable or self.req_bootable

    bootable = property(_getBootable, _setBootable)

    def flagAvailable(self, flag):
        if not self.partedPartition:
            return

        return self.partedPartition.isFlagAvailable(flag)

    def getFlag(self, flag):
        if not self.partedPartition or not self.flagAvailable(flag):
            return

        return self.partedPartition.getFlag(flag)

    def setFlag(self, flag):
        if not self.partedPartition or not self.flagAvailable(flag):
            return

        self.partedPartition.setFlag(flag)

    def unsetFlag(self, flag):
        if not self.partedPartition or not self.flagAvailable(flag):
            return

        self.partedPartition.unsetFlag(flag)

    def probe(self):
        """ Probe for any missing information about this device.

            size, partition type, flags
        """
        if not self.exists:
            return

        # this is in MB
        self._size = self.partedPartition.getSize()
        self.targetSize = self._size

        self._partType = self.partedPartition.type

        self._bootable = self.getFlag(parted.PARTITION_BOOT)

    def create(self, intf=None):
        """ Create the device. """
        if self.exists:
            raise DeviceError("device already exists")

        self.createParents()
        self.setupParents()

        self.disk.addPartition(self)
        self.disk.commit()

        self.partedPartition = self.disk.partedDisk.getPartitionByPath(self.path)

        self.exists = True
        self.setup()

    def _computeResize(self, partition):
        # compute new size for partition
        currentGeom = partition.geometry
        currentDev = currentGeom.device
        newLen = long(self.targetSize * 1024 * 1024) / currentDev.sectorSize
        newGeometry = parted.Geometry(device=currentDev,
                                      start=currentGeom.start,
                                      length=newLen)
        constraint = parted.Constraint(exactGeom=newGeometry)

        return (constraint, newGeometry)

    def resize(self, intf=None):
        """ Resize the device.

            self.targetSize must be set to the new size.
        """
        if self.targetSize != self.currentSize:
            # partedDisk has been restored to _origPartedDisk, so
            # recalculate resize geometry because we may have new
            # partitions on the disk, which could change constraints
            partition = self.disk.partedDisk.getPartitionByPath(self.path)
            (constraint, geometry) = self._computeResize(partition)

            self.disk.partedDisk.setPartitionGeometry(partition=partition,
                                                      constraint=constraint,
                                                      start=geometry.start,
                                                      end=geometry.end)

            self.disk.commit()
            self.notifyKernel()

    def destroy(self):
        """ Destroy the device. """
        if not self.exists:
            raise DeviceError("device has not been created")

        if not self.sysfsPath:
            return

        if not self.isleaf:
            raise DeviceError("Cannot destroy non-leaf device")

        self.setupParents()
        self.disk.removePartition(self)
        self.disk.commit()

        self.exists = False

    def _getSize(self):
        """ Get the device's size. """
        size = self._size
        if self.partedPartition:
            # this defaults to MB
            size = self.partedPartition.getSize()
        return size

    def _setSize(self, newsize):
        """ Set the device's size (for resize, not creation).

            Arguments:

                newsize -- the new size (in MB)

        """
        if not self.exists:
            raise DeviceError("device does not exist")

        if newsize > self.disk.size:
            raise ValueError("partition size would exceed disk size")

        # this defaults to MB
        maxAvailableSize = self.partedPartition.getMaxAvailableSize()

        if newsize > maxAvailableSize:
            raise ValueError("new size is greater than available space")

         # now convert the size to sectors and update the geometry
        geometry = self.partedPartition.geometry
        physicalSectorSize = geometry.device.physicalSectorSize

        new_length = (newsize * (1024 * 1024)) / physicalSectorSize
        geometry.length = new_length

    def _getDisk(self):
        """ The disk that contains this partition."""
        try:
            disk = self.parents[0]
        except IndexError:
            disk = None
        return disk

    def _setDisk(self, disk):
        """Change the parent.

        Setting up a disk is not trivial.  It has the potential to change
        the underlying object.  If necessary we must also change this object.
        """
        if self.disk:
            self.disk.removeChild()

        if disk:
            self.parents = [disk]
            disk.addChild()
        else:
            self.parents = []

    disk = property(lambda p: p._getDisk(), lambda p,d: p._setDisk(d))

    @property
    def maxSize(self):
        """ The maximum size this partition can be. """
        # XXX: this is MB by default
        maxPartSize = self.partedPartition.getMaxAvailableSize()

        if self.format.maxSize > maxPartSize:
            return maxPartSize
        else:
            return self.format.maxSize

class OpticalDevice(StorageDevice):
    """ An optical drive, eg: cdrom, dvd+r, &c.

        XXX Is this useful?
    """
    _type = "cdrom"

    def __init__(self, installer, name, major=None, minor=None, exists=None,
                 format=None, parents=None, sysfsPath=''):
        StorageDevice.__init__(self, installer, name, format=format,
                               major=major, minor=minor, exists=True,
                               parents=parents, sysfsPath=sysfsPath)

    @property
    def mediaPresent(self):
        """ Return a boolean indicating whether or not the device contains
            media.
        """
        if not self.exists:
            raise DeviceError("device has not been created", self.path)

        try:
            fd = os.open(self.path, os.O_RDONLY)
        except OSError as e:
            # errno 123 = No medium found
            if e.errno == 123:
                return False
            else:
                return True
        else:
            os.close(fd)
            return True

    def eject(self):
        """ Eject the drawer. """
        #import _isys

        if not self.exists:
            raise DeviceError("device has not been created", self.path)

        # Make a best effort attempt to do the eject.  If it fails, it's not
        # critical.
        fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

        #try:
        #    _isys.ejectcdrom(fd)
        #except SystemError as e:
        #    log.warning("error ejecting cdrom %s: %s" % (self.name, e))

        os.close(fd)

class DMDevice(StorageDevice):
    """ A device-mapper device """
    _type = "dm"
    _devDir = "/dev/mapper"

    def __init__(self, installer, name, format=None, size=None, dmUuid=None,
                 target=None, exists=None, parents=None, sysfsPath=''):
        """ Create a DMDevice instance.

            Arguments:

                name -- the device name (generally a device node's basename)

            Keyword Arguments:

                target -- the device-mapper target type (string)
                size -- the device's size (units/format TBD)
                dmUuid -- the device's device-mapper UUID
                sysfsPath -- sysfs device path
                format -- a DeviceFormat instance
                parents -- a list of required Device instances
                exists -- indicates whether this is an existing device
        """
        StorageDevice.__init__(self, installer, name, format=format, size=size,
                               exists=exists,
                               parents=parents, sysfsPath=sysfsPath)
        self.target = target
        self.dmUuid = dmUuid

    def __str__(self):
        s = StorageDevice.__str__(self)
        s += ("  target = %(target)s  dmUuid = %(dmUuid)s" %
              {"target": self.target, "dmUuid": self.dmUuid})
        return s

    @property
    def fstabSpec(self):
        """ Return the device specifier for use in /etc/fstab. """
        return self.path

    def updateSysfsPath(self):
        """ Update this device's sysfs path. """
        if not self.exists:
            raise DeviceError("device has not been created")

        if self.status:
            dm_node = self.getDMNode()
            path = os.path.join("/sys", self.sysfsBlockDir, dm_node)
            self.sysfsPath = os.path.realpath(path)[4:]
        else:
            self.sysfsPath = ''

    #def getTargetType(self):
    #    return dm.getDmTarget(name=self.name)

    def getDMNode(self):
        """ Return the dm-X (eg: dm-0) device node for this device. """
        if not self.exists:
            raise DeviceError("device has not been created")

        return dm.dm_node_from_name(self.name)

    def _setName(self, name):
        """ Set the device's map name. """
        if self.status:
            raise DeviceError("device is active")

        self._name = name
        #self.sysfsPath = "/dev/disk/by-id/dm-name-%s" % self.name

    name = property(lambda d: d._name,
                    lambda d,n: d._setName(n))


class LVMVolumeGroupDevice(DMDevice):
    """ An LVM Volume Group

        XXX Maybe this should inherit from StorageDevice instead of
            DMDevice since there's no actual device.
    """
    _type = "lvmvg"

    def __init__(self, installer, name, parents, size=None, free=None,
                 peSize=None, peCount=None, peFree=None, pvCount=None,
                 lvNames=[], uuid=None, exists=None, sysfsPath=''):
        """ Create a LVMVolumeGroupDevice instance.

            Arguments:

                name -- the device name (generally a device node's basename)
                parents -- a list of physical volumes (StorageDevice)

            Keyword Arguments:

                peSize -- physical extent size (in MB)
                exists -- indicates whether this is an existing device
                sysfsPath -- sysfs device path

                For existing VG's only:

                    size -- the VG's size (in MB)
                    free -- amount of free space in the VG
                    peFree -- number of free extents
                    peCount -- total number of extents
                    pvCount -- number of PVs in this VG
                    lvNames -- the names of this VG's LVs
                    uuid -- the VG's UUID

        """
        self.pvClass = get_device_format_class("lvmpv")
        if not self.pvClass:
            raise DeviceError("cannot find 'lvmpv' class")

        if isinstance(parents, list):
            for dev in parents:
                if not isinstance(dev.format, self.pvClass):
                    raise ValueError("constructor requires a list of PVs")
        elif not isinstance(parents.format, self.pvClass):
            raise ValueError("constructor requires a list of PVs")

        DMDevice.__init__(self, installer, name, parents=parents,
                          exists=exists, sysfsPath=sysfsPath)

        self.uuid = uuid
        self.free = numeric_type(free)
        self.peSize = numeric_type(peSize)
        self.peCount = numeric_type(peCount)
        self.peFree = numeric_type(peFree)
        self.pvCount = numeric_type(pvCount)
        self.lvNames = lvNames

        # circular references, here I come
        self._lvs = []

        # TODO: validate peSize if given
        if not self.peSize:
            self.peSize = 4.0   # MB

        #self.probe()

    def __str__(self):
        s = DMDevice.__str__(self)
        s += ("  free = %(free)s  PE Size = %(peSize)s  PE Count = %(peCount)s\n"
              "  PE Free = %(peFree)s  PV Count = %(pvCount)s\n"
              "  LV Names = %(lvNames)s  modified = %(modified)s\n"
              "  extents = %(extents)s  free space = %(freeSpace)s\n"
              "  free extents = %(freeExtents)s\n"
              "  PVs = %(pvs)s\n"
              "  LVs = %(lvs)s" %
              {"free": self.free, "peSize": self.peSize, "peCount": self.peCount,
               "peFree": self.peFree, "pvCount": self.pvCount,
               "lvNames": self.lvNames, "modified": self.isModified,
               "extents": self.extents, "freeSpace": self.freeSpace,
               "freeExtents": self.freeExtents, "pvs": self.pvs, "lvs": self.lvs})
        return s

    def probe(self):
        """ Probe for any information about this device. """
        if not self.exists:
            raise DeviceError("device has not been created")

    @property
    def status(self):
        """ The device's status (True means active). """
        if not self.exists:
            return False

        # certainly if any of this VG's LVs are active then so are we
        for lv in self.lvs:
            if lv.status:
                return True

        # if any of our PVs are not active then we cannot be
        for pv in self.pvs:
            if not pv.status:
                return False

        # if we are missing some of our PVs we cannot be active
        if len(self.pvs) != self.pvCount:
            return False

        return True

    def _addDevice(self, device):
        """ Add a new physical volume device to the volume group.

            XXX This is for use by device probing routines and is not
                intended for modification of the VG.
        """
        if not self.exists:
            raise DeviceError("device does not exist")

        if not isinstance(device.format, self.pvClass):
            raise ValueError("addDevice requires a PV arg")

        if self.uuid and device.format.vgUuid != self.uuid:
            raise ValueError("UUID mismatch")

        if device in self.pvs:
            raise ValueError("device is already a member of this VG")

        self.parents.append(device)
        device.addChild()

        # now see if the VG can be activated
        if len(self.parents) == self.pvCount:
            self.setup()

    def _removeDevice(self, device):
        """ Remove a physical volume from the volume group.

            This is for cases like clearing of preexisting partitions.
        """
        try:
            self.parents.remove(device)
        except ValueError, e:
            raise ValueError("cannot remove non-member PV device from VG")

        device.removeChild()

    def setup(self, intf=None):
        """ Open, or set up, a device.

            XXX we don't do anything like "vgchange -ay" because we don't
                want all of the LVs activated, just the VG itself.
        """
        if not self.exists:
            raise DeviceError("device has not been created")

        if self.status:
            return

        if len(self.parents) < self.pvCount:
            raise DeviceError("cannot activate VG with missing PV(s)")

        self.setupParents()

    def teardown(self, recursive=None):
        """ Close, or tear down, a device. """
        if not self.exists and not recursive:
            raise DeviceError("device has not been created")

        if self.status:
            lvm.vgdeactivate(self.name)

        if recursive:
            self.teardownParents(recursive=recursive)

    def create(self, intf=None):
        """ Create the device. """
        if self.exists:
            raise DeviceError("device already exists")

        pv_list = []
        #for pv in self.parents:
            # This is a little bit different from other devices in that
            # for VG we need the PVs to be formatted before we can create
            # the VG.
        #    pv.create()
        #    pv.format.create()
        #    pv_list.append(pv.path)
        pv_list = [pv.path for pv in self.parents]
        self.createParents()
        self.setupParents()
        lvm.vgcreate(self.name, pv_list, self.peSize)
        # FIXME set / update self.uuid here
        self.exists = True
        self.setup()

    def destroy(self):
        """ Destroy the device. """
        if not self.exists:
            raise DeviceError("device has not been created")

        # set up the pvs since lvm needs access to them to do the vgremove
        self.setupParents()

        # this sometimes fails for some reason.
        try:
            lvm.vgreduce(self.name, [], rm=True)
            lvm.vgremove(self.name)
        except lvm.LVMError:
            raise DeviceError("Could not completely remove VG %s" % self.name)
        finally:
            self.notifyKernel()
            self.exists = False

    def reduce(self, pv_list):
        """ Remove the listed PVs from the VG. """
        if not self.exists:
            raise DeviceError("device has not been created")

        lvm.vgreduce(self.name, pv_list)
        # XXX do we need to notify the kernel?

    def _addLogVol(self, lv):
        """ Add an LV to this VG. """
        if lv in self._lvs:
            raise ValueError("lv is already part of this vg")

        # verify we have the space, then add it
        # do not verify for growing vg (because of ks)
        if not lv.exists and \
           not [pv for pv in self.pvs if getattr(pv, "req_grow", None)] and \
           lv.size > self.freeSpace:
            raise DeviceError("new lv is too large to fit in free space")

        self._lvs.append(lv)

    def _removeLogVol(self, lv):
        """ Remove an LV from this VG. """
        if lv not in self.lvs:
            raise ValueError("specified lv is not part of this vg")

        self._lvs.remove(lv)

    def _addPV(self, pv):
        """ Add a PV to this VG. """
        if pv in self.pvs:
            raise ValueError("pv is already part of this vg")

        # for the time being we will not allow vgextend
        if self.exists:
            raise DeviceError("cannot add pv to existing vg")

        self.parents.append(pv)
        pv.addChild()

    def _removePV(self, pv):
        """ Remove an PV from this VG. """
        if not pv in self.pvs:
            raise ValueError("specified pv is not part of this vg")

        # for the time being we will not allow vgreduce
        if self.exists:
            raise DeviceError("cannot remove pv from existing vg")

        self.parents.remove(pv)
        pv.removeChild()

    # We can't rely on lvm to tell us about our size, free space, &c
    # since we could have modifications queued, unless the VG and all of
    # its PVs already exist.
    #
    #        -- liblvm may contain support for in-memory devices

    @property
    def isModified(self):
        """ Return True if the VG has changes queued that LVM is unaware of. """
        modified = True
        if self.exists and not filter(lambda d: not d.exists, self.pvs):
            modified = False

        return modified

    @property
    def size(self):
        """ The size of this VG """
        # TODO: just ask lvm if isModified returns False

        # sum up the sizes of the PVs and align to pesize
        size = 0
        for pv in self.pvs:
            size += max(0, self.align(pv.size - pv.format.peStart))

        return size

    @property
    def extents(self):
        """ Number of extents in this VG """
        # TODO: just ask lvm if isModified returns False

        return self.size / self.peSize

    @property
    def freeSpace(self):
        """ The amount of free space in this VG (in MB). """
        # TODO: just ask lvm if isModified returns False

        # total the sizes of any LVs
        used = 0
        size = self.size
        self.installer.log.debug("%s size is %dMB" % (self.name, size))
        for lv in self.lvs:
            self.installer.log.debug("lv %s (%s) uses %dMB" % (lv.name, lv, lv.size))
            used += self.align(lv.size, roundup=True)

        free = self.size - used
        self.installer.log.debug("vg %s has %dMB free" % (self.name, free))
        return free

    @property
    def freeExtents(self):
        """ The number of free extents in this VG. """
        # TODO: just ask lvm if isModified returns False
        return self.freeSpace / self.peSize

    def align(self, size, roundup=None):
        """ Align a size to a multiple of physical extent size. """
        size = numeric_type(size)

        if roundup:
            round = math.ceil
        else:
            round = math.floor

        # we want Kbytes as a float for our math
        size *= 1024.0
        pesize = self.peSize * 1024.0
        return long((round(size / pesize) * pesize) / 1024)

    @property
    def pvs(self):
        """ A list of this VG's PVs """
        return self.parents[:]  # we don't want folks changing our list

    @property
    def lvs(self):
        """ A list of this VG's LVs """
        return self._lvs[:]     # we don't want folks changing our list

    @property
    def complete(self):
        """Check if the vg has all its pvs in the system
        Return True if complete.
        """
        return len(self.pvs) == self.pvCount or not self.exists

class LVMLogicalVolumeDevice(DMDevice):
    """ An LVM Logical Volume """
    _type = "lvmlv"
    _resizable = True

    def __init__(self, installer, name, vgdev, size=None, uuid=None,
                 format=None, exists=None, sysfsPath='',
                 grow=None, maxsize=None, percent=None):
        """ Create a LVMLogicalVolumeDevice instance.

            Arguments:

                name -- the device name (generally a device node's basename)
                vgdev -- volume group (LVMVolumeGroupDevice instance)

            Keyword Arguments:

                size -- the device's size (in MB)
                uuid -- the device's UUID
                sysfsPath -- sysfs device path
                format -- a DeviceFormat instance
                exists -- indicates whether this is an existing device

                For new (non-existent) LVs only:

                    grow -- whether to grow this LV
                    maxsize -- maximum size for growable LV (in MB)
                    percent -- percent of VG space to take

        """
        if isinstance(vgdev, list):
            if len(vgdev) != 1:
                raise ValueError("constructor requires a single LVMVolumeGroupDevice instance")
            elif not isinstance(vgdev[0], LVMVolumeGroupDevice):
                raise ValueError("constructor requires a LVMVolumeGroupDevice instance")
        elif not isinstance(vgdev, LVMVolumeGroupDevice):
            raise ValueError("constructor requires a LVMVolumeGroupDevice instance")
        DMDevice.__init__(self, installer, name, size=size, format=format,
                          sysfsPath=sysfsPath, parents=vgdev,
                          exists=exists)

        self.uuid = uuid

        self.req_grow = None
        self.req_max_size = 0
        self.req_size = 0   
        self.req_percent = 0

        if not self.exists:
            self.req_grow = grow
            self.req_max_size = numeric_type(maxsize)
            # XXX should we enforce that req_size be pe-aligned?
            self.req_size = self._size
            self.req_percent = numeric_type(percent)

        # here we go with the circular references
        self.vg._addLogVol(self)

    def __str__(self):
        s = DMDevice.__str__(self)
        s += ("  VG device = %(vgdev)r  percent = %(percent)s" %
              {"vgdev": self.vg, "percent": self.req_percent})
        return s

    def _setSize(self, size):
        size = self.vg.align(numeric_type(size))
        self.installer.log.debug("Trying to set lv %s size to %dMB" % (self.name, size))
        if size <= (self.vg.freeSpace + self._size):
            self._size = size
            self.targetSize = size
        else:
            self.installer.log.debug("Failed to set size: %dMB short" % (size - (self.vg.freeSpace + self._size),))
            raise ValueError("Not enough free space in volume group")

    size = property(StorageDevice._getSize, _setSize)

    @property
    def vg(self):
        """ This Logical Volume's Volume Group. """
        return self.parents[0]

    @property
    def path(self):
        """ Device node representing this device. """
        # Thank you lvm for this lovely hack.
        return "%s/%s-%s" % (self._devDir, self.vg.name.replace("-","--"),
                self._name.replace("-","--"))

    def getDMNode(self):
        """ Return the dm-X (eg: dm-0) device node for this device. """
        # Thank you lvm for this lovely hack.
        if not self.exists:
            raise DeviceError("Device has not been created", self.path)

        return dm.dm_node_from_name("%s-%s" % (self.vg.name.replace("-","--"), \
                self._name.replace("-","--")))

    @property
    def name(self):
        """ This device's name. """
        return "%s-%s" % (self.vg.name, self._name)

    @property
    def lvname(self):
        """ The LV's name (not including VG name). """
        return self._name

    @property
    def complete(self):
        """ Test if vg exits and if it has all pvs. """
        return self.vg.complete

    def setup(self, intf=None):
        """ Open, or set up, a device. """
        if not self.exists:
            raise DeviceError("Device has not been created", self.path)

        if self.status:
            return

        self.vg.setup()
        lvm.lvactivate(self.vg.name, self._name)

        # we always probe since the device may not be set up when we want
        # information about it
        self._size = self.currentSize

    def teardown(self, recursive=None):
        """ Close, or tear down, a device. """
        if not self.exists and not recursive:
            raise DeviceError("Device has not been created", self.path)

        if self.status and self.format.exists:
            self.format.teardown()
            udev_settle(timeout=10)

        if self.status:
            lvm.lvdeactivate(self.vg.name, self._name)

        if recursive:
            # It's likely that teardown of a VG will fail due to other
            # LVs being active (filesystems mounted, &c), so don't let
            # it bring everything down.
            try:
                self.vg.teardown(recursive=recursive)
            except Exception as e:
                log.debug("vg %s teardown failed; continuing" % self.vg.name)

    def create(self, intf=None):
        """ Create the device. """
        if self.exists:
            raise DeviceError("Device already exists", self.path)

        self.createParents()
        self.setupParents()

        # should we use --zero for safety's sake?
        lvm.lvcreate(self.vg.name, self._name, self.size)
        # FIXME set / update self.uuid here
        self.exists = True
        self.setup()

    def destroy(self):
        """ Destroy the device. """
        if not self.exists:
            raise DeviceError("Device has not been created", self.path)

        self.teardown()
        # set up the vg's pvs so lvm can remove the lv
        self.vg.setupParents()
        lvm.lvremove(self.vg.name, self._name)
        self.exists = False

    def resize(self, intf=None):
        # XXX resize format probably, right?
        if not self.exists:
            raise DeviceError("Device has not been created", self.path)

        # Setup VG parents (in case they are dmraid partitions for example)
        self.vg.setupParents()

        if self.format.exists:
            self.format.teardown()

        udev_settle(timeout=10)
        lvm.lvresize(self.vg.name, self._name, self.size)
