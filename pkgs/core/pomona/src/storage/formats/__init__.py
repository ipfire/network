#!/usr/bin/python

import os
import copy

device_formats = {}
def register_device_format(fmt_class):
    if not issubclass(fmt_class, DeviceFormat):
        raise ValueError("Argument must be a subclass of DeviceFormat")
    device_formats[fmt_class._type] = fmt_class

def getFormat(fmt_type, *args, **kwargs):
    """ Return a DeviceFormat instance based on fmt_type and args.

        Given a device format type and a set of constructor arguments,
        return a DeviceFormat instance.

        Return None if no suitable format class is found.

        Arguments:

            fmt_type -- the name of the format type (eg: 'ext3', 'swap')

        Keyword Arguments:

            The keyword arguments may vary according to the format type,
            but here is the common set:

            device -- path to the device on which the format resides
            uuid -- the UUID of the (preexisting) formatted device
            exists -- whether or not the format exists on the device

    """
    fmt_class = get_device_format_class(fmt_type)
    fmt = None
    if fmt_class:
        fmt = fmt_class(*args, **kwargs)
    try:
        className = fmt.__class__.__name__
    except AttributeError:
        className = None
    return fmt

def get_device_format_class(fmt_type):
    """ Return an appropriate format class based on fmt_type. """
    if not device_formats:
        collect_device_format_classes()

    fmt = device_formats.get(fmt_type)
    if not fmt:
        for fmt_class in device_formats.values():
            if fmt_type and fmt_type == fmt_class._name:
                fmt = fmt_class
                break
            elif fmt_type in fmt_class._udevTypes:
                fmt = fmt_class
                break

    # default to no formatting, AKA "Unknown"
    if not fmt:
        fmt = DeviceFormat
    return fmt

def collect_device_format_classes():
    """ Pick up all device format classes from this directory.

        Note: Modules must call register_device_format(FormatClass) in
              order for the format class to be picked up.
    """
    dir = os.path.dirname(__file__)
    for module_file in os.listdir(dir):
        # make sure we're not importing this module
        if module_file.endswith(".py") and module_file != __file__:
            mod_name = module_file[:-3]
            try:
                globals()[mod_name] = __import__(mod_name, globals(), locals(), [], -1)
            except ImportError, e:
                pass

default_fstypes = ("ext4", "ext3", "ext2")
default_boot_fstypes = ("ext3", "ext2")
def get_default_filesystem_type(boot=None):
    if boot:
        fstypes = default_boot_fstypes
    else:
        fstypes = default_fstypes

    for fstype in fstypes:
        try:
            supported = get_device_format_class(fstype).supported
        except AttributeError:
            supported = None

        if supported:
            return fstype

    raise DeviceFormatError("None of %s is supported by your kernel" % ",".join(fstypes))

