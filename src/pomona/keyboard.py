#
# keyboard.py - keyboard backend data object
#
# Brent Fox <bfox@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2002 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import string
import os
import pyfire.executil as executil
from pyfire.config import ConfigFile
import keyboard_models

class Keyboard(ConfigFile):
    def __init__(self):
        self.type = "PC"
        self.beenset = 0
        self.info = {}

        # default to us
        self.info["KEYTABLE"] = "us"
        self.info["KEYBOARDTYPE"] = "pc"

        self._mods = keyboard_models.KeyboardModels()

    def _get_models(self):
        return self._mods.get_models()

    modelDict = property(_get_models)

    def set(self, keytable):
        self.info["KEYTABLE"] = keytable

    def get(self):
        return self.info["KEYTABLE"]

    def getKeymapName(self):
        kbd = self.modelDict[self.get()]
        if not kbd:
            return ""
        (name, layout, model, variant, options) = kbd
        return name

    def __getitem__(self, item):
        table = self.info["KEYTABLE"]
        if not self.modelDict.has_key(table):
            raise KeyError, "No such keyboard type %s" % (table,)

        kb = self.modelDict[table]
        if item == "rules":
            return "xorg"
        elif item == "model":
            return kb[2]
        elif item == "layout":
            return kb[1]
        elif item == "variant":
            return kb[3]
        elif item == "options":
            return kb[4]
        elif item == "name":
            return kb[0]
        elif item == "keytable":
            return table
        else:
            raise KeyError, item

    #def read(self, instPath = "/"):
    #       ConfigFile.read(self, instPath + "/etc/sysconfig/keyboard")
    #       self.beenset = 1

    def write(self, instPath = "/"):
        ConfigFile.write(self, instPath + "/etc/sysconfig/keyboard")

    def activate(self):
        console_kbd = self.get()
        if not console_kbd:
            return

        # Call loadkeys to change the console keymap
        if os.access("/bin/loadkeys", os.X_OK):
            command = "/bin/loadkeys"
        elif os.access("/usr/bin/loadkeys", os.X_OK):
            command = "/usr/bin/loadkeys"
        else:
            command = "/bin/loadkeys"
        argv = [ command, console_kbd ]

        ### XXX Don't run this at the moment because redirect doesn't work
        if os.access(argv[0], os.X_OK) == 1:
            executil.execWithRedirect(argv[0], argv, stdout="/dev/tty5", stderr="/dev/tty5")
