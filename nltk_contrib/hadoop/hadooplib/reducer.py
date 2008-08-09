from itertools import groupby
from operator import itemgetter

from inputformat import KeyValueInput
from outputcollector import LineOutput

class ReducerBase:
	""" Base class for every reduce tasks

	Your reduce class should extend this base class 
	and override the reduce function """

	def __init__(self):
		self.inputformat = KeyValueInput
		self.outputcollector = LineOutput

	def set_inputformat(self, format):
		""" set the input formatter for reduce task"""

		self.inputformat = format

	def set_outputcollector(self, collector):
		""" set the output collector for reduce task """

		self.outputcollector = collector

	def group_data(self, data):
		""" collect data that have the same key into a group
		assume the data is sorted """

		for key, group in  groupby(data, itemgetter(0)):
			values = map(itemgetter(1), group)
			yield key, values

	def reduce(self, key, values):
		""" you should implement this function in your reduce class"""

		raise NotImplementedError('reduce() is not implemented in this class')

	def call_reduce(self):
		""" driver function for reduce task, you should call this method 
		instead of the reduce method in main function """

		data = self.inputformat.read_line()
		for key, values in self.group_data(data):
			self.reduce(key, values)
