#!/usr/bin/python

import logging
import os
import re

import arches
import paks
import repo

from constants import *
from exception import *

DEP_INVALID, DEP_FILE, DEP_LIBRARY, DEP_PACKAGE = range(4)

class Dependency(object):
	def __init__(self, identifier, origin=None):
		self.identifier = identifier
		self.origin = origin

	def __cmp__(self, other):
		return cmp(self.identifier, other.identifier)

	def __repr__(self):
		s = "<%s %s" % (self.__class__.__name__, self.identifier)
		if self.origin:
			s += " by %s" % self.origin.name
			s += "(%s)" % os.path.basename(self.origin.filename)
		s += ">"

		return s

	@property
	def type(self):
		if self.identifier.startswith("/"):
			return DEP_FILE
		elif ".so" in self.identifier:
			return DEP_LIBRARY
		elif re.match("^[A-Za-z0-9\-\+]+$", self.identifier):
			return DEP_PACKAGE

		return DEP_INVALID

	def match(self, other):
		return self.type == other.type \
			and self.identifier == other.identifier


class Provides(Dependency):
	pass


class DependencySet(object):
	def __init__(self, package):
		self.package = package

		self.repo_bin = repo.BinaryRepository(self.arch.name)

		logging.debug("Successfully initialized %s" % self)
		self.reset()

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.package.id)

	def add_dependency(self, item):
		assert isinstance(item, Dependency)

		# If this dependency is already provided by something else
		# we skip the add
		for p in self.provides:
			if p.match(item):
				logging.debug("%s matches %s" % (p, item))
				return

		if not item in self.dependencies:
			self._dependencies.append(item)

			logging.debug("Added new dependency %s" % item)

	def add_package(self, item):
		assert isinstance(item, paks.BinaryPackage)

		if item in self._items:
			return

		for provides in item.get_provides():
			self.add_provides(provides)

		for dependency in item.get_dependencies():
			self.add_dependency(dependency)

		self._items.append(item)
		logging.debug("Added new package %s" % item)

	def add_provides(self, item):
		assert isinstance(item, Provides)

		if item in self._provides:
			return

		self._provides.append(item)
		self._provides.sort()

	def reset(self):
		self._dependencies = []
		self._items = []
		self._provides = []
		logging.debug("Reset %s" % self)

	def resolve(self):
		logging.debug("Resolving %s" % self)

		self.reset()

		# Always add the default packages
		_dependencies = [Dependency(i) for i in config["mandatory_packages"]]

		# Add build dependencies from package
		_dependencies += self.package.get_dependencies("build")
		
		for dependency in _dependencies:
			self.add_dependency(dependency)

		# Safe for endless loop
		counter = 1000

		while self.dependencies:
			counter -= 1
			if not counter:
				logging.debug("Maximum count of dependency loop was reached")
				break

			dependency = self._dependencies.pop(0)

			logging.debug("Processing dependency: %s" % dependency.identifier)

			if dependency.type == DEP_PACKAGE:
				package = self.repo_bin.find_package_by_name(dependency.identifier)
				if package:
					# Found a package and add this
					self.add_package(package)
					continue

			elif dependency.type == DEP_LIBRARY:
				for package in self.repo_bin.list():
					for provides in package.get_provides():
						if provides.match(dependency):
							self.add_package(package)
							break

			elif dependency.type == DEP_FILE:
				package = self.repo_bin.find_package_by_file(dependency.identifier)
				if package:
					self.add_package(package)
					continue

				logging.warning("Cannot find a package which provides file %s" % \
					dependency.identifier)

			elif dependency.type == DEP_INVALID:
				logging.warning("Dropping invalid dependency %s" % dependency.identifier)
				continue

			# Found not solution, push it to the end
			logging.debug("No match found: %s" % dependency)
			self.add_dependency(dependency)

		if self.dependencies:
			#logging.error("Unresolveable dependencies: %s" % self.dependencies)
			raise DependencyResolutionError, "%s" % self.dependencies

	@property
	def arch(self):
		return self.package.arch

	@property
	def dependencies(self):
		return sorted(self._dependencies)

	@property
	def items(self):
		#if not self._items:
		#	self.resolve()

		return self._items

	@property
	def packages(self):
		return sorted(self.items)

	@property
	def provides(self):
		return self._provides
