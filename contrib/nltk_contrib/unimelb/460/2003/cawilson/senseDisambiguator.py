#!/usr/local/bin/python

# 433- 460 Project
#
# Authors: Claire Louise Taylor (cltaylor) & Charlotte Wilson (cawilson)
# Date: October 2003
#
# Runs the Word Sense Disambiguation methods:
"""
The module contains methods to run the Word Sense Disambiguation system 
either in interactive or command-line mode. Additionally it contains some
demonstration functions for the translation module.  

"""
#############################################################

from naiveBayes import *
from parallelCorpus import *
from bagger import *
import re
from nltk.corpus import *
from nltk.tagger import *
from nltk.sense import *
from wordTranslator import *
from accuracy import *
import random

###############################################################

# the size of the portion of the senseval corpus to test on
test_portion= 300

# option lists to be displayed to the user
wsd_options= "Options: (1)Naive Bayes, (2)Bagging, (3)Basecase:"
corpus_options= "Options: (1)Senseval, (2)de-news parallel corpus,\
 (3)europarl parallel corpus:"
word_options= "Options: interest, hard, line or serve:"
context_options= "Options: (-1)Whole sentence, (0->)No. words either side\
 of the ambiguous word:"
replacement_message= "i.e. the number of samples to replace in bagging:"
sense_message= "Options: (0)no sense-grouping, (1->)No. of sense groups:"
europarl_message= "\nThe europarl corpus contains 353 training files.\n\
Training on all 353 files will take some time.\nPlease enter the number of\
 files to train on:"
europarl_options= "Options: (1-353)No. of files to train on:"

# invalid input messages to be displayed to the user
invalid_number= "\nInvalid option. Enter a number from the options below." 
invalid_word= "\nInvalid word. Enter a word from the options below."
invalid_context= "\nInvalid context window. Enter a number from the options\
 below." 
invalid_iterate = "\nInvalid number of iterations. Enter a positive number:"
invalid_replacement = "\nInvalid replacement value. Enter a positive number:"
invalid_numfiles = "\nInvalid number of files. Enter a positive number:"

#default settings
def_method=1
def_context_window=3
def_replacement=50
def_iterate=10
def_corpus=3
def_num_files=100
def_ambig_word="interest"
def_num_senses=2

###########################################################################

def wsd_interactive():
	"""
	Interactively gets the required system parameters as input from 
	the user and then calls senseDisambiguator to run the word sense 
	disambiguation system. Input parameters are validated as they are
	input. 
	"""

	print "Welcome to our Word Sense Disambiguation system."
	 
	# get the input paramaters interactively 
	# the WSD method to use
	options = range(1,4)	
	print "\nSelect a WSD method."
	try: method = int(raw_input(wsd_options))
	except ValueError: method = 0
	while options.count(method) == 0:
		print invalid_number
		try: method = int(raw_input(wsd_options))
		except ValueError: method = 0

	# the context window, where necessary
	context_window = None
	if method == 1 or method == 2:
		print "\nEnter a context window." 
		try: context_window = int(raw_input(context_options))
		except ValueError: context_window = -2 
		while context_window < -1:
			print invalid_context
			try: context_window = int(raw_input(context_options))
			except ValueError: context_window = -2 

	# options for bagging
	replacement = None
	iterate = None
	if method == 2:
		print "\nPlease enter a replacement value."
		try: replacement = int(raw_input(replacement_message))
		except ValueError: replacement = -2
		while replacement < 0:
			try: replacement = int(raw_input(invalid_replacement))
			except ValueError: replacement = -1

		try: iterate = int(raw_input("\nEnter the no. of iterations:"))
		except ValueError: iterate = -1
		while iterate < 0:
			try: iterate = int(raw_input(invalid_iterate))
			except ValueError: iterate = -1
		
	# the training corpus
	options = range(1,4)
	print "\nSelect a training corpus."
	try: corpus = int(raw_input(corpus_options))
	except ValueError: corpus = 0 
	while options.count(corpus) == 0:
		print invalid_number
		try: corpus = int(raw_input(corpus_options))
		except ValueError: corpus = 0 

	# the number of files to train on - if we've chosen europarl
	options = range(1,354)
	num_files = 0
	if corpus == 3:
		print europarl_message
		try: num_files = int(raw_input(europarl_options))
		except ValueError: num_files = 0 
		while options.count(num_files) == 0:
			print invalid_numfiles
			try: num_files = int(raw_input(europarl_options))
			except ValueError: num_files = 0 

	# the word to disambiguate
	options = ["interest", "hard", "line", "serve"]
	print "\nEnter a word to disambiguate."
	ambig_word = raw_input(word_options)
	while options.count(ambig_word) == 0:
		print invalid_word 
		ambig_word = raw_input(word_options)

	# the number of senses we want if using a parallel corpus
	num_senses = None
	if corpus == 2 or corpus == 3:
		print "\nEnter the number of senses to distinguish."
		try: num_senses = int(raw_input(sense_message))
		except ValueError: num_senses = -1 
		while num_senses < 0: 
			print invalid_number
			try: num_senses = int(raw_input(sense_message))
			except ValueError: num_senses = -1 

	# run the chosen word sense disambiguation method 
	senseDisambiguator(method, context_window, replacement, iterate, 
			corpus, num_files, ambig_word, num_senses)  
	return



