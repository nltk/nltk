#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

from Reducer import ReducerBase
from outputCollector import lineOutput

class wordCountReducer(ReducerBase):

	def reduce(self, key, values, outputCollector=lineOutput):
		sum  = 0
		try:
			for value in values:
				sum += int(value) 
			lineOutput.collect(key, sum)
		except ValueError:
			#count was not a number, so silently discard this item
			pass

if __name__ == "__main__":
	wordCountReducer().reduceCaller()
