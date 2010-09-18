#!/usr/bin/python

import logging
import operator
import os

import architectures
import packages

from constants import *
from decorators import *

class Repository(object):
	def __init__(self, arch):
		assert isinstance(arch, architectures.Architecture)
		self.arch = arch

		logging.debug("Successfully initialized %s" % self)

	def __repr__(self):
		return "<%s %s>" % (self.__class__.__name__, self.path)

	@property
	def path(self):
		raise NotImplementedError


class BinaryRepository(Repository):
	_cache = {}

	@property
	def path(self):
		return os.path.join(PACKAGESDIR, self.arch.name)

	def find_package_by_name(self, name):
		pkgs = self.find_packages_by_name(name)

		if pkgs:
			return pkgs[0]

	def find_packages_by_name(self, name):
		pkgs = []

		for package in self.all:
			if package.name == name:
				pkgs.append(package)

		return sorted(pkgs, reverse=True)

	@property
	def all(self):
		if not self._cache.has_key(self.arch.name):
			l = []

			for package in os.listdir(self.path):
				# Construct filename
				package = os.path.join(self.path, package)
	
				# Create package instance
				package = packages.BinaryPackage(package)
	
				# Append package to list
				l.append(package)

			self._cache[self.arch.name] = l

		return self._cache[self.arch.name]

	def find_package_by_file(self, filename):
		pkgs = self.find_packages_by_file(filename)

		if pkgs:
			return pkgs[0]

	def find_packages_by_file(self, filename):
		pkgs = []

		for package in self.all:
			if filename in package.filelist:
				pkgs.append(package)

		return sorted(pkgs, reverse=True)

	def find_package_by_provides(self, provides):
		pkgs = self.find_packages_by_provides(provides)

		if pkgs:
			return pkgs[0]

	def find_packages_by_provides(self, provides):
		pkgs = []

		for package in self.all:
			if provides in package.get_provides():
				pkgs.append(package)

		return sorted(pkgs, reverse=True)


class SourceRepository(Repository):
	def __init__(self, name, arch):
		self.name = name

		Repository.__init__(self, arch)

	def __iter__(self):
		pkgs = [os.path.join(self.path, p, p + ".nm") for p in self.packages]

		args = {
			"arch" : self.arch,
			"repo" : self,
		}

		return PackageIterator(pkgs, packages.SourcePackage, args)

	def find_package_by_name(self, name, fast=False):
		if fast:
			filename = os.path.join(self.path, name, name + ".nm")
			if os.path.exists(filename):
				return packages.SourcePackage(filename, repo=self, arch=self.arch)

		else:
			for package in self:
				if package.name == name:
					return package

	@property
	def path(self):
		return os.path.join(PKGSDIR, self.name)

	@property
	def packages(self):
		return sorted(os.listdir(self.path))

	@property
	def completely_built(self):
		for p in self:
			if not p.is_built:
				return False

		return True


class PackageIterator(object):
	def __init__(self, paks, package_cls=None, cls_args={}):
		self.packages = paks
		self.package_cls = package_cls
		self.package_cls_args = cls_args

		self.__i = 0

	def __iter__(self):
		return self

	def next(self):
		if self.__i >= len(self.packages):
			raise StopIteration

		pkgs = self.packages[self.__i]
		self.__i += 1

		if self.package_cls:
			package = self.package_cls(pkgs, **self.package_cls_args)

		return package


class SourceRepositories(object):
	def __init__(self, arch):
		assert isinstance(arch, architectures.Architecture)
		self.arch = arch

		self._repositories = []

		self.find_all()

	def find_all(self):
		for repo in sorted(os.listdir(PKGSDIR)):
			# Skip all non-directories
			if not os.path.isdir(os.path.join(PKGSDIR, repo)):
				continue

			logging.debug("Found source repository: %s" % repo)

			repo = SourceRepository(repo, self.arch)
			self._repositories.append(repo)

	@property
	def all(self):
		return self._repositories[:]

	def find_package_by_name(self, name):
		for fast in (True, False):
			for repo in self._repositories:
				package = repo.find_package_by_name(name, fast=fast)
				if package:
					return package

	@property
	def packages(self):
		#pkgs = []
		#for repository in self._repositories:
		#	pkgs += [p for p in repository]
		#
		#return pkgs

		for repository in self._repositories:
			for p in repository:
				yield p


if __name__ == "__main__":
	arches = architectures.Architectures()
	
	r = SourceRepositories(arches.get("i686"))

	for repo in r.all:
		print "%s" % repo.name

		#for pack in repo:
		#	print "  %s" % pack.name

	#for package in ("gcc", "screen", "iptables", "system-release", "glibc", "nonexistant"):
	#	print "Searching for %s" % package,
	#	print r.find_package_by_name(package)

	b = BinaryRepository(arches.get("i686"))

	print b.find_packages_by_name("aiccu")
	print b.find_package_by_name("aiccu")
