# Natural Language Toolkit: Interface to MaltParser
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2015 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_function

import os
import fnmatch
import tempfile
import subprocess
import inspect

from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag
from nltk.data import ZipFilePathPointer

from nltk.parse.api import ParserI
from nltk.parse.dependencygraph import DependencyGraph

def find_jars_within_path(path_to_jars):
	return [os.path.join(root, filename) 
			for root, dirnames, filenames in os.walk(path_to_jars) 
			for filename in fnmatch.filter(filenames, '*.jar')]

def taggedsent_to_conll(sentences):
	"""
	A module to convert the a POS tagged document stream 
	(i.e. list of list of tuples) and yield lines in CONLL format. 
	This module yields one line per word and two newlines for end of sentence. 

	>>> from nltk import word_tokenize, sent_tokenize
	>>> text = "This is a foobar sentence. Is that right?"
	>>> sentences = [word_tokenize(sent) for sent in sent_tokenize(text)]
	>>> for line in taggedsent_to_conll(sentences):
	...     print(line, end="")
	1    This    _    DT    DT    _    0    a    _    _
	2    is    _    VBZ    VBZ    _    0    a    _    _
	3    a    _    DT    DT    _    0    a    _    _
	4    foobar    _    NN    NN    _    0    a    _    _
	5    sentence    _    NN    NN    _    0    a    _    _
	6    .    _    .    .    _    0    a    _    _

	1    Is    _    VBZ    VBZ    _    0    a    _    _
	2    that    _    IN    IN    _    0    a    _    _
	3    right    _    JJ    JJ    _    0    a    _    _
	4    ?    _    .    .    _    0    a    _    _
	"""
	for sentence in sentences:
		for (i, (word, tag)) in enumerate(sentence, start=1):
			input_str = '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
			% (i, word, '_', tag, tag, '_', '0', 'a', '_', '_')
			yield input_str
		yield '\n\n'

def malt_regex_tagger():
	from nltk.tag import RegexpTagger
	_tagger = RegexpTagger(
	[(r'\.$','.'), (r'\,$',','), (r'\?$','?'),	# fullstop, comma, Qmark
	(r'\($','('), (r'\)$',')'), 				# round brackets
	(r'\[$','['), (r'\]$',']'), 				# square brackets
	(r'^-?[0-9]+(.[0-9]+)?$', 'CD'),			# cardinal numbers
	(r'(The|the|A|a|An|an)$', 'DT'),			# articles
	(r'(He|he|She|she|It|it|I|me|Me|You|you)$', 'PRP'), # pronouns
	(r'(His|his|Her|her|Its|its)$', 'PRP$'), 			# possesive
	(r'(my|Your|your|Yours|yours)$', 'PRP$'), 			# possesive
	(r'(on|On|in|In|at|At|since|Since)$', 'IN'), 	# time prepopsitions
	(r'(for|For|ago|Ago|before|Before)$', 'IN'),	# time prepopsitions
	(r'(till|Till|until|Until)$', 'IN'),  			# time prepopsitions
	(r'(by|By|beside|Beside)$', 'IN'),				# space prepopsitions
	(r'(under|Under|below|Below)$', 'IN'),			# space prepopsitions
	(r'(over|Over|above|Above)$', 'IN'),			# space prepopsitions
	(r'(across|Across|through|Through)$', 'IN'),	# space prepopsitions
	(r'(into|Into|towards|Towards)$', 'IN'),		# space prepopsitions
	(r'(onto|Onto|from|From)$', 'IN'),				# space prepopsitions
	(r'.*able$', 'JJ'),                # adjectives
	(r'.*ness$', 'NN'),                # nouns formed from adjectives
	(r'.*ly$', 'RB'),                  # adverbs
	(r'.*s$', 'NNS'),                  # plural nouns
	(r'.*ing$', 'VBG'),                # gerunds
	(r'.*ed$', 'VBD'),                 # past tense verbs
	(r'.*', 'NN'),                     # nouns (default)
	])
	return _tagger.tag

