#!/usr/bin/env python

class Reducer:
	def __init__(self):
		pass

	def read_mapper_input(self, file, separator='\t'):
		for line in file:
			yield line.rstrip().split(separator, 1)
