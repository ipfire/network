#!/usr/bin/python

import logging

import deps
import environ

from constants import *
from exception import *

class BuildSet(object):
	def __init__(self, package):
		self.package = package

		self.dependency_set = deps.DependencySet(self.package)

		logging.debug("Successfully created BuildSet for %s" % self.package)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.package.name)

	def _resolve(self, ignore_errors=False):
		try:
			self.dependency_set.resolve()
		except DependencyResolutionError, e:
			if ignore_errors:
				logging.warning("Ignoring dependency errors: %s" % e)
			else:
				raise

	@property
	def arch(self):
		return self.package.arch

	def print_info(self):
		logging.info("Building: %s" % self.package.id)
		logging.info("    %s" % self.package.summary)
		logging.info("")

	def build(self, ignore_dependency_errors=False):
		logging.debug("Running build process for %s" % self)
		self.print_info()

		self._resolve(ignore_errors=ignore_dependency_errors)

		env = environ.Environment(self)
		env.build()

	run = build

	def shell(self):
		logging.debug("Running shell for %s" % self)
		self.print_info()

		# Add some packages that are kind of nice in a shell
		# like an editor and less...
		for dependency in [deps.Dependency(d) for d in config["shell_packages"]]:
			logging.debug("Adding shell dependency: %s" % dependency)
			self.dependency_set.add_dependency(dependency)

		self._resolve()

		env = environ.Shell(self)
		env.shell()


class Builder(object):
	def __init__(self):
		self._items = []
		
		logging.debug("Successfully created Builder instance")

	def add(self, i):
		self._items.append(BuildSet(i))
		logging.debug("Added %s to %s" % (i, self))

	def _reorder(self):
		logging.debug("Reordering BuildSets")

	def run(self, *args, **kwargs):
		self._reorder()

		logging.info("Running build process")

		while self._items:
			i = self._items.pop(0)

			# Run the actual build
			i.run(*args, **kwargs)

