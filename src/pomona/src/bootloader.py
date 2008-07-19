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
import inutil
import string
from flags import flags
from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

from bootloaderInfo import x86BootloaderInfo, BootyNoKernelWarning
from fsset import *

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
