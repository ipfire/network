
from snack import *
from pyfire.translate import _
from constants import *
import os

class WelcomeWindow:
    def __call__(self, screen, infire):
        rc = ButtonChoiceWindow(screen, _("%s") % (name,),
                                                                                                                        _("Welcome to %s!\n\n")
                                                                                                                        % (name, ),
                                                                                                                        buttons = [TEXT_OK_BUTTON], width = 50,
                help = "welcome")

        return INSTALL_OK
