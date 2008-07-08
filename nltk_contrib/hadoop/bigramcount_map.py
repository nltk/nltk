#!/usr/bin/python

import sys

for line in sys.stdin:
	line = line.strip()
	words = filter(lambda word: word, line.split())
	# increase counters
	for word in words:
		# write the results to STDOUT (standard output);
		# what we output here will be the input for the
		# Reduce step, i.e. the input for reducer.py
		#
		# tab-delimited; the trivial word count is 1
		while (len(words) >= 2):
			print '%s %s\t%s' % (words[0], words[1], 1)
			words = words[1:]
