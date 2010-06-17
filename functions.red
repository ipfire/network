#!/bin/bash
###############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2010  Michael Tremer & Christian Schmidt                      #
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

function red_db_path() {
	local zone=${1}

	echo "${RED_DB_DIR}/${zone}"
}

function red_db_exists() {
	local zone=${1}

	[ -d "$(red_db_path ${zone})" ]
}

function red_db_create() {
	local zone=${1}

	red_db_exists ${zone} && return ${EXIT_OK}

	mkdir -p $(red_db_path ${zone})
}

function red_db_remove() {
	local zone=${1}

	[ -z "${zone}" ] && return ${EXIT_ERROR}

	rm -rf ${RED_DB_DIR}
}

function red_db_set() {
	local zone=${1}
	local parameter=${2}
	shift 2

	local value="$@"

	red_db_create ${zone}

	echo "${value}" > $(red_db_path ${zone})/${parameter}
}

function red_db_get() {
	local zone=${1}
	local parameter=${2}
	shift 2

	cat $(red_db_path ${zone})/${parameter} 2>/dev/null
}

function red_db_from_ppp() {
	local zone=${1}

	# Save ppp configuration
	red_db_set ${zone} type "ppp"
	red_db_set ${zone} local-ip-address ${PPP_IPLOCAL}
	red_db_set ${zone} remote-ip-address ${PPP_IPREMOTE}

	red_db_set ${zone} dns ${PPP_DNS1} ${PPP_DNS2}

	red_db_set ${zone} remote-address ${PPP_MACREMOTE,,}
}

function red_routing_update() {
	local zone=${1}

	local table=${zone}

	# Create routing table if not exists
	routing_table_create ${table}

	local remote_ip_address=$(red_db_get ${zone} remote-ip-address)
	local local_ip_address=$(red_db_get ${zone} local-ip-address)

	ip route replace table ${table} default nexthop via ${remote_ip_address}

	ip rule add from ${local_ip_address} lookup ${table}
}
