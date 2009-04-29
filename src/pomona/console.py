#!/usr/bin/python

from language import Language, LanguageWindow
from keyboard import Keyboard, KeyboardWindow

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)
N_ = lambda x: x

from constants import *

class Console:
    def __init__(self, installer):
        self.installer = installer

        self.language = Language(installer)
        self.keyboard = Keyboard(installer)
