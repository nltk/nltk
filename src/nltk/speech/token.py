##
# token.py: Tokenizing utilities for speech synthesis
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#	  Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
##

from nltk.token import *
import re


##
# SpeechTokenizer: Tokenizes text into lexemes for speech synthesis.
#
# The SpeechTokenizer is a variant of the NLTK RETokenizer that works by
# tokenizing text based on regular expressions. In addition, each token
# is then passed through a set of token-to-lexeme rules that will convert
# it to a list of lexemes suitable for speech synthesis.
#
# There is a default set of rules defined, and the user can also add their
# own rules. A rule is simply a regular expression to match a token, and
# a corresponding function which will take the token as an argument and
# return a list of lexical items corresponding to that token.
#
# In the SpeechTokenizer, because of the frequency of use of the regular
# expressions in each rule, they are first compiled into regular expression
# objects before being stored into the internal rules list.
##

import nltk.speech.rules as rules
class SpeechTokenizer(TokenizerI):

	##
	# Initializes the SpeechTokenizer.
	# The default set of rules are loaded only if an initial set
	# is not specified.
	# @param init_rules Initial set of rules
	##
	def __init__(self, init_rules = rules.default_rules):
		self.__rules = []
		self.add_rules(init_rules)


	##
	# Tokenizes text as per the specification of the TokenizerI interface.
	# @param str The text string to tokenize
	# @param source (optional) The source of the text
	##
	def tokenize(self, str, source=None):
		lexemes = []

		while str != '':
			match = None
			for ( regexpObj, func ) in self.__rules:
				match = regexpObj.match(str)
				if match:
					lexemes.extend( func(match.group()) )

					# Remove matched characters from string
					str = str[match.end():]
					break

			if not match:
				# No match: Skip one character
				str = str[1:]
					
		return [ Token( lexemes[i], Location(i, unit='w', source=source) )
			 for i in range(len(lexemes)) ]


	##
	# Adds a rule to the top of the rules list.
	# The regexp string is first compiled into a regular expression.
	# @param regexp The regular expression to match the token
	# @param func The function to apply to the matched tokens
	##
	def add_rule(self, regexp, func):
		self.__rules = [ (re.compile(regexp, re.DOTALL), func) ] + self.__rules


	##
	# Adds a list of custom rules to the top of the rules list
	# The first rule in the list will take precedence over the last rule
	# i.e. they are added to the beginning of the internal list in reverse order
	# @param rules The list of rules to add
	##
	def add_rules(self, rules):
		rules.reverse()
		for ( regexp, func ) in rules:
			self.add_rule(regexp, func)


##
# untokenize: Joins a list of tokens back into a string
#
# Tokens are joined such that spaces are added between word tokens,
# but not between other tokens.
#
# This is to preserve tokens such as punctuation which are not
# pronounced but still needed for pauses in speech synthesis.
#
# @param tokens The list of tokens to join
##

def untokenize(tokens):
	str = ''
	pattern = re.compile('\w+')

	for token in tokens:
		if pattern.match(token.type()):
			str = str + ' ' + token.type()
		else:
			str = str + token.type()

	return str
