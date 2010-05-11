#!/usr/bin/python

import curses
import logging
import logging.config
import logging.handlers
import sys
import time

# fix for python 2.4 logging module bug:
logging.raiseExceptions = 0

from constants import *

class Logging(object):
	def __init__(self, naoki):
		self.naoki = naoki

		self.setup()

	def setup(self):
		self.log = logging.getLogger()

		log_ini = config["log_config_file"]
		if os.path.exists(log_ini):
			logging.config.fileConfig(log_ini)

		if sys.stderr.isatty():
			curses.setupterm()
			self.log.handlers[0].setFormatter(_ColorLogFormatter())

		# Set default configuration
		self.quiet(config["quiet"])

		self.log.handlers[0].setLevel(logging.DEBUG)
		logging.getLogger("naoki").propagate = 1

		if not os.path.isdir(LOGDIR):
			os.makedirs(LOGDIR)
		fh = logging.handlers.RotatingFileHandler(config["log_file"],
			maxBytes=10*1024**2, backupCount=6)
		fh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		fh.setLevel(logging.NOTSET)
		self.log.addHandler(fh)

	def quiet(self, val):
		if val:
			self.log.debug("Enabled quiet logging mode")
			self.log.handlers[0].setLevel(logging.WARNING)
		else:
			#self.log.debug("Enabled verbose logging mode")
			self.log.handlers[0].setLevel(logging.INFO)

	def debug(self, val):
		if val:
			self.log.handlers[0].setLevel(logging.DEBUG)
			self.log.debug("Enabled debug logging mode")
		else:
			self.log.debug("Disabled debug logging mode")
			self.log.handlers[0].setLevel(logging.INFO)

	def _setupBuildLogger(self, logger, package):
		logger.setLevel(logging.DEBUG)
		logger.parent = self.log
		logger.propagate = 1

		logfile = package.logfile
		logdir  = os.path.dirname(logfile)

		if not os.path.exists(logdir):
			os.makedirs(logdir)

		handler = logging.handlers.RotatingFileHandler(logfile,
			maxBytes=10*1024**2, backupCount=5)

		formatter = logging.Formatter("[BUILD] %(message)s")
		handler.setFormatter(formatter)

		logger.addHandler(handler)

	def getBuildLogger(self, package):
		logger = logging.getLogger(package.id)
		if not logger.handlers:
			self._setupBuildLogger(logger, package)

		return logger


# defaults to module verbose log
# does a late binding on log. Forwards all attributes to logger.
# works around problem where reconfiguring the logging module means loggers
# configured before reconfig dont output.
class getLog(object):
    def __init__(self, name=None, prefix="", *args, **kargs):
        if name is None:
            frame = sys._getframe(1)
            name = frame.f_globals["__name__"]

        self.name = prefix + name

    def __getattr__(self, name):
        logger = logging.getLogger(self.name)
        return getattr(logger, name)


# Borrowed from tornado
class _ColorLogFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        logging.Formatter.__init__(self, *args, **kwargs)
        fg_color = curses.tigetstr("setaf") or curses.tigetstr("setf") or ""
        self._colors = {
            logging.DEBUG: curses.tparm(fg_color, 4), # Blue
            logging.INFO: curses.tparm(fg_color, 2), # Green
            logging.WARNING: curses.tparm(fg_color, 3), # Yellow
            logging.ERROR: curses.tparm(fg_color, 1), # Red
        }
        self._normal = curses.tigetstr("sgr0")

    def format(self, record):
        try:
            record.message = record.getMessage()
        except Exception, e:
            record.message = "Bad message (%r): %r" % (e, record.__dict__)
        record.asctime = time.strftime(
            "%H:%M:%S", self.converter(record.created))
        prefix = " %(levelname)-7s" % record.__dict__
        color = self._colors.get(record.levelno, self._normal)
        formatted = color + prefix + self._normal + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")
