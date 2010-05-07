#/usr/bin/python

import os
import locale
import string

from snack import ListboxChoiceWindow

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

from constants import *

# Converts a single language into a "language search path". For example,
# de_DE.utf8@euro would become "de_DE.utf8@euro de_DE.utf8 de_DE de"
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

class Language:
    def __init__(self, installer):
        self.installer = installer

        self.languages = {}

        # nick -> (name, short name, font, keyboard, timezone) mapping
        search = ('lang-table', '../lang-table', '/usr/lib/pomona/lang-table', '/etc/lang-table')
        for path in search:
            if os.access(path, os.R_OK):
                f = open(path, "r")
                break

        for line in f.readlines():
            line = line.strip() #string.strip(line)
            l = line.split("\t") #.split(line, '\t')

            # throw out invalid lines
            if len(l) < 6:
                continue

            (name, short, font, locale, keyboard, timezone) = l
            self.languages[short] = (name, _(name), font, locale, timezone)

        f.close()

    def getAllLanguages(self):
        ret = []
        for (name, name2, font, locale, timezone) in self.languages.values():
            ret.append(name2)
        return ret

    def getLanguage(self):
        return "English" # XXX

    def setLanguage(self, lang):
        self.installer.log.debug("Set language to \"%s\"" % lang)
        os.environ["LC_NUMERIC"] = 'C'
        #XXX os.environ["LANG"] = "de_DE.utf8"

        try:
            locale.setlocale(locale.LC_ALL, "")
        except locale.Error:
            pass


class LanguageWindow:
    def __call__(self, installer):
        language = installer.ds.console.language

        languages = language.getAllLanguages()
        languages.sort()

        current = language.getLanguage()

        (button, choice) = ListboxChoiceWindow(installer.intf.screen,
                           _("Language Selection"),
                           _("What language would you like to use during the "
                             "installation process?"), languages,
                           buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                           width = 30, default = _(current), scroll = 1,
                           height = min((8, len(languages))))

        if button == TEXT_BACK_CHECK:
            return INSTALL_BACK

        language.setLanguage(languages[choice])
        #installer.ds.timezone.setTimezoneInfo(id.console.getDefaultTimeZone())

        return INSTALL_OK


if __name__ == "__main__":
    language = Language(None)
    print language.getAllLanguages()
