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
#include <linux/nl80211.h>
#include <netlink/attr.h>
#include <netlink/genl/genl.h>
#include <netlink/msg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/queue.h>

#include <network/libnetwork.h>
#include <network/logging.h>
#include <network/phy.h>
#include "libnetwork-private.h"

struct network_phy_channel {
	unsigned int number;
	unsigned int frequency;
	bool dfs;
	double max_tx_power; // dBm

	TAILQ_ENTRY(network_phy_channel) channels;
};

struct network_phy {
	struct network_ctx* ctx;
	int refcount;

	int index;
	char* name;

	TAILQ_HEAD(head, network_phy_channel) channels;

	enum network_phy_ciphers ciphers;
	ssize_t max_mpdu_length;
	unsigned int vht_caps;
	unsigned int ht_caps;
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

static void phy_parse_ciphers(struct network_phy* phy, __u32* ciphers, int num) {
	enum network_phy_ciphers cipher;

	// Reset value
	phy->ciphers = 0;

	for (int i = 0; i < num; i++) {
		switch (ciphers[i]) {
			case 0x000fac01:
				cipher = NETWORK_PHY_CIPHER_WEP40;
				break;

			case 0x000fac02:
				cipher = NETWORK_PHY_CIPHER_TKIP;
				break;

			case 0x000fac04:
				cipher = NETWORK_PHY_CIPHER_CCMP128;
				break;

			case 0x000fac05:
				cipher = NETWORK_PHY_CIPHER_WEP104;
				break;

			case 0x000fac06:
				cipher = NETWORK_PHY_CIPHER_CMAC128;
				break;

			case 0x000fac08:
				cipher = NETWORK_PHY_CIPHER_GCMP128;
				break;

			case 0x000fac09:
				cipher = NETWORK_PHY_CIPHER_GCMP256;
				break;

			/*
				I have no idea what these are. My card reports them but
				I could not find out anything about them.
			*/
			case 0x000fac0a:
			case 0x000fac0b:
			case 0x000fac0c:
			case 0x000fac0d:
				continue;

			case 0x000fac10:
				cipher = NETWORK_PHY_CIPHER_CCMP256;
				break;

			case 0x000fac11:
				cipher = NETWORK_PHY_CIPHER_GMAC128;
				break;

			case 0x000fac12:
				cipher = NETWORK_PHY_CIPHER_GMAC256;
				break;

			case 0x000fac13:
				cipher = NETWORK_PHY_CIPHER_CMAC256;
				break;

			case 0x00147201:
				cipher = NETWORK_PHY_CIPHER_WPISMS4;
				break;

			default:
				ERROR(phy->ctx, "Unknown cipher found: %x\n", ciphers[i]);
				continue;
		}

		phy->ciphers |= cipher;
	}
}

static void phy_parse_vht_capabilities(struct network_phy* phy, __u32 caps) {
	// Max MPDU length
	switch (caps & 0x3) {
		case 0:
			phy->max_mpdu_length = 3895;
			break;

		case 1:
			phy->max_mpdu_length = 7991;
			break;

		case 2:
			phy->max_mpdu_length = 11454;
			break;

		case 3:
			phy->max_mpdu_length = -1;
	}

	// Supported channel widths
	switch ((caps >> 2) & 0x3) {
		case 0:
			break;

		// Supports 160 MHz
		case 1:
			phy->vht_caps |= NETWORK_PHY_VHT_CAP_VHT160;
			break;

		// Supports 160 MHz and 80+80 MHz
		case 2:
			phy->vht_caps |= NETWORK_PHY_VHT_CAP_VHT160;
			phy->vht_caps |= NETWORK_PHY_VHT_CAP_VHT80PLUS80;
			break;
	}

	// RX LDPC
	if (caps & BIT(4))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_RX_LDPC;

	// RX Short GI 80 MHz
	if (caps & BIT(5))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_RX_SHORT_GI_80;

	// RX Short GI 160 MHz and 80+80 MHz
	if (caps & BIT(6))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_RX_SHORT_GI_160;

	// TX STBC
	if (caps & BIT(7))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_TX_STBC;

	// Single User Beamformer
	if (caps & BIT(11))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_SU_BEAMFORMER;

	// Single User Beamformee
	if (caps & BIT(12))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_SU_BEAMFORMEE;

	// Multi User Beamformer
	if (caps & BIT(19))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_MU_BEAMFORMER;

	// Multi User Beamformee
	if (caps & BIT(20))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_MU_BEAMFORMEE;

	// TX-OP-PS
	if (caps & BIT(21))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_TXOP_PS;

	// HTC-VHT
	if (caps & BIT(22))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_HTC_VHT;

	// RX Antenna Pattern Consistency
	if (caps & BIT(28))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_RX_ANTENNA_PATTERN;

	// TX Antenna Pattern Consistency
	if (caps & BIT(29))
		phy->vht_caps |= NETWORK_PHY_VHT_CAP_TX_ANTENNA_PATTERN;
}

static void phy_parse_ht_capabilities(struct network_phy* phy, __u16 caps) {
	// RX LDPC
	if (caps & BIT(0))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_LDPC;

	// HT40
	if (caps & BIT(1))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_HT40;

	// Static/Dynamic SM Power Save
	switch ((caps >> 2) & 0x3) {
		case 0:
			phy->ht_caps |= NETWORK_PHY_HT_CAP_SMPS_STATIC;
			break;

		case 1:
			phy->ht_caps |= NETWORK_PHY_HT_CAP_SMPS_DYNAMIC;
			break;

		default:
			break;
	}

	// RX Greenfield
	if (caps & BIT(4))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_GF;

	// RX HT20 Short GI
	if (caps & BIT(5))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_HT20_SGI;

	// RX HT40 Short GI
	if (caps & BIT(6))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_HT40_SGI;

	// TX STBC
	if (caps & BIT(7))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_TX_STBC;

	// RX STBC
	switch ((caps >> 8) & 0x3) {
		case 1:
			phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_STBC1;
			break;

		case 2:
			phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_STBC2;
			break;

		case 3:
			phy->ht_caps |= NETWORK_PHY_HT_CAP_RX_STBC3;
			break;

		default:
			break;
	}

	// HT Delayed Block ACK
	if (caps & BIT(10))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_DELAYED_BA;

	// Max AMSDU length 7935
	if (caps & BIT(11))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_MAX_AMSDU_7935;

	// DSSS/CCK HT40
	if (caps & BIT(12))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_DSSS_CCK_HT40;

	// Bit 13 is reserved

	// HT40 Intolerant
	if (caps & BIT(14))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_HT40_INTOLERANT;

	// L-SIG TXOP protection
	if (caps & BIT(15))
		phy->ht_caps |= NETWORK_PHY_HT_CAP_LSIG_TXOP_PROT;
}

static struct nla_policy phy_frequency_policy[NL80211_FREQUENCY_ATTR_MAX + 1] = {
	[NL80211_FREQUENCY_ATTR_FREQ] = { .type = NLA_U32 },
	[NL80211_FREQUENCY_ATTR_DISABLED] = { .type = NLA_FLAG },
	[NL80211_FREQUENCY_ATTR_NO_IR] = { .type = NLA_FLAG },
	[__NL80211_FREQUENCY_ATTR_NO_IBSS] = { .type = NLA_FLAG },
	[NL80211_FREQUENCY_ATTR_RADAR] = { .type = NLA_FLAG },
	[NL80211_FREQUENCY_ATTR_MAX_TX_POWER] = { .type = NLA_U32 },
};

static unsigned int phy_frequency_to_channel(unsigned int freq) {
	if (freq == 2484)
		return 14;

	else if (freq < 2484)
		return (freq - 2407) / 5;

	else if (freq >= 4910 && freq <= 4980)
		return (freq - 4000) / 5;

	else if (freq <= 45000)
		return (freq - 5000) / 5;

	else if (freq >= 58320 && freq <= 64800)
		return (freq - 56160) / 2160;

	return 0;
};

static int phy_parse_channels(struct network_phy* phy, struct nlattr* nl_freqs) {
	struct nlattr* nl_freq;
	int rem_freq;

	struct nlattr* tb_freq[NL80211_FREQUENCY_ATTR_MAX + 1];
	nla_for_each_nested(nl_freq, nl_freqs, rem_freq) {
		// Get data
		nla_parse(tb_freq, NL80211_FREQUENCY_ATTR_MAX, nla_data(nl_freq),
				nla_len(nl_freq), phy_frequency_policy);

		if (!tb_freq[NL80211_FREQUENCY_ATTR_FREQ])
			continue;

		// Skip any disabled channels
		if (tb_freq[NL80211_FREQUENCY_ATTR_DISABLED])
			continue;

		struct network_phy_channel* channel = calloc(1, sizeof(*channel));
		if (!channel)
			return -1;

		// Append object to list of channels
		TAILQ_INSERT_TAIL(&phy->channels, channel, channels);

		// Get frequency
		channel->frequency = nla_get_u32(tb_freq[NL80211_FREQUENCY_ATTR_FREQ]);

		// Convert frequency to channel
		channel->number = phy_frequency_to_channel(channel->frequency);

		// Radar detection
		if (tb_freq[NL80211_FREQUENCY_ATTR_RADAR])
			channel->dfs = true;

		// Maximum TX power
		if (tb_freq[NL80211_FREQUENCY_ATTR_MAX_TX_POWER])
			channel->max_tx_power = \
				nla_get_u32(tb_freq[NL80211_FREQUENCY_ATTR_MAX_TX_POWER]) * 0.01;
	}

	return 0;
}

static int phy_parse_info(struct nl_msg* msg, void* data) {
	struct network_phy* phy = data;

	struct nlattr* attrs[NL80211_ATTR_MAX + 1];
	struct genlmsghdr *gnlh = nlmsg_data(nlmsg_hdr(msg));

	nla_parse(attrs, NL80211_ATTR_MAX, genlmsg_attrdata(gnlh, 0),
		genlmsg_attrlen(gnlh, 0), NULL);

	// Ciphers
	if (attrs[NL80211_ATTR_CIPHER_SUITES]) {
		int num = nla_len(attrs[NL80211_ATTR_CIPHER_SUITES]) / sizeof(__u32);
		__u32* ciphers = nla_data(attrs[NL80211_ATTR_CIPHER_SUITES]);
		phy_parse_ciphers(phy, ciphers, num);
	}

	if (attrs[NL80211_ATTR_WIPHY_BANDS]) {
		struct nlattr* nl_band;
		int i;

		nla_for_each_nested(nl_band, attrs[NL80211_ATTR_WIPHY_BANDS], i) {
			struct nlattr* band_attrs[NL80211_BAND_ATTR_MAX + 1];
			nla_parse(band_attrs, NL80211_BAND_ATTR_MAX, nla_data(nl_band),
				nla_len(nl_band), NULL);

			// HT Capabilities
			if (band_attrs[NL80211_BAND_ATTR_HT_CAPA]) {
				__u16 ht_caps = nla_get_u16(band_attrs[NL80211_BAND_ATTR_HT_CAPA]);
				phy_parse_ht_capabilities(phy, ht_caps);
			}

			// VHT Capabilities
			if (band_attrs[NL80211_BAND_ATTR_VHT_CAPA]) {
				__u32 vht_caps = nla_get_u32(band_attrs[NL80211_BAND_ATTR_VHT_CAPA]);

				phy_parse_vht_capabilities(phy, vht_caps);
			}

			// Frequencies
			if (band_attrs[NL80211_BAND_ATTR_FREQS]) {
				phy_parse_channels(phy, band_attrs[NL80211_BAND_ATTR_FREQS]);
			}
		}
	}

	return NL_OK;
}

static int phy_get_info(struct network_phy* phy) {
	DEBUG(phy->ctx, "Getting information for %s\n", phy->name);

	struct nl_msg* msg = network_phy_make_netlink_message(phy, NL80211_CMD_GET_WIPHY, 0);
	if (!msg)
		return -1;

	int r = network_send_netlink_message(phy->ctx, msg, phy_parse_info, phy);

	// This is fine since some devices are not supported by NL80211
	if (r == -ENODEV) {
		DEBUG(phy->ctx, "Could not fetch information from kernel\n");
		return 0;
	}

	return r;
}

static void network_phy_free(struct network_phy* phy) {
	DEBUG(phy->ctx, "Releasing phy at %p\n", phy);

	// Destroy all channels
	while (!TAILQ_EMPTY(&phy->channels)) {
		struct network_phy_channel* channel = TAILQ_FIRST(&phy->channels);
		TAILQ_REMOVE(&phy->channels, channel, channels);
		free(channel);
	}

	if (phy->name)
		free(phy->name);

	network_unref(phy->ctx);
	free(phy);
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

	p->name = strdup(name);
	p->index = index;

	TAILQ_INIT(&p->channels);

	// Load information from kernel
	int r = phy_get_info(p);
	if (r) {
		ERROR(p->ctx, "Error getting PHY information from kernel\n");
		network_phy_free(p);

		return r;
	}

	DEBUG(p->ctx, "Allocated phy at %p (index = %d)\n", p, p->index);
	*phy = p;
	return 0;
}

NETWORK_EXPORT struct network_phy* network_phy_ref(struct network_phy* phy) {
	if (!phy)
		return NULL;

	phy->refcount++;
	return phy;
}

NETWORK_EXPORT struct network_phy* network_phy_unref(struct network_phy* phy) {
	if (!phy)
		return NULL;

	if (--phy->refcount > 0)
		return phy;

	network_phy_free(phy);
	return NULL;
}

struct nl_msg* network_phy_make_netlink_message(struct network_phy* phy,
		enum nl80211_commands cmd, int flags) {
	struct nl_msg* msg = network_make_netlink_message(phy->ctx, cmd, flags);
	if (!msg)
		return NULL;

