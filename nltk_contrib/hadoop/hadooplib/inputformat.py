from sys import stdin

class TextLineInput:
	""" treat the input as lines of text
	
	emit None as key and text line as value"""

	@staticmethod
	def read_line(file=stdin):
		for line in file:
		# split the line into words, trailing space truncated
			yield None, line.strip()

class KeyValueInput:
	""" treat the input as lines of (key, value) pair splited by separator
	
	emit text before separator as key and the rest as value"""

	@staticmethod
	def read_line(file=stdin, separator='\t'):
		""" split the data """
		for line in file:
			yield line.rstrip().split(separator, 1)
