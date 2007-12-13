###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2007  Michael Tremer & Christian Schmidt                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

include ../Makefile.inc

POTFILES = ../src/*.py
NONPOTFILES = 

POS = $(wildcard *.po)
FMTCATALOGS = $(patsubst %.po,%.mo,$(POS))

MSGMERGE = msgmerge -v

all: $(FMTCATALOGS)

$(SNAME).pot: $(POTFILES) $(NONPOTFILES)
	xgettext --from-code=UTF-8 --default-domain=$(SNAME) \
		--keyword=_ --keyword=N_ $(POTFILES)
	if cmp -s $(SNAME).po $(SNAME).pot; then \
	    rm -f $(SNAME).po; \
	else \
	    mv $(SNAME).po $(SNAME).pot; \
	fi

refresh-po:
	for cat in $(POS); do \
		lang=`basename $$cat .po`; \
		if $(MSGMERGE) $$lang.po $(SNAME).pot > $$lang.pot ; then \
			mv -f $$lang.pot $$lang.po ; \
			echo "$(MSGMERGE) of $$lang succeeded" ; \
		else \
			echo "$(MSGMERGE) of $$lang failed" ; \
			rm -f $$lang.pot ; \
		fi \
	done

update-po: $(SNAME).pot refresh-po

install: all
	mkdir -p $(PREFIX)/$(INSTALLNLSDIR)
	for n in $(FMTCATALOGS); do \
	    l=`basename $$n .mo`; \
	    $(INSTALL) -m 755 -d $(PREFIX)/$(INSTALLNLSDIR)/$$l; \
	    $(INSTALL) -m 755 -d $(PREFIX)/$(INSTALLNLSDIR)/$$l/LC_MESSAGES; \
	    $(INSTALL) -m 644 $$n \
				$(PREFIX)/$(INSTALLNLSDIR)/$$l/LC_MESSAGES/$(SNAME).mo; \
	done

%.mo: %.po
	msgfmt --check -o $@ $<

report:
	@for cat in $(POS); do \
		echo -n "$$cat: "; \
		msgfmt -v --statistics -o /dev/null $$cat; \
	done

clean:
	rm -f *.mo missing
