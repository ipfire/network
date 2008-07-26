#!/bin/bash
############################################################################
#                                                                          #
# This file is part of the IPFire Firewall.                                #
#                                                                          #
# IPFire is free software; you can redistribute it and/or modify           #
# it under the terms of the GNU General Public License as published by     #
# the Free Software Foundation; either version 2 of the License, or        #
# (at your option) any later version.                                      #
#                                                                          #
# IPFire is distributed in the hope that it will be useful,                #
# but WITHOUT ANY WARRANTY; without even the implied warranty of           #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the            #
# GNU General Public License for more details.                             #
#                                                                          #
# You should have received a copy of the GNU General Public License        #
# along with IPFire; if not, write to the Free Software                    #
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA #
#                                                                          #
# Copyright (C) 2008 IPFire-Team <info@ipfire.org>.                        #
#                                                                          #
############################################################################
#

NAME="IPFire"			# Software name
SNAME="ipfire"			# Short name
VERSION="3.0-prealpha"		# Version number
TOOLCHAINVERSION="${VERSION}-5"	# Toolchain
SLOGAN="www.ipfire.org"		# Software slogan

# Include funtions
. tools/make-include


################################################################################
# This builds the entire stage "toolchain"                                     #
################################################################################
toolchain_build() {

	ORG_PATH=$PATH
	export PATH=${TOOLS_DIR}/usr/bin:${TOOLS_DIR}/bin:$PATH
	STAGE_ORDER=01
	STAGE=toolchain

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-toolchain.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	toolchain_make stage1
	# make distcc first so that CCACHE_PREFIX works immediately
	[ -z "$DISTCC_HOSTS" ] || toolchain_make distcc
	toolchain_make ccache
	toolchain_make gmp
	toolchain_make mpfr
	toolchain_make linux
	toolchain_make binutils		PASS=1
	toolchain_make gcc		PASS=1
	toolchain_make glibc
	toolchain_make adjust-toolchain
	toolchain_make binutils		PASS=2
	toolchain_make gcc		PASS=2
	#toolchain_make tcl		# Maybe this can be dropped
	#toolchain_make expect		# Maybe this can be dropped
	#toolchain_make dejagnu		# Maybe this can be dropped
	toolchain_make ncurses
	toolchain_make bash
	toolchain_make bzip2
	toolchain_make coreutils
	toolchain_make diffutils
	toolchain_make e2fsprogs
	toolchain_make findutils
	toolchain_make gawk
	toolchain_make gettext
	toolchain_make grep
	toolchain_make gzip
	toolchain_make m4
	toolchain_make make
	toolchain_make patch
	toolchain_make perl
	toolchain_make sed
	toolchain_make tar
	toolchain_make texinfo
	#toolchain_make bison
	toolchain_make flex
	toolchain_make bc
	toolchain_make util-linux-ng
	toolchain_make strip
	export PATH=$ORG_PATH
}

################################################################################
# This builds the entire stage "base"                                          #
################################################################################
base_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:$TOOLS_DIR/bin
	STAGE_ORDER=02
	STAGE=base

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-base.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	ipfire_make stage2
	ipfire_make gmp
	ipfire_make mpfr
	ipfire_make linux
	ipfire_make man-pages
	ipfire_make glibc
	ipfire_make adjust-toolchain
	ipfire_make binutils
	ipfire_make gcc
	ipfire_make berkeley
	ipfire_make sed
	ipfire_make e2fsprogs
	ipfire_make coreutils
	ipfire_make iana-etc
	ipfire_make m4
	ipfire_make bison
	ipfire_make ncurses
	ipfire_make procps
	ipfire_make libtool
	ipfire_make perl
	ipfire_make readline
	ipfire_make zlib
	ipfire_make gettext
	ipfire_make make
	ipfire_make attr
	ipfire_make libcap2
	ipfire_make paxctl
	ipfire_make autoconf
	ipfire_make automake
	ipfire_make bash
	ipfire_make bzip2
	ipfire_make diffutils
	ipfire_make file
	ipfire_make findutils
	ipfire_make flex
	ipfire_make grub
	ipfire_make gawk
	ipfire_make grep
	ipfire_make groff
	ipfire_make gzip
	ipfire_make inetutils
	ipfire_make iproute2
	ipfire_make kbd
	ipfire_make less
	ipfire_make man-db
	ipfire_make module-init-tools
	ipfire_make patch
	ipfire_make psmisc
	ipfire_make shadow
	ipfire_make sysklogd
	ipfire_make sysvinit
	ipfire_make tar
	ipfire_make texinfo
	ipfire_make udev					## NEED TO INSTALL CONFIG
	ipfire_make util-linux-ng
	ipfire_make vim
}

