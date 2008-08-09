#!/usr/bin/env python

from hadooplib.reducer import ReducerBase
from hadooplib.outputcollector import LineOutput

class ValueAggregater(ReducerBase):
	"""
	aggregate the values having the same key.

	e.g. animal [cat, dog, mouse] -> animal	: cat dog mouse
	"""

	def reduce(self, key, values):
		values_str = ""
		for value in values:
			values_str += " " + str(value)

		self.outputcollector.collect(key, values_str)

if __name__ == "__main__":
	ValueAggregater().call_reduce()
