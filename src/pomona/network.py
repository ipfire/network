#!/usr/bin/python

import string
import shutil
import isys
import inutil
import socket
import struct
import os
import time
import pyfire.hal
from flags import flags

from constants import *

from pyfire.config import ConfigFile

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

class IPError(Exception):
    pass

class IPMissing(Exception):
    pass

def sanityCheckHostname(hostname):
    if len(hostname) < 1:
        return None

    if len(hostname) > 255:
        return _("Hostname must be 255 or fewer characters in length.")

    validStart = string.ascii_letters + string.digits
    validAll = validStart + ".-"

    if string.find(validStart, hostname[0]) == -1:
        return _("Hostname must start with a valid character in the ranges "
                 "'a-z', 'A-Z', or '0-9'")

    for i in range(1, len(hostname)):
        if string.find(validAll, hostname[i]) == -1:
            return _("Hostnames can only contain the characters 'a-z', 'A-Z', '0-9', '-', or '.'")

    return None

# Try to determine what the hostname should be for this system
def getDefaultHostname(pomona):
    return pomona.id.network.hostname

# sanity check an IP string.
def sanityCheckIPString(ip_string):
    if ip_string.strip() == "":
        raise IPMissing, _("IP address is missing.")

    if ip_string.find(':') == -1 and ip_string.find('.') > 0:
        family = socket.AF_INET
        errstr = _("IPv4 addresses must contain four numbers between 0 and 255, separated by periods.")
    elif ip_string.find(':') > 0 and ip_string.find('.') == -1:
        family = socket.AF_INET6
        errstr = _("'%s' is not a valid IPv6 address.") % ip_string
    else:
        raise IPError, _("'%s' is an invalid IP address.") % ip_string

    try:
        socket.inet_pton(family, ip_string)
    except socket.error:
        raise IPError, errstr

def networkDeviceCheck(pomona):
    devs = pomona.id.network.available()
    if not devs:
        pomona.dispatch.skipStep("network")

class NetworkDevice(ConfigFile):
    def __init__(self, dev):
        self.info = { "DEVICE" : dev,
                      "ONBOOT": "no" }

class Network:
    def __init__(self):
        self.netdevices = {}
        self.gateway = ""
        self.primaryNS = ""
        self.secondaryNS = ""
        self.domains = []
        self.isConfigured = 0
        self.hostname = sname + ".localdomain"

        # now initialize devices
        self.available()

    def getDevice(self, device):
        return self.netdevices[device]

    def available(self):
        for device in pyfire.hal.get_devices_by_type("net"):
            if device.has_key('net.arp_proto_hw_id'):
                if device['net.arp_proto_hw_id'] == 1:
                    dev = device['device']
                    self.netdevices[dev] = NetworkDevice(dev)
                    self.netdevices[dev].set(('hwaddr',device['net.address']))
                    self.netdevices[dev].set(('desc',device['description']))

        return self.netdevices

    def setHostname(self, hn):
        self.hostname = hn

    def setDNS(self, ns):
        dns = ns.split(',')
        if len(dns) >= 1:
            self.primaryNS = dns[0]
        if len(dns) >= 2:
            self.secondaryNS = dns[1]

    def setGateway(self, gw):
        self.gateway = gw

    def write(self, instPath):
        filename = "%s/etc/sysconfig/network" % (instPath,)
        f = ConfigFile()
        f.read(filename)
        f.set(("HOSTNAME", self.hostname))
        f.write(filename)
