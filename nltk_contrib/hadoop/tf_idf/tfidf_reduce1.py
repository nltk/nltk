#!/usr/bin/env  python

from hadooplib.reducer import ReducerBase
from math import log

class TFIDFReducer1(ReducerBase):
	"""
	stage 1 of computing TF*IDF : reducer part

	word : (filename, occurences) -> word : [(filename, TF*IDF) ...]
	"""

	def reduce(self, key, values, outputcollector):
		idf = 1
		# first find the IDF value
		for value in values:
			if value[:3] == "All":
				idf = 1.0/(1 + log(int(value.split(',')[1].strip())))
				values.remove(value)
				break

		# then compute TF*IDF value for each word
		value_str = ""
		for value in values:
			file, tf = value.split(',')
			tf = int(tf.strip())
			value_str += " " + str(file) + "," + str(tf*idf) + " "
		outputcollector.collect(key, value_str)

if __name__ == "__main__":
	TFIDFReducer1().call_reduce()
