#!/usr/bin/python

import os
import sys
import urlgrabber
import urlgrabber.progress

import chroot
import terminal
import util

from constants import *
from logger import getLog

def list(toolchain=False):
	pkgs = []
	for dir in os.listdir(PKGSDIR):
		if not os.path.isdir(os.path.join(PKGSDIR, dir)):
			continue

		# If we work in toolchain mode we don't return the other
		# packages and if we are not, we don't return the toolchain packages.
		if toolchain:
			if dir != "toolchain":
				continue
		else:
			if dir == "toolchain":
				continue

		for package in os.listdir(os.path.join(PKGSDIR, dir)):
			package = os.path.join(dir, package)
			pkgs.append(Package(package))

	pkgs.sort()
	return pkgs

def find(s, toolchain=False):
	if not s:
		return

	p = Package(s)
	if p in list(toolchain):
		return p

	for package in list(toolchain):
		if os.path.basename(package.name) == s:
			return package

def groups():
	return [Group(name) for name in group_names()]

def group_names():
	groups = []
	for package in list():
		group = package.group
		if not group in groups:
			groups.append(group)
	groups.sort()
	return groups

def download(file, type):
	if not file:
		return

	dirs = {
		"object" : TARBALLDIR,
		"patch"  : PATCHESDIR,
	}
	filepath = os.path.join(dirs[type], file)
	if os.path.exists(filepath):
		return

	g = urlgrabber.grabber.URLGrabber(
		user_agent = "%sSourceGrabber/%s" % (config["distro_name"], config["distro_version"],),
		progress_obj = urlgrabber.progress.TextMeter(),
		text = "Downloading %s..." % file,
	)
	gobj = g.urlopen(config["download_%s_url" % type] % { "file" : file })

	# XXX Need to check SHA1 sum here

	for dir in dirs.values():
		util.mkdir(dir)

	fobj = open(filepath, "w")
	fobj.write(gobj.read())
	fobj.close()
	gobj.close()

def depsolve(packages, recursive=False):
		deps = []
		for package in packages:
			if not package:
				continue
			if package:
				deps.append(package)

		if not recursive or not deps:
			return deps

		while True:
			length = len(deps)
			for dep in deps[:]:
				deps.extend(dep.deps)

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
			for dep in package.getAllDeps(recursive=False):
				if dep in ret[-1]:
					stage.remove(package)
					next.append(package)
					break
		
		ret[-1] = sorted(stage)
		if next:
			ret.append(sorted(next))
			continue

		break

	return ret

def depsort(packages):
	ret = [] 
	for l1 in deptree(packages):
		ret.extend(l1)
	return ret

