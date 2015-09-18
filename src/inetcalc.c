/*#############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2015 IPFire Network Development Team                          #
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

#include <assert.h>
#include <arpa/inet.h>
#include <errno.h>
#include <getopt.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>

typedef struct ip_address {
	int family;
	__uint128_t addr;
	int prefix;
} ip_address_t;

static __uint128_t prefix_to_bitmask(int prefix) {
	__uint128_t bitmask = ~0;

	for (int i = 0; i < 128 - prefix; i++)
		bitmask >>= 1;

	return bitmask;	
}

static int bitmask_to_prefix(uint32_t bits) {
	int prefix = 0;

	// Count all ones until we find the first zero
	while (bits & (1 << 31)) {
		bits <<= 1;
		prefix++;
	}

	// The remaining bits must all be zero
	if (bits)
		return -1;

	return prefix;
}

static int ip_address_parse_subnet_mask(ip_address_t* ip, const char* prefix) {
	struct in_addr mask;

	int r = inet_pton(AF_INET, prefix, &mask.s_addr);
	if (r != 1)
		return 1;

	uint32_t bits = ntohl(mask.s_addr);
	ip->prefix = bitmask_to_prefix(bits);

	return (ip->prefix < 0 || ip->prefix > 32);
}

static int ip_address_parse_prefix_cidr(ip_address_t* ip, const int family, const char* prefix) {
	ip->prefix = 0;
	while (*prefix) {
		char p = *prefix++;

		if (p >= '0' && p <= '9') {
			ip->prefix *= 10;
			ip->prefix += p - '0';
		} else {
			return 1;
		}
	}

	switch (family) {
		case AF_INET6:
			return (ip->prefix < 0 || ip->prefix > 128);

		case AF_INET:
			return (ip->prefix < 0 || ip->prefix > 32);

		default:
			return 1;
	}
}

static int ip_address_parse_prefix(ip_address_t* ip, const int family, const char* prefix) {
	int r = ip_address_parse_prefix_cidr(ip, family, prefix);

	if (r && family == AF_INET) {
		r = ip_address_parse_subnet_mask(ip, prefix);
	}

	return r;
}

static int ip_address_parse_simple(ip_address_t* ip, const int family, const char* address) {
	assert(family == AF_INET || family == AF_INET6);

	size_t address_length = strlen(address);
	char buffer[address_length + 1];
	strncpy(buffer, address, sizeof(buffer));

	// Search for a prefix or subnet mask
	char* prefix = strchr(buffer, '/');
	if (prefix) {
		buffer[prefix - buffer] = '\0';
		prefix++;
	}

	memset(&ip->addr, 0, sizeof(ip->addr));
	int r = inet_pton(family, buffer, &ip->addr);

	switch (r) {
		// If parsing the IP address failed, we will return false
		case 0:
			return 1;

		// If the IP address could be successfully parsed, we will
		// save the address family and return true
		case 1:
			ip->family = family;
			r = 0;
			break;

		default:
			return r;
	}

	if (prefix)
		r = ip_address_parse_prefix(ip, family, prefix);
	else
		ip->prefix = -1;

	return r;
}

static int ip_address_parse(ip_address_t* ip, const int family, const char* address) {
	static int families[] = { AF_INET, AF_INET6, 0 };

	int r = 1;
	int* f = families;
	while (*f) {
		if (family == AF_UNSPEC || family == *f) {
			r = ip_address_parse_simple(ip, *f, address);

			if (r == 0)
				break;
		}

		f++;
	}

	return r;
}

static int ip_address_eq(const ip_address_t* a1, const ip_address_t* a2) {
	if (a1->family != a2->family)
		return 1;

	if (a1->addr != a2->addr)
		return 1;

	if (a1->prefix != a2->prefix)
		return 1;

	return 0;
}

static int ip_address_gt(const ip_address_t* a1, const ip_address_t* a2) {
	if (a1->family != a2->family || a1->prefix != a2->prefix)
		return -1;

	if (a1->addr > a2->addr)
		return 0;

	return 1;
}

static int ip_address_format_string(char* buffer, size_t size, const ip_address_t* ip) {
	assert(ip->family == AF_INET || ip->family == AF_INET6);

	const char* p = inet_ntop(ip->family, &ip->addr, buffer, size);
	if (!p)
		return errno;

	return 0;
}

static void ip_address_print(const ip_address_t* ip) {
	char buffer[INET6_ADDRSTRLEN+4];

	int r = ip_address_format_string(buffer, sizeof(buffer), ip);
	if (r)
		return;

	if (ip->prefix >= 0) {
		size_t len = strlen(buffer);
		snprintf(buffer + len, sizeof(buffer) - len, "/%d", ip->prefix);
	}

	printf("%s\n", buffer);
}

static void ip_address_make_network(ip_address_t* net, const ip_address_t* ip) {
	assert(ip->prefix >= 0);

	__uint128_t mask = prefix_to_bitmask(ip->prefix);

	net->family = ip->family;
	net->prefix = ip->prefix;
	net->addr = ip->addr & mask;
}

static void ip_address_make_broadcast(ip_address_t* broadcast, const ip_address_t* ip) {
	assert(ip->family == AF_INET && ip->prefix >= 0);

	__uint128_t mask = prefix_to_bitmask(ip->prefix);

	broadcast->family = ip->family;
	broadcast->prefix = ip->prefix;
	broadcast->addr = ip->addr | ~mask;
}

static int action_check(const int family, const char* address) {
	ip_address_t ip;

	int r = ip_address_parse(&ip, family, address);
	if (r)
		return r;

	// No prefix allowed
	return (ip.prefix >= 0);
}

static int action_equal(const int family, const char* addr1, const char* addr2) {
	ip_address_t a1;
	ip_address_t a2;
	int r;

	r = ip_address_parse(&a1, family, addr1);
	if (r)
		return 2;

	r = ip_address_parse(&a2, family, addr2);
	if (r)
		return 2;

	return ip_address_eq(&a1, &a2);
}

static int action_greater(const int family, const char* addr1, const char* addr2) {
	ip_address_t a1;
	ip_address_t a2;
	int r;

	r = ip_address_parse(&a1, family, addr1);
	if (r)
		return 2;

	r = ip_address_parse(&a2, family, addr2);
	if (r)
		return 2;

	return ip_address_gt(&a1, &a2);
}

static int action_format(const int family, const char* address) {
	ip_address_t ip;

	int r = ip_address_parse(&ip, family, address);
	if (r)
		return r;

	ip_address_print(&ip);
	return 0;
}

static int action_broadcast(const int family, const char* address) {
	ip_address_t ip;
	int r = ip_address_parse(&ip, family, address);
	if (r) {
		fprintf(stderr, "Invalid IP address: %s\n", address);
		return r;
	}

	if (ip.family != AF_INET) {
		fprintf(stderr, "This is only possible for IPv4\n");
		return 1;
	}

	ip_address_t broadcast;
	ip_address_make_broadcast(&broadcast, &ip);

	ip_address_print(&broadcast);
	return 0;
}

static int action_network(const int family, const char* address) {
	ip_address_t ip;

	int r = ip_address_parse(&ip, family, address);
	if (r) {
		fprintf(stderr, "Invalid IP address: %s\n", address);
		return r;
	}

	ip_address_t network;
	ip_address_make_network(&network, &ip);

	ip_address_print(&network);
	return 0;
}

static int action_prefix(const int family, const char* addr1, const char* addr2) {
	int r;

	ip_address_t network;
	r = ip_address_parse(&network, family, addr1);
	if (r)
		return r;

	ip_address_t broadcast;
	r = ip_address_parse(&broadcast, family, addr2);
	if (r)
		return r;

	r = ip_address_gt(&broadcast, &network);
	if (r)
		return r;

	uint32_t mask = ntohl(network.addr ^ broadcast.addr);
	int prefix = bitmask_to_prefix(~mask);
	if (prefix < 0)
		return 1;

	printf("%d\n", prefix);
	return 0;
}

enum actions {
	AC_UNSPEC = 0,
	AC_BROADCAST,
	AC_CHECK,
	AC_EQUAL,
	AC_FORMAT,
	AC_GREATER,
	AC_NETWORK,
	AC_PREFIX,
};

static void set_action(int* action, int what) {
	if (*action != AC_UNSPEC) {
		printf("Another action has already been selected\n");
		exit(1);
	}

	*action = what;		
}

static struct option long_options[] = {
	{"broadcast",         no_argument,       0, 'b'},
	{"check",             no_argument,       0, 'c'},
	{"equal",             no_argument,       0, 'e'},
	{"format",            no_argument,       0, 'f'},
	{"greater",           no_argument,       0, 'g'},
	{"ipv4-only",         no_argument,       0, '4'},
	{"ipv6-only",         no_argument,       0, '6'},
	{"network",           no_argument,       0, 'n'},
	{"prefix",            no_argument,       0, 'p'},
	{"verbose",           no_argument,       0, 'v'},
	{0, 0, 0, 0}
};

int main(int argc, char** argv) {
	int option_index = 0;
	int required_arguments = 0;

	int verbose = 0;
	int action = AC_UNSPEC;
	int family = AF_UNSPEC;

	while (1) {
		int c = getopt_long(argc, argv, "46bcefgnpv", long_options, &option_index);
		if (c == -1)
			break;

		switch (c) {
			case 0:
				if (long_options[option_index].flag != 0)
					break;

				printf("option: %s", long_options[option_index].name);
				if (optarg)
					printf(" with arg %s", optarg);
				printf("\n");
				break;

			case '4':
				family = AF_INET;
				break;

			case '6':
				family = AF_INET6;
				break;

			case 'b':
				set_action(&action, AC_BROADCAST);
				required_arguments = 1;
				break;

			case 'c':
				set_action(&action, AC_CHECK);
				required_arguments = 1;
				break;

			case 'e':
				set_action(&action, AC_EQUAL);
				required_arguments = 2;
				break;

			case 'f':
				set_action(&action, AC_FORMAT);
				required_arguments = 1;
				break;

			case 'g':
				set_action(&action, AC_GREATER);
				required_arguments = 2;
				break;

			case 'n':
				set_action(&action, AC_NETWORK);
				required_arguments = 1;
				break;

			case 'p':
				set_action(&action, AC_PREFIX);
				required_arguments = 2;
				break;

			case 'v':
				verbose = 1;
				break;

			case '?':
				break;

			default:
				abort();
		}
	}

	while (optind--) {
		argc--;
		argv++;
	}

	if (argc != required_arguments) {
		fprintf(stderr, "Invalid number of arguments. Got %d, required %d.\n",
			argc, required_arguments);
		return 1;
	}

	if (verbose && family != AF_UNSPEC)
		printf("Address family = %d\n", family);

	int r = 0;

	switch (action) {
		case AC_UNSPEC:
			printf("No action specified\n");
			r = 1;
			break;

		case AC_BROADCAST:
			r = action_broadcast(family, argv[0]);
			break;

		case AC_CHECK:
			r = action_check(family, argv[0]);

			if (verbose) {
				if (r == 0)
					printf("%s is a valid IP address\n", argv[0]);
				else
					printf("%s is not a valid IP address\n", argv[0]);
			}
			break;

		case AC_EQUAL:
			r = action_equal(family, argv[0], argv[1]);

			if (verbose) {
				if (r == 0)
					printf("%s equals %s\n", argv[0], argv[1]);
				else if (r == 2)
					printf("Invalid IP address provided\n");
				else
					printf("%s does not equal %s\n", argv[0], argv[1]); 
			}
			break;

		case AC_FORMAT:
			r = action_format(family, argv[0]);

			if (verbose && r)
				printf("Invalid IP address given\n");

			break;

		case AC_GREATER:
			r = action_greater(family, argv[0], argv[1]);

			if (verbose) {
				if (r == 0)
					printf("%s is greater than %s\n", argv[0], argv[1]);
				else if (r == 2)
					printf("Invalid IP address provided\n");
				else
					printf("%s is not greater than %s\n", argv[0], argv[1]);
			}
			break;

		case AC_NETWORK:
			r = action_network(family, argv[0]);
			break;

		case AC_PREFIX:
			r = action_prefix(family, argv[0], argv[1]);
			break;
	}

	return r;
}
