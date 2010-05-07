#!/usr/bin/python

class StorageError(Exception):
    pass

# Device
class DeviceError(StorageError):
    pass

class DeviceCreateError(DeviceError):
    pass

class DeviceDestroyError(DeviceError):
    pass

class DeviceResizeError(DeviceError):
    pass

class DeviceSetupError(DeviceError):
    pass

class DeviceTeardownError(DeviceError):
    pass

class DeviceUserDeniedFormatError(DeviceError):
    pass

# DeviceFormat
class DeviceFormatError(StorageError):
    pass

class FormatCreateError(DeviceFormatError):
    pass

class FormatDestroyError(DeviceFormatError):
    pass

class FormatSetupError(DeviceFormatError):
    pass

class FormatTeardownError(DeviceFormatError):
    pass

class DMRaidMemberError(DeviceFormatError):
    pass

class FSError(DeviceFormatError):
    pass

class FSResizeError(FSError):
    pass

class FSMigrateError(FSError):
    pass

class LUKSError(DeviceFormatError):
    pass

class MDMemberError(DeviceFormatError):
    pass

class PhysicalVolumeError(DeviceFormatError):
    pass

class SwapSpaceError(DeviceFormatError):
    pass

# devicelibs
class SwapError(StorageError):
    pass

class SuspendError(SwapError):
    pass

class OldSwapError(SwapError):
    pass

class MDRaidError(StorageError):
    pass

class DMError(StorageError):
    pass

class LVMError(StorageError):
    pass

class CryptoError(StorageError):
    pass

# DeviceTree
class DeviceTreeError(StorageError):
    pass

# DeviceAction
class DeviceActionError(StorageError):
    pass

# partitioning
class PartitioningError(StorageError):
    pass

class PartitioningWarning(StorageError):
    pass

# udev
class UdevError(StorageError):
    pass
