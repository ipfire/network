###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2008  Michael Tremer & Christian Schmidt                      #
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

include Makefile.inc

SUBDIRS = isys po

all: lang-names subdirs

lang-names: lang-table
	PYTHONPATH="./src/:." LANG=en_US.UTF-8 \
		python scripts/getlangnames.py > lang-names.tmp
	mv lang-names.tmp lang-names

install: all
	for d in $(SUBDIRS); do \
		make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; \
		[ $$? = 0 ] || exit 1; \
	done
	-mkdir -p $(PYTHONLIBDIR)
	cp -f *.py lang-{table,names} $(PYTHONLIBDIR)
	chmod 755 $(PYTHONLIBDIR)/installer.py
	sed -e "s/VERSION/$(VERSION)/g" \
		-e "s/SNAME/$(SNAME)/g" \
		-e "s/PNAME/$(PNAME)/g" \
		-e "s/NAME/$(NAME)/g" \
		-e "s/KVER/$(KVER)/g" \
		-i $(PYTHONLIBDIR)/constants.py
	-mkdir -p $(DESTDIR)/sbin
	install -m 755 $(PSNAME) $(DESTDIR)/sbin/$(PSNAME)

clean:
	rm -vf *.o *.so *.pyc *.pyo lang-names{,.tmp}
	for d in $(SUBDIRS); do make -C $$d clean; done

subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done
