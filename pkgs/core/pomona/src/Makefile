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

all: subdirs

install: all
	rm -rf $(PYTHONLIBDIR)
	-mkdir -p $(PYTHONLIBDIR)
	[ -d "$(PYTHONLIBDIR)" ]
	for d in $(SUBDIRS); do \
		make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; \
		[ $$? = 0 ] || exit 1; \
	done
	cp -avf *.py storage lang-table $(PYTHONLIBDIR)
	#sed -e "s/VERSION/$(VERSION)/g" \
	#	-e "s/SNAME/$(SNAME)/g" \
	#	-e "s/NAME/$(NAME)/g" \
	#	-i $(PYTHONLIBDIR)/constants.py
	-mkdir -p $(DESTDIR)/sbin
	install -m 755 pomona $(DESTDIR)/sbin/pomona

test:
	./runpychecker.sh

clean:
	rm -vf *.o *.so *.pyc *.pyo
	for d in $(SUBDIRS); do make -C $$d clean; done

subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done
