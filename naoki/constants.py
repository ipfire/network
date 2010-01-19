#!/usr/bin/python

import ConfigParser
import os

BASEDIR = os.getcwd()

BUILDDIR = os.path.join(BASEDIR, "build")
CACHEDIR = os.path.join(BASEDIR, "cache")
CONFIGDIR = os.path.join(BASEDIR, "config")
LOGDIR = os.path.join(BASEDIR, "logs")
PKGSDIR = os.path.join(BASEDIR, "pkgs")
PACKAGESDIR = os.path.join(BUILDDIR, "packages")
TOOLCHAINSDIR = os.path.join(BUILDDIR, "toolchains")
TOOLSDIR = os.path.join(BASEDIR, "tools")

TARBALLDIR = os.path.join(CACHEDIR, "tarballs")
PATCHESDIR = os.path.join(CACHEDIR, "patches")

CONFIGFILE = os.path.join(CONFIGDIR, "naoki.conf")

class Config(object):
	_items = {
		"toolchain" : False,
		"mandatory_packages" : [
			"core/bash",
			"core/gcc",
			"core/glibc",
			"core/make",
		],
		#
		# Cleanup settings
		"cleanup_after_fail" : True,
		#
		# Distro items
		"distro_name"     : "unknown",
		"distro_sname"    : "unknown",
		"distro_epoch"    : "unknown",
		"distro_version"  : "unknown",
		"distro_slogan"   : "unknown",
		#
		# Downloads
		"download_object_url" : "http://source.ipfire.org/source-3.x/%(file)s",
		"download_patch_url"  : "http://source.ipfire.org/source-3.x/%(file)s",
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
			"TERM"           : os.environ["TERM"],
			"PS1"            : os.environ.get("PS1", "\u:\w\$ "),
			#
			"DISTRO_NAME"    : self["distro_name"],
			"DISTRO_SNAME"   : self["distro_sname"],
			"DISTRO_EPOCH"   : self["distro_epoch"],
			"DISTRO_VERSION" : self["distro_version"],
			"DISTRO_SLOGAN"  : self["distro_slogan"],
		}

# Create a globally useable instance of the configuration
config = Config()