def senseDisambiguator(method=def_method, context_window=def_context_window, 
		replacement=def_replacement, iterate=def_iterate, 
		corpus=def_corpus, num_files=def_num_files, 
		ambig_word=def_ambig_word, num_senses=def_num_senses):  
	"""
	Runs the Word Sense Disambiguation system with the specified 
	parameters. 

	Gets the senseval test data then sense tags the training data 
	(by training and running the translation module) if required.  
	Trains the required WSD method and runs this, printing precision, 
	recall and accuracy counts for each sense.   

	This method does no validation user input and therefore behaviour 
	on invalid input may be unpredictable. 
	"""
	# get the senseval corpus, tagged for the ambiguous word - 
	# it will be needed to test against
	senseval_filename = ambig_word + ".pos"
	senseval_data = senseval.tokenize(senseval_filename)

	# shuffle the data so we don't end up with all one sense at the end
	# of the list
	temp_data = []
	while len(senseval_data) > 0:
		temp_data.append(senseval_data.pop(random.randint(
			0, len(senseval_data)-1)))
	senseval_data = temp_data	
		
	###############################################################
	# Get the training corpus
	###############################################################
	if corpus == 1:
		# get a portion of the senseval corpus for training 
		training_data = senseval_data[test_portion:]

	else:
		if corpus == 2:
			num_files = 0 
			# construct the parallelCorpus reader for de_news
			de_en_corpus = parallelCorpus.de_news

		if corpus == 3:
			# construct the parallelCorpus reader for europarl 
			de_en_corpus = parallelCorpus.europarl

		print "Training the translation module- this takes some time."
		# train the word translation module on the ambiguous word 
		word_trans = WordTranslator()
		word_trans.train(ambig_word, de_en_corpus, num_files)	

		# get the english data, sense-tagged with the German 
		# sense-grouped translation
		print "Sense-tagging the training data- this takes some time."
		training_data = get_sense_labeled_text(word_trans, 
			ambig_word, de_en_corpus, num_senses)

	###############################################################
	# Train the WSD Method and then test it (using an untagged 
	# portion of the senseval corpus) 
	###############################################################

	disambiguator = None 
	# Simple Bayesian  
	if method == 1:
		disambiguator = simpleBayesian(ambig_word, context_window)
		#s = simpleBayesian(ambig_word, context_window)
	# Naive Bayes with bagging 
	elif method == 2:
		disambiguator = bagger(iterate, replacement, context_window,
					ambig_word)
	# Basecase
	elif method == 3:
		disambiguator = basecase(ambig_word)

	# train the disambiguation method
	print "Training the disambiguation method."
	disambiguator.train(training_data)

	# get some test data
	test_data = []
	for t in senseval_data[:test_portion]:
    		test_data += untag(t.type().text())

	# sense-tag the test data
	result = disambiguator.sense_tag(test_data)

	# print accuracy statistics - precision, recall etc.
	precision_recall(senseval_data[:test_portion],result,ambig_word)
	return 


################# Demo methods for the translation module ###############

def get_translation(word, sentence, corpus=def_corpus, num_files=def_num_files):
	"""
	Given an ambiguous English word and a German sentence, get the 
	English word's translation in that sentence. Train the word 
	translation module on the specified number of files of the 
	specified corpus.
	"""
	# construct and train the word translator
	word_trans = get_translator(word, corpus, num_files)

	# get the translation in the given sentence
	trans = word_trans.get_translation(sentence)
	print "Translation of", word, "in:\n", sentence, "\nis", trans  
	
	return


def get_translation_list(word, corpus=def_corpus, num_files=def_num_files):
	"""
	Given an English word, get it's top 20 German translations. Train 
	the word translation module on the specified number of files of the 
	specified corpus.
	"""
	# construct and train the word translator
	word_trans = get_translator(word, corpus, num_files)

	# get the list of the top 20 possible translations 
	trans_list = word_trans.get_translations()
	print "Top 20 translations of", word, "are:"  
	print trans_list[:20]
	
	return


