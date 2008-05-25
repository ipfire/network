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

SUBDIRS = src po

all: subdirs

lang-names: lang-table
	PYTHONPATH="./src/:." LANG=en_US.UTF-8 \
		python scripts/getlangnames.py > lang-names.tmp
	mv lang-names.tmp lang-names

install: all
	@if [ "$(DESTDIR)" = "" ]; then \
		echo " "; \
		echo "ERROR: A destdir is required"; \
		exit 1; \
	fi
	for d in $(SUBDIRS); do \
		make DESTDIR=`cd $(DESTDIR); pwd` -C $$d install; \
		[ $$? = 0 ] || exit 1; \
	done

clean:
	for d in $(SUBDIRS); do make -C $$d clean; done
	rm -rf lang-names{,.tmp}

subdirs:
	for d in $(SUBDIRS); do make -C $$d; [ $$? = 0 ] || exit 1; done
