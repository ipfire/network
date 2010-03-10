#!/usr/bin/python

import os
import string
import locale
import gettext

import pyfire.executil as executil
from pyfire.config import ConfigFile
import keyboard_models

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)
N_ = lambda x: x

# Converts a single language into a "language search path". For example,
# de_DE.utf8@euro would become "de_DE.utf8@eueo de_DE.utf8 de_DE de"
def expandLangs(astring):
    langs = [astring]
    charset = None
    # remove charset ...
    if '.' in astring:
        langs.append(string.split(astring, '.')[0])

    if '@' in astring:
        charset = string.split(astring, '@')[1]

    # also add 2 character language code ...
    if len(astring) > 2:
        if charset:
            langs.append("%s@%s" %(astring[:2], charset))

    langs.append(astring[:2])

    return langs

class Console(ConfigFile):
    def __init__(self, filename):
        ConfigFile.__init__(self, filename)

        # default to us and unicode enabled
        self.info["KEYMAP"] = "us"
        self.info["UNICODE"] = "yes"

        self._mods = keyboard_models.KeyboardModels()

        self.nativeLangNames = {}
        self.locales = {}

        if os.environ.has_key("LANG"):
            self.lang = self.fixLang(os.environ["LANG"])
        else:
            self.lang = "en_US.UTF-8"

        # nick -> (name, short name, font, keyboard, timezone) mapping
        search = ( '../lang-table', 'lang-table', '/usr/lib/pomona/lang-table', '/etc/lang-table')
        for path in search:
            if os.access(path, os.R_OK):
                f = open(path, "r")
                break

        for line in f.readlines():
            string.strip(line)
            l = string.split(line, '\t')

            # throw out invalid lines
            if len(l) < 6:
                continue

            self.locales[l[3]] = (l[0], l[1], l[2], l[4], string.strip(l[5]))
            self.nativeLangNames[l[0]] = _(l[0])

        f.close()

    def availableLangs(self):
        return self.nativeLangNames.keys()

    def setKeymap(self, keymap):
        self.info["KEYMAP"] = keymap

    def getKeymap(self):
        return self.info["KEYMAP"]

    def getDefaultKeymap(self):
        return self.locales[self.canonLangNick(self.lang)][3]

    def getDefaultFont(self, nick):
        return self.locales[self.canonLangNick(nick)][2]

    def getDefaultTimeZone(self):
        return self.locales[self.canonLangNick(self.lang)][4]

    def _getKeyboardModels(self):
        return self._mods.get_models()

    modelDict = property(_getKeyboardModels)

    def getKeymapName(self):
        kbd = self.modelDict[self.getKeymap()]
        if not kbd:
            return ""
        (name, layout, model, variant, options) = kbd
        return name

    # Convert what might be a shortened form of a language's nick (en or
    # en_US, for example) into the full version (en_US.UTF-8).  If we
    # don't find it, return our default of en_US.UTF-8.
    def canonLangNick(self, nick):
        for key in self.locales.keys():
            if nick in expandLangs(key):
                return key
        return "en_US.UTF-8"

    def getNickByName(self, name):
        for k in self.locales.keys():
            row = self.locales[k]
            if row[0] == name:
                return k

    def fixLang(self, langToFix):
        ret = None
        for lang in self.locales.keys():
            if lang == langToFix:
                (a, b, font, c, d) = self.locales[lang]
                if font == "none":
                    ret = "en_US.UTF-8"
                    self.targetLang = lang

        if ret is None:
            ret = langToFix

        return ret

    def getNativeLangName(self, lang):
        return self.nativeLangNames[lang]

    def getLangNameByNick(self, nick):
        return self.locales[self.canonLangNick(nick)][0]

    def getCurrentLangSearchList(self):
        return expandLangs(self.lang) + ['C']

    def setLanguage(self, nick):
        self.info['LANG'] = os.environ["LANG"] = \
            self.lang = self.fixLang(self.canonLangNick(nick))
        os.environ["LC_NUMERIC"] = 'C'

        if self.locales[self.lang][2] == "none":
            self.info['FONT'] = None
        else:
            self.info['FONT'] = self.locales[self.lang][2]

        try:
            locale.setlocale(locale.LC_ALL, "")
        except locale.Error:
            pass

    def activate(self):
        console_kbd = self.getKeymap()
        if not console_kbd:
            return

        # Call loadkeys to change the console keymap
        if os.access("/bin/loadkeys", os.X_OK):
            command = "/bin/loadkeys"
        elif os.access("/usr/bin/loadkeys", os.X_OK):
            command = "/usr/bin/loadkeys"
        else:
            command = "/bin/loadkeys"
        argv = [ command, console_kbd ]

        if os.access(argv[0], os.X_OK) == 1:
            executil.execWithRedirect(argv[0], argv, stdout="/dev/tty5", stderr="/dev/tty5")
