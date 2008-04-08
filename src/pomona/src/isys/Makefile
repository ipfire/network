include ../../Makefile.inc

CFLAGS +=  -I$(PYTHONINCLUDE) -I..

OBJECTS = imount.o smp.o cpio.o uncpio.o \
          lang.o isofs.o vio.o eddsupport.o str.o

SOBJECTS = $(patsubst %.o,%.lo,$(OBJECTS))
SOURCES = $(patsubst %.o,%.c,$(OBJECTS)) isys.c
LOADLIBES = -lpci -lpopt -lext2fs -lz -lkudzu -lpci
PYMODULES = _isys.so

ifeq (.depend,$(wildcard .depend))
TARGET=all
else
TARGET=depend all
endif

everything: $(TARGET)

all: $(PYMODULES) libisys.a

%.lo: %.c
	$(CC) -c $(CFLAGS) -fPIC -o $@ $<

_isys.so: isys.lo $(SOBJECTS)
	gcc -shared -g -fPIC -o $@ isys.lo $(SOBJECTS) $(LOADLIBES) $(LDFLAGS)

libisys.a: libisys.a($(OBJECTS))

filtertest: filtertest.o libisys.a

clean:
	rm -f *.o *.so *.lo *.a *.pyc $(TARGET) $(SOBJECTS)
	rm -f $(OBJECTS)
	rm -f .depend

install: all
	install -s $(PYMODULES) $(PYTHONLIBDIR)
	install -m 644 isys.py $(PYTHONLIBDIR)

depend:
	$(CPP) -M $(CFLAGS) $(SOURCES) > .depend

ifeq (.depend,$(wildcard .depend))
include .depend
endif
