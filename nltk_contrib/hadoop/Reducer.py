#!/usr/bin/env python

import sys
from itertools import groupby
from operator import itemgetter

class Reducer:
	def __init__(self):
		pass

	def read_mapper_input(self, file, separator='\t'):
		""" split the data """
		for line in file:
			yield line.rstrip().split(separator, 1)

	def group_data(self, data):
		""" group data"""
		for key, group in  groupby(data, itemgetter(0)):
			values = map(itemgetter(1), group)
			yield key, values

	def reduceCaller(self, separator='\t'):
		# input comes from STDIN (standard input)
		data = self.read_mapper_input(sys.stdin, separator=separator)
		for key, values in self.group_data(data):
			self.reduce(key, values)
