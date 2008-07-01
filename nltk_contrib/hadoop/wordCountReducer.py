#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

import Reducer

class wordCountReducer(Reducer.Reducer):
	"""advanced Reducer, using Python iterators and generators."""

	def reduce(self, key, values):
		sum  = 0
		try:
			for value in values:
				sum += int(value) 
			print "%s%s%d" % (key, '\t', sum)
		except ValueError:
			#count was not a number, so silently discard this item
			pass


if __name__ == "__main__":
	wordCountReducer().reduceCaller()
