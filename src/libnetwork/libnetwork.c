/*#############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2017 IPFire Network Development Team                          #
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
#include <stdlib.h>

#include <network/libnetwork.h>
#include "libnetwork-private.h"

struct network_ctx {
	int refcount;
};

NETWORK_EXPORT int network_new(struct network_ctx** ctx) {
	struct network_ctx* c = calloc(1, sizeof(*c));
	if (!c)
		return -ENOMEM;

	// Initialise basic variables
	c->refcount = 1;

	*ctx = c;
	return 0;
}

NETWORK_EXPORT struct network_ctx* network_ref(struct network_ctx* ctx) {
	if (!ctx)
		return NULL;

	ctx->refcount++;
	return ctx;
}

static void network_free(struct network_ctx* ctx) {
	// Nothing to do, yet
}

NETWORK_EXPORT struct network_ctx* network_unref(struct network_ctx* ctx) {
	if (!ctx)
		return NULL;

	if (--ctx->refcount > 0)
		return ctx;

	network_free(ctx);
	return NULL;
}

NETWORK_EXPORT const char* network_version() {
	return "network " VERSION;
}
