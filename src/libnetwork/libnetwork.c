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
#include <linux/netlink.h>
#include <linux/nl80211.h>
#include <netlink/genl/ctrl.h>
#include <netlink/genl/genl.h>
#include <netlink/netlink.h>
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

	// Netlink
	struct nl_sock* nl_socket;
	int nl80211_id;
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

static int init_netlink(struct network_ctx* ctx) {
	// Allocate netlink socket
	ctx->nl_socket = nl_socket_alloc();
	if (!ctx->nl_socket) {
		ERROR(ctx, "Failed to allocate netlink socket\n");
		return -ENOMEM;
	}

	// Connect the socket
	if (genl_connect(ctx->nl_socket)) {
		ERROR(ctx, "Failed to connect to generic netlink");
		return -ENOLINK;
	}

	// Set buffer size
	nl_socket_set_buffer_size(ctx->nl_socket, 8192, 8192);

	// Register socket callback
	struct nl_cb* callback = nl_cb_alloc(NL_CB_DEFAULT);
	if (!callback) {
		ERROR(ctx, "Could not allocate socket callback\n");
		return -ENOMEM;
	}

	nl_socket_set_cb(ctx->nl_socket, callback);

	// Get nl80211 id
	ctx->nl80211_id = genl_ctrl_resolve(ctx->nl_socket, "nl80211");
	if (ctx->nl80211_id < 0) {
		ERROR(ctx, "Could not find nl80211\n");
		return -ENOENT;
	}

	return 0;
}

static void network_free(struct network_ctx* ctx) {
	DEBUG(ctx, "network ctx %p released\n", ctx);

	// Free netlink socket
	if (ctx->nl_socket)
		nl_socket_free(ctx->nl_socket);

	free(ctx);
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

	// Initiate netlink connection
	int r = init_netlink(c);
	if (r) {
		network_free(c);
		return r;
	}

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

// Creates a netlink message that can be sent with network_send_netlink_message
struct nl_msg* network_make_netlink_message(struct network_ctx* ctx,
		enum nl80211_commands cmd, int flags) {
	// Allocate message
	struct nl_msg* msg = nlmsg_alloc();
	if (!msg)
		return NULL;

	genlmsg_put(msg, 0, 0, ctx->nl80211_id, 0, flags, cmd, 0);

	DEBUG(ctx, "Created new netlink message %p\n", msg);

	return msg;
}

struct network_netlink_message_status {
	struct network_ctx* ctx;
	int r;
};

static int __nl_ack_handler(struct nl_msg* msg, void* data) {
	struct network_netlink_message_status* status = data;
	status->r = 0;

	return NL_STOP;
}

static int __nl_finish_handler(struct nl_msg* msg, void* data) {
	struct network_netlink_message_status* status = data;
	status->r = 0;

	return NL_SKIP;
}

static int __nl_error_handler(struct sockaddr_nl* nla, struct nlmsgerr* err, void* data) {
	struct network_netlink_message_status* status = data;
	status->r = 0;

	struct nlattr *attrs;
	struct nlattr *tb[NLMSGERR_ATTR_MAX + 1];
	struct nlmsghdr* nlh = (struct nlmsghdr*)err - 1;

	size_t len = nlh->nlmsg_len;
	size_t ack_len = sizeof(*nlh) + sizeof(int) + sizeof(*nlh);

	status->r = err->error;
	if (!(nlh->nlmsg_flags & NLM_F_ACK_TLVS))
		return NL_STOP;

	if (!(nlh->nlmsg_flags & NLM_F_CAPPED))
		ack_len += err->msg.nlmsg_len - sizeof(*nlh);

	if (len <= ack_len)
		return NL_STOP;

	attrs = (void *)((unsigned char *)nlh + ack_len);
	len -= ack_len;

	nla_parse(tb, NLMSGERR_ATTR_MAX, attrs, len, NULL);
	if (tb[NLMSGERR_ATTR_MSG]) {
		len = strnlen((char *)nla_data(tb[NLMSGERR_ATTR_MSG]),
			      nla_len(tb[NLMSGERR_ATTR_MSG]));

		ERROR(status->ctx, "Kernel reports: %*s\n", len,
			(const char *)nla_data(tb[NLMSGERR_ATTR_MSG]));
	}

	return NL_STOP;
}

// Sends a netlink message and calls the handler to handle the result
int network_send_netlink_message(struct network_ctx* ctx, struct nl_msg* msg,
		int(*handler)(struct nl_msg* msg, void* data), void* data) {
	struct network_netlink_message_status status;
	status.ctx = ctx;

	DEBUG(ctx, "Sending netlink message %p\n", msg);

	// Sending the message
	status.r = nl_send_auto(ctx->nl_socket, msg);
	if (status.r < 0) {
		ERROR(ctx, "Error sending netlink message: %d\n", status.r);
		return status.r;
	}

	// Register callback
	struct nl_cb* callback = nl_cb_alloc(NL_CB_DEFAULT);
	if (!callback) {
		ERROR(ctx, "Could not allocate callback\n");
		nlmsg_free(msg);

		return -1;
	}

	status.r = 1;

	nl_cb_set(callback, NL_CB_VALID, NL_CB_CUSTOM, handler, data);
	nl_cb_set(callback, NL_CB_ACK, NL_CB_CUSTOM, __nl_ack_handler, &status);
	nl_cb_set(callback, NL_CB_FINISH, NL_CB_CUSTOM, __nl_finish_handler, &status);
	nl_cb_err(callback, NL_CB_CUSTOM, __nl_error_handler, &status);

	while (status.r > 0)
		nl_recvmsgs(ctx->nl_socket, callback);

	DEBUG(ctx, "Netlink message returned with status %d\n", status.r);

	return status.r;
}
