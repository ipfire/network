#!/usr/bin/python

import curses
import logging
import sys
import time

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
        prefix = '[%(levelname)7s | %(asctime)s]' % \
            record.__dict__
        color = self._colors.get(record.levelno, self._normal)
        formatted = color + prefix + self._normal + " " + record.message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            formatted = formatted.rstrip() + "\n" + record.exc_text
        return formatted.replace("\n", "\n    ")
