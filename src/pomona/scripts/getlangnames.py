import sys
sys.path.append("..")
from pyfire.translate import _
import pyfire.translate
import language

langs = language.Language()
names = {}
for k in langs.localeInfo.keys():
    langs.setRuntimeLanguage(k)
    names[langs.localeInfo[k][0]] = _(langs.localeInfo[k][0])

nameList = names.keys()
nameList.sort()

for k in nameList:
    print "%s\t%s" % (k, names[k])
