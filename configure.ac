###############################################################################
#                                                                             #
# Pakfire - The IPFire package management system                              #
# Copyright (C) 2013 IPFire Network Development Team                          #
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

AC_PREREQ([2.64])

AC_INIT([network],
	[011],
	[info@ipfire.org],
	[network],
	[http://www.ipfire.org/])

AC_CONFIG_AUX_DIR([build-aux])

AC_PREFIX_DEFAULT([/usr])

AM_INIT_AUTOMAKE([
	foreign
	1.11
	-Wall
	-Wno-portability
	silent-rules
	tar-pax
	subdir-objects
])
AM_SILENT_RULES([yes])

LT_INIT([
	disable-static
	pic-only
])

AC_PROG_LN_S
AC_PROG_MKDIR_P
AC_PROG_SED

AC_PATH_PROG([NITSI], [nitsi])
AC_PATH_PROG([WGET], [wget])
AC_PATH_PROG([XSLTPROC], [xsltproc])

# pkg-config
PKG_PROG_PKG_CONFIG
# This makes sure pkg.m4 is available.
m4_pattern_forbid([^_?PKG_[A-Z_]+$],[*** pkg.m4 missing, please install pkg-config])

# C Compiler
AC_PROG_CC
AC_PROG_CC_C99
AC_PROG_CC_C_O
AC_PROG_GCC_TRADITIONAL

CC_CHECK_FLAGS_APPEND([with_cflags], [CFLAGS], [\
	-pipe \
	-Wall \
	-Wextra \
	-Wno-inline \
	-Wundef \
	"-Wformat=2 -Wformat-security -Wformat-nonliteral" \
	-Wno-unused-parameter \
	-Wno-unused-result \
	-fno-strict-aliasing \
	-ffunction-sections \
	-fdata-sections \
	-fstack-protector-all \
	--param=ssp-buffer-size=4])
AC_SUBST([OUR_CFLAGS], $with_cflags)

AS_CASE([$CFLAGS], [*-O[[12345g\ ]]*],
	[CC_CHECK_FLAGS_APPEND([with_cppflags], [CPPFLAGS], [\
		-Wp,-D_FORTIFY_SOURCE=2])],
	[AC_MSG_RESULT([skipping -D_FORTIFY_SOURCE, optimization not enabled])])
AC_SUBST([OUR_CPPFLAGS], $with_cppflags)

CC_CHECK_FLAGS_APPEND([with_ldflags], [LDFLAGS], [\
	-Wl,--as-needed \
	-Wl,--no-undefined \
	-Wl,--gc-sections \
	-Wl,-z,relro \
	-Wl,-z,now])
AC_SUBST([OUR_LDFLAGS], $with_ldflags)

# ------------------------------------------------------------------------------

AC_CHECK_HEADERS_ONCE([
	ctype.h
	errno.h
	linux/netlink.h
	net/if.h
	stdarg.h
	stdio.h
	stdlib.h
	string.h
	syslog.h
])

AC_CHECK_FUNCS([ \
	__secure_getenv \
	secure_getenv \
])

# ------------------------------------------------------------------------------

AC_ARG_ENABLE([debug],
	AS_HELP_STRING([--enable-debug], [enable debug messages @<:@default=disabled@:>@]),
	[], [enable_debug=no])
AS_IF([test "x$enable_debug" = "xyes"], [
	AC_DEFINE(ENABLE_DEBUG, [1], [Debug messages.])
])

# ------------------------------------------------------------------------------

have_manpages=no
AC_ARG_ENABLE(manpages, AS_HELP_STRING([--disable-man-pages],
	[do not install man pages]))
AS_IF([test "x$enable_manpages" != xno], [have_manpages=yes])
AM_CONDITIONAL(ENABLE_MANPAGES, [test "x$have_manpages" = "xyes"])

# ------------------------------------------------------------------------------
AC_ARG_WITH([systemdsystemunitdir],
	AS_HELP_STRING([--with-systemdsystemunitdir=DIR], [Directory for systemd service files]),
	[], [with_systemdsystemunitdir=$($PKG_CONFIG --variable=systemdsystemunitdir systemd)])
AC_SUBST([systemdsystemunitdir], [$with_systemdsystemunitdir])
AM_CONDITIONAL(HAVE_SYSTEMD, [test -n "$with_systemdsystemunitdir"])

# ------------------------------------------------------------------------------
AC_ARG_WITH([udevdir],
	AS_HELP_STRING([--with-udevdir=DIR], [Directory for udev files]),
	[], [with_udevdir=$($PKG_CONFIG --variable=udevdir udev)])
AC_SUBST([udevdir], [$with_udevdir])
AM_CONDITIONAL(HAVE_UDEV, [test -n "$with_udevdir"])

# ------------------------------------------------------------------------------

PKG_CHECK_MODULES([LIBNL], [libnl-3.0 libnl-genl-3.0])

# ------------------------------------------------------------------------------

AC_CHECK_PROGS(ASCIIDOC, [asciidoc])
if test "${have_manpages}" = "yes" && test -z "${ASCIIDOC}"; then
	AC_MSG_ERROR([Required program 'asciidoc' not found])
fi

# ------------------------------------------------------------------------------

AC_CONFIG_HEADERS(config.h)
AC_CONFIG_FILES([
	Makefile
])

AC_OUTPUT
AC_MSG_RESULT([
	$PACKAGE_NAME $VERSION

	CFLAGS:               ${OUR_CFLAGS} ${CFLAGS}
	CPPFLAGS:             ${OUR_CPPFLAGS} ${CPPFLAGS}
	LDFLAGS:              ${OUR_LDFLAGS} ${LDFLAGS}

	prefix:               $prefix

	systemdsystemunitdir: $systemdsystemunitdir
	udevdir:              $udevdir

	Generate man-pages:   ${have_manpages}
])
