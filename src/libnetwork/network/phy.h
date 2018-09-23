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

#ifndef NETWORK_PHY_H
#define NETWORK_PHY_H

#include <network/libnetwork.h>

struct network_phy;

int network_phy_new(struct network_ctx*, struct network_phy** phy, const char* name);

struct network_phy* network_phy_ref(struct network_phy* phy);
struct network_phy* network_phy_unref(struct network_phy* phy);

enum network_phy_ht_caps {
	NETWORK_PHY_HT_CAP_RX_LDPC         = (1 <<  0),
	NETWORK_PHY_HT_CAP_HT40            = (1 <<  1),
	NETWORK_PHY_HT_CAP_SMPS_STATIC     = (1 <<  2),
	NETWORK_PHY_HT_CAP_SMPS_DYNAMIC    = (1 <<  3),
	NETWORK_PHY_HT_CAP_RX_GF           = (1 <<  4),
	NETWORK_PHY_HT_CAP_RX_HT20_SGI     = (1 <<  5),
	NETWORK_PHY_HT_CAP_RX_HT40_SGI     = (1 <<  6),
	NETWORK_PHY_HT_CAP_TX_STBC         = (1 <<  7),
	NETWORK_PHY_HT_CAP_RX_STBC1        = (1 <<  8),
	NETWORK_PHY_HT_CAP_RX_STBC2        = (1 <<  9),
	NETWORK_PHY_HT_CAP_RX_STBC3        = (1 << 10),
	NETWORK_PHY_HT_CAP_DELAYED_BA      = (1 << 11),
	NETWORK_PHY_HT_CAP_MAX_AMSDU_7935  = (1 << 12),
	NETWORK_PHY_HT_CAP_DSSS_CCK_HT40   = (1 << 13),
	NETWORK_PHY_HT_CAP_HT40_INTOLERANT = (1 << 14),
	NETWORK_PHY_HT_CAP_LSIG_TXOP_PROT  = (1 << 15),
};

enum network_phy_vht_caps {
	NETWORK_PHY_VHT_CAP_VHT160             = (1 <<  0),
	NETWORK_PHY_VHT_CAP_VHT80PLUS80        = (1 <<  1),
	NETWORK_PHY_VHT_CAP_RX_LDPC            = (1 <<  2),
	NETWORK_PHY_VHT_CAP_RX_SHORT_GI_80     = (1 <<  3),
	NETWORK_PHY_VHT_CAP_RX_SHORT_GI_160    = (1 <<  4),
	NETWORK_PHY_VHT_CAP_TX_STBC            = (1 <<  5),
	NETWORK_PHY_VHT_CAP_SU_BEAMFORMER      = (1 <<  6),
	NETWORK_PHY_VHT_CAP_SU_BEAMFORMEE      = (1 <<  7),
	NETWORK_PHY_VHT_CAP_MU_BEAMFORMER      = (1 <<  8),
	NETWORK_PHY_VHT_CAP_MU_BEAMFORMEE      = (1 <<  9),
	NETWORK_PHY_VHT_CAP_TXOP_PS            = (1 << 10),
	NETWORK_PHY_VHT_CAP_HTC_VHT            = (1 << 11),
	NETWORK_PHY_VHT_CAP_RX_ANTENNA_PATTERN = (1 << 12),
	NETWORK_PHY_VHT_CAP_TX_ANTENNA_PATTERN = (1 << 13),
};


char* network_phy_list_channels(struct network_phy* phy);
int network_phy_has_vht_capability(struct network_phy* phy, const enum network_phy_vht_caps cap);
char* network_phy_list_vht_capabilities(struct network_phy* phy);
int network_phy_has_ht_capability(struct network_phy* phy, const enum network_phy_ht_caps cap);
char* network_phy_list_ht_capabilities(struct network_phy* phy);

#ifdef NETWORK_PRIVATE

#include <linux/nl80211.h>
#include <netlink/msg.h>

struct nl_msg* network_phy_make_netlink_message(struct network_phy* phy,
	enum nl80211_commands cmd, int flags);

#define foreach_vht_cap(cap) \
	for(int cap = NETWORK_PHY_VHT_CAP_VHT160; cap <= NETWORK_PHY_VHT_CAP_TX_ANTENNA_PATTERN; cap <<= 1)

#define foreach_ht_cap(cap) \
	for(int cap = NETWORK_PHY_HT_CAP_RX_LDPC; cap <= NETWORK_PHY_HT_CAP_LSIG_TXOP_PROT; cap <<= 1)

#endif

#endif /* NETWORK_PHY_H */
