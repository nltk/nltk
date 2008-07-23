#!/usr/bin/env  python

from hadooplib.mapper import MapperBase
from hadooplib.inputformat import KeyValueInput

class TFIDFMapper1(MapperBase):
	"""
	stage1 of computing TF*IDF : map part

	word, filename : number -> word : filename, number
	e.g. dog, 1.txt : 1 -> dog : 1.txt, 1
	"""
	def __init__(self):
		MapperBase.__init__(self)
		self.set_inputformat(KeyValueInput)

	def map(self, key, value, outputcollector):
		word, filename = key.split()
		outputcollector.collect(word, str(filename) + "," + value)

if __name__ == "__main__":
	TFIDFMapper1().call_map()
