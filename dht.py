#!/usr/bin/env python

import hashlib
import entangled.kademlia.node as kademlia

def _hash(key):
	h = hashlib.sha1()
	h.update(key)
	return h.digest()

class DHT(object):
	def __init__(self, port, knownNode):
		self.knownNodes = []
		self.knownNodes.append(knownNode)
		self.node = kademlia.Node(udpPort=port)
		self.node.joinNetwork(self.knownNodes)

	def store(self, key, value):
		return self.node.iterativeStore(_hash(key), value)

	def get(self, key):
		def fetch(result):
			value = result[_hash(key)]
			return value
		return self.node.iterativeFindValue(_hash(key)).addCallback(fetch)

	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		return self.store(key, value)
