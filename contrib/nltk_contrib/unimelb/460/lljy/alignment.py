# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# alignment.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Mon May 16 11:24:31 EST 2005
#
#----------------------------------------------------------------------------#

""" This module implements the iterative TF-IDF method.
"""

#----------------------------------------------------------------------------#

import potentials
import kana

import math
from sets import Set
import codecs

from progressBar import ProgressBar

#----------------------------------------------------------------------------#

# epsilon for testing for zero
eps = 1e-8

#----------------------------------------------------------------------------#

class FrequencyMap:
	def __init__(self):
		self.__graphemes = {}
		return
	
	def addCounts(self, alignment):
		""" This method updates all the counts associated with the entry.
		"""
		gSegments, pSegments = alignment
		for i in range(len(gSegments)):
			if kana.scriptType(gSegments[i]) == 'kanji':
				g, gp, gpc = self.__getContext(gSegments, pSegments, i)
				if not self.__graphemes.has_key(g):
					# if we don't have g, we can't have gp, gpc
					self.__graphemes[g] = (1, {gp: (1, {gpc: 1})})
				else:
					gCount, gpDict = self.__graphemes[g]
					gCount += 1
					if not gpDict.has_key(gp):
						# without gp, we also can't have gpc
						gpDict[gp] = (1, {gpc: 1})
					else:
						gpCount, gpcDict = gpDict[gp]
						gpCount += 1
						if not gpcDict.has_key(gpc):
							gpcDict[gpc] = 1
						else:
							gpcDict[gpc] += 1
						gpDict[gp] = gpCount, gpcDict
					self.__graphemes[g] = gCount, gpDict

		return
	
	def delCounts(self, alignment):
		""" This method updates all the counts associated with the entry.
		"""
		gSegments, pSegments = alignment
		for i in range(len(gSegments)):
			if kana.scriptType(gSegments[i]) == 'kanji':
				g, gp, gpc = self.__getContext(gSegments, pSegments, i)
				gCount, gpDict = self.__graphemes[g]
				gCount -= 1
				if gCount < 1:
					del self.__graphemes[g]
					continue

				gpCount, gpcDict = gpDict[gp]
				gpCount -= 1
				if gpCount < 1:
					del gpDict[gp]
					self.__graphemes[g] = gCount, gpDict
					continue

				gpcCount = gpcDict[gpc]
				gpcCount -= 1
				if gpcCount < 1:
					del gpcDict[gpc]
				else:
					gpcDict[gpc] = gpcCount

				gpDict[gp] = gpCount, gpcDict
				self.__graphemes[g] = gCount, gpDict

		return
		
	def __getContext(self, gSegments, pSegments, index):
		""" Determine the context needed for calculations or for frequency
			updates.
		"""
		grapheme = gSegments[index]
		phoneme = pSegments[index]

		# determine the left context...
		if index > 0:
			leftG = gSegments[index-1]
			leftP = pSegments[index-1]
		else:
			leftG = None
			leftP = None

		# ...and the right context 
		if index < len(gSegments) - 1:
			rightG = gSegments[index+1]
			rightP = pSegments[index+1]
		else:
			rightG = None
			rightP = None

		return grapheme, phoneme, (leftG, leftP, rightG, rightP)
	
	def frequencies(self, gSegments, pSegments, index):
		""" Calculates the frequencies of occurence of the segment specified
			within the alignment.
		"""
		g, gp, gpc = self.__getContext(gSegments, pSegments, index)

		gFreq, gpDict = self.__graphemes.get(g, (0, {}))
		gpFreq, gpcDict = gpDict.get(gp, (0, {}))
		gpcFreq = gpcDict.get(gpc, 0)

		return gFreq, gpFreq, gpcFreq
	
#----------------------------------------------------------------------------#
#----------------------------------------------------------------------------#

