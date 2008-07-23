#!/usr/bin/env  python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class IDFMapper(MapperBase):
	"""
	output word, 1 for every document contains this word

	(word, filename) tf -> (word,) 1
	"""

	def __init__(self):
		MapperBase.__init__(self)
		# use KeyValueInput instead of the default TextLineInput
		self.set_inputformat(KeyValueInput)

	def map(self, key, value, outputcollector):
		word, filename = key.split()
		outputcollector.collect(str(word) + str(" All"), 1)

if __name__ == "__main__":
	IDFMapper().call_map()
