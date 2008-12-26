#
# instdata.py - central store for all configuration data needed to install
#
# Erik Troan <ewt@redhat.com>
#
# Copyright 2001-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os
import string
import language
import keyboard
import network
import timezone
import fsset
import bootloader
import partitions
import partedUtils
import users
from flags import *
from constants import *

import logging
log = logging.getLogger("pomona")

# Collector class for all data related to an install.

class InstallData:
    def reset(self, pomona):
        # Reset everything except:
        #
        #       - The install language
        #       - The keyboard

        self.instClass = None
        self.network = network.Network()
        self.timezone = timezone.Timezone()
        self.timezone.setTimezoneInfo(self.instLanguage.getDefaultTimeZone())
        self.users = None
        self.rootPassword = { "password": "" }
        self.fsset.reset()
        self.diskset = partedUtils.DiskSet(pomona)
        self.partitions = partitions.Partitions()
        self.bootloader = bootloader.getBootloader()
        self.rootParts = None

    def setInstallProgressClass(self, c):
        self.instProgress = c

    # expects a Keyboard object
    def setKeyboard(self, keyboard):
        self.keyboard = keyboard

    def write(self, pomona):
        self.instLanguage.write(pomona.rootPath)
        self.keyboard.write(pomona.rootPath)
        #self.timezone.write(pomona.rootPath)
        self.network.write(pomona.rootPath)

        self.users = users.Users()

        # User should already exist, just without a password.
        self.users.setRootPassword(self.rootPassword["password"], algo="sha512")

    def __init__(self, pomona):
        self.instLanguage = language.Language()
        self.keyboard = keyboard.Keyboard()
        self.fsset = fsset.FileSystemSet()
        self.reset(pomona)
