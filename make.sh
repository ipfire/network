#!/usr/bin/python

import sys
try:
	import argparse
except ImportError:
	import naoki.argparse as argparse

import naoki

arches = naoki.arches
config = naoki.config

# silence Python 2.6 buggy warnings about Exception.message
if sys.version_info[:2] == (2, 6):
	import warnings
	warnings.filterwarnings(
		action="ignore",
		message="BaseException.message has been deprecated as of Python 2.6",
		category=DeprecationWarning)

parser = argparse.ArgumentParser(
	description = "Command to control the naoki buildsystem"
)

parser.add_argument("-q", "--quiet", action="store_true",
	help="run in silent mode")
parser.add_argument("-a", "--arch", default=arches.default["name"],
	help="set architecture")
parser.add_argument("--toolchain", action="store_true",
	help="toolchain mode")

subparsers = parser.add_subparsers(help="sub-command help")

parser_build = subparsers.add_parser("build", help="build command")
parser_build.set_defaults(action="build")
parser_build.add_argument("packages", nargs="+", help="packages...")

parser_toolchain = subparsers.add_parser("toolchain", help="toolchain command")
parser_toolchain.set_defaults(action="toolchain")

subparsers_toolchain = parser_toolchain.add_subparsers(help="sub-command help")
parser_toolchain_build = subparsers_toolchain.add_parser("build",
	help="build toolchain")
parser_toolchain_build.set_defaults(subaction="build")

parser_package = subparsers.add_parser("package", help="package command")
parser_package.set_defaults(action="package")

subparsers_package = parser_package.add_subparsers(help="sub-command help")
parser_package_tree = subparsers_package.add_parser("tree",
	help="show package tree")
parser_package_tree.set_defaults(subaction="tree")

parser_package_list = subparsers_package.add_parser("list",
	help="show package list")
parser_package_list.set_defaults(subaction="list")

# parse the command line
args = parser.parse_args()

# Are we in the toolchain mode?
config["toolchain"] = args.toolchain

# Set default arch
arches.set(args.arch)

kwargs = {}
for key, val in args._get_kwargs():
	kwargs[key] = val

try:
	n = naoki.Naoki()
	n(**kwargs)
	exitStatus = 0

except (SystemExit,):
	raise

except (KeyboardInterrupt,):
	exitStatus = 7
	n.log.error("Exiting on user interrupt, <CTRL>-C")

sys.exit(exitStatus)
