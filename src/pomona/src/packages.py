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

import inutil
import isys
import os
import sys
import fsset
import shutil
from flags import flags
from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

def doPostAction(pomona):
    pomona.id.instClass.postAction(pomona, flags.serial)

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

def turnOnFilesystems(pomona):
    if pomona.dir == DISPATCH_BACK:
        log.info("unmounting filesystems")
        pomona.id.fsset.umountFilesystems(pomona.rootPath)
        return

    #pomona.id.partitions.doMetaDeletes(pomona.id.diskset)
    pomona.id.diskset.clearDevices()
    pomona.id.fsset.setActive(pomona.id.diskset)
    if not pomona.id.fsset.isActive():
        pomona.id.diskset.savePartitions()
    pomona.id.fsset.checkBadblocks(pomona.rootPath)
    pomona.id.fsset.formatSwap(pomona.rootPath)
    pomona.id.fsset.turnOnSwap(pomona.rootPath)
    pomona.id.fsset.makeFilesystems(pomona.rootPath)
    pomona.id.fsset.mountFilesystems(pomona)

def setupTimezone(pomona):
    # we don't need this going backwards
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
    elif pomona.id.timezone.arc:
        #args.append("-a")
        args.append("-l")

    try:
        inutil.execWithRedirect("/sbin/hwclock", args, stdin = None,
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
                                                                                                                                        %(name, bugurl, name),
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
