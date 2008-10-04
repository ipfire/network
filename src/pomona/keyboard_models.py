#!/usr/bin/python -tt
#
# keyboard_models.py - keyboard model list
#
# Brent Fox <bfox@redhat.com>
# Mike Fulbright <msf@redhat.com>
# Jeremy Katz <katzj@redhat.com>
#
# Copyright 2002-2007 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

from pyfire.translate import _, N_

def gkn(str):
    idx = str.find("|")
    if idx == -1:
        return str
    return str[idx + 1:]

class KeyboardModels:
    def get_models(self):
        return self.modelDict

    def __init__(self):
        # NOTE: to add a keyboard model to this dict, copy the comment
        # above all of them, and then the key should be the console layout
        # name.  val is [N_('keyboard|Keyboard Name'), xlayout, kbmodel,
        # variant, options]
        self._modelDict = {
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ar-azerty'               : [N_('keyboard|Arabic (azerty)'), 'us,ara', 'pc105', 'azerty', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ar-azerty-digits'        : [N_('keyboard|Arabic (azerty/digits)'), 'us,ara', 'pc105', 'azerty_digits', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ar-digits'               : [N_('keyboard|Arabic (digits)'), 'us,ara', 'pc105', 'digits', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ar-qwerty'               : [N_('keyboard|Arabic (qwerty)'), 'us,ara', 'pc105', 'qwerty', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ar-qwerty-digits'        : [N_('keyboard|Arabic (qwerty/digits)'), 'us,ara', 'pc105', 'qwerty_digits', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'be-latin1'               : [N_('keyboard|Belgian (be-latin1)'), 'be', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ben'                      : [N_('keyboard|Bengali (Inscript)'), 'us,in', 'pc105', 'ben', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ben-probhat'             : [N_('keyboard|Bengali (Probhat)'), 'us,in', 'pc105', 'ben_probhat', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'bg_bds-utf8'             : [N_('keyboard|Bulgarian'), 'us,bg', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'bg_pho-utf8'             : [N_('keyboard|Bulgarian (Phonetic)'), 'us,bg', 'pc105', ',phonetic', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'br-abnt2'                : [N_('keyboard|Brazilian (ABNT2)'), 'br', 'abnt2', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'cf'                      : [N_('keyboard|French Canadian'), 'ca(fr)', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'croat'                   : [N_('keyboard|Croatian'), 'hr', 'pc105', '', '' ],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'cz-us-qwertz'            : [N_('keyboard|Czech'), 'us,cz', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'cz-lat2'                 : [N_('keyboard|Czech (qwerty)'), 'cz', 'pc105', 'qwerty', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'de'                      : [N_('keyboard|German'), 'de', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'de-latin1'               : [N_('keyboard|German (latin1)'), 'de', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'de-latin1-nodeadkeys'    : [N_('keyboard|German (latin1 w/ no deadkeys)'), 'de', 'pc105', 'nodeadkeys', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'dev'                     : [N_('keyboard|Devanagari (Inscript)'), 'us,dev', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'dvorak'                   : [N_('keyboard|Dvorak'), 'us', 'pc105', 'dvorak', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'dk'                      : [N_('keyboard|Danish'), 'dk', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'dk-latin1'               : [N_('keyboard|Danish (latin1)'), 'dk', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'es'                      : [N_('keyboard|Spanish'), 'es', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'et'                      : [N_('keyboard|Estonian'), 'ee', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fi'                      : [N_('keyboard|Finnish'), 'fi', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fi-latin1'               : [N_('keyboard|Finnish (latin1)'), 'fi', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr'                      : [N_('keyboard|French'), 'fr', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr-latin9'               : [N_('keyboard|French (latin9)'), 'fr', 'pc105', 'latin9', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr-latin1'               : [N_('keyboard|French (latin1)'), 'fr', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr-pc'                   : [N_('keyboard|French (pc)'), 'fr', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr_CH'                   : [N_('keyboard|Swiss French'), 'fr_CH', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'fr_CH-latin1'            : [N_('keyboard|Swiss French (latin1)'), 'ch', 'pc105', 'fr', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'gr'                      : [N_('keyboard|Greek'), 'us,gr', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'guj'                     : [N_('keyboard|Gujarati (Inscript)'), 'us,in', 'pc105', 'guj', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'gur'                     : [N_('keyboard|Punjabi (Inscript)'), 'us,gur', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'hu'                      : [N_('keyboard|Hungarian'), 'hu', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'hu101'                   : [N_('keyboard|Hungarian (101 key)'), 'hu', 'pc105', 'qwerty', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'is-latin1'               : [N_('keyboard|Icelandic'), 'is', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'it'                      : [N_('keyboard|Italian'), 'it', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'it-ibm'                  : [N_('keyboard|Italian (IBM)'), 'it', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'it2'                     : [N_('keyboard|Italian (it2)'), 'it', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'jp106'                   : [N_('keyboard|Japanese'), 'jp', 'jp106', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ko'               : [N_('keyboard|Korean'), 'kr', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'la-latin1'               : [N_('keyboard|Latin American'), 'latam', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'mk-utf'                  : [N_('keyboard|Macedonian'), 'us,mkd', 'pc105', '','grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'nl'                      : [N_('keyboard|Dutch'), 'nl', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'no'                      : [N_('keyboard|Norwegian'), 'no', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'pl2'                      : [N_('keyboard|Polish'), 'pl', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'pt-latin1'               : [N_('keyboard|Portuguese'), 'pt', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ro_win'                  : [N_('keyboard|Romanian'), 'ro', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ru'                      : [N_('keyboard|Russian'), 'us,ru', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sr-cy'                 : [N_('keyboard|Serbian'), 'cs', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sr-latin'                 : [N_('keyboard|Serbian (latin)'), 'cs', 'pc105', 'latin', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sv-latin1'               : [N_('keyboard|Swedish'), 'se', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sg'                      : [N_('keyboard|Swiss German'), 'ch', 'pc105', 'de_nodeadkeys', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sg-latin1'               : [N_('keyboard|Swiss German (latin1)'), 'ch', 'pc105', 'de_nodeadkeys', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'sk-qwerty'               : [N_('keyboard|Slovak (qwerty)'), 'sk', 'pc105', '', 'qwerty'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'slovene'                 : [N_('keyboard|Slovenian'), 'si', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'tml-inscript'            : [N_('keyboard|Tamil (Inscript)'), 'us,in', 'pc105', 'tam', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'tml-uni'                 : [N_('keyboard|Tamil (Typewriter)'), 'us,in', 'pc105', 'tam_TAB', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'trq'                     : [N_('keyboard|Turkish'), 'tr', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'uk'                      : [N_('keyboard|United Kingdom'), 'gb', 'pc105', '', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'ua-utf'                  : [N_('keyboard|Ukrainian'), 'us,ua', 'pc105', '', 'grp:shifts_toggle,grp_led:scroll'],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'us-acentos'              : [N_('keyboard|U.S. International'), 'us', 'pc105', 'intl', ''],
                # Translators: the word before the bar is just context and
                # doesn't need to be translated. Only after will be translated.
                'us'                      : [N_('keyboard|U.S. English'), 'us+inet', 'pc105', '', ''],
                }

    def _get_models(self):
        ret = {}
        for (key, item) in self._modelDict.items():
            ret[key] = [gkn(_(item[0])), item[1], item[2], item[3], item[4]]
        return ret

    modelDict = property(_get_models)

def get_supported_models():
    models = KeyboardModels()
    maps = models.modelDict.keys()
    maps.sort()
    for map in maps:
        print map

if __name__ == "__main__":
    get_supported_models()
