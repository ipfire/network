#
# Copyright (c) 2005-2007 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import sys
import os
import os.path
import shutil
import warnings
import locale
import signal
import subprocess
import time

import urlgrabber.progress
import urlgrabber.grabber
from urlgrabber.grabber import URLGrabber, URLGrabError
from backend import PomonaBackend
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

import logging
log = logging.getLogger("pomona")

import urlparse
urlparse.uses_fragment.append('media')

import inutil
import isys
import pyfire

def size_string(size):
    def number_format(s):
        return locale.format("%s", s, 1)

    if size > 1024 * 1024:
        size = size / (1024*1024)
        return _("%s MB") %(number_format(size),)
    elif size > 1024:
        size = size / 1024
        return _("%s KB") %(number_format(size),)
    else:
        if size == 1:
            return _("%s Byte") %(number_format(size),)
        else:
            return _("%s Bytes") %(number_format(size),)

class PomonaCallback:
    def __init__(self, pomona):
        self.messageWindow = pomona.intf.messageWindow
        self.waitWindow = pomona.intf.waitWindow
        self.progress = pomona.id.instProgress
        self.progressWindow = pomona.intf.progressWindow

        self.initWindow = None

        self.lastprogress = 0
        self.incr = 20

        self.text = ""

        self.window = None
        self.windowType = None

    def setSize(self, totalSize):
        self.totalSize = totalSize
        self.doneSize = 0
        self.lastprogress = 0
        self.incr = totalSize / 100

    def callback(self, what, amount=0, title=None, text=None):
        # first time here means we should pop the window telling
        # user to wait until we get here
        if self.initWindow is not None:
            self.initWindow.pop()
            self.initWindow = None

        if what == CB_START:
            if self.totalSize == 0:
                self.window = self.waitWindow(title, text, width=55)
                self.text = text
                self.windowType = "wait"
            else:
                self.window = self.progressWindow(title, text, self.totalSize)
                self.windowType = "progress"

        elif what == CB_STOP:
            self.window.pop()

        elif what == CB_PROGRESS:
            if self.windowType == "progress":
                if amount > self.lastprogress + self.incr:
                    self.window.set(amount)
                    self.lastprogress = amount
            elif self.windowType == "wait":
                self.window.set_text(self.text + " " + amount)

class PomonaPakfire:
    def __init__(self, pomona):
        self.pomona = pomona

    def run(self, cb, intf, id):
        self.extractFiles(cb, intf, id)

    def extractFiles(self, cb, intf, id):
        filename    = os.path.join(SOURCE_PATH, IMAGE_FILE)
        filename_ls = os.path.join(SOURCE_PATH, IMAGE_FILE_LS)

        fd = open(filename_ls, 'r')
        filesize = 0
        while fd.readline():
            filesize += 1
        fd.close()
        cb.setSize(filesize)

        filesize = int(os.path.getsize(filename))
        log.info("Source file %s has size of %dKB" % (filename, filesize / 1024,))

        command = "unsquashfs -n -i -f -d %s %s 2>/dev/tty5" % (HARDDISK_PATH, filename,)

        extractor = subprocess.Popen(command, shell=True,
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE)

        cb.callback(CB_START, title=_("Base system"), text=_("Installing base system..."))

        buf = extractor.stdout.readline()
        tot = 0
        while buf != "":
            tot += 1
            cb.callback(CB_PROGRESS, amount=tot)
            buf = extractor.stdout.readline()

        cb.callback(CB_STOP)

class PakfireBackend(PomonaBackend):
    def __init__(self, instPath):
        PomonaBackend.__init__(self, instPath)

    def selectBestKernel(self):
        """Find the best kernel package which is available and select it."""
        pass ## XXX todo?

    def selectFSPackages(self, fsset, diskset):
        for entry in fsset.entries:
            map(self.selectPackage, entry.fsystem.getNeededPackages())

    def doPostSelection(self, pomona):
        pass

    def doPreInstall(self, pomona):
        if pomona.dir == DISPATCH_BACK:
            return DISPATCH_BACK

        self.pompak = PomonaPakfire(pomona)

    def doInstall(self, pomona):
        log.info("Preparing to install files")

        cb = PomonaCallback(pomona)

        cb.initWindow = pomona.intf.waitWindow(_("Install Starting"),
                _("Starting install process.  This may take several minutes..."))
        time.sleep(2)

        self.pompak.run(cb, pomona.intf, pomona.id)

        if cb.initWindow is not None:
            cb.initWindow.pop()

        pomona.id.instProgress = None

    def doPostInstall(self, pomona):
        w = pomona.intf.waitWindow(_("Post Install"),
                                   _("Performing post install configuration..."))

        # we need to have a /dev after install and now that udev is
        # handling /dev, it gets to be more fun.  so just bind mount the
        # installer /dev
        isys.mount("/dev", "%s/dev" %(pomona.rootPath,), bindMount = 1)

        # write out the fstab
        pomona.id.fsset.write(pomona.rootPath)
        # rootpath mode doesn't have this file around
        if os.access("/tmp/modprobe.conf", os.R_OK):
            shutil.copyfile("/tmp/modprobe.conf",
                            pomona.rootPath + "/etc/modprobe.conf")

        ### XXX pomona.id.network.write(pomona.rootPath)

        for (kernelName, kernelVersion, kernelTag, kernelDesc) in self.kernelVersionList(pomona):
            initrd = "/boot/initramfs-%s%s.img" % (kernelVersion, kernelTag,)
            log.info("mkinitramfs: creating %s" % initrd)
            pyfire.executil.execWithRedirect("/sbin/mkinitramfs",
                                            ["/sbin/mkinitramfs", "-v", "-f", "%s" % initrd,
                                             "%s%s" % (kernelVersion, kernelTag,), ],
                                            stdout = "/dev/tty5", stderr = "/dev/tty5",
                                            root = pomona.rootPath)

        PomonaBackend.doPostInstall(self, pomona)
        w.pop()

    def kernelVersionList(self, pomona):
        kernelVersions = []

        tag2desc = { "-smp" : _("Symmetric multiprocessing"),
                     "-xen" : _("Xen guest"), }

        kernelName = "%skernel-%s" % (sname, kernelVersion)

        for kernelTag in [ "", "-smp", "-xen", ]:
            filename = "%s%s" % (kernelName, kernelTag)
            if os.access(pomona.rootPath + "/boot/" + filename, os.R_OK):
                if not kernelTag == "":
                    kernelDesc = tag2desc[kernelTag]
                else:
                    kernelDesc = _("Normal Boot")
                kernelVersions.append((kernelName, kernelVersion, kernelTag, kernelDesc))

        return kernelVersions

class PakfireProgress:
    def __init__(self, intf, text, total):
        window = intf.progressWindow(_("Installation Progress"), text, total, 0.01)
        self.window = window

        self.current = 0
        self.incr = 1
        self.total = total
        self.popped = False

    def set_incr(self, incr):
        self.incr = incr

    def progressbar(self, current, total, name=None):
        if not self.popped:
            self.window.set(float(current)/total * self.incr + self.current)
        else:
            warnings.warn("PakfireProgress.progressbar called when popped",
                          RuntimeWarning, stacklevel=2)

    def pop(self):
        self.window.pop()
        self.popped = True

    def next_task(self, current = None):
        if current:
            self.current = current
        else:
            self.current += self.incr
        if not self.popped:
            self.window.set(self.current)
        else:
            warnings.warn("PakfireProgress.set called when popped",
                          RuntimeWarning, stacklevel=2)
