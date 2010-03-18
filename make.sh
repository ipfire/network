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

# Command line parsing
parser = argparse.ArgumentParser(
	description = "Command to control the naoki buildsystem"
)

parser.add_argument("-q", "--quiet", action="store_true", help="run in silent mode")
parser.add_argument("-d", "--debug", action="store_true", help="run in debug mode")
parser.add_argument("-a", "--arch", default=arches.default["name"], help="set architecture")
subparsers = parser.add_subparsers(help="sub-command help")

# Build command
parser_build = subparsers.add_parser("build", help="build command")
parser_build.set_defaults(action="build")
parser_build.add_argument("package", nargs="+", help="package name")


# Toolchain command
parser_toolchain = subparsers.add_parser("toolchain", help="toolchain command")
parser_toolchain.set_defaults(action="toolchain")
subparsers_toolchain = parser_toolchain.add_subparsers(help="sub-command help")

	# toolchain build
parser_toolchain_build = subparsers_toolchain.add_parser("build", help="build toolchain")
parser_toolchain_build.set_defaults(subaction="build")

	# toolchain build
parser_toolchain_download = subparsers_toolchain.add_parser("download", help="download toolchain")
parser_toolchain_download.set_defaults(subaction="download")


# Package command
parser_package = subparsers.add_parser("package", help="package command")
parser_package.set_defaults(action="package")
subparsers_package = parser_package.add_subparsers(help="sub-command help")

	# package info [-l, --long]
parser_package_info = subparsers_package.add_parser("info", help="show package information")
parser_package_info.set_defaults(subaction="info")
parser_package_info.add_argument("-l", "--long", action="store_true", help="print in long format")
parser_package_info.add_argument("--machine", action="store_true", help="output in machine readable format")
parser_package_info.add_argument("--wiki", action="store_true", help="output in wiki format")
parser_package_info.add_argument("package", nargs="+", help="package name")

	# package tree
parser_package_tree = subparsers_package.add_parser("tree", help="show package tree")
parser_package_tree.set_defaults(subaction="tree")

	# package list [-l, --long]
parser_package_list = subparsers_package.add_parser("list", help="show package list")
parser_package_list.set_defaults(subaction="list")
parser_package_list.add_argument("-l", "--long", action="store_true", help="print list in long format")

	# package groups
parser_package_groups = subparsers_package.add_parser("groups", help="show package groups")
parser_package_groups.set_defaults(subaction="groups")
parser_package_groups.add_argument("--wiki", action="store_true", help="output in wiki format")


# Source command
parser_source = subparsers.add_parser("source", help="source command")
parser_source.set_defaults(action="source")
subparsers_source = parser_source.add_subparsers(help="sub-command help")

	# source download
parser_source_download = subparsers_source.add_parser("download", help="download source tarballs")
parser_source_download.set_defaults(subaction="download")
parser_source_download.add_argument("package", nargs="*", help="package name")

	# source upload
parser_source_upload = subparsers_source.add_parser("upload", help="upload source tarballs")
parser_source_upload.set_defaults(subaction="upload")
parser_source_upload.add_argument("package", nargs="*", help="package name")

	# source clean
parser_source_clean = subparsers_source.add_parser("clean", help="cleanup unused source tarballs")
parser_source_clean.set_defaults(subaction="clean")


# Check command
parser_check = subparsers.add_parser("check", help="check command")
parser_check.set_defaults(action="check")
subparsers_check = parser_check.add_subparsers(help="sub-command help")

	# check host
parser_check_host = subparsers_check.add_parser("host", help="check if host fulfills requirements")
parser_check_host.set_defaults(subaction="host")


# Batch command
parser_batch = subparsers.add_parser("batch", help="batch command")
parser_batch.set_defaults(action="batch")
subparsers_batch = parser_batch.add_subparsers(help="sub-command help")

	# batch cron
parser_batch_cron = subparsers_batch.add_parser("cron", help="gets called by a cron daemon")
parser_batch_cron.set_defaults(subaction="cron")


# parse the command line
args = parser.parse_args()

if args.debug:
	print "Command line arguments:", args

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
