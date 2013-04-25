###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2012-2013 IPFire Network Development Team                     #
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

PACKAGE_NAME    = network
PACKAGE_VERSION = 006

DESTDIR=

# Export HTML documents to this directory.
HTML_DOCS_DIR = html

prefix=/usr
bindir=$(prefix)/bin
sbindir=$(prefix)/sbin
libdir=$(prefix)/lib
datadir=$(prefix)/share
mandir=$(datadir)/man
sysconfdir=/etc
localstatedir=/var
systemdunitdir=$(prefix)/lib/systemd/system
tmpfilesdir=$(prefix)/lib/tmpfiles.d

# File to store the version number in.
VERSION_FILE = $(DESTDIR)$(libdir)/network/version

# A list of files which should be removed on "make clean"
CLEANFILES =

# man pages
MAN_PAGES = \
	man/network.8 \
	man/network-config.8 \
	man/network-device.8 \
	man/network-dns-server.8 \
	man/network-port-batman-adv.8 \
	man/network-port-batman-adv-port.8 \
	man/network-route.8 \
	man/network-zone.8 \
	man/network-zone-6to4-tunnel.8 \
	man/network-zone-aiccu.8 \
	man/network-zone-bridge.8 \
	man/network-zone-config-pppoe-server.8 \
	man/network-zone-pppoe.8

MAN_PAGES_HTML = $(patsubst %.xml,%.html,$(MAN_PAGES_XML))
MAN_PAGES_XML  = $(patsubst %.8,%.xml,$(MAN_PAGES))
MAN_PAGES_8    = $(filter %.8,$(MAN_PAGES))

CLEANFILES += \
	$(MAN_PAGES) \
	$(MAN_PAGES_HTML)

XSLTPROC = xsltproc

XSLTPROC_FLAGS = \
	--nonet \
	--stringparam man.output.quietly 1 \
	--stringparam funcsynopsis.style ansi \
	--stringparam man.th.extra1.suppress 1 \
	--stringparam man.authors.section.enabled 1 \
	--stringparam man.copyright.section.enabled 1

XSLTPROC_COMMAND_MAN = \
	$(XSLTPROC) -o $@ $(XSLTPROC_FLAGS) \
		http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl $<

XSLTPROC_COMMAND_HTML = \
	$(XSLTPROC) -o $@ $(XSLTPROC_FLAGS) man/custom-html.xsl $<

man/%.8: man/%.xml
	$(XSLTPROC_COMMAND_MAN)

man/%.html: man/%.xml man/custom-html.xsl
	$(XSLTPROC_COMMAND_HTML)

.PHONY: all
all: $(MAN_PAGES)

.PHONY: install
install: $(MAN_PAGES)
	-mkdir -pv $(DESTDIR)$(sysconfdir)/{network/{ports,zones},ppp}
	-mkdir -pv $(DESTDIR)$(libdir)/{network,sysctl.d,udev}
	-mkdir -pv $(DESTDIR)$(localstatedir)/log/network
	-mkdir -pv $(DESTDIR)$(sbindir)
	-mkdir -pv $(DESTDIR)$(systemdunitdir)
	-mkdir -pv $(DESTDIR)$(tmpfilesdir)
	-mkdir -pv $(DESTDIR)$(datadir)/firewall

	install -m 755 -v firewall6 $(DESTDIR)$(sbindir)
	install -m 755 -v firewall4 $(DESTDIR)$(sbindir)
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
	ln -svf --relative \
		$(DESTDIR)$(libdir)/network/helpers/bridge-stp \
		$(DESTDIR)$(sbindir)/

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

	# Install the firewall macros.
	cp -av macros $(DESTDIR)$(datadir)/firewall/

	# Create the version file.
	: > $(VERSION_FILE)
	echo "# This file is automatically generated." >> $(VERSION_FILE)
	echo "NETWORK_VERSION=$(PACKAGE_VERSION)" >> $(VERSION_FILE)

	# Install man pages.
	-mkdir -pv $(DESTDIR)$(mandir)/man8
	install -v -m 644 $(MAN_PAGES_8) $(DESTDIR)$(mandir)/man8

.PHONY: clean
clean:
	rm -f $(CLEANFILES)

dist:
	git archive --format tar --prefix $(PACKAGE_NAME)-$(PACKAGE_VERSION)/ HEAD | gzip -9 > \
		$(PACKAGE_NAME)-$(PACKAGE_VERSION).tar.gz

.PHONY: export-html-docs
export-html-docs: $(MAN_PAGES_HTML)
	mkdir -pv $(HTML_DOCS_DIR)
	cp -vf $^ $(HTML_DOCS_DIR)
