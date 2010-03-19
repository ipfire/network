#!/usr/bin/python

import os
import urlgrabber
import urllib

import chroot
import util

from constants import *

__cache = {
	"package_names" : None,
	"group_names" : None,
}

def get_package_names(toolchain=False):
	if not __cache["package_names"]:
		names = []
		for repo in get_repositories(toolchain):
			names.extend(repo.package_names)

		__cache["package_names"] = sorted(names)

	return __cache["package_names"]

def get_group_names():
	if not __cache["group_names"]:
		groups = []
		for package in get_package_names():
			package = PackageInfo(package)
			if not package.group in groups:
				groups.append(package.group)
		
		__cache["group_names"] = sorted(groups)

	return __cache["group_names"]

def find_package_name(name, toolchain=False):
	if name in get_package_names(toolchain):
		return name

	for package in get_package_names(toolchain):
		if os.path.basename(package) == name:
			return package

def depsolve(packages, recursive=False):
	deps = []
	for package in packages:
		if not package in deps:
			deps.append(package)

	if not recursive or not deps:
		return deps

	while True:
		length = len(deps)
		for dep in deps[:]:
			deps.extend(dep.dependencies)

		new_deps = []
		for dep in deps:
			if not dep in new_deps:
				new_deps.append(dep)

		deps = new_deps

		if length == len(deps):
			break

	deps.sort()
	return deps

def deptree(packages):
	ret = [packages]

	while True:
		next = []
		stage = ret[-1][:]
		for package in stage[:]:
			for dep in package.info.dependencies_all:
				if dep in ret[-1]:
					stage.remove(package)
					next.append(package)
					break
		
		ret[-1] = stage
		if next:
			ret.append(next)
			continue

		break

	return ret

def depsort(packages):
	ret = [] 
	for l1 in deptree(packages):
		ret.extend(l1)
	return ret

def download(files, logger=None):
	for file in files:
		filepath = os.path.join(TARBALLDIR, file)

		if not os.path.exists(TARBALLDIR):
			os.makedirs(TARBALLDIR)

		if os.path.exists(filepath):
			continue

		url = config["sources_download_url"] + "/" + file

		if logger:
			logger.debug("Retrieving %s" % url)

		g = urlgrabber.grabber.URLGrabber(
			user_agent = "%sSourceGrabber/%s" % (config["distro_name"], config["distro_version"],),
			progress_obj = urlgrabber.progress.TextMeter(),
			quote=0,
		)

		try:
			gobj = g.urlopen(url)
		except urlgrabber.grabber.URLGrabError, e:
			logger.error("Could not retrieve %s - %s" % (url, e))
			raise

		# XXX Need to check SHA1 sum here

		fobj = open(filepath, "w")
		fobj.write(gobj.read())
		fobj.close()
		gobj.close()

