#!/usr/bin/python

import os

from snack import ListboxChoiceWindow

import gettext
_ = lambda x: gettext.ldgettext("pomona", x)

from constants import *

def gkn(str):
    idx = str.find("|")
    if idx == -1:
        return str
    return str[idx + 1:]

class KeyboardModels:
    def __init__(self):
        self._modelDict = {
                'ar-azerty'               : [N_('keyboard|Arabic (azerty)'), 'us,ara', 'pc105', 'azerty', 'grp:shifts_toggle,grp_led:scroll'],
                'ar-azerty-digits'        : [N_('keyboard|Arabic (azerty/digits)'), 'us,ara', 'pc105', 'azerty_digits', 'grp:shifts_toggle,grp_led:scroll'],
                'ar-digits'               : [N_('keyboard|Arabic (digits)'), 'us,ara', 'pc105', 'digits', 'grp:shifts_toggle,grp_led:scroll'],
                'ar-qwerty'               : [N_('keyboard|Arabic (qwerty)'), 'us,ara', 'pc105', 'qwerty', 'grp:shifts_toggle,grp_led:scroll'],
                'ar-qwerty-digits'        : [N_('keyboard|Arabic (qwerty/digits)'), 'us,ara', 'pc105', 'qwerty_digits', 'grp:shifts_toggle,grp_led:scroll'],
                'be-latin1'               : [N_('keyboard|Belgian (be-latin1)'), 'be', 'pc105', '', ''],
                'ben'                     : [N_('keyboard|Bengali (Inscript)'), 'us,in', 'pc105', 'ben', 'grp:shifts_toggle,grp_led:scroll'],
                'ben-probhat'             : [N_('keyboard|Bengali (Probhat)'), 'us,in', 'pc105', 'ben_probhat', 'grp:shifts_toggle,grp_led:scroll'],
                'bg_bds-utf8'             : [N_('keyboard|Bulgarian'), 'us,bg', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'bg_pho-utf8'             : [N_('keyboard|Bulgarian (Phonetic)'), 'us,bg', 'pc105', ',phonetic', 'grp:shifts_toggle,grp_led:scroll'],
                'br-abnt2'                : [N_('keyboard|Brazilian (ABNT2)'), 'br', 'abnt2', '', ''],
                'cf'                      : [N_('keyboard|French Canadian'), 'ca(fr)', 'pc105', '', ''],
                'croat'                   : [N_('keyboard|Croatian'), 'hr', 'pc105', '', '' ],
                'cz-us-qwertz'            : [N_('keyboard|Czech'), 'us,cz', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'cz-lat2'                 : [N_('keyboard|Czech (qwerty)'), 'cz', 'pc105', 'qwerty', ''],
                'de'                      : [N_('keyboard|German'), 'de', 'pc105', '', ''],
                'de-latin1'               : [N_('keyboard|German (latin1)'), 'de', 'pc105', '', ''],
                'de-latin1-nodeadkeys'    : [N_('keyboard|German (latin1 w/ no deadkeys)'), 'de', 'pc105', 'nodeadkeys', ''],
                'dev'                     : [N_('keyboard|Devanagari (Inscript)'), 'us,dev', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'dvorak'                  : [N_('keyboard|Dvorak'), 'us', 'pc105', 'dvorak', ''],
                'dk'                      : [N_('keyboard|Danish'), 'dk', 'pc105', '', ''],
                'dk-latin1'               : [N_('keyboard|Danish (latin1)'), 'dk', 'pc105', '', ''],
                'es'                      : [N_('keyboard|Spanish'), 'es', 'pc105', '', ''],
                'et'                      : [N_('keyboard|Estonian'), 'ee', 'pc105', '', ''],
                'fi'                      : [N_('keyboard|Finnish'), 'fi', 'pc105', '', ''],
                'fi-latin1'               : [N_('keyboard|Finnish (latin1)'), 'fi', 'pc105', '', ''],
                'fr'                      : [N_('keyboard|French'), 'fr', 'pc105', '', ''],
                'fr-latin9'               : [N_('keyboard|French (latin9)'), 'fr', 'pc105', 'latin9', ''],
                'fr-latin1'               : [N_('keyboard|French (latin1)'), 'fr', 'pc105', '', ''],
                'fr-pc'                   : [N_('keyboard|French (pc)'), 'fr', 'pc105', '', ''],
                'fr_CH'                   : [N_('keyboard|Swiss French'), 'fr_CH', 'pc105', '', ''],
                'fr_CH-latin1'            : [N_('keyboard|Swiss French (latin1)'), 'ch', 'pc105', 'fr', ''],
                'gr'                      : [N_('keyboard|Greek'), 'us,gr', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'guj'                     : [N_('keyboard|Gujarati (Inscript)'), 'us,in', 'pc105', 'guj', 'grp:shifts_toggle,grp_led:scroll'],
                'gur'                     : [N_('keyboard|Punjabi (Inscript)'), 'us,gur', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'hu'                      : [N_('keyboard|Hungarian'), 'hu', 'pc105', '', ''],
                'hu101'                   : [N_('keyboard|Hungarian (101 key)'), 'hu', 'pc105', 'qwerty', ''],
                'is-latin1'               : [N_('keyboard|Icelandic'), 'is', 'pc105', '', ''],
                'it'                      : [N_('keyboard|Italian'), 'it', 'pc105', '', ''],
                'it-ibm'                  : [N_('keyboard|Italian (IBM)'), 'it', 'pc105', '', ''],
                'it2'                     : [N_('keyboard|Italian (it2)'), 'it', 'pc105', '', ''],
                'jp106'                   : [N_('keyboard|Japanese'), 'jp', 'jp106', '', ''],
                'ko'                      : [N_('keyboard|Korean'), 'kr', 'pc105', '', ''],
                'la-latin1'               : [N_('keyboard|Latin American'), 'latam', 'pc105', '', ''],
                'mk-utf'                  : [N_('keyboard|Macedonian'), 'us,mkd', 'pc105', '','grp:shifts_toggle,grp_led:scroll'],
                'nl'                      : [N_('keyboard|Dutch'), 'nl', 'pc105', '', ''],
                'no'                      : [N_('keyboard|Norwegian'), 'no', 'pc105', '', ''],
                'pl2'                     : [N_('keyboard|Polish'), 'pl', 'pc105', '', ''],
                'pt-latin1'               : [N_('keyboard|Portuguese'), 'pt', 'pc105', '', ''],
                'ro_win'                  : [N_('keyboard|Romanian'), 'ro', 'pc105', '', ''],
                'ru'                      : [N_('keyboard|Russian'), 'us,ru', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'sr-cy'                   : [N_('keyboard|Serbian'), 'cs', 'pc105', '', ''],
                'sr-latin'                : [N_('keyboard|Serbian (latin)'), 'cs', 'pc105', 'latin', ''],
                'sv-latin1'               : [N_('keyboard|Swedish'), 'se', 'pc105', '', ''],
                'sg'                      : [N_('keyboard|Swiss German'), 'ch', 'pc105', 'de_nodeadkeys', ''],
                'sg-latin1'               : [N_('keyboard|Swiss German (latin1)'), 'ch', 'pc105', 'de_nodeadkeys', ''],
                'sk-qwerty'               : [N_('keyboard|Slovak (qwerty)'), 'sk', 'pc105', '', 'qwerty'],
                'slovene'                 : [N_('keyboard|Slovenian'), 'si', 'pc105', '', ''],
                'tml-inscript'            : [N_('keyboard|Tamil (Inscript)'), 'us,in', 'pc105', 'tam', 'grp:shifts_toggle,grp_led:scroll'],
                'tml-uni'                 : [N_('keyboard|Tamil (Typewriter)'), 'us,in', 'pc105', 'tam_TAB', 'grp:shifts_toggle,grp_led:scroll'],
                'trq'                     : [N_('keyboard|Turkish'), 'tr', 'pc105', '', ''],
                'uk'                      : [N_('keyboard|United Kingdom'), 'gb', 'pc105', '', ''],
                'ua-utf'                  : [N_('keyboard|Ukrainian'), 'us,ua', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                'us-acentos'              : [N_('keyboard|U.S. International'), 'us', 'pc105', 'intl', ''],
                'us'                      : [N_('keyboard|U.S. English'), 'us+inet', 'pc105', '', ''],
                }

    def getAllModels(self):
        ret = []
        for model in self._modelDict.values():
            ret.append(gkn(_(model[0])))
        return ret

class Keyboard:
    def __init__(self, installer):
        self.installer = installer

        self.models = KeyboardModels()

    def getKeymap(self):
        return gkn(self.models._modelDict["us"][0]) # XXX

    def setKeymap(self, keymap):
        self.installer.log.debug("Set keymap to \"%s\"" % keymap)


class KeyboardWindow:
    def __call__(self, installer):
        #if flags.virtpconsole:
        #    return INSTALL_NOOP

        keyboard = installer.ds.console.keyboard

        keyboards = keyboard.models.getAllModels()
        keyboards.sort()

        default = keyboard.getKeymap()

        (button, choice) = ListboxChoiceWindow(installer.intf.screen,
                           _("Keyboard Selection"),
                           _("Which model keyboard is attached to this computer?"),
                           keyboards, buttons = [TEXT_OK_BUTTON, TEXT_BACK_BUTTON],
                           width = 30, scroll = 1, height = 8, default = default)

        if button == TEXT_BACK_CHECK:
            return INSTALL_BACK

        keyboard.setKeymap(keyboards[choice])
        #keyboard.activate()

        return INSTALL_OK
