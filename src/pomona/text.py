#!/usr/bin/python

import string

from snack import *
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

class TextWindow:
    def __init__(self, screen):
        self.screen = screen

    def pop(self):
        self.screen.popWindow()
        self.screen.refresh()

    def refresh(self):
        self.screen.refresh()


class WaitWindow(TextWindow):
    def setText(self, text):
        self.t.setText(text)
        self.g.draw()
        self.screen.refresh()

    def __init__(self, screen, title, text, width):
        TextWindow.__init__(self, screen)

        if width is None:
            width = 40
            if (len(text) < width):
                width = len(text)

        self.t = TextboxReflowed(width, text)

        self.g = GridForm(self.screen, title, 1, 1)
        self.g.add(self.t, 0, 0)
        self.g.draw()
        self.screen.refresh()


class OkCancelWindow:
    def getrc(self):
        return self.rc

    def __init__(self, screen, title, text):
        rc = ButtonChoiceWindow(screen, title, text, buttons=[TEXT_OK_BUTTON, _("Cancel")])
        if rc == string.lower(_("Cancel")):
            self.rc = 1
        else:
            self.rc = 0


class ExceptionWindow(TextWindow):
    def __init__ (self, short, long=None, screen=None):
        TextWindow.__init__(self, screen)
        self.text = "%s\n\n" % short
        self.buttons=[TEXT_OK_BUTTON]

    def run(self):
        self.rc = ButtonChoiceWindow(self.screen, _("Exception Occurred"),
                                                  self.text, self.buttons, width=60)

    def getrc(self):
        return 0


class TextInterface:
    def __init__(self, log):
        self.log    = log
        self.screen = SnackScreen()

        self.setRootline(SCREEN_ROOTLINE)
        self.setHelpline(SCREEN_HELPLINE)

    def __del__(self):
        if self.screen:
            self.screen.finish()

    def setRootline(self, msg):
        self.screen.drawRootText (0, 0, string.center(msg, self.screen.width))
        self.log.debug("Set rootline text: %s" % msg)

    def setHelpline(self, msg):
        self.screen.pushHelpLine(string.center(msg, self.screen.width))
        self.log.debug("Set helpline text: %s" % msg)


    ### WINDOW DEFINITIONS ###

    def waitWindow(self, title, text, width=None):
        return WaitWindow(self.screen, title, text, width)

    def exceptionWindow(self, short, long):
        self.log.critical(short)
        return ExceptionWindow(short, long, self.screen)

    def messageWindow(self, title, text, type="ok", default = None,
                      custom_icon=None, custom_buttons=[]):
        if type == "ok":
            ButtonChoiceWindow(self.screen, title, text, buttons=[TEXT_OK_BUTTON])

        elif type == "yesno":
            if default and default == "no":
                btnlist = [TEXT_NO_BUTTON, TEXT_YES_BUTTON]
            else:
                btnlist = [TEXT_YES_BUTTON, TEXT_NO_BUTTON]
            rc = ButtonChoiceWindow(self.screen, title, text, buttons=btnlist)
            if rc == "yes":
                return 1
            else:
                return 0

        elif type == "custom":
            tmpbut = []
            for but in custom_buttons:
                tmpbut.append(string.replace(but,"_",""))
            rc = ButtonChoiceWindow(self.screen, title, text, width=60, buttons=tmpbut)

            idx = 0
            for b in tmpbut:
                if string.lower(b) == rc:
                    return idx
                idx = idx + 1
            return 0

        else:
            return OkCancelWindow(self.screen, title, text)
