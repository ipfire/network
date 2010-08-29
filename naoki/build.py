#!/usr/bin/python

import logging

import deps
import environ

from exception import *

class BuildSet(object):
	def __init__(self, package):
		self.package = package

		self.dependency_set = deps.DependencySet(self.package)

		logging.debug("Successfully created BuildSet for %s" % self.package)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.package.name)

	@property
	def arch(self):
		return self.package.arch

	def print_info(self):
		logging.info("Building: %s" % self.package.id)
		logging.info("    %s" % self.package.summary)
		logging.info("")

	def run(self, ignore_dependency_errors=False):
		logging.debug("Running build process for %s" % self)
		self.print_info()

		try:
			self.dependency_set.resolve()
		except DependencyResolutionError, e:
			if ignore_dependency_errors:
				logging.warning("Ignoring dependency errors: %s" % e)
			else:
				raise

		env = environ.Environment(self)
		env.build()


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
