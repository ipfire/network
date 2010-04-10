#!/usr/bin/python

import time

from constants import *

class Logger:
    def __init__(self):
        self.logfile = open(LOGFILE, "w+")

        self.logline = "%s %8s: %s\n" # time, group, message

    def critical(self, msg):
        self.logfile.write(self.logline % (self.time(), "CRITICAL", msg,))
        self.flush()

    def info(self, msg):
        self.logfile.write(self.logline % (self.time(), "INFO",     msg,))
        self.flush()

    def debug(self, msg):
        self.logfile.write(self.logline % (self.time(), "DEBUG",    msg,))
        self.flush()

    def error(self, msg):
        self.logfile.write(self.logline % (self.time(), "ERROR",    msg,))
        self.flush()

    def warning(self, msg):
        self.logfile.write(self.logline % (self.time(), "WARNING",  msg,))
        self.flush()

    def stdout(self, msg):
        self.logfile.write(self.logline % (self.time(), "STDOUT",   msg,))
        self.flush()
        print msg

    def time(self):
        return time.strftime("%d %b %Y %H:%M:%S")

    def __del__(self):
        self.logfile.close()

    def flush(self):
        self.logfile.flush()
