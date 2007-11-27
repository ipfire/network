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
# Copyright (C) 2007 IPFire-Team <info@ipfire.org>.                        #
#                                                                          #
############################################################################
#

NAME="IPFire"										# Software name
SNAME="ipfire"									# Short name
VERSION="2.9"										# Version number
TOOLCHAINVERSION="${VERSION}"   # Toolchain
SLOGAN="www.ipfire.org"					# Software slogan

# Include funtions
. tools/make-include


################################################################################
# This builds the entire stage "toolchain"                                     #
################################################################################
toolchain_build() {

	ORG_PATH=$PATH
	export PATH=$BASEDIR/build_${MACHINE}/usr/local/ccache/bin:$BASEDIR/build_${MACHINE}/usr/local/distcc/bin:$BASEDIR/build_${MACHINE}/$TOOLS_DIR/bin:$PATH
	STAGE_ORDER=01
	STAGE=toolchain

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.toolchain.log"
	export LOGFILE
	
	NATIVEGCC=`gcc --version | grep GCC | awk {'print $3'}`
	export NATIVEGCC GCCmajor=${NATIVEGCC:0:1} GCCminor=${NATIVEGCC:2:1} GCCrelease=${NATIVEGCC:4:1}
	
	# make distcc first so that CCACHE_PREFIX works immediately
	[ -z "$DISTCC_HOSTS" ] || toolchain_make distcc
	toolchain_make ccache
	
	toolchain_make binutils											PASS=1
	toolchain_make gcc													PASS=1
	toolchain_make linux
	toolchain_make glibc
	toolchain_make adjust-toolchain
	toolchain_make tcl
	toolchain_make expect
	toolchain_make dejagnu
	toolchain_make gcc													PASS=2
	toolchain_make binutils											PASS=2
	toolchain_make ncurses
	toolchain_make bash
	toolchain_make bzip2
	toolchain_make coreutils
	toolchain_make diffutils
	toolchain_make findutils
	toolchain_make gawk
	toolchain_make gettext
	toolchain_make grep
	toolchain_make gzip
	toolchain_make make
	toolchain_make patch
	toolchain_make perl
	toolchain_make sed
	toolchain_make tar
	toolchain_make texinfo
	toolchain_make util-linux
	# toolchain_make strip
	export PATH=$ORG_PATH
}

################################################################################
# This builds the entire stage "base"                                          #
################################################################################
base_build() {

	PATH=/usr/local/ccache/bin:/usr/local/distcc/bin:/bin:/usr/bin:/sbin:/usr/sbin:$TOOLS_DIR/bin
	STAGE_ORDER=02
	STAGE=base

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.base.log"
	export LOGFILE
	
	ipfire_make stage2
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
	ipfire_make gettext
	ipfire_make grep
	ipfire_make groff
	ipfire_make gzip
	ipfire_make inetutils
	ipfire_make iproute2
	ipfire_make kbd
	ipfire_make less
	ipfire_make make
	ipfire_make man-db
	ipfire_make mktemp
	ipfire_make module-init-tools
	ipfire_make patch
	ipfire_make psmisc
	ipfire_make shadow
	ipfire_make sysklogd
	ipfire_make sysvinit
	ipfire_make tar
	ipfire_make texinfo
	ipfire_make udev					## NEED TO INSTALL CONFIG
	ipfire_make util-linux
	ipfire_make vim
}

