from sys import stdin

class TextLineInput:
	""" the input is lines of text"""

	@staticmethod
	def read_line(file=stdin):
		for line in file:
		# split the line into words
			yield None, line

class KeyValueInput:
	""" the input is lines of key'\t'value """

	@staticmethod
	def read_line(file=stdin, separator='\t'):
		""" split the data """
		for line in file:
			yield line.rstrip().split(separator, 1)