class MaltParser(ParserI):
	def __init__(self, path_to_maltparser, model=None, tagger=None, 
		     working_dir=None, additional_java_args=[]):
		"""
		An interface for parsing with the Malt Parser.

		:param model: The name of the pre-trained model with .mco file 
		extension. If provided, training will not be required.
		(see http://www.maltparser.org/mco/mco.html and 
		see http://www.patful.com/chalk/node/185)
		:type model: str
		:param tagger: The tagger used to POS tag the raw string before 
		formatting to CONLL format. It should behave like `nltk.pos_tag`
		:type tagger: function
		:param additional_java_args: This is the additional Java arguments that 
		one can use when calling Maltparser, usually this is the heapsize 
		limits, e.g. `additional_java_args=['-Xmx1024m']`
		(see http://goo.gl/mpDBvQ)
		:type additional_java_args: list
		:param path_to_maltparser: The path to the maltparser directory that 
		contains the maltparser-1.x.jar
		:type path_to_malt_binary: str
		"""
		
		# Collects all the jar files found in the MaltParser distribution.
		self.malt_jars = find_jars_within_path(path_to_maltparser)
		# Initialize additional java arguments.
		self.additional_java_args = additional_java_args
		# Initialize model.
		self.model = 'malt_temp.mco' if model is None else model
		self._trained = False if self.model == 'malt_temp' else True
		# Set the working_dir parameters i.e. `-w` from MaltParser's option.
		self.working_dir = tempfile.gettempdir() \
				        if working_dir is None  else working_dir
		# Initialize POS tagger.
		if tagger is not None:
			self.tagger = tagger
		else:
			self.tagger = malt_regex_tagger()	

	def pretrained_model_sanity_checks(self, tree_str):
		"""
		Performs sanity checks and replace oddities in pre-trained model
		outputs from http://www.maltparser.org/mco/english_parser/engmalt.html
		
		:param tree_str: The CONLL output file for a single parse
		:type tree_str: str
		:return: str
		"""
		# Checks for oddities in English pre-trained model.
		if '\t0\tnull\t' in tree_str and \
		(self.model.endswith('engmalt.linear-1.7.mco') or
		self.model.endswith('engmalt.poly-1.7.mco')
		):
			tree_str = tree_str.replace('\t0\tnull\t','\t0\tROOT\t')
		# Checks for oddities in French pre-trained model.
		if '\t0\troot\t' in tree_str and \
		self.model.endswith('fremalt-1.7.mco'):
			tree_str = tree_str.replace('\t0\troot\t','\t0\tROOT\t')
		return tree_str	
	
	def parse_tagged_sents(self, sentences, verbose=False):
		"""
		Use MaltParser to parse multiple POS tagged sentences. Takes multiple 
		sentences where each sentence is a list of (word, tag) tuples. 
		The sentences must have already been tokenized and tagged.

		:param sentences: Input sentences to parse
		:type sentence: list(list(tuple(str, str)))
		:return: iter(iter(``DependencyGraph``)) the dependency graph 
		representation of each sentence
		"""
		if not self._trained:
			raise Exception("Parser has not been trained. Call train() first.")

		input_file = tempfile.NamedTemporaryFile(prefix='malt_input.conll', 
										dir=self.working_dir, 
										mode='w', delete=False)
		output_file = tempfile.NamedTemporaryFile(prefix='malt_output.conll', 
										dir=self.working_dir, 
										mode='w', delete=False)

		try: 
			# Convert list of sentences to CONLL format.
			for line in taggedsent_to_conll(sentences):
				input_file.write(line)
			input_file.close()

			# Generate command to run maltparser.
			cmd =self.generate_malt_command(input_file.name, 
			output_file.name,
			mode="parse")

			# This is a maltparser quirk, it needs to be run 
			# where the model file is. otherwise it goes into an awkward
			# missing .jars or strange -w working_dir problem.
			_current_path = os.getcwd() # Remembers the current path.
			try: # Change to modelfile path
				os.chdir(os.path.split(self.model)[0]) 
			except:
				pass
			ret = self._execute(cmd, verbose) # Run command.
			os.chdir(_current_path) # Change back to current path.

			if ret != 0:
				raise Exception("MaltParser parsing (%s) failed with exit "
								"code %d" % (' '.join(cmd), ret))

			# Must return iter(iter(Tree))
			with open(output_file.name) as infile:
				for tree_str in infile.read().split('\n\n'):
					tree_str = self.pretrained_model_sanity_checks(tree_str)
					yield(iter([DependencyGraph(tree_str)]))
					
		finally:
			# Deletes temp files created in the process.
			input_file.close()
			#os.remove(input_file.name)
			output_file.close()
			#os.remove(output_file.name)

	
	def parse_sents(self, sentences, verbose=False):
		"""
		Use MaltParser to parse multiple sentences. 
		Takes a list of sentences, where each sentence is a list of words.
		Each sentence will be automatically tagged with this 
		MaltParser instance's tagger.

		:param sentences: Input sentences to parse
		:type sentence: list(list(str))
		:return: iter(DependencyGraph)
		"""
		tagged_sentences = [self.tagger(sentence) for sentence in sentences]
		parsed_sentences = self.parse_tagged_sents(tagged_sentences, verbose)
		return parsed_sentences
		
		
	def generate_malt_command(self, inputfilename, outputfilename=None, 
							mode=None):
		"""
		This function generates the maltparser command use at the terminal.

		:param inputfilename: path to the input file
		:type inputfilename: str
		:param outputfilename: path to the output file
		:type outputfilename: str
		"""

		cmd = ['java']
		cmd+= self.additional_java_args # Adds additional java arguments.
		cmd+= ['-cp', ':'.join(self.malt_jars)] # Adds classpaths for jars
		cmd+= ['org.maltparser.Malt'] # Adds the main function.
		##cmd+= ['-w', self.working_dir]

		# Adds the model file.
		if os.path.exists(self.model): # when parsing
			cmd+= ['-c', os.path.split(self.model)[-1]] 
		else: # when learning
			cmd+= ['-c', self.model]

		cmd+= ['-i', inputfilename]
		if mode == 'parse':
			cmd+= ['-o', outputfilename]
		cmd+= ['-m', mode] # mode use to generate parses.
		#print(" ".join(cmd))
		return cmd

	@staticmethod
	def _execute(cmd, verbose=False):
		output = None if verbose else subprocess.PIPE
		p = subprocess.Popen(cmd, stdout=output, stderr=output)
		return p.wait()

	def train(self, depgraphs, verbose=False):
		"""
		Train MaltParser from a list of ``DependencyGraph`` objects

		:param depgraphs: list of ``DependencyGraph`` objects for training input data
		:type depgraphs: DependencyGraph
		"""
		input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
				                                 dir=self.working_dir,
				                                 delete=False)
		try:
			input_str = ('\n'.join(dg.to_conll(10) for dg in depgraphs))
			input_file.write(input_str)
			input_file.close()
			self.train_from_file(input_file.name, verbose=verbose)
		finally:
			input_file.close()
			#os.remove(input_file.name)
            
	def train_from_file(self, conll_file, verbose=False):
		"""
		Train MaltParser from a file
		:param conll_file: str for the filename of the training input data
		:type conll_file: str
		"""

		# If conll_file is a ZipFilePathPointer, 
		# then we need to do some extra massaging
		if isinstance(conll_file, ZipFilePathPointer):
			input_file = tempfile.NamedTemporaryFile(prefix='malt_train.conll',
				                                    dir=self.working_dir, 
				                                    mode='w', delete=False)
			try:
				conll_str = conll_file.open().read()
				conll_file.close()
				input_file.write(conll_str)
				input_file.close()
				return self.train_from_file(input_file.name, verbose=verbose)
			finally:
				input_file.close()
				#os.remove(input_file.name)

		# Generate command to run maltparser.
		cmd =self.generate_malt_command(conll_file, mode="learn")
		
		ret = self._execute(cmd, verbose)
		if ret != 0:
			raise Exception("MaltParser training (%s) "
				            "failed with exit code %d" %
				            (' '.join(cmd), ret))

		self._trained = True

	
