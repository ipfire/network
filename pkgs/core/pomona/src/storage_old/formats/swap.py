#!/usr/bin/python

from parted import PARTITION_SWAP

from . import DeviceFormat, register_device_format
from ..devicelibs import swap

class SwapSpace(DeviceFormat):
    """ Swap space """
    _type = "swap"
    _name = None
    _udevTypes = ["swap"]
    partedFlag = PARTITION_SWAP
    _formattable = True                # can be formatted
    _supported = True                  # is supported
    _linuxNative = True                # for clearpart

    def __init__(self, installer, *args, **kwargs):
        """ Create a SwapSpace instance.

            Keyword Arguments:

                device -- path to the underlying device
                uuid -- this swap space's uuid
                label -- this swap space's label
                priority -- this swap space's priority
                exists -- indicates whether this is an existing format

        """
        self.installer = installer
        DeviceFormat.__init__(self, self.installer, *args, **kwargs)

        self.priority = kwargs.get("priority")
        self.label = kwargs.get("label")

    def _setPriority(self, priority):
        if priority is None:
            self._priority = None
            return

        if not isinstance(priority, int) or not 0 <= priority <= 32767:
            raise ValueError("swap priority must be an integer between 0 and 32767")

        self._priority = priority

    def _getPriority(self):
        return self._priority

    priority = property(_getPriority, _setPriority,
                        doc="The priority of the swap device")

    def _getOptions(self):
        opts = ""
        if self.priority is not None:
            opts += "pri=%d" % self.priority

        return opts

    def _setOptions(self, opts):
        if not opts:
            self.priority = None
            return

        for option in opts.split(","):
            (opt, equals, arg) = option.partition("=")
            if equals and opt == "pri":
                try:
                    self.priority = int(arg)
                except ValueError:
                    self.installer.log.info("invalid value for swap priority: %s" % arg)

    options = property(_getOptions, _setOptions,
                       doc="The swap device's fstab options string")

    @property
    def status(self):
        """ Device status. """
        return self.exists and swap.swapstatus(self.device)

    def setup(self, *args, **kwargs):
        """ Open, or set up, a device. """
        if not self.exists:
            raise SwapSpaceError("format has not been created")

        if self.status:
            return

        DeviceFormat.setup(self, *args, **kwargs)
        swap.swapon(self.device, priority=self.priority)

    def teardown(self, *args, **kwargs):
        """ Close, or tear down, a device. """
        if not self.exists:
            raise SwapSpaceError("format has not been created")

        if self.status:
            swap.swapoff(self.device)

    def create(self, *args, **kwargs):
        """ Create the device. """
        if self.exists:
            raise SwapSpaceError("format already exists")

        if self.status:
            raise SwapSpaceError("device exists and is active")

        DeviceFormat.create(self, *args, **kwargs)
        swap.mkswap(self.device, label=self.label)
        self.exists = True


register_device_format(SwapSpace)
