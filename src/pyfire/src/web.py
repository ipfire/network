#!/usr/bin/python
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2008  Michael Tremer & Christian Schmidt                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import os
import cgi

from pyfire.translate import _, textdomain, addPoPath
import pyfire.net as net

addPoPath("/srv/www/ipfire/cgi-bin/po/")
textdomain("ipfire")

### Variables
allowed_endings = [ "cgi", "py",]

class IPFireWeb:
	def __init__(self, title, icon):
		self.title = title
		self.icon  = icon
		self.hostname = net.gethostname()

		### This is a hash with all of the important vars:
		##            - "title"	- The title of the current page
		##            - "icon"	- The displayed icon
		##            - "hostname" - The local hostname
		self.info = {	"title": self.title,
				"icon": self.icon,
				"hostname": self.hostname,
			    }

		### This is the menu tree
		##  Every index has got a hash with a few arguments:
		##                        - "title" which is the title of the section
		##                        - "subs"  is a tuple with all the submenu items
		##  One submenu items looks like this:
		##                        (_("Home"), "index.py")
		##           name of the item ^^^^     ^^^^^^^^ filename
		self.menu = {}

		for section in os.listdir("/etc/ipfire/menu"):
			f = open("/etc/ipfire/menu/" + section)
			self.menu[section] = { "title" : "", "subs" : [],}
			for line in f.readlines():
				(item, filename) = line.rstrip("\n").split(":",1)
				if item == "title":
					self.menu[section]["title"] = _(filename)
				else:
					self.menu[section]["subs"].append((_(item), filename))
			f.close()

	def __run__(self):
		### This initializes the http(s) response
		self.showhttpheaders()
		self.getcgihash()

		### Page
		self.openpage()
		self.content()
		self.closepage()

	def openpage(self):
		print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
	<!-- HTML HEADER -->
	<head>
		<title>%(hostname)s - IPFire v3 - %(title)s</title>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<link rel="shortcut icon" href="/favicon.ico" />
		<link rel="stylesheet" type="text/css" href="include/style.css" />
	</head>
	<!-- HTML HEADER END -->""" % self.info
		self.openheader()
		self.genbigmenu()
		self.closeheader()
		self.openbigbox()

	def closepage(self):
		self.closebigbox()
		self.footer()

	def openheader(self):
		print """
	<!-- HTML BODY -->
	<body>
		<!-- IPFIRE HEADER -->
		<div id="header">
			<div id="header_inner" class="fixed">
				<!-- IPFIRE LOGO -->
				<div id="logo">
					<img src="/images/icons/%(icon)s" width="48px" height="48px" alt="Symbol" class="symbol" />
					<h1><span>%(hostname)s</span></h1>
					<br />
					<h2>%(title)s</h2>
				</div>""" % self.info
	def closeheader(self):
		print """			</div>
		</div>
		<!-- IPFIRE HEADER END -->"""

	def openbigbox(self):
		print """
		<!-- IPFIRE BODY -->
		<div id="main">
			<div id="main_inner" class="fixed">
				<div id="primaryContent_2columns">
					<div id="columnA_2columns">
					<!-- IPFIRE CONTENT -->"""

	def openbox(self, title):
		print """
					<div class="post">
						<h3>%s</h3>""" % (title,)

	def closebox(self):
		print """
					</div>
					<br class="clear" />"""

	def closebigbox(self):
		print """
					<!-- IPFIRE CONTENT END -->
					</div>
				</div>"""
		self.genmenu()

	def genbigmenu(self):
		print """
				<!-- IPFIRE MENU -->
				<div id="menu">
					<ul>"""
		sections = self.menu.keys()
		sections.sort()
		for section in sections:
			filename = self.menu[section]["subs"][0][1]
			print "\t\t\t\t\t\t",
			print "<li><a href=\"/%s\">%s</a></li>" % \
				(filename, self.menu[section]["title"])
		print """
					</ul>
				</div>"""

	def genmenu(self):
		this_file = os.path.basename(os.environ["SCRIPT_NAME"])
		this_section = None

		for i in self.menu.keys():
			for j in self.menu[i]["subs"]:
				if this_file == os.path.basename(j[1]):
					this_section = i
					break
			if not this_section is None:
				break

		if this_section is None:
			return

		print """
				<div id="secondaryContent_2columns">
					<div id="columnC_2columns">
						<h4><span>Side</span>menu</h4>
						<ul class="links">"""

		for item in self.menu[this_section]["subs"]:
			print "\t\t\t\t\t\t\t",
			if item[1] == this_file:
				print "<li class=\"selected\">",
			else:
				print "<li>",
			print "<a href=\"/cgi-bin/%s\">%s</a></li>" \
				% (item[1], item[0],)

		print """
						</ul>
					</div>
				</div>
				<br class="clear" />"""

	def footer(self):
		print """
				<div id="footer" class="fixed">
					<span>Load average: %(load)s
				</div>""" % { "load" : os.getloadavg() }
		print """
			</div>
		</div>
	</body>
</html>
"""

	def showhttpheaders(self, type="text/html"):
		print "Pragma: no-cache"
		print "Cache-control: no-cache"
		print "Connection: close"
		print "Content-type:" + type
		print
		# An empty line ends the header

	def getcgihash(self):
		self.cgihash = cgi.FieldStorage()

	def content(self):
		self.openbox(_("Error"))
		print "This site has no content defined, yet. Please define site.content()."
		self.closebox()
