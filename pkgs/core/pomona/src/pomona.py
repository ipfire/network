#!/usr/bin/python

import imputil
import os
import sys

from datastore import DataStore
from dispatch import Dispatcher
from exception import handleException
from text import TextInterface
from log import Logger

from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

class Installer:
    def __init__(self):
        self.log = Logger()

        self.dispatch = None
        self.ds = None
        self.intf = TextInterface(self.log)
        self.window = None

    def __call__(self):
        if self.window:
            self.window.pop()

        step = self.dispatch.nextStep()
        while step:
            self.log.info("")
            self.log.info("---------- Running step \"%s\" ----------" % step[0])

            if type(step[1]) == type(_):
                (name, function) = step
                self.log.debug("\"%s\" is called directly (%s)" % (name, function,))
                rc = function(self)
                if rc in [DISPATCH_BACK, DISPATCH_FORWARD]:
                    self.dispatch.dir = rc
            else:
                (file, classes) = step
                substep = 0
                while substep < len(classes):
                    while 1:
                        try:
                            found = imputil.imp.find_module(file)
                            loaded = imputil.imp.load_module(classes[substep],
                                                             found[0], found[1],
                                                             found[2])
                            nextWindow = loaded.__dict__[classes[substep]]
                            break
                        except ImportError, e:
                            rc = self.intf.messageWindow(_("Error!"),
                                                         _("An error occurred when attempting "
                                                           "to load an pomona interface "
                                                           "component.\n\nclassName = %s\n\n"
                                                           "Error: %s") % (classes[substep],e),
                                                         type="custom", custom_buttons=[_("Exit"), _("Retry")])
                            if rc == 0:
                                sys.exit(0)

                    self.window = nextWindow()
                    rc = self.window(self)

                    #if rc == INSTALL_NOOP:
                    #    rc = lastrc

                    if rc == INSTALL_BACK:
                        #step = step - 1
                        self.dispatch.dir = DISPATCH_BACK
                    elif rc == INSTALL_OK:
                        #step = step + 1
                        self.dispatch.dir = DISPATCH_FORWARD

                    substep += 1

            step = self.dispatch.nextStep()



if __name__ == "__main__":
    # Set up environment
    if not os.environ.has_key("LANG"):
        os.environ["LANG"] = "en_US.UTF-8"
    os.environ['HOME'] = '/tmp'
    os.environ['LC_NUMERIC'] = 'C'

    installer = Installer()

    sys.excepthook = lambda type, value, tb, installer=installer: \
        handleException(installer, (type, value, tb))

    # Display some information
    installer.window = \
        installer.intf.waitWindow(_("Installer"), _("Setting up installer..."),)
    installer.log.info("Going on to install %s-v%s (%s)..." % \
            (PRODUCT_NAME, PRODUCT_VERSION, PRODUCT_SLOGAN,))

    # Applying classes to installer
    installer.dispatch = Dispatcher(installer)
    installer.ds = DataStore(installer)

    try:
        installer()
    except SystemExit, code:
        pass
    except:
        handleException(installer, sys.exc_info())

    del installer.intf
    del installer
