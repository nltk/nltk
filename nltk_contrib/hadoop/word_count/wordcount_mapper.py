#!/usr/bin/env python

from hadooplib.mapper import MapperBase

class WordCountMapper(MapperBase):

	def map(self, key, value):
		words = value.split()
		for word in words:
			self.outputcollector.collect(word, 1)

if __name__ == "__main__":
	WordCountMapper().call_map()