class PackageInfo(object):
	__data = {}

	def __init__(self, name):
		self._name = name

	def __repr__(self):
		return "<PackageInfo %s>" % self.name

	def get_data(self):
		if not self.__data.has_key(self.name):
			self.__data[self.name] = self.fetch()

		return self.__data[self.name]

	def set_data(self, data):
		self.__data[self.name] = data

	_data = property(get_data, set_data)
	
	def fetch(self):
		env = os.environ.copy()
		env.update(config.environment)
		env["PKGROOT"] = PKGSDIR
		output = util.do("make -f %s" % self.filename, shell=True,
			cwd=os.path.join(PKGSDIR, self.name), returnOutput=1, env=env)

		ret = {}
		for line in output.splitlines():
			a = line.split("=", 1)
			if not len(a) == 2: continue
			key, val = a
			ret[key] = val.strip("\"")

		ret["FINGERPRINT"] = self.fingerprint

		return ret

	def fmtstr(self, s):
		return s % self.all

	def getPackage(self, naoki):
		return Package(self.name, naoki)

	@property
	def all(self):
		return {
			"description" : self.description,
			"filename"    : self.filename,
			"fingerprint" : self.fingerprint,
			"group"       : self.group,
			"license"     : self.license,
			"maintainer"  : self.maintainer,
			"name"        : self.name,
			"objects"     : self.objects,
			"patches"     : self.patches,
			"release"     : self.release,
			"summary"     : self.summary,
			"version"     : self.version,
		}

	def _dependencies(self, s, recursive=False):
		c = s + "_CACHE"
		if not self._data.has_key(c):
			deps = []
			for name in self._data.get(s).split(" "):
				name = find_package_name(name)
				if name:
					deps.append(Dependency(name))

			self._data.update({c : depsolve(deps, recursive)})

		return self._data.get(c)

	@property
	def dependencies(self):
		return self._dependencies("PKG_DEPENDENCIES")

	@property
	def dependencies_build(self):
		return self._dependencies("PKG_BUILD_DEPENDENCIES")

	@property
	def dependencies_all(self):
		return depsolve(self.dependencies + self.dependencies_build, recursive=True)

	@property
	def description(self):
		return self._data.get("PKG_DESCRIPTION")

	@property
	def filename(self):
		return os.path.join(PKGSDIR, self.name, os.path.basename(self.name)) + ".nm"

	@property
	def fingerprint(self):
		return "%d" % os.stat(self.filename).st_mtime

	@property
	def group(self):
		return self._data.get("PKG_GROUP")

	@property
	def id(self):
		return "%s-%s-%s" % (self.name, self.version, self.release)

	@property
	def license(self):
		return self._data.get("PKG_LICENSE")

	@property
	def maintainer(self):
		return self._data.get("PKG_MAINTAINER")

	@property
	def name(self):
		return self._name

	@property
	def objects(self):
		return self._data.get("PKG_OBJECTS").split(" ")

	@property
	def package_files(self):
		return self._data.get("PKG_PACKAGES_FILES").split(" ")

	@property
	def patches(self):
		return self._data.get("PKG_PATCHES").split(" ")

	@property
	def release(self):
		return self._data.get("PKG_REL")

	@property
	def summary(self):
		return self._data.get("PKG_SUMMARY")

	@property
	def version(self):
		return self._data.get("PKG_VER")


class Dependency(PackageInfo):
	def __repr__(self):
		return "<Dependency %s>" % self.name


class Package(object):
	def __init__(self, name, naoki):
		self.info = PackageInfo(name)
		self.naoki = naoki

		#self.log.debug("Initialized package object %s" % name)

	def build(self):
		environment = chroot.Environment(self)
		environment.build()

	def download(self):
		download(self.info.objects, logger=self.log)

	def extract(self, dest):
		files = [os.path.join(PACKAGESDIR, file) for file in self.info.package_files]
		if not files:
			return

		self.log.debug("Extracting %s..." % files)
		util.do("%s --root=%s %s" % (os.path.join(TOOLSDIR, "decompressor"),
			dest, " ".join(files)), shell=True)

	@property
	def log(self):
		return self.naoki.logging.getBuildLogger(self.info.id)


def get_repositories(toolchain=False):
	if toolchain:
		return Repository("toolchain")

	repos = []
	for repo in os.listdir(PKGSDIR):
		if os.path.isdir(os.path.join(PKGSDIR, repo)):
			repos.append(repo)

	repos.remove("toolchain")

	return [Repository(repo) for repo in repos]

class Repository(object):
	def __init__(self, name):
		self.name = name

	def __repr__(self):
		return "<Repository %s>" % self.name

	@property
	def packages(self):
		packages = []
		for package in os.listdir(self.path):
			package = PackageInfo(os.path.join(self.name, package))
			packages.append(package)

		return packages

	@property
	def package_names(self):
		return [package.name for package in self.packages]

	@property
	def path(self):
		return os.path.join(PKGSDIR, self.name)

if __name__ == "__main__":
	pi = PackageInfo("core/grub")

	print pi.dependencies
