##
# token_tts.py: text-to-speech wrapper that uses the Speech tokenizers
#
# Author: David Zhang <dlz@students.cs.mu.oz.au>
#         Steven Bird <sb@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# This module is intended to be used on top of the tts extension module. It
# defines similar functions to those in the tts module, but first passes the
# text through the speech tokenizers and untokenizers before sending the text
# to speech synthesis.
#
# All text-to-speech functions in this module return the text that was sent
# to the speech synthesis engine.
#
# Like the tts module the initialization of this module must be called before
# any other functions are called.
##

# speech modules
import nltk.speech.tts as tts
import nltk.speech.token as token
import nltk.speech.rules as rules
import urllib

##
# Passes text through the tokenizer and untokenizer
# @param s the text to process
##
def process(s):
	return token.untokenize(token.SpeechTokenizer().tokenize(s))


##
# Initializes the speech engine with default parameters
##
def initialize():
	tts.initialize()

##
# Initializes the speech engine with custom parameters
# @param heap_size Scheme heap size
# @param load_init_files Load init files?
##
def initialize_with(heap_size, load_init_files):
	tts.initialize(heap_size, load_init_files)


##
# Say the contents of a string
# @param s the string to say
##
def say_text(s):
	text = process(s)
	tts.say_text(text)
	return text


##
# Say the contents of a file
# @param file the file to say
##
def say_file(file):
	text = open(file).read()
	return say_text(text)


##
# Say the contents of a URL
# @param url the URL to say
##
def say_URL(url):
	# Set up SpeechTokenizer to handle HTML tags
	st = token.SpeechTokenizer()
	st.add_rules(rules.html_rules)

	text = urllib.urlopen(url).read()
	text = token.untokenize(st.tokenize(text))

	tts.say_text(text)
	return text


##
# Synthesizes the string into a wave file
# @param s the string to synthesize
# @param file the output wave file
##
def text_to_wave(s, file):
	text = process(s)
	tts.text_to_wave(text, file)
	return text
