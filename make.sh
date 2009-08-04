#!/bin/bash
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2007, 2008, 2009 Michael Tremer & Christian Schmidt           #
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
#

NAME="IPFire"			# Software name
SNAME="ipfire"			# Short name
VERSION="3.0-prealpha2"		# Version number
TOOLCHAINVERSION="${VERSION}-12"	# Toolchain
SLOGAN="Gluttony"		# Software slogan

# Include funtions
. tools/make-include


################################################################################
# This builds the entire stage "toolchain"                                     #
################################################################################
toolchain_build() {

	ORG_PATH=$PATH
	export PATH=${TOOLS_DIR}/usr/bin:${TOOLS_DIR}/usr/sbin:${TOOLS_DIR}/bin:${TOOLS_DIR}/sbin:$PATH
	STAGE_ORDER=01
	STAGE=toolchain

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-toolchain.log"
	export LOGFILE

	build_spy stage ${STAGE}

	# We can't skip packages in toolchain stage
	SAVE_SKIP_PACKAGE_LIST=$SKIP_PACKAGE_LIST
	SKIP_PACKAGE_LIST=

	icecc_disable

	toolchain_make stage1
	toolchain_make ccache
	toolchain_make binutils		PASS=1
	toolchain_make gcc		PASS=1
	toolchain_make linux-headers
	toolchain_make glibc
	toolchain_make adjust-toolchain
	toolchain_make test-toolchain	PASS=1
	toolchain_make zlib
	toolchain_make gcc		PASS=2
	toolchain_make binutils		PASS=2
	toolchain_make test-toolchain	PASS=2
	toolchain_make ncurses
	toolchain_make attr
	toolchain_make acl
	toolchain_make bash
	toolchain_make bzip2
	toolchain_make coreutils
	toolchain_make cpio
	toolchain_make diffutils
	toolchain_make e2fsprogs
	toolchain_make icecc
	icecc_enable
	icecc_use toolchain		# Use the fresh gcc
	toolchain_make file
	toolchain_make findutils
	toolchain_make gawk
	toolchain_make gettext
	toolchain_make grep
	toolchain_make gzip
	toolchain_make m4
	toolchain_make make
	toolchain_make patch
	toolchain_make pax-utils
	toolchain_make perl
	toolchain_make sed
	toolchain_make tar
	toolchain_make texinfo
	toolchain_make flex
	toolchain_make bc
	toolchain_make xz
	toolchain_make autoconf
	toolchain_make automake
	toolchain_make strip

	export PATH=$ORG_PATH SKIP_PACKAGE_LIST=$SAVE_SKIP_PACKAGE_LIST
	unset SAVE_SKIP_PACKAGE_LIST
}

################################################################################
# This builds the entire stage "base"                                          #
################################################################################
base_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:$TOOLS_DIR/bin
	STAGE_ORDER=02
	STAGE=base

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-base.log"
	export LOGFILE

	build_spy stage ${STAGE}

	# Start distributed compiling with toolchain
	iceccd_start
	icecc_use toolchain

	ipfire_make stage2
	ipfire_make scripts
	ipfire_make system-release
	ipfire_make linux-headers
	ipfire_make man-pages
	ipfire_make glibc
	ipfire_make adjust-toolchain
	ipfire_make test-toolchain
	ipfire_make zlib
	ipfire_make binutils
	ipfire_make gcc

	# Change to self-built gcc
	icecc_use base

	ipfire_make make
	ipfire_make libtool
	ipfire_make gettext
	ipfire_make pkg-config
	ipfire_make berkeley
	ipfire_make sed
	ipfire_make iana-etc
	ipfire_make m4
	ipfire_make bison
	ipfire_make flex
	ipfire_make ncurses
	ipfire_make shadow
	ipfire_make cracklib
	ipfire_make pam
	ipfire_make attr
	ipfire_make acl
	ipfire_make libcap2
	ipfire_make util-linux-ng
	ipfire_make e2fsprogs
	ipfire_make coreutils
	ipfire_make procps
	ipfire_make perl
	ipfire_make readline
	ipfire_make libidn
	ipfire_make bzip2
	ipfire_make pcre
	ipfire_make paxctl
	ipfire_make autoconf
	ipfire_make automake
	ipfire_make bash
	ipfire_make cpio
	ipfire_make diffutils
	ipfire_make eventlog
	ipfire_make file
	ipfire_make findutils
	ipfire_make gmp
	ipfire_make grub
	ipfire_make gawk
	ipfire_make glib2
	ipfire_make grep
	ipfire_make groff
	ipfire_make gzip
	ipfire_make iputils
	ipfire_make iproute2
	ipfire_make kbd
	ipfire_make less
	ipfire_make man-db
	ipfire_make module-init-tools
	ipfire_make mpfr
	ipfire_make patch
	ipfire_make pax-utils
	ipfire_make psmisc
	ipfire_make syslog-ng
	ipfire_make sysvinit
	ipfire_make tar
	ipfire_make texinfo
	ipfire_make vim
}

