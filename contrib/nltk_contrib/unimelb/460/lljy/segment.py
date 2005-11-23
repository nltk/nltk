#!/usr/bin/python
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# segment.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Sat May 14 14:49:45 EST 2005
#
#----------------------------------------------------------------------------#

""" This module is an executable script performing grapheme-phoneme alignment
	based on papers by Baldwin and Tanaka.
"""

#----------------------------------------------------------------------------#

import os, sys
import optparse
import pdb
import codecs

sys.stdout = codecs.getwriter('utf8')(sys.stdout)

import potentials
import dictionary
import alignment

#----------------------------------------------------------------------------#
# MAIN METHOD
#

def performSegmentation(inputFile, outputFile, options):
	""" The main method for this module. Performs the entire segmentation run,
		taking an edict dictionary as input and producing a segmented output
		for each kanji input row.
	"""
	# read in edict dictionary
	print 'Reading entries'
	if options.evaluation:
		entries, numRejected = dictionary.evaluationEntries(inputFile)
	else:
		entries, numRejected = dictionary.edictEntries(inputFile)
	print '--> found %d entries (rejected %d)' % (len(entries), numRejected)

	print 'Separating long and short entries'
	shortEntries, longEntries = dictionary.separateEntries(entries,
			options.longestRun)
	print '--> %d short, %d long' % (len(shortEntries), len(longEntries))

	# short entries
	print 'Considering short entries'
	print 'Generating possible alignments'
	(unique, ambiguous) = potentials.generateAlignments(shortEntries, options)
	print '--> %d unique, %d ambiguous' % (len(unique), len(ambiguous))
	del shortEntries
	print 'Processing unique entries'
	aligner = alignment.AutoAlignment(unique, outputFile, options)
	del unique
	print 'Disambiguating readings'
	aligner.disambiguate(ambiguous, options)
	del ambiguous

	# preprocess edict, creating all potential readings
	print 'Considering long entries'
	print 'Generating possible alignments'
	(unique, ambiguous) = potentials.generateAlignments(longEntries, options)
	del longEntries
	print '--> %d unique, %d ambiguous' % (len(unique), len(ambiguous))
	assert not unique, "Shouldn't have any unique long alignments"
	print 'Disambiguating readings'
	aligner.disambiguate(ambiguous, options)
	del ambiguous

	print 'Segmentation complete, sorting output'
	if options.evaluation:
		aligner.finish(inputFile)
	else:
		aligner.finish()

	return

#----------------------------------------------------------------------------#
# COMMAND-LINE INTERFACE
#

def createOptionParser():
	""" Creates an option parser instance to handle command-line options.
	"""
	usage = \
"""%prog [options] inputEntryFile outputFile

An efficient implementation of the Baldwin-Tanaka automated grapheme-phoneme
alignment algorithm based on TF-IDF."""

	parser = optparse.OptionParser(usage)

	parser.add_option('--max-per-kanji', action='store', dest='maxPerKanji',
			type='int', default=5,
			help='The maximum number of kana aligned to one kanji [5]')

	parser.add_option('--longest-run', action='store', dest='longestRun',
			type='int', default=4,
			help='The longest kanji run to be handled in the first pass [4]')

	parser.add_option('-e', '--evaluation', action='store_true',
			dest='evaluation', help='Indicates an evaluation run [False]')

	parser.add_option('-t', '--test-run', action='store', type='int',
			dest='maxEntries',
			help='Only segment the first NUMENTRIES entries, then exit.')

	parser.add_option('-v', '--verbose', action='store_true', dest='verbose',
			help='Enable verbose output [False]')

	parser.add_option('-a', '--alpha', action='store', dest='alpha',
			default=0.5, type='float',
			help='The smoothing value to use in tf-idf [0.05]')

	parser.add_option('-s', '--solved', action='store', dest='solved',
			default=1.0, type='float',
			help='The weight of solved frequencies in the tf-idf equation')

	parser.add_option('-u', '--unsolved', action='store', dest='unsolved',
			default=0.5, type='float',
			help='The weight of unsolved frequencies in the tf-idf equation')

	return parser

#----------------------------------------------------------------------------#

def main(argv):
	""" The main method for this module.
	"""
	parser = createOptionParser()
	(options, args) = parser.parse_args(argv)

	try:
		[inputDict, outputFile] = args
	except:
		parser.print_help()
		sys.exit(1)

	# execute new code here
	performSegmentation(inputDict, outputFile, options)
	
	return

#----------------------------------------------------------------------------#

if __name__ == '__main__':
	try:
		import psyco
		psyco.profile()
	except:
		pass

	try:
		main(sys.argv[1:])
	except KeyboardInterrupt:
		# we cancel runs often, so do it nicely
		print >> sys.stderr, '\nAborting run!'
		sys.exit(1)

#----------------------------------------------------------------------------#