def get_translator(word, corpus, num_files):
	"""
	Construct and train a word translator for the given English word. 
	Train the translator on the specified number of files in the 
	specified corpus. Return the word translator.
	"""
	if corpus != 2 and corpus != 3:
		print "Invalid corpus selected.\n See README for instructions."
		return

	if corpus == 2:
		num_files = 0 
		# construct the parallelCorpus reader for de_news
		de_en_corpus = parallelCorpus.de_news

	if corpus == 3:
		# construct the parallelCorpus reader for europarl 
		de_en_corpus = parallelCorpus.europarl

	print "Training the translation module- this takes some time."
	# train the word translation module on the ambiguous word 
	word_trans = WordTranslator()
	word_trans.train(word, de_en_corpus, num_files)	

	return word_trans
	 
	
############################## Utility Functions ##########################

def get_sense_labeled_text(word_trans, ambig_word, de_news, num_senses):
	"""
	Get the training text from the parallel corpus in the same format 
	as the senseval data. Tag the English section of the parallel corpus
	with the appropriate sense-tags. For each occurence of the 
	ambiguous word, tag according to the sense-group of its translation 
	(see the wordTranslator module for details).    

	Append each section od sense-labeled-text onto the data and return 
	the tagged data once completed.  
	"""
	sense_labeled_text = []

	for item in de_news.items():
		english_sents = open(de_news.path(item[0])).readlines()
		german_sents = open(de_news.path(item[1])).readlines()

		for i in xrange(len(english_sents)):
			english_sent = english_sents[i]
			english_sent = english_sent[0].lower() + \
					english_sent[1:]
	
			german_sent = german_sents[i]
			german_sent = german_sent[0].lower() + german_sent[1:]
				
			# get the list of english tokens
			english_tokens = WSTokenizer().tokenize(english_sent)
			english_taggedtokens = [Token(TaggedType(token.type(), 
				None)) for token in english_tokens]

			# check whether the sentence contains the ambiguous 
			# word if it doesn't we don't need it for training
			headIndex = contains(english_tokens, ambig_word)
			if headIndex == -1:
				continue	  
			else:
				#get the sense_tag for the ambiguous word in 
				#this context 
				sense_tag = word_trans.get_sense_tag(
					german_sent, num_senses)

				# create the sense-labeled-text
				if sense_tag != None:
					slt = SenseLabeledText(
						english_taggedtokens, 
						(sense_tag,), headIndex, 
						ambig_word)
					next_token = Token(slt, None) 
					sense_labeled_text.append(next_token)

	return sense_labeled_text	


def contains(sentence, word):
        """
        Checks whether this sentence contains the ambiguous word.
        Returns the position of the ambious word in the sentene, or -1 if
	the sentence does not contain the ambiguous word.

        @param sentence: list of tokens that make up a sentence
        @type sentence: List{tokens}

        @param ambig_word: the word we are looking for in the sentence
        @type ambig_word: C{string}

        @return: position of the word in the sentence or -1.
        @rtype: C{int}
        """
        for i in range(len(sentence)):
            if sentence[i].type() == word:
                return i

        return -1


#############################################################################
# for running the system  

if __name__ == '__main__':
        import sys
	# interactive mode
        if len(sys.argv) > 1 and sys.argv[1] == 'wsd':
                wsd_interactive()

	# command line mode
        elif len(sys.argv) > 1 and sys.argv[1] == 'sense_disambiguator':
		# use the defaults
		if len(sys.argv) == 2:
			senseDisambiguator()
		# user specifies all parameters 
		else:
                	senseDisambiguator(int(sys.argv[2]), int(sys.argv[3]), 
				int(sys.argv[4]), int(sys.argv[5]), 
				int(sys.argv[6]), int(sys.argv[7]), 
				sys.argv[8], int(sys.argv[9]))
	# Translation demo 1
	elif len(sys.argv) > 1 and sys.argv[1] == 'translate':
		# use the default corpus
		if len(sys.argv) == 4:
			get_translation(sys.argv[2], sys.argv[3])
		# user specifies all parameters 
		else:
			get_translation(sys.argv[2], sys.argv[3], 
				int(sys.argv[4]), int(sys.argv[5]))
	# Translation demo 2
	elif len(sys.argv) > 1 and sys.argv[1] == 'translate_list':
		# use the default corpus
		if len(sys.argv) == 3:
			get_translation_list(sys.argv[2])
		# user specifies all parameters 
		else:
			get_translation_list(sys.argv[2], int(sys.argv[3]), 
				int(sys.argv[4]))

	# interactive mode -the default
        else:
               wsd_interactive() 

