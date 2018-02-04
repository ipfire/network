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

#ifndef LIBNETWORK_H
#define LIBNETWORK_H

#include <stdarg.h>

// Central context for all network operations
struct network_ctx;

int network_new(struct network_ctx** ctx);
struct network_ctx* network_ref(struct network_ctx* ctx);
struct network_ctx* network_unref(struct network_ctx* ctx);

void network_set_log_fn(struct network_ctx* ctx,
	void (*log_fn)(struct network_ctx* ctx, int priority, const char* file,
	int line, const char* fn, const char* format, va_list args));
int network_get_log_priority(struct network_ctx* ctx);
void network_set_log_priority(struct network_ctx* ctx, int priority);

const char* network_version();

#ifdef NETWORK_PRIVATE

void network_log(struct network_ctx* ctx,
	int priority, const char* file, int line, const char* fn,
	const char* format, ...);

#endif

#endif
