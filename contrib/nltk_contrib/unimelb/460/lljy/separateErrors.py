#!/usr/bin/python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# separateErrors.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Wed May 25 23:45:40 EST 2005
#
#----------------------------------------------------------------------------#

import os, sys
import optparse

import codecs

import kana

#----------------------------------------------------------------------------#

def separateAlignments(alignmentFile):
	""" Separates out the errors from the alignments, and tries to classify
		them.
	"""
	inputFile = codecs.open(alignmentFile, 'r', 'utf8')
	goodFile = codecs.open(alignmentFile + '.good', 'w', 'utf8')
	okuriganaFile = codecs.open(alignmentFile + '.okurigana', 'w', 'utf8')
	badFile = codecs.open(alignmentFile + '.bad', 'w', 'utf8')

	nGood = 0
	nBad = 0
	nOkurigana = 0
	for line in inputFile:
		lineTuple = line.strip().split(':')
		if len(lineTuple) == 2:
			goodFile.write(line)
			nGood += 1
		elif len(lineTuple) == 3:
			original, erronous, good = lineTuple
			if __detectOkurigana(good):
				nOkurigana += 1
				okuriganaFile.write(line)
			else:
				badFile.write(line)
			nBad += 1
	
	total = nGood + nBad
	print '%d total alignments' % total
	print '--> %.2f%% correct (%d)' % ((100*nGood / float(total)),nGood)
	print '--> %.2f%% in error (%d)' % ((100*nBad / float(total)),nBad)
	print '----> %.2f%% okurigana (%d)' % ((100*nOkurigana / float(total)),\
			nOkurigana)
	print '----> %.2f%% unknown (%d)' % ((100*(nBad-nOkurigana)/float(total)),\
			(nBad-nOkurigana))

	return

#----------------------------------------------------------------------------#

def __detectOkurigana(segmentation):
	""" Detects whether the correct solution contained an okurigana segment.
		These are characterized by mixed script.
	"""
	gSegments, pSegments = segmentation.split('-')
	gSegments = gSegments.strip('|').split('|')
	for segment in gSegments:
		scriptType = kana.scriptType(segment[0])
		if scriptType != 'kanji':
			continue

		for char in segment[1:]:
			if kana.scriptType(char) != 'kanji':
				return True
	else:
		return False

#----------------------------------------------------------------------------#

def createOptionParser():
	""" Creates an option parser instance to handle command-line options.
	"""
	usage = \
"""%prog [options] alignments

Separates out the different error types from the alignment file."""

	parser = optparse.OptionParser(usage)

	return parser

#----------------------------------------------------------------------------#

def main(argv):
	""" The main method for this module.
	"""

	parser = createOptionParser()
	(options, args) = parser.parse_args(argv)

	try:
		[alignmentFile] = args
	except:
		parser.print_help()
		sys.exit(1)

	# execute new code here
	separateAlignments(alignmentFile)
	
	return

#----------------------------------------------------------------------------#

if __name__ == '__main__':
	main(sys.argv[1:])

