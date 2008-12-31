#
# language_text.py: text mode language selection dialog
#
# Copyright 2001-2007 Red Hat, Inc.
#
# This software may be freely redistributed under the terms of the GNU
# library public license.
#
# You should have received a copy of the GNU Library Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

from snack import *
from constants import *

from pyfire.translate import _

import logging
log = logging.getLogger("pomona")

class LanguageWindow:
    def __call__(self, screen, pomona):
        id = pomona.id
        languages = id.console.availableLangs()
        languages.sort()

        current = id.console.lang

        height = min((8, len(languages)))
        buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON]

        translated = []
        for lang in languages:
            translated.append((_(lang), id.console.getNickByName(lang)))

        (button, choice) = \
                ListboxChoiceWindow(screen, _("Language Selection"),
                _("What language would you like to use during the "
                        "installation process?"), translated,
                buttons, width = 30, default = _(current), scroll = 1,
                height = height, help = "lang")

        if button == TEXT_BACK_CHECK:
            return INSTALL_BACK

        id.console.setLanguage(choice)
        id.timezone.setTimezoneInfo(id.console.getDefaultTimeZone())

        pomona.intf.drawFrame()

        return INSTALL_OK
