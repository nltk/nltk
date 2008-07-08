from hadooplib.mapper import MapperBase
from hadooplib.outputcollector import LineOutput

class WordCountMapper(MapperBase):

	def map(self, key, value, outputCollector = LineOutput):
		words = value.split()
		for word in words:
			outputCollector.collect(word, 1)

if __name__ == "__main__":
	WordCountMapper().call_map()
