import sys
from itertools import groupby
from operator import itemgetter
from InputFormat import KeyValueInput

class ReducerBase:
	""" base class for every reduce tasks"""
	def __init__(self):
		pass

	def group_data(self, data):
		""" group data"""
		for key, group in  groupby(data, itemgetter(0)):
			values = map(itemgetter(1), group)
			yield key, values

	def reduce(self, key, values):
		raise NotImplementedError('reduce() is not implemented in this class')

	def reduceCaller(self):
		# input comes from STDIN (standard input)
		data = KeyValueInput.readLine()
		for key, values in self.group_data(data):
			self.reduce(key, values)
