#
# flags.py: global pomona flags
#
# Copyright 2001 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import os
import shlex
from constants import *

# A lot of effort, but it only allows a limited set of flags to be referenced
class Flags:
    def __getattr__(self, attr):
        if self.__dict__['flags'].has_key(attr):
            return self.__dict__['flags'][attr]
        raise AttributeError, attr

    def __setattr__(self, attr, val):
        if self.__dict__['flags'].has_key(attr):
            self.__dict__['flags'][attr] = val
        else:
            raise AttributeError, attr

    def createCmdlineDict(self):
        cmdlineDict = {}
        cmdline = open("/proc/cmdline", "r").read()
        lst = shlex.split(cmdline)

        for i in lst:
            try:
                (key, val) = i.split("=", 1)
            except:
                key = i
                val = True

            cmdlineDict[key] = val

        return cmdlineDict

    def __init__(self):
        self.__dict__['flags'] = {}
        self.__dict__['flags']['expert'] = 0
        self.__dict__['flags']['debug'] = 0
        self.__dict__['flags']['cmdline'] = self.createCmdlineDict()
        self.__dict__['flags']['network'] = False
        self.__dict__['flags']['mpath'] = 1
        self.__dict__['flags']['dmraid'] = 1

        for line in os.popen("tty"):
            line = line.strip()
            if line.startswith("/dev/tty"):
                self.__dict__['flags']['virtpconsole'] = False
            else:
                self.__dict__['flags']['virtpconsole'] = True

        if self.__dict__['flags']['cmdline'].has_key("debug"):
            self.__dict__['flags']['debug'] = self.__dict__['flags']['cmdline']['debug']

global flags
flags = Flags()
