/*#############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2018 IPFire Network Development Team                          #
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
#############################################################################*/

#ifndef NETWORK_INTERFACE_H
#define NETWORK_INTERFACE_H

#include <network/libnetwork.h>

struct network_interface;

int network_interface_new(struct network_ctx* ctx,
	struct network_interface** intf, const char* name);

struct network_interface* network_interface_ref(struct network_interface* intf);
struct network_interface* network_interface_unref(struct network_interface* intf);

const char* network_interface_get_name(struct network_interface* intf);

#endif /* NETWORK_INTERFACE_H */
