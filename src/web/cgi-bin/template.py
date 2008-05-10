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

from pyfire.web import IPFireWeb
from pyfire.translate import _

class Site(IPFireWeb):
	def __init__(self, title, icon="ipfire.png"):
		IPFireWeb.__init__(self, title, icon)

	def content(self):
		self.openbox(_("Template"))
		print _("This is a template page to show new developers how our"
			"nice framework works.")
		self.closebox()

site = Site(title=_("Template"), icon="ipfire.png")
site.__run__()
