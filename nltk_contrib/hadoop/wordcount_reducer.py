from hadooplib.reducer import ReducerBase
from hadooplib.outputcollector import LineOutput

class WordCountReducer(ReducerBase):

	def reduce(self, key, values, outputCollector=LineOutput):
		sum  = 0
		try:
			for value in values:
				sum += int(value) 
			LineOutput.collect(key, sum)
		except ValueError:
			#count was not a number, so silently discard this item
			pass

if __name__ == "__main__":
	WordCountReducer().call_reduce()
