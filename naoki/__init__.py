#!/usr/bin/python

import ConfigParser
import fcntl
import os.path
import random
import sys
import time

import backend
import build
import chroot
import environ
import logger
import repo
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

		if config["nice_level"]:
			os.nice(int(config["nice_level"]))

		actionmap = {
			"build" : self.call_build,
			"package" : self.call_package,
			"source" : self.call_source,
			"shell" : self.call_shell,
			"repository" : self.call_repository,
			"generate" : self.call_generate,
			"batch" : self.call_batch,
		}

		return actionmap[args.action.name](args.action)

	def call_build(self, args):
		builder = build.Builder()

		if args.all:
			raise Exception, "XXX to be implemented"
		else:
			for name in args.packages:
				p = repo.find_source_package(name)
				if not p:
					raise Exception, "Could not find package: %s" % name

				builder.add(p)

		return builder.run(ignore_dependency_errors=args.ignore_dependency_errors)

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
		p = repo.find_source_package(args.package)
		if not p:
			raise Exception, "Could not find package: %s" % args.package

		build_set = build.BuildSet(p)

		return build_set.shell()

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

	def call_batch(self, args):
                try:
                        self._lock = open(LOCK_BATCH, "a+")
                except IOError, e:
                        return 0

                try:
                        fcntl.lockf(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except IOError, e:
                        print >>sys.stderr, "Batch operations are locked by another process"
			return 0

		actionmap = {
			"cron" : self.call_batch_cron,
		}

		return actionmap[args.action.name](args.action)

	def call_batch_cron(self, args):
		packages = []
		packages_may = []
		for package in backend.parse_package_info(backend.get_package_names()):
			if not package.built and package.buildable:
				packages.append(package)
				continue

			# If package was altered since last build
			if package.last_change >= package.last_build:
				packages.append(package)
				continue

			if package.buildable:
				packages_may.append(package)

		packages_may = sorted(packages_may, key=lambda p: p.last_build)

		while len(packages) < 10 and packages_may:
			package = packages_may.pop(0)
			packages.append(package)

		# Bad hack because we lack a _build method
		args.packages = [p.name for p in packages]
		args.onlydeps = False
		args.withdeps = False
		args.shell = False

		self.call_build(args)
