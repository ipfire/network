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

BASEDIR=/ipfire-3.x

. ${BASEDIR}/tools/common-include

while [ $# -gt 0 ]; do
	case "${1}" in
		--debug|-d)
			DEBUG=1
			log DEBUG "Debugging mode enabled by command line."
			;;
		--toolchain)
			TOOLCHAIN=1
			log DEBUG "Toolchain mode enabled by command line."
			;;
		*)
			action=${1}
			shift
			break
			;;
	esac
	shift
done

export DEBUG TOOLCHAIN

function package() {
	local action=${1}
	shift

	case "${action}" in
		dependencies|deps)
			echo -e "${BOLD}Build dependencies:${NORMAL} $(package_build_dependencies $@ | tr '\n' ' ')"
			echo -e "${BOLD}Dependencies:${NORMAL}       $(package_runtime_dependencies $@ | tr '\n' ' ')"
			;;
		find)
			find_package $@
			;;
		is_built)
			if package_is_built $(find_package $@); then
				echo "Package is built."
				return 0
			else
				echo "Package is NOT built."
				return 1
			fi
			;;
		list)
			package_list
			;;
		packages)
			package_packages $(find_package $@)
			;;
		profile|info)
			package_profile $(find_package $@)
			;;
		_info)
			package_info $(find_package $@)
			;;
	esac
}

case "${action}" in
	all)
		for pkg in $(${NAOKI} tree); do
			echo "${pkg}:"
			package is_built ${pkg} && continue
			${NAOKI} build ${pkg} || break
		done
		;;
	build)
		${NAOKI} build $@
		;;
	package|pkg)
		package $@
		;;
	toolchain)
		TOOLCHAIN=1
		${NAOKI} --toolchain tree
		;;
	toolchain_build)
		for i in $($0 toolchain); do
			${NAOKI} --toolchain toolchain ${i}
		done
		;;
	tree)
		${NAOKI} tree
		;;
	random)
		pkgs=$(package_list)
		while true; do
			if [ -z "${pkgs}" ]; then
				break
			fi

			pkgs=$(package_random ${pkgs})
			pkg=$(awk '{print $NF }' <<<${pkgs})

			${NAOKI} build ${pkg}

			pkgs=$(listremove ${pkg} ${pkgs})
		done
		;;
esac
