#!/usr/bin/python

import logging
import uuid

import dependencies
import environ

from constants import *
from exception import *


class Build(object):
	def __init__(self, package, **kwargs):
		self.package = package

		# Generate a random, but unique id
		self.id = uuid.uuid4()

		# Create dependency set
		self.dependency_set = dependencies.DependencySet(arch=self.arch)

		# Add all mandatory packages and build dependencies
		deps = [dependencies.Dependency(p) for p in config["mandatory_packages"]]
		deps += self.package.get_dependencies("build")
		for package in deps:
			self.dependency_set.add_dependency(package)

		self.settings = {
			"ignore_dependency_errors" : False,
		}

		self.settings.update(kwargs)

	def __repr__(self):
		return "<%s %s-%s:%s>" % \
			(self.__class__.__name__, self.id, self.package.name, self.arch.name)

	@property
	def arch(self):
		return self.package.arch

	def build(self, **settings):
		self.settings.update(settings)

		logging.info("Building: %s (%s)" % (self.package.id, self.id))
		logging.info("")
		logging.info("    %s" % self.package.summary)
		logging.info("")

		# Download the source tarballs
		self.package.source_download()

		# Resolve the dependencies
		try:
			self.dependency_set.resolve()
		except DependencyResolutionError, e:
			if self.settings["ignore_dependency_errors"]:
				logging.warning("Ignoring dependency errors: %s" % e)
			else:
				raise

		e = environ.Build(self.package, build_id="%s" % self.id)

		# Extract all tools
		for package in self.dependency_set.packages:
			e.extract(package)

		# Build :D
		e.build()


class Jobs(object):
	def __init__(self):
		self.__jobs = []
		self.__error_jobs = []

		logging.debug("Initialized jobs queue")

	def __len__(self):
		return len(self.__jobs)

	def add(self, job):
		assert isinstance(job, Build)

		self.__jobs.append(job)

	@property
	def all(self):
		return self.__jobs[:]

	@property
	def has_jobs(self):
		return self.__jobs != []

	def process_next(self):
		if not self.__jobs:
			return

		job = self.__jobs[0]

		try:
			job.build()
		finally:
			self.__jobs.remove(job)


class PackageShell(Build):
	def __init__(self, *args, **kwargs):
		Build.__init__(self, *args, **kwargs)

		# Add shell packages to have a little bit more
		# comfort in here...
		for dependency in config["shell_packages"]:
			dependency = dependencies.Dependency(dependency)
			self.dependency_set.add_dependency(dependency)

	def shell(self, **settings):
		# Resolve the dependencies
		try:
			self.dependency_set.resolve()
		except DependencyResolutionError, e:
			if self.settings["ignore_dependency_errors"]:
				logging.warning("Ignoring dependency errors: %s" % e)
			else:
				raise

		e = environ.Build(self.package, build_id="%s" % self.id)

		# Extract all tools
		for package in self.dependency_set.packages:
			e.extract(package)

		# Download the source tarballs
		self.package.source_download()

		# Preparing source...
		e.make("prepare")

		# Run the shell
		e.shell()