class DeviceFormat(object):
    """ Generic device format. """
    _type = None
    _name = "Unknown"
    _udevTypes = []
    partedFlag = None
    _formattable = False                # can be formatted
    _supported = False                  # is supported
    _resizable = False                  # can be resized
    _bootable = False                   # can be used as boot
    _migratable = False                 # can be migrated
    _maxSize = 0                        # maximum size in MB
    _minSize = 0                        # minimum size in MB
    _dump = False
    _check = False

    def __init__(self, installer, *args, **kwargs):
        """ Create a DeviceFormat instance.

            Keyword Arguments:

                device -- path to the underlying device
                uuid -- this format's UUID
                exists -- indicates whether this is an existing format

        """
        self.installer = installer

        self.device = kwargs.get("device")
        self.uuid = kwargs.get("uuid")
        self.exists = kwargs.get("exists")
        self.options = kwargs.get("options")
        self._migrate = False

    def __deepcopy__(self, memo):
        new = self.__class__.__new__(self.__class__)
        memo[id(self)] = new
        shallow_copy_attrs = ('installer', 'screen')
        for (attr, value) in self.__dict__.items():
            if attr in shallow_copy_attrs:
                setattr(new, attr, copy.copy(value))
            else:
                setattr(new, attr, copy.deepcopy(value, memo))

        return new

    def _setOptions(self, options):
        self._options = options

    def _getOptions(self):
        return self._options

    options = property(_getOptions, _setOptions)

    def _setDevice(self, devspec):
        if devspec and not devspec.startswith("/"):
            raise ValueError("device must be a fully qualified path: %s" % devspec)
        self._device = devspec

    def _getDevice(self):
        return self._device

    device = property(lambda f: f._getDevice(),
                      lambda f,d: f._setDevice(d),
                      doc="Full path the device this format occupies")

    @property
    def name(self):
        if self._name:
            name = self._name
        else:
            name = self.type
        return name

    @property
    def type(self):
        return self._type

    def probe(self):
        pass

    def notifyKernel(self):
        if not self.device:
            return

        if self.device.startswith("/dev/mapper/"):
            try:
                name = dm_node_from_name(os.path.basename(self.device))
            except Exception, e:
                self.installer.log.warning("Failed to get dm node for %s" % self.device)
                return
        elif self.device:
            name = os.path.basename(self.device)

        path = get_sysfs_path_by_name(name)
        try:
            notify_kernel(path, action="change")
        except Exception, e:
            self.installer.log.warning("Failed to notify kernel of change: %s" % e)

    def create(self, *args, **kwargs):
        # allow late specification of device path
        device = kwargs.get("device")
        if device:
            self.device = device

        if not os.path.exists(self.device):
            raise FormatCreateError("invalid device specification")

    def destroy(self, *args, **kwargs):
        # zero out the 1MB at the beginning and end of the device in the
        # hope that it will wipe any metadata from filesystems that
        # previously occupied this device
        self.installer.log.debug("Zeroing out beginning and end of %s..." % self.device)
        try:
            fd = os.open(self.device, os.O_RDWR)
            buf = '\0' * 1024 * 1024
            os.write(fd, buf)
            os.lseek(fd, -1024 * 1024, 2)
            os.write(fd, buf)
            os.close(fd)
        except OSError as e:
            if getattr(e, "errno", None) == 28: # No space left in device
                pass
            else:
                self.installer.log.error("Error zeroing out %s: %s" % (self.device, e))
            os.close(fd)
        except Exception as e:
            self.installer.log.error("Error zeroing out %s: %s" % (self.device, e))
            os.close(fd)

        self.exists = False

    def setup(self, *args, **kwargs):
        if not self.exists:
            raise FormatSetupError("format has not been created")

        if self.status:
            return

        # allow late specification of device path
        device = kwargs.get("device")
        if device:
            self.device = device

        if not self.device or not os.path.exists(self.device):
            raise FormatSetupError("invalid device specification")

    def teardown(self, *args, **kwargs):
        pass

    @property
    def status(self):
        return (self.exists and
                self.__class__ is not DeviceFormat and
                isinstance(self.device, str) and
                self.device and
                os.path.exists(self.device))

    @property
    def formattable(self):
        """ Can we create formats of this type? """
        return self._formattable

    @property
    def supported(self):
        """ Is this format a supported type? """
        return self._supported

    @property
    def resizable(self):
        """ Can formats of this type be resized? """
        return self._resizable

    @property
    def bootable(self):
        """ Is this format type suitable for a boot partition? """
        return self._bootable

    @property
    def migratable(self):
        """ Can formats of this type be migrated? """
        return self._migratable

    @property
    def migrate(self):
        return self._migrate

    @property
    def linuxNative(self):
        """ Is this format type native to linux? """
        return self._linuxNative

    @property
    def mountable(self):
        """ Is this something we can mount? """
        return False

    @property
    def dump(self):
        """ Whether or not this format will be dumped by dump(8). """
        return self._dump

    @property
    def check(self):
        """ Whether or not this format is checked on boot. """
        return self._check

    @property
    def maxSize(self):
        """ Maximum size (in MB) for this format type. """
        return self._maxSize

    @property
    def minSize(self):
        """ Minimum size (in MB) for this format type. """
        return self._minSize


collect_device_format_classes()