if __name__ == '__main__':
	'''
	A demostration function to show how NLTK users can use the malt parser API.
	'''

	#########################################################################
	# Demo to train a new model with DependencyGraph objects and 
	# parse example sentences with the new model.
	#########################################################################
	_dg1_str = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
					"2    sees    _    VB    _    _    0    ROOT    _    _\n"
					"3    a       _    DT    _    _    4    SPEC    _    _\n"
					"4    dog     _    NN    _    _    2    OBJ     _    _\n"
					"4    .     _    .    _    _    2    PUNCT     _    _\n")


	_dg2_str  = str("1    John    _    NNP   _    _    2    SUBJ    _    _\n"
					"2    walks   _    VB    _    _    0    ROOT    _    _\n"
					"3    .     _    .    _    _    2    PUNCT     _    _\n")
	dg1 = DependencyGraph(_dg1_str)
	dg2 = DependencyGraph(_dg2_str)

	# Initial a MaltParser object
	verbose = False
	path_to_maltparser = '/home/alvas/maltparser-1.7.2/'
	mp = MaltParser(path_to_maltparser=path_to_maltparser)
	# Trains a model.
	mp.train([dg1,dg2], verbose=verbose)
	
	sent1 = ['John','sees','Mary', '.']
	sent2 = ['John', 'walks', 'a', 'dog', '.']
	# Parse a single sentence.
	parsed_sent1 = mp.parse_one(sent1)
	parsed_sent2 = mp.parse_one(sent2)
	print (parsed_sent1.tree())
	print (parsed_sent2.tree())
	# Parsing multiple sentences.
	sentences = [sent1,sent2]
	parsed_sents = mp.parse_sents(sentences)
	print(next(next(parsed_sents)).tree())
	print(next(next(parsed_sents)).tree())

	
	#########################################################################
	# Demo to parse example sentences with pre-trained English model
	#########################################################################

	# Initialize a MaltParser object with an English pre-trained model.
	path_to_maltparser = '/home/alvas/maltparser-1.7.2/'
	path_to_model = '/home/alvas/engmalt.linear-1.7.mco'
	mp = MaltParser(path_to_maltparser=path_to_maltparser, model=path_to_model, tagger=pos_tag)	
	sent = 'I shot an elephant in my pajamas .'.split()
	sent2 = 'Time flies like banana .'.split()
	# Parse a single sentence.
	print(mp.parse_one(sent).tree())
	# Parsing multiple sentences
	sentences = [sent1,sent2]
	parsed_sents = mp.parse_sents(sentences)
	print(next(next(parsed_sents)).tree())
	print(next(next(parsed_sents)).tree())

	
	#########################################################################
	# Demo to parse example sentences with pre-trained French model
	#########################################################################

	path_to_maltparser = '/home/alvas/maltparser-1.7.2/'
	path_to_model = '/home/alvas/fremalt-1.7.mco'

	# Initialize a MaltParser object with a French pre-trained model.
	mp = MaltParser(path_to_maltparser=path_to_maltparser, model=path_to_model)	
	sent = 'Nous prions les cineastes et tous nos lecteurs de bien vouloir nous en excuser .'.split()
	pos = 'CLS V DET NC CC ADJ DET NC P ADV VINF CLS CLO VINF PUNCT'.split()
	tagged_sent = list(zip(sent,pos))

	parsed_sent = mp.parse_tagged_sents([tagged_sent])
	print(next(next(parsed_sent)).tree())

	


