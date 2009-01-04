#!/usr/bin/python

import os
import subprocess
import string
import stat
from errno import *

import logging
log = logging.getLogger("pomona")

## Run an external program and redirect the output to a file.
# @param command The command to run.
# @param argv A list of arguments.
# @param stdin The file descriptor to read stdin from.
# @param stdout The file descriptor to redirect stdout to.
# @param stderr The file descriptor to redirect stderr to.
# @param searchPath Should command be searched for in $PATH?
# @param root The directory to chroot to before running command.
# @return The return code of command.
def execWithRedirect(command, argv, stdin = 0, stdout = 1, stderr = 2,
                     searchPath = 0, root = '/'):
    def chroot ():
        os.chroot(root)

        if not searchPath and not os.access (command, os.X_OK):
            raise RuntimeError, command + " can not be run"

    argv = list(argv)
    if type(stdin) == type("string"):
        if os.access(stdin, os.R_OK):
            stdin = open(stdin)
        else:
            stdin = 0
    if type(stdout) == type("string"):
        stdout = open(stdout, "w")
    if type(stderr) == type("string"):
        stderr = open(stderr, "w")

    if stdout is not None and type(stdout) != int:
        stdout.write("Running... %s\n" %([command] + argv,))

    try:
        proc = subprocess.Popen([command] + argv, stdin=stdin, stdout=stdout,
                                stderr=stderr, preexec_fn=chroot, cwd=root)
        ret = proc.wait()
    except OSError, (errno, msg):
        errstr = "Error running %s: %s" % (command, msg)
        log.error (errstr)
        raise RuntimeError, errstr

    return ret

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

def execWithPulseProgress(command, argv, stdin = 0, stdout = 1, stderr = 2,
                          progress = None, root = '/'):
    def chroot():
        os.chroot(root)

    argv = list(argv)
    if type(stdin) == type("string"):
        if os.access(stdin, os.R_OK):
            stdin = open(stdin)
        else:
            stdin = 0
    if type(stdout) == type("string"):
        stdout = open(stdout, "w")
    if type(stderr) == type("string"):
        stderr = open(stderr, "w")
    if stdout is not None and type(stdout) != int:
        stdout.write("Running... %s\n" %([command] + argv,))

    p = os.pipe()
    childpid = os.fork()
    if not childpid:
        os.close(p[0])
        os.dup2(p[1], 1)
        os.dup2(stderr.fileno(), 2)
        os.dup2(stdin, 0)
        os.close(stdin)
        os.close(p[1])
        stderr.close()

        os.execvp(command, [command] + argv)
        os._exit(1)

    os.close(p[1])

    while 1:
        try:
            s = os.read(p[0], 1)
        except OSError, args:
            (num, str) = args
            if (num != 4):
                raise IOError, args

        stdout.write(s)
        if progress: progress.pulse()

        if len(s) < 1:
            break

    try:
        (pid, status) = os.waitpid(childpid, 0)
    except OSError, (num, msg):
        log.critical("exception from waitpid: %s %s" %(num, msg))

    progress and progress.pop()

    # *shrug*  no clue why this would happen, but hope that things are fine
    if status is None:
        return 0

    if os.WIFEXITED(status):
        return os.WEXITSTATUS(status)

    return 1

## Run a shell.
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
