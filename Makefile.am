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

ACLOCAL_AMFLAGS = -I m4 ${ACLOCAL_FLAGS}
AM_MAKEFLAGS = --no-print-directory
AUTOMAKE_OPTIONS = color-tests

# remove target it the command fails
.DELETE_ON_ERROR:

# keep itermediate files
.SECONDARY:

bashcompletiondir= $(datadir)/bash-completion/completions
libexecdir       = $(prefix)/lib
pkgconfigdatadir = $(datadir)/pkgconfig
pppdir           = $(sysconfdir)/ppp
systemconfigdir  = $(datadir)/network
sysctldir        = $(prefix)/lib/sysctl.d
tmpfilesdir      = $(prefix)/lib/tmpfiles.d
udevrulesdir     = $(udevdir)/rules.d

networkdir       = $(libexecdir)/network
helpersdir       = $(networkdir)/helpers

macrosdir        = $(libexecdir)/firewall/macros

hooksdir         = $(networkdir)/hooks
hooks_configsdir = $(hooksdir)/configs
hooks_portsdir   = $(hooksdir)/ports
hooks_zonesdir   = $(hooksdir)/zones

triggersdir      = $(networkdir)/triggers

logdir           = $(localestatedir)/log/network

CLEANFILES =
DISTCLEANFILES =
EXTRA_DIST =
INSTALL_DIRS =
INSTALL_EXEC_HOOKS =
UNINSTALL_EXEC_HOOKS =
noinst_DATA =

AM_CFLAGS       = $(OUR_CFLAGS)
AM_CPPFLAGS     = $(OUR_CPPFLAGS)
AM_LDFLAGS      = $(OUR_LDFLAGS)

DISTCHECK_CONFIGURE_FLAGS = \
	--with-systemdsystemunitdir=$$dc_install_base/$(systemdsystemunitdir) \
	--with-udevdir=$$dc_install_base/$(udevdir)

install-directories-hook:
	$(MKDIR_P) $(addprefix $(DESTDIR),$(INSTALL_DIRS))

INSTALL_EXEC_HOOKS += \
	install-directories-hook

# ------------------------------------------------------------------------------

AM_V_XSLT   = $(AM_V_XSLT_$(V))
AM_V_XSLT_  = $(AM_V_XSLT_$(AM_DEFAULT_VERBOSITY))
AM_V_XSLT_0 = @echo "  XSLT    " $@;

# ------------------------------------------------------------------------------

dist_doc_DATA = \
	README \
	docs/CODING_STYLE \
	docs/COPYING

dist_sbin_SCRIPTS = \
	src/dhclient-script \
	src/firewall-config \
	src/firewall4 \
	src/firewall6 \
	src/network

network_SCRIPTS = \
	src/functions/functions

CLEANFILES += \
	src/functions/functions

EXTRA_DIST += \
	src/functions/functions.in

dist_network_SCRIPTS = \
	src/functions/functions.at \
	src/functions/functions.auth \
	src/functions/functions.batman-adv \
	src/functions/functions.bonding \
	src/functions/functions.bridge \
	src/functions/functions.cli \
	src/functions/functions.cli.firewall \
	src/functions/functions.colors \
	src/functions/functions.config \
	src/functions/functions.conntrack \
	src/functions/functions.constants \
	src/functions/functions.constants-firewall \
	src/functions/functions.db \
	src/functions/functions.description \
	src/functions/functions.device \
	src/functions/functions.dhclient \
	src/functions/functions.dhcpd \
	src/functions/functions.distro \
	src/functions/functions.dns \
	src/functions/functions.dummy \
	src/functions/functions.editor \
	src/functions/functions.firewall \
	src/functions/functions.firewall-policy \
	src/functions/functions.firewall-zones \
	src/functions/functions.he \
	src/functions/functions.hook \
	src/functions/functions.hostapd \
	src/functions/functions.hotplug \
	src/functions/functions.http \
	src/functions/functions.interrupts \
	src/functions/functions.ip \
	src/functions/functions.ipsec \
	src/functions/functions.iptables \
	src/functions/functions.ip-tunnel \
	src/functions/functions.ipv4 \
	src/functions/functions.ipv6 \
	src/functions/functions.list \
	src/functions/functions.lock \
	src/functions/functions.logging \
	src/functions/functions.macros \
	src/functions/functions.modem \
	src/functions/functions.phy \
	src/functions/functions.ports \
	src/functions/functions.ppp \
	src/functions/functions.pppoe-server \
	src/functions/functions.radvd \
	src/functions/functions.route \
	src/functions/functions.routing \
	src/functions/functions.serial \
	src/functions/functions.service \
	src/functions/functions.settings \
	src/functions/functions.stp \
	src/functions/functions.sysctl \
	src/functions/functions.system \
	src/functions/functions.triggers \
	src/functions/functions.usb \
	src/functions/functions.util \
	src/functions/functions.vlan \
	src/functions/functions.vpn \
	src/functions/functions.vpn-security-policies \
	src/functions/functions.wireless \
	src/functions/functions.wpa_supplicant \
	src/functions/functions.zone \
	src/network-radvd-config \
	src/dhclient-helper \
	src/header-config \
	src/header-port \
	src/header-zone \
	src/ppp/dialer \
	src/ppp/pppoe-server

