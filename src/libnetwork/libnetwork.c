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

#include <ctype.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#include <network/libnetwork.h>
#include <network/logging.h>
#include "libnetwork-private.h"

struct network_ctx {
	int refcount;

	// Logging
	void (*log_fn)(struct network_ctx* ctx,
		int priority, const char *file, int line, const char *fn,
		const char *format, va_list args);
	int log_priority;
};

void network_log(struct network_ctx* ctx,
		int priority, const char* file, int line, const char* fn,
		const char* format, ...) {
	va_list args;

	va_start(args, format);
	ctx->log_fn(ctx, priority, file, line, fn, format, args);
	va_end(args);
}

static void log_stderr(struct network_ctx* ctx,
		int priority, const char* file, int line, const char* fn,
		const char* format, va_list args) {
	fprintf(stderr, "libnetwork: %s: ", fn);
	vfprintf(stderr, format, args);
}

static int log_priority(const char* priority) {
	char *endptr;

	int prio = strtol(priority, &endptr, 10);

	if (endptr[0] == '\0' || isspace(endptr[0]))
		return prio;

	if (strncmp(priority, "err", 3) == 0)
		return LOG_ERR;

	if (strncmp(priority, "info", 4) == 0)
		return LOG_INFO;

	if (strncmp(priority, "debug", 5) == 0)
		return LOG_DEBUG;

	return 0;
}

NETWORK_EXPORT int network_new(struct network_ctx** ctx) {
	struct network_ctx* c = calloc(1, sizeof(*c));
	if (!c)
		return -ENOMEM;

	// Initialise basic variables
	c->refcount = 1;

	// Initialise logging
	c->log_fn = log_stderr;
	c->log_priority = LOG_ERR;

	const char* env = secure_getenv("NETWORK_LOG");
	if (env)
		network_set_log_priority(c, log_priority(env));

	INFO(c, "network ctx %p created\n", c);
	DEBUG(c, "log_priority=%d\n", c->log_priority);

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
	DEBUG(ctx, "network ctx %p released\n", ctx);

	free(ctx);
}

NETWORK_EXPORT struct network_ctx* network_unref(struct network_ctx* ctx) {
	if (!ctx)
		return NULL;

	if (--ctx->refcount > 0)
		return ctx;

	network_free(ctx);
	return NULL;
}

NETWORK_EXPORT void network_set_log_fn(struct network_ctx* ctx,
		void (*log_fn)(struct network_ctx* ctx, int priority, const char* file,
		int line, const char* fn, const char* format, va_list args)) {
	ctx->log_fn = log_fn;
	INFO(ctx, "custom logging function %p registered\n", log_fn);
}

NETWORK_EXPORT int network_get_log_priority(struct network_ctx* ctx) {
	return ctx->log_priority;
}

NETWORK_EXPORT void network_set_log_priority(struct network_ctx* ctx, int priority) {
	ctx->log_priority = priority;
}

NETWORK_EXPORT const char* network_version() {
	return "network " VERSION;
}
