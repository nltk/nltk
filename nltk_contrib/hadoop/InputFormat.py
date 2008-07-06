import sys

class TextLineInput:
	""" the input is lines of text"""

	@staticmethod
	def readLine(file=sys.stdin):
		for line in file:
		# split the line into words
			yield line

class KeyValueInput:
	""" the input is lines of key'\t'value """

	@staticmethod
	def readLine(file=sys.stdin, separator='\t'):
		""" split the data """
		for line in file:
			yield line.rstrip().split(separator, 1)
