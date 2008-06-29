#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

import sys
import Mapper

class wordCountMapper(Mapper.Mapper):
	"""advanced Mapper, using Python iterators and generators."""

	def map(self, separator='\t'):
		# input comes from STDIN (standard input)
		data = self.read_input(sys.stdin)
		for words in data:
		# write the results to STDOUT (standard output);
		# what we output here will be the input for the
		# Reduce step, i.e. the input for reducer.py
		#
		# tab-delimited; the trivial word count is 1
			for word in words:
				print '%s%s%d' % (word, separator, 1)

if __name__ == "__main__":
	wordCountMapper().map()
