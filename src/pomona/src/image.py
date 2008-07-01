#
# image.py - Install method for disk image installs (CD & NFS)
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
import shutil
import os
import sys
import isys
import time
import string
import shutil

from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

class CdromInstallMethod(InstallMethod):
	def umountMedia(self):
		while True:
			try:
				isys.umount(SOURCE_PATH)
				break
			except Exception, e:
				log.error("exception when umounting media: %s" % (e,))
				self.messageWindow(_("Error"),
													 _("An error occurred unmounting the disc. "
														 "Please make sure you're not accessing "
														 "the disk from the shell on tty2 "
														 "and then click OK to retry."))

	def ejectMedia(self):
		isys.ejectCdrom(self.device)

	def badPackageError(self, pkgname):
		return _("The file %s cannot be opened.  This is due to a missing "
						 "file or perhaps a corrupt package.  Please verify your "
						 "installation images and that you have all the required "
						 "media.\n\n"
						 "If you reboot, your system will be left in an inconsistent "
						 "state that will likely require reinstallation.\n\n") % pkgname

	def getFilename(self, filename, callback=None, destdir=None, retry=1):
		return self.tree + "/" + filename

	def mountMedia(self, filename=None):
		if not filename:
			filename = INFO_FILE
		
		log.info("Going to mount the source media")
		
		if os.access(SOURCE_PATH + "/%s" % filename, os.R_OK):
			log.info("The correct media is already mounted")
			return
		else:
			try:
				isys.umount(SOURCE_PATH)
			except:
				pass

		done = False
		cdlist = isys.cdromList()
				
		while 1:
			## Check if there is a disc in ANY device
			for dev in cdlist:
				w = self.waitWindow(_("Probing CDROM"),
					_("Searching for a valid disc on /dev/%s...") % (dev,))
				try:
					if not isys.mount(dev, SOURCE_PATH, fstype="iso9660", readOnly=1):
						time.sleep(5)
						if os.access(SOURCE_PATH + "/%s" % filename, os.R_OK):
							self.device = dev
							done = True
							log.info("Successfully mounted %s as source" % (self.device,))
							w.pop()
							break
						else:
							w.pop()
							self.messageWindow(_("Wrong CDROM"),
								_("That's not the correct %s CDROM in /dev/%s.") % (name, dev,))
							isys.umount(SOURCE_PATH)
							isys.ejectCdrom(dev)
					else:
						w.pop()
				except:
					w.pop()
					#self.messageWindow(_("Error"), _("Unable to access the CDROM."))
			
			if done:
				break

			if self.intf is not None:
				self.intf.beep()

			self.messageWindow(_("Insert CDROM"), 
					_("Please insert the %s disc to continue.") % (name,))

	def unlinkFilename(self, fullName):
		pass

	def filesDone(self):
		# we're trying to unmount the CD here.  if it fails, oh well,
		# they'll reboot soon enough I guess :)
		try:
			isys.umount(SOURCE_PATH)
		except Exception, e:
			log.error("Unable to umount source: %s" %(e,))

	def __init__(self, rootPath, intf):
		"""@param method cdrom://device:/path"""
			
		self.messageWindow = intf.messageWindow
		self.progressWindow = intf.progressWindow
		self.waitWindow = intf.waitWindow
		self.loopbackFile = None

		InstallMethod.__init__(self, rootPath, intf)
		
		self.mountMedia()