dist_helpers_SCRIPTS = \
	src/helpers/bridge-stp \
	src/helpers/dhcpd-config-helper \
	src/helpers/firewall-kernel-init \
	src/helpers/hostapd-config-helper \
	src/helpers/ipsec-updown \
	src/helpers/pppd-angel \
	src/helpers/wpa_supplicant \
	src/helpers/wpa_supplicant-config-helper

bin_PROGRAMS = \
	src/inetcalc

src_inetcalc_SOURCES = \
	src/inetcalc.c

bridge-stp-install-hook: bridge-stp-uninstall-hook
	ln -svf --relative $(DESTDIR)$(helpersdir)/bridge-stp $(DESTDIR)$(sbindir)/

bridge-stp-uninstall-hook:
	rm -f $(DESTDIR)$(sbindir)/bridge-stp

INSTALL_EXEC_HOOKS += bridge-stp-install-hook
UNINSTALL_EXEC_HOOKS += bridge-stp-uninstall-hook

dist_hooks_configs_SCRIPTS = \
	src/hooks/configs/dhcp \
	src/hooks/configs/ipv4-static \
	src/hooks/configs/ipv6-auto \
	src/hooks/configs/ipv6-static \
	src/hooks/configs/pppoe-server

dist_hooks_ports_SCRIPTS = \
	src/hooks/ports/batman-adv \
	src/hooks/ports/bonding \
	src/hooks/ports/dummy \
	src/hooks/ports/ethernet \
	src/hooks/ports/vlan \
	src/hooks/ports/wireless-adhoc \
	src/hooks/ports/wireless-ap

dist_hooks_zones_SCRIPTS = \
	src/hooks/zones/6to4-tunnel \
	src/hooks/zones/bridge \
	src/hooks/zones/modem \
	src/hooks/zones/pppoe \
	src/hooks/zones/wireless

# ------------------------------------------------------------------------------

ppp_SCRIPTS = \
	src/ppp/ip-updown

CLEANFILES += \
	src/ppp/ip-updown

EXTRA_DIST += \
	src/ppp/ip-updown.in

INSTALL_DIRS += \
	$(pppdir) \
	$(logdir)

ppp-install-hook:
	ln -svf ip-updown $(DESTDIR)$(pppdir)/ip-pre-up
	ln -svf ip-updown $(DESTDIR)$(pppdir)/ip-up
	ln -svf ip-updown $(DESTDIR)$(pppdir)/ip-down
	ln -svf ip-updown $(DESTDIR)$(pppdir)/ipv6-up
	ln -svf ip-updown $(DESTDIR)$(pppdir)/ipv6-down

ppp-uninstall-hook:
	rm -f $(DESTDIR)$(pppdir)/ip-{down,pre-up,up}
	rm -f $(DESTDIR)$(pppdir)/ipv6-{down,up}

INSTALL_EXEC_HOOKS += ppp-install-hook
UNINSTALL_EXEC_HOOKS += ppp-uninstall-hook

# ------------------------------------------------------------------------------

if HAVE_SYSTEMD
systemdsystemunit_DATA = \
	src/systemd/firewall4.service \
	src/systemd/firewall6.service \
	src/systemd/firewall-init.service \
	src/systemd/network-init.service \
	src/systemd/network@.service

CLEANFILES += \
	$(systemdsystemunit_DATA)

INSTALL_DIRS += \
	$(systemdsystemunitdir)
endif

EXTRA_DIST += \
	src/systemd/firewall4.service.in \
	src/systemd/firewall6.service.in \
	src/systemd/firewall-init.service.in \
	src/systemd/network-init.service.in \
	src/systemd/network@.service.in

# ------------------------------------------------------------------------------

systemconfig_vpndir = $(systemconfigdir)/vpn

dist_systemconfig_vpn_security_policies_DATA = \
	config/vpn/security-policies/performance \
	config/vpn/security-policies/system

systemconfig_vpn_security_policiesdir = $(systemconfig_vpndir)/security-policies

# ------------------------------------------------------------------------------

dist_sysctl_DATA = \
	src/sysctl/network.conf

# ------------------------------------------------------------------------------

dist_bashcompletion_SCRIPTS = \
	src/bash-completion/network

# ------------------------------------------------------------------------------

dist_tmpfiles_DATA = \
	src/tmpfiles/network.conf

# ------------------------------------------------------------------------------

if HAVE_UDEV
dist_udev_SCRIPTS = \
	src/udev/network-hotplug \
	src/udev/network-hotplug-rename \
	src/udev/network-hotplug-serial

dist_udevrules_DATA = \
	src/udev/rules.d/50-serial-whitelist.rules \
	src/udev/rules.d/60-net.rules

INSTALL_DIRS += \
	$(udevdir) \
	$(udevrulesdir)
endif

# ------------------------------------------------------------------------------

pkgconfigdata_DATA = \
	src/network.pc

