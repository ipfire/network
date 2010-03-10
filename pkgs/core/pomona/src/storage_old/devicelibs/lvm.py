#!/usr/bin/python

import os
import re

import util

MAX_LV_SLOTS = 256

def has_lvm():
    has_lvm = False
    for path in os.environ["PATH"].split(":"):
        if os.access("%s/lvm" % path, os.X_OK):
            has_lvm = True
            break

    if has_lvm:
        has_lvm = False
        for line in open("/proc/devices").readlines():
            if "device-mapper" in line.split():
                has_lvm = True
                break

    return has_lvm

# Start config_args handling code
#
# Theoretically we can handle all that can be handled with the LVM --config
# argument.  For every time we call an lvm_cc (lvm compose config) funciton
# we regenerate the config_args with all global info.
config_args = [] # Holds the final argument list
config_args_data = { "filterRejects": [],    # regular expressions to reject.
                            "filterAccepts": [] }   # regexp to accept

def _composeConfig():
    """lvm command accepts lvm.conf type arguments preceded by --config. """
    global config_args, config_args_data
    config_args = []

    filter_string = ""
    rejects = config_args_data["filterRejects"]
    # we don't need the accept for now.
    # accepts = config_args_data["filterAccepts"]
    # if len(accepts) > 0:
    #   for i in range(len(rejects)):
    #       filter_string = filter_string + ("\"a|%s|\", " % accpets[i])

    if len(rejects) > 0:
        for i in range(len(rejects)):
            filter_string = filter_string + ("\"r|%s|\"," % rejects[i])

    filter_string = " filter=[%s] " % filter_string.strip(",")

    # As we add config strings we should check them all.
    if filter_string == "":
        # Nothing was really done.
        return

    # devices_string can have (inside the brackets) "dir", "scan",
    # "preferred_names", "filter", "cache_dir", "write_cache_state",
    # "types", "sysfs_scan", "md_component_detection".  see man lvm.conf.
    devices_string = " devices {%s} " % (filter_string) # strings can be added
    config_string = devices_string # more strings can be added.
    config_args = ["--config", config_string]

def lvm_cc_addFilterRejectRegexp(regexp):
    """ Add a regular expression to the --config string."""
    global config_args_data
    config_args_data["filterRejects"].append(regexp)

    # compoes config once more.
    _composeConfig()

def lvm_cc_resetFilter():
    global config_args_data
    config_args_data["filterRejects"] = []
    config_args_data["filterAccepts"] = []
# End config_args handling code.

# Names that should not be used int the creation of VGs
lvm_vg_blacklist = []
def blacklistVG(name):
    global lvm_vg_blacklist
    lvm_vg_blacklist.append(name)

def getPossiblePhysicalExtents(floor=0):
    """Returns a list of integers representing the possible values for
       the physical extent of a volume group.  Value is in KB.

       floor - size (in KB) of smallest PE we care about.
    """

    possiblePE = []
    curpe = 8
    while curpe <= 16384*1024:
        if curpe >= floor:
            possiblePE.append(curpe)
        curpe = curpe * 2

    return possiblePE

def getMaxLVSize():
    """ Return the maximum size (in MB) of a logical volume. """
    if util.getArch() in ("x86_64",): #64bit architectures
        return (8*1024*1024*1024*1024) #Max is 8EiB (very large number..)
    else:
        return (16*1024*1024) #Max is 16TiB

def safeLvmName(name):
    tmp = name.strip()
    tmp = tmp.replace("/", "_")
    tmp = re.sub("[^0-9a-zA-Z._]", "", tmp)
    tmp = tmp.lstrip("_")

    return tmp
