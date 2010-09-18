#!/usr/bin/python

import grp
import logging
import os
import stat

import logger
import mail
import util

from constants import *

# XXX to be moved to somewhere else
ENVIRONMENT_ARGS = ["PATH", "PWD" ]

def set(e):
	env = {}

	for key in ENVIRONMENT_ARGS:
		if os.environ.has_key(key):
			env[key] = os.environ[key]

	env.update(config.environment)
	env.update(e)

	return env


class _Environment(object):
	kernel_version = os.uname()[2]

	def __init__(self, arch):
		self.arch = arch

		logging.debug("Successfully initialized %s" % self)

		# XXX check if already locked
		self.prepare()

	def chrootPath(self, *args):
		raise NotImplementedError

	def clean(self):
		logging.debug("Cleaning environment %s" % self)
		if os.path.exists(self.chrootPath()):
			util.rm(self.chrootPath())
	
	def prepare(self):
		self.clean()

		logging.debug("Preparing environment %s" % self)

		dirs = (
			CACHEDIR,
			CCACHEDIR,
			IMAGESDIR,
			PACKAGESDIR,
			"dev",
			"dev/pts",
			"dev/shm",
			"proc",
			"root",
			"sys",
			"tmp",
			"usr/src",
			"usr/src/cache",
			"usr/src/ccache",
			"usr/src/images",
			"usr/src/packages",
			"usr/src/pkgs",
			"usr/src/src",
			"usr/src/tools",
			"var/tmp",
		)

		for dir in dirs:
			util.mkdir(self.chrootPath(dir))

		files = (
			"etc/fstab",
			"etc/mtab"
		)

		for file in files:
			file = self.chrootPath(file)
			dir = os.path.dirname(file)
			if not os.path.exists(dir):
				util.mkdir(dir)
			util.touch(file)

		# Prepare the other stuff
		self._prepare_dev()
		self._prepare_users()
		self._prepare_dns()

	def _prepare_dev(self):
		prevMask = os.umask(0000)

		devNodes = [
			(stat.S_IFCHR | 0666, os.makedev(1, 3), "dev/null"),
			(stat.S_IFCHR | 0666, os.makedev(1, 7), "dev/full"),
			(stat.S_IFCHR | 0666, os.makedev(1, 5), "dev/zero"),
			(stat.S_IFCHR | 0666, os.makedev(1, 8), "dev/random"),
			(stat.S_IFCHR | 0444, os.makedev(1, 9), "dev/urandom"),
			(stat.S_IFCHR | 0666, os.makedev(5, 0), "dev/tty"),
			(stat.S_IFCHR | 0600, os.makedev(5, 1), "dev/console")
		]

		# make device node for el4 and el5
		if self.kernel_version < "2.6.19":
			devNodes.append((stat.S_IFCHR | 0666, os.makedev(5, 2), "dev/ptmx"))

		for i in devNodes:
			# create node
			os.mknod(self.chrootPath(i[2]), i[0], i[1])

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/proc/self/fd", self.chrootPath("dev", "fd"))

		if self.kernel_version >= "2.6.19":
			os.symlink("/dev/pts/ptmx", self.chrootPath("dev", "ptmx"))

		os.umask(prevMask)

	def _prepare_users(self):
		f = open(self.chrootPath("etc", "passwd"), "w")
		f.write("root:x:0:0:root:/root:/bin/bash\n")
		f.write("nobody:x:99:99:Nobody:/:/sbin/nologin\n")
		f.close()

		f = open(self.chrootPath("etc", "group"), "w")
		f.write("root:x:0:root\n")
		f.write("nobody:x:99:\n")
		f.close()

	def _prepare_dns(self):
		# XXX to be replaced
		nameservers = []
		f = open("/etc/resolv.conf")
		for line in f.readlines():
			if line.startswith("nameserver"):
				nameservers.append(line.split(" ")[-1].strip())
		f.close()

		logging.debug("Using nameservers: %s" % nameservers)

		f = open(self.chrootPath("etc", "resolv.conf"), "w")
		for nameserver in nameservers:
			f.write("nameserver %s" % nameserver)
		f.close()

		logging.debug("Creating record for localhost")
		f = open(self.chrootPath("etc", "hosts"), "w")
		f.write("127.0.0.1 localhost\n")
		f.close()

	def extract(self, package, *args):
		logging.info("Extracting %s" % package)

		package.extract(self.chrootPath(*args))

	def variables(self):
		env = set({
			"HOME"           : "/root",
			"PATH"           : "/sbin:/bin:/usr/sbin:/usr/bin",
			"BASEDIR"        : "/usr/src",
			"PKGROOT"        : "/usr/src/pkgs",
			"TARGET"         : "%s-ipfire-linux-gnu" % self.arch.machine,
			"TARGET_MACHINE" : self.arch.machine,
			"CHROOT"         : "1", # XXX to be removed
			"CFLAGS"         : self.arch.cflags,
			"CXXFLAGS"       : self.arch.cxxflags,
			"PKG_ARCH"       : self.arch.name,
		})

		# Settings for ccache
		env.update({
			"PATH" : "/usr/ccache/bin:%s" % env["PATH"],
			"CCACHE_COMPILERCHECK" : "none",
			"CCACHE_COMPRESS" : "1",
			"CCACHE_DIR" : "/usr/src/ccache",
		})

		return env

	def doChroot(self, command, shell=True, *args, **kwargs):
		ret = None
		try:
			env = self.variables()

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			self._mountall()

			if not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(command,
				personality=self.arch.personality,
				shell=shell,
				env=env,
				logger=self.logger,
				*args, **kwargs)

		finally:
			self._umountall()

		return ret

	def _mountall(self):
		logging.debug("Mounting environment")
		for cmd in self.mountCmds:
			util.do(cmd, shell=True)

	def _umountall(self):
		logging.debug("Umounting environment")
		for cmd in self.umountCmds:
			util.do(cmd, raiseExc=0, shell=True)

	@property
	def umountCmds(self):
		return (
			"umount -n %s" % self.chrootPath("proc"),
			"umount -n %s" % self.chrootPath("sys"),
			"umount -n %s" % self.chrootPath("usr", "src", "cache"),
			"umount -n %s" % self.chrootPath("usr", "src", "ccache"),
			"umount -n %s" % self.chrootPath("usr", "src", "images"),
			"umount -n %s" % self.chrootPath("usr", "src", "packages"),
			"umount -n %s" % self.chrootPath("usr", "src", "pkgs"),
			"umount -n %s" % self.chrootPath("usr", "src", "src"),
			"umount -n %s" % self.chrootPath("usr", "src", "tools"),
			"umount -n %s" % self.chrootPath("dev", "pts"),
			"umount -n %s" % self.chrootPath("dev", "shm")
		)

	@property
	def mountCmds(self):
		ret = [
			"mount -n -t proc naoki_chroot_proc %s" % self.chrootPath("proc"),
			"mount -n -t sysfs naoki_chroot_sysfs %s" % self.chrootPath("sys"),
			"mount -n --bind %s %s" % (CACHEDIR, self.chrootPath("usr", "src", "cache")),
			"mount -n --bind %s %s" % (CCACHEDIR, self.chrootPath("usr", "src", "ccache")),
			"mount -n --bind %s %s" % (IMAGESDIR, self.chrootPath("usr", "src", "images")),
			"mount -n --bind %s %s" % (PACKAGESDIR, self.chrootPath("usr", "src", "packages")),
			"mount -n --bind %s %s" % (PKGSDIR, self.chrootPath("usr", "src", "pkgs")),
			"mount -n --bind %s %s" % (os.path.join(BASEDIR, "src"), self.chrootPath("usr", "src", "src")),
			"mount -n --bind %s %s" % (TOOLSDIR, self.chrootPath("usr", "src", "tools")),
		]

		mountopt = "gid=%d,mode=0620,ptmxmode=0666" % grp.getgrnam("tty").gr_gid
		if self.kernel_version >= "2.6.29":
			mountopt += ",newinstance"

		ret.extend([
			"mount -n -t devpts -o %s naoki_chroot_devpts %s" % (mountopt, self.chrootPath("dev", "pts")),
			"mount -n -t tmpfs naoki_chroot_shmfs %s" % self.chrootPath("dev", "shm")])

		return ret

	@property
	def logger(self):
		return logging.getLogger()


