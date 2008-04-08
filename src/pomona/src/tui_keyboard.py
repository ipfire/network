#
# keyboard_text: text mode keyboard setup dialogs
#
# Copyright 2001-2002 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

import inutil
from snack import *
from constants import *
from flags import flags

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

class KeyboardWindow:
	def __call__(self, screen, pomona):
		if flags.virtpconsole:
			return INSTALL_NOOP
		
		keyboards = pomona.id.keyboard.modelDict.keys()
		keyboards.sort()

		if pomona.id.keyboard.beenset:
			default = pomona.id.keyboard.get()
		else:
			default = pomona.id.instLanguage.getDefaultKeyboard()

		(button, choice) = \
			ListboxChoiceWindow(screen, _("Keyboard Selection"),
																	_("Which model keyboard is attached to this computer?"), keyboards, 
				buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON], width = 30, scroll = 1, height = 8,
				default = default, help = "kybd")
        
		if button == TEXT_BACK_CHECK:
			return INSTALL_BACK

		pomona.id.keyboard.set(keyboards[choice])
		pomona.id.keyboard.beenset = 1

		pomona.id.keyboard.activate()

		return INSTALL_OK
