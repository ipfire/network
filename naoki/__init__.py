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
	packages = []

	def __init__(self, op):
		(self.options, self.args) = op.parse_args()

		# set up basic logging until config file can be read
		logging.basicConfig(format="%(levelname)s: %(message)s",
			level=logging.WARNING)
		self.log = logging.getLogger()

		self.config = config
		self.setup_logging()
		
		self.log.info("Started naoki on %s" % time.strftime("%a, %d %b %Y %H:%M:%S"))
		
		# dump configuration to log
		self.log.debug("Configuration:")
		for k, v in self.config.items():
			self.log.debug("    %s:  %s" % (k, v))

	def setup_logging(self):
		log_ini = self.config["log_config_file"]
		if os.path.exists(log_ini):
			logging.config.fileConfig(log_ini)

		if sys.stderr.isatty():
			curses.setupterm()
			self.log.handlers[0].setFormatter(logger._ColorLogFormatter())

		if self.options.verbose == 0:
			self.log.handlers[0].setLevel(logging.WARNING)
		elif self.options.verbose == 1:
			self.log.handlers[0].setLevel(logging.INFO)
		elif self.options.verbose == 2:
			self.log.handlers[0].setLevel(logging.DEBUG)
			logging.getLogger("naoki").propagate = 1

		fh = logging.handlers.RotatingFileHandler(self.config["log_file"],
			maxBytes=1073741824, backupCount=6)
		fh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		fh.setLevel(logging.NOTSET)
		self.log.addHandler(fh)

	def addPackage(self, package):
		self.log.debug("Add package: %s" % repr(package))
		self.packages.append(package)

	def action(self, action=None):
		if not action:
			action = self.options.mode

		# Parse all package names
		for pkg_name in self.args:
			pkg = package.find(pkg_name)
			if not pkg:
				self.log.warn("Not a package: %s" % pkg_name)
				continue
			self.addPackage(pkg)

		if action == "download":
			if not self.packages:
				self.packages = package.list()
			for pkg in self.packages:
				pkg.download()

		elif action == "info":
			for pkg in self.packages:
				print pkg.info

		elif action == "list-packages":
			for pkg in package.list():
				print "%s" % pkg
		
		elif action == "list-groups":
			print "\n".join(naoki.package.groups())

		elif action == "rebuild":
			self.build()

	def build(self):
		requeue = []
		while True:
			if not self.packages:
				return

			# Get first package that is to be done
			build = Build(self.packages.pop(0))
			
			if build.package.isBuilt:
				self.log.warn("Package is already built. Will overwrite.")

			self.log.info("Building %s..." % build.package.name)
			build.build()


class Build(object):
	def __init__(self, package):
		self.package = package

		self.environment = chroot.Environment(self.package)

	def init(self):
		self.environment.init()

		self.extractAll()
	
	def extractAll(self):
		packages = self.package.deps + self.package.build_deps
		for pkg in config["mandatory_packages"]:
			pkg = package.find(pkg)
			if not pkg in packages:
				packages.append(pkg)

		packages = package.depsolve(packages, recursive=True)

		for pkg in packages:
			pkg.extract(self.environment.chrootPath())

	def build(self):
		self.package.download()
		self.init()
		self.make("package")

	def make(self, target):
		file = self.package.filename.replace(BASEDIR, "/usr/src")
		cmd = "make --no-print-directory -C %s -f %s %s" % (os.path.dirname(file),
			file, target,)
		self.environment.doChroot(cmd)
