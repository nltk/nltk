# 433-460 Project
# Author: Charlotte Wilson (cawilson)
# Date:	  October 2003
# 
# Word Translation and Sense-Tag Generation Module-
"""
This module contains the wordTranslator class which works out the possible 
translations of a word which we aim to disambiguate (called from the 
senseDisambiguator module). This uses a sentence-aligned bilingual training 
corpus with one sentence per line to train a statistical translation method.
The statistcal method is based on contingency tables and phi squared scores 
as described in William A. Gale and Kenneth Ward Church (1991), "Identifying 
Word Correspondences in Parallel Texts" Proceedings of the DARPA SNL Workshop.

This module also contains methods to return the word's translation in a 
given sentence and to group these possible translations into "sense groups" 
according to common morphology. 
"""


from nltk.probability import FreqDist
from nltk.tokenizer import WSTokenizer
from __future__ import division
import re

##############################################################################

class WordTranslator:
	"""
	A class to work out the translation of an English word in a given 
	German sentence and to group translations with a common morpheme 
	into a single "sense group".  

	The translation is performed using a statistical method - phi 
	squared - (as described below) and is trained on a one-to-one 
	sentence aligned bilingual corpus with one sentence per line. 

	Translations can then be grouped by common morphology into (rather
	fuzzy) sense groupings. This allows for translation morphemes occuring
	in compound words and is unnecessary if the corpus were stemmed
	(including compound splitting) before training. 

	For further discussion of these issues see the associated report.
	"""
	
	def __init__(self):
                """
                Constructor function for WordTranslator. Create a frequency
                distribution for the ambiguous word, its possible translations
		and their co-occurences. Inititalize class variables -
		the ambiguous word, the total number of aligned sentences, 
		a list of possible translations and mappings of those 
		translations to sense groupings.   
                """
                self._cooccur_fdist = FreqDist()
                self._ambig_word_fdist = FreqDist()
                self._trans_fdist = FreqDist()

		self._ambig_word = None
		self._num_sents = 0
		self._poss_translations = None
		self._sense_dict = None
		self._sense_list = None
		

	def train(self, ambig_word, de_en_corpus, numfiles=0):
		"""
		Train the word translator for the given ambiguous word on 
		the corresponding corpus files. If numfiles is 0 train
		on the whole corpus, otherwise train on either the number 
		of files specified or the whole corpus, whichever is smaller. 
		"""
		# set the ambiguous word to train on
		self._ambig_word = ambig_word

		# train the word translator for the given word on the 
		# parallel corpus
		if numfiles == 0 or numfiles > len(de_en_corpus.items()):
			numfiles = len(de_en_corpus.items()) 	
		for i in range(numfiles):
			english_file = de_en_corpus.items()[i][0]
			german_file = de_en_corpus.items()[i][1]

			self.train_file(de_en_corpus.path(english_file),
				de_en_corpus.path(german_file))	
		return


	def train_file(self, english_filename, german_filename):
		"""
		Given corresponding corpus files - 1 per language, 
	 	train the word translator on them. Parallel corpus files 
		are assumed to be one-to-one sentence aligned and to contain 
		one sentence per line.	
		Perform some preprocessing such as the removal of sentence 
		intital capitalisation, sentence tokenization and removal of 
		document titles. German nouns and proper nouns are 
		capitalised and thus we don't want convert the whole sentence 
		to lower case as we would lose important contextual 
		information.    
		Increment frequency counts for both co-occurence and individual
		frequecies. i.e. counts of the number of times the ambiguous 
		English word occurs, the number of times every German word 
		occurs and the number of times the a German word co-occurs 
		in an aligned sentence with the ambiguous English word. 
		Note: sentence punctuation is not included in these frequency 
		counts.
		"""

		#our corpus has one sentence per line so read line by line 
		english_sents = open(english_filename).readlines()
		german_sents = open(german_filename).readlines()

		# increment the sentence count
		num_sents = len(english_sents)
		self._num_sents = self._num_sents + num_sents

		# remove sentence initial capitalisation - German nouns 
		# begin with a capital letter, therefore just lower the 
		# first sentence character 
		for sent_num in xrange(num_sents):  
			english_sent = english_sents[sent_num]
			english_sent = english_sent[0].lower() + \
					english_sent[1:]

			german_sent = german_sents[sent_num]
			german_sent = german_sent[0].lower() + german_sent[1:]
			
			# tokenize the sentences
			english_tokens = WSTokenizer().tokenize(english_sent)
			german_tokens = WSTokenizer().tokenize(german_sent) 

			# discard if the line contains a doc title 
			if len(english_tokens) > 0 and len(german_tokens) > 0:
				doc_regexp = re.compile(r'<DOC')
				if doc_regexp.match(english_tokens[0].type()) \
					and doc_regexp.match(
					german_tokens[0].type()):     
					continue
			
		
			# increment the frequency counts - both co-occurence
			# frequency and individual frequencies
			contains_ambig_word = False 

			# find the ambiguous word in the English sentence
			# and increment its frequency count
			for english_token in english_tokens:
				if english_token.type() == self._ambig_word:
					self._ambig_word_fdist.inc(
						self._ambig_word)
					contains_ambig_word = True
					break
	
			# increment the frequency count for each German word
			in_sent = {}
			for german_token in german_tokens:
				german_word = german_token.type()
				if not in_sent.has_key(german_word) and \
					self.not_punctuation(german_word):
					self._trans_fdist.inc(german_word)
					in_sent[german_word] = True

					# increment the co-occurence frequency
					# count
					if contains_ambig_word:
						self._cooccur_fdist.inc(
								german_word) 

		return				


	def not_punctuation(self, word):
		"""
		Returns True if the given word is not punctuation and False 
		otherwise.
		"""
		# uses a regular expression for punctuation as any number of 
		# non-word characters 
		punct_regexp = re.compile(r'[^a-zA-Z0-9]*$')
		if punct_regexp.match(word):
			return False 
		else:
			return True


	def get_trans_score_pairs(self):
		"""
		Get a list of translation, score tuples, sorted from most 
		likely to least likely. Every possible tranlsation of the 
		English word (i.e. every German word that occurs in a 
		sentence aligned with an English sentence containing the 
		English word) is given a score between 0 and 1. 
		This score is a measure of the dependence between the 
		ambiguous word and the possible translation. The score is 
		calculated from the values in a 2-by-2 contingency table 
		(a table containing counts of the word cooccurence and 
		word non-cooccurence). The score (called phi squared) is a 
		variant of the chi squared score, commonly
		used in the identification of collocations. Phi squared
		is described in William A. Gale and Kenneth Ward Church 
		(1991). "Identifying Word Correspondences in Parallel Texts"
		Proceedings of the DARPA SNL Workshop.

		See the assosciated report for an further explanation of 
		contingency tables and phi squared.

		The list of possible translations is then sorted from most 
		likely to least likely according to phi squared score. The
		higher the phi-squared score the more dependent the two words
		are and the more likely the German word is to be a translation 
		of the English word. 
		"""
		# for every possible translation of the ambiguous word 
		# construct a contingency table and calculate the phi 
		# squared score 
		samples = []
		for sample in self._cooccur_fdist.samples():
			# calculate the contingency table values
			a = self._cooccur_fdist.count(sample)
			b = self._ambig_word_fdist.count(self._ambig_word) - a
			c = self._trans_fdist.count(sample) - a
			d = self._num_sents - a - b - c
				
			# do the maths
			score = self.calc_score(a, b, c, d)

			samples.append((score, sample))

		# sort from most likely to least likely translation
		samples.sort()
		samples.reverse()

		return samples 


	def calc_score(self, a, b, c, d):
		"""
		Given the values of a 2-by-2 contingency table, calculate 
		the phi squared score as per Church and Gale's formula (see 
		reference in description of get_trans_score_pairs() above).

		a = no. sents containing both the German and English words
		b = no. sents containing the English but not the German word
		c = no. sents containing the German but not the English word
		d = no. sents containing neither the English or German word

		See the assosciated report for an further explanation of 
		contingency tables and phi squared.
		"""
		top = (a * d - b * c)**2
		bottom = (a + b)*(a + c)*(b + d)*(c + d)
		
		score = top / bottom 
		return score 


	def get_translations(self):
		"""
		Get a list of the ambiguous word's possible translations 
		sorted from most likely to least likely. 
		""" 
		return [trans for (score, trans) in 
				self.get_trans_score_pairs()]


	def get_translation(self, german_sentence):
		"""
		Get the translation of the ambiguous word in the given German 
		sentence. We take this to be the highest ranked possible 
		translation that occurs in the German sentence.
		"""
		# tokenize the german sentence
		german_tokens = WSTokenizer().tokenize(german_sentence)
		german_types = [token.type() for token in german_tokens] 

		# get the list of possible translations sorted from most 
		#likely to least likely if we haven't already  
		if self._poss_translations == None: 
			self._poss_translations = self.get_translations()
		for poss_trans in self._poss_translations:
			# take the most likely translation that occurs in our
			# german sentence 
			if german_types.count(poss_trans) != 0:
				return poss_trans

		return None


	def get_sense_tag(self, german_sentence, num_senses):
		"""
		Get the sense-tag of the ambiguous word in the given German 
		sentence containing its translation. German translations 
		are grouped into "sense groups" because many translations are
		compound nouns containing morphemes that are translations not
		only of the ambiguous English word, but also of other word 
		or concepts (not to metion grammatical morphology such as 
		plural endings etc.). 
		For example: "Zins" is a direct translation of "interest", 
		however it occurs translated in German corpora within 
		compounds such as "Zinserhoehung" or "Zinsniveau". 
		Sense-grouping aims to collapse such compounds into the one 
		"sense group" corresponding to "Zins".
 
		If num_senses is greater than 1, then we take the most-likely
		num_senses senses and return the sense-tag of the sense 
		group that the direct translation fits into. If the word's 
		direct translation does no occur in a sense group, we return 
		None.

		If num_senses is 0 then we do not attempt to group the 
		translations into sense groups. Instead we return the direct 
		translation.	
		"""
		# get the most likely translation
		translation = self.get_translation(german_sentence)
		if translation == None:
			return None

		# do not perform sense-grouping- return the direct translation
		if num_senses ==0:
			return translation

		# create the sense dictionary if we haven't already
		if self._sense_dict == None:
			self._sense_dict, self._sense_list = self.sense_group(
				self._poss_translations, num_senses)
		# get the translation's corresponding sense tag
		if self._sense_dict.has_key(translation):
			return self._sense_dict[translation]
		else:
			for sense in self._sense_list:
				low_trans = translation.lower()
				if low_trans.find(sense) != -1:
					return sense

		return None
		

	def sense_group(self, trans_list, num_senses):
		"""
		Group the translations into "sense groups" according to common
		morphology. The grouping is done by searching for common 
		substrings in the translations. We take a 4 letter prefix 
		from each the top 30 possible translations and search for
		this prefix within the other translations. The idea is that the
		4-letter prefix contains information that will help to locate 
		common morphemes that occur in the translations.    
		
		Of course this is not foolproof as some morphemes may not 
		occur as prefixes and 4 letters may not distinguish some 
		morphemes from one another - see the associated report for
		a broader discussion of this strategy.

		For each of the resulting "sense groups" the phi squared score
		(discussed above) is recalculated for the group and the 
		groups are then sorted by these scores. The specified number 
		of highest ranked senses (given by num_senses) is then taken 
		from the sense groups.
		
		Returns a set of translation /sense mappings and a list of the
		valid senses (by prefix).       	
		"""
		# take the first 30 possible translations and search for 
		# prefixes that form common substrings  
		senses = {}
		trans_len = 30 
		for i in range(len(trans_list[:trans_len])):
			trans = trans_list[i]
			prefix = trans[:4].lower() 	
			if not senses.has_key(prefix):
				senses[prefix] = [trans]
			for trans1 in trans_list[i:trans_len] + trans_list[:i]:
				substring_index = trans1.lower().find(prefix)
				if substring_index != -1:
					if senses[prefix].count(trans1) == 0:
						senses[prefix].append(trans1)
		
		# recaluate the phi squared score for each sense group
		scored_senses = []
		for sense in senses.keys():
			total_a = 0 
			total_c = 0 
			translations = senses[sense]
			for trans in translations:
				a = self._cooccur_fdist.count(trans)
				c = self._trans_fdist.count(trans) - a
				total_a += a
				total_c += c
				
			b = self._ambig_word_fdist.count(self._ambig_word) \
				- total_a
			d = self._num_sents - total_a - b - total_c
	
			new_score = self.calc_score(total_a, b, total_c, d)
			# a dictionary of sense/ score pairs
			scored_senses.append((new_score, sense))
	 
 		scored_senses.sort()
		scored_senses.reverse()
	
		# take the specified number of highest ranked senses 
		valid_senses = [sense for (score, sense) in 
				scored_senses[:num_senses]]

		# reverse the list of senses, so that we take the most 
		# likely sense for the translation 
		valid_senses.reverse()
		
		# construct a translation, sense mapping for the valid senses
		sense_dict = {}
		for valid_sense in valid_senses:
			t_list = senses[valid_sense] 
			for trans in t_list:
				sense_dict[trans] = valid_sense
	
		return sense_dict, valid_senses

