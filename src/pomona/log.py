#!/usr/bin/python

import time

from constants import *

class Logger:
    def __init__(self):
        self.logfile = open(LOGFILE, "w+")

        self.logline = "%s %8s: %s\n" # time, group, message

    def critical(self, msg):
        self.logfile.write(self.logline % (self.time(), "CRITICAL", msg,))

    def info(self, msg):
        self.logfile.write(self.logline % (self.time(), "INFO",     msg,))

    def debug(self, msg):
        self.logfile.write(self.logline % (self.time(), "DEBUG",    msg,))

    def error(self, msg):
        self.logfile.write(self.logline % (self.time(), "ERROR",    msg,))

    def warning(self, msg):
        self.logfile.write(self.logline % (self.time(), "WARNING",  msg,))

    def stdout(self, msg):
        self.logfile.write(self.logline % (self.time(), "STDOUT",   msg,))
        print msg

    def time(self):
        return time.strftime("%d %b %Y %H:%M:%S")

    def __del__(self):
        self.logfile.close()
