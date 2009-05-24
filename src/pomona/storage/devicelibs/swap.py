import resource

import util
import os

from ..errors import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

def mkswap(device, label=''):
    argv = []
    if label:
        argv.extend(["-L", label])
    argv.append(device)

    rc = util.execWithRedirect("mkswap", argv,
                                stderr = "/dev/tty5",
                                stdout = "/dev/tty5",
                                searchPath=1)

    if rc:
        raise SwapError("mkswap failed for '%s'" % device)

def swapon(device, priority=None):
    pagesize = resource.getpagesize()
    buf = None
    if pagesize > 2048:
        num = pagesize
    else:
        num = 2048

    try:
        fd = os.open(device, os.O_RDONLY)
        buf = os.read(fd, num)
    except OSError:
        pass
    finally:
        try:
            os.close(fd)
        except (OSError, UnboundLocalError):
            pass

    if buf is not None and len(buf) == pagesize:
        sig = buf[pagesize - 10:]
        if sig == 'SWAP-SPACE':
            raise OldSwapError
        if sig == 'S1SUSPEND\x00' or sig == 'S2SUSPEND\x00':
            raise SuspendError

    argv = []
    if isinstance(priority, int) and 0 <= priority <= 32767:
        argv.extend(["-p", "%d" % priority])
    argv.append(device)
        
    rc = util.execWithRedirect("swapon",
                                argv,
                                stderr = "/dev/tty5",
                                stdout = "/dev/tty5",
                                searchPath=1)

    if rc:
        raise SwapError("swapon failed for '%s'" % device)

def swapoff(device):
    rc = util.execWithRedirect("swapoff", [device],
                                stderr = "/dev/tty5",
                                stdout = "/dev/tty5",
                                searchPath=1)

    if rc:
        raise SwapError("swapoff failed for '%s'" % device)

def swapstatus(device):
    lines = open("/proc/swaps").readlines()
    status = False
    for line in lines:
        if not line.strip():
            continue
            
        if line.split()[0] == device:
            status = True
            break

    return status
