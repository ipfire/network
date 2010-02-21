
PROGS = console_check securetty

CFLAGS += -D_GNU_SOURCE

all: $(PROGS)

clean:
	rm -vf $(PROGS) *.o

install:
	-mkdir -pv $(DESTDIR)/lib/udev $(DESTDIR)/sbin
	install -v -m 755 console_check $(DESTDIR)/lib/udev/
	install -v -m 755 securetty $(DESTDIR)/sbin


console_check: console_check.o
	$(CC) $(LDFLAGS) -o $@ $<

securetty: securetty.o
	$(CC) $(LDFLAGS) -o $@ $<
