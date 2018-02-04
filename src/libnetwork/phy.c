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
#include <stdio.h>
#include <stdlib.h>

#include <network/libnetwork.h>
#include <network/logging.h>
#include "libnetwork-private.h"

struct network_phy {
	struct network_ctx* ctx;
	int refcount;

	int index;
	char* name;
};

static int phy_get_index(const char* name) {
	char path[1024];
	char index[8];

	snprintf(path, sizeof(path), "/sys/class/ieee80211/%s/index", name);

	FILE* f = fopen(path, "r");
	if (!f)
		return -1;

	int p = fread(index, 1, sizeof(index), f);
	if (p < 0) {
		fclose(f);
		return -1;
	}

	// Terminate buffer
	index[p] = '\0';
	fclose(f);

	return atoi(index);
}

NETWORK_EXPORT int network_phy_new(struct network_ctx* ctx, struct network_phy** phy,
		const char* name) {
	if (!name)
		return -EINVAL;

	int index = phy_get_index(name);
	if (index < 0)
		return -ENODEV;

	struct network_phy* p = calloc(1, sizeof(*p));
	if (!p)
		return -ENOMEM;

	// Initalise object
	p->ctx = network_ref(ctx);
	p->refcount = 1;

	DEBUG(p->ctx, "Allocated phy at %p\n", p);
	*phy = p;
	return 0;
}

NETWORK_EXPORT struct network_phy* network_phy_ref(struct network_phy* phy) {
	if (!phy)
		return NULL;

	phy->refcount++;
	return phy;
}

static void network_phy_free(struct network_phy* phy) {
	DEBUG(phy->ctx, "Releasing phy at %p\n", phy);

	if (phy->name)
		free(phy->name);

	network_unref(phy->ctx);
	free(phy);
}

NETWORK_EXPORT struct network_phy* network_phy_unref(struct network_phy* phy) {
	if (!phy)
		return NULL;

	if (--phy->refcount > 0)
		return phy;

	network_phy_free(phy);
	return NULL;
}
