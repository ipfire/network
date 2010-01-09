#!/usr/bin/python

import sys
from optparse import OptionParser

import naoki

op = OptionParser()

# toolchain mode
op.add_option("--toolchain", action="store_const", const=1,
				dest="toolchain", default=0, help="toolchain mode")

# verbosity
op.add_option("-v", "--verbose", action="store_const", const=2,
				dest="verbose", default=1, help="verbose build")
op.add_option("-q", "--quiet", action="store_const", const=0,
				dest="verbose", help="quiet build")

# modes (basic commands)
op.add_option("--download", action="store_const", const="download",
				dest="mode", help="download files")
op.add_option("--build", "--rebuild", action="store_const",
				const="rebuild", dest="mode", default='rebuild',
				help="rebuild the specified packages")
op.add_option("--info", action="store_const", const="info", dest="mode",
				help="return some info about the specified packages")
op.add_option("--list-packages", action="store_const", const="list-packages",
				dest="mode", help="list all packages")
op.add_option("--list-groups", action="store_const", const="list-groups",
				dest="mode", help="list all groups")
op.add_option("--list-tree", action="store_const", const="list-tree",
				dest="mode", help="list the dependency tree")

n = naoki.Naoki(op)
exitStatus = 0

try:
	n.action()

except (SystemExit,):
	raise

except (KeyboardInterrupt,):
	exitStatus = 7
	n.log.error("Exiting on user interrupt, <CTRL>-C")

sys.exit(exitStatus)
