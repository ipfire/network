###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2007  Michael Tremer & Christian Schmidt                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

__all__ = [ "config", "executil", "hal", "net", "translate", "web", ]

import os

import hal

class System:
    def __init__(self):
        self.dbus = hal.get_device("/org/freedesktop/Hal/devices/computer")

    def getKernelVersion(self):
        ret = None
        try:
            ret = self.dbus["system.kernel.version"]
        except KeyError:
            pass
        return ret

    def getFormfactor(self):
        return self.dbus["system.formfactor"]

    def getVendor(self):
        ret = None
        try:
            ret = self.dbus["system.vendor"]
        except KeyError:
            pass
        return ret

    def getProduct(self):
        ret = None
        try:
            ret = self.dbus["system.product"]
        except KeyError:
            pass
        return ret


if __name__ == "__main__":
    system = System()
    print "Kernel Version    : %s" % system.getKernelVersion()
    print "System Formfactor : %s" % system.getFormfactor()
    print "System Vendor     : %s" % system.getVendor()
    print "System Product    : %s" % system.getProduct()
