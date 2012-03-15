#!/usr/bin/env python

import sys, dht, bootsource

from twisted.names import dns, server, client, cache
from twisted.internet import reactor, error, defer
from twisted.python import failure

class DHTMapping(dht.DHT):
	def __contains__(self, key):
		plainkey = key.lower()
		return plainkey.endswith('.dark') or plainkey.endswith('d.f.ip6.arpa')

def dhtQueryString(name, type):
	return "%s %s" % (name.lower().rstrip('.'), dns.QUERY_TYPES[type])

class MapResolver(client.Resolver):
	"""
	Resolve .dark domains from dht 
	and the other ones via forward dns-server
	"""
	def __init__(self, mapping, servers):
		self.mapping = mapping
		client.Resolver.__init__(self, servers=servers)
		self.ttl = 10

	def _dhtlookup(self, name, cls, type, timeout=None):
		if type in [dns.A, dns.AAAA, dns.CNAME, dns.MX, dns.PTR]:
			result = self.mapping[dhtQueryString(name, type)]

			def makeResult(value):
				print "dht: %s -> %s" % (dhtQueryString(name,type),value)
				response = dns.RRHeader(name=name, type=type, ttl=10)
				if type == dns.A:
					payload = dns.Record_A(address=value, ttl=10)
				elif type == dns.AAAA:
					payload = dns.Record_AAAA(address=value, ttl=10)
				elif type == dns.CNAME:
					payload = dns.Record_CNAME(name=value, ttl=10)
				elif type == dns.MX:
					payload = dns.Record_MX(name=value, ttl=10)
				elif type == dns.PTR:
					payload = dns.Record_PTR(name=value, ttl=10)
				response.payload = payload
				return ([response], [], [])

			def cnameResult(value):
				# resolve cname
				cnamed = self._dhtlookup(name, dns.IN, dns.CNAME, timeout)

				def getAfromCNAME(value):
					cname = value[0][0]
					cname_name = cname.payload.name.name
					arec = self._dhtlookup(cname_name, dns.IN, type, timeout)

					def mergeRecords(value):
						return ([cname,value[0][0]], [], [])

					arec.addCallback(mergeRecords)
					return arec

				cnamed.addCallback(getAfromCNAME)
				return cnamed

			def nxdomain(value):
				# send error
				print "dht: %s -> NXDOMAIN" % dhtQueryString(name, type)
				return failure.Failure(self.exceptionForCode(dns.ENAME)(value))

			result.addCallback(makeResult)
			if type in [dns.A, dns.AAAA]:
				result.addErrback(cnameResult)
			result.addErrback(nxdomain)

			return result
		else:
			return defer.fail(NotImplementedError("MapResolver._dhtlookup: %s record lookup" % dns.QUERY_TYPES[type]))

	def dolookup(self, name, cls, type, timeout=None):
		if name in self.mapping:
			return self._dhtlookup(name, dns.IN, type, timeout)
		else:
			return self._lookup(name, dns.IN, type, timeout)

	def lookupAddress(self, name, timeout=None):
		return self.dolookup(name, dns.IN, dns.A, timeout)

	def lookupIPV6Address(self, name, timeout=None):
		return self.dolookup(name, dns.IN, dns.AAAA, timeout)

	def lookupCanonicalName(self, name, timeout=None):
		return self.dolookup(name, dns.IN, dns.CNAME, timeout)

	def lookupMailExchange(self, name, timeout=None):
		return self.dolookup(name, dns.IN, dns.MX, timeout)

	def lookupPointer(self, name, timeout=None):
		return self.dolookup(name, dns.IN, dns.PTR, timeout)

# bootstrap dht from 127.0.0.1:4000 and listen on 4053
knownNodes = [('127.0.0.1', 4000)]
#twisted bug: there is no ipv6 support yet
#knownNodes.extend( bootsource.bootstrapList(bootsource.routingTable()) )
mapping = DHTMapping(dht.PORT, knownNodes)

# test hosts
mapping[dhtQueryString('test.dark', dns.A)] = '1.2.3.4'
mapping[dhtQueryString('test6.dark', dns.AAAA)] = '2001:7f8:1d14:0:22cf:31ff:fe4c:3213'
mapping[dhtQueryString('testc.dark', dns.CNAME)] = 'test.dark.'
mapping[dhtQueryString('testd.dark', dns.CNAME)] = 'testf.dark.'
mapping[dhtQueryString('testm.dark', dns.MX)] = 'testf.dark.'
mapping[dhtQueryString('1.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.3.2.3.2.c.2.9.a.7.a.1.2.e.9.d.f.ip6.arpa', dns.PTR)] = 'test7.dark'

# classic dns forward servers
mr = MapResolver(mapping, [('8.8.8.8', 53), ('8.8.4.4', 53)])
factory = server.DNSServerFactory(clients=[mr])
protocol = dns.DNSDatagramProtocol(factory)

try:
	reactor.listenUDP(dns.PORT, protocol)
	reactor.listenTCP(dns.PORT, factory)
except error.CannotListenError, e:
	print "ERROR:", e
	sys.exit(1)

reactor.run()
