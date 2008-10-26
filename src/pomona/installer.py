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

import sys, os, re
import users
from optparse import OptionParser
import inutil, isys, dispatch
from flags import flags
from constants import *
import signal

# Make sure messages sent through python's warnings module get logged.
def PomonaShowWarning(message, category, filename, lineno, file=sys.stderr):
    log.warning("%s" % warnings.formatwarning(message, category, filename, lineno))

def setupEnvironment():
    if not os.environ.has_key("LANG"):
        os.environ["LANG"] = "en_US.UTF-8"
    os.environ['HOME'] = '/tmp'
    os.environ['LC_NUMERIC'] = 'C'

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGSEGV, isys.handleSegv)

def getInstClass():
    from installclass import DefaultInstall
    return DefaultInstall(flags.expert)

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

def expandFTPMethod(opts):
    filename = opts.method[1:]
    opts.method = open(filename, "r").readline()
    opts.method = opts.method[:len(opts.method) - 1]
    os.unlink(filename)

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
        self.backend = None

    def setDispatch(self):
        self.dispatch = dispatch.Dispatcher(self)

    def setBackend(self):
        from pakfireinstall import PakfireBackend
        self.backend = PakfireBackend(self.rootPath)

if __name__ == "__main__":
    pomona = Pomona()

    ### Set up logging
    #
    import logging
    from pomona_log import logger, logLevelMap

    log = logging.getLogger("pomona")
    stdoutLog = logging.getLogger("pomona.stdout")
    if os.access("/dev/tty3", os.W_OK):
        logger.addFileHandler("/dev/tty3", log)

    log.info("pomona called with cmdline = %s" %(sys.argv,))

    ### Set up environment
    #
    setupEnvironment()

    ### Set up i18n
    #
    from pyfire.translate import _, textdomain
    textdomain("pomona")

    ### Reading command line options
    #
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

    instClass = getInstClass()

    checkMemory()

    from tui import InstallInterface
    pomona.intf = InstallInterface()

    import warnings, signal
    warnings.showwarning = PomonaShowWarning

    # reset python's default SIGINT handler
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    pomona.setBackend()

    pomona.id = instClass.installDataClass(pomona)
    instClass.setInstallData(pomona)
    users.createLuserConf(pomona.rootPath)

    pomona.setDispatch()

    #if opts.lang:
    #       anaconda.dispatch.skipStep("language", permanent = 1)
    #       instClass.setLanguage(anaconda.id, opts.lang)
    #       instClass.setLanguageDefault(anaconda.id, opts.lang)
    #       anaconda.id.timezone.setTimezoneInfo(anaconda.id.instLanguage.getDefaultTimeZone())

    #if opts.keymap:
    #       anaconda.dispatch.skipStep("keyboard", permanent = 1)
    #       instClass.setKeyboard(anaconda.id, opts.keymap)

    from exception import handleException
    sys.excepthook = lambda type, value, tb, pomona=pomona: handleException(pomona, (type, value, tb))

    try:
        pomona.intf.run(pomona)
    except SystemExit, code:
        pomona.intf.shutdown()
    except:
        handleException(pomona, sys.exc_info())

    del pomona.intf
