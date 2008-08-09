#!/usr/bin/env python

from hadooplib.mapper import MapperBase
from hadooplib.outputcollector import LineOutput

class NameMapper(MapperBase):
	"""
	map a name to its first character

	e.g. Adam -> Adam, A
	"""

	def map(self, key, value):
		self.outputcollector.collect(value.strip(), value[0])

if __name__ == "__main__":
	NameMapper().call_map()
