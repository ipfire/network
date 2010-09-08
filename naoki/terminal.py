#!/usr/bin/python

import fcntl
import os
import struct
import sys
import termios

import arches
from constants import *

class ParsingError(Exception):
	pass


class NameSpace(dict):
	def __getattr__(self, attr):
		try:
			return self.__getitem__(attr)
		except KeyError:
			raise AttributeError


class Parser(object):
	def __init__(self, name, arguments=[], parsers=[], **kwargs):
		self.name = name
		self.arguments = arguments
		self.parsers = parsers

		self._help = kwargs.get("help", "No help available")

		self.subparser = None

	def __repr__(self):
		return "<Parser %s>" % self.name

	def check(self, args):
		if not args:
			return False

		return self.name == args[0]

	def parse(self, args):
		if args and self.name == args[0]:
			args = args[1:]

		for argument in self.arguments:
			args = argument.parse(args)

		if args and self.parsers:
			for parser in self.parsers:
				if not parser.check(args):
					continue

				self.subparser = parser
				break

			if self.subparser:
				args = self.subparser.parse(args)

		return args

	@property
	def values(self):
		ret = NameSpace(
			name=self.name,
		)
		if self.subparser:
			ret["action"] = self.subparser.values

		for argument in self.arguments:
			ret[argument.name] = argument.value()

		return ret

	@property
	def help_line(self):
		ret = ""
		for argument in self.arguments:
			ret += " %s" % argument.help_line

		if self.parsers:
			ret += " <command ...>"

		return ret

	def help(self, indent=0):
		ret = self.name

		help_line = self.help_line
		if help_line:
			ret += self.help_line + "\n"
			if self._help:
				ret += "\n  " + self._help + "\n"
		else:
			ret += " - " + self._help + "\n"

		if self.arguments:
			ret += "\n"
			for argument in sorted(self.arguments):
				ret += "  %15s  | %s\n" % (", ".join(argument.args), argument.help)
			ret += "\n"

		if self.parsers:
			ret += "\n"
			for parser in self.parsers:
				ret += parser.help(indent=indent + 4)

		indent_string = " " * 4
		return indent_string.join(["%s\n" % line for line in ret.split("\n")])


class _Argument(object):
	DEFAULT_HELP = "No help available"

	def __init__(self, name, args, **kwargs):
		self.name = name
		self.args = sorted(args, reverse=True, key=str.__len__)
		self.help = kwargs.get("help", self.DEFAULT_HELP)

		self._parsed = False
		self._parsed_args = []

	def __cmp__(self, other):
		return cmp(self.name, other.name)

	def parse(self, args):
		raise NotImplementedError

	def value(self):
		raise NotImplementedError

	@property
	def help_line(self):
		raise NotImplementedError


class Argument(_Argument):
	def __init__(self, name, **kwargs):
		_Argument.__init__(self, name, [], **kwargs)

	def parse(self, args):
		self._parsed = True

		if len(args) >= 1:
			self._parsed_args = args[:1]

		return args[1:]

	def value(self):
		if self._parsed_args:
			return self._parsed_args[0]

		return []

	@property
	def help_line(self):
		return self.name


class Option(_Argument):
	def parse(self, args):
		self._parsed = True

		new_args = []
		for arg in args:
			if arg in self.args:
				self._parsed_args.append(arg)
			else:
				new_args.append(arg)

		return new_args

	def value(self):
		for arg in self._parsed_args:
			if arg in self.args:
				return True

		return False

	@property
	def help_line(self):
		return "[%s]" % ", ".join(self.args)


class Choice(_Argument):
	def __init__(self, *args, **kwargs):
		_Argument.__init__(self, *args, **kwargs)

		self.choices = kwargs.get("choices", [])
		self.choices.sort()

		self.help += " [%s]" % ", ".join(self.choices)

	def parse(self, args):
		self._parsed = True

		new_args = []
		next_arg = False
		for arg in args:
			if next_arg:
				if self.choices and not arg in self.choices:
					raise ParsingError, "'%s' is not an allowed choice" % arg

				self._parsed_args.append(arg)
				next_arg = False
				continue

			if arg in self.args:
				self._parsed_args.append(arg)
				next_arg = True
			else:
				new_args.append(arg)

		return new_args

	def value(self):
		if self._parsed_args:
			return self._parsed_args[-1]

		return None

	@property
	def help_line(self):
		return "[%s %s]" % (", ".join(self.args), self.name.upper())


class List(_Argument):
	def __init__(self, name, **kwargs):
		_Argument.__init__(self, name, [], **kwargs)

	def parse(self, args):
		self._parsed = True
		self._parsed_args = args

		return []

	def value(self):
		return self._parsed_args

	@property
	def help_line(self):
		name = self.name[:-1] + " "
		return "[" + name * 2 + "...]"


