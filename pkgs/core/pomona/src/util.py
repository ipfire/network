#!/usr/bin/python

import os
import stat

from pyfire.executil import *

def getArch():
    return "i386"

def notify_kernel(path, action="change"):
    """ Signal the kernel that the specified device has changed. """
    path = os.path.join(path, "uevent")
    if not path.startswith("/sys/") or not os.access(path, os.W_OK):
        raise ValueError("invalid sysfs path")
    f = open(path, "a")
    f.write("%s\n" % action)
    f.close()

def numeric_type(num):
    """ Verify that a value is given as a numeric data type.

        Return the number if the type is sensible or raise ValueError
        if not.
    """
    if num is None:
        num = 0
    elif not (isinstance(num, int) or \
              isinstance(num, long) or \
              isinstance(num, float)):
        raise ValueError("value (%s) must be either a number or None" % num)

    return num

## Create a directory path.  Don't fail if the directory already exists.
# @param dir The directory path to create.
def mkdirChain(dir):
    try:
        os.makedirs(dir, 0755)
    except OSError, (errno, msg):
        try:
            if errno == EEXIST and stat.S_ISDIR(os.stat(dir).st_mode):
                return
        except:
            pass
