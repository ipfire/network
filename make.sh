#!/usr/bin/python

import sys
import naoki

# silence Python 2.6 buggy warnings about Exception.message
if sys.version_info[:2] == (2, 6):
	import warnings
	warnings.filterwarnings(
		action="ignore",
		message="BaseException.message has been deprecated as of Python 2.6",
		category=DeprecationWarning)

# Initialize system
n = naoki.Naoki()

try:
	# Run...
	n.run()
	exitStatus = 0

except (SystemExit,):
	raise

except (KeyboardInterrupt,):
	exitStatus = 7
	n.log.error("Exiting on user interrupt, <CTRL>-C")

sys.exit(exitStatus)
