#!/usr/bin/python

import fcntl
import os
import struct
import sys
import termios

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
	def __init__(self, name, arguments=[], parsers=[]):
		self.name = name
		self.arguments = arguments
		self.parsers = parsers

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


class _Argument(object):
	DEFAULT_HELP = "No help available"

	def __init__(self, name, args, **kwargs):
		self.name = name
		self.args = args
		self.help = kwargs.get("help", self.DEFAULT_HELP)

		self._parsed = False
		self._parsed_args = []

	def parse(self, args):
		raise NotImplementedError

	def value(self):
		raise NotImplementedError


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


class Choice(_Argument):
	def __init__(self, *args, **kwargs):
		_Argument.__init__(self, *args, **kwargs)

		self.choices = kwargs.get("choices", [])

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


class List(_Argument):
	def __init__(self, name, **kwargs):
		_Argument.__init__(self, name, [], **kwargs)

	def parse(self, args):
		self._parsed = True
		self._parsed_args = args

		return []

	def value(self):
		return self._parsed_args


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
		self.naoki.logging.debug(args.debug)

		# Set architecture
		arches.set(args.arch)

	def __parse(self):
		parser = Parser("root",
			arguments=[
				Option("help",  ["-h", "--help"],  help="Show help text"),
				Option("quiet", ["-q", "--quiet"], help="Set quiet mode"),
				Option("debug", ["-d", "--debug"], help="Set debugging mode"),
				Choice("arch",  ["-a", "--arch"], help="Set architecture",
					choices=[arch for arch in arches.all]),
			],
			parsers=[
				# Build
				Parser("build",
					arguments=[
						List("packages"),
					]),

				# Toolchain
				Parser("toolchain",
					parsers=[
						Parser("download"),
						Parser("build"),
						Parser("tree"),
					]),

				# Package
				Parser("package",
					parsers=[
						Parser("info",
							arguments=[
								Option("long", ["-l", "--long"]),
								Option("machine", ["--machine"]),
								Option("wiki", ["--wiki"]),
								List("packages"),
							]),
						Parser("tree"),
						Parser("list",
							arguments=[
								Option("long", ["-l", "--long"]),
								Option("unbuilt", ["-u", "--unbuilt"]),
								Option("built", ["-b", "--built"]),
							]),
						Parser("groups",
							arguments=[
								Option("wiki", ["--wiki"]),
							]),
					]),

				# Source
				Parser("source",
					parsers=[
						Parser("download",
							arguments=[
								List("packages"),
							]),
						Parser("upload",
							arguments=[
								List("packages"),
							]),
						Parser("clean"),
					]),

				# Check
				Parser("check",
					parsers=[
						Parser("host"),
					]),

				# Batch
				Parser("batch",
					parsers=[
						Parser("cron"),
					]),
			])

		args = parser.parse(sys.argv[1:])

		if args:
			raise ParsingError, "Unknown argument(s) passed: %s" % args

		return parser.values

	def help(self):
		print "PRINTING HELP TEXT"


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
