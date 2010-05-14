#!/usr/bin/python

import fcntl
import grp
import logging
import os
import random
import shutil
import stat
import time

import backend
import util
from constants import *
from exception import *
from logger import getLog

class Environment(object):
	kernel_version = os.uname()[2]

	def __init__(self, naoki, arch=arches.current):
		self.arch = arch
		self.config = config
		self.naoki = naoki

		self.initialized = False
		self.__buildroot = None

		self.toolchain = Toolchain(self.arch["name"])

		# Create initial directory that we can set the lock
		util.mkdir(self.chrootPath())

		# Lock environment. Throws exception if function cannot set the lock.
		self.lock()

	def init(self, clean=True):
		marker = self.chrootPath(".initialized")
		self.log.debug("Initialize environment %s..." % self.chrootPath())

		if clean:
			self.clean()

		# If marker exists, we won't reinit again
		if os.path.exists(marker):
			return

		# create dirs
		dirs = (
			CACHEDIR,
			CCACHEDIR,
			IMAGESDIR,
			PACKAGESDIR,
			self.chrootPath("bin"),
			self.chrootPath("etc"),
			self.chrootPath("proc"),
			self.chrootPath("root"),
			self.chrootPath("sbin"),
			self.chrootPath("sys"),
			self.chrootPath("tmp"),
			self.chrootPath("tools_%s" % self.arch["name"]),
			self.chrootPath("usr/src/cache"),
			self.chrootPath("usr/src/ccache"),
			self.chrootPath("usr/src/images"),
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
		self._setupDns()

		self.toolchain.extract(self.chrootPath())

		self.extractAll()

		self.toolchain.adjust(self.chrootPath())

		# Set marker
		util.touch(marker)

	@property
	def buildroot(self):
		if not self.__buildroot:
			self.__buildroot = "buildroot.%s" % util.random_string()

		return self.__buildroot

	def lock(self):
		self.log.debug("Trying to lock environment")

		try:
			self._lock = open(self.chrootPath(".lock"), "a+")
		except IOError, e:
			return 0

		try:
			fcntl.lockf(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
		except IOError, e:
			raise BuildRootLocked, "Environment is locked by another process"

		return 1

	def clean(self):
		if os.path.exists(self.chrootPath()):
			util.rm(self.chrootPath())

	@property
	def environ(self):
		env = config.environment.copy()
		env.update({
			"HOME"           : "/root",
			"BASEDIR"        : "/usr/src",
			"PKGROOT"        : "/usr/src/pkgs",
			"TOOLS_DIR"      : "/tools_%s" % self.arch["name"],
			"TARGET"         : "%s-ipfire-linux-gnu" % self.arch["machine"],
			"TARGET_MACHINE" : self.arch["machine"],
			"PATH"           : CHROOT_PATH + ":/tools_%(arch)s/sbin:/tools_%(arch)s/bin" \
								 % { "arch" : self.arch["name"], },
			"BUILDROOT"      : "/%s" % self.buildroot,
			"CHROOT"         : "1",
			"CFLAGS"         : self.arch["cflags"],
			"CXXFLAGS"       : self.arch["cxxflags"],
			"PKG_ARCH"       : self.arch["name"],
		})

		ccache_path = os.path.join("tools_%s" % self.arch["name"],
			"usr", "ccache", "bin")
		if os.path.exists(self.chrootPath(ccache_path)):
			env.update({
				"PATH" : "/%s:%s" % (ccache_path, env["PATH"]),
				"CCACHE_DIR" : "/usr/src/ccache",
			})

		return env

	def doChroot(self, command, shell=True, *args, **kwargs):
		ret = None
		try:
			env = self.environ

			if kwargs.has_key("env"):
				env.update(kwargs.pop("env"))

			self._mountall()

			if not kwargs.has_key("chrootPath"):
				kwargs["chrootPath"] = self.chrootPath()

			ret = util.do(command, personality=self.arch["personality"],
				shell=shell, env=env, logger=self.log, *args, **kwargs)

		finally:
			self._umountall()

		return ret

	def chrootPath(self, *args):
		raise NotImplementedError

	def _setupDev(self):
		self.log.debug("Setting up /dev and /proc")

		# files in /dev
		util.rm(self.chrootPath("dev"))
		util.mkdir(self.chrootPath("dev", "pts"))
		util.mkdir(self.chrootPath("dev", "shm"))
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

	def _setupUsers(self):
		self.log.debug("Creating users")
		f = open(self.chrootPath("etc", "passwd"), "w")
		f.write("root:x:0:0:root:/root:/bin/bash\n")
		f.write("nobody:x:99:99:Nobody:/:/sbin/nologin\n")
		f.close()

		f = open(self.chrootPath("etc", "group"), "w")
		f.write("root:x:0:root\n")
		f.write("nobody:x:99:\n")
		f.close()

	def _setupDns(self):
		self.log.debug("Setting up DNS")
		nameservers = []
		f = open("/etc/resolv.conf")
		for line in f.readlines():
			if line.startswith("nameserver"):
				nameservers.append(line.split(" ")[-1])
		f.close()

		self.log.debug("Using nameservers: %s" % nameservers)

		f = open(self.chrootPath("etc", "resolv.conf"), "w")
		for nameserver in nameservers:
			f.write("nameserver %s" % nameserver)
		f.close()

		self.log.debug("Creating record for localhost")
		f = open(self.chrootPath("etc", "hosts"), "w")
		f.write("127.0.0.1 localhost\n")
		f.close()

	def _mountall(self):
		"""mount 'normal' fs like /dev/ /proc/ /sys"""
		self.log.debug("Mounting chroot")
		for cmd in self.mountCmds:
			util.do(cmd, shell=True)

	def _umountall(self):
		"""umount all mounted chroot fs."""
		self.log.debug("Umounting chroot")
		for cmd in self.umountCmds:
			util.do(cmd, raiseExc=0, shell=True)

	@property
	def log(self):
		return getLog()

	def shell(self, args=[]):
		command = "chroot %s /usr/src/tools/chroot-shell %s" % \
			(self.chrootPath(), " ".join(args))

		for key, val in self.environ.items():
			command = "%s=\"%s\" " % (key, val) + command

		try:
			self._mountall()

			shell = os.system(command)
			return os.WEXITSTATUS(shell)

		finally:
			self._umountall()

	@property
	def umountCmds(self):
		ret = (
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

		return ret

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

	def extractAll(self):
		raise NotImplementedError


class PackageEnvironment(Environment):
	def __init__(self, package, *args, **kwargs):
		self.package = package

		Environment.__init__(self, naoki=package.naoki, *args, **kwargs)

	def build(self):
		self.log.debug(LOG_MARKER)

		self.package.download()

		# Save start time
		time_start = time.time()

		try:
			self.make("package")
		except Error:
			if config["cleanup_on_failure"]:
				self.clean()
			backend.report_error_by_mail(self.package)
			raise

		time_end = time.time()
		self.log.debug("Package build took %.2fs" % (time_end - time_start))

		if config["cleanup_on_success"]:
			self.clean()

	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "environments", self.package.info.id, *args)

	def extractAll(self):
		packages = [p.getPackage(self.naoki) \
			for p in self.package.info.dependencies_all]

		for package in packages:
			package.extract(self.chrootPath())

	def make(self, target):
		file = "/usr/src%s" % self.package.info.filename[len(BASEDIR):]

		return self.doChroot("make -C %s -f %s %s" % \
			(os.path.dirname(file), file, target), shell=True)

	@property
	def log(self):
		return self.package.log


class ShellEnvironment(Environment):
	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "environments", "shell", *args)

	def extractAll(self):
		pass


class Toolchain(object):
	def __init__(self, arch):
		util.mkdir(TOOLCHAINSDIR)

		self.arch = arches[arch]

		# Create a filename object
		self.filename = "toolchain-%s.%s.tar.gz" % \
			(self.arch["name"], config["toolchain_version"],)

		# Store the path including the filename
		self.path = os.path.join(TOOLCHAINSDIR, self.filename)

		self.build_dir = os.path.join(BUILDDIR, "toolchains",
			"tools_%s.%s" % (self.arch["name"], config["toolchain_version"]))

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
		util.do(cmd, cwd=self.build_dir, shell=True, logger=self.log,
			env={ "TOOLS_DIR" : self.build_dir })

	# TODO:
	#	- logging
	def make(self, pkg, target):
		env = config.environment.copy()
		env.update({
			"BASEDIR"        : BASEDIR,
			"PATH"           : "/tools_%(arch)s/sbin:/tools_%(arch)s/bin:%(path)s" % \
								{ "arch" : self.arch["name"], "path" : os.environ["PATH"], },
			"PKGROOT"        : PKGSDIR,
			"ROOT"           : self.build_dir,
			"TARGET"         : "%s-ipfire-linux-gnu" % self.arch["machine"],
			"TARGET_MACHINE" : self.arch["machine"],
			"TOOLCHAIN"      : "1",
			"TOOLS_DIR"      : "/tools_%s" % self.arch["name"],
			
			"CFLAGS"         : self.arch["cflags"],
			"CXXFLAGS"       : self.arch["cxxflags"],
		})

		command = "make -C %s -f %s %s" % \
			(os.path.dirname(pkg.filename), pkg.filename, target)

		return util.do(command, shell=True, env=env, personality=self.arch["personality"],
			logger=self.log)

	def build_package(self, pkg):
		self.log.info("Building %s..." % pkg.name)

		source_dir = os.path.join(self.build_dir, "usr/src")

		util.rm(source_dir)
		util.mkdir(source_dir)

		self.checkLink()

		return self.make(pkg, "package")

	def compress(self):
		self.cmd(["compress", self.path, self.build_dir])

	def extract(self, path):
		self.cmd(["extract", self.path, os.path.join(path, "tools_%s" % self.arch["name"])])

	def adjust(self, path):
		self.cmd(["adjust", path])

	def build(self, naoki):
		self.log.info("Building toolchain...")

		packages = backend.get_package_names(toolchain=True)
		packages = backend.parse_package(packages, toolchain=True, naoki=naoki)
		packages = backend.depsort(packages)
		for pkg in packages:
			if os.path.exists(os.path.join(self.path, pkg.name)):
				continue
			self.build_package(pkg)
		self.compress()

	def checkLink(self):
		link = "/tools_%s" % self.arch["name"]
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


class Generator(Environment):
	def __init__(self, naoki, arch, type):
		self.type = type
		Environment.__init__(self, naoki, arch)

	def chrootPath(self, *args):
		return os.path.join(BUILDDIR, "generators", self.type, self.arch["name"], *args)

	def run(self):
		self.init()

		# Extracting installer packages
		util.mkdir(self.chrootPath("installer"))

		for package in self.get_packages("installer"):
			package.extract(self.chrootPath("installer"))

		all_package_files = []
		for package in self.get_packages("all"):
			all_package_files.extend(package.package_files)

		self.doChroot("/usr/src/tools/generator %s" % self.type,
			env={"ALL_PACKAGES" : " ".join(all_package_files)})

	def get_packages(self, type):
		_packages = {
			"all" : backend.get_package_names(),
			"build" : [ "arping", "bash", "coreutils", "cpio", "curl",
				"dhcp", "findutils", "grep", "iproute2", "iputils", "kbd",
				"less", "module-init-tools", "procps", "sed", "sysvinit",
				"udev", "util-linux-ng", "which", "dvdrtools", "kernel", 
				"squashfs-tools", "syslinux", "zlib",],
			"installer" : ["initscripts", "kernel", "pomona", "upstart"],
		}
		_package_infos = backend.parse_package_info(_packages[type])

		packages = []
		for package in backend.depsolve(_package_infos, recursive=True):
			package = package.getPackage(self.naoki)
			if not package in packages:
				packages.append(package)

		return packages

	def extractAll(self):
		# Extract required tools
		for package in self.get_packages("build"):
			package.extract(self.chrootPath())
