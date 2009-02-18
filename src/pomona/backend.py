#
# backend.py: Interface for installation backends
#
# Paul Nasrat <pnasrat@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright (c) 2005 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import shutil
import iutil
import os, sys
import logging
from constants import *

import packages

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

from flags import flags
log = logging.getLogger("pomona")

class PomonaBackend:
    def __init__(self, instPath):
        """Abstract backend class all backends should inherit from this
           @param instPath: root path for the installation to occur"""

        self.instPath = instPath
        self.modeText = ""

    def doPreSelection(self, intf, id, instPath):
        pass

    def doPostSelection(self, pomona):
        pass

    def doPreInstall(self, pomona):
        pass

    def doPostInstall(self, pomona):
        sys.stdout.flush()

    def doInstall(self, pomona):
        log.warning("doInstall not implemented for backend!")
        pass

    def postAction(self, pomona):
        pass

    def kernelVersionList(self):
        return []

    def doInitialSetup(self, pomona):
        pass

    def doRepoSetup(self, pomona):
        log.warning("doRepoSetup not implemented for backend!")
        pass

    def groupExists(self, group):
        log.warning("groupExists not implemented for backend!")
        pass

    def selectGroup(self, group, *args):
        log.warning("selectGroup not implemented for backend!")
        pass

    def deselectGroup(self, group, *args):
        log.warning("deselectGroup not implemented for backend!")
        pass

    def packageExists(self, pkg):
        log.warning("packageExists not implemented for backend!")
        pass

    def selectPackage(self, pkg, *args):
        log.warning("selectPackage not implemented for backend!")
        pass

    def deselectPackage(self, pkg, *args):
        log.warning("deselectPackage not implemented for backend!")
        pass

    def getDefaultGroups(self, pomona):
        log.warning("getDefaultGroups not implemented for backend!")
        pass

    def writeConfiguration(self):
        log.warning("writeConfig not implemented for backend!")
        pass

    def getRequiredMedia(self):
        log.warning("getRequiredMedia not implmented for backend!")
        pass

def doRepoSetup(pomona):
    pomona.backend.doInitialSetup(pomona)
    if pomona.backend.doRepoSetup(pomona) == DISPATCH_BACK:
        return DISPATCH_BACK

def doPostSelection(pomona):
    return pomona.backend.doPostSelection(pomona)

def doPreInstall(pomona):
    pomona.backend.doPreInstall(pomona)

def doPostInstall(pomona):
    pomona.backend.doPostInstall(pomona)

def doInstall(pomona):
    pomona.backend.doInstall(pomona)

def writeConfiguration(pomona):
    log.info("Writing main configuration")
    pomona.id.write(pomona)
    pomona.backend.writeConfiguration()
