#!/usr/bin/python

import grp
import logging
import os
import random
import stat

import package
import util
from constants import *
from exception import *
from logger import getLog

class Environment(object):
	def __init__(self, package):
		self.package = package
		self.config = config

		self.toolchain = Toolchain()

		# mount/umount
		self.umountCmds = [
			"umount -n %s" % self.chrootPath("proc"),
			"umount -n %s" % self.chrootPath("sys"),
			"umount -n %s" % self.chrootPath("usr", "src", "cache"),
			"umount -n %s" % self.chrootPath("usr", "src", "packages"),
			"umount -n %s" % self.chrootPath("usr", "src", "pkgs"),
			"umount -n %s" % self.chrootPath("usr", "src", "src"),
			"umount -n %s" % self.chrootPath("usr", "src", "tools"),
		]
		self.mountCmds = [
			"mount -n -t proc naoki_chroot_proc %s" % self.chrootPath("proc"),
			"mount -n -t sysfs naoki_chroot_sysfs %s" % self.chrootPath("sys"),
			"mount -n --bind %s %s" % (os.path.join(CACHEDIR), self.chrootPath("usr", "src", "cache")),
			"mount -n --bind %s %s" % (os.path.join(PACKAGESDIR), self.chrootPath("usr", "src", "packages")),
			"mount -n --bind %s %s" % (os.path.join(PKGSDIR), self.chrootPath("usr", "src", "pkgs")),
			"mount -n --bind %s %s" % (os.path.join(BASEDIR, "src"), self.chrootPath("usr", "src", "src")),
			"mount -n --bind %s %s" % (os.path.join(TOOLSDIR), self.chrootPath("usr", "src", "tools")),
		]

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

		self.log.info("Setting up environment %s..." % self.chrootPath())

		if os.path.exists(self.chrootPath()):
			self.clean()

		# create dirs
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
		files = (
			"etc/fstab",
			"etc/mtab",
		)
		for item in files:
			util.touch(self.chrootPath(item))

		self._setupDev()
		self._setupUsers()

		self.toolchain.extract(self.chrootPath())

		self.extractAll()

		self.toolchain.adjust(self.chrootPath())

	def clean(self):
		util.rm(self.chrootPath())

	def make(self, target):
		file = "/usr/src%s" % self.package.filename[len(BASEDIR):]

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
				"PATH"           : "/sbin:/bin:/usr/sbin:/usr/bin:/tools_i686/sbin:/tools_i686/bin",
				"BUILDROOT"      : "/%s" % self.buildroot,
				"CHROOT"         : "1",
			})

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			self._mountall()
			
			if not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(command,
				shell=shell, env=env, logger=self.log, *args, **kwargs)

		finally:
			self._umountall()
		
		return ret

	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "environments", self.package.id, *args)

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

	def _mountall(self):
		"""mount 'normal' fs like /dev/ /proc/ /sys"""
		for cmd in self.mountCmds:
			util.do(cmd, shell=True)

	def _umountall(self):
		"""umount all mounted chroot fs."""
		for cmd in self.umountCmds:
			util.do(cmd, raiseExc=0, shell=True)

	def extractAll(self):
		packages = self.package.deps + self.package.build_deps
		for pkg in config["mandatory_packages"]:
			pkg = package.find(pkg)
			if not pkg in packages:
				packages.append(pkg)

		packages = package.depsolve(packages, recursive=True)

		for pkg in packages:
			pkg.extract(self.chrootPath())

	def build(self):
		self.package.download()
		self.init()

		try:
			self.make("package")
		except Error:
			if config["cleanup_on_failure"]:
				self.clean()
			raise

		if config["cleanup_on_success"]:
			self.clean()


class Toolchain(object):
	arch = "i686"

	def __init__(self):
		util.mkdir(TOOLCHAINSDIR)

		# Create a filename object
		self.filename = "toolchain-i686.%s.tar.gz" % config["toolchain_version"]

		# Store the path including the filename
		self.path = os.path.join(TOOLCHAINSDIR, self.filename)

		self.build_dir = os.path.join(BUILDDIR, "toolchains",
			"tools_i686.%s" % config["toolchain_version"])

		self.log = getLog()

	@property
	def exists(self):
		return os.path.exists(self.path)

	def download(self):
		self.log.info("Downloading toolchain...")
		pass

	def cmd(self, args=[]):
		cmd = "%s" % os.path.join(TOOLSDIR, "toolchain")
		if args:
			cmd += " "
			cmd += " ".join(args)
		util.do(cmd, cwd=self.build_dir, shell=True,
			env={ "TOOLS_DIR" : self.build_dir })

	# TODO:
	#	- logging
	def make(self, pkg, target):
		env = config.environment.copy()
		env.update({
			"BASEDIR"        : BASEDIR,
			"PATH"           : "/tools_i686/sbin:/tools_i686/bin:%s" % os.environ["PATH"],
			"PKGROOT"        : PKGSDIR,
			"ROOT"           : self.build_dir,
			"TARGET"         : "i686-ipfire-linux-gnu",
			"TARGET_MACHINE" : "i686",
			"TOOLCHAIN"      : "1",
			"TOOLS_DIR"      : "/tools_i686",
		})

		command = "make -C %s -f %s %s" % \
			(os.path.dirname(pkg.filename), pkg.filename, target)

		return util.do(command, shell=True, env=env)

	def build_package(self, pkg):
		self.log.debug("Building %s..." % pkg.name)

		source_dir = os.path.join(self.build_dir, "usr/src")

		util.rm(source_dir)
		util.mkdir(source_dir)

		self.checkLink()

		return self.make(pkg, "package")

	def compress(self):
		self.cmd(["compress", self.path, self.build_dir])

	def extract(self, path):
		self.cmd(["extract", self.path, os.path.join(path, "tools_i686")])

	def adjust(self, path):
		self.cmd(["adjust", path])

	def build(self):
		self.log.info("Building toolchain...")

		packages = package.depsort(package.list(toolchain=True))
		for pkg in packages:
			if pkg.isBuilt:
				continue
			self.build_package(pkg)
		self.compress()

	def checkLink(self):
		link = "/tools_%s" % self.arch
		destination = os.path.abspath(self.build_dir)

		if not os.path.islink(link):
			# File is not a link. Remove it...
			util.rm(link)

		else:
			# If link points to correct destination we break up
			if os.path.abspath(os.readlink(link)) == destination:
				return
			os.unlink(link)


		os.symlink(destination, link)
