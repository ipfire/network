
from snack import *
import sys, os
import isys
import parted
import signal
import inutil
import imputil
from pyfire.translate import _, cat, N_
from constants import *

import logging
log = logging.getLogger("pomona")

stepToClasses = {
                "accounts" : ("tui_userauth", "RootPasswordWindow"),
                "bootloader" : ("tui_bootloader", ("BootloaderChoiceWindow",
                                                   "BootloaderAppendWindow",
                                                   "BootloaderPasswordWindow")),
                "bootloaderadvanced" : ("tui_bootloader", ("BootloaderImagesWindow",
                                                           "BootloaderLocationWindow")),
                "complete" : ("tui_complete", "FinishedWindow"),
                "confirminstall" : ("tui_confirm", "BeginInstallWindow"),
                "install"  : ("tui_progress", "setupForInstall"),
                "keyboard" : ("tui_keyboard", "KeyboardWindow"),
                "language" : ("tui_language", "LanguageWindow"),
                "network"  : ("tui_network", "HostnameWindow"),
                "partition": ("tui_partition", "PartitionWindow"),
                "parttype" : ("tui_partition", "PartitionTypeWindow"),
                "timezone" : ("tui_timezone", "TimezoneWindow"),
                "welcome"  : ("tui_welcome", "WelcomeWindow"),
}

class WaitWindow:
    def pop(self):
        self.screen.popWindow()
        self.screen.refresh()

    def refresh(self):
        self.screen.refresh()

    def set_text(self, text):
        self.t.setText(text)
        self.g.draw()
        self.screen.refresh()

    def __init__(self, screen, title, text, width):
        self.screen = screen
        if width is None:
            width = 40
            if (len(text) < width):
                width = len(text)

        self.t = TextboxReflowed(width, text)

        self.g = GridForm(self.screen, title, 1, 1)
        self.g.add(self.t, 0, 0)
        self.g.draw()
        self.screen.refresh()

class ProgressWindow:
    def pop(self):
        self.screen.popWindow()
        self.screen.refresh()
        del self.scale
        self.scale = None

    def set(self, amount):
        self.scale.set(int(float(amount) * self.multiplier))
        self.screen.refresh()

    def refresh(self):
        pass

    def __init__(self, screen, title, text, total, updpct = 0.05):
        self.multiplier = 1
        if total == 1.0:
            self.multiplier = 100
        self.screen = screen
        width = 55
        if (len(text) > width): width = len(text)

        t = TextboxReflowed(width, text)

        g = GridForm(self.screen, title, 1, 2)
        g.add(t, 0, 0, (0, 0, 0, 1), anchorLeft=1)

        self.scale = Scale(int(width), int(float(total) * self.multiplier))
        g.add(self.scale, 0, 1)

        g.draw()
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

class ExceptionWindow:
    def __init__ (self, shortTraceback, longTracebackFile=None, screen=None):
        self.text = "%s\n\n" % shortTraceback
        self.screen = screen

        self.buttons=[TEXT_OK_BUTTON]

    def run(self):
        log.info ("in run, screen = %s" % self.screen)
        self.rc = ButtonChoiceWindow(self.screen, _("Exception Occurred"),
                                                  self.text, self.buttons)

    def getrc(self):
        return 0

    def pop(self):
        self.screen.popWindow()
        self.screen.refresh()

