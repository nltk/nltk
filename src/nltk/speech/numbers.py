##
# numbers.py: Numbers helper module for Speech Tokenizer
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#	  Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# This module contains various functions to process different kinds of
# numbers, including digits, decimal numbers, dates, times and cardinals.
##

import re


### Dictionary of Numbers ###

# Primary Dictionaries
units = {
	'0': '',	# Zero is handled differently
	'1': 'one',
	'2': 'two',
	'3': 'three',
	'4': 'four',
	'5': 'five',
	'6': 'six',
	'7': 'seven',
	'8': 'eight',
	'9': 'nine',
}

teens = {
	'0': 'ten',
	'1': 'eleven',
	'2': 'twelve',
	'3': 'thirteen',
	'4': 'fourteen',
	'5': 'fifteen',
	'6': 'sixteen',
	'7': 'seventeen',
	'8': 'eighteen',
	'9': 'nineteen',
}

tens = {
	'2': 'twenty',
	'3': 'thirty',
	'4': 'forty',
	'5': 'fifty',
	'6': 'sixty',
	'7': 'seventy',
	'8': 'eighty',
	'9': 'ninety',
}

powers = [
	'',
	'thousand',
	'million',
	'billion',
	'trillion',
	'quadrillion',
	'quintrillion',
	'sextillion',
	'septillion',
]

# Secondary Dictionaries
ordinals = {
	'one':	  'first',
	'two':	  'second',
	'three':  'third',
	'four':	  'fourth',
	'five':	  'fifth',
	'six': 	  'sixth',
	'seven':  'seventh',
	'eight':  'eighth',
	'nine':	  'ninth',

	'twelve': 'twelfth'
}


### Module Functions ###

# Returns in a list the digit string in groups of 3

def group(s):
	# Pad digit string with 0 until it has a multiple of 3 digits
	while len(s) % 3 != 0:
		s = '0' + s

	# Add spaces between each group of 3 digits
	s_spaced = re.sub(r'(\d{3})', r'\1 ', s)
	return s_spaced.split()


# Converts a 3-digit number into words in a list

def numToWords3(s):
	( hundred, ten, one ) = tuple(s)
	words = []

	if ten == '0':
		words = [ units[one] ]
	elif ten == '1':
		words = [ teens[one] ]
	else:
		words = [ tens[ten], units[one] ]

	if hundred != '0':
		if words == ['']:
			words = [ units[hundred], 'hundred' ]
		else:
			words = [ units[hundred], 'hundred', 'and' ] + words

	return words


##
# Converts an integer string into words in a list
# Uses digitToWords if number is too big
# BUG: 1001 gives "one thousand one", and similar
# @param s the integer number in a string
##

def numToWords(s):
	if len(s) > len(powers)*3:
		return digitToWords(s)

	groups = group(s)
	groups.reverse()

	words = []
	for i in range(len(groups)):
		group_word = numToWords3(groups[i])

		if group_word != ['']:
			words = group_word + [ powers[i] ] + words


	# Is it zero?
	if words == []:
		words = [ 'zero' ]

	# Remove blank strings
	words = [ word for word in words if word != '' ]

	return words


##
# Converts a decimal string into words in a list
# @param s the decimal number in a string
##

def decToWords(s):
	parts = s.split( '.', 1 )	# Split into integer and decimal part
	return numToWords( parts[0] ) + [ "point" ] + digitToWords( parts[1] )
	

##
# Converts a digit string into digit words in a list
# @param s the digits in a string
##

def digitToWords(s):
	words = []

	for d in s:
		if units[d] == '':
			words.append( 'zero' )
		else:
			words.append( units[d] )

	return words


##
# Converts an integer into its ordinal form, returning the words in a list
# Uses numToWords, then converts the final word to its ordinal form
# @param s the integer number in a string
##

def ordToWords(s):
	words = numToWords(s)
	final_word = words[-1]

	# Final word is a special word: Use look-up table
	if ordinals.has_key(final_word):
		final_word = ordinals[final_word]

	# Final word is an umpty : Remove 'ty' and add 'tieth'
	elif final_word[-2:] == 'ty':
		final_word = final_word[:-2] + 'tieth'

	# Anything else: Just add 'th'
	else:
		final_word += 'th'

	words[-1] = final_word
	return words
