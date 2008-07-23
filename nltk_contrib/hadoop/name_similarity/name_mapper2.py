#!/usr/bin/env python

from hadooplib.inputformat import KeyValueInput
from hadooplib.outputcollector import LineOutput
from hadooplib.mapper import MapperBase

class Name2Names(MapperBase):
	"""
	map a name to the name before and after it

	e.g. Adam -> Adam : Ada Adams
	"""

	def __init__(self):
		MapperBase.__init__(self)
		self.set_inputformat(KeyValueInput)

	def map(self, key, value, outputcollector):
		namelist = value.strip().split()
		namelist.insert(0, '')
		namelist.append('')
		n = len(namelist)
		for i in range(1, n - 1):
			outputcollector.collect(namelist[i], namelist[i-1] + " " + namelist[i+1])
	
if __name__ == "__main__":
	Name2Names().call_map()
