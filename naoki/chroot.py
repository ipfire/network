#!/usr/bin/python

import grp
import logging
import os
import random
import stat

import backend
import util
from constants import *
from exception import *
from logger import getLog

class Environment(object):
	def __init__(self, package):
		self.package = package
		self.naoki = self.package.naoki

		self.arch = arches.current
		self.config = config

		self.toolchain = Toolchain(self.arch["name"])

		# mount/umount
		self.umountCmds = [
			"umount -n %s" % self.chrootPath("proc"),
			"umount -n %s" % self.chrootPath("sys"),
			"umount -n %s" % self.chrootPath("usr", "src", "cache"),
			"umount -n %s" % self.chrootPath("usr", "src", "ccache"),
			"umount -n %s" % self.chrootPath("usr", "src", "packages"),
			"umount -n %s" % self.chrootPath("usr", "src", "pkgs"),
			"umount -n %s" % self.chrootPath("usr", "src", "src"),
			"umount -n %s" % self.chrootPath("usr", "src", "tools"),
		]
		self.mountCmds = [
			"mount -n -t proc naoki_chroot_proc %s" % self.chrootPath("proc"),
			"mount -n -t sysfs naoki_chroot_sysfs %s" % self.chrootPath("sys"),
			"mount -n --bind %s %s" % (os.path.join(CACHEDIR), self.chrootPath("usr", "src", "cache")),
			"mount -n --bind %s %s" % (os.path.join(CCACHEDIR), self.chrootPath("usr", "src", "ccache")),
			"mount -n --bind %s %s" % (os.path.join(PACKAGESDIR), self.chrootPath("usr", "src", "packages")),
			"mount -n --bind %s %s" % (os.path.join(PKGSDIR), self.chrootPath("usr", "src", "pkgs")),
			"mount -n --bind %s %s" % (os.path.join(BASEDIR, "src"), self.chrootPath("usr", "src", "src")),
			"mount -n --bind %s %s" % (os.path.join(TOOLSDIR), self.chrootPath("usr", "src", "tools")),
		]

		self.buildroot = "buildroot.%d" % random.randint(0, 1024)

		self.log.debug("Setting up environment %s..." % self.chrootPath())

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
			self.chrootPath("tools_%s" % self.arch["name"]),
			self.chrootPath("usr/src/cache"),
			self.chrootPath("usr/src/ccache"),
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
		file = "/usr/src%s" % self.package.info.filename[len(BASEDIR):]

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
				"TOOLS_DIR"      : "/tools_%s" % self.arch["name"],
				"TARGET"         : "%s-ipfire-linux-gnu" % self.arch["machine"],
				"TARGET_MACHINE" : self.arch["machine"],
				"PATH"           : "/sbin:/bin:/usr/sbin:/usr/bin:/tools_%(arch)s/sbin:/tools_%(arch)s/bin" \
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
		return os.path.join(BUILDDIR, "environments", self.package.info.id, *args)

	def _setupDev(self):
		# files in /dev
		util.rm(self.chrootPath("dev"))
		util.mkdir(self.chrootPath("dev", "pts"))
		util.mkdir(self.chrootPath("dev", "shm"))
		prevMask = os.umask(0000)

		kernel_version = os.uname()[2]
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
		if kernel_version < "2.6.19":
			devNodes.append((stat.S_IFCHR | 0666, os.makedev(5, 2), "dev/ptmx"))

		for i in devNodes:
			# create node
			os.mknod(self.chrootPath(i[2]), i[0], i[1])

		os.symlink("/proc/self/fd/0", self.chrootPath("dev", "stdin"))
		os.symlink("/proc/self/fd/1", self.chrootPath("dev", "stdout"))
		os.symlink("/proc/self/fd/2", self.chrootPath("dev", "stderr"))
		os.symlink("/proc/self/fd", self.chrootPath("dev", "fd"))

		if kernel_version >= "2.6.19":
			os.symlink("/dev/pts/ptmx", self.chrootPath("dev", "ptmx"))

		os.umask(prevMask)

		# mount/umount
		for devUnmtCmd in (
				"umount -n %s" % self.chrootPath("dev", "pts"),
				"umount -n %s" % self.chrootPath("dev", "shm")):
			if devUnmtCmd not in self.umountCmds:
				self.umountCmds.append(devUnmtCmd)

		mountopt = "gid=%d,mode=0620,ptmxmode=0666" % grp.getgrnam("tty").gr_gid
		if kernel_version >= "2.6.29":
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
		g = open(self.chrootPath("etc", "passwd"), "w")
		for line in f.readlines():
			if line.startswith("root") or line.startswith("nobody"):
				g.write("%s" % line)
		g.close()
		f.close()

		f = open("/etc/group")
		g = open(self.chrootPath("etc", "group"), "w")
		for line in f.readlines():
			if line.startswith("root") or line.startswith("nobody"):
				g.write("%s" % line)
		g.close()
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
		packages = [p.getPackage(self.naoki) \
			for p in self.package.info.dependencies_all]

		for package in packages:
			package.extract(self.chrootPath())

	def build(self):
		self.package.download()

		try:
			self.make("package")
		except Error:
			if config["cleanup_on_failure"]:
				self.clean()
			raise

		if config["cleanup_on_success"]:
			self.clean()

	@property
	def log(self):
		return self.package.log


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
		util.do(cmd, cwd=self.build_dir, shell=True,
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

	def build(self):
		self.log.info("Building toolchain...")

		packages = backend.get_package_names(toolchain=True)
		packages = backend.parse_package(packages, toolchain=True)
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