class InstallInterface:
    def __init__(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)
        log.info("Starting the TUI...")
        self.screen = SnackScreen()
        self.showingHelpOnHelp = 0

    def __del__(self):
        if self.screen:
            self.screen.finish()

    def shutdown(self):
        log.info("Shutting down the TUI...")
        self.screen.finish()
        self.screen = None

    def run(self, pomona):
        self.console = pomona.id.console

        self.screen.helpCallback(self.helpWindow)

        if not self.isRealConsole():
            self.screen.suspendCallback(spawnShell, self.screen)

        # draw the frame after setting up the fallback
        self.drawFrame()

        pomona.id.fsset.registerMessageWindow(self.messageWindow)
        pomona.id.fsset.registerProgressWindow(self.progressWindow)
        pomona.id.fsset.registerWaitWindow(self.waitWindow)

        parted.exception_set_handler(self.partedExceptionWindow)

        lastrc = INSTALL_OK
        (step, instance) = pomona.dispatch.currentStep()
        while step:
            (file, classNames) = stepToClasses[step]

            if type(classNames) != type(()):
                classNames = (classNames,)

            if lastrc == INSTALL_OK:
                step = 0
            else:
                step = len(classNames) - 1

            while step >= 0 and step < len(classNames):
                # reget the args.  they could change (especially direction)
                (foo, args) = pomona.dispatch.currentStep()
                nextWindow = None

                while 1:
                    try:
                        found = imputil.imp.find_module(file)
                        loaded = imputil.imp.load_module(classNames[step],
                                                         found[0], found[1],
                                                         found[2])
                        nextWindow = loaded.__dict__[classNames[step]]
                        break
                    except ImportError, e:
                        rc = ButtonChoiceWindow(self.screen, _("Error!"),
                                                             _("An error occurred when attempting "
                                                               "to load an pomona interface "
                                                               "component.\n\nclassName = %s\n\n"
                                                               "Error: %s")
                                                             % (classNames[step],e),
                                                                buttons=[_("Exit"), _("Retry")])

                        if rc == string.lower(_("Exit")):
                            sys.exit(0)

                win = nextWindow()

                #log.info("TUI running step %s (class %s, file %s)" % (step, classNames, file))

                rc = win(self.screen, instance)

                if rc == INSTALL_NOOP:
                    rc = lastrc

                if rc == INSTALL_BACK:
                    step = step - 1
                    pomona.dispatch.dir = DISPATCH_BACK
                elif rc == INSTALL_OK:
                    step = step + 1
                    pomona.dispatch.dir = DISPATCH_FORWARD

                lastrc = rc

            if step == -1:
                if not pomona.dispatch.canGoBack():
                    ButtonChoiceWindow(self.screen, _("Cancelled"),
                                                    _("I can't go to the previous step "
                                                      "from here. You will have to try "
                                                      "again."),
                                                    buttons=[_("OK")])
                pomona.dispatch.gotoPrev()
            else:
                pomona.dispatch.gotoNext()

            (step, args) = pomona.dispatch.currentStep()

        self.screen.finish()

    def drawFrame(self):
        self.screen.drawRootText (0, 0, self.screen.width * " ")
        self.screen.drawRootText (0, 0, _("Welcome to %s") % name)

        if (os.access("/usr/share/pomona/help/C/s1-help-screens-lang.txt", os.R_OK)):
            self.screen.pushHelpLine(_(" <F1> for help | <Tab> between elements | <Space> selects | <F12> next screen"))
        else:
            self.screen.pushHelpLine(_("  <Tab>/<Alt-Tab> between elements   |  <Space> selects   |  <F12> next screen"))

    def setScreen(self, screen):
        self.screen = screen

    def beep(self):
        # no-op. could call newtBell() if it was bound
        pass

    def isRealConsole(self):
        """Returns True if this is a _real_ console that can do things, False
        for non-real consoles such as serial, i/p virtual consoles or xen."""
        #if flags.serial or flags.virtpconsole:
        #       return False
        if isys.isPsudoTTY(0):
            return False
        if isys.isVioConsole():
            return False
        if os.path.exists("/proc/xen"): # this keys us that we're a xen guest
            return False
        return True

    def helpWindow(self, screen, key):
        if key == "helponhelp":
            if self.showingHelpOnHelp:
                return None
            else:
                self.showingHelpOnHelp = 1
        try:
            f = None
            found = 0
            for path in ("./text-", "/usr/share/pomona/"):
                if found:
                    break
                for lang in self.console.getCurrentLangSearchList():
                    for tag in tags:
                        fn = "%shelp/%s/s1-help-screens-%s%s.txt" % (path, lang, key, tag)
                        try:
                            f = open(fn)
                        except IOError, msg:
                            continue
                        found = 1
                        break

            if not f:
                ButtonChoiceWindow(screen, _("Help not available"),
                                           _("No help is available for this "
                                             "step of the install."),
                                           buttons=[TEXT_OK_BUTTON])
                return None

            lines = f.readlines()
            for l in lines:
                l = l.replace("@IPFIRE@", name)
                l = l.replace("@VERSION@", version)
                while not string.strip(l[0]):
                    l = l[1:]
                    title = string.strip(l[0])
                    l = l[1:]
                while not string.strip(l[0]):
                    l = l[1:]
            f.close()

            height = 10
            scroll = 1
            if len(l) < height:
                height = len(l)
                scroll = 0

            width = len(title) + 6
            stream = ""
            for line in l:
                line = string.strip(line)
                stream = stream + line + "\n"
                if len(line) > width:
                    width = len(line)

            bb = ButtonBar(screen, [TEXT_OK_BUTTON])
            t = Textbox(width, height, stream, scroll=scroll)

            g = GridFormHelp(screen, title, "helponhelp", 1, 2)
            g.add(t, 0, 0, padding=(0, 0, 0, 1))
            g.add(bb, 0, 1, growx=1)

            g.runOnce()
            self.showingHelpOnHelp = 0
        except:
            import traceback
            (type, value, tb) = sys.exc_info()
            from string import joinfields
            list = traceback.format_exception(type, value, tb)
            text = joinfields(list, "")
            win = self.exceptionWindow(text)
            win.run()
            rc = win.getrc()
            if rc == 0:
                os._exit(1)

    def progressWindow(self, title, text, total, updpct = 0.05):
        return ProgressWindow(self.screen, title, text, total, updpct)

    def waitWindow(self, title, text, width=None):
        return WaitWindow(self.screen, title, text, width)

    def exceptionWindow(self, shortText, longTextFile):
        log.critical(shortText)
        exnWin = ExceptionWindow(shortText, longTextFile, self.screen)
        return exnWin

    def messageWindow(self, title, text, type="ok", default = None,
                      custom_icon=None, custom_buttons=[]):
        if type == "ok":
            ButtonChoiceWindow(self.screen, title, text,
                               buttons=[TEXT_OK_BUTTON])
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

    def partedExceptionWindow(self, exc):
        # if our only option is to cancel, let us handle the exception
        # in our code and avoid popping up the exception window here.
        if exc.options == parted.EXCEPTION_CANCEL:
            return parted.EXCEPTION_UNHANDLED
        log.critical("parted exception: %s: %s" %(exc.type_string,exc.message))
        buttons = []
        buttonToAction = {}
        flags = ((parted.EXCEPTION_FIX, N_("Fix")),
                                         (parted.EXCEPTION_YES, N_("Yes")),
                                         (parted.EXCEPTION_NO, N_("No")),
                                         (parted.EXCEPTION_OK, N_("OK")),
                                         (parted.EXCEPTION_RETRY, N_("Retry")),
                                         (parted.EXCEPTION_IGNORE, N_("Ignore")),
                                         (parted.EXCEPTION_CANCEL, N_("Cancel")))
        for flag, errorstring in flags:
            if exc.options & flag:
                buttons.append(_(errorstring))
                buttonToAction[string.lower(_(errorstring))] = flag

        rc = None
        while not buttonToAction.has_key(rc):
            rc = ButtonChoiceWindow(self.screen, exc.type_string, exc.message,
                                    buttons=buttons)

        return buttonToAction[rc]

def spawnShell(screen):
    screen.suspend()
    print "\n\nType <exit> to return to the install program.\n"
    if os.path.exists("/bin/sh"):
        inutil.execConsole()
    else:
        print "Unable to find /bin/sh to execute!  Not starting shell"
    time.sleep(5)
    screen.resume()
