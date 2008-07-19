#
# urlinstall.py - URL based install source method
#
# Erik Troan <ewt@redhat.com>
#
# Copyright 1999-2006 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

from installmethod import InstallMethod, FileCopyException
import os
import re
import time
import shutil
import string
import socket
import urlparse
import urlgrabber.grabber as grabber
import isys
from pakfireinstall import PomonaCallback

from snack import *
from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

def urlretrieve(location, file, callback=None):
    """Downloads from location and saves to file."""
    if callback is not None:
        callback.initWindow = \
                callback.waitWindow(_("Downloading"), _("Connecting..."))

    log.info("Retrieving url %s" % location)

    try:
        url = grabber.urlopen(location)
    except grabber.URLGrabError, e:
        raise IOError(e.errno, e.strerror)

    # see if there is a size
    try:
        filesize = int(url.info()["Content-Length"])
        if filesize == 0:
            filesize = None
    except:
        filesize = None

    if callback is not None:
        if not filesize:
            callback.setSize(0)
        else:
            callback.setSize(filesize)

    # create output file
    f = open(file, 'w+')

    if callback is not None:
        callback.callback(CB_START, title=_("Downloading"), text=_("Retrieving %s")
            % os.path.basename(urlparse.urlparse(location).path))

    # if they dont want a status callback just do it in one big swoop
    if callback is None:
        f.write(url.read())
    else:
        buf = url.read(65535)
        tot = len(buf)
        while len(buf) > 0:
            if filesize is not None:
                callback.callback(CB_PROGRESS, amount=tot)
            else:
                callback.callback(CB_PROGRESS, amount="%dKB..." % (tot/1024,))
            f.write(buf)
            buf = url.read(65535)
            tot += len(buf)

    f.close()
    url.close()
    if callback is not None:
        callback.callback(CB_STOP)

class UrlInstallMethod(InstallMethod):
    def badPackageError(self, pkgname):
        return _("The file %s cannot be opened.  This is due to a missing "
                 "file or perhaps a corrupt package.  Please verify your "
                 "mirror contains all required packages, and try using a "
                 "different one.\n\n"
                 "If you reboot, your system will be left in an inconsistent "
                 "state that will likely require reinstallation.\n\n") % pkgname

    def getFilename(self, filename, callback=None, destdir=None, retry=1):
        if destdir is None:
            tmppath = self.getTempPath()
        else:
            tmppath = destdir

        fullPath = urlparse.urljoin(self.url, filename)

        file = tmppath + "/" + os.path.basename(fullPath)

        tries = 0
        while tries < 5:
            try:
                rc=urlretrieve(fullPath, file, callback=callback)
            except IOError, (errnum, msg):
                log.critical("IOError %s occurred getting %s: %s"
                    % (errnum, fullPath.replace("%", "%%"), str(msg)))

                if not retry:
                    raise FileCopyException

                time.sleep(5)
            else:
                break

            tries = tries + 1

            if tries >= 5:
                raise FileCopyException

        return file

    def __copyFileToTemp(self, baseurl, filename, raise404=False):
        tmppath = self.getTempPath()

        fullPath = baseurl + "/" + filename

        file = tmppath + "/" + os.path.basename(fullPath)

        tries = 0
        while tries < 5:
            try:
                urlretrieve(fullPath, file)
            except IOError, (errnum, msg):
                if errnum == 14 and "404" in msg and raise404:
                    raise
                log.critical("IOError %s occurred getting %s: %s",
                                errnum, fullPath.replace("%", "%%"), str(msg))
                time.sleep(5)
            else:
                break
            tries = tries + 1

            if tries >= 5:
                raise FileCopyException
        return file

    def copyFileToTemp(self, filename):
        return self.__copyFileToTemp(self.pkgUrl, filename)

    def unlinkFilename(self, fullName):
        os.remove(fullName)

    def setIntf(self, intf):
        self.intf = intf
        self.messageWindow = intf.messageWindow
        self.progressWindow = intf.progressWindow

    def getMethodUri(self):
        return self.baseUrl

    def unmountMedia(self):
        if not self.tree:
            return

        while True:
            try:
                isys.umount("/mnt/source")
                break
            except Exception, e:
                log.error("exception in unmountCD: %s" %(e,))
                self.messageWindow(_("Error"),
                                   _("An error occurred unmounting the disc. "
                                     "Please make sure you're not accessing "
                                     "%s from the shell on tty2 "
                                     "and then click OK to retry.")
                                   % ("/mnt/source",))

    def filesDone(self):
        for file in REQUIRED_FILES:
            try:
                os.unlink("%s/%s" % (SOURCE_PATH, file,))
            except Exception, e:
                log.error("Cannot remove %s/%s: %s" % (SOURCE_PATH, file, e,))

    def __init__(self, url, rootPath, intf):
        InstallMethod.__init__(self, rootPath, intf)

        self.url = url
        log.info("Got base url: %s" % (self.url,))

        (scheme, netloc, path, query, fragid) = urlparse.urlsplit(self.url)

        try:
            socket.inet_pton(socket.AF_INET6, netloc)
            netloc = '[' + netloc + ']'
        except:
            pass

        # encoding fun so that we can handle absolute paths
        if scheme == "ftp" and path and path.startswith("//"):
            path = "/%2F" + path[1:]

        self.messageWindow = intf.messageWindow
        self.progressWindow = intf.progressWindow
        self.waitWindow = intf.waitWindow

    def doPreInstall(self, pomona):
        cb = PomonaCallback(pomona, pomona.method)

        for file in REQUIRED_FILES:
            self.getFilename(file, destdir=SOURCE_PATH, callback=cb)

    def doPostInstall(self, pomona):
        pass
