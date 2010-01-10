#!/usr/bin/python

import grp
import logging
import os
import random
import stat

import util
from constants import *
from logger import getLog

class Environment(object):
	def __init__(self, package):
		self.package = package
		self.config = config

		# Indication if we run in toolchain mode
		self.toolchain = self.package.toolchain

		# mount/umount
		self.umountCmds = []
		self.mountCmds = []
		
		if not self.toolchain:
			self.umountCmds.extend([
				"umount -n %s" % self.chrootPath("tools_i686"),
				"umount -n %s" % self.chrootPath("proc"),
				"umount -n %s" % self.chrootPath("sys"),
				"umount -n %s" % self.chrootPath("usr", "src", "cache"),
				"umount -n %s" % self.chrootPath("usr", "src", "packages"),
				"umount -n %s" % self.chrootPath("usr", "src", "pkgs"),
				"umount -n %s" % self.chrootPath("usr", "src", "src"),
				"umount -n %s" % self.chrootPath("usr", "src", "tools"),
			])
			self.mountCmds.extend([
				"mount -n --bind %s/tools_i686 %s" % (TOOLCHAINSDIR, self.chrootPath("tools_i686")),
				"mount -n -t proc naoki_chroot_proc %s" % self.chrootPath("proc"),
				"mount -n -t sysfs naoki_chroot_sysfs %s" % self.chrootPath("sys"),
				"mount -n --bind %s %s" % (os.path.join(CACHEDIR), self.chrootPath("usr", "src", "cache")),
				"mount -n --bind %s %s" % (os.path.join(PACKAGESDIR), self.chrootPath("usr", "src", "packages")),
				"mount -n --bind %s %s" % (os.path.join(PKGSDIR), self.chrootPath("usr", "src", "pkgs")),
				"mount -n --bind %s %s" % (os.path.join(BASEDIR, "src"), self.chrootPath("usr", "src", "src")),
				"mount -n --bind %s %s" % (os.path.join(TOOLSDIR), self.chrootPath("usr", "src", "tools")),
			])

		self.buildroot = "buildroot.%d" % random.randint(0, 1024)
		self.log = None
		self.__initialized = False

	def init(self):
		if self.__initialized:
			return
		try:
			self._init()
		except (KeyboardInterrupt, Exception):
			#self._callHooks('initfailed')
			raise
		self.__initialized = True

	def _init(self):
		self._setupLogging()

		if os.path.exists(self.chrootPath()):
			self.clean()

		# create dirs
		self.log.debug("Creating directories...")
		dirs = (
			CACHEDIR,
			PACKAGESDIR,
			self.chrootPath(self.buildroot),
			self.chrootPath("bin"),
			self.chrootPath("etc"),
			self.chrootPath("proc"),
			self.chrootPath("root"),
			self.chrootPath("sbin"),
			self.chrootPath("sys"),
			self.chrootPath("tmp"),
			self.chrootPath("tools_i686"),
			self.chrootPath("usr/src/cache"),
			self.chrootPath("usr/src/packages"),
			self.chrootPath("usr/src/pkgs"),
			self.chrootPath("usr/src/src"),
			self.chrootPath("usr/src/tools"),
			self.chrootPath("var/tmp"),
		)
		for item in dirs:
			util.mkdir(item)

		# touch files
		self.log.debug("Touching files...")
		files = (
			"etc/fstab",
			"etc/mtab",
		)
		for item in files:
			util.touch(self.chrootPath(item))

		self._setupDev()
		self._setupUsers()
		self._setupToolchain()

	def clean(self):
		util.rm(self.chrootPath())

	def make(self, target):
		file = self.package.filename
		if not self.toolchain:
			file = "/usr/src%s" % file[len(BASEDIR):]

		return self.doChroot("make -C %s -f %s %s" % \
			(os.path.dirname(file), file, target), shell=True)

	def doChroot(self, command, shell=True, *args, **kwargs):
		ret = None
		try:
			# XXX Should be globally defined
			env = config.environment.copy()
			env.update({
				"HOME"           : "/root",
				"BASEDIR"        : "/usr/src",
				"PKGROOT"        : "/usr/src/pkgs",
				"TOOLS_DIR"      : "/tools_i686",
				"TARGET"         : "i686-ipfire-linux-gnu",
				"TARGET_MACHINE" : "i686",
			})
			if self.toolchain:
				env.update({
					"PATH"           : "/tools_i686/sbin:/tools_i686/bin:%s" % os.environ["PATH"],
					"TOOLCHAIN"      : "1",
					"PKGROOT"        : PKGSDIR,
					"ROOT"           : self.chrootPath(),
					"BASEDIR"        : BASEDIR,
				})
			else:
				env.update({
					"PATH"           : "/sbin:/bin:/usr/sbin:/usr/bin:/tools_i686/sbin:/tools_i686/bin",
					"BUILDROOT"      : "/%s" % self.buildroot,
					"CHROOT"         : "1",
				})

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			self._mountall()
			
			if not self.toolchain and not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(command,
				shell=shell, env=env, logger=self.log, *args, **kwargs)

		finally:
			self._umountall()
		
		return ret

	do = doChroot

	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "environments", self.package.id, *args)

	path = chrootPath

	def _setupLogging(self):
		logfile = os.path.join(LOGDIR, self.package.id, "build.log")
		if not os.path.exists(os.path.dirname(logfile)):
			util.mkdir(os.path.dirname(logfile))
		self.log = logging.getLogger(self.package.id)
		fh = logging.FileHandler(logfile)
		fh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		fh.setLevel(logging.NOTSET)
		self.log.addHandler(fh)

	def _setupDev(self):
		if self.toolchain:
			return

		# files in /dev
		util.rm(self.chrootPath("dev"))
		util.mkdir(self.chrootPath("dev", "pts"))
		util.mkdir(self.chrootPath("dev", "shm"))
		prevMask = os.umask(0000)
		for i in (
				(stat.S_IFCHR | 0666, os.makedev(1, 3), "dev/null"),
				(stat.S_IFCHR | 0666, os.makedev(1, 7), "dev/full"),
				(stat.S_IFCHR | 0666, os.makedev(1, 5), "dev/zero"),
				(stat.S_IFCHR | 0666, os.makedev(1, 8), "dev/random"),
				(stat.S_IFCHR | 0444, os.makedev(1, 9), "dev/urandom"),
				(stat.S_IFCHR | 0666, os.makedev(5, 0), "dev/tty"),
				(stat.S_IFCHR | 0600, os.makedev(5, 1), "dev/console")
			):
			# create node
			os.mknod(self.chrootPath(i[2]), i[0], i[1])

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/dev/pts/ptmx", self.chrootPath("dev", "ptmx"))
		os.umask(prevMask)

		# mount/umount
		for devUnmtCmd in (
				"umount -n %s" % self.chrootPath("dev", "pts"),
				"umount -n %s" % self.chrootPath("dev", "shm")):
			if devUnmtCmd not in self.umountCmds:
				self.umountCmds.append(devUnmtCmd)

		mountopt = "gid=%d,mode=0620,ptmxmode=0666" % grp.getgrnam("tty").gr_gid
		if os.uname()[2] >= "2.6.29":
			mountopt += ",newinstance"

		for devMntCmd in (
				"mount -n -t devpts -o %s naoki_chroot_devpts %s" % (mountopt, self.chrootPath("dev", "pts")),
				"mount -n -t tmpfs naoki_chroot_shmfs %s" % self.chrootPath("dev", "shm")):
			if devMntCmd not in self.mountCmds:
				self.mountCmds.append(devMntCmd)

	def _setupUsers(self):
		if self.toolchain:
			return

		## XXX Could be done better
		self.log.debug("Creating users")
		f = open("/etc/passwd")
		for line in f.readlines():
			if line.startswith("root"):
				g = open(self.chrootPath("etc", "passwd"), "w")
				g.write("%s" % line)
				g.close()
				break
		f.close()

		f = open("/etc/group")
		for line in f.readlines():
			if line.startswith("root"):
				g = open(self.chrootPath("etc", "group"), "w")
				g.write("%s" % line)
				g.close()
				break
		f.close()

	def _setupToolchain(self):
		symlinks = (
			"bin/bash",
			"bin/sh",
			"bin/pwd",
		)
		for symlink in symlinks:
			if os.path.exists(self.chrootPath(symlink)):
				continue
			self.log.debug("Creating symlink /%s" % symlink)
			os.symlink("/tools_i686/%s" % symlink, self.chrootPath(symlink))

	def _mountall(self):
		"""mount 'normal' fs like /dev/ /proc/ /sys"""
		for cmd in self.mountCmds:
			util.do(cmd, shell=True)

	def _umountall(self):
		"""umount all mounted chroot fs."""
		for cmd in self.umountCmds:
			util.do(cmd, raiseExc=0, shell=True)
