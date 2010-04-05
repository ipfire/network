#!/usr/bin/python

import ConfigParser
import os.path
import sys
import time

import backend
import chroot
import logger
import terminal
import util

from constants import *

class Naoki(object):
	def __init__(self):
		# First, setup the logging
		self.logging = logger.Logging(self)
		self.log = self.logging.log

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
			return 1

		actionmap = {
			"build" : self.call_build,
			"toolchain" : self.call_toolchain,
			"package" : self.call_package,
			"source" : self.call_source,
			"shell" : self.call_shell,
			"repository" : self.call_repository,
			"generate" : self.call_generate,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain(self, args):
		if not args.has_key("action"):
			self.cli.help()
			return 1

		actionmap = {
			"build" : self.call_toolchain_build,
			"download" : self.call_toolchain_download,
			"tree" : self.call_toolchain_tree,
		}

		return actionmap[args.action.name](args.action)

	def call_toolchain_build(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.build(naoki=self)

	def call_toolchain_download(self, args):
		toolchain = chroot.Toolchain(arches.current["name"])

		return toolchain.download()

	def call_toolchain_tree(self, args):
		print backend.deptree(backend.parse_package(backend.get_package_names(toolchain=True), toolchain=True, naoki=self))

	def call_build(self, args):
		force = True

		if args.packages == ["all"]:
			force = False
			package_names = backend.get_package_names()
		else:
			package_names = args.packages

		packages = []
		for package in backend.parse_package(package_names, naoki=self):
			if not force and package.built:
				self.log.warn("Skipping %s which was already built" % package.name)
				continue

			if not args.onlydeps:
				packages.append(package)

			if args.withdeps or args.onlydeps:
				deps = []
				for dep in package.dependencies_all:
					if not dep.built:
						deps.append(dep.name)

				packages.extend(backend.parse_package(deps, naoki=self))

		if len(packages) >= 2:
			packages_sorted = backend.depsort(packages)
			if packages_sorted != packages:
				self.log.warn("Packages were resorted for build: %s" % packages_sorted)
				packages = packages_sorted

		for i in range(0, len(packages)):
			package = packages[i]
			if not package.buildable:
				for dep in package.dependencies_unbuilt:
					if not dep in packages[:i]:
						self.log.error("%s is currently not buildable" % package.name)
						self.log.error("  The package requires these packages to be built first: %s" \
							% [dep.name for dep in package.dependencies_unbuilt])
						return

		self.log.info("Going on to build %d packages in order: %s" \
			% (len(packages), [package.name for package in packages]))

		for package in packages:
			environ = package.getEnvironment()

			if not environ.toolchain.exists:
				self.log.error("You need to build or download a toolchain first.")
				continue

			if args.shell:
				environ.init(clean=False)
				return environ.shell([])

			environ.init()

			environ.build()

	def call_package(self, args):
		if not args.has_key("action"):
			self.cli.help()
			return 1

		actionmap = {
			"info" : self.call_package_info,
			"list" : self.call_package_list,
			"tree" : self.call_package_tree,
			"groups" : self.call_package_groups,
		}

		return actionmap[args.action.name](args.action)

	def call_package_info(self, args):
		for package in backend.parse_package_info(args.packages):
			if args.wiki:
				print package.fmtstr("""\
====== %(name)s ======
| **Version:**  | %(version)s  |
| **Release:**  | %(release)s  |
| **Group:**  | %(group)s  |
| **License:**  | %(license)s  |
| **Maintainer:**  | %(maintainer)s |
| **Dependencies:** | %(deps)s |
| **Build dependencies:** | %(build_deps)s |
| %(summary)s ||
| %(description)s ||
| **Website:**  | %(url)s  |
""")
				continue

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

Files         : %(files)s
Objects       : %(objects)s
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
		for package in backend.parse_package_info(backend.get_package_names()):
			# Skip unbuilt packages if we want built packages
			if args.built and not package.built:
				continue

			# Skip built packages if we want unbuilt only
			if args.unbuilt and package.built:
				continue

			if args.long:
				print package.fmtstr("%(name)-32s | %(version)-15s | %(summary)s")
			else:
				print package.name

	def call_package_tree(self, args):
		print backend.deptree(backend.parse_package(backend.get_package_names(), naoki=self))

	def call_package_groups(self, args):
		groups = backend.get_group_names()
		if args.wiki:
			print "====== All available groups of packages ======"
			for group in groups:
				print "===== %s =====" % group
				for package in backend.parse_package_info(backend.get_package_names()):
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
			"clean" : self.call_source_clean,
		}

		return actionmap[args.action.name](args.action)

	def call_source_download(self, args):
		for package in backend.parse_package(args.packages or \
				backend.get_package_names(), naoki=self):
			package.download()

	def call_source_upload(self, args):
		pass # TODO

	def call_source_clean(self, args):
		self.log.info("Remove all unused files")
		files = os.listdir(TARBALLDIR)
		for package in backend.parse_package_info(backend.get_package_names()):
			for object in package.objects:
				if object in files:
					files.remove(object)

		for file in sorted(files):
			self.log.info("Removing %s..." % file)
			os.remove(os.path.join(TARBALLDIR, file))

	def call_shell(self, args):
		environ = chroot.ShellEnvironment(naoki=self)

		actionmap = {
			"clean" : self.call_shell_clean,
			"extract" : self.call_shell_extract,
			"enter" : self.call_shell_enter,
		}

		if args.action.name in ("enter", "execute"):
			environ.init(clean=False)

		return actionmap[args.action.name](environ, args.action)

	def call_shell_clean(self, environ, args):
		return environ.clean()

	def call_shell_extract(self, environ, args):
		if args.packages == ["all"]:
			args.packages = backend.get_package_names()

		packages = backend.parse_package(args.packages, naoki=self)
		for package in backend.depsolve(packages, recursive=True):
			package.getPackage(self).extract(environ.chrootPath())

	def call_shell_enter(self, environ, args):
		return environ.shell()

	def call_repository(self, args):
		actionmap = {
			"clean" : self.call_repository_clean,
			"build" : self.call_repository_build,
		}

		return actionmap[args.action.name](args.action)

	def call_repository_clean(self, repo, args):
		if args.names == ["all"]:
			args.names = [r.name for r in backend.get_repositories()]

		for name in args.names:
			repo = backend.BinaryRepository(name, naoki=self)
			repo.clean()

	def call_repository_build(self, args):
		if args.names == ["all"]:
			args.names = [r.name for r in backend.get_repositories()]

		for name in args.names:
			repo = backend.BinaryRepository(name, naoki=self)
			repo.build()

	def call_generate(self, args):
		if not args.type in ("iso",):
			return

		gen = chroot.Generator(self, arches.current, args.type)
		return gen.run()
