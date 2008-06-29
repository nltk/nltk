#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python

from itertools import groupby
from operator import itemgetter
import sys
import Reducer

class wordCountReducer(Reducer.Reducer):
	"""advanced Reducer, using Python iterators and generators."""

	def group_data(self, data):
		""" how to ensure that it generate data one at a time"""
		for key, group in  groupby(data, itemgetter(0)):
			values = map(itemgetter(1), group)
			yield key, values

	def reduce(self, separator='\t'):
		# input comes from STDIN (standard input)
		data = self.read_mapper_input(sys.stdin, separator=separator)
		# groupby groups multiple word-count pairs by word,
		# and creates an iterator that returns consecutive keys and their group:
		#   current_word - string containing a word (the key)
		#   group - iterator yielding all ["<current_word>", "<count>"] items
		#for current_word, group in groupby(data, itemgetter(0)):
			#try:
				#for e in group:
					#print e
				#total_count = sum(int(count) for current_word, count in group)
				#print "%s%s%d" % (current_word, separator, total_count)
			#except ValueError:
				 #count was not a number, so silently discard this item
				#pass
		for key, values in self.group_data(data):
			sum  = 0
			try:
				for value in values:
					sum += int(value) 
				print "%s%s%d" % (key, separator, sum)
			except ValueError:
				#count was not a number, so silently discard this item
				pass

if __name__ == "__main__":
	wordCountReducer().reduce()
