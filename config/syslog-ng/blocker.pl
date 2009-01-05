#!/usr/bin/perl
# /usr/local/sbin/blocker.pl

# Later we may increase the recent list
# modprobe ipt_recent ip_list_tot=1000

while (<>) {
	if ( /.*[1:1810:12].* -> ((d{1,3}.){3}d{1,3})/ )/ ) {
		system "echo $1 > /proc/net/ipt_recent/BLOCK";
	}
}