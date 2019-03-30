/*#############################################################################
#                                                                             #
# IPFire.org - A linux based firewall                                         #
# Copyright (C) 2019 IPFire Network Development Team                          #
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

#include <stdio.h>
#include <stdlib.h>

#include <network/libnetwork.h>
#include <network/logging.h>
#include <network/phy.h>

int main(int argc, char** argv) {
    struct network_ctx* ctx = NULL;
    struct network_phy* phy = NULL;
    int r;

    if (argc < 2) {
        fprintf(stderr, "No enough arguments\n");
        r = 2;
        goto END;
    }

    // Initialise context
    r = network_new(&ctx);
    if (r)
        return r;

    r = network_phy_new(ctx, &phy, argv[1]);
    if (r) {
        fprintf(stderr, "Could not find %s\n", argv[1]);
        goto END;
    }

    // Print all supported ciphers
    char* ciphers = network_phy_list_ciphers(phy);
    if (ciphers && *ciphers) {
        printf("%s\n", ciphers);
        free(ciphers);
    }

END:
    network_phy_unref(phy);
    network_unref(ctx);
    return r;
}
