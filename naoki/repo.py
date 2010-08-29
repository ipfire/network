#!/usr/bin/python

# XXX make better version comparison

import logging
import os
import re

import arches
import paks

from constants import *

def find_source_repos():
	# XXX detection for all repositories missing
	return [SourceRepository("core", arches.get_default()),]

def find_source_package(name):
	for r in find_source_repos():
		p = r.get_package(name)
		if p:
			return p

class Repository(object):
	def __init__(self, arch):
		self.arch = arches.get(arch)

		logging.debug("Successfully initialized %s" % self)


class SourceRepository(Repository):
	_cache = {}

	def __init__(self, name, arch):
		self.name = name

		Repository.__init__(self, arch)

	@property
	def path(self):
		return os.path.join(PKGSDIR, self.name)

	def list(self):
		if not self._cache.has_key(self.arch.name):
			l = []
	
			for package in os.listdir(self.path):
				filename = os.path.join(self.path, package, package + ".nm")
				if not os.path.exists(filename):
					continue
	
				package = paks.SourcePackage(package, repo=self, arch=self.arch.name)
				
				l.append(package)

			self._cache[self.arch.name] = l

		return self._cache[self.arch.name]

	def get_package(self, name):
		for package in self.list():
			if package.name == name:
				return package

		return None


class BinaryRepository(Repository):
	_cache = {}

	@property
	def path(self):
		return os.path.join(PACKAGESDIR, self.arch.name)

	def list(self):
		if not self._cache.has_key(self.arch.name):
			l = []
	
			for package in os.listdir(self.path):
				# Construct filename
				package = os.path.join(self.path, package)
	
				# Create package instance
				package = paks.BinaryPackage(package)
	
				# Append package to list
				l.append(package)
	
			self._cache[self.arch.name] = l

		return self._cache[self.arch.name]

	def get_packages(self, name):
		l = []

		# Check every package if name is equal
		for package in self.list():
			if package.name == name:
				l.append(package)

		return l

	def get_latest_package(self, name):
		# XXX to be done
		l = self.get_packages(name)
		if not len(l):
			return

		return l[-1]

	def find_package_by_name(self, name, all=False):
		if all:
			return self.get_packages(name)

		return self.get_latest_package(name)

	def find_package_by_file(self, file):
		for package in self.list():
			if file in package.filelist:
				return package
		# XXX first match is not always the best result 







