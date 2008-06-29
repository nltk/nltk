#!/usr/bin/env python
# Based on: http://www.michael-noll.com/wiki/Writing_An_Hadoop_MapReduce_Program_In_Python
"""dvanced Mapper, using Python iterators and generators."""

import sys

def read_input(file):
	for line in file:
	# split the line into words
		yield line.split()

def main(separator='\t'):
	# input comes from STDIN (standard input)
	data = read_input(sys.stdin)
	for words in data:
	# write the results to STDOUT (standard output);
	# what we output here will be the input for the
	# Reduce step, i.e. the input for reducer.py
	#
	# tab-delimited; the trivial word count is 1
		for wordTag in words:
			print '%s%s%d' % (wordTag, separator, 1)
			wordWithoutTag = wordTag.split('/')[0]
			print '%s%s%d' % (wordWithoutTag+'/*', separator, 1)

if __name__ == "__main__":
	main()
