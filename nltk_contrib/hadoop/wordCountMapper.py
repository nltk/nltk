#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

import sys
import Mapper

class wordCountMapper(Mapper.Mapper):
	"""advanced Mapper, using Python iterators and generators."""

	def read_input(self, file):
		for line in file:
		# split the line into words
			yield line

	def map(self, key, value, separator='\t'):
		words = value.split()
		for word in words:
			print '%s%s%d' % (word, separator, 1)

	def mapCaller(self, separator='\t'):
		# input comes from STDIN (standard input)
		data = self.read_input(sys.stdin)
		lineNo = 0
		for line in data:
			lineNo += 1
			self.map(lineNo, line)

if __name__ == "__main__":
	wordCountMapper().mapCaller()
