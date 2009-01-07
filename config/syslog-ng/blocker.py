#!/usr/bin/python

import sys,os,re
#print sys.argv

if len(sys.argv) < 2:
	print 'Es wurden keine Parameter uebergeben.'
	sys.exit()

#os.system('modprobe ipt_recent ip_list_tot=1000')

m = re.findall(r"[1-9]{1,1}[0-9]{0,2}\.[1-9]{1,1}[0-9]{0,2}\.[1-9]{1,1}[0-9]{0,2}\.[1-9]{1,1}[0-9]{0,2}", sys.argv[1])
#print m
os.system('echo %s > /proc/net/ipt_recent/BLOCK' % m[0])
