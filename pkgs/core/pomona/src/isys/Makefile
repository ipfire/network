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

OBJECTS = isys.o mount.o

CFLAGS += -I$(PYTHONINCLUDE)
LDFLAGS =
LIBS =

all: depend _isys.so

depend: $(patsubst %.o,%.c,$(OBJECTS))
	$(CPP) -M $(CFLAGS) $(patsubst %.o,%.c,$(OBJECTS)) > depend

%.o: %.c
	$(CC) -c $(CFLAGS) -o $@ $<

_isys.so: $(OBJECTS)
	$(CC) -shared $(CFLAGS) $(LDFLAGS) $(LIBS) -o $@ $(OBJECTS)

install: _isys.so isys.py
	cp -vf _isys.so isys.py $(PYTHONLIBDIR)

clean:
	rm -vf $(OBJECTS) depend _isys.so *.py[co]

test: _isys.so
	python -c "import isys"

ifeq (depend,$(wildcard depend))
include depend
endif