class Build(_Environment):
	def __init__(self, package, build_id=None):
		self.package = package
		self.build_id = build_id

		_Environment.__init__(self, self.package.arch)

	@property
	def logger(self):
		return logging.getLogger() # XXX just for now

	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "environments", self.package.id, *args)

	@property
	def buildroot(self):
		if not hasattr(self, "__buildroot"):
			self.__buildroot = "buildroot.%s" % util.random_string()

		return self.__buildroot

	def variables(self):
		v = _Environment.variables(self)
		v.update({
			"BUILDROOT" : "/%s" % self.buildroot,
			"BUILD_ID"  : self.build_id or "",
		})
		return v

	def build(self, *args, **kwargs):
		try:
			self.make("package")
		except:
			if config["cleanup_on_failure"]:
				self.clean()

			# Send email report about an error
			mail.report_error(self.package)
			raise

		if config["cleanup_on_success"]:
			self.clean()

	def make(self, target):
		file = "/usr/src%s" % self.package.filename[len(BASEDIR):]

		return self.doChroot("make -C %s -f %s %s" % \
			(os.path.dirname(file), file, target), shell=True)

	def shell(self, args=[]):
		command = "chroot %s /usr/src/tools/chroot-shell %s" % \
			(self.chrootPath(), " ".join(args))

		for key, val in self.variables().items():
			command = "%s=\"%s\" " % (key, val) + command

		if self.package.source_dir:
			command = "SOURCE_DIR=%s %s" % (self.package.source_dir, command)

		logging.debug("Shell command: %s" % command)

		try:
			self._mountall()

			shell = os.system(command)
			return os.WEXITSTATUS(shell)

		finally:
			self._umountall()

			# Clean up the environment
			self.clean()
