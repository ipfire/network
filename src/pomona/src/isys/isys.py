#
# isys.py - installer utility functions and glue for C module
#
# Matt Wilson <msw@redhat.com>
# Erik Troan <ewt@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2001 - 2004 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import _isys
import string
import os
import os.path
import socket
import stat
import posix
import sys
import kudzu
import inutil
import warnings
import resource
import re
import struct

import logging
log = logging.getLogger("pomona")

mountCount = {}
raidCount = {}

MIN_RAM = _isys.MIN_RAM
EARLY_SWAP_RAM = _isys.EARLY_SWAP_RAM

def pathSpaceAvailable(path, fsystem = "ext2"):
	return _isys.devSpaceFree(path)

def spaceAvailable(device, fsystem = "ext2"):
	mount(device, "/mnt/space", fstype = fsystem)
	space = _isys.devSpaceFree("/mnt/space/.")
	umount("/mnt/space")
	return space

def fsSpaceAvailable(fsystem):
	return _isys.devSpaceFree(fsystem)

def losetup(device, file, readOnly = 0):
	if readOnly:
		mode = os.O_RDONLY
	else:
		mode = os.O_RDWR
	targ = os.open(file, mode)
	loop = os.open(device, mode)
	try:
		_isys.losetup(loop, targ, file)
	finally:
		os.close(loop)
		os.close(targ)

def lochangefd(device, file):
	loop = os.open(device, os.O_RDONLY)
	targ = os.open(file, os.O_RDONLY)
	try:
		_isys.lochangefd(loop, targ)
	finally:
		os.close(loop)
		os.close(targ)

def unlosetup(device):
	loop = os.open(device, os.O_RDONLY)
	try:
		_isys.unlosetup(loop)
	finally:
		os.close(loop)

def ddfile(file, megs, pw = None):
	buf = '\x00' * (1024 * 256)
	
	fd = os.open(file, os.O_RDWR | os.O_CREAT)
	
	total = megs * 4	    # we write out 1/4 of a meg each time through
	
	if pw:
		(fn, title, text) = pw
		win = fn(title, text, total - 1)

	for n in range(total):
		os.write(fd, buf)
		if pw:
			win.set(n)

	if pw:
		win.pop()

	os.close(fd)

def mount(device, location, fstype = "ext2", readOnly = 0, bindMount = 0, remount = 0):
	location = os.path.normpath(location)
	
	# We don't need to create device nodes for devices that start with '/'
	# (like '/usbdevfs') and also some special fake devices like 'proc'.
	# First try to make a device node and if that fails, assume we can
	# mount without making a device node.  If that still fails, the caller
	# will have to deal with the exception.
	# We note whether or not we created a node so we can clean up later.
	if device and device != "none" and device[0] != "/":
		devName = "/dev/%s" % device
		device = devName

	if mountCount.has_key(location) and mountCount[location] > 0:
		mountCount[location] = mountCount[location] + 1
		return

	log.debug("mounting %s --> %s" % (device, location))
	rc = _isys.mount(fstype, device, location, readOnly, bindMount, remount)

	if not rc:
		mountCount[location] = 1

	return rc

def umount(what, removeDir = 1):
	what = os.path.normpath(what)

	if not os.path.isdir(what):
		raise ValueError, "isys.umount() can only umount by mount point"

	if mountCount.has_key(what) and mountCount[what] > 1:
		mountCount[what] = mountCount[what] - 1
		return

	rc = _isys.umount(what)

	if removeDir and os.path.isdir(what):
		os.rmdir(what)

	if not rc and mountCount.has_key(what):
		del mountCount[what]

	return rc

def smpAvailable():
	return _isys.smpavailable()

htavailable = _isys.htavailable

def chroot (path):
	return os.chroot(path)

def checkBoot (path):
	return _isys.checkBoot(path)

def swapoff(path):
	return _isys.swapoff(path)

def swapon(path):
	return _isys.swapon(path)

def loadFont(): ### DO WE NEED THIS?
	return _isys.loadFont()

def loadKeymap(keymap):
	return _isys.loadKeymap(keymap)

classMap = { "disk": kudzu.CLASS_HD,
						 "cdrom": kudzu.CLASS_CDROM,
						 "floppy": kudzu.CLASS_FLOPPY }

cachedDrives = None

def flushDriveDict():
	global cachedDrives
	cachedDrives = None

