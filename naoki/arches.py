#!/usr/bin/python

from ConfigParser import ConfigParser

from constants import *

_architectures = []

def all():
	return _architectures

def get(name):
	for arch in _architectures:
		if arch.name == name:
			return arch

	raise Exception, "Architecture was not found: %s" % name

def get_default():
	for a in _architectures:
		if a.default:
			return a

	return "i686" # XXX for now

def set_default(name):
	for a in _architectures:
		if a.name == name:
			a.default = True
		else:
			a.default = False

def read(configuration_file):
	p = ConfigParser()
	p.read(configuration_file)

	for arch in p.sections():
		settings = {}
		for key, val in p.items(arch):
			settings[key] = val
		a = Architecture(arch, **settings)
		_architectures.append(a)

class Architecture(object):
	def __init__(self, name, **settings):
		self.name = name

		self.settings = {
			"default" : False,
			"package_dir" : os.path.join(PACKAGESDIR, self.name),
		}
		self.settings.update(settings)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.name)

	def __getattr__(self, key):
		try:
			return self.settings[key]
		except KeyError:
			raise ValueError

	def get_default(self):
		return self.settings["default"]

	def set_default(self, val):
		self.settings["default"]

	default = property(get_default, set_default)


read(config["architecture_config"])

if __name__ == "__main__":
	for a in _architectures:
		print a, a.settings
