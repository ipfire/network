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

include ../Makefile.inc

SUBDIRS = isys

all: subdirs

install: all
	-mkdir -p $(PYTHONLIBDIR)
	cp -vf *.py ../lang-{table,names} $(PYTHONLIBDIR)
	chmod -v 755 $(PYTHONLIBDIR)/installer.py
	for d in $(SUBDIRS); do make -C $$d install; [ $$? = 0 ] || exit 1; done
	
	sed -e "s/VERSION/$(VERSION)/g" \
			-e "s/SNAME/$(SNAME)/g" \
			-e "s/PNAME/$(PNAME)/g" \
			-e "s/NAME/$(NAME)/g" \
			-e "s/KVER/$(KVER)/g" \
			-i $(PYTHONLIBDIR)/constants.py

	sh ../py-compile $(PYTHONLIBDIR)/*.py
	-mkdir -p $(DESTDIR)/sbin
	#ln -svf ../usr/lib/$(PSNAME)/installer.py $(DESTDIR)/sbin/$(PSNAME)
	install -m 755 -v $(PSNAME) $(DESTDIR)/sbin/$(PSNAME)

clean:
	rm -f *.o *.so *.pyc *.pyo
	for d in $(SUBDIRS); do make -C $$d clean; [ $$? = 0 ] || exit 1; done

subdirs:
	for d in $(SUBDIRS); do make -C $$d everything; [ $$? = 0 ] || exit 1; done
