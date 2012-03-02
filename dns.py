#!/usr/bin/env python

import sys, dht

from twisted.names import dns, server, client, cache
from twisted.internet import reactor, error
from twisted.python import failure

class DHTMapping(dht.DHT):
	def __contains__(self, key):
		return key.endswith('.dark')

class MapResolver(client.Resolver):
	"""
	Resolve .dark domains from dht 
	and the other ones via forward dns-server
	"""
	def __init__(self, mapping, servers):
		self.mapping = mapping
		client.Resolver.__init__(self, servers=servers)
		self.ttl = 10

	def lookupAddress(self, name, timeout = None):
		if name in self.mapping:
			# this is a .dark. request using dht
			result = self.mapping[name]
			def makeResult(value):
				print "dht: %s -> %s" % (name,value)
				a = dns.RRHeader(name=name, type=dns.A, ttl=10)
				payload = dns.Record_A(value, ttl=10)
				a.payload = payload
				return ([a], [], [])
			def nxdomain(value):
				print "dht: %s -> NXDOMAIN" % name
				return failure.Failure(self.exceptionForCode(dns.ENAME)(value))
			result.addCallback(makeResult)
			result.addErrback(nxdomain)
			return result
		else:
			# classic dns lookup
			return self._lookup(name, dns.IN, dns.A, timeout)

# bootstrap dht from 127.0.0.1:4000 and listen on 4444
mapping = DHTMapping(4444, ('127.0.0.1', 4000))

# test hosts
mapping['test.dark'] = '1.2.3.4'

# classic dns forward servers
mr = MapResolver(mapping, [('8.8.8.8', 53), ('8.8.4.4', 53)])
factory = server.DNSServerFactory(clients=[mr])
protocol = dns.DNSDatagramProtocol(factory)

try:
	dns_port = 53
	reactor.listenUDP(dns_port, protocol)
	reactor.listenTCP(dns_port, factory)
except error.CannotListenError, e:
	print "ERROR:", e
	sys.exit(1)

reactor.run()
