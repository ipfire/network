#!/usr/bin/python

import logging
import os.path

from ConfigParser import ConfigParser, DEFAULTSECT

from constants import *
from decorators import *

class Architecture(object):
	def __init__(self, name, **settings):

		self._settings = {
			"default" : False,
			"name" : name,
		}
		self._settings.update(settings)

		logging.debug("Set up new architecture: %s" % self._settings)

	def __repr__(self):
		s = "<%s %s" % (self.__class__.__name__, self._settings["name"])
		if self.default:
			s += " (default)"
		s += ">"
		return s

	@property
	def buildable(self):
		""" Check if this architecture is buildable on the local host"""

		return True # TODO

	def get_default(self):
		return self._settings["default"]

	def set_default(self, value):
		self._settings["default"] = value

	default = property(get_default, set_default)

	def __getattr__(self, attr):
		try:
			return self._settings[attr]
		except KeyError:
			raise AttributeError, attr


@singleton
class Architectures(object):
	def __init__(self):
		self._architectures = []

		# Try to read the default architectures
		self.read(ARCHES_DEFAULT)

	def read(self, filename):
		logging.debug("Reading architectures from %s" % filename)

		if not os.path.exists(filename):
			return

		p = ConfigParser()
		p.read(filename)

		default = {}

		for arch in p.sections():
			if arch == "default":
				default = p.items(arch)
				continue
			
			settings = {}
			for key, val in p.items(arch):
				settings[key] = val

			a = Architecture(arch, **settings)
			self.add_architecture(a)

		for key, val in default:
			if key == "default":
				self.default = val

	def add_architecture(self, arch):
		assert isinstance(arch, Architecture)

		self._architectures.append(arch)

	def get_default(self):
		for a in self._architectures:
			if a.default:
				return a

		raise Exception, "Cannot find default architecture"

	def set_default(self, arch):
		if arch is None:
			return

		if not arch in [a.name for a in self.all]:
			raise Exception, "Cannot set default architecture: Unknown architecture %s" % arch

		logging.debug("Setting default architecture: %s" % arch)

		for a in self._architectures:
			if a.name == arch:
				a.default = True
			else:
				a.default = False

	default = property(get_default, set_default)

	def get(self, name):
		for arch in self._architectures:
			if arch.name == name:
				return arch

		raise Exception, "Could not find arch: %s" % name

	@property
	def all(self):
		return self._architectures[:]


if __name__ == "__main__":
	arches = Architectures()

	for arch in arches.all:
		print "Name: %s" % arch.name
		for key, val in arch._settings.items():
			print "	%-20s : %s" % (key, val)

	print arches.get("i686")
	print arches.default

