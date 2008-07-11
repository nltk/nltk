from itertools import groupby
from operator import itemgetter

from inputformat import KeyValueInput
from outputcollector import LineOutput

class ReducerBase:
	""" base class for every reduce tasks"""
	def __init__(self):
		self.inputformat = KeyValueInput
		self.outputcollector = LineOutput

	def set_inputformat(self, format):
		self.inputformat = format

	def group_data(self, data):
		""" group data"""
		for key, group in  groupby(data, itemgetter(0)):
			values = map(itemgetter(1), group)
			yield key, values

	def reduce(self, key, values):
		raise NotImplementedError('reduce() is not implemented in this class')

	def call_reduce(self):
		# input comes from STDIN (standard input)
		data = self.inputformat.read_line()
		for key, values in self.group_data(data):
			self.reduce(key, values, self.outputcollector)