################################################################################
# This builds the entire stage "ipfire"                                        #
################################################################################
ipfire_build() {
	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=03
	STAGE=ipfire

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-ipfire.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	### Building the configuration dirs and files
	#
	ipfire_make stage3
	ipfire_make lzma

	ipfire_make linux
	
	### Building some general stuff
	#   STAGE 1
	ipfire_make pkg-config
	ipfire_make expat
	ipfire_make glib
	ipfire_make dbus
	ipfire_make dbus-glib
	ipfire_make openssl
	ipfire_make perl			### We are building the modules here.
	ipfire_make python
	ipfire_make python-dbus
	ipfire_make python-urlgrabber
	ipfire_make python-iconv
	ipfire_make libxml2
	ipfire_make libxslt
	#ipfire_make libidn		### Do we need this?
	ipfire_make pcre
	ipfire_make popt
	ipfire_make libusb
	ipfire_make bc
	
	### Building some network stuff
	#
	ipfire_make libpcap
	ipfire_make linux-atm
	ipfire_make ppp
	ipfire_make rp-pppoe
	ipfire_make dhcp
	ipfire_make iptables
	ipfire_make libnfnetlink
	ipfire_make libnetfilter_queue
	ipfire_make libnetfilter_conntrack
	ipfire_make libnetfilter_log
	ipfire_make dnsmasq
	ipfire_make l7-protocols
	ipfire_make bridge-utils
	ipfire_make vlan
	ipfire_make bind
	ipfire_make whois
	
	### Building some general stuff
	#   STAGE 2
	ipfire_make pam					PASS=1
	ipfire_make shadow
	ipfire_make pam					PASS=2
	ipfire_make slang
	ipfire_make newt
	ipfire_make cyrus-sasl
	ipfire_make openldap
	ipfire_make sqlite
	ipfire_make curl
	ipfire_make gnupg
	ipfire_make sudo
	#ipfire_make libjpeg
	ipfire_make libpng
	ipfire_make libtiff
	ipfire_make libart
	ipfire_make freetype
	ipfire_make lzo
	ipfire_make lsof
	ipfire_make br2684ctl
	ipfire_make etherwake
	ipfire_make beep
	
	### Building vpn stuff
	#
	ipfire_make strongswan
	#ipfire_make openvpn
	
	### Building filesystem stuff
	#
	ipfire_make reiserfsprogs
	ipfire_make libaal
	ipfire_make reiser4progs
	ipfire_make xfsprogs
	ipfire_make sysfsutils
		
	### Building hardware utils
	#
	ipfire_make pciutils
	ipfire_make usbutils
	ipfire_make hdparm
	ipfire_make smartmontools
	ipfire_make lm-sensors
	ipfire_make hal
	ipfire_make hal-info

	### Building some important tools
	#
	ipfire_make ulogd2
	ipfire_make fcron
	ipfire_make which
	ipfire_make screen
	ipfire_make rrdtool
	ipfire_make ntp			### Needs config.
	ipfire_make openssh
	ipfire_make ez-ipupdate
	ipfire_make noip
	ipfire_make lighttpd
	ipfire_make collectd
	#ipfire_make logrotate
	#ipfire_make logwatch	
	ipfire_make cpio
	ipfire_make cdrtools
	ipfire_make parted
	ipfire_make memtest86+
	#ipfire_make pakfire
	#ipfire_make initscripts
	ipfire_make chkconfig
	
	ipfire_make pyfire
  
	### -------------------------------------------------------------------------
	### Tools that maybe not needed
	#
	#ipfire_make gd
	#ipfire_make libcap
	#ipfire_make mtools
	#ipfire_make mISDN
	
	#ipfire_make wireless
	#ipfire_make libsafe
}

