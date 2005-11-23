# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------#
# stats.py
# Lars Yencken <lars.yencken@gmail.com>
# vim: ts=4 sw=4 noet tw=78:
# Mon May 16 14:18:59 EST 2005
#
#----------------------------------------------------------------------------#

""" This module is responsible for any general combinatoric methods, in
	particular determining possible combinations of input.
"""

#----------------------------------------------------------------------------#

def combinations(combinationList):
	""" Generates a list of all possible combinations of one element from the
		first item in combinationList, one from the second, etc. For example::
	"""
	allCombinations = combinationList[0]

	for i in range(1, len(combinationList)):
		newAllCombinations = []
		for extra in combinationList[i]:
			for item in allCombinations:
				newAllCombinations.append(item + extra)

		allCombinations = newAllCombinations

	return allCombinations

#----------------------------------------------------------------------------#

def segmentCombinations(kanjiString):	
	""" Determines the possible segment combinations a kanji-only string. For
		example::

			> segmentCombinations('学校')
			[(学,校),(学校)]
		
	"""
	possibleSegments = [[kanjiString[0]]]
	for char in kanjiString[1:]: 
		newPossibleSegments = []
		for segment in possibleSegments:
			newPossibleSegments.append(segment + [char])
			segment[-1] += char
			newPossibleSegments.append(segment)
		possibleSegments = newPossibleSegments
	
	possibleSegments = map(tuple, possibleSegments)

	return possibleSegments

#----------------------------------------------------------------------------#

