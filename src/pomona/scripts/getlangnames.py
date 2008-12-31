#!/usr/bin/python

import os
import sys
sys.path.append("..")

import gettext
import console

_ = lambda x: gettext.ldgettext("pomona", x)

console = console.Console("/etc/sysconfig/console")
names = {}
for k in console.locales.keys():
    os.environ["LANG"] = console.locales[k][3]
    names[console.locales[k][0]] = _(console.locales[k][0])

nameList = names.keys()
nameList.sort()

for k in nameList:
    print "%s\t%s" % (k, names[k])
