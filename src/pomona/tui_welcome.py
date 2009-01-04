
import os
from snack import *

from constants import *
from console import _

class WelcomeWindow:
    def __call__(self, screen, infire):
        rc = ButtonChoiceWindow(screen, _("%s") % (name,),
                                                                                                                        _("Welcome to %s!\n\n")
                                                                                                                        % (name, ),
                                                                                                                        buttons = [TEXT_OK_BUTTON], width = 50,
                help = "welcome")

        return INSTALL_OK
