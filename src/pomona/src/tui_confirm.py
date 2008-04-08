#
# confirm_text.py: text mode install/upgrade confirmation window
#
# Copyright 2001-2003 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import sys

from snack import *
from constants import *
from pyfire.translate import _

class BeginInstallWindow:
	def __call__ (self, screen, pomona):
		rc = ButtonChoiceWindow(screen, _("Installation to begin"),
																		_("Now, we got all information we need for "
																			"installation. If there is something you "
																			"want change you can still go back. "
																			"If not choose OK to start."),
																		buttons = [ _("OK"), _("Back") ],
																		help = "begininstall")
		if rc == string.lower(_("Back")):
			return INSTALL_BACK

		if rc == 0:
			rc2 = pomona.intf.messageWindow(_("Reboot?"),
																			_("The system will be rebooted now."),
																			type="custom", custom_icon="warning",
																			custom_buttons=[_("_Back"), _("_Reboot")])
			if rc2 == 1:
				sys.exit(0)
			else:
				return INSTALL_BACK
		elif rc == 1: # they asked to go back
			return INSTALL_BACK
	
		return INSTALL_OK
