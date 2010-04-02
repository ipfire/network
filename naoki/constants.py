#!/usr/bin/python

import ConfigParser
import math
import os

BASEDIR = os.getcwd()

BUILDDIR = os.path.join(BASEDIR, "build")
CACHEDIR = os.path.join(BASEDIR, "cache")
CCACHEDIR = os.path.join(BASEDIR, "ccache")
CONFIGDIR = os.path.join(BASEDIR, "config")
DOCDIR = os.path.join(BASEDIR, "doc")
LOGDIR = os.path.join(BASEDIR, "logs")
PKGSDIR = os.path.join(BASEDIR, "pkgs")
PACKAGESDIR = os.path.join(BUILDDIR, "packages")
REPOSDIR = os.path.join(BUILDDIR, "repositories")
TOOLSDIR = os.path.join(BASEDIR, "tools")

TARBALLDIR = os.path.join(CACHEDIR, "tarballs")
TOOLCHAINSDIR = os.path.join(CACHEDIR, "toolchains")
PATCHESDIR = os.path.join(CACHEDIR, "patches")

CONFIGFILE = os.path.join(CONFIGDIR, "naoki.conf")

CHROOT_PATH = "/sbin:/bin:/usr/sbin:/usr/bin"

def calc_parallelism():
	"""
		Calculate how many processes to run
		at the same time.

		We take the log10(number of processors) * factor
	"""
	num = os.sysconf("SC_NPROCESSORS_CONF")
	if num == 1:
		return 2
	else:
		return int(round(math.log10(num) * 26))

class Config(object):
	_items = {
		"toolchain" : False,
		"mandatory_packages" : [
			"core/ccache",
			"core/glibc",
		],
		"nice_level" : 0,
		"parallelism" : calc_parallelism(),
		#
		# Cleanup settings
		"cleanup_on_failure" : False,
		"cleanup_on_success" : True,
		#
		# CLI variables
		"quiet" : False,
		#
		# Distro items
		"distro_name"     : "unknown",
		"distro_sname"    : "unknown",
		"distro_epoch"    : "unknown",
		"distro_version"  : "unknown",
		"distro_slogan"   : "unknown",
		#
		# Logging
		"log_config_file" : os.path.join(CONFIGDIR, "logging.ini"),
		"log_file"        : os.path.join(LOGDIR, "naoki.log"),
	}

	def __init__(self):
		self.read([CONFIGFILE, os.path.join(BASEDIR, ".config")])

	def read(self, files):
		parser = ConfigParser.ConfigParser()
		parser.read(files)

		config = {}
		for key, val in parser.items(ConfigParser.DEFAULTSECT):
			config[key] = val

		for section in parser.sections():
			for key, val in parser.items(section):
				config["%s_%s" % (section, key)] = val

		self._items.update(config)

	def items(self):
		return self._items.items()

	def __getitem__(self, item):
		return self._items[item]

	def __setitem__(self, item, value):
		self._items[item] = value

	@property
	def environment(self):
		return {
			"HOME"           : os.environ.get("HOME", "/root"),
			"TERM"           : os.environ.get("TERM", ""),
			"PS1"            : os.environ.get("PS1", "\u:\w\$ "),
			#
			"DISTRO_NAME"    : self["distro_name"],
			"DISTRO_SNAME"   : self["distro_sname"],
			"DISTRO_EPOCH"   : self["distro_epoch"],
			"DISTRO_VERSION" : self["distro_version"],
			"DISTRO_SLOGAN"  : self["distro_slogan"],
			#
			"PARALLELISMFLAGS" : "-j%d" % self["parallelism"],
		}


class Architectures(object):
	def __init__(self, configfile):
		parser = ConfigParser.ConfigParser()
		parser.read(configfile)

		arches = {}
		for arch in parser.sections():
			arches[arch] = { "name" : arch }
			for key, val in parser.items(arch):
				arches[arch][key] = val

		self._arches = arches
		self.__current = None

	def set(self, arch):
		self.__current = arch

	@property
	def all(self):
		return self._arches

	@property
	def default(self):
		return self._arches.get("i686")

	@property
	def current(self):
		if not self.__current:
			return self.default
		return self._arches[self.__current]

	def __getitem__(self, key):
		return self._arches[key]


# Create a globally useable instance of the configuration
config = Config()

arches = Architectures(config["architecture_config"])
