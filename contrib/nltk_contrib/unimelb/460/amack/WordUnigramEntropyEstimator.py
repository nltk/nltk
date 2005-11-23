#!/usr/bin/python

import pickle
import re
import sys
import commands
from string import rstrip
from getopt import getopt
from nltk.tokenizer import Token
from nltk.tokenizer import RegexpTokenizer
from nltk.probability import WittenBellProbDist
from nltk.probability import FreqDist

def main():
	opts, args = getopt(sys.argv[1:], "c:t:l:b:w:v:")
	estimator_load_fname = None
	estimator_save_fname = None
	est_vocab_size = 20000
	textcat_path = None
	num_likely_words = None
	training_mode = False
	bootstrap_mode = False
	for o, p in opts:
		if o == "-c":
			textcat_path = p
		if o == "-l":
			estimator_load_fname = p
		if o == "-b":
			bootstrap_thresh = float(p)
			bootstrap_mode = True
		if o == "-t":
			estimator_save_fname = p
			training_mode = True
		if o == "-w":
			num_likely_words = int(p)
		if o == "-v":
			est_vocab_size = int(p)

	if len(args) == 0: fnames = sys.stdin
	else: fnames = args

	if bootstrap_mode: training_mode = False

	if estimator_load_fname != None:
		estimator = pickle.load(open(estimator_load_fname, 'r'))
	else:
		estimator = WordUnigramEntropyEstimator(est_vocab_size)

	if training_mode:
		for line in fnames:
			sample_tokens = Token(TEXT = open(rstrip(line), "r").read())
			estimator.train(sample_tokens)
		estimator.rebuild()
		pickle.dump(estimator, open(estimator_save_fname, "w"))
		
	elif bootstrap_mode:
		boots_fname_list = []
		for line in fnames:
			fname = rstrip(line)
			sample_tokens = Token(TEXT = open(fname, "r").read())
			file_ent = estimator.get_log_prob_per_word(sample_tokens)
			if file_ent >= bootstrap_thresh:
				boots_fname_list.append(fname)
			sys.stderr.write('.')
		new_estimator = WordUnigramEntropyEstimator()
		print("Training on %d files" % len(boots_fname_list))
		for fname in boots_fname_list:
			new_estimator.train(Token(TEXT = open(fname, "r").read()))
		new_estimator.rebuild()	
		pickle.dump(new_estimator, open(estimator_save_fname, "w"))
		estimator = new_estimator
			
	else:
		file_ent_list = []
		for line in fnames:
			fname = rstrip(line)
			sample_tokens = Token(TEXT = open(fname, "r").read())
			file_ent = estimator.get_log_prob_per_word(sample_tokens)
			if file_ent != None:
				file_ent_list.append((fname, file_ent))
			sys.stderr.write('.')
		file_ent_list.sort(fname_ent_cmp)
		for (fname, ent) in file_ent_list:
			if textcat_path != None:
				textcat_res = commands.getoutput(textcat_path + ' ' + fname)
			else:
				textcat_res = ""
			print("%s\t%4.2f\t%s" % (fname, ent, textcat_res))

	if num_likely_words:
		likely = estimator.get_most_probable_words(num_likely_words)
		for word in likely:
			print(word)
			

def fname_ent_cmp((fname1, ent1), (fname2, ent2)):
	if ent1 < ent2:
		return -1
	elif ent1 > ent2:
		return 1
	elif fname1 < fname2:
		return -1
	elif fname1 > fname2:
		return 1
	else:
		return 0	
	



class WordUnigramEntropyEstimator:
	
	def __init__(self, EstVocabSize = 20000):
		self.est_vocab_size = EstVocabSize
		self.unigram_freq_dist = FreqDist()
		self.prob_dist = None
		self.custTokenizer = RegexpTokenizer(r'([^\s\[\]\{\}\(\)"]*[\w%]+)|([^\w\s]+)', SUBTOKENS = 'WORDS')
		self.alpha_regexp = re.compile(r'[a-z]+')

	def get_log_prob_per_word(self, tokens):
		if self.prob_dist == None:
			return None
		self.custTokenizer.tokenize(tokens)
		prob_sum = 0
		num_words = 0
		for word_token in tokens['WORDS']:
			num_words += 1
			word_text = word_token['TEXT'].lower()  
			prob_sum -= self.prob_dist.logprob(word_token['TEXT'])
		if num_words > 0:
			return float(prob_sum)/num_words
		else:
			return None


	def rebuild(self):
		self.prob_dist = WittenBellProbDist(self.unigram_freq_dist, self.est_vocab_size)
	
	def get_most_probable_words(self, num = 1):
		return self.unigram_freq_dist.sorted_samples()[:num]

	def train(self, tokens):
		self.custTokenizer.tokenize(tokens)
		for word_token in tokens['WORDS']:
			word_text = word_token['TEXT'].lower()  
			if self.alpha_regexp.search(word_text):	#test that there is >= 1 alphnumeric character
				self.unigram_freq_dist.inc(word_text)	#increment the counter in the distribution for word

	def __getstate__(self):
		odict = self.__dict__.copy()
		del odict['custTokenizer']
		return odict
		
	def __setstate__(self, dict): # as custTokenizer can't be unpickled for some reason
		self.custTokenizer = RegexpTokenizer(r'([^\s\[\]\{\}\(\)"]*[\w%]+)|([^\w\s]+)', SUBTOKENS = 'WORDS')
		self.__dict__.update(dict)
"""	
	def __reduce__(self):
		return "WordUnigramEntropyEstimator"
"""

if __name__ == "__main__":
    main()


