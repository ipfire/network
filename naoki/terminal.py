#!/usr/bin/python

import fcntl
import os
import struct
import termios

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
