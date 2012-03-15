#!/usr/bin/env python

import subprocess, re, dht

def bootstrapList(hosts, port=dht.PORT):
	return [(host, port) for host in hosts]

def routingTable():
	rtstring = subprocess.check_output(['netstat', '-rn6'])
	routing_table = re.findall(r"^.+?\s+(\S+)\s+.*$", rtstring, re.M)[2:]

	nodelist = []
	for router_ip in routing_table:
		if router_ip.startswith('fe80'):
			nodelist.append(router_ip)

	return nodelist