################################################################################
# This builds the entire stage "ipfire"                                        #
################################################################################
ipfire_build() {
	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=03
	STAGE=ipfire

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-ipfire.log"
	export LOGFILE

	build_spy stage ${STAGE}

	### Building the configuration dirs and files
	#
	ipfire_make stage3
	ipfire_make xz

	ipfire_make linux

	### Building some general stuff
	#   STAGE 1
	ipfire_make libdaemon
	ipfire_make expat
	ipfire_make dbus
	ipfire_make dbus-glib
	ipfire_make upstart
	ipfire_make initscripts
	ipfire_make openssl
	ipfire_make perl-xml-parser
	ipfire_make intltool
	ipfire_make python
	ipfire_make python-cracklib
	ipfire_make python-dbus
	ipfire_make python-urlgrabber
	ipfire_make python-IPy
	ipfire_make libxml2
	ipfire_make libxslt
	ipfire_make popt
	ipfire_make libusb
	ipfire_make libusb-compat	# Can be removed if usbutils supports libusb-1.0
	ipfire_make bc
	ipfire_make boost
	ipfire_make lua
	
	### Building some network stuff
	#
	ipfire_make libpcap
	ipfire_make linux-atm
	ipfire_make ppp
	ipfire_make rp-pppoe
	ipfire_make pptp
	ipfire_make dhcp
	ipfire_make iptables
	ipfire_make libnfnetlink
	ipfire_make libnetfilter_queue
	ipfire_make libnetfilter_conntrack
	ipfire_make libnetfilter_log
	ipfire_make python-netfilter_conntrack
	ipfire_make l7-protocols
	ipfire_make bridge-utils
	ipfire_make vlan
	ipfire_make bind
	ipfire_make whois
	ipfire_make avahi
	ipfire_make libssh2
	ipfire_make libdnet
	#ipfire_make rstp
	ipfire_make ebtables
	ipfire_make openlldp
	
	### Building some general stuff
	#   STAGE 2
	ipfire_make pth
	ipfire_make libassuan
	ipfire_make libgpg-error
	ipfire_make libgcrypt
	ipfire_make gnutls
	ipfire_make libksba
	ipfire_make slang
	ipfire_make newt
	ipfire_make cyrus-sasl
	ipfire_make openldap
	ipfire_make pam_ldap
	ipfire_make nss_ldap
	ipfire_make ldapvi
	ipfire_make sqlite
	ipfire_make python-sqlite2
	ipfire_make curl
	ipfire_make pinentry
	ipfire_make gnupg2
	ipfire_make sudo
	ipfire_make libjpeg
	ipfire_make libpng
	ipfire_make libtiff
	ipfire_make libart
	ipfire_make freetype
	ipfire_make fontconfig
	ipfire_make pixman
	ipfire_make cairo
	ipfire_make pango
	ipfire_make lzo
	ipfire_make lsof
	ipfire_make br2684ctl
	ipfire_make etherwake
	ipfire_make beep
	ipfire_make libuser
	ipfire_make passwd
	ipfire_make directfb
	ipfire_make pdns
	ipfire_make pdns-recursor
	ipfire_make libevent
	ipfire_make libnfsidmap
	ipfire_make libgssglue
	ipfire_make librpcsecgss
	ipfire_make gperf
	
	### Building vpn stuff
	#
	ipfire_make strongswan
	ipfire_make openvpn
	
	### Building filesystem stuff
	#
	ipfire_make btrfs-progs
	ipfire_make reiserfsprogs
	ipfire_make libaal
	ipfire_make reiser4progs
	ipfire_make xfsprogs
	ipfire_make sysfsutils
	ipfire_make squashfs-tools
	ipfire_make dosfstools
	ipfire_make lvm2
	ipfire_make mdadm
	ipfire_make dmraid
	ipfire_make cryptsetup-luks
	ipfire_make python-cryptsetup
	ipfire_make fuse

	### Building hardware utils
	#
	ipfire_make pciutils
	ipfire_make usbutils
	ipfire_make hdparm
	ipfire_make smartmontools
	ipfire_make lm-sensors
	ipfire_make parted
	ipfire_make hal
	ipfire_make hal-info
	ipfire_make udev

	### Building some important tools
	#
	ipfire_make ulogd2
	ipfire_make fcron
	ipfire_make which
	ipfire_make screen
	ipfire_make rrdtool
	ipfire_make ntp
	ipfire_make openssh
	ipfire_make ez-ipupdate
	ipfire_make noip
	ipfire_make lighttpd
	ipfire_make webinterface
	ipfire_make collectd
	ipfire_make logrotate
	#ipfire_make logwatch
	ipfire_make dvdrtools
	ipfire_make python-parted
	ipfire_make python-pyblock
	ipfire_make libbdevid
	ipfire_make memtest86+
	ipfire_make quagga
	#ipfire_make mISDN
	ipfire_make wireless-tools

	ipfire_make pyfire
	ipfire_make network
	ipfire_make firewall
	ipfire_make pakfire
}