################################################################################
# This builds the entire stage "ipfire"                                        #
################################################################################
ipfire_build() {
	PATH=/usr/local/ccache/bin:/usr/local/distcc/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=03
	STAGE=ipfire

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.ipfire.log"
	export LOGFILE
	
	### Building the configuration dirs and files
	#
	ipfire_make stage3
	
	### Building the kernel stuff
	#
	ipfire_make linux
	
	### Building pkg-config
	#
	ipfire_make pkg-config
	
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
	ipfire_make dnsmasq
	ipfire_make l7-protocols
	ipfire_make iptstate
	ipfire_make bridge-utils
	ipfire_make vlan
	
	### Building some general stuff
	#
	ipfire_make openssl
	ipfire_make pam																			PASS=1
	ipfire_make shadow
	ipfire_make pam																			PASS=2
	
	#ipfire_make libidn		### Do we need this?
  ipfire_make pcre
	ipfire_make popt
	ipfire_make python
	ipfire_make libxml2
	ipfire_make libxslt
	ipfire_make slang
	ipfire_make newt
	ipfire_make cyrus-sasl
  ipfire_make openldap
  ipfire_make sqlite
	ipfire_make curl
	ipfire_make libusb
	ipfire_make gnupg
	ipfire_make sudo
	#ipfire_make libjpeg	### Do we need this?
	ipfire_make libpng
	ipfire_make libtiff
	ipfire_make libart
	ipfire_make freetype
	ipfire_make lzo
	ipfire_make lsof
	ipfire_make br2684ctl
	ipfire_make etherwake
	ipfire_make htop
	ipfire_make beep
	
	### Building filesystem stuff
	#
	ipfire_make reiserfsprogs
	ipfire_make libaal
	ipfire_make reiser4progs
	ipfire_make xfsprogs
		
	### Building hardware utils
	#
	ipfire_make pciutils
	ipfire_make usbutils
	ipfire_make hdparm
	ipfire_make kudzu
	ipfire_make smartmontools

	### Building some important tools
	#
	ipfire_make fcron
	ipfire_make which
	ipfire_make nano
	ipfire_make screen
	ipfire_make rrdtool
	ipfire_make ntp			### Needs config.
	ipfire_make openssh
	ipfire_make ez-ipupdate
	ipfire_make noip
	ipfire_make lighttpd
	ipfire_make lzma
	
	### Programs that are still for discussion
	#   package or in the standard system
	#
	## NTFS
	#ipfire_make fuse
  #ipfire_make ntfs-3g
  #
  ## Net tools
  #ipfire_make bwm-ng
  #ipfire_make openvpn
  #
  ## UPNP
  #ipfire_make libupnp
  #ipfire_make linux-igd
  
  #ipfire_make pakfire
  #ipfire_make initscripts
	
	#ipfire_make backup
  #ipfire_make expat
  #ipfire_make gmp
  #ipfire_make gd
  #ipfire_make libcap

  #ipfire_make bind
  #ipfire_make cdrtools
  #ipfire_make dosfstools
  #ipfire_make sysfsutils
  #ipfire_make mtools
  #ipfire_make mISDN
  #ipfire_make logrotate
  #ipfire_make logwatch
  #ipfire_make nasm
  #ipfire_make glib
  
  #ipfire_make wireless
  #ipfire_make libsafe
}

################################################################################
# This builds the entire stage "misc"                                          #
################################################################################
misc_build() {

	PATH=/usr/local/ccache/bin:/usr/local/distcc/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=04
	STAGE=misc

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.misc.log"
	export LOGFILE
	
	#ipfire_make stage4
	
	ipfire_make cpio
	ipfire_make cdrtools
	ipfire_make parted
	ipfire_make memtest86+
	
	#ipfire_make snort
	#ipfire_make oinkmaster
	#ipfire_make squid
	#ipfire_make squid-graph
	#ipfire_make squidguard
	#ipfire_make calamaris
	#ipfire_make tcpdump
	#ipfire_make traceroute
	#ipfire_make vsftpd
	#ipfire_make centerim
	#ipfire_make ncftp
	#ipfire_make tripwire
	#ipfire_make java
	#ipfire_make spandsp
	#ipfire_make cups
	#ipfire_make ghostscript
	#ipfire_make foomatic
	#ipfire_make hplip
	#ipfire_make samba
	#ipfire_make mc
	#ipfire_make wget
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
	#ipfire_make gnump3d
	#ipfire_make libsigc++
	#ipfire_make applejuice
	#ipfire_make ocaml
	#ipfire_make mldonkey
	#ipfire_make libtorrent
	#ipfire_make rtorrent
	#ipfire_make ipfireseeder
	#ipfire_make rsync
	#ipfire_make nfs
	#ipfire_make nmap
	
}

