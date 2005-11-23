# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# dictionary.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Mon May 16 10:50:57 EST 2005
#
#----------------------------------------------------------------------------#

""" This module is responsible for parsing input data sets for
	grapheme/phoneme string pairs to align. Its main methods are
	edictEntries() and evaluationEntries().
"""

#----------------------------------------------------------------------------#

import kana
import codecs

#----------------------------------------------------------------------------#

def __validEntry(entry):
	""" Returns True if the word is only kanji and kana, False otherwise.
	"""
	kanjiString, readingString = entry

	# throw out any reading which non-kana readings
	for char in readingString:
		if kana.scriptType(char) == 'kanji':
			return False
	
	if kana.containsRoman(kanjiString):
		return False
	else:
		return True
	
#----------------------------------------------------------------------------#

def edictEntries(inputFile):
	""" Determines all the kanji entries available in the input file. The input
		file is assumed to be in edict format.
	"""
	entries = []
	inputStream = codecs.open(inputFile, 'r', 'utf8')

	rejectionStream = codecs.open('logs/rejected-entries', 'w', 'utf8')

	numRejected = 0
	for line in inputStream:
		lineParts = line.split()
		kanji = lineParts[0]
		reading = lineParts[1][1:-1]
		entry = (kanji, reading)
		
		if __validEntry(entry):
			entries.append(entry)
		else:
			numRejected += 1
			rejectionStream.write(line)

	return entries, numRejected

#----------------------------------------------------------------------------#

def evaluationEntries(inputFile):
	""" Get entries from a file formatted like an evaluation type instead of
		in edict format.
	"""
	entries = []
	inputStream = codecs.open(inputFile, 'r', 'utf8')

	rejectionStream = codecs.open('logs/rejected-entries', 'w', 'utf8')

	numRejected = 0
	for line in inputStream:
		kanji, reading = line.split(':')[0].split('-')
		entry = (kanji, reading)
		
		if __validEntry(entry):
			entries.append(entry)
		else:
			numRejected += 1
			rejectionStream.write(line)

	return entries, numRejected

#----------------------------------------------------------------------------#

def __longestKanjiRun(kanjiString):
	run = 0
	longest = 0
	for char in kanjiString:
		if kana.scriptType(char) == 'kanji':
			run += 1
		else:
			if run > longest:
				longest = run
			run = 0
	else:
		if run > longest:
			longest = run
	
	return longest

#----------------------------------------------------------------------------#

def separateEntries(entries, maxRunLength):
	""" Split out the longest entries for later processing.
	"""
	shortEntries = []
	longEntries = []

	for entry in entries:
		kanjiString, readingString = entry
		if __longestKanjiRun(kanjiString) > maxRunLength:
			longEntries.append(entry)
		else:
			shortEntries.append(entry)
	
	return shortEntries, longEntries

#----------------------------------------------------------------------------#
