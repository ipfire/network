
import bdb
import os, sys, signal, types
from cPickle import Pickler
from string import joinfields
import traceback

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

import logging
log = logging.getLogger("pomona")

dumpHash = {}

def dumpClass(instance, fd, level=0, parentkey="", skipList=[]):
    # protect from loops
    try:
        if not dumpHash.has_key(instance):
            dumpHash[instance] = None
        else:
            fd.write("Already dumped\n")
            return
    except TypeError:
        fd.write("Cannot dump object\n")
        return

    if (instance.__class__.__dict__.has_key("__str__") or
                    instance.__class__.__dict__.has_key("__repr__")):
        fd.write("%s\n" % (instance,))
        return
    fd.write("%s instance, containing members:\n" %
             (instance.__class__.__name__))
    pad = ' ' * ((level) * 2)

    for key, value in instance.__dict__.items():
        if parentkey != "":
            curkey = parentkey + "." + key
        else:
            curkey = key

        # Don't dump objects that are in our skip list, though ones that are
        # None are probably okay.
        if eval("instance.%s is not None" % key) and \
                eval("id(instance.%s)" % key) in skipList:
            continue

    if type(value) == types.ListType:
        fd.write("%s%s: [" % (pad, curkey))
        first = 1
        for item in value:
            if not first:
                fd.write(", ")
            else:
                first = 0
            if type(item) == types.InstanceType:
                dumpClass(item, fd, level + 1, skipList=skipList)
            else:
                fd.write("%s" % (item,))
            fd.write("]\n")
    elif type(value) == types.DictType:
        fd.write("%s%s: {" % (pad, curkey))
        first = 1
        for k, v in value.items():
            if not first:
                fd.write(", ")
            else:
                first = 0
            if type(k) == types.StringType:
                fd.write("'%s': " % (k,))
            else:
                fd.write("%s: " % (k,))
            if type(v) == types.InstanceType:
                dumpClass(v, fd, level + 1, parentkey = curkey, skipList=skipList)
            else:
                fd.write("%s" % (v,))
            fd.write("}\n")
    elif type(value) == types.InstanceType:
        fd.write("%s%s: " % (pad, curkey))
        dumpClass(value, fd, level + 1, parentkey=curkey, skipList=skipList)
    else:
        fd.write("%s%s: %s\n" % (pad, curkey, value))

def dumpException(out, text, tb, pomona):
    skipList = []
    idSkipList = []

    # Catch attributes that do not exist at the time we do the exception dump
    # and ignore them.
    for k in skipList:
        try:
            eval("idSkipList.append(id(%s))" % k)
        except:
            pass

    p = Pickler(out)

    out.write(text)

    trace = tb
    if trace is not None:
        while trace.tb_next:
            trace = trace.tb_next
        frame = trace.tb_frame
        out.write("\nLocal variables in innermost frame:\n")
        try:
            for (key, value) in frame.f_locals.items():
                out.write("%s: %s\n" % (key, value))
        except:
            pass

    try:
        out.write("\n\n")
        dumpClass(pomona, out, skipList=idSkipList)
    except:
        out.write("\nException occurred during state dump:\n")
        traceback.print_exc(None, out)

    for file in ("/root/syslog", "/root/pomona.log", "/root/install.log"):
        try:
            f = open(file, 'r')
            line = "\n\n%s:\n" % (file,)
            while line:
                out.write(line)
                line = f.readline()
                f.close()
        except IOError:
            pass
        except:
            out.write("\nException occurred during %s file copy:\n" % (file,))
            traceback.print_exc(None, out)

# Reverse the order that tracebacks are printed so people will hopefully quit
# giving us the least useful part of the exception in bug reports.
def formatException(type, value, tb):
    lst = traceback.format_tb(tb)
    lst.reverse()
    lst.insert(0, 'Traceback (most recent call first):\n')
    lst.extend(traceback.format_exception_only(type, value))
    return lst

def handleException(pomona, (type, value, tb)):
    if isinstance(value, bdb.BdbQuit):
        sys.exit(1)

    # restore original exception handler
    sys.excepthook = sys.__excepthook__

    # get traceback information
    list = formatException(type, value, tb)
    text = joinfields(list, "")

    # save to local storage first
    out = open("/tmp/instdump.txt", "w")
    dumpException(out, text, tb, pomona)
    out.close()

    win = pomona.intf.exceptionWindow(text, "/tmp/instdump.txt")
    if not win:
        pomona.intf.__del__()
        os.kill(os.getpid(), signal.SIGKILL)

    while 1:
        win.run()
        rc = win.getrc()

        if rc == 0:
            pomona.intf.__del__()
            os.kill(os.getpid(), signal.SIGKILL)
