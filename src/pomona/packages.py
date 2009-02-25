#
# packages.py: package management - mainly package installation
#
# Erik Troan <ewt@redhat.com>
# Matt Wilson <msw@redhat.com>
# Michael Fulbright <msf@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2001-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import iutil
import isys
import os
import sys
import fsset
import shutil
import time
import lvm
from flags import flags
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

import logging
log = logging.getLogger("pomona")

def doPostAction(pomona):
    pomona.backend.postAction(pomona)

def copyPomonaLogs(pomona):
    log.info("Copying pomona logs")
    for (fn, dest) in (("/root/pomona.log", "pomona.log"),
                       ("/tmp/syslog", "pomona.syslog")):
        if os.access(fn, os.R_OK):
            try:
                shutil.copyfile(fn, "%s/var/log/%s" %(pomona.rootPath, dest))
                os.chmod("%s/var/log/%s" %(pomona.rootPath, dest), 0600)
            except:
                pass

def doMigrateFilesystems(pomona):
    if pomona.dir == DISPATCH_BACK:
        return DISPATCH_NOOP

    if pomona.id.fsset.haveMigratedFilesystems():
        return DISPATCH_NOOP

    pomona.id.fsset.migrateFilesystems (pomona)

def turnOnFilesystems(pomona):
    def handleResizeError(e, dev):
        if os.path.exists("/tmp/resize.out"):
            details = open("/tmp/resize.out", "r").read()
        else:
            details = "%s" %(e,)
        pomona.intf.detailedMessageWindow(_("Resizing Failed"),
                                            _("There was an error encountered "
                                            "resizing the device %s.") %(dev,),
                                            details,
                                            type = "custom",
                                            custom_buttons = [_("_Exit installer")])
        sys.exit(1)

    if pomona.dir == DISPATCH_BACK:
        log.info("unmounting filesystems")
        pomona.id.fsset.umountFilesystems(pomona.rootPath)
        return

    if not pomona.id.fsset.isActive():
        # turn off any swaps that we didn't turn on
        # needed for live installs
        iutil.execWithRedirect("swapoff", ["-a"],
                               stdout = "/dev/tty5", stderr="/dev/tty5",
                               searchPath = 1)
    pomona.id.partitions.doMetaDeletes(pomona.id.diskset)
    pomona.id.fsset.setActive(pomona.id.diskset)
    try:
        pomona.id.fsset.shrinkFilesystems(pomona.id.diskset, pomona.rootPath)
    except fsset.ResizeError, (e, dev):
        handleResizeError(e, dev)

    if not pomona.id.fsset.isActive():
        pomona.id.diskset.savePartitions()
        # this is somewhat lame, but we seem to be racing with
        # device node creation sometimes.  so wait for device nodes
        # to settle
        w = pomona.intf.waitWindow(_("Activating"), _("Activating new partitions.  Please wait..."))
        time.sleep(1)
        rc = iutil.execWithRedirect("/sbin/udevadm", [ "settle" ],
                                    stdout = "/dev/tty5",
                                    stderr = "/dev/tty5",
                                    searchPath = 1)
        w.pop()

        pomona.id.partitions.doEncryptionRetrofits()

        try:
            pomona.id.partitions.doMetaResizes(pomona.id.diskset)
        except lvm.LVResizeError, e:
            handleResizeError("%s" %(e,), "%s/%s" %(e.vgname, e.lvname))

    try:
        pomona.id.fsset.growFilesystems(pomona.id.diskset, pomona.rootPath)
    except fsset.ResizeError, (e, dev):
        handleResizeError(e, dev)

    if not pomona.id.fsset.volumesCreated:
        try:
            pomona.id.fsset.createLogicalVolumes(pomona.rootPath)
        except SystemError, e:
            log.error("createLogicalVolumes failed with %s", str(e))
            pomona.intf.messageWindow(_("LVM operation failed"),
                                str(e)+"\n\n"+_("The installer will now exit..."),
                                type="custom", custom_icon="error", custom_buttons=[_("_Reboot")])
            sys.exit(0)

    pomona.id.fsset.formatSwap(pomona.rootPath)
    pomona.id.fsset.turnOnSwap(pomona.rootPath)
    pomona.id.fsset.makeFilesystems(pomona.rootPath,
                                      pomona.backend.skipFormatRoot)
    pomona.id.fsset.mountFilesystems(pomona,0,0,
                                       pomona.backend.skipFormatRoot)

def setupTimezone(pomona):
    # we don't need this on going backwards
    if pomona.dir == DISPATCH_BACK:
        return

    os.environ["TZ"] = pomona.id.timezone.tz
    tzfile = "/usr/share/zoneinfo/" + pomona.id.timezone.tz
    if not os.access(tzfile, os.R_OK):
        log.error("unable to set timezone")
    else:
        try:
            shutil.copyfile(tzfile, "/etc/localtime")
        except OSError, (errno, msg):
            log.error("Error copying timezone (from %s): %s" %(tzfile, msg))

    args = [ "--hctosys" ]
    if pomona.id.timezone.utc:
        args.append("-u")

    try:
        iutil.execWithRedirect("/usr/sbin/hwclock", args, stdin = None,
                               stdout = "/dev/tty5", stderr = "/dev/tty5")
    except RuntimeError:
        log.error("Failed to set clock")

def betaNagScreen(pomona):
    if pomona.dir == DISPATCH_BACK:
        return DISPATCH_NOOP

    ### Check if we run a pre-release version
    if not version.find("alpha") and \
             not version.find("beta")  and \
             not version.find("rc"):
        return DISPATCH_NOOP

    while 1:
        rc = pomona.intf.messageWindow( _("Warning! This is pre-release software!"),
                                        _("Thank you for downloading this "
                                          "pre-release of %s.\n\n"
                                          "This is not a final "
                                          "release and is not intended for use "
                                          "on production systems.  The purpose of "
                                          "this release is to collect feedback "
                                          "from testers, and it is not suitable "
                                          "for day to day usage.\n\n"
                                          "To report feedback, please visit:\n\n"
                                          "   %s\n\n"
                                          "and file a report against '%s'.\n")
                                        % (name, bugurl, name),
                                           type="custom", custom_icon="warning",
                                           custom_buttons=[_("_Exit"), _("_Install anyway")])

        if not rc:
            msg =  _("Your system will now be rebooted...")
            buttons = [_("_Back"), _("_Reboot")]
            rc = pomona.intf.messageWindow(_("Rebooting System"),
                         msg,
                         type="custom", custom_icon="warning",
                         custom_buttons=buttons)
            if rc:
                sys.exit(0)
        else:
            break
