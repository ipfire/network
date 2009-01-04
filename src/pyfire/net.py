#!/usr/bin/python
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2008  Michael Tremer & Christian Schmidt                      #
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

import os
import os.path
import socket
import string

import hal
from config import ConfigFile

NETWORK_DEVICES="/etc/sysconfig/network-devices/"
NETWORK_SETTINGS="/etc/sysconfig/network"
NETWORK_SCRIPTS="/etc/init.d/networking/"

class Network:
    def __init__(self):
        self.bridges = {}
        self.nics = {}

        self.settings = NetworkSettings(NETWORK_SETTINGS)

    def getNics(self):
        for device in hal.get_devices_by_type("net"):
            if device.has_key('net.arp_proto_hw_id'):
                if device['net.arp_proto_hw_id'] == 1 and \
                    not device['info.category'] == 'net.bridge':
                    nic = device['device']
                    self.nics[nic] = NetworkDevice(nic, device)
        return self.nics

    def getNic(self, nic):
        return self.nics[nic]

    def getBridges(self, colour=None):
        for file in os.listdir(NETWORK_DEVICES):
            bridge = os.path.basename(file)
            if colour and not bridge.startswith(colour):
                continue
            self.bridges[bridge] = BrideDevice(bridge)
        return self.bridges

    def getBridge(self, bridge):
        return self.bridges[bridge]

    def addBridge(self, dev):
        self.bridges[dev] = BridgeDevice(dev)

    def delBridge(self, dev):
        self.bridges[dev].remove()
        del self.bridges[dev]

    def write(self):
        for bridge in self.bridges.items():
            self.bridges[bridge].write()
        self.settings.write()


class NetworkSettings(ConfigFile):
    def __init__(self, filename):
        ConfigFile.__init__(self, filename)

    def getHostname(self):
        return self.get("HOSTNAME")

    def setHostname(self, hostname):
        self.set(("HOSTNAME", hostname))


class BridgeDevice:
    def __init__(self, dev):
        self.filename = "%s/%s/" % (NETWORK_DEVICES, dev,)
        self.device = dev
        self.services = []

        for file in os.listdir(self.filename):
            service = Service(file, bridge=self.device)
            self.addService(service)

    def addService(self, service):
        self.services.append(service)

    def getPolicy(self, service):
        ret = []
        for service in self.services:
            if service.service == service:
                ret.append(service)
        return ret

    def delService(self, service):
        pass # how to do this?

    def addNic(self, nic):
        # requires a NetworkDevice instance
        filename = os.path.join(self.filename, nic.getDevice())
        service = Service(filename, bridge=self.name, service="bridge-slave")
        service.set(("DESCRIPTION", nic.getDescription()),
                    ("MAC", nic.getMac()))
        self.addService(service)

    def write(self):
        if not os.path.isdir(fn):
            os.makedirs(fn)

        # Save all service information
        for service in self.services:
            service.write()


class NetworkDevice:
    def __init__(self, dev, dbus):
        self.device = dev
        self.dbus = dbus

    def __str__(self):
        return "%s (%s) - %s" % (self.device, self.getDescription(), self.getMac())

    def getDevice(self):
        return self.device

    def getMac(self):
        return self.dbus["net.address"]

    def getDescription(self):
        return self.dbus["description"]


class ServiceError(Exception):
    pass


class Service(ConfigFile):
    def __init__(self, filename, bridge=None, service=None):
        self.service = None
        if service:
            self.setService(service)
        ConfigFile.__init__(self, filename)
        self.bridge = bridge
        self.name = os.path.basename(self.filename)

    def setService(self, service):
        if not service in listAllServices():
            raise ServiceError, "The given service is not available: %s" % service
        self.service = service


def listAllServices():
    ret = []
    for service in os.listdir(NETWORK_SCRIPTS + "services/"):
        ret.append(service)
    return ret

if __name__ == "__main__":
    network = Network()
    print "All available nics on this system:"
    for nic, obj in network.getNics().items():
        print obj