################################################################################
# This builds the entire stage "misc"                                          #
################################################################################
misc_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=04
	STAGE=misc

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-misc.log"
	export LOGFILE

	build_spy stage ${STAGE}

	ipfire_make stage4

	ipfire_make miniupnpd

	### Console tools
	#
	ipfire_make mc
	ipfire_make traceroute
	ipfire_make nmap
	#ipfire_make rsync
	ipfire_make tcpdump
	ipfire_make htop
	ipfire_make nano

	### Servers
	#
	ipfire_make squid
	ipfire_make samba

	### Assembler
	#
	ipfire_make nasm
	ipfire_make syslinux

	ipfire_make mkinitramfs
	ipfire_make splashy

	ipfire_make vsftpd

	## NTFS
	#ipfire_make ntfs-3g
	#
	## Net tools
	#ipfire_make bwm-ng

	### These will become addons as usual but will be integrated later
	#
	#ipfire_make snort
	#ipfire_make oinkmaster
	#ipfire_make cups
	#ipfire_make ghostscript
	#ipfire_make foomatic
	#ipfire_make hplip
	#ipfire_make postfix
	#ipfire_make fetchmail
	#ipfire_make cyrus-imapd
	#ipfire_make clamav
	#ipfire_make alsa
	#ipfire_make mpfire
	#ipfire_make guardian
	#ipfire_make ipfireseeder
	ipfire_make portmap
	ipfire_make nfs-utils

	### Debugging
	#
	ipfire_make paxtest
	ipfire_make gdb
	ipfire_make strace
	ipfire_make pychecker

	### Virtualization
	#
	ipfire_make xen
	ipfire_make qemu
	ipfire_make libvirt
}

################################################################################
# This builds the entire stage "installer"                                     #
################################################################################
installer_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=05
	STAGE=installer

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-installer.log"
	export LOGFILE

	build_spy stage ${STAGE}

	ipfire_make stage5
	ipfire_make pomona
}

################################################################################
# This builds the entire stage "packages"                                      #
################################################################################
packages_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=06
	STAGE=packages

	LOGFILE="$BASEDIR/log_${TARGET}/_build.${STAGE_ORDER}-packages.log"
	export LOGFILE

	build_spy stage ${STAGE}

	# Generate ChangeLog
	git_log

	# Generate packages list
	echo -n "Generating packages list"
	pkg_list_packages > $BASEDIR/doc/packages-list.txt
	beautify message DONE

	if [ ${EMB} -eq 0 ]; then
		ipfire_make images-core
		ipfire_make images-info
		ipfire_make images-initramfs
		ipfire_make images-overlays
		ipfire_make pxe
		ipfire_make cdrom

		if check_loop; then
			: #ipfire_make usb-key
		else
			echo -n "Can't build usb-key images on this machine"
			beautify message WARN
		fi
		mv $LFS/$IMAGES_DIR/{*.iso,*.tar.gz,*.img.gz} $BASEDIR >>$LOGFILE 2>&1
	else
		if check_loop; then
			# We put here the code that is done when
			# we do an embedded build
			:
		fi
	fi

	# Cleanup
	stdumount
	rm -rf $LFS/tmp/*

	cd $PWD
}

# See what we're supposed to do
. $BASEDIR/tools/make-interactive
