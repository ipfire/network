
NAME = network
VER  = 003

DESTDIR=

prefix=/usr
bindir=$(prefix)/bin
sbindir=$(prefix)/sbin
libdir=$(prefix)/lib
sysconfdir=/etc
localstatedir=/var

# File to store the version number in.
VERSION_FILE = $(DESTDIR)$(libdir)/network/version

all:
	@echo "Nothing to do here."

install:
	-mkdir -pv $(DESTDIR)$(sysconfdir)/{network/{ports,zones},ppp}
	-mkdir -pv $(DESTDIR)$(libdir)/{network,sysctl.d,udev}
	-mkdir -pv $(DESTDIR)$(localstatedir)/log/network
	-mkdir -pv $(DESTDIR)$(sbindir)

	install -m 755 -v network $(DESTDIR)$(sbindir)

	cp -rfv {hooks,header*,functions*} $(DESTDIR)$(libdir)/network/
	cp -fv  sysctl.d/* $(DESTDIR)$(libdir)/sysctl.d/
	cp -rfv udev/* $(DESTDIR)$(libdir)/udev
	cp -rfv network-* $(DESTDIR)$(libdir)/network/

	# Install bridge-stp. 
	install -m 755 bridge-stp $(DESTDIR)$(sbindir)/

	install -m 755 -v ppp/ip-updown $(DESTDIR)$(sysconfdir)/ppp
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-pre-up
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-up
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-down
	ln -svf ip-updown ${DESTDIR}$(sysconfdir)/ppp/ipv6-up
	ln -svf ip-updown ${DESTDIR}$(sysconfdir)/ppp/ipv6-down
	install -m 755 -v ppp/dialer $(DESTDIR)$(sysconfdir)/ppp

	# Create the version file.
	: > ${VERSION_FILE}
	echo "# This file is automatically generated." >> ${VERSION_FILE}
	echo "NETWORK_VERSION=$(VER)" >> ${VERSION_FILE}

dist:
	git archive --format tar --prefix $(NAME)-$(VER)/ HEAD | gzip -9 > \
		$(NAME)-$(VER).tar.gz
