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

import pyfire.hal
from pyfire.config import ConfigFile

NETWORK_DEVICES="/etc/sysconfig/network-devices/"
NETWORK_SETTINGS="/etc/sysconfig/network"
NETWORK_SCRIPTS="/etc/init.d/networking/"

class IPError(Exception):
    pass

class IPMissing(Exception):
    pass

class Network:
    def __init__(self):
        self.bridges = {}
        self.nics = {}

        self.settings = NetworkSettings()

    def getNics(self):
        for device in pyfire.hal.get_devices_by_type("net"):
            if device.has_key('net.arp_proto_hw_id'):
                if device['net.arp_proto_hw_id'] == 1:
                    nic = device['device']
                    self.nics[nic] = BridgeSlave(dev)
                    self.nics[nic].set(('hwaddr',device['net.address']))
                    self.nics[nic].set(('desc',device['description']))
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
    def __init__(self, path):
        ConfigFile.__init__(self, path + NETWORK_SETTINGS)

    def getHostname(self):
        return self.get("HOSTNAME")

    def setHostname(self, hostname):
        self.set(("HOSTNAME", hostname))


class BridgeDevice:
    def __init__(self, dev):
        self.filename = "%s/%s/" % (NETWORK_DEVICES, dev,)
        self.name = dev
        self.services = []

        for file in os.listdir(self.filename):
            service = Service(file, bridge=self.name)
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

    def write(self):
        if not os.path.isdir(fn):
            os.makedirs(fn)

        # Save all service information
        for service in self.services:
            service.write()


class Service(ConfigFile):
    def __init__(self, filename, bridge=None, service=None):
        ConfigFile.__init__(self, filename)
        self.service = service
        self.bridge = bridge
        self.name = os.path.basename(self.filename)


def listAllServices():
    ret = []
    for service in os.listdir(NETWORK_SCRIPTS + "services/"):
        ret.append(service)
    return ret

### Returns the hostname
def gethostname():
    return socket.gethostname()

def has_device(device):
    for nic in os.listdir("/sys/class/net/"):
        if device == nic:
            return True
    return False

def has_blue():
    return has_device("blue0")

def has_orange():
    return has_device("orange0")
