#
# executil.py - generic utility functions for executing programs
#
# Erik Troan <ewt@redhat.com>
#
# Copyright 1999-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import os
import sys
import types
import select
import signal

def getfd(filespec, readOnly = 0):
    if type(filespec) == types.IntType:
        return filespec
    if filespec == None:
        filespec = "/dev/null"

    flags = os.O_RDWR | os.O_CREAT
    if (readOnly):
        flags = os.O_RDONLY
    return os.open(filespec, flags)

def execWithRedirect(command, argv, stdin = 0, stdout = 1, stderr = 2,
                searchPath = 0, root = '/', newPgrp = 0, ignoreTermSigs = 0):
    stdin = getfd(stdin)
    if stdout == stderr:
        stdout = getfd(stdout)
        stderr = stdout
    else:
        stdout = getfd(stdout)
        stderr = getfd(stderr)

    childpid = os.fork()
    if (not childpid):
        if (root and root != '/'):
            os.chroot(root)
            os.chdir("/")

        if ignoreTermSigs:
            signal.signal(signal.SIGTSTP, signal.SIG_IGN)
            signal.signal(signal.SIGINT, signal.SIG_IGN)

        if type(stdin) == type("a"):
            stdin = os.open(stdin, os.O_RDONLY)
        if type(stdout) == type("a"):
            stdout = os.open(stdout, os.O_RDWR)
        if type(stderr) == type("a"):
            stderr = os.open(stderr, os.O_RDWR)

        if stdin != 0:
            os.dup2(stdin, 0)
            os.close(stdin)
        if stdout != 1:
            os.dup2(stdout, 1)
            if stdout != stderr:
                os.close(stdout)
        if stderr != 2:
            os.dup2(stderr, 2)
            os.close(stderr)

        if (searchPath):
            os.execvp(command, argv)
        else:
            os.execv(command, argv)

        sys.exit(1)

    if newPgrp:
        os.setpgid(childpid, childpid)
        oldPgrp = os.tcgetpgrp(0)
        os.tcsetpgrp(0, childpid)

    status = -1
    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    if newPgrp:
        os.tcsetpgrp(0, oldPgrp)

    return status

## Run an external program and capture standard out.
# @param command The command to run.
# @param argv A list of arguments.
# @param stdin The file descriptor to read stdin from.
# @param stderr The file descriptor to redirect stderr to.
# @param root The directory to chroot to before running command.
# @return The output of command from stdout.
def execWithCapture(command, argv, stdin = 0, stderr = 2, root='/'):
    def chroot():
        os.chroot(root)

    argv = list(argv)
    if type(stdin) == type("string"):
        if os.access(stdin, os.R_OK):
            stdin = open(stdin)
        else:
            stdin = 0
    if type(stderr) == type("string"):
        stderr = open(stderr, "w")

    try:
        pipe = subprocess.Popen([command] + argv, stdin=stdin,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                preexec_fn=chroot, cwd=root)
    except OSError, (errno, msg):
        log.error ("Error running " + command + ": " + msg)
        raise RuntimeError, "Error running " + command + ": " + msg

    rc = pipe.stdout.read()
    pipe.wait()
    return rc

def execWithCaptureStatus(command, argv, searchPath = 0, root = '/', stdin = 0,
                catchfd = 1, closefd = -1):

    if not os.access (root + command, os.X_OK):
        raise RuntimeError, command + " can not be run"

    (read, write) = os.pipe()

    childpid = os.fork()
    if (not childpid):
        if (root and root != '/'): os.chroot (root)
        if isinstance(catchfd, tuple):
            for fd in catchfd:
                os.dup2(write, fd)
        else:
            os.dup2(write, catchfd)
    os.close(write)
    os.close(read)

    if closefd != -1:
        os.close(closefd)

    if stdin:
        os.dup2(stdin, 0)
        os.close(stdin)

    if (searchPath):
        os.execvp(command, argv)
    else:
        os.execv(command, argv)

    sys.exit(1)

    os.close(write)

    rc = ""
    s = "1"
    while (s):
        select.select([read], [], [])
        s = os.read(read, 1000)
        rc = rc + s

    os.close(read)

    status = None

    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    if os.WIFEXITED(status) and (os.WEXITSTATUS(status) == 0):
        status = os.WEXITSTATUS(status)
    else:
        status = -1

    return (rc, status)

def execWithCaptureErrorStatus(command, argv, searchPath = 0, root = '/',
                stdin = 0, catchfd = 1, catcherrfd = 2, closefd = -1):

    if not os.access (root + command, os.X_OK):
        raise RuntimeError, command + " can not be run"

    (read, write) = os.pipe()
    (read_err,write_err) = os.pipe()

    childpid = os.fork()
    if (not childpid):
        if (root and root != '/'): os.chroot (root)
        if isinstance(catchfd, tuple):
            for fd in catchfd:
                os.dup2(write, fd)
        else:
            os.dup2(write, catchfd)
    os.close(write)
    os.close(read)

    if isinstance(catcherrfd, tuple):
        for fd in catcherrfd:
            os.dup2(write_err, fd)
    else:
        os.dup2(write_err, catcherrfd)
    os.close(write_err)
    os.close(read_err)

    if closefd != -1:
        os.close(closefd)

    if stdin:
        os.dup2(stdin, 0)
        os.close(stdin)

    if (searchPath):
        os.execvp(command, argv)
    else:
        os.execv(command, argv)

    sys.exit(1)

    os.close(write)
    os.close(write_err)

    rc = ""
    rc_err = ""
    s = "1"
    t = "1"
    while (s or t):
        select.select([read], [], [])
        s = os.read(read, 1000)
        t = os.read(read_err, 1000)
        rc = rc + s
        rc_err = rc_err + t

    os.close(read)
    os.close(read_err)

    status = None

    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (errno, msg):
        print __name__, "waitpid:", msg

    if os.WIFEXITED(status) and (os.WEXITSTATUS(status) == 0):
        status = os.WEXITSTATUS(status)
    else:
        status = -1

    return (rc, rc_err, status)
