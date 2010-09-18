#!/usr/bin/python

from ConfigParser import ConfigParser, DEFAULTSECT
import math
import os
import socket

BASEDIR = os.getcwd()

BUILDDIR = os.path.join(BASEDIR, "build")
CACHEDIR = os.path.join(BASEDIR, "cache")
CCACHEDIR = os.path.join(BASEDIR, "ccache")
CONFIGDIR = os.path.join(BASEDIR, "config")
DOCDIR = os.path.join(BASEDIR, "doc")
GENDIR = os.path.join(BUILDDIR, "generators")
IMAGESDIR = os.path.join(BUILDDIR, "images")
LOGDIR = os.path.join(BASEDIR, "logs")
PKGSDIR = os.path.join(BASEDIR, "pkgs")
PACKAGESDIR = os.path.join(BUILDDIR, "packages")
REPOSDIR = os.path.join(BUILDDIR, "repositories")
TOOLSDIR = os.path.join(BASEDIR, "tools")

ARCHES_DEFAULT = os.path.join(CONFIGDIR, "architectures.conf")

CONFIGFILE = os.path.join(CONFIGDIR, "naoki.conf")

CHROOT_PATH = "/sbin:/bin:/usr/sbin:/usr/bin"

LOCK_BATCH = os.path.join(BUILDDIR, ".batch")

LOG_MARKER = "### LOG MARKER ###"

DEP_INVALID, DEP_FILE, DEP_LIBRARY, DEP_PACKAGE = range(4)

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
			"bash",
			"bzip2",
			"ccache",
			"coreutils",
			"cpio",
			"diffutils",
			"file",
			"findutils",
			"gawk",
			"grep",
			"gzip",
			"make",
			"patch",
			"sed",
			"tar",
			"which",
			"xz",
		],
		"shell_packages" : [
			"/bin/bash",
			"less",
			"vim",
		],
		"nice_level" : 0,
		"parallelism" : calc_parallelism(),
		#
		# Cleanup settings
		"cleanup_on_failure" : False,
		"cleanup_on_success" : True,
		#
		# CLI variables
		"debug" : False,
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
		#
		# Reporting
		"error_report_recipient" : None,
		"error_report_sender" : "buildsystem@%s" % socket.gethostname(),
		"error_report_subject" : "[NAOKI] %(id)s got a build failure",
		#
		# SMTP
		"smtp_server" : None,
		"smtp_user" : None,
		"smtp_password" : None,
	}

	def __init__(self):
		self.read([CONFIGFILE, os.path.join(BASEDIR, ".config")])

	def read(self, files):
		parser = ConfigParser()
		parser.read(files)

		config = {}
		for key, val in parser.items(DEFAULTSECT):
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

	def __getattr__(self, *args):
		return self.__getitem__(*args)

	def __setattr__(self, *args):
		return self.__setitem__(*args)

	@property
	def environment(self):
		ret = {
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

		if self["debug"]:
			ret["NAOKI_DEBUG"] = "1"

		return ret


# Create a globally useable instance of the configuration
config = Config()

