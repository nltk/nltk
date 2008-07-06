#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

from Mapper import MapperBase
from outputCollector import lineOutput

class wordCountMapper(MapperBase):

	def map(self, key, value, outputCollector = lineOutput):
		words = value.split()
		for word in words:
			outputCollector.collect(word, 1)

if __name__ == "__main__":
	wordCountMapper().mapCaller()
