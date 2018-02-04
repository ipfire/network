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

#include <errno.h>
#include <net/if.h>
#include <stdlib.h>
#include <string.h>

#include <network/interface.h>
#include <network/libnetwork.h>
#include <network/logging.h>
#include "libnetwork-private.h"

struct network_interface {
	struct network_ctx* ctx;
	int refcount;

	unsigned int index;
	char* name;
};

NETWORK_EXPORT int network_interface_new(struct network_ctx* ctx,
		struct network_interface** intf, const char* name) {
	if (!name)
		return -EINVAL;

	unsigned int index = if_nametoindex(name);
	if (!index) {
		ERROR(ctx, "Could not find interface %s\n", name);
		return -ENODEV;
	}

	struct network_interface* i = calloc(1, sizeof(*i));
	if (!i)
		return -ENOMEM;

	// Initialise object
	i->ctx = network_ref(ctx);
	i->refcount = 1;
	i->index = index;
	i->name = strdup(name);

	DEBUG(i->ctx, "Allocated network interface at %p\n", i);

	*intf = i;
	return 0;
}

NETWORK_EXPORT struct network_interface* network_interface_ref(struct network_interface* intf) {
	if (!intf)
		return NULL;

	intf->refcount++;
	return intf;
}

static void network_interface_free(struct network_interface* intf) {
	DEBUG(intf->ctx, "Released network interface at %p\n", intf);

	if (intf->name)
		free(intf->name);

	network_unref(intf->ctx);
	free(intf);
}

NETWORK_EXPORT struct network_interface* network_interface_unref(struct network_interface* intf) {
	if (!intf)
		return NULL;

	if (--intf->refcount > 0)
		return intf;

	network_interface_free(intf);
	return NULL;
}

NETWORK_EXPORT const char* network_interface_get_name(struct network_interface* intf) {
	return intf->name;
}