class Commandline(object):
	def __init__(self, naoki):
		self.naoki = naoki

		# Parse the stuff
		self.args = self.__parse()

		# ... afterwards, process global directives
		self.__process_global(self.args)

	def __process_global(self, args):
		# Set quiet mode
		self.naoki.logging.quiet(args.quiet)

		# Set debugging mode
		config.debug = args.debug
		self.naoki.logging.debug(args.debug)

		# Set architecture
		arches.set_default(args.arch)

	def __parse(self):
		parser = Parser(sys.argv[0],
			help="Global help",
			arguments=[
				Option("help",  ["-h", "--help"],  help="Show help text"),
				Option("quiet", ["-q", "--quiet"], help="Set quiet mode"),
				Option("debug", ["-d", "--debug"], help="Set debugging mode"),
				Choice("arch",  ["-a", "--arch"], help="Set architecture",
					choices=[arch.name for arch in arches.all()]),
			],
			parsers=[
				# Build
				Parser("build",
					help="Primary build command",
					arguments=[
						Option("all", ["--all"], help="Build all packages"),
						Option("withdeps", ["--with-deps"], help="Build all dependencies first if needed"),
						Option("onlydeps", ["--only-deps"], help="Build only dependencies that belong to a package"),
						Option("shell", ["-s", "--shell"], help="Change into a chroot environment"),
						Option("ignore_dependency_errors", ["-i", "--ignore-dependency-errors"],
							help="Ignore dependency errors."),
						List("packages", help="Give a list of packages to build or say 'all'"),
					]),

				# Package
				Parser("package",
					parsers=[
						Parser("info",
							help="Show detailed information about given packages",
							arguments=[
								Option("long", ["-l", "--long"], help="Show long list of information"),
								Option("machine", ["--machine"], help="Output in machine parseable format"),
								List("packages"),
							]),
						Parser("tree", help="Show package tree"),
						Parser("list",
							help="Show package list",
							arguments=[
								Option("long", ["-l", "--long"], help="Show list with lots of information"),
								Option("unbuilt", ["-u", "--unbuilt"], help="Do only show unbuilt packages"),
								Option("built", ["-b", "--built"], help="Do only show already built packages"),
							]),
						Parser("groups",
							help="Show package groups",
							),
					]),

				# Source
				Parser("source",
					help="Handle source tarballs",
					parsers=[
						Parser("download",
							help="Download source tarballs",
							arguments=[
								List("packages"),
							]),
						Parser("upload",
							help="Upload source tarballs",
							arguments=[
								List("packages"),
							]),
						Parser("clean", help="Cleanup unused tarballs"),
					]),

				# Check
				Parser("check",
					help="Check commands",
					parsers=[
						Parser("host", help="Check if host fullfills prerequisites"),
					]),

				# Batch
				Parser("batch",
					help="Batch command - use with caution",
					parsers=[
						Parser("cron", help="Command that gets called by cron"),
					]),

				# Shell
				Parser("shell",
					help="Shell environment",
					arguments=[
						Argument("package", help="Package to process."),
					]),

				# Repository
				Parser("repository",
					help="Repository commands",
					parsers=[
						Parser("clean",
							help="Cleanup the repository",
							arguments=[
								List("names", help="List of repositories"),
							]),
						Parser("build",
							help="Build the repository",
							arguments=[
								List("names", help="List of repositories"),
							]),
					]),

				# Generator
				Parser("generate",
					help="Generator command",
					arguments=[
						Argument("type", help="Type of image to generate"),
					]),
			])

		self.parser = parser

		args = parser.parse(sys.argv[1:])

		if args:
			raise ParsingError, "Unknown argument(s) passed: %s" % args

		return parser.values

	def help(self):
		print >>sys.stderr, self.parser.help(),


DEFAULT_COLUMNS = 80
DEFAULT_LINES = 25

def get_size():
	"""
		returns the size of the terminal
		
		tupel: lines, columns
	"""
	def ioctl_GWINSZ(fd):
		try:
			cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))
		except:
			return None

		return cr

	cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
	if not cr:
		try:
			fd = os.open(os.ctermid(), os.O_RDONLY)
			cr = ioctl_GWINSZ(fd)
			os.close(fd)
		except:
			pass

	if not cr:
		try:
			cr = (os.environ['LINES'], os.environ['COLUMNS'])
		except:
			cr = (DEFAULT_LINES, DEFAULT_COLUMNS)

	return int(cr[1]), int(cr[0])

def get_lines():
	return get_size()[0]

def get_columns():
	return get_size()[1]


if __name__ == "__main__":
	cl = Commandline(naoki=None)
