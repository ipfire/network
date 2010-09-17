#!/usr/bin/python

class Error(Exception):
	"base class for our errors."
	def __init__(self, msg, status=None):
		Exception.__init__(self)
		self.msg = msg
		self.resultcode = 1
		if status is not None:
			self.resultcode = status

	def __str__(self):
		return self.msg


class BuildRootLocked(Error):
	"build root in use by another process."
	def __init__(self, msg):
		Error.__init__(self, msg)
		self.msg = msg
		self.resultcode = 60


class commandTimeoutExpired(Error):
	def __init__(self, msg):
		Error.__init__(self, msg)
		self.msg = msg
		self.resultcode = 10


class DownloadError(Error):
	pass


class DependencyResolutionError(Error):
	pass
