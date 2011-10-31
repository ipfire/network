
NAME = network
VER  = 003

DESTDIR=

# File to store the version number in.
VERSION_FILE = $(DESTDIR)/lib/network/version

all:
	@echo "Nothing to do here."

install:
	-mkdir -pv $(DESTDIR)/etc/{network,ppp}
	-mkdir -pv $(DESTDIR)/lib/{network,sysctl.d,udev}
	-mkdir -pv $(DESTDIR)/sbin
	-mkdir -pv $(DESTDIR)/var/log/network

	install -m 755 -v network $(DESTDIR)/sbin

	cp -rfv {hooks,header*,functions*} $(DESTDIR)/lib/network/
	cp -fv  sysctl.d/* $(DESTDIR)/lib/sysctl.d/
	cp -rfv udev/* $(DESTDIR)/lib/udev
	cp -rfv network-* $(DESTDIR)/lib/network/

	install -m 755 -v ppp/ip-updown $(DESTDIR)/etc/ppp
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-pre-up
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-up
	ln -svf ip-updown $(DESTDIR)/etc/ppp/ip-down
	ln -svf ip-updown ${DESTDIR}/etc/ppp/ipv6-up
	ln -svf ip-updown ${DESTDIR}/etc/ppp/ipv6-down
	install -m 755 -v ppp/dialer $(DESTDIR)/etc/ppp

	# Create the version file.
	: > ${VERSION_FILE}
	echo "# This file is automatically generated." >> ${VERSION_FILE}
	echo "NETWORK_VERSION=$(VER)" >> ${VERSION_FILE}

dist:
	git archive --format tar --prefix $(NAME)-$(VER)/ HEAD | gzip -9 > \
		$(NAME)-$(VER).tar.gz
