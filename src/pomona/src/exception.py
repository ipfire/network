
import bdb
import os, sys, signal, types
from cPickle import Pickler
from string import joinfields
from pyfire.translate import _
import traceback

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
        out.write ("\nLocal variables in innermost frame:\n")
        try:
            for (key, value) in frame.f_locals.items():
                out.write ("%s: %s\n" % (key, value))
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

# Returns 0 on success, 1 on cancel, 2 on error.
def copyExceptionToRemote(intf):
    import pty

    scpWin = intf.scpWindow()
    while 1:
        # Bail if they hit the cancel button.
        scpWin.run()
        scpInfo = scpWin.getrc()

        if scpInfo == None:
            scpWin.pop()
            return 1

        (host, path, user, password) = scpInfo

        if host.find(":") != -1:
            (host, port) = host.split(":")

            # Try to convert the port to an integer just as a check to see
            # if it's a valid port number.  If not, they'll get a chance to
            # correct the information when scp fails.
            try:
                int(port)
                portArgs = ["-P", port]
            except ValueError:
                portArgs = []
        else:
            portArgs = []

        # Thanks to Will Woods <wwoods@redhat.com> for the scp control
        # here and in scpAuthenticate.

        # Fork ssh into its own pty
        (childpid, master) = pty.fork()
        if childpid < 0:
            log.critical("Could not fork process to run scp")
            scpWin.pop()
            return 2
        elif childpid == 0:
            # child process - run scp
            args = ["scp", "-oNumberOfPasswordPrompts=1",
                    "-oStrictHostKeyChecking=no"] + portArgs + \
                   ["/tmp/anacdump.txt", "%s@%s:%s" % (user, host, path)]
            os.execvp("scp", args)

            # parent process
            try:
                childstatus = scpAuthenticate(master, childpid, password)
            except OSError:
                scpWin.pop()
                return 2

        os.close(master)

        if os.WIFEXITED(childstatus) and os.WEXITSTATUS(childstatus) == 0:
            return 0
        else:
            scpWin.pop()
            return 2

def scpAuthenticate(master, childpid, password):
    while 1:
        # Read up to password prompt.  Propagate OSError exceptions, which
        # can occur for anything that causes scp to immediately die (bad
        # hostname, host down, etc.)
        buf = os.read(master, 4096)
        if buf.find("'s password: ") != -1:
            os.write(master, password+"\n")
            # read the space and newline that get echoed back
            os.read(master, 2)
            break

    while 1:
        buf = ""
        try:
            buf = os.read(master, 4096)
        except (OSError, EOFError):
            break

    (pid, childstatus) = os.waitpid (childpid, 0)
    return childstatus

# Reverse the order that tracebacks are printed so people will hopefully quit
# giving us the least useful part of the exception in bug reports.
def formatException (type, value, tb):
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
    list = formatException (type, value, tb)
    text = joinfields (list, "")

    # save to local storage first
    out = open("/tmp/instdump.txt", "w")
    dumpException (out, text, tb, pomona)
    out.close()

    win = pomona.intf.exceptionWindow(text, "/tmp/instdump.txt")
    if not win:
        pomona.intf.__del__()
        os.kill(os.getpid(), signal.SIGKILL)

    while 1:
        win.run()
        rc = win.getrc()

        if rc == 0:
            pomona.intf.__del__ ()
            os.kill(os.getpid(), signal.SIGKILL)
        elif rc == 1:
            scpRc = copyExceptionToRemote(pomona.intf)

            if scpRc == 0:
                pomona.intf.messageWindow(_("Dump Written"),
                                          _("Your system's state has been successfully written to "
                                            "the remote host.  Your system will now be rebooted."),
                                          type="custom", custom_icon="info",
                                          custom_buttons=[_("_Reboot")])
                sys.exit(0)
            elif scpRc == 1:
                continue
            elif scpRc == 2:
                pomona.intf.messageWindow(_("Dump Not Written"),
                                          _("There was a problem writing the system state to the "
                                            "remote host."))
                continue
