#!/usr/bin/python

from parted import PARTITION_LVM

from . import DeviceFormat, register_device_format
from ..errors import *
from ..devicelibs import lvm

class LVMPhysicalVolume(DeviceFormat):
    """ An LVM physical volume. """
    _type = "lvmpv"
    _name = "physical volume (LVM)"
    _udevTypes = ["LVM2_member"]
    partedFlag = PARTITION_LVM
    _formattable = True                 # can be formatted
    _supported = True                   # is supported
    _linuxNative = True                 # for clearpart

    def __init__(self, *args, **kwargs):
        """ Create an LVMPhysicalVolume instance.

            Keyword Arguments:

                device -- path to the underlying device
                uuid -- this PV's uuid (not the VG uuid)
                vgName -- the name of the VG this PV belongs to
                vgUuid -- the UUID of the VG this PV belongs to
                peStart -- offset of first physical extent
                exists -- indicates whether this is an existing format

        """
        DeviceFormat.__init__(self, *args, **kwargs)
        self.vgName = kwargs.get("vgName")
        self.vgUuid = kwargs.get("vgUuid")
        # liblvm may be able to tell us this at some point, even
        # for not-yet-created devices
        self.peStart = kwargs.get("peStart", 0.1875)    # in MB

    def probe(self):
        """ Probe for any missing information about this device. """
        if not self.exists:
            raise PhysicalVolumeError("format has not been created")

        #info = lvm.pvinfo(self.device)
        #self.vgName = info['vg_name']
        #self.vgUuid = info['vg_uuid']

    def create(self, *args, **kwargs):
        """ Create the format. """
        DeviceFormat.create(self, *args, **kwargs)
        # Consider use of -Z|--zero
        # -f|--force or -y|--yes may be required

        # lvm has issues with persistence of metadata, so here comes the
        # hammer...
        DeviceFormat.destroy(self, *args, **kwargs)

        lvm.pvcreate(self.device)
        self.exists = True
        self.notifyKernel()

    def destroy(self, *args, **kwargs):
        """ Destroy the format. """
        if not self.exists:
            raise PhysicalVolumeError("format has not been created")

        if self.status:
            raise PhysicalVolumeError("device is active")

        # FIXME: verify path exists?
        try:
            lvm.pvremove(self.device)
        except LVMError:
            DeviceFormat.destroy(self, *args, **kwargs)

        self.exists = False
        self.notifyKernel()

    @property
    def status(self):
        # XXX hack
        return (self.exists and self.vgName and
                os.path.isdir("/dev/mapper/%s" % self.vgName))

register_device_format(LVMPhysicalVolume)