################################################################################
# This builds the entire stage "installer"                                     #
################################################################################
installer_build() {

	PATH=/usr/local/ccache/bin:/usr/local/distcc/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=05
	STAGE=installer

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.installer.log"
	export LOGFILE
	
	ipfire_make busybox
	ipfire_make initramfs
	
	exiterror "Stop here."
	
	#ipfire_make klibc  ##### Maybe this will be in the installer pass
  #ipfire_make mkinitcpio
  #ipfire_make udev																	KLIBC=1

  ipfire_make as86
  ipfire_make mbr
  ipfire_make gettext
  ipfire_make kbd
  ipfire_make popt
  ipfire_make sysvinit
  ipfire_make libaal
  ipfire_make reiser4progs
  ipfire_make reiserfsprogs
  ipfire_make sysfsutils
  ipfire_make util-linux
  ipfire_make pciutils
  ipfire_make zlib
  ipfire_make mtd
  ipfire_make wget
  ipfire_make hwdata
  ipfire_make kudzu
  ipfire_make installer
  ipfire_make initrd
}

################################################################################
# This builds the entire stage "packages"                                      #
################################################################################
packages_build() {

	PATH=/usr/local/ccache/bin:/usr/local/distcc/bin:/bin:/usr/bin:/sbin:/usr/sbin:/usr/${MACHINE_REAL}-linux/bin
	STAGE_ORDER=06
	STAGE=packages

	LOGFILE="$BASEDIR/log_${MACHINE}/_build.packages.log"
	export LOGFILE
	
  echo "... see detailed log in _build.*.log files" >> $LOGFILE

  ipfire_make strip
  
  # Generating list of packages used
  echo -n "Generating packages list from logs" | tee -a $LOGFILE
  rm -f $BASEDIR/doc/packages-list
  for i in `ls -1tr $BASEDIR/log/[^_]*`; do
	if [ "$i" != "$BASEDIR/log/FILES" -a -n $i ]; then
		echo "* `basename $i`" >>$BASEDIR/doc/packages-list
	fi
  done
  echo "== List of softwares used to build $NAME Version: $VERSION ==" > $BASEDIR/doc/packages-list.txt
  grep -v 'configroot$\|img$\|initrd$\|initscripts$\|installer$\|install$\|setup$\|pakfire$\|stage2$\|smp$\|tools$\|tools1$\|tools2$\|.tgz$\|-config$\|_missing_rootfile$\|install1$\|install2$\|pass1$\|pass2$\|pass3$' \
	$BASEDIR/doc/packages-list | sort >> $BASEDIR/doc/packages-list.txt
  rm -f $BASEDIR/doc/packages-list
  # packages-list.txt is ready to be displayed for wiki page
  beautify message DONE

  # Create images for install
	ipfire_make cdrom ED=full
	
  # Check if there is a loop device for building in virtual environments
  if [ -e /dev/loop/0 ] || [ -e /dev/loop0 ]; then
  	ipfire_make usb-stick
  fi
  mv $LFS/install/images/{*.iso,*.tgz,*.img.gz} $BASEDIR >> $LOGFILE 2>&1

  ipfirepackages

  # Cleanup
  stdumount
  rm -rf $BASEDIR/build/tmp/*

  # Generating total list of files
  echo -n "Generating files list from logs" | tee -a $LOGFILE
  rm -f $BASEDIR/log/FILES
  for i in `ls -1tr $BASEDIR/log/[^_]*`; do
	if [ "$i" != "$BASEDIR/log/FILES" -a -n $i ]; then
		echo "##" >>$BASEDIR/log/FILES
		echo "## `basename $i`" >>$BASEDIR/log/FILES
		echo "##" >>$BASEDIR/log/FILES
		cat $i | sed "s%^\./%#%" | sort >> $BASEDIR/log/FILES
	fi
  done
  beautify message DONE

  cd $PWD
}

ipfirepackages() {
	ipfire_make core-updates
	for i in $(ls -1 $BASEDIR/src/rootfiles/extras); do
		if [ -e $BASEDIR/lfs/$i ]; then
			ipfire_dist $i
		else
			echo -n $i
			beautify message SKIP
		fi
	done
  test -d $BASEDIR/packages || mkdir $BASEDIR/packages
  mv -f $LFS/install/packages/* $BASEDIR/packages >> $LOGFILE 2>&1
  rm -rf  $BASEDIR/build/install/packages/*
}

# See what we're supposed to do
case "$1" in 
build)
	clear
	#a prebuilt toolchain package is only used if found in cache
	if [ ! -d $BASEDIR/cache ]; then
		exiterror "Use make.sh downloadsrc first!"
	fi
	cd $BASEDIR/cache
	PACKAGE=`ls -v -r $TOOLCHAINNAME.tar.gz 2> /dev/null | head -n 1`
	#only restore on a clean disk

	echo -ne "Building for ${BOLD}${MACHINE} on ${MACHINE_REAL}${NORMAL}\n"
	
	if [ -f $BASEDIR/log_${MACHINE}/02_base/stage2-LFS ]; then
		prepareenv
		echo "Using installed toolchain" >> $LOGFILE
		beautify message DONE "Stage toolchain already built or extracted"
	else
		if [ -z "$PACKAGE" ]; then
			echo "Full toolchain compilation" | tee -a $LOGFILE
			prepareenv
			
			# Check if host can build the toolchain
			check_toolchain_prerequisites
			
			beautify build_stage "Building toolchain"
			toolchain_build
		else
			echo "Restore from $PACKAGE" | tee -a $LOGFILE
			if [ `md5sum $BASEDIR/cache/$PACKAGE | awk '{print $1}'` == `cat $BASEDIR/cache/$TOOLCHAINNAME.md5 | awk '{print $1}'` ]; then
				cd $BASEDIR && tar zxf $BASEDIR/cache/$PACKAGE
				prepareenv
			else
				exiterror "$TOOLCHAINNAME md5 did not match, check downloaded package"
			fi
		fi
	fi
	
	if [ ! -e $BASEDIR/log_${MACHINE}/03_ipfire/stage3-LFS ]; then
		beautify build_stage "Building base"
		base_build
	else
		beautify message DONE "Stage base      already built"
	fi

	if [ ! -e $BASEDIR/log_${MACHINE}/04_misc/stage4-LFS ]; then
		beautify build_stage "Building $NAME"
		ipfire_build
	else
		beautify message DONE "Stage ipfire    already built"
	fi

	if [ ! -e $BASEDIR/log_${MACHINE}/05_installer/stage5-LFS ]; then
		beautify build_stage "Building miscellaneous"
		misc_build
	else
		beautify message DONE "Stage misc      already built"
	fi

	beautify build_stage "Building installer"
	installer_build

	beautify build_stage "Building packages"
	packages_build
	
	echo ""
	echo "Burn a CD (floppy is too big) or use pxe to boot."
	echo "... and all this hard work for this:"
	du -bsh $BASEDIR/${SNAME}-${VERSION}*.${MACHINE}.iso
	;;
	
shell)
	# enter a shell inside LFS chroot
	# may be used to changed kernel settings
	prepareenv
	entershell
	;;
	
changelog)
	echo -n "Loading new Changelog from SVN: "
	svn log http://svn.ipfire.org/svn/ipfire > doc/ChangeLog
	beautify message DONE
	;;
	
clean)
	echo -ne "Cleaning ${BOLD}$MACHINE${NORMAL} buildtree"
	for i in `mount | grep $BASEDIR | sed 's/^.*loop=\(.*\))/\1/'`
	do
		$LOSETUP -d $i 2>/dev/null
	done

	for i in `mount | grep $BASEDIR | cut -d " " -f 1`
	do
		umount $i
	done

	stdumount
	
	for i in `seq 0 7`
	do
		if ( losetup /dev/loop${i} 2>/dev/null | grep -q "/install/images" ); then
			umount /dev/loop${i}     2>/dev/null;
			losetup -d /dev/loop${i} 2>/dev/null;
		fi;
	done

	rm -rf $BASEDIR/build_${MACHINE}
	rm -rf $BASEDIR/log_${MACHINE}
	rm -rf $BASEDIR/packages
	
	if [ -h $TOOLS_DIR ]; then
		rm -f $TOOLS_DIR
	fi
	beautify message DONE
	;;
	
downloadsrc)
	LOGFILE=$BASEDIR/log_${MACHINE}/_build.preparation.log
	
	if [ ! -d $BASEDIR/cache ]; then
		mkdir $BASEDIR/cache
	fi
	mkdir -p $BASEDIR/log_${MACHINE}
	echo -e "${BOLD}Preload all source files${NORMAL}" | tee -a $LOGFILE
	FINISHED=0
	cd $BASEDIR/lfs
	for c in `seq $MAX_RETRIES`; do
		if (( FINISHED==1 )); then 
			break
		fi
		FINISHED=1
		cd $BASEDIR/lfs
		for i in *; do
			if [ -f "$i" -a "$i" != "Config" ]; then
				echo -ne "Loading $i"
				make -s -f $i LFS_BASEDIR=$BASEDIR MESSAGE="$i\t ($c/$MAX_RETRIES)" download >> $LOGFILE 2>&1
				if [ $? -ne 0 ]; then
					beautify message FAIL
					FINISHED=0
				else
					if [ $c -eq 1 ]; then
					beautify message DONE
					fi
				fi
			fi
		done
	done
	cd - >/dev/null 2>&1
	;;
	
toolchain)
	prepareenv
	# Check if host can build the toolchain
	check_toolchain_prerequisites
	toolchain_build
	echo "Create toolchain tar.bz for $MACHINE" | tee -a $LOGFILE
	# Safer inside the chroot
	echo -ne "Stripping lib"
	chroot $LFS $TOOLS_DIR/bin/find $TOOLS_DIR/lib \
		-type f \( -name '*.so' -o -name '*.so[\.0-9]*' \) \
		-exec $TOOLS_DIR/bin/strip --strip-debug {} \; 2>/dev/null
	beautify message DONE
	echo -ne "Stripping binaries"
	chroot $LFS $TOOLS_DIR/bin/find /usr/local /usr/src/binutils-build $TOOLS_DIR/bin $TOOLS_DIR/sbin \
		-type f \
		-exec $TOOLS_DIR/bin/strip --strip-all {} \; 2> /dev/null
	beautify message DONE
	stdumount
	echo -ne "Tar creation "
	cd $BASEDIR && tar cvj \
				--exclude='log_${MACHINE}/_build.*.log' \
				--file=cache/$TOOLCHAINNAME.tar.bz2 \
				build_${MACHINE} \
				log_${MACHINE} >> $LOGFILE
	beautify message DONE
	echo `ls -sh cache/$TOOLCHAINNAME.tar.bz2`
	md5sum cache/$TOOLCHAINNAME.tar.bz2 \
		> cache/$TOOLCHAINNAME.md5

	stdumount
	;;
	
gettoolchain)
	if [ ! -f $BASEDIR/cache/toolchains/$TOOLCHAINNAME.tar.bz2 ]; then
		URL_TOOLCHAIN=`grep URL_TOOLCHAIN lfs/Config | awk '{ print $3 }'`
		test -d $BASEDIR/cache/toolchains || mkdir $BASEDIR/cache/toolchains
		echo "Load toolchain tar.bz2 for $MACHINE" | tee -a $LOGFILE
		cd $BASEDIR/cache/toolchains
		wget -c -nv $URL_TOOLCHAIN/$TOOLCHAINNAME.tar.bz2 $URL_TOOLCHAIN/$TOOLCHAINNAME.md5
		if [ $? -ne 0 ]; then
			echo -ne "Error downloading toolchain for $MACHINE machine" | tee -a $LOGFILE
			beautify message FAIL
			echo "Precompiled toolchain not always available for every MACHINE" | tee -a $LOGFILE
		else
			if [ "`md5sum $TOOLCHAINNAME.tar.bz2 | awk '{print $1}'`" = "`cat $TOOLCHAINNAME.md5 | awk '{print $1}'`" ]; then
				beautify message DONE
				echo "Toolchain md5 ok" | tee -a $LOGFILE
			else
				exiterror "$TOOLCHAINNAME.md5 did not match, check downloaded package"
			fi
		fi
	else
		echo "Toolchain tar.bz2 for $MACHINE is already downloaded" | tee -a $LOGFILE
		beautify message SKIP
	fi
	;;
	
othersrc)
	prepareenv
	echo -ne "`date -u '+%b %e %T'`: Build sources iso for $MACHINE" | tee -a $LOGFILE
	chroot $LFS /tools/bin/env -i   HOME=/root \
	TERM=$TERM PS1='\u:\w\$ ' \
	PATH=/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin \
	VERSION=$VERSION NAME="$NAME" SNAME="$SNAME" MACHINE=$MACHINE \
	/bin/bash -x -c "cd /usr/src/lfs && make -f sources-iso LFS_BASEDIR=/usr/src install" >>$LOGFILE 2>&1
	mv $LFS/install/images/ipfire-* $BASEDIR >> $LOGFILE 2>&1
	if [ $? -eq "0" ]; then
		beautify message DONE
	else
		beautify message FAIL
	fi
	stdumount
	;;
	
svn)
	case "$2" in
	  update|up)
		# clear
		echo -ne "Loading the latest source files...\n"
		if [ $3 ]; then
			svn update -r $3 | tee -a $PWD/log/_build.svn.update.log
		else
			svn update | tee -a $PWD/log/_build.svn.update.log
		fi
		if [ $? -eq "0" ]; then
			beautify message DONE
		else
			beautify message FAIL
			exit 1
		fi
		echo -ne "Writing the svn-info to a file"
		svn info > $PWD/svn_status
		if [ $? -eq "0" ]; then
			beautify message DONE
		else
			beautify message FAIL
			exit 1
		fi
		chmod 755 $0
		exit 0
	  ;;
	  commit|ci)
		clear
		if [ -f /usr/bin/mcedit ]; then
			export EDITOR=/usr/bin/mcedit
		fi
		if [ -f /usr/bin/nano ]; then
			export EDITOR=/usr/bin/nano
		fi
		echo -ne "Selecting editor $EDITOR..."
		beautify message DONE
		if [ -e /sbin/yast ]; then
			if [ "`echo $SVN_REVISION | cut -c 3`" -eq "0" ]; then
				$0 changelog
			fi
		fi
		update_langs
		svn commit
		$0 svn up
		if [ -n "$FTP_CACHE_URL" ]; then
			$0 uploadsrc
		fi
	  ;;
	  dist)
		if [ $3 ]; then
			SVN_REVISION=$3
		fi
		if [ -f ipfire-source-r$SVN_REVISION.tar.gz ]; then
			echo -ne "REV $SVN_REVISION: SKIPPED!\n"
			exit 0
		fi
		echo -en "REV $SVN_REVISION: Downloading..."
		svn export http://svn.ipfire.org/svn/ipfire/trunk ipfire-source/ --force > /dev/null
		svn log http://svn.ipfire.org/svn/ipfire/trunk -r 1:$SVN_REVISION > ipfire-source/Changelog
		#svn info http://svn.ipfire.org/svn/ipfire/trunk -r $SVN_REVISION > ipfire-source/svn_status
		evaluate 1

		echo -en "REV $SVN_REVISION: Compressing files..."
		if [ -e ipfire-source/trunk/make.sh ]; then
			chmod 755 ipfire-source/trunk/make.sh
		fi
		tar cfz ipfire-source-r$SVN_REVISION.tar.gz ipfire-source
		evaluate 1
		echo -en "REV $SVN_REVISION: Cleaning up..."
		rm ipfire-source/ -r
		evaluate 1
	  ;;
	  diff|di)
	  update_langs
		echo -ne "Make a local diff to last svn revision"
		svn diff > ipfire-diff-`date +'%Y-%m-%d-%H:%M'`-r`svn info | grep Revision | cut -c 11-`.diff
		evaluate 1
		echo "Diff was successfully saved to ipfire-diff-`date +'%Y-%m-%d-%H:%M'`-r`svn info | grep Revision | cut -c 11-`.diff"
		svn status
	  ;;
	esac
	;;
	
uploadsrc)
	PWD=`pwd`
	cd $BASEDIR/cache/
	echo -e "Uploading cache to ftp server:"
	for i in *; do
		echo "${i}" | fgrep -q .md5 && continue
		[ -e ${i}.md5 ] && continue
		md5sum ${i} | tee ${i}.md5
	done
	ncftpls -u $FTP_CACHE_USER -p $FTP_CACHE_PASS ftp://$FTP_CACHE_URL/$FTP_CACHE_PATH/ > /tmp/ftplist
	for i in *; do
		if [ "$(basename $i)" == "toolchains" ]; then continue; fi
		grep -q $(basename $i) /tmp/ftplist
		if [ "$?" -ne "0" ]; then
			echo -ne "$(basename $i)"
			ncftpput -u $FTP_CACHE_USER -p $FTP_CACHE_PASS $FTP_CACHE_URL $FTP_CACHE_PATH/ $(basename $i)
			if [ "$?" -ne "0" ]; then
				beautify message FAIL
			fi
		fi
	done
	rm -f /tmp/ftplist
	cd $PWD
	exit 0
	;;
	
upload)
	FTP_ISO_PORT=`echo "$FTP_ISO_URL" | awk -F: '{ print $2 }'`
	FTP_ISO_URL=`echo "$FTP_ISO_URL" | awk -F: '{ print $1 }'`
	if [ -z $FTP_ISO_PORT ]; then
	    FTP_ISO_PORT=21
	fi
	cat <<EOF > .ftp-commands
mkdir -p $FTP_ISO_PATH$SVN_REVISION
mkdir -p $FTP_ISO_PATH$SVN_REVISION/paks
quit
EOF
	ncftp -u $FTP_ISO_USER -p $FTP_ISO_PASS -P $FTP_ISO_PORT $FTP_ISO_URL < .ftp-commands
	rm -f .ftp-commands
		
	case "$2" in
	  iso)
		echo -e "Uploading the iso to $FTP_ISO_PATH/$SVN_REVISION."

		md5sum ipfire-$VERSION.$MACHINE-full.iso > ipfire-$VERSION.$MACHINE-full.iso.md5
		for i in svn_status ipfire-source-r$SVN_REVISION.tar.gz ipfire-$VERSION.$MACHINE-full.iso ipfire-$VERSION.$MACHINE-full.iso.md5 ipfire-$VERSION.$MACHINE-devel.iso ipfire-$VERSION.$MACHINE-devel.iso.md5; do
				if [ -e "$i" ]; then
			    ncftpput -u $FTP_ISO_USER -p $FTP_ISO_PASS -P $FTP_ISO_PORT $FTP_ISO_URL $FTP_ISO_PATH$SVN_REVISION/ $i
					if [ "$?" -eq "0" ]; then
						echo "The file with name $i was successfully uploaded to $FTP_ISO_URL$FTP_ISO_PATH$SVN_REVISION/."
					else
						echo "There was an error while uploading the file $i to the ftp server."
						exit 1
					fi
				fi
		done
		rm -f ipfire-$VERSION.$MACHINE-full.iso.md5
		if [ "$3" = "--with-sources-cd" ]; then
			ncftpput -u $FTP_ISO_USER -p $FTP_ISO_PASS -P $FTP_ISO_PORT $FTP_ISO_URL $FTP_ISO_PATH/$SVN_REVISION/ ipfire-sources-cd-$VERSION.$MACHINE.iso
		fi
		;;
	  paks)
		ncftpput -u $FTP_ISO_USER -p $FTP_ISO_PASS -P $FTP_ISO_PORT $FTP_ISO_URL $FTP_ISO_PATH$SVN_REVISION/paks packages/*
		if [ "$?" -eq "0" ]; then
			echo -e "The packages were successfully uploaded to $FTP_ISO_URL$FTP_ISO_PATH$SVN_REVISION/."
		else
			echo -e "There was an error while uploading the packages to the ftp server."
			exit 1
		fi
	  ;;
	esac
	;;
	
batch)
	if [ "$2" = "--background" ]; then
		batch_script
		exit $?
	fi
	if [ `screen -ls | grep -q ipfire` ]; then
		echo "Build is already running, sorry!"
		exit 1
	else
		if [ "$2" = "--rebuild" ]; then
			export IPFIRE_REBUILD=1
			echo "REBUILD!"
		else
			export IPFIRE_REBUILD=0
		fi
		echo -en "${BOLD}***IPFire-Batch-Build is starting...${NORMAL}"
		screen -dmS ipfire $0 batch --background
		evaluate 1
		exit 0
	fi
	;;
	
watch|attach)
	watch_screen
	;;

*)
	cat doc/make.sh-usage
	;;
	
esac