def driveDict(klassArg):
	import parted
	global cachedDrives
	if cachedDrives is None:
		devs = kudzu.probe(kudzu.CLASS_HD | kudzu.CLASS_CDROM | \
											 kudzu.CLASS_FLOPPY,
		                   kudzu.BUS_UNSPEC, kudzu.PROBE_SAFE)
		new = {}
		for dev in devs:
			device = dev.device
			if device is None: # none devices make no sense
				continue
			if dev.deviceclass != classMap["disk"]:
				new[device] = dev
				continue
			try:
				devName = "/dev/%s" % (device,)

				if not mediaPresent(device):
					new[device] = dev
					continue

				#if device.startswith("sd"):
					# XXX peddev = parted.PedDevice.get(devName)
					# model = peddev.model
					# del peddev
				
				new[device] = dev
			except Exception, e:
				log.debug("exception checking disk blacklist on %s: %s" % (device, e))
		cachedDrives = new

	ret = {}
	for key,dev in cachedDrives.items():
		# XXX these devices should have deviceclass attributes.  Or they
		# should all be subclasses in a device tree and we should be able
		# to use isinstance on all of them.  Not both.
		#if isinstance(dev, block.MultiPath) or isinstance(dev, block.RaidSet):
		#	if klassArg == "disk":
		#		ret[key] = dev
		#el
		if dev.deviceclass == classMap[klassArg]:
			ret[key] = dev.desc
	return ret

def hardDriveDict():
	return driveDict("disk")

def floppyDriveDict():
	return driveDict("floppy")

def cdromList():
	list = driveDict("cdrom").keys()
	list.sort()
	return list

def makedev(major, minor):
	return os.makedev(major, minor)

def mknod(pathname, mode, dev):
	return os.mknod(pathname, mode, dev)

def getopt(*args):
	return apply(_isys.getopt, args)

def doProbeBiosDisks():
	return _isys.biosDiskProbe()

def doGetBiosDisk(mbrSig):
	return _isys.getbiosdisk(mbrSig)

handleSegv = _isys.handleSegv

biosdisks = {}
for d in range(80, 80 + 15):
	disk = doGetBiosDisk("%d" %(d,))
	#print "biosdisk of %s is %s" %(d, disk)
	if disk is not None:
		biosdisks[disk] = d

def compareDrives(first, second):
	if biosdisks.has_key(first) and biosdisks.has_key(second):
		one = biosdisks[first]
		two = biosdisks[second]
		if (one < two):
			return -1
		elif (one > two):
			return 1

		if first.startswith("hd"):
			type1 = 0
		elif first.startswith("sd"):
			type1 = 1
		elif first.startswith("xvd"):
			type1 = -1
		else:
			type1 = 2

		if second.startswith("hd"):
			type2 = 0
		elif second.startswith("sd"):
			type2 = 1
		elif second.startswith("xvd"):
			type2 = -1
		else:
			type2 = 2

		if (type1 < type2):
			return -1
		elif (type1 > type2):
			return 1
		else:
			len1 = len(first)
			len2 = len(second)

		if (len1 < len2):
			return -1
		elif (len1 > len2):
			return 1
		else:
			if (first < second):
				return -1
			elif (first > second):
				return 1

	return 0

def readXFSLabel_int(device):
	try:
		fd = os.open(device, os.O_RDONLY)
	except:
		return None
	
	try:
		buf = os.read(fd, 128)
		os.close(fd)
	except OSError, e:
		log.debug("error reading xfs label on %s: %s" %(device, e))
		try:
			os.close(fd)
		except:
			pass
		return None
	
	xfslabel = None
	if len(buf) == 128 and buf[0:4] == "XFSB":
		xfslabel = string.rstrip(buf[108:120],"\0x00")
	
	return xfslabel
    
def readXFSLabel(device):
	label = readXFSLabel_int(device)
	return label

def readSwapLabel_int(device):
	label = None
	try:
		fd = os.open(device, os.O_RDONLY)
	except:
		return label
	
	pagesize = resource.getpagesize()
	try:
		buf = os.read(fd, pagesize)
		os.close(fd)
	except OSError, e:
		log.debug("error reading swap label on %s: %s" %(device, e))
		try:
			os.close(fd)
		except:
			pass
		return label
	
	if ((len(buf) == pagesize) and (buf[pagesize - 10:] == "SWAPSPACE2")):
		label = string.rstrip(buf[1052:1068], "\0x00")
	return label

def readSwapLabel(device):
	label = readSwapLabel_int(device)
	return label

def readExt2Label(device):
	label = _isys.e2fslabel(device)
	return label

