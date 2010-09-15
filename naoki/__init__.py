#!/usr/bin/python

import ConfigParser
import fcntl
import os.path
import random
import sys
import time

import architectures
import build
import environ
import generators
import logger
import repositories
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
			"generate" : self.call_generate,
			"batch" : self.call_batch,
		}

		return actionmap[args.action.name](args.action)

	def _get_source_repos(self, arch=None):
		if not arch:
			arches = architectures.Architectures()
			arch = arches.get_default()

		return repositories.SourceRepositories(arch=arch)

	def call_build(self, args):
		# Source repository
		repo = self._get_source_repos()

		# Initialize job queue
		jobs = build.Jobs()

		if args.all:
			raise Exception, "XXX to be implemented"
		else:
			for name in args.packages:
				p = repo.find_package_by_name(name)
				if not p:
					raise Exception, "Could not find package: %s" % name

				p = build.Build(p, ignore_dependency_errors=args.ignore_dependency_errors)
				jobs.add(p)

		#return builder.run(ignore_dependency_errors=args.ignore_dependency_errors)
		while jobs.has_jobs:
			jobs.process_next()

	def call_package(self, args):
		if not args.has_key("action"):
			self.cli.help()
			return 1

		actionmap = {
			"info" : self.call_package_info,
			"list" : self.call_package_list,
			"groups" : self.call_package_groups,
			"raw"  : self.call_package_raw,
		}

		return actionmap[args.action.name](args.action)

	def call_package_info(self, args):
		# Source repositories
		repo = self._get_source_repos()

		for package in repo.packages:
			if args.packages:
				if not package.name in args.packages:
					continue

			if args.long:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(PKG_NAME)s
Version       : %(PKG_VER)s
Release       : %(PKG_REL)s

  %(PKG_SUMMARY)s

%(PKG_DESCRIPTION)s

Maintainer    : %(PKG_MAINTAINER)s
License       : %(PKG_LICENSE)s

Objects       : %(PKG_OBJECTS)s
Patches       : %(PKG_PATCHES)s
--------------------------------------------------------------------------------\
""")
			else:
				print package.fmtstr("""\
--------------------------------------------------------------------------------
Name          : %(PKG_NAME)s
Version       : %(PKG_VER)s
Release       : %(PKG_REL)s

  %(PKG_SUMMARY)s

--------------------------------------------------------------------------------\
""")

	def call_package_list(self, args):
		repo = self._get_source_repos()

		for package in repo.packages:
			# Skip unbuilt packages if we want built packages
			if args.built and not package.is_built:
				continue

			# Skip built packages if we want unbuilt only
			if args.unbuilt and package.is_built:
				continue

			if args.long:
				print package.fmtstr("%(PKG_NAME)-32s | %(PKG_VER)-15s | %(PKG_SUMMARY)s")
			else:
				print package.name

	def call_package_groups(self, args):
		# XXX
		#groups = backend.get_group_names()
		#print "\n".join(groups)
		pass

	def call_package_raw(self, args):
		repo = self._get_source_repos()

		p = repo.find_package_by_name(args.package)
		if not p:
			raise Exception, "Could not find package: %s" % args.package

		p.print_raw_info()

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
		repo = self._get_source_repos()

		for package in repo.packages:
			if args.packages:
				if not package.name in args.packages:
					continue

			package.source_download()

	def call_source_upload(self, args):
		pass # TODO

	def call_shell(self, args):
		# Load architecture set
		arches = architectures.Architectures()

		# Choose default architecture
		arch = arches.get_default()

		# Load all source packages
		repo = repositories.SourceRepositories(arch=arch)

		# Pick the one we need
		p = repo.find_package_by_name(args.package)
		if not p:
			raise Exception, "Could not find package: %s" % args.package

		# Initialize and run the shell
		shell = build.PackageShell(p)

		return shell.shell()

	def call_generate(self, args):
		if not args.type in ("iso",):
			return

		arch = architectures.Architectures().get_default()

		gen = generators.Generator(args.type, arch)
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
		pkgs = []
		candidates = []

		# Choose architecture
		arches = architectures.Architectures()
		arch = arches.get_default()

		repo = repositories.SourceRepositories(arch=arch)
		for package in repo.packages:
			if not package.is_built:
				pkgs.append(package)
			else:
				candidates.append(package)

		# Initialize a job queue
		jobs = build.Jobs()

		# Add all unbuilt packages to the job queue
		for package in pkgs:
			package = build.Build(package)
			jobs.add(package)

		# If we have less than ten packages in the queue we add some random
		# ones
		need_counter = 10 - len(jobs)
		if need_counter >= 0:
			for candidate in random.sample(candidates, need_counter):
				candidate = build.Build(candidate)
				jobs.add(candidate)

		while jobs.has_jobs:
			jobs.process_next()
