#!/usr/bin/env  python

from hadooplib.reducer import ReducerBase

class TFReducer(ReducerBase):

	def reduce(self, key, values, outputCollector):
		sum  = 0
		try:
			for value in values:
				sum += int(value) 
			outputCollector.collect(key, sum)
		except ValueError:
			#count was not a number, so silently discard this item
			pass

if __name__ == "__main__":
	TFReducer().call_reduce()