class Package(object):
	info_str = """\
Name        : %(name)s
Version     : %(version)s
Release     : %(release)s
Group       : %(group)s

%(summary)s

Description :
%(description)s

Maintainer  : %(maintainer)s
License     : %(license)s

Built?      : %(isBuilt)s
Can build?  : %(canBuild)s

Files       :
%(objects)s

Patches     :
%(patches)s
"""

	info_wiki_str = """\
====== %(name)s ======
| **Version:**  | %(version)s  |
| **Release:**  | %(release)s  |
| **Group:**  | %(group)s  |
| **License:**  | %(license)s  |
| **Maintainer:**  | %(maintainer)s |
| **Dependencies:** | %(deps)s |
| **Build dependencies:** | %(build_deps)s |
| %(summary)s ||
| **Website:**  | %(url)s  |
"""

	def __init__(self, name):
		self._name = name

		self.config = config
		self.__fetch_data = None

	def __repr__(self):
		return "<Package %s>" % self.name

	def __cmp__(self, other):
		return cmp(self.name, other.name)

	def fetch(self, key=None):
		return self.__fetch()[key]

	def __fetch(self):
		if not self.__fetch_data:
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
			self.__fetch_data = ret

		return self.__fetch_data

	def download(self):
		for object in self.objects:
			download(object, type="object")
		for patch in self.patches:
			download(patch, type="patch")

	@property
	def fingerprint(self):
		return str(os.stat(self.filename).st_mtime)

	@property
	def filename(self):
		return os.path.join(PKGSDIR, self.name, os.path.basename(self.name)) + ".nm"

	@property
	def name(self):
		return self._name

	@property
	def version(self):
		return self.fetch("PKG_VER")

	@property
	def release(self):
		return self.fetch("PKG_REL")

	@property
	def summary(self):
		return self.fetch("PKG_SUMMARY")

	@property
	def description(self):
		return self.fetch("PKG_DESCRIPTION")

	@property
	def group(self):
		return self.fetch("PKG_GROUP")

	@property
	def packages(self):
		return self.fetch("PKG_PACKAGES")

	@property
	def package_files(self):
		return sorted(self.fetch("PKG_PACKAGES_FILES").split(" "))

	@property
	def objects(self):
		objects = []
		for object in sorted(self.fetch("PKG_OBJECTS").split(" ")):
			if not object in self.patches:
				objects.append(object)
		return objects

	@property
	def patches(self):
		return sorted(self.fetch("PKG_PATCHES").split(" "))

	@property
	def maintainer(self):
		return self.fetch("PKG_MAINTAINER")

	@property
	def deps(self):
		return self.getDeps()

	def getDeps(self, recursive=False):
		deps = []
		for package in self.fetch("PKG_DEPENDENCIES").split(" "):
			package = find(package)
			if package:
				deps.append(package)
		return depsolve(deps, recursive)

	def getAllDeps(self, recursive=True):
		if self.toolchain:
			return depsolve(self.toolchain_deps, recursive)

		return depsolve(self.deps + self.build_deps, recursive)

	@property
	def build_deps(self):
		deps = []
		for package in self.fetch("PKG_BUILD_DEPENDENCIES").split(" "):
			package = find(package)
			if package:
				deps.append(package)
		
		deps.sort()
		return deps

	@property
	def toolchain_deps(self):
		deps = []
		for package in self.fetch("PKG_TOOLCHAIN_DEPENDENCIES").split(" "):
			package = find(package, toolchain=True)
			if package:
				deps.append(package)

		deps.sort()
		return deps

	@property
	def url(self):
		return self.fetch("PKG_URL")

	@property
	def id(self):
		return "%s-%s-%s" % (self.name, self.version, self.release)

	@property
	def license(self):
		return self.fetch("PKG_LICENSE")

	@property
	def __info(self):
		return {
			"name" : self.name,
			"version" : self.version,
			"release" : self.release,
			"summary" : self.summary,
			"description" : self.description,
			"maintainer" : self.maintainer,
			"objects" : self.objects,
			"patches" : self.patches,
			"group" : self.group,
			"license" : self.license,
			"isBuilt" : self.isBuilt,
			"canBuild" : self.canBuild,
			"url" : self.url,
		}

	def info(self, long=False):
		return self.info_str % self.__info

	def info_line(self, long=False):
		if long:
			s = "%-30s | %-15s | %s" % \
				(self.name, "%s-%s" % (self.version, self.release), self.summary)

			# Cut if text gets too long
			columns = terminal.get_columns()
			if len(s) >= columns:
				s = s[:columns - 3] + "..."

			return s

		else:
			return self.name

	def info_wiki(self, long=True):
		if not long:
			return "  * [[.package:%(name)s|%(name)s]] - %(summary)s" % \
				{ "name" : self.name, "summary" : self.summary, }

		__info = self.__info
		__info.update({
			"deps" : "NOT IMPLEMENTED YET",
			"build_deps" : "NOT IMPLEMENTED YET",
		})

		return self.info_wiki_str % __info

	@property
	def isBuilt(self):
		if self.toolchain:
			return os.path.exists(self.toolchain_file)

		for item in self.package_files:
			if not os.path.exists(os.path.join(PACKAGESDIR, item)):
				return False
		return True

	@property
	def canBuild(self):
		if self.toolchain:
			for dep in self.toolchain_deps:
				if not dep.isBuilt:
					return False
			return True

		deps = self.deps + self.build_deps
		for dep in deps:
			if not dep.isBuilt:
				return False

		return True

	def extract(self, dest):
		files = [os.path.join(PACKAGESDIR, file) for file in self.package_files]
		if not files:
			return

		getLog().debug("Extracting %s..." % self.name)
		util.do("%s --root=%s %s" % (os.path.join(TOOLSDIR, "decompressor"),
			dest, " ".join(files)), shell=True)

	@property
	def toolchain(self):
		if self.name.startswith("toolchain"):
			return True
		return False

	@property
	def toolchain_file(self):
		return os.path.join(TOOLCHAINSDIR, "tools_i686", "built", self.id)


class Group(object):
	def __init__(self, name):
		self.name = name

		self.__packages = []

	def wiki_headline(self):
		return "===== %s =====" % self.name

	@property
	def packages(self):
		if not self.__packages:
			for pkg in list():
				if not pkg.group == self.name:
					continue
				self.__packages.append(pkg)

			self.__packages.sort()

		return self.__packages
