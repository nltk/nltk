from inputformat import TextLineInput
from outputcollector import LineOutput


class MapperBase:
	""" 
	Base class for every map tasks
	
	Your map class should extend this base class 
	and override the map function
	"""

	def __init__(self):
		self.inputformat = TextLineInput
		self.outputcollector = LineOutput

	def set_inputformat(self, format):
		""" set the input formatter for map task"""

		self.inputformat = format
	
	def set_outputcollector(self, collector):
		""" set the output collector for map task """

		self.outputcollector = collector

	def map(self, key, value):
		""" you should implement this function in your map class"""

		raise NotImplementedError('map() is not implemented in this class')

	def call_map(self, separator='\t'):
		""" driver function for map task, you should call this method 
		instead of the map method in main function """

		data = self.inputformat.read_line()
		for key, value in data:
			self.map(key, value)
