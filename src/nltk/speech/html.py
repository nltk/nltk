##
# html.py: HTML helper module for Speech Tokenizer
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#	  Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# This module processes HTML tags for speech synthesis.
##

import re


# Speech for tags
# All tags are in uppercase

tag_talk = {
	'<H1>':		'level one heading',
	'<P>':		'new paragraph',
}


##
# Converts HTML tags to words
# @param tag the html tag to speak
##

def tagToWords(tag):
	tag = tag.upper()
	words = []

	# Basic tags
	if tag_talk.has_key(tag):
		words = tag_talk[tag].split()

	# Image tag: Read ALT text
	elif tag[:4] == '<IMG':
		match = re.search(r"""ALT=['"]?([\w\d\s]*)['"]?""", tag)
		if match:
			words = ['image', '!'] + match.group(1).split()

	if words != []:
		# Exclamation marks used to force a pause between tags
		return ['!'] + words + ['!']
	else:
		return []
