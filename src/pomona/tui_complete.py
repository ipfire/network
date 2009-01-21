#
# complete_text.py: text mode congratulations windows
#
# Copyright 2001-2006 Red Hat, Inc.
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
from constants import *

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

class FinishedWindow:
    def __call__ (self, screen, pomona):
        bootstr = ""

        floppystr = _("Press <Enter> to end the installation process.\n\n")
        bottomstr = _("<Enter> to exit")

        screen.pushHelpLine(string.center(bottomstr, screen.width))

        txt = _("Congratulations, your %s installation is "
                "complete.\n\n"
                "%s%s") %(name, floppystr, bootstr)
        foo = _("For information on errata (updates and bug fixes), visit "
                "%s.\n\n"
                "Information on using your "
                "system is available in the %s wiki at "
                "%s.") %(bugurl, name, wikiurl,)

        rc = ButtonChoiceWindow(screen, _("Complete"), txt,
                                      [ _("Reboot") ], help = "finished", width=60)

        return INSTALL_OK