class AutoAlignment:
	""" This class is responsible for the alignment algorithm, and all its
		internal data structures.
	"""
	def __init__(self, alignedReadings, outputFile, options):
		""" Creates a new instance using the list of correctly aligned
			readings.
		"""
		print '--> Initialising aligned readings'
		self.__uniqueCounts = FrequencyMap()
		self.__ambiguousCounts = FrequencyMap()

		# we write aligned readings as we go, rather than storing them in
		# memory
		self.__output = codecs.open(outputFile, 'w', 'utf8')
		self.__outputName = outputFile

		# add all unambiguous readings to our model
		for entry in alignedReadings:
			self.__uniqueCounts.addCounts(entry)
			potentials.printSolution(entry, self.__output)

		# keep a list of ambiguous alignments, of the form
		# (bestScore, [(score, alignment)])
		self.__ambiguous = []
	
		self.__alpha = options.alpha
		self.__solved = options.solved
		self.__unsolved = options.unsolved

		return

	def __addAmbiguous(self, ambiguousEntries):
		""" Updates the counts for ambiguous readings.
		"""
		for (base, ambigousReadings) in ambiguousEntries:
			assert len(Set(ambigousReadings)) == len(ambigousReadings)

			# update our counts
			for entry in ambigousReadings:
				self.__ambiguousCounts.addCounts(entry)

			self.__ambiguous.append(
					(
						0.0, # best score so far
						[(0.0, x) for x in ambigousReadings] # dummy scores
					)
				)

		return
 
	def getAlignments(self):
		""" Returns the current list of aligned readings.
		"""
		return self.__aligned

	def __disambiguateEntry(self, entry):
		""" Output a disambiguated entry, and update counts to match.
		"""
		bestScore, alignments = entry
		for i in range(len(alignments)):
			score, bestAlignment = alignments[i]
			if score == bestScore:
				break
		else:
			raise Exception, "best score wasn't found -- something fishy"

		del alignments[i]

		# put this count amongst the unique ones
		self.__uniqueCounts.addCounts(bestAlignment)

		# fill in the rest of this count
		# eliminate the bad readings from the model
		for score, alignment in alignments:
			self.__ambiguousCounts.delCounts(alignment)

		return bestAlignment

	def __rescore(self):
		""" Loops over the entire list of ambiguous entries, rescoring each.
		"""
		for i in xrange(len(self.__ambiguous)):
			oldBestScore, alignments = self.__ambiguous[i]
			newBestScore = 0.0
			for j in range(len(alignments)):
				oldScore, alignment = alignments[j]
				newScore = self.tfidf(alignment)
				if newScore > newBestScore:
					newBestScore = newScore
				alignments[j] = newScore, alignment

			self.__ambiguous[i] = newBestScore, alignments

		return

	def disambiguate(self, ambiguousReadings, options):
		""" Incorporates and aligns the ambiguous readings based on existing
			alignments.
		"""
		self.__addAmbiguous(ambiguousReadings)

		maxEntries = options.maxEntries
		if not maxEntries:
			maxEntries = len(self.__ambiguous)

		if options.verbose:
			self.__verboseDisambiguate(maxEntries)

		progressBar = ProgressBar()
		progressBar.start(maxEntries)

		i = 0
		while i < maxEntries:
			self.__rescore()
			self.__ambiguous.sort()
			bestEntry = self.__ambiguous.pop()
			alignment = self.__disambiguateEntry(bestEntry)
			potentials.printSolution(alignment, self.__output)
			i += 1
			progressBar.update(i)

		progressBar.finish()

		return
	
	def __verboseDisambiguate(self, maxEntries):
		""" Disambiguates in a verbose manner.
		"""
		i = 0
		while i < maxEntries:
			print '%d left' % len(self.__ambiguous)
			print '--> Rescoring...'
			self.__rescore()
			print '--> Sorting...'
			self.__ambiguous.sort()
			bestEntry = self.__ambiguous.pop()
			alignment = self.__disambiguateEntry(bestEntry)
			potentials.printSolution(alignment, self.__output)
			self.__explainAlignment(bestEntry, alignment)
			i += 1

		return
	
	def __explainAlignment(self, entry, alignment):
		"""
		"""
		bestScore, allAlignments = entry
		print '--->', bestScore,
		potentials.printAlignment(alignment)
		allAlignments.sort()
		allAlignments.reverse()
		for otherScore, otherAlignment in allAlignments:
			print '----->', otherScore,
			potentials.printAlignment(otherAlignment)
	
		return

	def finish(self, evaluationFile=None):
		""" Closes the output stream and sorts the output for easier
			comparison.
		"""
		self.__output.close()
		fStream = codecs.open(self.__outputName, 'r', 'utf8')
		lines = fStream.readlines()
		fStream.close()
		lines.sort()
		
		fStream = codecs.open(self.__outputName, 'w', 'utf8')
		if evaluationFile:
			# perform evaluation, incorporate corrections into output
			evalLines = codecs.open(evaluationFile, 'r', 'utf8').readlines()
			if len(evalLines) == len(lines):
				nLines = 0
				nCorrect = 0
				for line, evalLine in zip(lines, evalLines):
					nLines += 1
					if line != evalLine:
						line = line.strip() + ':' + evalLine.split(':')[1]
					else:
						nCorrect += 1
					fStream.write(line)
	
				print 'Got %.2f%% correct!' % (nCorrect*100.0/nLines)
				return
			else:
				print "Can't evaluate, missing %d entries" % \
						len(evalLines)-len(lines)

		for line in lines:
			fStream.write(line)

		return
	
	def __weightedFreqs(self, gSegments, pSegments, index):
		""" Weight the frequencies from the two models.
		"""
		s_gFreq, s_gpFreq, s_gpcFreq = self.__uniqueCounts.frequencies(
				gSegments, pSegments, index)
		u_gFreq, u_gpFreq, u_gpcFreq = self.__ambiguousCounts.frequencies(
				gSegments, pSegments, index)

		gFreq = self.__solved*s_gFreq + self.__unsolved*u_gFreq
		gpFreq = self.__solved*s_gpFreq + self.__unsolved*u_gpFreq
		gpcFreq = self.__solved*s_gpcFreq + self.__unsolved*u_gpcFreq

		return gFreq, gpFreq, gpcFreq
		
	def tfidf(self, alignment):
		""" Calculates the tf-idf score of the alignment passed in based on
			the current model.
		"""
		currentScores = []
		gSegments, pSegments = alignment
		for i in range(len(gSegments)):
			if not kana.scriptType(gSegments[i]) == 'kanji':
				continue

			gFreq, gpFreq, gpcFreq = self.__weightedFreqs(gSegments,
					pSegments, i)

			tf = (gpFreq + self.__alpha - self.__unsolved) / gFreq

			idf = math.log(gpFreq/(gpcFreq + self.__alpha - self.__unsolved))

			currentScores.append(tf*idf)
 
		newScore = sum(currentScores) / float(len(currentScores))

		return newScore
	

#----------------------------------------------------------------------------#

