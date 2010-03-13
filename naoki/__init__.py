#!/usr/bin/python

import ConfigParser
import curses
import logging
import logging.config
import logging.handlers
import os.path
import sys
import time

import logger
import package
import util

from constants import *

# fix for python 2.4 logging module bug:
logging.raiseExceptions = 0

class Naoki(object):
	def __init__(self):
		self.setup_logging()

		self.log.debug("Successfully initialized naoki instance")
		for k, v in config.items():
			self.log.debug("    %s: %s" % (k, v))

	def setup_logging(self):
		self.log = logging.getLogger()

		log_ini = config["log_config_file"]
		if os.path.exists(log_ini):
			logging.config.fileConfig(log_ini)

		if sys.stderr.isatty():
			curses.setupterm()
			self.log.handlers[0].setFormatter(logger._ColorLogFormatter())

		if config["quiet"]:
			self.log.handlers[0].setLevel(logging.WARNING)
		else:
			self.log.handlers[0].setLevel(logging.INFO)

		fh = logging.handlers.RotatingFileHandler(config["log_file"],
			maxBytes=10*1024**2, backupCount=6)
		fh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		fh.setLevel(logging.NOTSET)
		self.log.addHandler(fh)

	def __call__(self, action, **kwargs):
		if action == "build":
			self.call_build(kwargs.get("package"))

		elif action == "toolchain":
			self.call_toolchain(kwargs.get("subaction"), kwargs.get("arch"))
		
		elif action == "package":
			self.call_package(kwargs.pop("subaction"), **kwargs)

	def call_toolchain(self, subaction, arch):
		tc = chroot.Toolchain(arch)
		
		if subaction == "build":
			tc.build()

		elif subaction == "download":
			tc.download()

	def call_build(self, packages):
		force = True

		if packages == ["all"]:
			force = False
			packages = package.list()
		else:
			packages = [package.find(p) for p in packages]
			for p in packages:
				if not p: packages.remove(p)

		self._build(packages, force=force)

	def call_package(self, subaction, **kwargs):
		if subaction == "list":
			for pkg in self.packages:
				print pkg.info_line(long=kwargs["long"])

		elif subaction == "info":
			packages = [package.find(pkg) for pkg in kwargs.get("package")]
			packages.sort()

			if kwargs["wiki"]:
				for pkg in packages:
					print pkg.info_wiki()
				return
			
			delimiter = "----------------------------------------------------\n"

			print delimiter.join([pkg.info(long=kwargs["long"]) for pkg in packages])
		
		elif subaction == "tree":
			print package.deptree(self.packages)
		
		elif subaction == "groups":
			groups = package.groups()

			if kwargs["wiki"]:
				print "====== All available groups of packages ======"
				for group in groups:
					print group.wiki_headline()
					for pkg in group.packages:
						print pkg.info_wiki(long=False)

				return

			print "\n".join(package.group_names())

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
	def packages(self):
		return package.list()
