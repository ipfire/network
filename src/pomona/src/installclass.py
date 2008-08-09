# this is the prototypical class for workstation, server, and kickstart
# installs
#
# The interface to BaseInstallClass is *public* -- ISVs/OEMs can customize the
# install by creating a new derived type of this class.
#
# Copyright 1999-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os, sys, inutil
import string
import language
import imputil

from instdata import InstallData
from partitioning import *
from autopart import getAutopartitionBoot, autoCreatePartitionRequests
#import pakfireinstall

from pyfire.translate import _, N_

import logging
log = logging.getLogger("pomona")

from flags import flags
from constants import *

class BaseInstallClass:
    # default to not being hidden
    hidden = 0
    pixmap = None
    showMinimal = 1
    showLoginChoice = 0
    _description = ""
    _descriptionFields = ()
    regkeydesc = None
    name = "base"
    pkgstext = ""
    # default to showing the upgrade option
    showUpgrade = True

    # list of of (txt, grplist) tuples for task selection screen
    tasks = []

    # dict of repoid: (baseurl, mirrorurl) tuples for additional repos
    repos = {}

    # don't select this class by default
    default = 0

    # don't force text mode
    forceTextMode = 0

    # allow additional software repositories beyond the base to be configured
    allowExtraRepos = True

    # by default, place this under the "install" category; it gets it's
    # own toplevel category otherwise
    parentClass = ( _("Install on System"), "install.png" )

    # we can use a different install data class
    installDataClass = InstallData

    # install key related bits
    skipkeytext = None
    instkeyname = None
    allowinstkeyskip = True
    instkeydesc = None
    installkey = None
    skipkey = False

    def setBootloader(self, id, location=None, forceLBA=0, password=None,
                      md5pass=None, appendLine="", driveorder = []):
        if appendLine:
            id.bootloader.args.set(appendLine)
            id.bootloader.setForceLBA(forceLBA)
        if password:
            id.bootloader.setPassword(password, isCrypted = 0)
        if md5pass:
            id.bootloader.setPassword(md5pass)
        if location != None:
            id.bootloader.defaultDevice = location
        else:
            id.bootloader.defaultDevice = -1

        # XXX throw out drives specified that don't exist.  anything else
        # seems silly
        if driveorder and len(driveorder) > 0:
            new = []
            for drive in driveorder:
                if drive in id.bootloader.drivelist:
                    new.append(drive)
                else:
                    log.warning("requested drive %s in boot drive order "
                                "doesn't exist" %(drive,))
            id.bootloader.drivelist = new

    def setIgnoredDisks(self, id, drives):
        diskset = id.diskset
        for drive in drives:
            if not drive in diskset.skippedDisks:
                diskset.skippedDisks.append(drive)

    def setClearParts(self, id, clear, drives = None, initAll = False):
        id.partitions.autoClearPartType = clear
        id.partitions.autoClearPartDrives = drives
        if initAll:
            id.partitions.reinitializeDisks = initAll

    def setSteps(self, pomona):
        dispatch = pomona.dispatch
        dispatch.setStepList(
            "language",
            "keyboard",
            "welcome",
            "findrootparts",
            "betanag",
            "installtype",
            "partitionobjinit",
            "parttype",
            "autopartitionexecute",
            "partition",
            "partitiondone",
            "bootloadersetup",
            "bootloader",
            "networkdevicecheck",
            "network",
            "timezone",
            "accounts",
            "reposetup",
            "basepkgsel",
            "tasksel",
            "postselection",
            "confirminstall",
            "install",
            "enablefilesystems",
            "migratefilesystems",
            "setuptime",
            "preinstallconfig",
            "installpackages",
            "postinstallconfig",
            "writeconfig",
            "firstboot",
            "instbootloader",
            "dopostaction",
            "postscripts",
            "writexconfig",
            "writeksconfig",
            "writeregkey",
            "methodcomplete",
            "copylogs",
            "setfilecon",
            "complete"
        )

    def setZeroMbr(self, id, zeroMbr):
        id.partitions.zeroMbr = zeroMbr

    def setKeyboard(self, id, kb):
        id.keyboard.set(kb)

    def setTimezoneInfo(self, id, timezone, asUtc = 0, asArc = 0):
        id.timezone.setTimezoneInfo(timezone, asUtc, asArc)

    def setLanguageDefault(self, id, default):
        id.instLanguage.setDefault(default)

    def setLanguage(self, id, nick):
        id.instLanguage.setRuntimeLanguage(nick)

    def setDefaultPartitioning(self, partitions, clear = CLEARPART_TYPE_ALL,
                               doClear = 1):
        autorequests = [ ("/", None, 1024, None, 1, 1, 1) ]

        bootreq = getAutopartitionBoot()
        if bootreq:
            autorequests.extend(bootreq)

        (minswap, maxswap) = inutil.swapSuggestion()
        autorequests.append((None, "swap", minswap, maxswap, 1, 1, 1))

        if doClear:
            partitions.autoClearPartType = clear
            partitions.autoClearPartDrives = []

        partitions.autoPartitionRequests = autoCreatePartitionRequests(autorequests)

    def setInstallData(self, pomona):
        pomona.id.reset(pomona)
        pomona.id.instClass = self

    def getMethod(self, methodstr):
        if methodstr.startswith('cdrom://'):
            from image import CdromInstallMethod
            return CdromInstallMethod
        elif methodstr.startswith('ftp://') or methodstr.startswith('http://'):
            from urlinstall import UrlInstallMethod
            return UrlInstallMethod
        ### XXX Currently out of order :)
        #elif methodstr.startswith('hd://'):
        #       from harddrive import HardDriveInstallMethod
        #       return HardDriveInstallMethod
        else:
            return None

    def getBackend(self):
        #return pakfireinstall.PakfireBackend
        return None ### XXX

    # Classes should call these on __init__ to set up install data
    #id.setKeyboard()
    #id.setLanguage()
    #id.setLanguageDefault()
    #id.setTimezone()

    def __init__(self, expert):
        pass

    def postAction(self, pomona):
        pomona.backend.postAction(pomona)

# we need to be able to differentiate between this and custom
class DefaultInstall(BaseInstallClass):
    def __init__(self, expert):
        BaseInstallClass.__init__(self, expert)

# custom installs are easy :-)
class InstallClass(BaseInstallClass):
    # name has underscore used for mnemonics, strip if you dont need it
    id = "ipfire"
    name = N_("IPFire")

    def setInstallData(self, pomona):
        BaseInstallClass.setInstallData(self, pomona)
        BaseInstallClass.setDefaultPartitioning(self, pomona.id.partitions,
                                                CLEARPART_TYPE_ALL)

    def setSteps(self, pomona):
        dispatch = pomona.dispatch
        BaseInstallClass.setSteps(self, dispatch)
        dispatch.skipStep("partition")

    def __init__(self, expert):
        BaseInstallClass.__init__(self, expert)
