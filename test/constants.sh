#!/bin/bash

INVALID_IPv4_NETWORKS=(
        2001:470:1f09:1249::
        2001:470:1f09:1249::/256
        2001:470:1f09:1249::/-20
        2001:470:6ef3::
        192.168.101.0/224
        192.168.190.0/-23
        1.2.3.X/abc
        1.2.3.4/33
        a.b.c.d/24
        a.b.c.d/e
        1.2.3.4/e
)

INVALID_IPv6_NETWORKS=(
        192.168.101.0/24
	192.168.190.0/23
	1.2.3.X/abc
        1.2.3.4/33
        a.b.c.d/24
        a.b.c.d/e
        1.2.3.4/e
        2001:470:1f09:1249::
        2001:470:1f09:1249::/256
        2001:470:1f09:1249::/-20
	2001:470:6ef3::
)


INVALID_NETWORKS=(
	1.2.3.X/abc
	1.2.3.4/33
	a.b.c.d/24
	a.b.c.d/e
	1.2.3.4/e
	2001:470:6ef3::
	2001:470:1f09:1249::
	2001:470:1f09:1249::/256
	2001:470:1f09:1249::/-20
	1.2.3.4/33
	1.2.3.4/-33
	192.168.106.1
	8.8.8.8
)


VALID_IPv4_NETWORKS=(
        1.2.3.4/24
        192.168.101.0/24
        1.2.3.4/32
)

VALID_IPv6_NETWORKS=(
        2001:470:1f09:1249::/64
        2001:470:6ef3::/48
)

VALID_NETWORKS=( "${VALID_IPv4_NETWORKS[@]}" "${VALID_IPv6_NETWORKS[@]}")



VALID_IPv4_ADDRESSES=(
	12.3.4.5/32
	192.168.101.254
	127.0.0.1
)

VALID_IPv6_ADDRESSES=(
	2001:470:1f08:1249::2
	2001:470:1f08:1249::1
	::1

)

# We can merge these two array because bot of them conatin only vaild IP adresses
VALID_ADDRESSES=("${VALID_IPv4_ADDRESSES[@]}" "${VALID_IPv6_ADDRESSES[@]}")



INVALID_IPv4_ADDRESSES=(
	1.2.3.X/abc
	a.b.c.d/24
	a.b.c.d/e
	1.2.3.500
	1.2.3.4/33
	1.2.3.4/e
	::1
	2001:470:1f08:1249::2
	2001:470:1f08:1249::1
)


INVALID_IPv6_ADDRESSES=(
	1200::AB00:1234::2552:7777:1313
	1200:0000:AB00:1234:O000:2552:7777:1313
	127.0.0.0.1
	"::1/256"
	
)

# we cannot just merge the 2 array above because 127.0.0.0.1 is a valid IPv4 addresse but an invalid IPv6 address
INVALID_ADDRESSES=(
        1200::AB00:1234::2552:7777:1313
        1200:0000:AB00:1234:O000:2552:7777:1313
        "::1/256"
        1.2.3.X/abc
        a.b.c.d/24
        a.b.c.d/e
        1.2.3.500
        1.2.3.4/33
        1.2.3.4/e
)

IP_TEST_SUPPORTED_PROTOCOLS=(
	ipv4
	ipv6
)

IP_TEST_UNSUPPORTED_PROTOCOLS=(
	""
	ipb6
	ipc6
	upv6
	ipb4
        ipc4
        upv4
)
