#!/usr/bin/env python

from hadooplib.mapper import MapperBase

class WordCountMapper(MapperBase):

	def map(self, key, value, outputcollector):
		words = value.split()
		for word in words:
			outputcollector.collect(word, 1)

if __name__ == "__main__":
	WordCountMapper().call_map()
