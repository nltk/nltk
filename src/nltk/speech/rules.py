##
# rules.py: Rules used by Speech Tokenizer
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#         Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# Defines sets of rules for the speech tokenizer.
#
# A rule is the pair
#	( regexp, func(s) )
#
# where
#	regexp: The regular expression to match a token
#	func: 	A function that takes the token as its single argument
#		and returns a list of corresponding lexical items
#
# Since the rules are processed in sequence rather than simultaneously,
# rules that use more specific patterns should come before those than use
# more general patterns.
##


import nltk.speech.numbers as numbers, nltk.speech.html as html

# Returns a list with the original string as its only element
def identity(s):
	return [s]

# Returns an empty list
def empty(s):
	return []


# Default rules used by the Speech Tokenizer
default_rules = [

	# Forms of numbers
	( r'\$\d+\.\d+', lambda s:		# decimal currency
		numbers.decToWords(s[1:]) + [ "dollars" ] ),

	( r'\$\d+', lambda s:			# integer currency
		numbers.numToWords(s[1:]) + [ "dollars" ] ),

	( r'\d+(st|nd|rd|th)', lambda s:	# ordinal number
		numbers.ordToWords(s[:-2]) ),

	( r'\d{1,3}(,\d{3,3})+', lambda s:	# comma-delimited integer
		numbers.numToWords(s.replace(',', '')) ),

	( r'\d+\.\d+', numbers.decToWords ),	# decimal digit string

	( r'\d+', numbers.numToWords ),		# integer digit string

	# Unpronounced separator-punctuation
	( r'[,.?!]', identity ),

	# Words
	( r'[a-zA-Z]+', identity ),

]


# Add these rules if the text is expected to be an HTML document
html_rules = [

	# Scripting languages: Not read
	( r'<SCRIPT.*?</SCRIPT>', empty ),
	( r'<script.*?</script>', empty ),

	# HTML tags
	( r'<.*?>', html.tagToWords ),

	# Special pronounced mark-up
	( r'&copy;', lambda s: ['copyright'] ),

	# Unpronounced mark-up
	( r'&.*?;', empty ),

]
