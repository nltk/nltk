#!/usr/bin/env python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class SwapMapper(MapperBase):
	"""
	swap key, value to value, key, i.e. swap the role of key and value

	e.g. word 1 -> 1 word
	"""

	def __init__(self):
		MapperBase.__init__(self)
		# use KeyValueInput instead of the default TextLineInput
		self.set_inputformat(KeyValueInput)


	def map(self, key, value):
		self.outputcollector.collect(value, key)

if __name__ == "__main__":
	SwapMapper().call_map()