def readReiserFSLabel_int(device):
	label = None
	
	try:
		fd = os.open(device, os.O_RDONLY)
	except OSError, e:
		log.debug("error opening device %s: %s" % (device, e))
		return label

	# valid block sizes in reiserfs are 512 - 8192, powers of 2
	# we put 4096 first, since it's the default
	# reiserfs superblock occupies either the 2nd or 16th block
	for blksize in (4096, 512, 1024, 2048, 8192):
		for start in (blksize, (blksize*16)):
			try:
				os.lseek(fd, start, 0)
				# read 120 bytes to get s_magic and s_label
				buf = os.read(fd, 120)
				
				# see if this block is the superblock
				# this reads reiserfs_super_block_v1.s_magic as defined
				# in include/reiserfs_fs.h in the reiserfsprogs source
				m = string.rstrip(buf[52:61], "\0x00")
				if m == "ReIsErFs" or m == "ReIsEr2Fs" or m == "ReIsEr3Fs":
					# this reads reiserfs_super_block.s_label as
					# defined in include/reiserfs_fs.h
					label = string.rstrip(buf[100:116], "\0x00")
					os.close(fd)
					return label
			except OSError, e:
				# [Error 22] probably means we're trying to read an
				# extended partition. 
				log.debug("error reading reiserfs label on %s: %s" %(device, e))
				
				try:
					os.close(fd)
				except:
					pass
				
				return label
	
	os.close(fd)
	return label

def readReiserFSLabel(device):
	label = readReiserFSLabel_int(device)
	return label

def readFSLabel(device):
	if not device.startswith("/dev/"):
		device = "/dev/%s" % device
	
	label = readExt2Label(device)
	if label is None:
		label = readSwapLabel(device)
	if label is None:
		label = readXFSLabel(device)
	if label is None:
		label = readReiserFSLabel(device)
	return label

def ext2Clobber(device):
	if not device.startswith("/dev/"):
		device = "/dev/%s" % device
	_isys.e2fsclobber(device)

def ext2IsDirty(device):
	label = _isys.e2dirty(device)
	return label

def ext2HasJournal(device):
	hasjournal = _isys.e2hasjournal(device)
	return hasjournal

def ejectCdrom(device):
	fd = os.open(device, os.O_RDONLY|os.O_NONBLOCK)

	# this is a best effort
	try:
		_isys.ejectcdrom(fd)
	except SystemError, e:
		log.warning("error ejecting cdrom (%s): %s" %(device, e))
	pass

	os.close(fd)

def driveUsesModule(device, modules):
	"""Returns true if a drive is using a prticular module.  Only works
	   for SCSI devices right now."""
	if not isinstance(modules, ().__class__) and not \
			isinstance(modules, [].__class__):
		modules = [modules]
        
	if device[:2] == "hd":
		return False
	rc = False
	if os.access("/tmp/scsidisks", os.R_OK):
		sdlist=open("/tmp/scsidisks", "r")
		sdlines = sdlist.readlines()
		sdlist.close()
		for l in sdlines:
			try:
				# each line has format of:  <device>  <module>
				(sddev, sdmod) = string.split(l)
				
				if sddev == device:
					if sdmod in modules:
						rc = True
						break
			except:
				pass
	return rc

def mediaPresent(device):
	try:
		fd = os.open("/dev/%s" % device, os.O_RDONLY)
	except OSError, (errno, strerror):
		# error 123 = No medium found
		if errno == 123:
			log.debug("No medium found on %s" % device)
			return False
		else:
			return True
	else:
		os.close(fd)
		return True

def vtActivate (num):
	_isys.vtActivate (num)

def isPsudoTTY(fd):
	return _isys.isPsudoTTY(fd)

def sync():
	return _isys.sync ()

def isIsoImage(file):
	return _isys.isisoimage(file)

def fbinfo():
	return _isys.fbinfo()

def cdRwList():
	if not os.access("/proc/sys/dev/cdrom/info", os.R_OK): return []
	
	f = open("/proc/sys/dev/cdrom/info", "r")
	lines = f.readlines()
	f.close()
	
	driveList = []
	finalDict = {}
	
	for line in lines:
		line = string.split(line, ':', 1)

		if (line and line[0] == "drive name"):
			line = string.split(line[1])
			# no CDROM drives
			if not line:  return []

			for device in line:
				if device[0:2] == 'sr':
					device = "scd" + device[2:]
					driveList.append(device)
				elif ((line and line[0] == "Can write CD-R") or
					(line and line[0] == "Can write CD-RW")):
					line = string.split(line[1])
					field = 0
					for ability in line:
						if ability == "1":
							finalDict[driveList[field]] = 1
							field = field + 1

	l = finalDict.keys()
	l.sort()
	return l

def ideCdRwList():
	newList = []
	for dev in cdRwList():
		if dev[0:2] == 'hd': newList.append(dev)

	return newList


handleSegv = _isys.handleSegv

printObject = _isys.printObject
bind_textdomain_codeset = _isys.bind_textdomain_codeset
isVioConsole = _isys.isVioConsole
