import os, subprocess
import string
import stat
from pyfire.executil import *

import logging
log = logging.getLogger("pomona")

def execConsole():
    try:
        proc = subprocess.Popen(["/bin/sh"])
        proc.wait()
    except OSError, (errno, msg):
        raise RuntimeError, "Error running /bin/sh: " + msg

# try to keep 2.4 kernel swapper happy!
def swapSuggestion(quiet=0):
    mem = memInstalled()/1024
    mem = ((mem/16)+1)*16
    if not quiet:
        log.info("Detected %sM of memory", mem)

    if mem <= 256:
        minswap = 256
        maxswap = 512
    else:
        if mem > 1000:
            minswap = 1000
            maxswap = 2000
        else:
            minswap = mem
            maxswap = 2*mem

    if not quiet:
        log.info("Swap attempt of %sM to %sM", minswap, maxswap)

    return (minswap, maxswap)

# this is in kilobytes
def memInstalled():
    f = open("/proc/meminfo", "r")
    lines = f.readlines()
    f.close()

    for l in lines:
        if l.startswith("MemTotal:"):
            fields = string.split(l)
            mem = fields[1]
            break

    return int(mem)

# this is in kilobytes - returns amount of RAM not used by /tmp
def memAvailable():
    tram = memInstalled()

    ramused = getDirSize("/tmp")
    if os.path.isdir("/tmp/ramfs"):
        ramused += getDirSize("/tmp/ramfs")

    return tram - ramused

# return size of directory (and subdirs) in kilobytes
def getDirSize(dir):
    def getSubdirSize(dir):
        # returns size in bytes
        mydev = os.lstat(dir)[stat.ST_DEV]
        dsize = 0
        for f in os.listdir(dir):
            curpath = '%s/%s' % (dir, f)
            sinfo = os.lstat(curpath)
            if stat.S_ISDIR(sinfo[stat.ST_MODE]):
                if mydev == sinfo[stat.ST_DEV]:
                    dsize += getSubdirSize(curpath)
            elif stat.S_ISREG(sinfo[stat.ST_MODE]):
                dsize += sinfo[stat.ST_SIZE]
            else:
                pass
        return dsize

    return getSubdirSize(dir)/1024

# this is a mkdir that won't fail if a directory already exists and will
# happily make all of the directories leading up to it.
def mkdirChain(dir):
    try:
        os.makedirs(dir, 0755)
    except OSError, (errno, msg):
        try:
            if errno == EEXIST and stat.S_ISDIR(os.stat(dir).st_mode):
                return
        except:
            pass

        log.error("could not create directory %s: %s" % (dir, msg))
