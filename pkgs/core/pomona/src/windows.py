#!/usr/bin/python

import sys

from snack import *
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

def welcomeWindow(installer):
    rc = installer.intf.messageWindow(_("%s") % PRODUCT_NAME,
                                      _("Welcome to %s-v%s!\n\n") % (PRODUCT_NAME, PRODUCT_VERSION,))
    return DISPATCH_FORWARD

def experimentalWindow(installer):
    if installer.dispatch.dir == DISPATCH_BACK:
        return DISPATCH_NOOP

    # Check if we are running a pre-release version
    version = PRODUCT_VERSION
    if not version.find("alpha") and \
             not version.find("beta")  and \
             not version.find("rc"):
        return DISPATCH_NOOP

    while 1:
        rc = installer.intf.messageWindow( _("Warning! This is pre-release software!"),
                                           _("Thank you for downloading this "
                                             "pre-release of %s.\n\n"
                                             "This is not a final "
                                             "release and is not intended for use "
                                             "on production systems. The purpose of "
                                             "this release is to collect feedback "
                                             "from testers, and it is not suitable "
                                             "for day to day usage.\n\n"
                                             "To report feedback, please visit:\n\n"
                                             "   %s\n\n"
                                             "and file a report.\n")
                                            % (PRODUCT_NAME, PRODUCT_URL),
                                           type="custom", custom_buttons=[_("_Exit"), _("_Install anyway")])

        if not rc:
            rc = installer.intf.messageWindow(_("Rebooting System"),
                         _("Your system will now be rebooted..."),
                         type="custom", custom_buttons=[_("_Back"), _("_Reboot")])
            if rc:
                sys.exit(0)
        else:
            break

def finishedWindow(installer):
    installer.intf.setHelpline(_("Press <Enter> to exit"))

    rc = installer.intf.messageWindow(_("Complete"),
                                      _("Congratulations, your %s installation is "
                                        "complete.\n\n"
                                        "Press <Enter> to end the installation process.\n\n"
                                        "For information on errata (updates and bug fixes), visit "
                                        "%s.\n\n") % (PRODUCT_NAME, PRODUCT_URL,),
                                      type="custom", custom_buttons=[_("Reboot")])

    return INSTALL_OK

def partmethodWindow(installer):
    storage = installer.ds.storage

    if storage.checkNoDisks():
        sys.exit(0)
    
    # Resetting options
    storage.doAutoPart = False
#    installer.dispatch.skipStep("partition", skip=0)

    methods = [ _("Automatic partitioning"), _("Custom partitioning"),]
    default = methods[0] # first should be autopartitioning

    (button, choice) = ListboxChoiceWindow(installer.intf.screen,
                       _("Partition Method"),
                       _("Installation requires partitioning of your hard drive. "
                         "The default option is suitable for most users. "
                         "You can also choose to create your own custom layout."),
                       methods, buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                       width = 60, default=default, height = len(methods))

    if button == TEXT_BACK_CHECK:
        return INSTALL_BACK
    
    if choice == 0:
        installer.ds.storage.doAutoPart = True
        #installer.dispatch.skipStep("partition", skip=1)

    installer.log.info("User has chosen \"%s\"" % methods[choice])

    return INSTALL_OK

def autopartitionWindow(installer):
    storage = installer.ds.storage
    while 1:
        g = GridForm(installer.intf.screen, _("Device Selection"), 1, 6)
        txt = TextboxReflowed(65, _("Which drive(s) do you want to use for this installation?\n\n"
                                    "ALL DATA stored on the devices will be destroyed."))
        g.add(txt, 0, 0, (0, 0, 0, 0))
        
        drivelist = CheckboxTree(height=4, scroll=1)
        g.add(drivelist, 0, 4, (0, 1, 0, 0))
        
        bb = ButtonBar(installer.intf.screen, [ TEXT_OK_BUTTON, TEXT_BACK_BUTTON ])
        g.add(bb, 0, 5, (0,1,0,0))

        for disk in storage.disks:
                if not storage.clearDisks or len(storage.clearDisks) < 1:
                    selected = 1
                else:
                    if disk in storage.clearDisks: # XXX never matches...
                        selected = 1
                    else:
                        selected = 0

                diskdesc = "%6s %8.0f MB (%s)" % (disk.name, disk.size, disk.model[:24],)

                drivelist.append(diskdesc, selected = selected)
        
        rc = g.run()
        
        installer.intf.screen.popWindow()
        
        if bb.buttonPressed(rc) == TEXT_BACK_CHECK:
            return INSTALL_BACK

        if len(drivelist.getSelection()) > 0:
            storage.clearDisks = map(lambda s: s.split()[0], drivelist.getSelection())
        else:
            storage.clearDisks = []
            installer.intf.messageWindow(_("No Drives Selected"),
                                         _("An error has occurred - no valid devices were "
                                           "selected on which to create the new file system. "
                                           "For the installation of %s, "
                                           "you have to select at least one drive.") % PRODUCT_NAME,
                                         type="ok")
            
            continue

        installer.log.info("User selected \"%s\"" % storage.clearDisks)
        break

    return INSTALL_OK

def reviewlayoutWindow(installer):
    if installer.dispatch.dir == DISPATCH_BACK:
        return DISPATCH_NOOP

    rc = installer.intf.messageWindow(_("Review Partition Layout"),
                                      _("Review and modify partitioning layout?"),
                                      type = "yesno")
    if rc != 1:
        #installer.dispatch.skipStep("partition", skip=1)
        pass

    return INSTALL_OK

def bootloaderWindow(installer):
    bootloaders = [ _("Use Grand unified bootloader"), _("Install no bootloader"),]
    default = bootloaders[0] # first should a bootloader
    
    (button, choice) = ListboxChoiceWindow(installer.intf.screen,
                       _("Bootloader"),
                       _("Which bootloader do you want to install?\n\n"
                         "NOTE: If you don't choose a bootloader the system "
                         "might not be bootable!"),
                       bootloaders, buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                       width = 60, default=default, height = len(bootloaders))

    if button == TEXT_BACK_CHECK:
        return INSTALL_BACK

    installer.log.info("User has chosen \"%s\"" % bootloaders[choice])
    # XXX skip step installbootloader here

    return INSTALL_OK
