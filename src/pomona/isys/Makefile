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

CFLAGS +=  -I$(PYTHONINCLUDE) -I/usr/include -I.. -I.

OBJECTS = devices.o imount.o smp.o linkdetect.o \
	lang.o isofs.o vio.o eddsupport.o str.o \
	wireless.o ethtool.o

SOBJECTS = $(patsubst %.o,%.lo,$(OBJECTS))
SOURCES = $(patsubst %.o,%.c,$(OBJECTS)) isys.c
LOADLIBES = -lpci -lpopt -lext2fs -lz -lpci -lblkid
PYMODULES = _isys.so

all: depend $(PYMODULES) libisys.a

%.lo: %.c
	$(CC) -c $(CFLAGS) -fPIC -o $@ $<

_isys.so: isys.lo $(SOBJECTS)
	$(CC) -shared -g -fPIC -o $@ isys.lo $(SOBJECTS) $(LOADLIBES) $(LDFLAGS)

libisys.a: libisys.a($(OBJECTS))

filtertest: filtertest.o libisys.a

clean:
	rm -f *.o *.so *.lo *.a *.pyc $(TARGET) $(SOBJECTS)
	rm -f $(OBJECTS)
	rm -f depend

install: all
	install -s $(PYMODULES) $(PYTHONLIBDIR)
	install -m 644 isys.py $(PYTHONLIBDIR)

depend:
	$(CPP) -M $(CFLAGS) $(SOURCES) > depend

ifeq (depend,$(wildcard depend))
include depend
endif