################################################################################
# This builds the entire stage "misc"                                          #
################################################################################
misc_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=04
	STAGE=misc

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-misc.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	ipfire_make stage4
	
	### Console tools
	#
	ipfire_make mc
	#ipfire_make traceroute
	#ipfire_make nmap
	#ipfire_make rsync
	#ipfire_make tcpdump
	ipfire_make htop
	ipfire_make nano
	
	### Assembler
	#
	ipfire_make nasm
	ipfire_make syslinux

	ipfire_make busybox
	ipfire_make mkinitramfs
	
	#ipfire_make squid
	#ipfire_make squidguard		## CAN THIS BE BANISHED BY ANYTHING BETTER?
	#ipfire_make calamaris		## CAN THIS BE BANISHED BY ANYTHING BETTER?
	#ipfire_make vsftpd

	## NTFS
	#ipfire_make fuse
	#ipfire_make ntfs-3g
	#
	## Net tools
	#ipfire_make bwm-ng
	#
	## UPNP
	#ipfire_make libupnp
	#ipfire_make linux-igd

	### These will become addons as usual but will be integrated later
	#
	#ipfire_make snort
	#ipfire_make oinkmaster
	#ipfire_make centerim
	#ipfire_make tripwire
	#ipfire_make java
	#ipfire_make cups
	#ipfire_make ghostscript
	#ipfire_make foomatic
	#ipfire_make hplip
	#ipfire_make samba
	#ipfire_make postfix
	#ipfire_make fetchmail
	#ipfire_make cyrus-imapd
	#ipfire_make clamav
	#ipfire_make alsa
	#ipfire_make mpg123
	#ipfire_make mpfire
	#ipfire_make guardian
	#ipfire_make libid3tag
	#ipfire_make libmad
	#ipfire_make libogg
	#ipfire_make libvorbis
	#ipfire_make lame
	#ipfire_make sox
	#ipfire_make libshout
	#ipfire_make icecast
	#ipfire_make icegenerator
	#ipfire_make mpd
	#ipfire_make mpc
	#ipfire_make xvid
	#ipfire_make libmpeg2
	#ipfire_make videolan
	#ipfire_make libpri
	#ipfire_make asterisk
	#ipfire_make libsigc++
	#ipfire_make applejuice
	#ipfire_make libtorrent
	#ipfire_make rtorrent
	#ipfire_make ipfireseeder
	#ipfire_make nfs

	# ---------------------------------------------------------------------------
	#ipfire_make as86
	#ipfire_make mbr

	### Debugging
	#
	ipfire_make strace
}

################################################################################
# This builds the entire stage "installer"                                     #
################################################################################
installer_build() {

	PATH=${TOOLS_DIR}/usr/bin:${UCLIBC_DIR}/bin:${UCLIBC_DIR}/usr/bin
	PATH=$PATH:${UCLIBC_CC_CORE_STATIC_DIR}/bin:/bin:/usr/bin
	PATH=$PATH:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=05
	STAGE=installer

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-installer.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	ipfire_make stage5
	ipfire_make ccache
	ipfire_make gmp
	ipfire_make mpfr
	ipfire_make linux
	ipfire_make binutils
	ipfire_make uClibc		PASS=1
	ipfire_make gcc			PASS=1
	ipfire_make uClibc		PASS=2
	ipfire_make gettext		PASS=1
	ipfire_make gcc			PASS=2
	ipfire_make gettext		PASS=2
	ipfire_make udev
	ipfire_make pciutils
	ipfire_make zlib
	ipfire_make ncurses
	ipfire_make pcre
	ipfire_make popt
	ipfire_make glib
	ipfire_make readline
	ipfire_make e2fsprogs
	ipfire_make util-linux-ng
	ipfire_make parted
	ipfire_make expat
	ipfire_make dbus
	ipfire_make dbus-glib
	ipfire_make hal
	ipfire_make hal-info
	ipfire_make openssl
	ipfire_make python
	ipfire_make python-dbus
	ipfire_make python-parted
	ipfire_make python-urlgrabber
	ipfire_make python-iconv
	ipfire_make slang
	ipfire_make newt
	ipfire_make bash
	ipfire_make strace
	ipfire_make cpio
	ipfire_make lzma
	ipfire_make reiserfsprogs
	ipfire_make pyfire
	ipfire_make pomona
	ipfire_make busybox
}

################################################################################
# This builds the entire stage "packages"                                      #
################################################################################
packages_build() {

	PATH=${TOOLS_DIR}/usr/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=06
	STAGE=packages

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.${STAGE_ORDER}-packages.log"
	export LOGFILE

	build_spy set stage ${STAGE} &

	toolchain_make strip

	# Generate ChangeLog
	git_log

	if [ ${EMB} -eq 0 ]; then
		ipfire_make initramfs

		ipfire_make cdrom

		if check_loop; then
			#ipfire_make usb-stick
			:
		else
			echo -n "Can't build usb-key images on this machine"
			beautify message WARN
		fi
		mv $LFS/$IMAGES_DIR/{*.iso,*.tgz,*.img.gz} $BASEDIR >> $LOGFILE 2>&1
	else
		if check_loop; then
			# We put here the code that is done when
			# we do an embedded build
			:
		fi
	fi

	# Build packages
	for i in $(ls -1 $BASEDIR/src/rootfiles/extras); do
		if [ -e $BASEDIR/lfs/$i ]; then
			echo -n $i
			beautify message SKIP
		else
			echo -n $i
			beautify message SKIP
		fi
	done

	# Cleanup
	stdumount
	rm -rf $LFS/tmp/*
	
	cd $PWD
}

# See what we're supposed to do
. $BASEDIR/tools/make-interactive
