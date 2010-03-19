#!/usr/bin/python

import ConfigParser
import os.path
import sys
import time

import backend
import logger
import terminal
import util

from constants import *

class Naoki(object):
	def __init__(self):
		# First, setup the logging
		self.logging = logger.Logging(self)

		# Second, parse the command line options
		self.cli = terminal.Commandline(self)

		self.log.debug("Successfully initialized naoki instance")
		for k, v in config.items():
			self.log.debug("    %s: %s" % (k, v))

	def run(self):
		args = self.cli.args

		# If there is no action provided, exit
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"build" : self.call_build,
			"toolchain" : self.call_toolchain,
			"package" : self.call_package,
			"source" : self.call_source,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"build" : self.call_toolchain_build,
			"download" : self.call_toolchain_download,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain_build(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.build()

	def call_toolchain_download(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.download()

	def call_build(self, args):
		force = True

		if args.packages == ["all"]:
			force = False
			package_names = backend.get_package_names()
		else:
			package_names = args.packages

		packages = []
		for package in package_names:
			package = backend.Package(package, naoki=self)
			packages.append(package)

		if len(packages) >= 2:
			packages_sorted = backend.depsort(packages)
			if packages_sorted == packages:
				self.log.warn("Packages were resorted for build: %s" % packages_sorted)
			packages = packages_sorted
		
		for package in packages:
			environ = chroot.Environment(package)
			
			if not environ.toolchain.exists:
				self.log.error("You need to build or download a toolchain first.")
				continue

			environ.build()

	def call_package(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"info" : self.call_package_info,
			"list" : self.call_package_list,
			"tree" : self.call_package_tree,
			"groups" : self.call_package_groups,
		}

		return actionmap[args.action.name](args.action)

	def call_package_info(self, args):
		packages = args.packages or backend.get_package_names()

		for package in packages:
			package = backend.PackageInfo(package)
			if args.long:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(name)s
Version       : %(version)s
Release       : %(release)s

  %(summary)s

%(description)s

Maintainer    : %(maintainer)s
License       : %(license)s

Files         : %(objects)s
Patches       : %(patches)s
--------------------------------------------------------------------------------\
""")
			else:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(name)s
Version       : %(version)s
Release       : %(release)s

  %(summary)s

--------------------------------------------------------------------------------\
""")

	def call_package_list(self, args):
		for package in self.package_names:
			package = backend.PackageInfo(package)
			if args.long:
				print package.fmtstr("%(name)-32s | %(version)-15s | %(summary)s")
			else:
				print package.fmtstr("%(name)s")

	def call_package_tree(self, args):
		print "TBD"

	def call_package_groups(self, args):
		groups = backend.get_group_names()
		if args.wiki:
			print "====== All available groups of packages ======"
			for group in groups:
				print "===== %s =====" % group
				for package in backend.get_package_names():
					package = backend.PackageInfo(package)
					if not package.group == group:
						continue

					print package.fmtstr("  * [[.package:%(name)s|%(name)s]] - %(summary)s")

		else:
			print "\n".join(groups)

	def call_source(self, args):
		if not args.has_key("action"):
			self.cli.help()
			sys.exit(1)

		actionmap = {
			"download" : self.call_source_download,
			"upload" : self.call_source_upload,
		}

		return actionmap[args.action.name](args.action)

	def call_source_download(self, args):
		packages = args.packages or backend.get_package_names()

		for package in packages:
			package = backend.Package(package, naoki=self)
			package.download()

	def call_source_upload(self, args):
		pass # TODO

	def _build(self, packages, force=False):
		requeue = []
		packages = package.depsort(packages)
		while packages:
			# Get first package that is to be done
			build = chroot.Environment(packages.pop(0))
			
			if not build.toolchain.exists:
				self.log.error("You need to build or download a toolchain first.")
				return
			
			if build.package.isBuilt:
				if not force:
					self.log.info("Skipping already built package %s..." % build.package.name)
					continue
				self.log.warn("Package is already built. Will overwrite.")
			
			if not build.package.canBuild:
				self.log.warn("Cannot build package %s." % build.package.name)
				if not self.packages:
					self.log.error("Blah")
					return
				self.log.warn("Requeueing. %s" % build.package.name)
				self.packages.append(build.package)
				continue

			self.log.info("Building %s..." % build.package.name)
			build.build()

	@property
	def package_names(self):
		return backend.get_package_names()
