#!/usr/bin/env python

from hadooplib.reducer import ReducerBase

class WordCountReducer(ReducerBase):

	def reduce(self, key, values, outputcollector):
		sum  = 0
		try:
			for value in values:
				sum += int(value) 
			outputcollector.collect(key, sum)
		except ValueError:
			#count was not a number, so silently discard this item
			pass

if __name__ == "__main__":
	WordCountReducer().call_reduce()