CLEANFILES += \
	$(pkgconfigdata_DATA)

EXTRA_DIST += \
	src/network.pc.in

# ------------------------------------------------------------------------------

dist_macros_DATA = \
	src/macros/DHCP \
	src/macros/HTTP \
	src/macros/HTTPS \
	src/macros/WWW

# ------------------------------------------------------------------------------

INSTALL_DIRS += \
	$(triggersdir)

# ------------------------------------------------------------------------------

MANPAGES = \
	man/firewall-settings.8 \
	man/network.8 \
	man/network-color.8 \
	man/network-description.8 \
	man/network-device.8 \
	man/network-dhcp.8 \
	man/network-dns-server.8 \
	man/network-performance-tuning.8 \
	man/network-port.8 \
	man/network-port-batman-adv.8 \
	man/network-port-batman-adv-port.8 \
	man/network-quick-start.8 \
	man/network-route.8 \
	man/network-route-static.8 \
	man/network-settings.8 \
	man/network-zone.8 \
	man/network-zone-6to4-tunnel.8 \
	man/network-zone-bridge.8 \
	man/network-zone-config-pppoe-server.8 \
	man/network-zone-modem.8 \
	man/network-zone-pppoe.8 \
	man/network-zone-wireless.8

MANPAGES_XML  = $(patsubst %.8,%.xml,$(MANPAGES))
MANPAGES_HTML = $(patsubst %.xml,%.html,$(MANPAGES_XML))

.PHONY: man
man: $(MANPAGES) $(MANPAGES_HTML)

man_MANS = \
	$(MANPAGES)

noinst_DATA += \
	$(MANPAGES_HTML)

CLEANFILES += \
	$(man_MANS) \
	$(MANPAGES_HTML)

EXTRA_DIST += \
	$(MANPAGES_XML) \
	man/custom-html.xsl

XSLTPROC_FLAGS = \
	--nonet \
	--stringparam man.output.quietly 1 \
	--stringparam funcsynopsis.style ansi \
	--stringparam man.th.extra1.suppress 1 \
	--stringparam man.authors.section.enabled 1 \
	--stringparam man.copyright.section.enabled 1

XSLTPROC_COMMAND_MAN = \
	$(AM_V_XSLT)$(XSLTPROC) -o $@ $(XSLTPROC_FLAGS) \
		http://docbook.sourceforge.net/release/xsl/current/manpages/docbook.xsl $<

XSLTPROC_COMMAND_HTML = \
	$(AM_V_XSLT)$(XSLTPROC) -o $@ $(XSLTPROC_FLAGS) $(srcdir)/man/custom-html.xsl $<

man/%.8: man/%.xml
	$(XSLTPROC_COMMAND_MAN)

man/%.html: man/%.xml man/custom-html.xsl
	$(XSLTPROC_COMMAND_HTML)

# ------------------------------------------------------------------------------

substitutions = \
	'|PACKAGE_NAME=$(PACKAGE_NAME)|' \
	'|PACKAGE_URL=$(PACKAGE_URL)|' \
	'|PACKAGE_VERSION=$(PACKAGE_VERSION)|' \
	'|prefix=$(prefix)|' \
	'|exec_prefix=$(exec_prefix)|' \
	'|sbindir=$(sbindir)|' \
	'|networkdir=$(networkdir)|' \
	'|helpersdir=$(helpersdir)|'

SED_PROCESS = \
	$(AM_V_GEN)$(MKDIR_P) $(dir $@) && \
	$(SED) $(subst '|,-e 's|@,$(subst =,\@|,$(subst |',|g',$(substitutions)))) \
		< $< > $@

src/functions/functions: src/functions/functions.in Makefile
	$(SED_PROCESS)

src/ppp/ip-updown: src/ppp/ip-updown.in Makefile
	$(SED_PROCESS)

src/systemd/%: src/systemd/%.in Makefile
	$(SED_PROCESS)

src/%.pc: src/%.pc.in Makefile
	$(SED_PROCESS)

INSTALL_DIRS += \
	$(sbindir)

install-exec-hook: $(INSTALL_EXEC_HOOKS)

uninstall-hook: $(UNINSTALL_EXEC_HOOKS)

# - testsuite ------------------------------------------------------------------

TESTS_ENVIRONMENT = \
	PATH=$(top_builddir)/src:$(PATH) \
	functions=$(abs_builddir)/src/functions/functions \
	networkdir=$(abs_srcdir)/src/functions \
	testdir=$(top_srcdir)/test

dist_check_DATA = \
	test/constants.sh \
	test/test-functions

dist_check_SCRIPTS = \
	$(TESTS)

TESTS = \
	test/load-library \
	test/functions/ip/ip_detect_protocol \
	test/functions/ip/ip_get_prefix \
	test/functions/ip/ip_net_is_valid \
	test/functions/ip/ip_is_valid \
	test/functions/ip/ip_network_is_subnet_of \
	test/functions/ip/ip_prefix_is_valid \
	test/functions/ip/ip_protocol_is_supported \
	test/functions/ip/ip_split_prefix