	// Set PHY index
	NLA_PUT_U32(msg, NL80211_ATTR_WIPHY, phy->index);

	return msg;

nla_put_failure:
	nlmsg_free(msg);

	return NULL;
}

NETWORK_EXPORT const char* network_phy_get_cipher_string(const enum network_phy_ciphers cipher) {
	switch (cipher) {
		case NETWORK_PHY_CIPHER_WEP40:
			return "WEP40";

		case NETWORK_PHY_CIPHER_TKIP:
			return "TKIP";

		case NETWORK_PHY_CIPHER_CCMP128:
			return "CCMP-128";

		case NETWORK_PHY_CIPHER_WEP104:
			return "WEP-104";

		case NETWORK_PHY_CIPHER_CMAC128:
			return "CMAC-128";

		case NETWORK_PHY_CIPHER_GCMP128:
			return "GCMP-128";

		case NETWORK_PHY_CIPHER_GCMP256:
			return "GCMP-256";

		case NETWORK_PHY_CIPHER_CCMP256:
			return "CCMP-256";

		case NETWORK_PHY_CIPHER_GMAC128:
			return "GMAC-128";

		case NETWORK_PHY_CIPHER_GMAC256:
			return "GMAC-256";

		case NETWORK_PHY_CIPHER_CMAC256:
			return "CMAC-256";

		case NETWORK_PHY_CIPHER_WPISMS4:
			return "WPI-SMS4";
	}

	return NULL;
}

NETWORK_EXPORT int network_phy_supports_cipher(struct network_phy* phy, const enum network_phy_ciphers cipher) {
	return phy->ciphers & cipher;
}

NETWORK_EXPORT char* network_phy_list_ciphers(struct network_phy* phy) {
	char* buffer = NULL;

	foreach_cipher(cipher) {
		if (network_phy_supports_cipher(phy, cipher)) {
			const char* s = network_phy_get_cipher_string(cipher);

			if (!s)
				continue;

			if (buffer)
				asprintf(&buffer, "%s %s", buffer, s);
			else
				asprintf(&buffer, "%s", s);
		}
	}

	return buffer;
}

NETWORK_EXPORT int network_phy_has_vht_capability(struct network_phy* phy, const enum network_phy_vht_caps cap) {
	return phy->vht_caps & cap;
}

NETWORK_EXPORT int network_phy_has_ht_capability(struct network_phy* phy, const enum network_phy_ht_caps cap) {
	return phy->ht_caps & cap;
}

static const char* network_phy_get_vht_capability_string(const enum network_phy_vht_caps cap) {
	switch (cap) {
		case NETWORK_PHY_VHT_CAP_VHT160:
			return "[VHT-160]";

		case NETWORK_PHY_VHT_CAP_VHT80PLUS80:
			return "[VHT-160-80PLUS80]";

		case NETWORK_PHY_VHT_CAP_RX_LDPC:
			return "[RXLDPC]";

		case NETWORK_PHY_VHT_CAP_RX_SHORT_GI_80:
			return "[SHORT-GI-80]";

		case NETWORK_PHY_VHT_CAP_RX_SHORT_GI_160:
			return "[SHORT-GI-160]";

		case NETWORK_PHY_VHT_CAP_TX_STBC:
			return "[TX-STBC-2BY1]";

		case NETWORK_PHY_VHT_CAP_SU_BEAMFORMER:
			return "[SU-BEAMFORMER]";

		case NETWORK_PHY_VHT_CAP_SU_BEAMFORMEE:
			return "[SU-BEAMFORMEE]";

		case NETWORK_PHY_VHT_CAP_MU_BEAMFORMER:
			return "[MU-BEAMFORMER]";

		case NETWORK_PHY_VHT_CAP_MU_BEAMFORMEE:
			return "[MU-BEAMFORMEE]";

		case NETWORK_PHY_VHT_CAP_TXOP_PS:
			return "[VHT-TXOP-PS]";

		case NETWORK_PHY_VHT_CAP_HTC_VHT:
			return "[HTC-VHT]";

		case NETWORK_PHY_VHT_CAP_RX_ANTENNA_PATTERN:
			return "[RX-ANTENNA-PATTERN]";

		case NETWORK_PHY_VHT_CAP_TX_ANTENNA_PATTERN:
			return "[TX-ANTENNA-PATTERN]";
	}

	return NULL;
}

static const char* network_phy_get_ht_capability_string(const enum network_phy_ht_caps cap) {
	switch (cap) {
		case NETWORK_PHY_HT_CAP_RX_LDPC:
			return "[LDPC]";

		case NETWORK_PHY_HT_CAP_HT40:
			return "[HT40+][HT40-]";

		case NETWORK_PHY_HT_CAP_SMPS_STATIC:
			return "[SMPS-STATIC]";

		case NETWORK_PHY_HT_CAP_SMPS_DYNAMIC:
			return "[SMPS-DYNAMIC]";

		case NETWORK_PHY_HT_CAP_RX_GF:
			return "[GF]";

		case NETWORK_PHY_HT_CAP_RX_HT20_SGI:
			return "[SHORT-GI-20]";

		case NETWORK_PHY_HT_CAP_RX_HT40_SGI:
			return "[SHORT-GI-40]";

		case NETWORK_PHY_HT_CAP_TX_STBC:
			return "[TX-STBC]";

		case NETWORK_PHY_HT_CAP_RX_STBC1:
			return "[RX-STBC1]";

		case NETWORK_PHY_HT_CAP_RX_STBC2:
			return "[RX-STBC12]";

		case NETWORK_PHY_HT_CAP_RX_STBC3:
			return "[RX-STBC123]";

		case NETWORK_PHY_HT_CAP_DELAYED_BA:
			return "[DELAYED-BA]";

		case NETWORK_PHY_HT_CAP_MAX_AMSDU_7935:
			return "[MAX-AMSDU-7935]";

		case NETWORK_PHY_HT_CAP_DSSS_CCK_HT40:
			return "[DSSS_CCK-40]";

		case NETWORK_PHY_HT_CAP_HT40_INTOLERANT:
			return "[40-INTOLERANT]";

		case NETWORK_PHY_HT_CAP_LSIG_TXOP_PROT:
			return "[LSIG-TXOP-PROT]";
	}

	return NULL;
}

NETWORK_EXPORT char* network_phy_list_vht_capabilities(struct network_phy* phy) {
	char* buffer = malloc(1024);
	*buffer = '\0';

	char* p = buffer;

	switch (phy->max_mpdu_length) {
		case 7991:
		case 11454:
			snprintf(p, 1024 - 1, "[MAX-MPDU-%zu]", phy->max_mpdu_length);
			break;

	}

	foreach_vht_cap(cap) {
		if (network_phy_has_vht_capability(phy, cap)) {
			const char* cap_str = network_phy_get_vht_capability_string(cap);

			if (cap_str)
				p = strncat(p, cap_str, 1024 - 1);
		}
	}

	return buffer;
}

NETWORK_EXPORT char* network_phy_list_ht_capabilities(struct network_phy* phy) {
	char* buffer = malloc(1024);
	*buffer = '\0';

	char* p = buffer;
	foreach_ht_cap(cap) {
		if (network_phy_has_ht_capability(phy, cap)) {
			const char* cap_str = network_phy_get_ht_capability_string(cap);

			if (cap_str)
				p = strncat(p, cap_str, 1024 - 1);
		}
	}

	return buffer;
}

NETWORK_EXPORT char* network_phy_list_channels(struct network_phy* phy) {
	char string[10240] = "CHAN FREQ  DFS TXPWR\n";
	char* p = string + strlen(string);

	struct network_phy_channel* channel;
	TAILQ_FOREACH(channel, &phy->channels, channels) {
		p += sprintf(p, "%-4u %-5u %-3s %-4.1f\n",
			channel->number,
			channel->frequency,
			(channel->dfs) ? "Y" : "N",
			channel->max_tx_power
		);
	}

	return strdup(string);
}
