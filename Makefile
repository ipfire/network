
include Makeconfig

DESTDIR=

prefix=/usr
bindir=$(prefix)/bin
sbindir=$(prefix)/sbin
libdir=$(prefix)/lib
sysconfdir=/etc
localstatedir=/var
systemdunitdir=$(prefix)/lib/systemd/system
tmpfilesdir=$(prefix)/lib/tmpfiles.d

# File to store the version number in.
VERSION_FILE = $(DESTDIR)$(libdir)/network/version

.PHONY: all
all:
	make -C man all

.PHONY: install
install:
	-mkdir -pv $(DESTDIR)$(sysconfdir)/{network/{ports,zones},ppp}
	-mkdir -pv $(DESTDIR)$(libdir)/{network,sysctl.d,udev}
	-mkdir -pv $(DESTDIR)$(localstatedir)/log/network
	-mkdir -pv $(DESTDIR)$(sbindir)
	-mkdir -pv $(DESTDIR)$(systemdunitdir)
	-mkdir -pv $(DESTDIR)$(tmpfilesdir)

	install -m 755 -v firewall $(DESTDIR)$(sbindir)
	install -m 755 -v network $(DESTDIR)$(sbindir)

	cp -rfv {hooks,header*,functions*} $(DESTDIR)$(libdir)/network/
	cp -fv  sysctl.d/* $(DESTDIR)$(libdir)/sysctl.d/
	cp -rfv udev/* $(DESTDIR)$(libdir)/udev
	cp -rfv network-* $(DESTDIR)$(libdir)/network/
	cp -vf  systemd/*.service $(DESTDIR)$(systemdunitdir)
	cp -vf network.tmpfiles $(DESTDIR)$(tmpfilesdir)/network.conf

	# Install the helper tools.
	-mkdir -pv $(DESTDIR)$(libdir)/network/helpers
	cp -vf helpers/* $(DESTDIR)$(libdir)/network/helpers

	# Install bridge-stp. 
	install -m 755 bridge-stp $(DESTDIR)$(sbindir)/

	# Install dhclient script and helper.
	install -m 755 dhclient-helper $(DESTDIR)$(libdir)/network/
	install -m 755 dhclient-script $(DESTDIR)$(sbindir)/

	install -m 755 -v ppp/ip-updown $(DESTDIR)$(sysconfdir)/ppp
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-pre-up
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-up
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ip-down
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ipv6-up
	ln -svf ip-updown $(DESTDIR)$(sysconfdir)/ppp/ipv6-down
	install -m 755 -v ppp/dialer $(DESTDIR)$(libdir)/network/

	# Install pppoe-server wrapper.
	install -m 755 ppp/pppoe-server $(DESTDIR)$(libdir)/network/

	# Create the version file.
	: > $(VERSION_FILE)
	echo "# This file is automatically generated." >> $(VERSION_FILE)
	echo "NETWORK_VERSION=$(PACKAGE_VERSION)" >> $(VERSION_FILE)

	# Descend into subdirectories.
	make -C man install

dist:
	git archive --format tar --prefix $(PACKAGE_NAME)-$(PACKAGE_VERSION)/ HEAD | gzip -9 > \
		$(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz
