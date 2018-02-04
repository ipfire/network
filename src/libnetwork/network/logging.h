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

#ifndef NETWORK_LOGGING_H
#define NETWORK_LOGGING_H

#ifdef NETWORK_PRIVATE

#include <stdlib.h>
#include <syslog.h>

#include <network/libnetwork.h>

static inline void __attribute__((always_inline, format(printf, 2, 3)))
    network_log_null(struct network_ctx* ctx, const char* format, ...) {}

#define network_log_cond(ctx, prio, arg...) \
    do { \
        if (network_get_log_priority(ctx) >= prio) \
            network_log(ctx, prio, __FILE__, __LINE__, __FUNCTION__, ## arg); \
    } while (0)

#ifdef ENABLE_DEBUG
#  define DEBUG(ctx, arg...) network_log_cond(ctx, LOG_DEBUG, ## arg)
#else
#  define DEBUG(ctx, arg...) network_log_null(ctx, ## arg)
#endif

#define INFO(ctx, arg...) network_log_cond(ctx, LOG_INFO, ## arg)
#define ERROR(ctx, arg...) network_log_cond(ctx, LOG_ERR, ## arg)

#ifndef HAVE_SECURE_GETENV
#  ifdef HAVE___SECURE_GETENV
#    define secure_getenv __secure_getenv
#  else
#    error neither secure_getenv nor __secure_getenv is available
#  endif
#endif

#endif

#endif /* NETWORK_LOGGING_H */
