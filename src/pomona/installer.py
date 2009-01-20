#!/usr/bin/python
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2008  Michael Tremer & Christian Schmidt                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import os
import sys
import re
import signal
import warnings
from optparse import OptionParser

import isys
import users
import inutil
import dispatch
from flags import flags
from constants import *

from tui import InstallInterface
from pakfireinstall import PakfireBackend
from instdata import InstallData
from autopart import getAutopartitionBoot, autoCreatePartitionRequests

# Make sure messages sent through python's warnings module get logged.
def PomonaShowWarning(message, category, filename, lineno, file=sys.stderr):
    log.warning("%s" % warnings.formatwarning(message, category, filename, lineno))

warnings.showwarning = PomonaShowWarning

def parseOptions():

    op = OptionParser()

    # Method of operation
    op.add_option("-d", "--debug", dest="debug", action="store_true", default=False)
    op.add_option("--expert", action="store_true", default=False)
    op.add_option("-t", "--test", action="store_true", default=False)

    op.add_option("-m", "--method", default=None)

    # Language
    op.add_option("--keymap")
    op.add_option("--kbdtype")
    op.add_option("--lang")

    # Obvious
    op.add_option("--loglevel")
    op.add_option("--syslog")

    return op.parse_args()

def setupLoggingFromOpts(opts):
    if opts.loglevel and logLevelMap.has_key(opts.loglevel):
        log.setHandlersLevel(logLevelMap[opts.loglevel])

    if opts.syslog:
        if opts.syslog.find(":") != -1:
            (host, port) = opts.syslog.split(":")
            logger.addSysLogHandler(log, host, port=int(port))
        else:
            logger.addSysLogHandler(log, opts.syslog)

def checkMemory():
    if inutil.memInstalled() < isys.MIN_RAM:
        from snack import SnackScreen, ButtonChoiceWindow

        screen = SnackScreen()
        ButtonChoiceWindow(screen, _("Fatal Error"),
                                   _("You do not have enough RAM to install %s "
                                     "on this machine.\n"
                                     "\n"
                                     "Press <return> to reboot your system.\n")
                                    % (name,), buttons = (_("OK"),))
        screen.finish()
        sys.exit(0)

class Pomona:
    def __init__(self):
        self.intf = None
        self.id = None
        self.rootPath = HARDDISK_PATH
        self.dispatch = dispatch.Dispatcher(self)

        self.backend = PakfireBackend(self.rootPath)

    def setDefaultPartitioning(self, partitions, clear = CLEARPART_TYPE_ALL, doClear = 1):
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

    def setZeroMbr(self, zeroMbr):
        self.id.partitions.zeroMbr = zeroMbr

    def setKeyboard(self, kb):
        self.id.console.setKeymap(kb)

    def setTimezoneInfo(self, timezone, asUtc = 0, asArc = 0):
        self.id.timezone.setTimezoneInfo(timezone, asUtc, asArc)

    def setLanguage(self, lang):
        self.id.console.setLanguage(lang)

if __name__ == "__main__":
    pomona = Pomona()

    # Set up logging
    import logging
    from pomona_log import logger, logLevelMap

    log = logging.getLogger("pomona")
    stdoutLog = logging.getLogger("pomona.stdout")
    if os.access("/dev/tty3", os.W_OK):
        logger.addFileHandler("/dev/tty3", log)

    log.info("pomona called with cmdline = %s" %(sys.argv,))

    # Set up environment
    if not os.environ.has_key("LANG"):
        os.environ["LANG"] = "en_US.UTF-8"
    os.environ['HOME'] = '/tmp'
    os.environ['LC_NUMERIC'] = 'C'

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGSEGV, isys.handleSegv)

    # Reading command line options
    (opts, args) = parseOptions()

    setupLoggingFromOpts(opts)

    if opts.expert:
        flags.expert = 1

    if opts.test:
        flags.test = 1

    if opts.debug:
        flags.debug = True
        import pdb
        pdb.set_trace()

    log.info (_("Starting text installation..."))

    checkMemory()

    pomona.intf = InstallInterface()

    pomona.id = InstallData(pomona)
    pomona.id.reset(pomona)
    pomona.setDefaultPartitioning(pomona.id.partitions, CLEARPART_TYPE_ALL)

    if flags.expert:
        pomona.dispatch.setStepList(
            "language",
            "keyboard",
            "welcome",
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
    else:
        pomona.dispatch.setStepList(
            "language",
            "keyboard",
            "welcome",
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

    users.createLuserConf(pomona.rootPath)

    if opts.lang:
        pomona.dispatch.skipStep("language", permanent = 1)
        pomona.setLanguage(opts.lang)
        pomona.id.timezone.setTimezoneInfo(pomona.id.console.getDefaultTimeZone())

    if opts.keymap:
        pomona.dispatch.skipStep("keyboard", permanent = 1)
        pomona.setKeyboard(opts.keymap)

    from exception import handleException
    sys.excepthook = lambda type, value, tb, pomona=pomona: handleException(pomona, (type, value, tb))

    try:
        pomona.intf.run(pomona)
    except SystemExit, code:
        pomona.intf.shutdown()
    except:
        handleException(pomona, sys.exc_info())

    del pomona.intf
