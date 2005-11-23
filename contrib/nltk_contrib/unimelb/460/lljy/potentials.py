# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# potentials.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Sun May 15 22:41:16 EST 2005
#----------------------------------------------------------------------------#

""" This module is responsible for generating all possible segmentations for
	each grapheme string/phoneme string pair. The main method exported is the
	generateAlignments() method.
"""

#----------------------------------------------------------------------------#

import kana
import stats
import potentials

import string
import sys
from sets import Set
import codecs

#----------------------------------------------------------------------------#

def segmentToString(segment):
	return string.join(segment, '|')

def alignmentToString(alignment):
	return segmentToString(alignment[0]) +' - '+ segmentToString(alignment[1])

def printSegment(segment, stream=sys.stdout):
	print >> stream, string.join(segment, '|')
	return

def printAlignment(alignment, stream=sys.stdout):
	print >> stream, '|'.join(alignment[0]) + ' - ' + '|'.join(alignment[1])
	return

#----------------------------------------------------------------------------#

def printSolution(alignment, stream=sys.stdout):
	alignment = '|' + '|'.join(alignment[0]) + '|-|' + \
			'|'.join(alignment[1]) + '|'
	original = filter(lambda x: x != '|', alignment)
	print >> stream, original + ':' + alignment
	return

#----------------------------------------------------------------------------#

def __kanjiAlignments(kanjiString):
	""" Determine all possible segmentations of the mixed script entry string
		only, leaving the hiragana reading string untouched for now.
	"""
	forcedSegments = ()
	lastScriptType = kana.scriptType(kanjiString[0])
	currentSegment = ''
	for char in kanjiString:
		if kana.scriptType(char) == lastScriptType:
			currentSegment += char
		else:
			lastScriptType = kana.scriptType(char)
			forcedSegments += currentSegment,
			currentSegment = char
	else:
		if currentSegment:
			forcedSegments += currentSegment,
	
	combinationSets = []
	for segment in forcedSegments:
		if len(segment) > 1 and kana.scriptType(segment[0]) == 'kanji':
			combinationSets.append(stats.segmentCombinations(segment))
		else:
			combinationSets.append([(segment,)])
	
	allPossible = stats.combinations(combinationSets)

	return allPossible

#----------------------------------------------------------------------------#

def __matchSegments(readingString, segmentedKanji):
	""" Creates one or more segmentations which match the kanji segments with
		the reading string.
	"""
	# where there's only one segment, no worries
	numSegments = len(segmentedKanji)
	if numSegments == 1:
		return [(segmentedKanji, (readingString,))]

	potentials = [((), readingString)]
	for i in range(numSegments):
		newPotentials = []
		thisSegment = segmentedKanji[i]
		nMoreSegments = numSegments - i - 1
		finalSegment = (numSegments == i+1)

		if kana.scriptType(thisSegment) == 'kanji':
			# for each potential, generate many possible alignments
			for existingSegments, remainingReading in potentials:
				maxSegLength = len(remainingReading) + i - numSegments + 1
				for j in range(1, maxSegLength+1):
					newSegments = existingSegments + (remainingReading[:j],)
					newRemainingReading = remainingReading[j:]
					if not finalSegment or not newRemainingReading:
						newPotentials.append((newSegments, newRemainingReading))

		else:
			# only keep each potential if it lined up with this kana
			katakanaSeg = kana.katakanaForm(thisSegment)
			for existingSegments, remainingReading in potentials:
				kanaReading = kana.katakanaForm(remainingReading)
				if kanaReading.startswith(katakanaSeg):
					existingSegments += (thisSegment,)
					remainingReading = remainingReading[len(katakanaSeg):]
					if not finalSegment or not remainingReading:
						newPotentials.append(
								(existingSegments, remainingReading)
							)

		potentials = newPotentials
	
	return [(segmentedKanji, x) for (x,y) in potentials]

#----------------------------------------------------------------------------#

def __pruneAlignments(alignments, options):
	""" Applies additional constraints to the list of alignments, returning a
		subset of that list.
	"""
	keptAlignments = []
	for kanjiSeg, readingSeg in alignments:
		assert len(kanjiSeg) == len(readingSeg)
		for i in range(len(readingSeg)):
			rSeg = readingSeg[i]
			kSeg = kanjiSeg[i]

			# don't allow reading segments to start with ゅ or ん
			if kana.scriptType(kSeg) == 'kanji' and \
					(rSeg[0] == kana.nKana or rSeg[0] in kana.smallKanaSet):
				break

			# don't allow kanji segments with more than 4 kana per kanji
			rSegShort = filter(lambda x: x not in kana.smallKanaSet, rSeg)
			maxLength = options.maxPerKanji*len(kSeg)
			if kana.scriptType(kSeg) == 'kanji' and len(rSegShort) > maxLength:
				break
		else:
			keptAlignments.append((kanjiSeg, readingSeg))

	return keptAlignments

#----------------------------------------------------------------------------#

def __readingAlignments(readingString, partialAlignments, options):
	""" For each segmented kanji string, this method segments the reading to
		match.
	"""
	finalAlignments = []
	for alignment in partialAlignments:
		finalAlignments.extend(__matchSegments(readingString, alignment))
	
	finalAlignments = __pruneAlignments(finalAlignments, options)

	return finalAlignments

#----------------------------------------------------------------------------#

def __allAlignments(entry, options):
	""" Determine all possible kanji/reading segmentations and aligments,
		taking linguistic constraints into account.
	"""
	kanjiString, readingString = entry
	partialAlignments = __kanjiAlignments(kanjiString)
	finalAlignments = __readingAlignments(readingString, partialAlignments,
			options)

	assert len(Set(finalAlignments)) == len(finalAlignments), \
			"duplicate alignments detected"

	return finalAlignments

#----------------------------------------------------------------------------#

def generateAlignments(entries, options):
	""" Generates all possible alignments for each entry/reading pair in the
		input list.

		@param entries: A list of (grapheme string, phoneme string) pairs.
		@type entries: [(str, str)]
		@return: A pair (unique alignments, ambiguous alignments) where the
		second member is a list of (graphemeString, [potentialAlignments]).
	"""
	uniqueEntries = []
	ambiguousEntries = []

	overconstrained = codecs.open('logs/overconstrained', 'w', 'utf8')

	for entry in entries:
		alignments = __allAlignments(entry, options)
		if not alignments:
			print >> overconstrained, entry[0], '[' + entry[1] + ']'
			continue
			
		if len(alignments) == 1:
			[uniqueAlignment] = alignments
			uniqueEntries.append(uniqueAlignment)
		else:
			ambiguousEntries.append((entry[0], alignments))

	return uniqueEntries, ambiguousEntries

#----------------------------------------------------------------------------#
