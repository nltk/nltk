from inputformat import TextLineInput


class MapperBase:
	""" base class for every map tasks"""

	def __init__(self):
		self.inputformat = TextLineInput

	def set_inputformat(self, format):
		self.inputformat = format

	def map(self, key, value, outputCollector):
		raise NotImplementedError('map() is not implemented in this class')

	def call_map(self, separator='\t'):
		""" driver function for map task, call the map() function for subclass"""
		# input comes from STDIN (standard input)
		data = self.inputformat.read_line()
		for key, value in data:
			self.map(key, value)
