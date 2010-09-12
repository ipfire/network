#!/usr/bin/python

import logging
import os
import re

import architectures
import dependencies
import environ
import io
import util

from constants import *

class Package(object):
	def __repr__(self):
		return "<%s %s:%s>" % \
			(self.__class__.__name__, self.name, self.arch.name)

	#@property
	#def arch(self):
	#	raise NotImplementedError

	@property
	def name(self):
		return self._info["PKG_NAME"]

	@property
	def id(self):
		return "%s-%s-%s.%s" % \
			(self.name, self.version, self.release, self.arch.name)

	@property
	def release(self):
		return int(self._info["PKG_REL"])

	@property
	def version(self):
		return self._info["PKG_VER"]


class SourcePackage(Package):
	def __init__(self, filename, repo, arch):
		self.arch = arch
		self.filename = filename
		self.repository = repo

		self.init()

		logging.debug("Successfully initialized %s" % self)

	def init(self):
		self._info = {}

		env = environ.set({
			"PKG_ARCH" : self.arch.name,
			"PKGROOT" : PKGSDIR,
		})

		output = util.do("make -f %s" % os.path.basename(self.filename),
			shell=True,
			cwd=os.path.dirname(self.filename),
			returnOutput=1,
			env=env)

		for line in output.splitlines():
			if not line:
				continue

			m = re.match(r"^(\w+)=(.*)$", line)
			if m is None:
				continue

			key, val = m.groups()
			self._info[key] = val.strip("\"")

	# XXX should return a dependencyset
	def get_dependencies(self, type=""):
		type2var = {
			"" : "PKG_DEPENDENCIES",
			"build" : "PKG_BUILD_DEPENDENCIES",
		}

		type = type2var[type]

		return [dependencies.Dependency(d, origin=self) for d in self._info[type].split()]

	@property
	def source_dir(self):
		return self._info.get("SOURCE_DIR", "")

	@property
	def summary(self):
		return self._info["PKG_SUMMARY"]

	@property
	def binary_files(self):
		return self._info.get("PKG_PACKAGES_FILES").split()

	@property
	def is_built(self):
		for file in self.binary_files:
			file = os.path.join(PACKAGESDIR, self.arch.name, file)
			if not os.path.exists(file):
				return False

		return True


class BinaryPackage(Package):
	def __init__(self, filename):
		self.filename = filename

		self.init()
		logging.debug("Successfully initialized %s" % self)

	def __repr__(self):
		return "<%s %s-%s-%s>" % \
			(self.__class__.__name__, self.name, self.version, self.release)

	def __cmp__(self, other):
		return cmp(self.id, other.id)

	def _readfile(self, name):
		f = io.CpioArchive(self.filename)

		# If file is not available, return None
		ret = None
		if name in [e.name for e in f.entries]:
			ret = f.get(name).read()

		f.close()
		return ret

	def init(self):
		self._info = {}
		self._filelist = []

		info = self._readfile("info")

		for line in info.splitlines():
			if not line:
				continue

			m = re.match(r"^(\w+)=(.*)$", line)
			if m is None:
				continue

			key, val = m.groups()
			self._info[key] = val.strip("\"")

	def extract(self, path):
		logging.debug("Extracting %s to %s" % (self, path))

		cmd = os.path.join(TOOLSDIR, "decompressor")
		cmd += " --root=%s %s" % (path, self.filename)

		util.do(cmd, shell=True, logger=logging.getLogger())

	@property
	def arch(self):
		arches = architectures.Architectures()

		arch = self._info.get("PKG_ARCH", None)
		if arch:
			arch = arches.get(arch)
		else:
			arch = arches.get_default()

		return arch

	@property
	def name(self):
		return self._info["PKG_NAME"]

	def get_dependencies(self):
		objects = self._info.get("PKG_DEPS", "").split()

		# Compatibility to older package format
		objects += self._info.get("PKG_REQUIRES", "").split()

		return [dependencies.Dependency(o, origin=self) for o in objects]

	def get_provides(self):
		return [dependencies.Provides(p, origin=self) \
			for p in self._info.get("PKG_PROVIDES", "").split()]

	@property
	def filelist(self):
		if not self._filelist:

			filelist = self._readfile("filelist")
			if not filelist:
				return []

			for file in filelist.splitlines():
				if not file or not file.startswith("/"):
					continue

				self._filelist.append(file)

		return self._filelist
