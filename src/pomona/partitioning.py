#
# partitioning.py: partitioning and other disk management
#
# Matt Wilson <msw@redhat.com>
# Jeremy Katz <katzj@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Harald Hoyer <harald@redhat.de>
#
# Copyright 2001-2003 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import isys
import sys
import inutil
from constants import *
from flags import flags
from partErrors import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

def partitionObjectsInitialize(pomona):
    # read in drive info
    pomona.id.diskset.refreshDevices()
    pomona.id.partitions.setFromDisk(pomona.id.diskset)

def partitioningComplete(pomona):
    if pomona.dir == DISPATCH_BACK and pomona.id.fsset.isActive():
        rc = pomona.intf.messageWindow(_("Installation cannot continue."),
                                       _("The partitioning options you have chosen "
                                         "have already been activated. You can "
                                         "no longer return to the disk editing "
                                         "screen. Would you like to continue "
                                         "with the installation process?"),
                                        type = "yesno")
        if rc == 0:
            sys.exit(0)
        return DISPATCH_FORWARD

    pomona.id.partitions.sortRequests()
    pomona.id.fsset.reset()
    for request in pomona.id.partitions.requests:
        # XXX improve sanity checking
        if (not request.fstype or (request.fstype.isMountable()
                        and not request.mountpoint)):
            continue

        entry = request.toEntry(pomona.id.partitions)
        if entry:
            pomona.id.fsset.add(entry)
        else:
            raise RuntimeError, ("Managed to not get an entry back from "
                                 "request.toEntry")

    if inutil.memAvailable() > isys.EARLY_SWAP_RAM:
        return

    rc = pomona.intf.messageWindow(_("Low Memory"),
                                   _("As you don't have much memory in this "
                                     "machine, we need to turn on swap space "
                                     "immediately. To do this we'll have to "
                                     "write your new partition table to the disk "
                                     "immediately. Is that OK?"), "yesno")

    if rc:
        pomona.id.diskset.clearDevices()
        pomona.id.fsset.setActive(pomona.id.diskset)
        pomona.id.diskset.savePartitions()
        pomona.id.fsset.formatSwap(pomona.rootPath)
        pomona.id.fsset.turnOnSwap(pomona.rootPath)

    return
