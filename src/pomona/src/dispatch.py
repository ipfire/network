#
# dispatch.py: install/upgrade master flow control
#
# Erik Troan <ewt@redhat.com>
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

import string
from types import *
from constants import *
from autopart import doAutoPartition
from bootloader import writeBootloader, bootloaderSetupChoices
from packages import turnOnFilesystems, betaNagScreen, setupTimezone
from partitioning import partitionObjectsInitialize, partitioningComplete

from packages import doMigrateFilesystems
from packages import doPostAction
from packages import copyPomonaLogs
#
#from flags import flags
#from installmethod import doMethodComplete

#from backend import doPostSelection, doRepoSetup, doBasePackageSelect
from backend import doPreInstall, doPostInstall, doInstall
from backend import writeConfiguration

import logging
log = logging.getLogger("pomona")

#
# items are one of
#
#       ( name )
#       ( name, Function )
#
# in the second case, the function is called directly from the dispatcher

# All install steps take the pomona object as their sole argument.  This
# gets passed in when we call the function.
installSteps = [
                ("welcome", ),
                ("betanag", betaNagScreen, ),
                ("language", ),
                ("keyboard", ),
                ("source", ),
                ("partitionobjinit", partitionObjectsInitialize, ),
                ("parttype", ),
                ("autopartitionexecute", doAutoPartition, ),
                ("partition", ),
                ("partitiondone", partitioningComplete, ),
                ("bootloadersetup", bootloaderSetupChoices, ),
                ("bootloader", ),
                ("bootloaderadvanced", ),
                #("network", ),
                ("timezone", ),
                ("accounts", ),
                #("reposetup", doRepoSetup, ),
                #("basepkgsel", doBasePackageSelect, ),
                #("tasksel", ),
                #("group-selection", ),
                #("postselection", doPostSelection, ),
                ("confirminstall", ),
                ("install", ),
                ("migratefilesystems", doMigrateFilesystems, ),
                ("enablefilesystems", turnOnFilesystems, ),
                ("setuptime", setupTimezone, ),
                ("preinstallconfig", doPreInstall, ),
                ("installpackages", doInstall, ),
                ("postinstallconfig", doPostInstall, ),
                ("writeconfig", writeConfiguration, ),
                ("instbootloader", writeBootloader, ),
                ("copylogs", copyPomonaLogs, ),
                #("methodcomplete", doMethodComplete, ),
                #("postscripts", runPostScripts, ),
                ("dopostaction", doPostAction, ),
                ("complete", ),
        ]

class Dispatcher:
    def gotoPrev(self):
        self._setDir(DISPATCH_BACK)
        self.moveStep()

    def gotoNext(self):
        self._setDir(DISPATCH_FORWARD)
        self.moveStep()

    def canGoBack(self):
        # begin with the step before this one.  If all steps are skipped,
        # we can not go backwards from this screen
        i = self.step - 1
        while i >= self.firstStep:
            if not self.stepIsDirect(i) and not self.skipSteps.has_key(installSteps[i][0]):
                return True
            i = i - 1
        return False

    def setStepList(self, *steps):
        # only remove non-permanently skipped steps from our skip list
        for step, state in self.skipSteps.items():
            if state == 1:
                del self.skipSteps[step]

        stepExists = {}
        for step in installSteps:
            name = step[0]
            if not name in steps:
                self.skipSteps[name] = 1

            stepExists[name] = 1

        for name in steps:
            if not stepExists.has_key(name):
                log.warning("step %s does not exist", name)

    def stepInSkipList(self, step):
        if type(step) == type(1):
            step = installSteps[step][0]
        return self.skipSteps.has_key(step)

    def skipStep(self, stepToSkip, skip = 1, permanent = 0):
        for step in installSteps:
            name = step[0]
            if name == stepToSkip:
                if skip:
                    if permanent:
                        self.skipSteps[name] = 2
                    elif not self.skipSteps.has_key(name):
                        self.skipSteps[name] = 1
                elif self.skipSteps.has_key(name):
                    # if marked as permanent then dont change
                    if self.skipSteps[name] != 2:
                        del self.skipSteps[name]
                return
        log.warning("step %s does not exist", stepToSkip)

    def stepIsDirect(self, step):
        """Takes a step number"""
        if len(installSteps[step]) == 2:
            return True
        else:
            return False

    def moveStep(self):
        if self.step == None:
            self.step = self.firstStep
        else:
            self.step = self.step + self._getDir()

        if self.step >= len(installSteps):
            return None

        while self.step >= self.firstStep and self.step < len(installSteps) \
                        and (self.stepInSkipList(self.step) or self.stepIsDirect(self.step)):
            if self.stepIsDirect(self.step) and not self.stepInSkipList(self.step):
                (stepName, stepFunc) = installSteps[self.step]
                log.info("moving (%d) to step %s" % (self._getDir(), stepName))
                rc = stepFunc(self.pomona)
                if rc in [DISPATCH_BACK, DISPATCH_FORWARD]:
                    self._setDir(rc)
                    # if anything else, leave self.dir alone

            self.step = self.step + self._getDir()
            if self.step == len(installSteps):
                return None

        if (self.step < 0):
            # pick the first step not in the skip list
            self.step = 0
            while self.skipSteps.has_key(installSteps[self.step][0]):
                self.step = self.step + 1
        elif self.step >= len(installSteps):
            self.step = len(installSteps) - 1
            while self.skipSteps.has_key(installSteps[self.step][0]):
                self.step = self.step - 1
        log.info("moving (%d) to step %s" % (self._getDir(), installSteps[self.step][0]))

    def currentStep(self):
        if self.step == None:
            self.gotoNext()
        elif self.step >= len(installSteps):
            return (None, None)

        stepInfo = installSteps[self.step]
        step = stepInfo[0]

        return (step, self.pomona)

    def __init__(self, pomona):
        self.pomona = pomona
        self.pomona.dir = DISPATCH_FORWARD
        self.step = None
        self.skipSteps = {}

        self.method = pomona.method
        self.firstStep = 0

    def _getDir(self):
        return self.pomona.dir

    def _setDir(self, dir):
        self.pomona.dir = dir

    dir = property(_getDir,_setDir)
