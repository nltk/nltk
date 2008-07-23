#!/usr/bin/env  python

from hadooplib.mapper import MapperBase

class TFMapper(MapperBase):
	"""
	read the filename (one filename per line), count the term frequency.
	"""

	def map(self, key, value, outputCollector):
		filename = value.strip()
		if len(filename) == 0:
			return
		file = open(filename, 'r')
		for line in file:
			words = line.strip().split()
			for word in words:
				outputCollector.collect(str(word) + " " + str(filename), 1)

if __name__ == "__main__":
	TFMapper().call_map()
